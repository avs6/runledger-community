"""
Ledger endpoints — tamper-evident daily snapshots.

Prefix: /ledger
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
GET  /ledger/snapshots              List workspace snapshots (limit 30)
POST /ledger/snapshots/generate     Seal yesterday's snapshot (immutable once sealed)
GET  /ledger/verify/{snapshot_date} Verify integrity of a snapshot
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_platform_admin
from runledger_api.core.pagination import PageDep, paginate
from runledger_api.models.ledger import LedgerSnapshot
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.ledger import (
    LedgerClosureSummary,
    LedgerSnapshotList,
    LedgerSnapshotResponse,
    LedgerVerifyResult,
)
from runledger_api.services.ledger import (
    get_ledger_closure_summary,
    seal_snapshot,
    verify_snapshot,
)
from runledger_api.services.ledger_anchor import anchor_snapshot

router = APIRouter(prefix="/ledger", tags=["ledger"])
log = structlog.get_logger()
DbDep = Annotated[AsyncSession, Depends(get_db)]
PlatformAdminDep = Annotated[tuple[Any, ...], Depends(require_platform_admin)]


def _snap_to_response(snap: LedgerSnapshot) -> LedgerSnapshotResponse:
    return LedgerSnapshotResponse(
        id=str(snap.id),
        workspace_id=str(snap.workspace_id),
        snapshot_date=snap.snapshot_date,
        total_cost_usd=snap.total_cost_usd,
        model_breakdown=snap.model_breakdown or {},
        call_count=snap.call_count,
        hash=snap.hash,
        key_id=str(snap.key_id),
        prev_hash=snap.prev_hash,
        entry_count=snap.entry_count,
        sealed_at=snap.sealed_at,
        anchor_uri=getattr(snap, "anchor_uri", None),
        anchored_at=getattr(snap, "anchored_at", None),
        anchor_locked=getattr(snap, "anchor_locked", None),
        created_at=snap.created_at,
    )


# ── GET /ledger/snapshots ─────────────────────────────────────────────────────


@router.get("/snapshots", response_model=LedgerSnapshotList)
async def list_snapshots(
    auth: PlatformAdminDep,
    db: DbDep,
    page: PageDep,
    response: Response,
) -> LedgerSnapshotList:
    workspace: Workspace = auth[0]
    snaps = await paginate(
        db,
        select(LedgerSnapshot)
        .where(LedgerSnapshot.workspace_id == workspace.id)
        .order_by(LedgerSnapshot.snapshot_date.desc(), LedgerSnapshot.id),
        page,
        response,
    )
    return LedgerSnapshotList(items=[_snap_to_response(s) for s in snaps])


@router.get("/closure-summary", response_model=LedgerClosureSummary)
async def get_closure_summary(
    auth: PlatformAdminDep,
    db: DbDep,
) -> LedgerClosureSummary:
    workspace: Workspace = auth[0]
    return await get_ledger_closure_summary(db, workspace.id)


# ── POST /ledger/snapshots/generate ──────────────────────────────────────────


@router.post("/snapshots/generate", response_model=LedgerSnapshotResponse)
async def generate_snapshot(
    auth: PlatformAdminDep,
    db: DbDep,
    response: Response,
    snapshot_date: date | None = None,
) -> LedgerSnapshotResponse:
    """Seal yesterday's (or ``snapshot_date``'s) snapshot.

    Sealed snapshots are immutable (review cd:M-02): if the day is already sealed the
    existing snapshot is returned with 200; a new seal returns 201.
    """
    workspace: Workspace = auth[0]
    day = snapshot_date or (datetime.now(UTC) - timedelta(days=1)).date()
    if day >= datetime.now(UTC).date():
        from fastapi import HTTPException, status  # noqa: PLC0415

        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Only past days can be sealed")
    snap, created = await seal_snapshot(db, workspace.id, day)
    await db.commit()
    # Anchor off-box right away when a backup target is configured (cd:M-02); the
    # daily worker retries anything left unanchored.
    if await anchor_snapshot(db, snap) == "anchored":
        await db.commit()
    await db.refresh(snap)
    response.status_code = 201 if created else 200
    return _snap_to_response(snap)


@router.post("/snapshots/{snapshot_date}/anchor", response_model=LedgerSnapshotResponse)
async def anchor_ledger_snapshot(
    snapshot_date: date,
    auth: PlatformAdminDep,
    db: DbDep,
) -> LedgerSnapshotResponse:
    """Write a sealed snapshot's hash to the workspace's backup bucket (Object Lock
    when the bucket supports it). 409 without a backup target, 502 if the write fails."""
    from fastapi import HTTPException, status  # noqa: PLC0415

    workspace: Workspace = auth[0]
    snap = (
        await db.execute(
            select(LedgerSnapshot).where(
                LedgerSnapshot.workspace_id == workspace.id,
                LedgerSnapshot.snapshot_date == snapshot_date,
            )
        )
    ).scalar_one_or_none()
    if snap is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No snapshot for that day")
    outcome = await anchor_snapshot(db, snap)
    if outcome == "no_target":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Configure a backup target (Settings → Backups) to anchor"
        )
    if outcome == "unsealed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Legacy snapshot without a seal")
    if outcome.startswith("failed"):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Anchor write {outcome}")
    await db.commit()
    await db.refresh(snap)
    return _snap_to_response(snap)


# ── GET /ledger/verify/{snapshot_date} ────────────────────────────────────────


@router.get("/verify/{snapshot_date}", response_model=LedgerVerifyResult)
async def verify_ledger_snapshot(
    snapshot_date: date,
    auth: PlatformAdminDep,
    db: DbDep,
) -> LedgerVerifyResult:
    workspace: Workspace = auth[0]
    return await verify_snapshot(db, workspace.id, snapshot_date)
