"""
Audit log endpoints.

Prefix: /audit
Auth: Bearer API key (workspace admins, org admins/managers and org auditors)

Endpoints
---------
GET  /audit/events          Paginated audit log with filters (X-Total-Count)
GET  /audit/events/export   CSV / JSON export with the same filters
GET  /audit/events/{id}     Single event detail
GET  /audit/actors          Distinct actors seen in this workspace (filter options)
GET  /audit/verify          Recompute this workspace's hash chain (review S-16)

Filters shared by list and export: ``action`` (prefix), ``actor`` (email/label
substring or a user id), ``actor_user_id``, ``actor_type``, ``api_key_prefix``,
``access_group_id`` (members of an access group), ``target_type``, ``target_id``,
``from`` / ``to`` (ISO timestamps).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_audit_access
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.audit import AuditEvent
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.audit import (
    AuditActor,
    AuditActorList,
    AuditChainVerification,
    AuditEventList,
    AuditEventResponse,
)
from runledger_api.services.audit import chain_key_for, verify_chain

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(management_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
# Workspace admins, org admins/managers and org auditors read the audit trail.
AdminDep = Annotated[tuple[Any, ...], Depends(require_audit_access)]


class AuditFilters:
    """Query parameters shared by list and export."""

    def __init__(
        self,
        action: str | None = Query(None, description="Action prefix, e.g. 'budget' or 'secret'"),
        actor: str | None = Query(None, description="Actor email/label substring, or a user id"),
        actor_user_id: uuid.UUID | None = Query(None),
        actor_type: str | None = Query(
            None, pattern="^(user|session|api_key|oidc|admin_secret|service|system)$"
        ),
        api_key_prefix: str | None = Query(None, max_length=24),
        access_group_id: uuid.UUID | None = Query(None),
        target_type: str | None = Query(None),
        target_id: str | None = Query(None),
        from_ts: datetime | None = Query(None, alias="from"),
        to_ts: datetime | None = Query(None, alias="to"),
    ) -> None:
        self.action = action
        self.actor = actor
        self.actor_user_id = actor_user_id
        self.actor_type = actor_type
        self.api_key_prefix = api_key_prefix
        self.access_group_id = access_group_id
        self.target_type = target_type
        self.target_id = target_id
        self.from_ts = from_ts
        self.to_ts = to_ts

    async def apply(self, db: AsyncSession, base: Select[Any]) -> Select[Any]:
        if self.action:
            base = base.where(AuditEvent.action.ilike(f"{self.action}%"))
        if self.actor_user_id:
            base = base.where(AuditEvent.actor_user_id == self.actor_user_id)
        if self.actor:
            term = self.actor.strip()
            try:
                base = base.where(AuditEvent.actor_user_id == uuid.UUID(term))
            except ValueError:
                like = f"%{term}%"
                base = base.where(
                    or_(
                        AuditEvent.actor_label.ilike(like),
                        AuditEvent.actor_api_key_prefix.ilike(like),
                    )
                )
        if self.actor_type:
            base = base.where(AuditEvent.actor_type == self.actor_type)
        if self.api_key_prefix:
            base = base.where(AuditEvent.actor_api_key_prefix == self.api_key_prefix)
        if self.target_type:
            base = base.where(AuditEvent.target_type == self.target_type)
        if self.target_id:
            base = base.where(AuditEvent.target_id == self.target_id)
        if self.from_ts:
            base = base.where(AuditEvent.created_at >= self.from_ts)
        if self.to_ts:
            base = base.where(AuditEvent.created_at <= self.to_ts)
        if self.access_group_id:
            from runledger_api.models.access_groups import AccessGroupMember  # noqa: PLC0415

            member_ids = (
                (
                    await db.execute(
                        select(AccessGroupMember.user_id).where(
                            AccessGroupMember.group_id == self.access_group_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            base = (
                base.where(AuditEvent.actor_user_id.in_(member_ids))
                if member_ids
                else base.where(False)
            )
        return base


FiltersDep = Annotated[AuditFilters, Depends()]


@router.get("/events", response_model=AuditEventList)
async def list_audit_events(
    auth: AdminDep,
    db: DbDep,
    filters: FiltersDep,
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditEventList:
    """Return paginated audit events for this workspace, newest first."""
    ws: Workspace = auth[0]
    base = await filters.apply(db, select(AuditEvent).where(AuditEvent.workspace_id == ws.id))

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    result = await db.execute(
        base.order_by(AuditEvent.created_at.desc(), AuditEvent.id).limit(limit).offset(offset)
    )
    items = result.scalars().all()
    response.headers["X-Total-Count"] = str(total)
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
    filters: FiltersDep,
    format: str = Query("csv", pattern="^(csv|json)$"),
) -> StreamingResponse:
    """Export audit events as CSV or JSON download (same filters as the list)."""
    ws: Workspace = auth[0]
    base = await filters.apply(db, select(AuditEvent).where(AuditEvent.workspace_id == ws.id))
    result = await db.execute(base.order_by(AuditEvent.created_at.desc()).limit(5000))
    items = result.scalars().all()

    if format == "json":
        import json  # noqa: PLC0415

        rows = [AuditEventResponse.model_validate(e).model_dump(mode="json") for e in items]
        body = json.dumps(rows, indent=2, default=str)
        return StreamingResponse(
            iter([body]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_events.json"},
        )

    import csv  # noqa: PLC0415
    import io  # noqa: PLC0415

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "seq",
            "action",
            "actor_type",
            "actor",
            "actor_user_id",
            "api_key_prefix",
            "target_type",
            "target_id",
            "details",
            "created_at",
            "hash",
        ]
    )
    for e in items:
        writer.writerow(
            [
                str(e.id),
                e.seq or "",
                e.action,
                e.actor_type or "",
                e.actor_label or "",
                str(e.actor_user_id) if e.actor_user_id else "",
                e.actor_api_key_prefix or "",
                e.target_type or "",
                e.target_id or "",
                str({"before": e.before, "after": e.after}) if e.before or e.after else "",
                str(e.created_at),
                e.hash or "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_events.csv"},
    )


@router.get("/actors", response_model=AuditActorList)
async def list_audit_actors(auth: AdminDep, db: DbDep) -> AuditActorList:
    """Distinct actors in this workspace's audit log, most active first."""
    ws: Workspace = auth[0]
    rows = await db.execute(
        select(
            AuditEvent.actor_type,
            AuditEvent.actor_label,
            AuditEvent.actor_user_id,
            AuditEvent.actor_api_key_prefix,
            func.count().label("events"),
            func.max(AuditEvent.created_at).label("last_seen"),
        )
        .where(AuditEvent.workspace_id == ws.id)
        .group_by(
            AuditEvent.actor_type,
            AuditEvent.actor_label,
            AuditEvent.actor_user_id,
            AuditEvent.actor_api_key_prefix,
        )
        .order_by(func.count().desc())
        .limit(200)
    )
    return AuditActorList(
        items=[
            AuditActor(
                actor_type=r.actor_type,
                actor_label=r.actor_label,
                actor_user_id=r.actor_user_id,
                actor_api_key_prefix=r.actor_api_key_prefix,
                events=int(r.events or 0),
                last_seen=r.last_seen,
            )
            for r in rows
        ]
    )


@router.get("/verify", response_model=AuditChainVerification)
async def verify_audit_chain(auth: AdminDep, db: DbDep) -> AuditChainVerification:
    """Recompute this workspace's audit hash chain and report the first broken link."""
    ws: Workspace = auth[0]
    result = await verify_chain(db, chain_key_for(ws.id, None))
    return AuditChainVerification(
        chain_key=result.chain_key,
        ok=result.ok,
        checked=result.checked,
        unchained=result.unchained,
        first_bad_seq=result.first_bad_seq,
        first_bad_event_id=result.first_bad_event_id,
        reason=result.reason,
        head_hash=result.head_hash,
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
