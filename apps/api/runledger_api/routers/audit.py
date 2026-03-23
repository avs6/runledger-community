"""
Audit log endpoints.

Prefix: /audit
Auth: Bearer API key (workspace-scoped; workspace-admin+ to read)

Endpoints
---------
GET  /audit/events          Paginated audit log with filters
GET  /audit/events/{id}     Single event detail
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.audit import AuditEvent
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.audit import AuditEventList, AuditEventResponse

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(management_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
WsDep = Annotated[Workspace, Depends(get_current_workspace)]
AdminDep = Annotated[Workspace, Depends(require_workspace_admin)]


@router.get("/events", response_model=AuditEventList)
async def list_audit_events(
    ws: AdminDep,
    db: DbDep,
    action: str | None = Query(None, description="Filter by action prefix, e.g. 'budget'"),
    actor_user_id: uuid.UUID | None = Query(None),
    target_type: str | None = Query(None),
    target_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditEventList:
    """Return paginated audit events for this workspace, newest first."""
    base = select(AuditEvent).where(AuditEvent.workspace_id == ws.id)

    if action:
        base = base.where(AuditEvent.action.ilike(f"{action}%"))
    if actor_user_id:
        base = base.where(AuditEvent.actor_user_id == actor_user_id)
    if target_type:
        base = base.where(AuditEvent.target_type == target_type)
    if target_id:
        base = base.where(AuditEvent.target_id == target_id)

    total_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        base.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
    )
    items = result.scalars().all()

    return AuditEventList(
        items=[AuditEventResponse.model_validate(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/events/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: uuid.UUID,
    ws: AdminDep,
    db: DbDep,
) -> AuditEventResponse:
    result = await db.execute(
        select(AuditEvent).where(
            AuditEvent.id == event_id,
            AuditEvent.workspace_id == ws.id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return AuditEventResponse.model_validate(event)
