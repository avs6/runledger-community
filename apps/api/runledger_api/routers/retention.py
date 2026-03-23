"""
Data Retention & Deletion Policy API.

Prefix: /retention
Auth: Bearer API key (workspace-admin only)

Endpoints
---------
POST   /retention/policies            Create a retention policy
GET    /retention/policies            List retention policies
GET    /retention/policies/{id}       Get a single policy
PUT    /retention/policies/{id}       Update a policy (max_age_days, is_active, scope_value)
DELETE /retention/policies/{id}       Delete a policy
POST   /retention/purge               Immediate ad-hoc purge (supports dry_run)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_workspace_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.retention import RetentionPolicy
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.retention import (
    PurgeRequest,
    PurgeResult,
    RetentionPolicyCreate,
    RetentionPolicyList,
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.retention import purge_resource

router = APIRouter(
    prefix="/retention",
    tags=["retention"],
    dependencies=[Depends(management_rate_limit)],
)
log = structlog.get_logger()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[tuple, Depends(require_workspace_admin)]


# ── POST /retention/policies ──────────────────────────────────────────────────


@router.post(
    "/policies", response_model=RetentionPolicyResponse, status_code=status.HTTP_201_CREATED
)
async def create_retention_policy(
    body: RetentionPolicyCreate,
    auth: AdminDep,
    db: DbDep,
) -> RetentionPolicyResponse:
    """Create a new data retention policy for this workspace."""
    workspace: Workspace = auth[0]

    policy = RetentionPolicy(
        workspace_id=workspace.id,
        resource_type=body.resource_type,
        action=body.action,
        scope=body.scope,
        scope_value=body.scope_value,
        max_age_days=body.max_age_days,
        is_active=body.is_active,
    )
    db.add(policy)
    await db.flush()
    await db.commit()
    await db.refresh(policy)

    log.info(
        "retention_policy_created",
        policy_id=str(policy.id),
        workspace_id=str(workspace.id),
        resource_type=policy.resource_type,
        action=policy.action,
    )
    await emit_audit_event(
        db,
        workspace.id,
        "retention_policy.created",
        target_type="retention_policy",
        target_id=str(policy.id),
        after={
            "resource_type": policy.resource_type,
            "action": policy.action,
            "scope": policy.scope,
        },
    )
    await db.commit()

    return RetentionPolicyResponse.model_validate(policy)


# ── GET /retention/policies ───────────────────────────────────────────────────


@router.get("/policies", response_model=RetentionPolicyList)
async def list_retention_policies(
    auth: AdminDep,
    db: DbDep,
    resource_type: Annotated[str | None, Query()] = None,
    include_inactive: Annotated[bool, Query()] = False,
) -> RetentionPolicyList:
    """List retention policies for this workspace."""
    workspace: Workspace = auth[0]

    stmt = select(RetentionPolicy).where(RetentionPolicy.workspace_id == workspace.id)
    if resource_type:
        stmt = stmt.where(RetentionPolicy.resource_type == resource_type)
    if not include_inactive:
        stmt = stmt.where(RetentionPolicy.is_active.is_(True))
    stmt = stmt.order_by(RetentionPolicy.created_at.desc())

    result = await db.execute(stmt)
    policies = list(result.scalars().all())

    return RetentionPolicyList(
        items=[RetentionPolicyResponse.model_validate(p) for p in policies],
        total=len(policies),
    )


# ── GET /retention/policies/{id} ──────────────────────────────────────────────


@router.get("/policies/{policy_id}", response_model=RetentionPolicyResponse)
async def get_retention_policy(
    policy_id: uuid.UUID,
    auth: AdminDep,
    db: DbDep,
) -> RetentionPolicyResponse:
    workspace: Workspace = auth[0]

    result = await db.execute(
        select(RetentionPolicy).where(
            RetentionPolicy.id == policy_id,
            RetentionPolicy.workspace_id == workspace.id,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Retention policy not found"
        )

    return RetentionPolicyResponse.model_validate(policy)


# ── PUT /retention/policies/{id} ──────────────────────────────────────────────


@router.put("/policies/{policy_id}", response_model=RetentionPolicyResponse)
async def update_retention_policy(
    policy_id: uuid.UUID,
    body: RetentionPolicyUpdate,
    auth: AdminDep,
    db: DbDep,
) -> RetentionPolicyResponse:
    workspace: Workspace = auth[0]

    result = await db.execute(
        select(RetentionPolicy).where(
            RetentionPolicy.id == policy_id,
            RetentionPolicy.workspace_id == workspace.id,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Retention policy not found"
        )

    before = {"max_age_days": policy.max_age_days, "is_active": policy.is_active}

    if body.max_age_days is not None:
        policy.max_age_days = body.max_age_days
    if body.is_active is not None:
        policy.is_active = body.is_active
    if body.scope_value is not None:
        policy.scope_value = body.scope_value

    await db.commit()
    await db.refresh(policy)

    await emit_audit_event(
        db,
        workspace.id,
        "retention_policy.updated",
        target_type="retention_policy",
        target_id=str(policy_id),
        before=before,
        after={"max_age_days": policy.max_age_days, "is_active": policy.is_active},
    )
    await db.commit()

    return RetentionPolicyResponse.model_validate(policy)


# ── DELETE /retention/policies/{id} ───────────────────────────────────────────


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_retention_policy(
    policy_id: uuid.UUID,
    auth: AdminDep,
    db: DbDep,
) -> None:
    workspace: Workspace = auth[0]

    result = await db.execute(
        select(RetentionPolicy).where(
            RetentionPolicy.id == policy_id,
            RetentionPolicy.workspace_id == workspace.id,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Retention policy not found"
        )

    await emit_audit_event(
        db,
        workspace.id,
        "retention_policy.deleted",
        target_type="retention_policy",
        target_id=str(policy_id),
        before={
            "resource_type": policy.resource_type,
            "action": policy.action,
            "scope": policy.scope,
        },
    )
    await db.delete(policy)
    await db.commit()

    log.info("retention_policy_deleted", policy_id=str(policy_id), workspace_id=str(workspace.id))


# ── POST /retention/purge ─────────────────────────────────────────────────────


@router.post("/purge", response_model=PurgeResult)
async def immediate_purge(
    body: PurgeRequest,
    auth: AdminDep,
    db: DbDep,
) -> PurgeResult:
    """
    Execute an immediate purge (or dry-run count).

    Provide either `policy_id` to run a saved policy, or explicit
    resource_type / action / scope fields for a one-off purge.
    """
    workspace: Workspace = auth[0]

    # Resolve params: from policy or from request body directly
    if body.policy_id is not None:
        pol_result = await db.execute(
            select(RetentionPolicy).where(
                RetentionPolicy.id == body.policy_id,
                RetentionPolicy.workspace_id == workspace.id,
            )
        )
        policy = pol_result.scalar_one_or_none()
        if policy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Retention policy not found"
            )

        resource_type = policy.resource_type
        action = policy.action
        scope = policy.scope
        scope_value = policy.scope_value
        max_age_days = policy.max_age_days
    else:
        if not body.resource_type or not body.action:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide either policy_id or both resource_type and action",
            )
        resource_type = body.resource_type
        action = body.action
        scope = body.scope
        scope_value = body.scope_value
        max_age_days = body.max_age_days
        policy = None

    try:
        affected_rows, cutoff = await purge_resource(
            db,
            workspace_id=workspace.id,
            resource_type=resource_type,
            action=action,
            scope=scope,
            scope_value=scope_value,
            max_age_days=max_age_days,
            dry_run=body.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    # Update policy stats on live run
    if policy is not None and not body.dry_run:
        policy.last_run_at = datetime.now(UTC)
        policy.last_purged_count = affected_rows
        await db.commit()

    if not body.dry_run:
        await emit_audit_event(
            db,
            workspace.id,
            "retention.purge",
            target_type="retention_policy",
            target_id=str(policy.id) if policy else None,
            after={
                "resource_type": resource_type,
                "action": action,
                "scope": scope,
                "affected_rows": affected_rows,
                "dry_run": False,
            },
        )
        await db.commit()

    log.info(
        "retention_purge_executed",
        workspace_id=str(workspace.id),
        resource_type=resource_type,
        action=action,
        scope=scope,
        dry_run=body.dry_run,
        affected_rows=affected_rows,
    )

    return PurgeResult(
        resource_type=resource_type,
        action=action,
        scope=scope,
        scope_value=scope_value,
        affected_rows=affected_rows,
        dry_run=body.dry_run,
        cutoff=cutoff,
    )
