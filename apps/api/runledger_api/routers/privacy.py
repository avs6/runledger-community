"""
Privacy / capture policy endpoints.

Prefix: /privacy
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
GET /privacy/capture-policy   Current capture policy (404 if not set)
PUT /privacy/capture-policy   Upsert capture policy
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.models.ledger import CapturePolicy
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.privacy import CapturePolicyResponse, CapturePolicyUpsert

router = APIRouter(prefix="/privacy", tags=["privacy"])
log = structlog.get_logger()


def _policy_to_response(policy: CapturePolicy) -> CapturePolicyResponse:
    return CapturePolicyResponse(
        id=str(policy.id),
        workspace_id=str(policy.workspace_id),
        privacy_mode=policy.privacy_mode,
        sampled_rate=policy.sampled_rate,
        updated_at=policy.updated_at,
        created_at=policy.created_at,
    )


# ── GET /privacy/capture-policy ───────────────────────────────────────────────


@router.get("/capture-policy", response_model=CapturePolicyResponse)
async def get_capture_policy(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CapturePolicyResponse:
    result = await db.execute(
        select(CapturePolicy).where(CapturePolicy.workspace_id == workspace.id)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=404, detail="No capture policy set for this workspace")
    return _policy_to_response(policy)


# ── PUT /privacy/capture-policy ───────────────────────────────────────────────


@router.put("/capture-policy", response_model=CapturePolicyResponse)
async def upsert_capture_policy(
    body: CapturePolicyUpsert,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CapturePolicyResponse:
    result = await db.execute(
        select(CapturePolicy).where(CapturePolicy.workspace_id == workspace.id)
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        await db.execute(
            update(CapturePolicy)
            .where(CapturePolicy.id == existing.id)
            .values(
                privacy_mode=body.privacy_mode,
                sampled_rate=body.sampled_rate,
                updated_at=datetime.now(UTC),
            )
        )
        await db.commit()
        await db.refresh(existing)
        return _policy_to_response(existing)

    policy = CapturePolicy(
        workspace_id=workspace.id,
        privacy_mode=body.privacy_mode,
        sampled_rate=body.sampled_rate,
    )
    db.add(policy)
    await db.flush()
    await db.commit()
    await db.refresh(policy)

    log.info(
        "capture_policy_upserted",
        workspace_id=str(workspace.id),
        privacy_mode=body.privacy_mode,
    )
    return _policy_to_response(policy)
