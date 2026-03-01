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
