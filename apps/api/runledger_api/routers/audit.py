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
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
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
AdminDep = Annotated[tuple[Any, ...], Depends(require_workspace_admin)]


@router.get("/events", response_model=AuditEventList)
async def list_audit_events(
    auth: AdminDep,
    db: DbDep,
    action: str | None = Query(None, description="Filter by action prefix, e.g. 'budget'"),
    actor_user_id: uuid.UUID | None = Query(None),
    target_type: str | None = Query(None),
    target_id: str | None = Query(None),
    access_group_id: uuid.UUID | None = Query(None),
    api_key_prefix: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditEventList:
    """Return paginated audit events for this workspace, newest first."""
    ws: Workspace = auth[0]
    base = select(AuditEvent).where(AuditEvent.workspace_id == ws.id)

    if action:
        base = base.where(AuditEvent.action.ilike(f"{action}%"))
    if actor_user_id:
        base = base.where(AuditEvent.actor_user_id == actor_user_id)
    if target_type:
        base = base.where(AuditEvent.target_type == target_type)
    if target_id:
        base = base.where(AuditEvent.target_id == target_id)
    if api_key_prefix:
        base = base.where(AuditEvent.actor_api_key_prefix == api_key_prefix)
    if access_group_id:
        from runledger_api.models.access_groups import AccessGroupMember

        member_ids_result = await db.execute(
            select(AccessGroupMember.user_id).where(AccessGroupMember.group_id == access_group_id)
        )
        member_ids = member_ids_result.scalars().all()
        if member_ids:
            base = base.where(AuditEvent.actor_user_id.in_(member_ids))
        else:
            base = base.where(False)

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
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


@router.get("/events/export")
async def export_audit_events(
    auth: AdminDep,
    db: DbDep,
    action: str | None = Query(None),
    target_type: str | None = Query(None),
    actor_user_id: uuid.UUID | None = Query(None),
    access_group_id: uuid.UUID | None = Query(None),
    api_key_prefix: str | None = Query(None),
    format: str = Query("csv", pattern="^(csv|json)$"),
) -> StreamingResponse:
    """Export audit events as CSV or JSON download."""
    ws: Workspace = auth[0]
    base = select(AuditEvent).where(AuditEvent.workspace_id == ws.id)
    if action:
        base = base.where(AuditEvent.action.ilike(f"{action}%"))
    if target_type:
        base = base.where(AuditEvent.target_type == target_type)
    if actor_user_id:
        base = base.where(AuditEvent.actor_user_id == actor_user_id)
    if api_key_prefix:
        base = base.where(AuditEvent.actor_api_key_prefix == api_key_prefix)
    if access_group_id:
        from runledger_api.models.access_groups import AccessGroupMember

        member_ids_result = await db.execute(
            select(AccessGroupMember.user_id).where(AccessGroupMember.group_id == access_group_id)
        )
        member_ids = member_ids_result.scalars().all()
        if member_ids:
            base = base.where(AuditEvent.actor_user_id.in_(member_ids))
        else:
            base = base.where(False)

    result = await db.execute(base.order_by(AuditEvent.created_at.desc()).limit(5000))
    items = result.scalars().all()

    if format == "json":
        import json

        rows = [AuditEventResponse.model_validate(e).model_dump(mode="json") for e in items]
        body = json.dumps(rows, indent=2, default=str)
        return StreamingResponse(
            iter([body]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_events.json"},
        )

    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "action", "actor_user_id", "target_type", "target_id", "details", "created_at"]
    )
    for e in items:
        writer.writerow(
            [
                str(e.id),
                e.action,
                str(e.actor_user_id) if e.actor_user_id else "",
                e.target_type or "",
                e.target_id or "",
                str({"before": e.before, "after": e.after}) if e.before or e.after else "",
                str(e.created_at),
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_events.csv"},
    )


@router.get("/events/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: uuid.UUID,
    auth: AdminDep,
    db: DbDep,
) -> AuditEventResponse:
    ws: Workspace = auth[0]
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
