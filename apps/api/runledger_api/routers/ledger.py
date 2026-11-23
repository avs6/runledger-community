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
    await db.refresh(snap)
    response.status_code = 201 if created else 200
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
