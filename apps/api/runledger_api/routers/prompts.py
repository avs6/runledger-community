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
from runledger_api.services.audit import emit_audit_event
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.routers.approvals import validate_approved
from runledger_api.models.events import AgentRun
from runledger_api.models.prompts import Prompt, PromptVersion
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import Workspace
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
        select(Prompt).where(
            Prompt.workspace_id == workspace.id, Prompt.name == body.name
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409, detail=f"Prompt '{body.name}' already exists"
        )

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
        select(Prompt)
        .where(Prompt.workspace_id == workspace.id)
        .order_by(Prompt.created_at.desc())
    )
    items = result.scalars().all()
    return PromptList(items=[PromptResponse.model_validate(p) for p in items])


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
        select(func.max(PromptVersion.version)).where(
            PromptVersion.prompt_id == prompt.id
        )
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
        select(func.max(PromptVersion.version)).where(
            PromptVersion.prompt_id == prompt.id
        )
    )
    max_version = max_result.scalar() or 0
    new_version_num = max_version + 1

    promoted = PromptVersion(
        prompt_id=prompt.id,
        version=new_version_num,
        content=src_version.content,
        variables=src_version.variables,
        commit_message=body.commit_message or f"Promoted from {body.source_environment} v{src_version.version}",
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
        db, workspace.id, "prompt.promoted",
        target_type="prompt", target_id=name,
        after={"from_env": body.source_environment, "to_env": body.target_environment, "version": new_version_num},
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
