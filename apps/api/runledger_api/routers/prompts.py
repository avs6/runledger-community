"""
Prompts API — version-controlled prompt management.

Prefix: /prompts
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /prompts                        Create a new prompt
GET    /prompts                        List prompts for workspace
GET    /prompts/{name}                 Get prompt metadata
DELETE /prompts/{name}                 Delete prompt + all versions
POST   /prompts/{name}/versions        Commit a new version
GET    /prompts/{name}/versions        List all versions (desc)
GET    /prompts/{name}/latest          Latest version for an environment (SDK pull)
GET    /prompts/{name}/versions/{v}    Get a specific version
PATCH  /prompts/{name}                 Update description, default env, score gate
POST   /prompts/{name}/promote         Promote latest staging → production
GET    /prompts/{name}/metrics         Per-version cost + avg score + run count
POST   /prompts/{name}/promotion-requests  Ask for a prompt_promote approval
GET    /prompts/{name}/promotion-requests  Approvals for this prompt (pending/approved/used)
GET    /prompts/{name}/versions/{v}/score  Score used by the promotion gate
GET    /prompts/{name}/diff            Line diff between two versions

Production governance (review B-02, B-03): every way into the production
environment (create, edit, promote, GitHub pull) needs an approved
``prompt_promote`` approval for this prompt, and each approval authorises exactly
one production version. A prompt can also carry a score gate: the source version
must score at least ``promotion_min_score`` before it can be promoted.
"""

from __future__ import annotations

import base64
import difflib
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_api_key,
    get_current_workspace,
    require_workspace_admin,
    require_workspace_writer,
)
from runledger_api.core.pagination import PageDep, paginate
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.approvals import Approval
from runledger_api.models.eval_experiments import EvalExperiment, PromptGithubConfig
from runledger_api.models.events import AgentRun
from runledger_api.models.prompts import Prompt, PromptVersion
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.routers.approvals import create_approval, validate_approved
from runledger_api.schemas.approvals import ApprovalCreate
from runledger_api.schemas.eval_experiments import (
    GithubConfigCreate,
    GithubConfigResponse,
    GithubConfigUpdate,
    GithubSyncResult,
)
from runledger_api.schemas.prompts import (
    DiffLine,
    PromoteRequest,
    PromotionApproval,
    PromotionApprovalList,
    PromotionRequestCreate,
    PromptCreate,
    PromptDiff,
    PromptList,
    PromptMetrics,
    PromptResponse,
    PromptUpdate,
    VersionCreate,
    VersionList,
    VersionMetrics,
    VersionResponse,
    VersionScore,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.github_sync import pull_prompts_from_github, push_prompts_to_github
from runledger_api.services.kafka_export import encrypt_secret_value, resolve_secret_value

router = APIRouter(
    prefix="/prompts",
    tags=["prompts"],
    dependencies=[Depends(management_rate_limit)],
)
log = structlog.get_logger()

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
ApiKeyDep = Annotated[ApiKey, Depends(get_current_api_key)]

# Deployment version convention: "{prompt_name}:{version_number}"
_DEPLOYMENT_VERSION_RE = re.compile(r"^(.+):(\d+)$")


async def _get_prompt_or_404(name: str, workspace_id: uuid.UUID, db: AsyncSession) -> Prompt:
    result = await db.execute(
        select(Prompt).where(Prompt.workspace_id == workspace_id, Prompt.name == name)
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")
    return prompt


# ── Production governance helpers (review B-02, B-03; ENH score gate) ──────────


def _pulled_environment(env: str | None) -> str:
    """Environment for a version pulled from GitHub: never production directly."""
    if env in ("dev", "staging"):
        return env
    return "staging"


def _approval_prompt_name(approval: Approval) -> str | None:
    request = approval.request or {}
    value = request.get("prompt_name") or request.get("prompt")
    return str(value) if value else None


async def _require_production_approval(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    name: str,
    approval_id: uuid.UUID | None,
) -> Approval:
    """An approved ``prompt_promote`` approval for this prompt that hasn't been used yet."""
    if approval_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Writing to production requires an approved prompt_promote approval. "
                f"Request one with POST /prompts/{name}/promotion-requests (or POST /approvals "
                "with request_type='prompt_promote' and request.prompt_name), then pass its "
                "approval_id once approved."
            ),
        )
    approval = await validate_approved(db, workspace_id, approval_id, "prompt_promote")
    approved_for = _approval_prompt_name(approval)
    if approved_for != name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Approval is for prompt '{approved_for}', not '{name}'",
        )
    used = (
        await db.execute(
            select(PromptVersion.version).where(PromptVersion.approval_id == approval.id)
        )
    ).scalar_one_or_none()
    if used is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval was already used for v{used}; request a new one",
        )
    return approval


