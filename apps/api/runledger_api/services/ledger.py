"""
Ledger service — signing key management, daily snapshot build/verify.

All functions are pure async with no FastAPI dependencies.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core import secrets as secret_store
from runledger_api.models.audit import AuditEvent
from runledger_api.models.backup_ops import BackupSnapshot
from runledger_api.models.billing import BillingPeriod
from runledger_api.models.events import ProviderCall
from runledger_api.models.ledger import LedgerKey, LedgerSnapshot, LedgerSnapshotEntry
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


def _encrypt_key(plaintext: str) -> str:
    """Ledger signing keys are always encrypted at rest (review cd:M-03).

    Uses the shared envelope in ``core/secrets.py`` (SECRETS_MASTER_KEY / KMS, or
    the SECRET_KEY-derived key in development); LEDGER_MASTER_KEY stays a
    decryption key for keys written before this change.
    """
    return secret_store.encrypt(plaintext)


def _decrypt_key(stored: str) -> str:
    """Decrypt a stored key. Raises SecretDecryptError instead of silently using
    the ciphertext as the HMAC key (review cd:M-03)."""
    plain = secret_store.decrypt(stored)
    if not plain:
        raise secret_store.SecretDecryptError("ledger key is empty")
    return plain


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


def _day_range(d: date) -> tuple[datetime, datetime]:
    """UTC ``[start, end)`` of a calendar day (index-friendly, timezone-independent)."""
    start = datetime(d.year, d.month, d.day, tzinfo=UTC)
    return start, start + timedelta(days=1)


def _day_filters(workspace_id: uuid.UUID, snapshot_date: date) -> list[Any]:
    start, end = _day_range(snapshot_date)
    return [
        ProviderCall.workspace_id == workspace_id,
        ProviderCall.created_at >= start,
        ProviderCall.created_at < end,
        ProviderCall.status == "success",
    ]


async def build_daily_snapshot(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    snapshot_date: date,
) -> dict[str, Any]:
    """Aggregate provider_calls for the given UTC day into a snapshot dict."""
    filters = _day_filters(workspace_id, snapshot_date)
    totals_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("total_cost"),
                func.count(ProviderCall.id).label("call_count"),
            ).where(*filters)
        )
    ).one()
    total_cost: Decimal = totals_row.total_cost or Decimal(0)
    call_count: int = totals_row.call_count or 0

    model_rows = (
        await db.execute(
            select(
                ProviderCall.model,
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
            )
            .where(*filters)
            .group_by(ProviderCall.model)
        )
    ).all()
    model_breakdown = {row.model: str(row.cost) for row in model_rows if row.model}

    return {
        "workspace_id": str(workspace_id),
        "snapshot_date": str(snapshot_date),
        "total_cost_usd": str(total_cost),
        "call_count": call_count,
        "model_breakdown": model_breakdown,
    }


# ── Sealing (review cd:M-02) ──────────────────────────────────────────────────
#
# A sealed snapshot stores, per provider call of the day, a hash of the call's
# canonical fields (who, what, how many tokens, cost) and the cost at sealing time.
# The snapshot signature covers the digest of that manifest and the previous
# snapshot's hash, so snapshots form a chain. Verification compares the live rows
# against the manifest instead of re-aggregating them: a call priced after sealing
# (cost NULL → value) or a call that arrived late is reported as late data, not as
# tampering; changing a sealed call's user, key, model, tokens or cost is tampering.

_CANONICAL_FIELDS = (
    "id",
    "run_id",
    "api_key_id",
    "end_user_id",
    "provider",
    "model",
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "status",
    "created_at",
)


def canonical_row_hash(row: Any, *, cost: Any = "__row__") -> str:
    """SHA-256 of a provider call's canonical fields; ``cost`` overrides its cost."""
    value = getattr(row, "cost_usd", None) if cost == "__row__" else cost
    parts = []
    for field in _CANONICAL_FIELDS:
        v = getattr(row, field, None)
        if isinstance(v, datetime):
            v = v.astimezone(UTC).isoformat()
        parts.append("" if v is None else str(v))
    parts.append("" if value is None else str(Decimal(value).normalize()))
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def entries_digest(entries: list[tuple[str, str]]) -> str:
    """Digest of a manifest: SHA-256 over sorted ``call_id:row_hash`` lines."""
    body = "\n".join(f"{cid}:{h}" for cid, h in sorted(entries))
    return hashlib.sha256(body.encode()).hexdigest()


