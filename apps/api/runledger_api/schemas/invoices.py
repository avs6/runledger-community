"""Pydantic schemas for provider invoice reconciliation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    provider: str
    period_start: date
    period_end: date
    currency: str
    total_amount: Decimal
    line_count: int
    matched_count: int
    unmatched_amount: Decimal | None
    status: str
    filename: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceList(BaseModel):
    items: list[InvoiceResponse]


class InvoiceLineResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    provider_request_id: str | None
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    amount: Decimal
    occurred_at: datetime | None
    match_status: str
    matched_call_id: uuid.UUID | None
    token_delta: int | None
    cost_delta: Decimal | None
    dispute_note: str | None
    raw: dict[str, Any]

    model_config = {"from_attributes": True}


class InvoiceLineList(BaseModel):
    items: list[InvoiceLineResponse]
    total: int


class DisputeRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)


# ── Reconciliation summary ─────────────────────────────────────────────────────


class TokenMismatchBucket(BaseModel):
    """Groups lines by token count divergence (0–5%, 5–20%, >20%)."""

    bucket: str  # "0-5%", "5-20%", ">20%"
    count: int
    amount: Decimal


class ReconciliationSummary(BaseModel):
    invoice_id: uuid.UUID
    provider: str
    period_start: date
    period_end: date
    total_amount: Decimal
    line_count: int
    matched_exact: int
    matched_fuzzy: int
    unmatched: int
    disputed: int
    matched_pct: Decimal
    unmatched_amount: Decimal
    runledger_total: Decimal  # sum of matched provider_calls.cost_usd
    delta_amount: Decimal  # invoice_total - runledger_total
    delta_pct: Decimal | None
    token_mismatch_buckets: list[TokenMismatchBucket]
    status: str


# ── Dispute export ─────────────────────────────────────────────────────────────


class DisputeExport(BaseModel):
    """Signed JSON package for finance disputes."""

    invoice_id: str
    provider: str
    period_start: str
    period_end: str
    exported_at: str
    unmatched_lines: list[dict[str, Any]]
    disputed_lines: list[dict[str, Any]]
    summary: dict[str, Any]
    signature: str  # HMAC-SHA256 of the payload