async def _version_score(
    db: AsyncSession, workspace_id: uuid.UUID, prompt: Prompt, version: int
) -> VersionScore:
    """Score the promotion gate checks: the latest completed experiment on this
    version if there is one, otherwise the average score of its recorded runs."""
    gate = prompt.promotion_min_score
    score: float | None = None
    source: str | None = None
    sample = 0

    exp = (
        await db.execute(
            select(EvalExperiment)
            .where(
                EvalExperiment.workspace_id == workspace_id,
                EvalExperiment.prompt_name == prompt.name,
                EvalExperiment.prompt_version == version,
                EvalExperiment.status == "completed",
            )
            .order_by(EvalExperiment.completed_at.desc().nulls_last())
            .limit(1)
        )
    ).scalar_one_or_none()
    if exp is not None and isinstance(exp.results, dict):
        overall = exp.results.get("summary", {}).get("avg_score")
        if overall is not None:
            score = float(overall)
            source = "experiment"
            sample = int(exp.results.get("summary", {}).get("scored_items") or 0)

    if score is None:
        stmt = select(func.avg(ScoreEvent.value), func.count(ScoreEvent.id)).where(
            ScoreEvent.workspace_id == workspace_id,
            ScoreEvent.run_id.in_(
                select(AgentRun.id).where(
                    AgentRun.workspace_id == workspace_id,
                    AgentRun.deployment_version == f"{prompt.name}:{version}",
                )
            ),
        )
        if prompt.promotion_score_name:
            stmt = stmt.where(ScoreEvent.name == prompt.promotion_score_name)
        avg, count = (await db.execute(stmt)).one()
        if count:
            score = float(avg)
            source = "runs"
            sample = int(count)

    passes: bool | None = None
    if gate is not None:
        passes = score is not None and score >= gate
    return VersionScore(
        version=version,
        score=score,
        source=source,
        sample_size=sample,
        min_score=gate,
        passes_gate=passes,
    )


