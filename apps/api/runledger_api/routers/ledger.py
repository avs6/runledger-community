"""
Ledger endpoints — tamper-evident daily snapshots.

Prefix: /ledger
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
GET  /ledger/snapshots              List workspace snapshots (limit 30)
POST /ledger/snapshots/generate     Trigger immediate snapshot for yesterday
GET  /ledger/verify/{snapshot_date} Verify integrity of a snapshot
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_platform_admin
from runledger_api.models.ledger import LedgerSnapshot
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.ledger import (
    LedgerClosureSummary,
    LedgerSnapshotList,
    LedgerSnapshotResponse,
    LedgerVerifyResult,
)
from runledger_api.services.ledger import (
    build_daily_snapshot,
    compute_snapshot_hash,
    get_ledger_closure_summary,
    get_or_create_active_key,
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
        created_at=snap.created_at,
    )


# ── GET /ledger/snapshots ─────────────────────────────────────────────────────


@router.get("/snapshots", response_model=LedgerSnapshotList)
async def list_snapshots(
    auth: PlatformAdminDep,
    db: DbDep,
) -> LedgerSnapshotList:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(LedgerSnapshot)
        .where(LedgerSnapshot.workspace_id == workspace.id)
        .order_by(LedgerSnapshot.snapshot_date.desc())
        .limit(30)
    )
    snaps = result.scalars().all()
    return LedgerSnapshotList(items=[_snap_to_response(s) for s in snaps])


@router.get("/closure-summary", response_model=LedgerClosureSummary)
async def get_closure_summary(
    auth: PlatformAdminDep,
    db: DbDep,
) -> LedgerClosureSummary:
    workspace: Workspace = auth[0]
    return await get_ledger_closure_summary(db, workspace.id)


# ── POST /ledger/snapshots/generate ──────────────────────────────────────────


@router.post("/snapshots/generate", response_model=LedgerSnapshotResponse, status_code=201)
async def generate_snapshot(
    auth: PlatformAdminDep,
    db: DbDep,
) -> LedgerSnapshotResponse:
    workspace: Workspace = auth[0]
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date()
    snapshot_data = await build_daily_snapshot(db, workspace.id, yesterday)
    key = await get_or_create_active_key(db, workspace.id)
    from runledger_api.services.ledger import _decrypt_key  # noqa: PLC0415

    snapshot_hash = compute_snapshot_hash(snapshot_data, _decrypt_key(key.key_value))

    total_cost = Decimal(snapshot_data["total_cost_usd"])
    call_count = snapshot_data["call_count"]
    model_breakdown = snapshot_data["model_breakdown"]

    # Check if snapshot already exists for this date
    existing_result = await db.execute(
        select(LedgerSnapshot).where(
            LedgerSnapshot.workspace_id == workspace.id,
            LedgerSnapshot.snapshot_date == yesterday,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        await db.execute(
            update(LedgerSnapshot)
            .where(LedgerSnapshot.id == existing.id)
            .values(
                total_cost_usd=total_cost,
                model_breakdown=model_breakdown,
                call_count=call_count,
                hash=snapshot_hash,
                key_id=key.id,
            )
        )
        await db.commit()
        await db.refresh(existing)
        return _snap_to_response(existing)

    snap = LedgerSnapshot(
        workspace_id=workspace.id,
        snapshot_date=yesterday,
        total_cost_usd=total_cost,
        model_breakdown=model_breakdown,
        call_count=call_count,
        hash=snapshot_hash,
        key_id=key.id,
    )
    db.add(snap)
    await db.flush()
    await db.commit()
    await db.refresh(snap)

    log.info(
        "ledger_snapshot_generated",
        workspace_id=str(workspace.id),
        snapshot_date=str(yesterday),
        hash=snapshot_hash[:16],
    )
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
