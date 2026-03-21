"""
Pydantic request/response schemas for the billing endpoints.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ── Requests ──────────────────────────────────────────────────────────────────


class BillingPeriodCreate(BaseModel):
    period_start: date
    period_end: date


class ChargebackRuleCreate(BaseModel):
    allocation_type: str = Field(..., pattern="^(cost_center|team|env)$")
    dimension: str
    weight: Decimal = Field(..., ge=0, le=1)


# ── Responses ─────────────────────────────────────────────────────────────────


class BillingPeriodResponse(BaseModel):
    id: str
    period_start: date
    period_end: date
    status: str
    total_cost_usd: Decimal | None
    snapshot_hash: str | None
    closed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingPeriodList(BaseModel):
    items: list[BillingPeriodResponse]


class ChargebackRuleResponse(BaseModel):
    id: str
    allocation_type: str
    dimension: str
    weight: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class ChargebackRuleList(BaseModel):
    items: list[ChargebackRuleResponse]


class ReconciliationResult(BaseModel):
    period_id: str
    status: str  # "pass" | "warning" | "fail"
    provider_calls_sum: Decimal
    usage_daily_sum: Decimal
    delta_pct: Decimal
    orphaned_calls: int
    duplicate_calls: int
    issues: list[str]
    warnings: list[str] = []


class BreakdownUser(BaseModel):
    end_user_id: str | None
    cost_usd: Decimal
    run_count: int


class BreakdownApp(BaseModel):
    application_id: str | None
    cost_usd: Decimal
    users: list[BreakdownUser]


class PeriodBreakdown(BaseModel):
    period_id: str
    total_cost_usd: Decimal
    by_application: list[BreakdownApp]


class UsageSnapshotResponse(BaseModel):
    id: str
    billing_period_id: str
    signature: str
    signing_key_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