# ── POST /prompts ──────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer)],
)
async def create_prompt(
    body: PromptCreate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> PromptResponse:
    """Create a new named prompt template."""
    # Check uniqueness within workspace
    existing = await db.execute(
        select(Prompt).where(Prompt.workspace_id == workspace.id, Prompt.name == body.name)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail=f"Prompt '{body.name}' already exists")

    prompt = Prompt(
        workspace_id=workspace.id,
        name=body.name,
        description=body.description,
        default_environment=body.default_environment,
        promotion_min_score=body.promotion_min_score,
        promotion_score_name=body.promotion_score_name,
    )
    db.add(prompt)
    await db.flush()
    await db.commit()
    await db.refresh(prompt)
    log.info("prompt_created", workspace_id=str(workspace.id), name=body.name)
    return PromptResponse.model_validate(prompt)


# ── GET /prompts ───────────────────────────────────────────────────────────────


@router.get("", response_model=PromptList)
async def list_prompts(
    workspace: WorkspaceDep,
    db: DbDep,
    page: PageDep,
    response: Response,
) -> PromptList:
    """List prompts for the workspace (paged; total in X-Total-Count)."""
    items = await paginate(
        db,
        select(Prompt)
        .where(Prompt.workspace_id == workspace.id)
        .order_by(Prompt.created_at.desc(), Prompt.id),
        page,
        response,
    )
    return PromptList(items=[PromptResponse.model_validate(p) for p in items])


# ── GitHub sync endpoints (must come before /{name} to avoid route capture) ───


def _decrypt_token(token_enc: str | None) -> str | None:
    """Decrypt stored token or fall back to env var."""
    if token_enc:
        if token_enc.startswith("enc::"):
            return resolve_secret_value(token_enc)
        if token_enc.startswith("b64:"):  # legacy, written before encryption at rest
            return base64.b64decode(token_enc[4:]).decode()
        return token_enc
    return os.environ.get("GITHUB_TOKEN")


@router.get("/github-config", response_model=GithubConfigResponse | None)
async def get_github_config(workspace: WorkspaceDep, db: DbDep) -> PromptGithubConfig | None:
    """Get GitHub sync config for this workspace."""
    result = await db.execute(
        select(PromptGithubConfig).where(PromptGithubConfig.workspace_id == workspace.id)
    )
    return result.scalar_one_or_none()


@router.post(
    "/github-config",
    response_model=GithubConfigResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_admin)],
)
async def create_github_config(
    body: GithubConfigCreate, workspace: WorkspaceDep, db: DbDep
) -> PromptGithubConfig:
    """Create GitHub sync config for this workspace."""
    existing = await db.execute(
        select(PromptGithubConfig).where(PromptGithubConfig.workspace_id == workspace.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="GitHub config already exists — use PUT to update"
        )

    token_enc: str | None = None
    if body.token:
        token_enc = encrypt_secret_value(body.token)

    cfg = PromptGithubConfig(
        workspace_id=workspace.id,
        repo=body.repo,
        branch=body.branch,
        path_prefix=body.path_prefix,
        token_enc=token_enc,
        auto_sync=body.auto_sync,
    )
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.put(
    "/github-config",
    response_model=GithubConfigResponse,
    dependencies=[Depends(require_workspace_admin)],
)
async def update_github_config(
    body: GithubConfigUpdate, workspace: WorkspaceDep, db: DbDep
) -> PromptGithubConfig:
    """Update GitHub sync config."""
    result = await db.execute(
        select(PromptGithubConfig).where(PromptGithubConfig.workspace_id == workspace.id)
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="No GitHub config — use POST to create")

    if body.repo is not None:
        cfg.repo = body.repo
    if body.branch is not None:
        cfg.branch = body.branch
    if body.path_prefix is not None:
        cfg.path_prefix = body.path_prefix
    if body.token is not None:
        cfg.token_enc = encrypt_secret_value(body.token)
    if body.auto_sync is not None:
        cfg.auto_sync = body.auto_sync
    cfg.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.post(
    "/sync/push", response_model=GithubSyncResult, dependencies=[Depends(require_workspace_writer)]
)
async def push_to_github(workspace: WorkspaceDep, db: DbDep) -> GithubSyncResult:
    """Push all workspace prompts to GitHub."""
    result = await db.execute(
        select(PromptGithubConfig).where(PromptGithubConfig.workspace_id == workspace.id)
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="No GitHub config found. Create one first.")

    token = _decrypt_token(cfg.token_enc)
    if not token:
        raise HTTPException(status_code=400, detail="No GitHub token configured")

    prompts_result = await db.execute(select(Prompt).where(Prompt.workspace_id == workspace.id))
    prompts = list(prompts_result.scalars().all())

    prompt_dicts = []
    for p in prompts:
        versions_result = await db.execute(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == p.id)
            .order_by(PromptVersion.version.asc())
        )
        versions = list(versions_result.scalars().all())
        prompt_dicts.append(
            {
                "name": p.name,
                "description": p.description or "",
                "variables": [],
                "versions": [
                    {
                        "version": v.version,
                        "content": v.content,
                        "environment": v.environment,
                        "model_hint": v.model_hint,
                        "commit_message": v.commit_message or "",
                    }
                    for v in versions
                ],
            }
        )

    sync_result = await push_prompts_to_github(
        token, cfg.repo, cfg.branch, cfg.path_prefix, prompt_dicts
    )
    cfg.last_sync_at = datetime.now(UTC)
    cfg.last_sync_status = "success" if not sync_result["errors"] else "partial"
    cfg.last_sync_message = f"Pushed {sync_result['pushed']} prompts" + (
        f"; errors: {'; '.join(sync_result['errors'][:3])}" if sync_result["errors"] else ""
    )
    await db.commit()
    log.info("github_sync_push", workspace_id=str(workspace.id), **sync_result)
    return GithubSyncResult(
        pushed=sync_result["pushed"],
        pulled=0,
        skipped=sync_result["skipped"],
        errors=sync_result["errors"],
        synced_at=cfg.last_sync_at,
    )


