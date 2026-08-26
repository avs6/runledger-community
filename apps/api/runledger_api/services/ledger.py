"""
Ledger service — signing key management, daily snapshot build/verify.

All functions are pure async with no FastAPI dependencies.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.models.audit import AuditEvent
from runledger_api.models.backup_ops import BackupSnapshot
from runledger_api.models.billing import BillingPeriod
from runledger_api.models.events import ProviderCall
from runledger_api.models.ledger import LedgerKey, LedgerSnapshot
from runledger_api.schemas.ledger import (
    LedgerBackupEvidenceSummary,
    LedgerChargebackSummary,
    LedgerClosedPeriodSummary,
    LedgerClosureSummary,
    LedgerSnapshotResponse,
    LedgerVerificationSummary,
    LedgerVerifyResult,
)

log = structlog.get_logger()


def _get_fernet():
    master = settings.ledger_master_key
    if not master:
        return None
    from cryptography.fernet import Fernet

    if len(master) == 44 and master.endswith("="):
        return Fernet(master.encode())
    key = base64.urlsafe_b64encode(hashlib.sha256(master.encode()).digest())
    return Fernet(key)


def _encrypt_key(plaintext: str) -> str:
    f = _get_fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def _decrypt_key(stored: str) -> str:
    f = _get_fernet()
    if f is None:
        return stored
    try:
        return f.decrypt(stored.encode()).decode()
    except Exception:
        return stored


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

    # Create a new 30-day key (encrypted at rest when LEDGER_MASTER_KEY is set)
    raw = secrets.token_hex(32)
    new_key = LedgerKey(
        workspace_id=workspace_id,
        key_value=_encrypt_key(raw),
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
    computed = compute_snapshot_hash(snapshot_data, _decrypt_key(key.key_value))
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


async def get_ledger_closure_summary(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> LedgerClosureSummary:
    from runledger_api.services.billing import build_chargeback_report  # noqa: PLC0415

    generated_at = datetime.now(UTC)

    snapshots = (
        (
            await db.execute(
                select(LedgerSnapshot)
                .where(LedgerSnapshot.workspace_id == workspace_id)
                .order_by(LedgerSnapshot.snapshot_date.desc())
                .limit(12)
            )
        )
        .scalars()
        .all()
    )

    latest_snapshot_response = None
    latest_status: str | None = None
    ok_count = 0
    tampered_count = 0
    pending_count = 0

    for index, snap in enumerate(snapshots):
        result = await verify_snapshot(db, workspace_id, snap.snapshot_date)
        if index == 0:
            latest_status = result.status
            latest_snapshot_response = LedgerSnapshotResponse(
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
        if result.status == "ok":
            ok_count += 1
        elif result.status == "tampered":
            tampered_count += 1
        else:
            pending_count += 1

    latest_closed_period = (
        (
            await db.execute(
                select(BillingPeriod)
                .where(
                    BillingPeriod.workspace_id == workspace_id,
                    BillingPeriod.status == "closed",
                )
                .order_by(BillingPeriod.closed_at.desc(), BillingPeriod.period_end.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )

    latest_closed_period_summary = None
    if latest_closed_period is not None:
        latest_closed_period_summary = LedgerClosedPeriodSummary(
            id=str(latest_closed_period.id),
            period_start=latest_closed_period.period_start,
            period_end=latest_closed_period.period_end,
            total_cost_usd=latest_closed_period.total_cost_usd,
            net_cost_usd=latest_closed_period.net_cost_usd,
            closed_at=latest_closed_period.closed_at,
        )

    latest_backup_snapshot = (
        (
            await db.execute(
                select(BackupSnapshot)
                .where(BackupSnapshot.workspace_id == workspace_id)
                .order_by(BackupSnapshot.created_at.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )

    latest_backup_summary = None
    if latest_backup_snapshot is not None:
        latest_backup_summary = LedgerBackupEvidenceSummary(
            id=str(latest_backup_snapshot.id),
            bucket=latest_backup_snapshot.bucket,
            manifest_key=latest_backup_snapshot.manifest_key,
            checksum=latest_backup_snapshot.checksum,
            integrity_status=latest_backup_snapshot.integrity_status,
            artifact_count=latest_backup_snapshot.artifact_count,
            created_at=latest_backup_snapshot.created_at,
        )

    audit_window_start = generated_at - timedelta(days=30)
    recent_audit_event_count = int(
        (
            await db.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.workspace_id == workspace_id,
                    AuditEvent.created_at >= audit_window_start,
                )
            )
        ).scalar()
        or 0
    )

    chargeback_summary = None
    try:
        period = f"{generated_at.year}-{generated_at.month:02d}"
        chargeback = await build_chargeback_report(
            db,
            workspace_id,
            period=period,
            dimension="workspace",
        )
        chargeback_summary = LedgerChargebackSummary(
            period=chargeback.period,
            dimension=chargeback.dimension,
            total_cost_usd=chargeback.total_cost_usd,
            covered_cost_usd=chargeback.covered_cost_usd,
            unallocated_cost_usd=chargeback.unallocated_cost_usd,
            breakdown_count=len(chargeback.breakdown),
        )
    except Exception:
        chargeback_summary = None

    missing_evidence: list[str] = []
    evidence_score = 0

    if latest_closed_period_summary is not None:
        evidence_score += 1
    else:
        missing_evidence.append("closed_billing_period")

    if latest_snapshot_response is not None:
        evidence_score += 1
    else:
        missing_evidence.append("ledger_snapshot")

    if latest_status == "ok":
        evidence_score += 1
    elif latest_snapshot_response is not None:
        missing_evidence.append("snapshot_verification")

    if chargeback_summary is not None and chargeback_summary.breakdown_count > 0:
        evidence_score += 1
    else:
        missing_evidence.append("chargeback_allocation")

    if latest_backup_summary is not None and latest_backup_summary.integrity_status != "failed":
        evidence_score += 1
    else:
        missing_evidence.append("backup_snapshot")

    readiness_status = "empty"
    if tampered_count > 0:
        readiness_status = "at_risk"
    elif evidence_score >= 5:
        readiness_status = "ready"
    elif evidence_score > 0:
        readiness_status = "partial"

    return LedgerClosureSummary(
        generated_at=generated_at,
        readiness_status=readiness_status,
        evidence_score=evidence_score,
        missing_evidence=missing_evidence,
        latest_snapshot=latest_snapshot_response,
        verification=LedgerVerificationSummary(
            total_snapshots=len(snapshots),
            ok_count=ok_count,
            tampered_count=tampered_count,
            pending_count=pending_count,
            latest_status=latest_status,
        ),
        latest_closed_period=latest_closed_period_summary,
        chargeback=chargeback_summary,
        latest_backup_snapshot=latest_backup_summary,
        recent_audit_event_count=recent_audit_event_count,
    )
