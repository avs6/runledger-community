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
POST   /prompts/{name}/promote         Promote latest staging → production
GET    /prompts/{name}/metrics         Per-version cost + avg score + run count
"""

from __future__ import annotations

import base64
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.events import AgentRun
from runledger_api.models.prompts import Prompt, PromptVersion
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import Workspace
from runledger_api.routers.approvals import validate_approved
from runledger_api.models.eval_experiments import PromptGithubConfig
from runledger_api.schemas.eval_experiments import (
    GithubConfigCreate,
    GithubConfigResponse,
    GithubConfigUpdate,
    GithubSyncResult,
)
from runledger_api.schemas.prompts import (
    PromoteRequest,
    PromptCreate,
    PromptList,
    PromptMetrics,
    PromptResponse,
    VersionCreate,
    VersionList,
    VersionMetrics,
    VersionResponse,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.github_sync import pull_prompts_from_github, push_prompts_to_github

router = APIRouter(
    prefix="/prompts",
    tags=["prompts"],
    dependencies=[Depends(management_rate_limit)],
)
log = structlog.get_logger()

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

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


# ── POST /prompts ──────────────────────────────────────────────────────────────


@router.post("", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
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
) -> PromptList:
    """List all prompts for the workspace."""
    result = await db.execute(
        select(Prompt).where(Prompt.workspace_id == workspace.id).order_by(Prompt.created_at.desc())
    )
    items = result.scalars().all()
    return PromptList(items=[PromptResponse.model_validate(p) for p in items])


# ── GitHub sync endpoints (must come before /{name} to avoid route capture) ───


def _decrypt_token(token_enc: str | None) -> str | None:
    """Decrypt stored token or fall back to env var."""
    if token_enc:
        if token_enc.startswith("b64:"):
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


@router.post("/github-config", response_model=GithubConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_github_config(body: GithubConfigCreate, workspace: WorkspaceDep, db: DbDep) -> PromptGithubConfig:
    """Create GitHub sync config for this workspace."""
    existing = await db.execute(
        select(PromptGithubConfig).where(PromptGithubConfig.workspace_id == workspace.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="GitHub config already exists — use PUT to update")

    token_enc: str | None = None
    if body.token:
        token_enc = "b64:" + base64.b64encode(body.token.encode()).decode()

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


@router.put("/github-config", response_model=GithubConfigResponse)
async def update_github_config(body: GithubConfigUpdate, workspace: WorkspaceDep, db: DbDep) -> PromptGithubConfig:
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
        cfg.token_enc = "b64:" + base64.b64encode(body.token.encode()).decode()
    if body.auto_sync is not None:
        cfg.auto_sync = body.auto_sync
    cfg.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.post("/sync/push", response_model=GithubSyncResult)
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
            select(PromptVersion).where(PromptVersion.prompt_id == p.id).order_by(PromptVersion.version.asc())
        )
        versions = list(versions_result.scalars().all())
        prompt_dicts.append({
            "name": p.name, "description": p.description or "", "variables": [],
            "versions": [{"version": v.version, "content": v.content, "environment": v.environment,
                          "model_hint": v.model_hint, "commit_message": v.commit_message or ""} for v in versions],
        })

    sync_result = await push_prompts_to_github(token, cfg.repo, cfg.branch, cfg.path_prefix, prompt_dicts)
    cfg.last_sync_at = datetime.now(UTC)
    cfg.last_sync_status = "success" if not sync_result["errors"] else "partial"
    cfg.last_sync_message = f"Pushed {sync_result['pushed']} prompts" + (
        f"; errors: {'; '.join(sync_result['errors'][:3])}" if sync_result["errors"] else ""
    )
    await db.commit()
    log.info("github_sync_push", workspace_id=str(workspace.id), **sync_result)
    return GithubSyncResult(
        pushed=sync_result["pushed"], pulled=0, skipped=sync_result["skipped"],
        errors=sync_result["errors"], synced_at=cfg.last_sync_at,
    )


@router.post("/sync/pull", response_model=GithubSyncResult)
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

    pulled_prompts, errors = await pull_prompts_from_github(token, cfg.repo, cfg.branch, cfg.path_prefix)
    pulled = 0
    for pd in pulled_prompts:
        pr_result = await db.execute(
            select(Prompt).where(Prompt.workspace_id == workspace.id, Prompt.name == pd["name"])
        )
        prompt = pr_result.scalar_one_or_none()
        if not prompt:
            prompt = Prompt(workspace_id=workspace.id, name=pd["name"], description=pd.get("description"))
            db.add(prompt)
            await db.flush()
        max_r = await db.execute(
            select(func.max(PromptVersion.version)).where(PromptVersion.prompt_id == prompt.id)
        )
        current_max = max_r.scalar() or 0
        for pv in (pd.get("versions") or []):
            db.add(PromptVersion(
                prompt_id=prompt.id, version=current_max + 1, content=pv.get("content", ""),
                variables=[], commit_message=pv.get("commit_message") or "Pulled from GitHub",
                environment=pv.get("environment", "production"), model_hint=pv.get("model_hint"),
            ))
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
    return GithubSyncResult(pushed=0, pulled=pulled, skipped=0, errors=errors, synced_at=cfg.last_sync_at)


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


# ── DELETE /prompts/{name} ─────────────────────────────────────────────────────


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
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


# ── POST /prompts/{name}/versions ──────────────────────────────────────────────


@router.post(
    "/{name}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    name: str,
    body: VersionCreate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> VersionResponse:
    """Commit a new version of the prompt template."""
    prompt = await _get_prompt_or_404(name, workspace.id, db)

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
    approval is required. Pass ``?approval_id=<uuid>`` from ``POST /approvals``.
    """
    # Enforce approval gate for production promotes
    if body.target_environment == "production":
        if approval_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Promoting to production requires an approved governance approval. "
                    "Create one via POST /approvals with request_type='prompt_promote', "
                    "then pass ?approval_id=<id> once approved."
                ),
            )
        await validate_approved(db, workspace.id, approval_id, "prompt_promote")

    prompt = await _get_prompt_or_404(name, workspace.id, db)

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


@router.put("/{name}/versions/{v}", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def edit_version(
    name: str,
    v: int,
    body: VersionCreate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> VersionResponse:
    """
    Edit a version's content. Creates a new version (auto-bump) — versions are immutable.
    The new version inherits environment/model_hint from the source unless overridden in body.
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
        environment=body.environment if body.environment != "production" or src.environment == "production" else src.environment,
        model_hint=body.model_hint if body.model_hint is not None else src.model_hint,
    )
    db.add(new_v)
    prompt.updated_at = datetime.now(UTC)
    await db.flush()
    await db.commit()
    await db.refresh(new_v)
    log.info("prompt_version_edited", workspace_id=str(workspace.id), name=name, source_version=v, new_version=new_version_num)
    return VersionResponse.model_validate(new_v)