@router.post(
    "/sync/pull", response_model=GithubSyncResult, dependencies=[Depends(require_workspace_writer)]
)
async def pull_from_github(workspace: WorkspaceDep, db: DbDep) -> GithubSyncResult:
    """Pull prompts from GitHub and upsert into workspace."""
    result = await db.execute(
        select(PromptGithubConfig).where(PromptGithubConfig.workspace_id == workspace.id)
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="No GitHub config found. Create one first.")

    token = _decrypt_token(cfg.token_enc)
    if not token:
        raise HTTPException(status_code=400, detail="No GitHub token configured")

    pulled_prompts, errors = await pull_prompts_from_github(
        token, cfg.repo, cfg.branch, cfg.path_prefix
    )
    pulled = 0
    for pd in pulled_prompts:
        pr_result = await db.execute(
            select(Prompt).where(Prompt.workspace_id == workspace.id, Prompt.name == pd["name"])
        )
        prompt = pr_result.scalar_one_or_none()
        if not prompt:
            prompt = Prompt(
                workspace_id=workspace.id, name=pd["name"], description=pd.get("description")
            )
            db.add(prompt)
            await db.flush()
        max_r = await db.execute(
            select(func.max(PromptVersion.version)).where(PromptVersion.prompt_id == prompt.id)
        )
        current_max = max_r.scalar() or 0
        for pv in pd.get("versions") or []:
            db.add(
                PromptVersion(
                    prompt_id=prompt.id,
                    version=current_max + 1,
                    content=pv.get("content", ""),
                    variables=[],
                    commit_message=pv.get("commit_message") or "Pulled from GitHub",
                    # Pulled versions never land in production directly; they go
                    # to staging and are promoted through an approval (review B-02).
                    environment=_pulled_environment(pv.get("environment")),
                    model_hint=pv.get("model_hint"),
                )
            )
            current_max += 1
        pulled += 1

    await db.commit()
    cfg.last_sync_at = datetime.now(UTC)
    cfg.last_sync_status = "success" if not errors else "partial"
    cfg.last_sync_message = f"Pulled {pulled} prompts" + (
        f"; errors: {'; '.join(errors[:3])}" if errors else ""
    )
    await db.commit()
    log.info("github_sync_pull", workspace_id=str(workspace.id), pulled=pulled, errors=len(errors))
    return GithubSyncResult(
        pushed=0, pulled=pulled, skipped=0, errors=errors, synced_at=cfg.last_sync_at
    )


# ── GET /prompts/{name} ────────────────────────────────────────────────────────


@router.get("/{name}", response_model=PromptResponse)
async def get_prompt(
    name: str,
    workspace: WorkspaceDep,
    db: DbDep,
) -> PromptResponse:
    """Get prompt metadata by name."""
    prompt = await _get_prompt_or_404(name, workspace.id, db)
    return PromptResponse.model_validate(prompt)


# ── PATCH /prompts/{name} ──────────────────────────────────────────────────────


