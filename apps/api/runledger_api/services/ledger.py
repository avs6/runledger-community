"""
Ledger service — signing key management, daily snapshot build/verify.

All functions are pure async with no FastAPI dependencies.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import ProviderCall
from runledger_api.models.ledger import LedgerKey, LedgerSnapshot
from runledger_api.schemas.ledger import LedgerVerifyResult

log = structlog.get_logger()


# ── Key management ────────────────────────────────────────────────────────────


async def get_or_create_active_key(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> LedgerKey:
    """Return the active non-expired key for the workspace, or create one."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(LedgerKey)
        .where(
            LedgerKey.workspace_id == workspace_id,
            LedgerKey.active.is_(True),
            LedgerKey.expires_at > now,
        )
        .order_by(LedgerKey.created_at.desc())
        .limit(1)
    )
    key = result.scalar_one_or_none()
    if key is not None:
        return key

    # Create a new 30-day key
    new_key = LedgerKey(
        workspace_id=workspace_id,
        key_value=secrets.token_hex(32),
        active=True,
        expires_at=now + timedelta(days=30),
    )
    db.add(new_key)
    await db.flush()
    log.info("ledger_key_created", workspace_id=str(workspace_id), key_id=str(new_key.id))
    return new_key


# ── Snapshot build ────────────────────────────────────────────────────────────


async def build_daily_snapshot(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    snapshot_date: date,
) -> dict[str, Any]:
    """Query provider_calls for the given date and return a snapshot dict."""
    # Total cost + call count
    totals_result = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("total_cost"),
            func.count(ProviderCall.id).label("call_count"),
        ).where(
            ProviderCall.workspace_id == workspace_id,
            func.date(ProviderCall.created_at) == snapshot_date,
            ProviderCall.status == "success",
        )
    )
    totals_row = totals_result.one()
    total_cost: Decimal = totals_row.total_cost or Decimal(0)
    call_count: int = totals_row.call_count or 0

    # Per-model breakdown
    model_result = await db.execute(
        select(
            ProviderCall.model,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
        )
        .where(
            ProviderCall.workspace_id == workspace_id,
            func.date(ProviderCall.created_at) == snapshot_date,
            ProviderCall.status == "success",
        )
        .group_by(ProviderCall.model)
    )
    model_rows = model_result.all()
    model_breakdown = {row.model: str(row.cost) for row in model_rows if row.model}

    return {
        "workspace_id": str(workspace_id),
        "snapshot_date": str(snapshot_date),
        "total_cost_usd": str(total_cost),
        "call_count": call_count,
        "model_breakdown": model_breakdown,
    }


# ── Hash helpers ──────────────────────────────────────────────────────────────


def compute_snapshot_hash(snapshot_data: dict[str, Any], key_value: str) -> str:
    """Compute HMAC-SHA256 of the snapshot data using sign_snapshot."""
    from runledger_api.services.billing import sign_snapshot  # noqa: PLC0415

    return sign_snapshot(snapshot_data, key_value)


# ── Verify ────────────────────────────────────────────────────────────────────


async def verify_snapshot(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    snapshot_date: date,
) -> LedgerVerifyResult:
    """Re-build snapshot data, re-compute hash, compare with stored."""
    snap_result = await db.execute(
        select(LedgerSnapshot).where(
            LedgerSnapshot.workspace_id == workspace_id,
            LedgerSnapshot.snapshot_date == snapshot_date,
        )
    )
    snapshot = snap_result.scalar_one_or_none()

    if snapshot is None:
        return LedgerVerifyResult(
            snapshot_date=snapshot_date,
            status="not_found",
            stored_hash=None,
            computed_hash=None,
            match=False,
        )

    # Fetch the signing key
    key_result = await db.execute(select(LedgerKey).where(LedgerKey.id == snapshot.key_id))
    key = key_result.scalar_one_or_none()
    if key is None:
        return LedgerVerifyResult(
            snapshot_date=snapshot_date,
            status="tampered",
            stored_hash=snapshot.hash,
            computed_hash=None,
            match=False,
        )

    # Re-build the snapshot data and re-compute hash
    snapshot_data = await build_daily_snapshot(db, workspace_id, snapshot_date)
    computed = compute_snapshot_hash(snapshot_data, key.key_value)
    stored = snapshot.hash
    match = computed == stored

    log.info(
        "ledger_verify",
        workspace_id=str(workspace_id),
        snapshot_date=str(snapshot_date),
        match=match,
    )

    return LedgerVerifyResult(
        snapshot_date=snapshot_date,
        status="ok" if match else "tampered",
        stored_hash=stored,
        computed_hash=computed,
        match=match,
    )
