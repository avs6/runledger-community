"""Pydantic schemas for ledger endpoints (Phase 11)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class LedgerSnapshotResponse(BaseModel):
    id: str
    workspace_id: str
    snapshot_date: date
    total_cost_usd: Decimal
    model_breakdown: dict[str, Any]
    call_count: int
    hash: str
    key_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LedgerSnapshotList(BaseModel):
    items: list[LedgerSnapshotResponse]


class LedgerVerifyResult(BaseModel):
    snapshot_date: date
    status: str  # "ok" | "tampered" | "not_found"
    stored_hash: str | None
    computed_hash: str | None
    match: bool


class LedgerVerificationSummary(BaseModel):
    total_snapshots: int
    ok_count: int
    tampered_count: int
    pending_count: int
    latest_status: str | None = None


class LedgerClosedPeriodSummary(BaseModel):
    id: str
    period_start: date
    period_end: date
    total_cost_usd: Decimal | None
    net_cost_usd: Decimal | None
    closed_at: datetime | None


class LedgerChargebackSummary(BaseModel):
    period: str
    dimension: str
    total_cost_usd: Decimal
    covered_cost_usd: Decimal
    unallocated_cost_usd: Decimal
    breakdown_count: int


class LedgerBackupEvidenceSummary(BaseModel):
    id: str
    bucket: str
    manifest_key: str | None
    checksum: str | None
    integrity_status: str
    artifact_count: int
    created_at: datetime


class LedgerClosureSummary(BaseModel):
    generated_at: datetime
    readiness_status: str
    evidence_score: int
    missing_evidence: list[str]
    latest_snapshot: LedgerSnapshotResponse | None = None
    verification: LedgerVerificationSummary
    latest_closed_period: LedgerClosedPeriodSummary | None = None
    chargeback: LedgerChargebackSummary | None = None
    latest_backup_snapshot: LedgerBackupEvidenceSummary | None = None
    recent_audit_event_count: int = 0