@router.patch(
    "/{name}",
    response_model=PromptResponse,
    dependencies=[Depends(require_workspace_writer)],
)
async def update_prompt(
    name: str,
    body: PromptUpdate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> PromptResponse:
    """Update description, default environment, or the promotion score gate."""
    prompt = await _get_prompt_or_404(name, workspace.id, db)
    before = {
        "promotion_min_score": prompt.promotion_min_score,
        "promotion_score_name": prompt.promotion_score_name,
    }
    if body.description is not None:
        prompt.description = body.description
    if body.default_environment is not None:
        prompt.default_environment = body.default_environment
    if body.clear_promotion_gate:
        prompt.promotion_min_score = None
        prompt.promotion_score_name = None
    else:
        if body.promotion_min_score is not None:
            prompt.promotion_min_score = body.promotion_min_score
        if body.promotion_score_name is not None:
            prompt.promotion_score_name = body.promotion_score_name or None
    prompt.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(prompt)
    after = {
        "promotion_min_score": prompt.promotion_min_score,
        "promotion_score_name": prompt.promotion_score_name,
    }
    if before != after:
        await emit_audit_event(
            db,
            workspace.id,
            "prompt.gate_changed",
            target_type="prompt",
            target_id=name,
            before=before,
            after=after,
        )
    return PromptResponse.model_validate(prompt)


# ── DELETE /prompts/{name} ─────────────────────────────────────────────────────


@router.delete(
    "/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_workspace_writer)],
)
async def delete_prompt(
    name: str,
    workspace: WorkspaceDep,
    db: DbDep,
) -> None:
    """Delete a prompt and all its versions."""
    prompt = await _get_prompt_or_404(name, workspace.id, db)
    await db.delete(prompt)
    await db.commit()
    log.info("prompt_deleted", workspace_id=str(workspace.id), name=name)
    await emit_audit_event(db, workspace.id, "prompt.deleted", target_type="prompt", target_id=name)


# ── POST /prompts/{name}/versions ──────────────────────────────────────────────


@router.post(
    "/{name}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer)],
)
async def create_version(
    name: str,
    body: VersionCreate,
    workspace: WorkspaceDep,
    db: DbDep,
    approval_id: Annotated[uuid.UUID | None, Query()] = None,
) -> VersionResponse:
    """Commit a new version of the prompt template.

    Versions land in ``dev`` by default. Writing to ``production`` requires an approved
    ``prompt_promote`` approval for this prompt (body or ``?approval_id=``).
    """
    prompt = await _get_prompt_or_404(name, workspace.id, db)
    approval = None
    if body.environment == "production":
        approval = await _require_production_approval(
            db, workspace.id, name, body.approval_id or approval_id
        )

    # Auto-increment version number per prompt
    max_result = await db.execute(
        select(func.max(PromptVersion.version)).where(PromptVersion.prompt_id == prompt.id)
    )
    max_version = max_result.scalar() or 0
    new_version_num = max_version + 1

    version = PromptVersion(
        prompt_id=prompt.id,
        version=new_version_num,
        content=body.content,
        variables=body.variables,
        commit_message=body.commit_message,
        environment=body.environment,
        model_hint=body.model_hint,
        approval_id=approval.id if approval else None,
    )
    db.add(version)

    # Update prompt's updated_at
    prompt.updated_at = datetime.now(UTC)

    await db.flush()
    await db.commit()
    await db.refresh(version)
    log.info(
        "prompt_version_created",
        workspace_id=str(workspace.id),
        name=name,
        version=new_version_num,
        environment=body.environment,
    )
    if approval is not None:
        await emit_audit_event(
            db,
            workspace.id,
            "prompt.version_production",
            target_type="prompt",
            target_id=name,
            after={"version": new_version_num, "approval_id": str(approval.id)},
        )
    return VersionResponse.model_validate(version)


# ── GET /prompts/{name}/versions ───────────────────────────────────────────────


@router.get("/{name}/versions", response_model=VersionList)
async def list_versions(
    name: str,
    workspace: WorkspaceDep,
    db: DbDep,
    environment: Annotated[str | None, Query()] = None,
) -> VersionList:
    """List all versions of a prompt, newest first."""
    prompt = await _get_prompt_or_404(name, workspace.id, db)

    stmt = (
        select(PromptVersion)
        .where(PromptVersion.prompt_id == prompt.id)
        .order_by(PromptVersion.version.desc())
    )
    if environment is not None:
        stmt = stmt.where(PromptVersion.environment == environment)

    result = await db.execute(stmt)
    items = result.scalars().all()
    return VersionList(items=[VersionResponse.model_validate(v) for v in items])


# ── GET /prompts/{name}/latest ─────────────────────────────────────────────────


@router.get("/{name}/latest", response_model=VersionResponse)
async def get_latest_version(
    name: str,
    workspace: WorkspaceDep,
    db: DbDep,
    environment: Annotated[str, Query()] = "production",
) -> VersionResponse:
    """Get the latest version of a prompt for the given environment (SDK pull endpoint)."""
    prompt = await _get_prompt_or_404(name, workspace.id, db)

    result = await db.execute(
        select(PromptVersion)
        .where(
            PromptVersion.prompt_id == prompt.id,
            PromptVersion.environment == environment,
        )
        .order_by(PromptVersion.version.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(
            status_code=404,
            detail=f"No version found for prompt '{name}' in environment '{environment}'",
        )
    return VersionResponse.model_validate(version)


# ── GET /prompts/{name}/versions/{v} ──────────────────────────────────────────


@router.get("/{name}/versions/{v}", response_model=VersionResponse)
async def get_version(
    name: str,
    v: int,
    workspace: WorkspaceDep,
    db: DbDep,
) -> VersionResponse:
    """Get a specific version of a prompt."""
    prompt = await _get_prompt_or_404(name, workspace.id, db)

    result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.prompt_id == prompt.id,
            PromptVersion.version == v,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {v} not found for prompt '{name}'",
        )
    return VersionResponse.model_validate(version)


# ── POST /prompts/{name}/promote ───────────────────────────────────────────────


@router.post(
    "/{name}/promote",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer)],
)
async def promote_version(
    name: str,
    body: PromoteRequest,
    workspace: WorkspaceDep,
    db: DbDep,
    approval_id: Annotated[uuid.UUID | None, Query()] = None,
) -> VersionResponse:
    """
    Promote the latest version from source_environment to target_environment.

    When target_environment is 'production', an approved ``prompt_promote``
    approval for this prompt is required (``POST /prompts/{name}/promotion-requests``
    or ``POST /approvals``); pass its id in the body or as ``?approval_id=``. If the
    prompt has a score gate, the source version must meet it.
    """
    prompt = await _get_prompt_or_404(name, workspace.id, db)
    approval = None
    if body.target_environment == "production":
        approval = await _require_production_approval(
            db, workspace.id, name, body.approval_id or approval_id
        )

    # Find latest version in source environment
    src_result = await db.execute(
        select(PromptVersion)
        .where(
            PromptVersion.prompt_id == prompt.id,
            PromptVersion.environment == body.source_environment,
        )
        .order_by(PromptVersion.version.desc())
        .limit(1)
    )
    src_version = src_result.scalar_one_or_none()
    if src_version is None:
        raise HTTPException(
            status_code=404,
            detail=f"No version found in '{body.source_environment}' environment for prompt '{name}'",
        )
    if approval is not None:
        pinned = (approval.request or {}).get("version")
        if pinned is not None and int(pinned) != src_version.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Approval covers v{pinned}, but the latest "
                    f"{body.source_environment} version is v{src_version.version}"
                ),
            )
        score = await _version_score(db, workspace.id, prompt, src_version.version)
        if score.passes_gate is False:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Score gate: v{src_version.version} scores "
                    f"{'n/a' if score.score is None else round(score.score, 4)} "
                    f"(source: {score.source or 'none'}), below the "
                    f"{prompt.promotion_min_score} required for production. Run an "
                    "experiment on this version or lower the gate."
                ),
            )

    # Auto-increment version for the target
    max_result = await db.execute(
        select(func.max(PromptVersion.version)).where(PromptVersion.prompt_id == prompt.id)
    )
    max_version = max_result.scalar() or 0
    new_version_num = max_version + 1

    promoted = PromptVersion(
        prompt_id=prompt.id,
        version=new_version_num,
        content=src_version.content,
        variables=src_version.variables,
        commit_message=body.commit_message
        or f"Promoted from {body.source_environment} v{src_version.version}",
        environment=body.target_environment,
        model_hint=src_version.model_hint,
        approval_id=approval.id if approval else None,
    )
    db.add(promoted)
    prompt.updated_at = datetime.now(UTC)

    await db.flush()
    await db.commit()
    await db.refresh(promoted)
    log.info(
        "prompt_promoted",
        workspace_id=str(workspace.id),
        name=name,
        from_env=body.source_environment,
        to_env=body.target_environment,
        new_version=new_version_num,
    )
    await emit_audit_event(
        db,
        workspace.id,
        "prompt.promoted",
        target_type="prompt",
        target_id=name,
        after={
            "from_env": body.source_environment,
            "to_env": body.target_environment,
            "version": new_version_num,
            "source_version": src_version.version,
            "approval_id": str(approval.id) if approval else None,
        },
    )
    return VersionResponse.model_validate(promoted)