def _signed_payload(
    data: dict[str, Any], entries_root: str | None, entry_count: int | None, prev_hash: str | None
) -> dict[str, Any]:
    if entries_root is None:
        return data  # legacy, aggregates only
    return {
        **data,
        "entries_root": entries_root,
        "entry_count": entry_count,
        "prev_hash": prev_hash,
    }


def _snapshot_data(snap: LedgerSnapshot) -> dict[str, Any]:
    return {
        "workspace_id": str(snap.workspace_id),
        "snapshot_date": str(snap.snapshot_date),
        "total_cost_usd": str(snap.total_cost_usd),
        "call_count": snap.call_count,
        "model_breakdown": snap.model_breakdown or {},
    }


async def _day_calls(db: AsyncSession, workspace_id: uuid.UUID, snapshot_date: date) -> list[Any]:
    cols = [getattr(ProviderCall, f) for f in _CANONICAL_FIELDS] + [ProviderCall.cost_usd]
    return list(
        (await db.execute(select(*cols).where(*_day_filters(workspace_id, snapshot_date)))).all()
    )


async def seal_snapshot(
    db: AsyncSession, workspace_id: uuid.UUID, snapshot_date: date
) -> tuple[LedgerSnapshot, bool]:
    """Seal the day's snapshot; returns ``(snapshot, created)``.

    Sealed snapshots are immutable: sealing a day that already has a snapshot
    returns it unchanged, so history can't be re-signed through the API or worker.
    Does not commit.
    """
    existing = (
        await db.execute(
            select(LedgerSnapshot).where(
                LedgerSnapshot.workspace_id == workspace_id,
                LedgerSnapshot.snapshot_date == snapshot_date,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    data = await build_daily_snapshot(db, workspace_id, snapshot_date)
    rows = await _day_calls(db, workspace_id, snapshot_date)
    entries = [(str(r.id), canonical_row_hash(r)) for r in rows]
    root = entries_digest(entries)
    prev = (
        await db.execute(
            select(LedgerSnapshot.hash)
            .where(
                LedgerSnapshot.workspace_id == workspace_id,
                LedgerSnapshot.snapshot_date < snapshot_date,
            )
            .order_by(LedgerSnapshot.snapshot_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    key = await get_or_create_active_key(db, workspace_id)
    signature = compute_snapshot_hash(
        _signed_payload(data, root, len(entries), prev), _decrypt_key(key.key_value)
    )
    snap = LedgerSnapshot(
        workspace_id=workspace_id,
        snapshot_date=snapshot_date,
        total_cost_usd=Decimal(data["total_cost_usd"]),
        model_breakdown=data["model_breakdown"],
        call_count=data["call_count"],
        hash=signature,
        key_id=key.id,
        prev_hash=prev,
        entries_root=root,
        entry_count=len(entries),
        sealed_at=datetime.now(UTC),
    )
    db.add(snap)
    await db.flush()
    db.add_all(
        LedgerSnapshotEntry(
            snapshot_id=snap.id,
            provider_call_id=r.id,
            row_hash=h,
            cost_usd=r.cost_usd,
        )
        for r, (_, h) in zip(rows, entries, strict=True)
    )
    await db.flush()
    log.info(
        "ledger_snapshot_sealed",
        workspace_id=str(workspace_id),
        snapshot_date=str(snapshot_date),
        entries=len(entries),
    )
    return snap, True


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
    """Verify a snapshot.

    Statuses: ``ok``; ``late_data`` (only calls priced or recorded after sealing);
    ``incomplete`` (sealed calls no longer exist, e.g. retention); ``tampered`` (the
    signature, the chain link or a sealed call's fields don't match);
    ``unsealed_drift`` (a legacy aggregate-only snapshot no longer matches; it can't
    tell late data from tampering); ``not_found``. An anchored snapshot is also
    compared with its off-box anchor; a mismatch is tampering.
    """
    snapshot = (
        await db.execute(
            select(LedgerSnapshot).where(
                LedgerSnapshot.workspace_id == workspace_id,
                LedgerSnapshot.snapshot_date == snapshot_date,
            )
        )
    ).scalar_one_or_none()
    if snapshot is None:
        return LedgerVerifyResult(
            snapshot_date=snapshot_date,
            status="not_found",
            stored_hash=None,
            computed_hash=None,
            match=False,
        )
    key = (
        await db.execute(select(LedgerKey).where(LedgerKey.id == snapshot.key_id))
    ).scalar_one_or_none()
    if key is None:
        return LedgerVerifyResult(
            snapshot_date=snapshot_date,
            status="tampered",
            stored_hash=snapshot.hash,
            computed_hash=None,
            match=False,
            sealed=getattr(snapshot, "entries_root", None) is not None,
            detail="Signing key is missing",
        )
    key_value = _decrypt_key(key.key_value)

    if getattr(snapshot, "entries_root", None) is None:
        live = await build_daily_snapshot(db, workspace_id, snapshot_date)
        computed = compute_snapshot_hash(live, key_value)
        match = computed == snapshot.hash
        return LedgerVerifyResult(
            snapshot_date=snapshot_date,
            status="ok" if match else "unsealed_drift",
            stored_hash=snapshot.hash,
            computed_hash=computed,
            match=match,
            sealed=False,
            detail=None
            if match
            else "Legacy snapshot without a sealed manifest: live totals differ, which may be "
            "late enrichment or late data rather than tampering",
        )

    entries = list(
        (
            await db.execute(
                select(LedgerSnapshotEntry).where(LedgerSnapshotEntry.snapshot_id == snapshot.id)
            )
        ).scalars()
    )
    root = entries_digest([(str(e.provider_call_id), e.row_hash) for e in entries])
    computed = compute_snapshot_hash(
        _signed_payload(_snapshot_data(snapshot), root, len(entries), snapshot.prev_hash),
        key_value,
    )
    signature_ok = computed == snapshot.hash and root == snapshot.entries_root
    prev = (
        await db.execute(
            select(LedgerSnapshot.hash)
            .where(
                LedgerSnapshot.workspace_id == workspace_id,
                LedgerSnapshot.snapshot_date < snapshot_date,
            )
            .order_by(LedgerSnapshot.snapshot_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    chain_ok = prev == snapshot.prev_hash

    live = {str(r.id): r for r in await _day_calls(db, workspace_id, snapshot_date)}
    sealed_ids = {str(e.provider_call_id) for e in entries}
    modified = missing = late_enriched = 0
    for e in entries:
        row = live.get(str(e.provider_call_id))
        if row is None:
            missing += 1
            continue
        if canonical_row_hash(row) == e.row_hash:
            continue
        if e.cost_usd is None and canonical_row_hash(row, cost=None) == e.row_hash:
            late_enriched += 1
        else:
            modified += 1
    late_arrivals = len(set(live) - sealed_ids)

    from runledger_api.services.ledger_anchor import check_anchor  # noqa: PLC0415

    anchor_ok, anchor_detail = await check_anchor(db, snapshot)

    if not signature_ok or not chain_ok or modified or anchor_ok is False:
        status_ = "tampered"
    elif missing:
        status_ = "incomplete"
    elif late_enriched or late_arrivals:
        status_ = "late_data"
    else:
        status_ = "ok"
    log.info(
        "ledger_verify",
        workspace_id=str(workspace_id),
        snapshot_date=str(snapshot_date),
        status=status_,
    )
    problems = []
    if not signature_ok:
        problems.append("signature or manifest does not match")
    if not chain_ok:
        problems.append("previous-snapshot link does not match")
    if anchor_ok is False and anchor_detail:
        problems.append(anchor_detail)
    return LedgerVerifyResult(
        snapshot_date=snapshot_date,
        status=status_,
        stored_hash=snapshot.hash,
        computed_hash=computed,
        match=signature_ok and chain_ok,
        sealed=True,
        chain_ok=chain_ok,
        entry_count=len(entries),
        modified_rows=modified,
        missing_rows=missing,
        late_enriched_rows=late_enriched,
        late_arrival_rows=late_arrivals,
        anchored=bool(getattr(snapshot, "anchor_uri", None)),
        anchor_ok=anchor_ok,
        detail="; ".join(problems) or None,
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
                prev_hash=snap.prev_hash,
                entry_count=snap.entry_count,
                sealed_at=snap.sealed_at,
                anchor_uri=getattr(snap, "anchor_uri", None),
                anchored_at=getattr(snap, "anchored_at", None),
                anchor_locked=getattr(snap, "anchor_locked", None),
                created_at=snap.created_at,
            )
        if result.status in {"ok", "late_data"}:
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

    if latest_status in {"ok", "late_data"}:
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