# ── GET /prompts/{name}/metrics ────────────────────────────────────────────────


@router.get("/{name}/metrics", response_model=PromptMetrics)
async def get_prompt_metrics(
    name: str,
    workspace: WorkspaceDep,
    db: DbDep,
) -> PromptMetrics:
    """Per-version run count, avg cost, and avg quality score.

    Joins with agent_runs using the deployment_version convention:
    deployment_version = "{prompt_name}:{version_number}"
    """
    prompt = await _get_prompt_or_404(name, workspace.id, db)

    # Get all versions
    versions_result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.prompt_id == prompt.id)
        .order_by(PromptVersion.version.desc())
    )
    versions = versions_result.scalars().all()

    items: list[VersionMetrics] = []
    for v in versions:
        deployment_version_key = f"{name}:{v.version}"

        # Run count + avg cost
        run_result = await db.execute(
            select(
                func.count(AgentRun.id).label("run_count"),
                func.avg(AgentRun.total_cost_usd).label("avg_cost"),
            ).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.deployment_version == deployment_version_key,
            )
        )
        run_row = run_result.one()

        # Avg score
        score_result = await db.execute(
            select(func.avg(ScoreEvent.value).label("avg_score")).where(
                ScoreEvent.workspace_id == workspace.id,
                ScoreEvent.run_id.in_(
                    select(AgentRun.id).where(
                        AgentRun.workspace_id == workspace.id,
                        AgentRun.deployment_version == deployment_version_key,
                    )
                ),
            )
        )
        avg_score = score_result.scalar()

        items.append(
            VersionMetrics(
                version=v.version,
                environment=v.environment,
                run_count=int(run_row.run_count or 0),
                avg_cost_usd=float(run_row.avg_cost) if run_row.avg_cost is not None else None,
                avg_score=float(avg_score) if avg_score is not None else None,
                commit_message=v.commit_message,
                created_at=v.created_at,
            )
        )

    return PromptMetrics(items=items)


# ── PUT /prompts/{name}/versions/{v} — edit content (auto-bumps version) ───────


@router.put(
    "/{name}/versions/{v}",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer)],
)
async def edit_version(
    name: str,
    v: int,
    body: VersionCreate,
    workspace: WorkspaceDep,
    db: DbDep,
    approval_id: Annotated[uuid.UUID | None, Query()] = None,
) -> VersionResponse:
    """
    Edit a version's content. Creates a new version (auto-bump) — versions are immutable.
    The new version lands in ``body.environment`` (default ``dev``). An edit never
    inherits ``production``: writing to production needs an approval, like create.
    """
    prompt = await _get_prompt_or_404(name, workspace.id, db)

    # Load source version to inherit defaults
    src_result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.prompt_id == prompt.id,
            PromptVersion.version == v,
        )
    )
    src = src_result.scalar_one_or_none()
    if src is None:
        raise HTTPException(status_code=404, detail=f"Version {v} not found for prompt '{name}'")

    approval = None
    if body.environment == "production":
        approval = await _require_production_approval(
            db, workspace.id, name, body.approval_id or approval_id
        )

    max_result = await db.execute(
        select(func.max(PromptVersion.version)).where(PromptVersion.prompt_id == prompt.id)
    )
    new_version_num = (max_result.scalar() or 0) + 1

    new_v = PromptVersion(
        prompt_id=prompt.id,
        version=new_version_num,
        content=body.content,
        variables=body.variables if body.variables else src.variables,
        commit_message=body.commit_message or f"Edit of v{v}",
        environment=body.environment,
        model_hint=body.model_hint if body.model_hint is not None else src.model_hint,
        approval_id=approval.id if approval else None,
    )
    db.add(new_v)
    prompt.updated_at = datetime.now(UTC)
    await db.flush()
    await db.commit()
    await db.refresh(new_v)
    log.info(
        "prompt_version_edited",
        workspace_id=str(workspace.id),
        name=name,
        source_version=v,
        new_version=new_version_num,
    )
    return VersionResponse.model_validate(new_v)


# ── Promotion requests (approval flow in the UI, review B-03) ──────────────────


def _promotion_from(approval: Approval, used: dict[uuid.UUID, int]) -> PromotionApproval:
    request = approval.request or {}
    version = request.get("version")
    return PromotionApproval(
        id=approval.id,
        status=approval.status,
        source_environment=request.get("source_environment"),
        version=int(version) if version is not None else None,
        requested_by=approval.requested_by,
        decided_by=approval.decided_by,
        decided_at=approval.decided_at,
        decision_note=approval.decision_note,
        used_by_version=used.get(approval.id),
        created_at=approval.created_at,
    )


@router.post(
    "/{name}/promotion-requests",
    response_model=PromotionApproval,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer)],
)
async def request_promotion(
    name: str,
    body: PromotionRequestCreate,
    workspace: WorkspaceDep,
    api_key: ApiKeyDep,
    db: DbDep,
) -> PromotionApproval:
    """Create a ``prompt_promote`` approval for this prompt (goes through the normal
    approvals queue, including auto-approval policies and notifications)."""
    prompt = await _get_prompt_or_404(name, workspace.id, db)
    version = body.version
    if version is None:
        version = (
            await db.execute(
                select(func.max(PromptVersion.version)).where(
                    PromptVersion.prompt_id == prompt.id,
                    PromptVersion.environment == body.source_environment,
                )
            )
        ).scalar()
    if version is None:
        raise HTTPException(
            status_code=404,
            detail=f"No version in '{body.source_environment}' to promote for prompt '{name}'",
        )
    created = await create_approval(
        ApprovalCreate(
            request_type="prompt_promote",
            request={
                "prompt_name": name,
                "version": int(version),
                "source_environment": body.source_environment,
                "environment": "production",
            },
            reason=body.reason,
        ),
        workspace,
        api_key,
        db,
    )
    approval = await db.get(Approval, created.id)
    if approval is None:  # pragma: no cover - just created
        raise HTTPException(status_code=500, detail="Approval was not stored")
    return _promotion_from(approval, {})


@router.get("/{name}/promotion-requests", response_model=PromotionApprovalList)
async def list_promotion_requests(
    name: str,
    workspace: WorkspaceDep,
    db: DbDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> PromotionApprovalList:
    """Approvals for promoting this prompt, newest first, with the version each one
    was used for (an approval authorises one production version)."""
    await _get_prompt_or_404(name, workspace.id, db)
    stmt = select(Approval).where(
        Approval.workspace_id == workspace.id,
        Approval.request_type == "prompt_promote",
        or_(
            Approval.request["prompt_name"].astext == name,
            Approval.request["prompt"].astext == name,
        ),
    )
    if status_filter:
        stmt = stmt.where(Approval.status == status_filter)
    approvals = list(
        (await db.execute(stmt.order_by(Approval.created_at.desc()).limit(100))).scalars().all()
    )
    used: dict[uuid.UUID, int] = {}
    ids = [a.id for a in approvals]
    if ids:
        rows = await db.execute(
            select(PromptVersion.approval_id, PromptVersion.version).where(
                PromptVersion.approval_id.in_(ids)
            )
        )
        used = {aid: ver for aid, ver in rows.all() if aid is not None}
    return PromotionApprovalList(items=[_promotion_from(a, used) for a in approvals])


# ── Score gate + diff (ENH) ────────────────────────────────────────────────────


@router.get("/{name}/versions/{v}/score", response_model=VersionScore)
async def get_version_score(
    name: str,
    v: int,
    workspace: WorkspaceDep,
    db: DbDep,
) -> VersionScore:
    """The score the promotion gate uses for this version, and whether it passes."""
    prompt = await _get_prompt_or_404(name, workspace.id, db)
    exists = (
        await db.execute(
            select(PromptVersion.id).where(
                PromptVersion.prompt_id == prompt.id, PromptVersion.version == v
            )
        )
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail=f"Version {v} not found for prompt '{name}'")
    return await _version_score(db, workspace.id, prompt, v)


def build_diff(old: str, new: str) -> tuple[list[DiffLine], int, int]:
    """Line diff between two prompt bodies (unified, 3 lines of context)."""
    lines: list[DiffLine] = []
    added = removed = 0
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    for group in matcher.get_grouped_opcodes(3):
        first, last = group[0], group[-1]
        lines.append(
            DiffLine(
                kind="hunk",
                text=f"@@ -{first[1] + 1},{last[2] - first[1]} +{first[3] + 1},{last[4] - first[3]} @@",
            )
        )
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                for k in range(i2 - i1):
                    lines.append(
                        DiffLine(
                            kind="context",
                            text=old_lines[i1 + k],
                            old_line=i1 + k + 1,
                            new_line=j1 + k + 1,
                        )
                    )
                continue
            for k in range(i1, i2):
                removed += 1
                lines.append(DiffLine(kind="remove", text=old_lines[k], old_line=k + 1))
            for k in range(j1, j2):
                added += 1
                lines.append(DiffLine(kind="add", text=new_lines[k], new_line=k + 1))
    return lines, added, removed


@router.get("/{name}/diff", response_model=PromptDiff)
async def diff_versions(
    name: str,
    workspace: WorkspaceDep,
    db: DbDep,
    from_version: Annotated[int, Query(alias="from", ge=1)],
    to_version: Annotated[int, Query(alias="to", ge=1)],
) -> PromptDiff:
    """Line-by-line diff between two versions of a prompt."""
    prompt = await _get_prompt_or_404(name, workspace.id, db)
    rows = (
        (
            await db.execute(
                select(PromptVersion).where(
                    PromptVersion.prompt_id == prompt.id,
                    PromptVersion.version.in_([from_version, to_version]),
                )
            )
        )
        .scalars()
        .all()
    )
    by_version = {r.version: r for r in rows}
    for wanted in (from_version, to_version):
        if wanted not in by_version:
            raise HTTPException(
                status_code=404, detail=f"Version {wanted} not found for prompt '{name}'"
            )
    old, new = by_version[from_version], by_version[to_version]
    lines, added, removed = build_diff(old.content, new.content)
    return PromptDiff(
        name=name,
        from_version=from_version,
        to_version=to_version,
        from_environment=old.environment,
        to_environment=new.environment,
        added=added,
        removed=removed,
        lines=lines,
        model_hint_changed=old.model_hint != new.model_hint,
        variables_changed=(old.variables or []) != (new.variables or []),
    )
