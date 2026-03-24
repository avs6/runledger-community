"""
Pydantic request/response schemas for the billing endpoints.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

# ── Requests ──────────────────────────────────────────────────────────────────


class BillingPeriodCreate(BaseModel):
    period_start: date
    period_end: date
    currency: str = Field("USD", min_length=3, max_length=3)
    exchange_rate_to_usd: Decimal = Field(Decimal("1.0"), gt=0)


class ChargebackRuleCreate(BaseModel):
    allocation_type: str = Field(..., pattern="^(cost_center|team|env)$")
    dimension: str
    weight: Decimal = Field(..., ge=0, le=1)
    cost_center_id: uuid.UUID | None = None
    require_approval: bool = False


class CostCenterCreate(BaseModel):
    name: str
    code: str | None = None
    parent_id: uuid.UUID | None = None
    description: str | None = None


class CostCenterUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    parent_id: uuid.UUID | None = None
    description: str | None = None


class BillingAdjustmentCreate(BaseModel):
    adjustment_type: str = Field(
        ..., pattern="^(credit|refund|prepaid_deduction|surcharge)$"
    )
    amount_usd: Decimal = Field(..., gt=0)
    description: str | None = None
    reference_id: str | None = None


# ── Responses ─────────────────────────────────────────────────────────────────


class BillingPeriodResponse(BaseModel):
    id: uuid.UUID
    period_start: date
    period_end: date
    status: str
    total_cost_usd: Decimal | None
    net_cost_usd: Decimal | None = None
    currency: str = "USD"
    exchange_rate_to_usd: Decimal = Decimal("1.0")
    snapshot_hash: str | None
    closed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingPeriodList(BaseModel):
    items: list[BillingPeriodResponse]


class ChargebackRuleResponse(BaseModel):
    id: uuid.UUID
    allocation_type: str
    dimension: str
    weight: Decimal
    cost_center_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChargebackRuleList(BaseModel):
    items: list[ChargebackRuleResponse]


class CostCenterResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    code: str | None
    parent_id: uuid.UUID | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CostCenterNode(BaseModel):
    """Tree node — includes recursively nested children."""

    id: uuid.UUID
    name: str
    code: str | None
    parent_id: uuid.UUID | None
    description: str | None
    children: list[Any] = []  # list[CostCenterNode] — forward ref


CostCenterNode.model_rebuild()


class CostCenterList(BaseModel):
    items: list[CostCenterResponse]
    total: int


class BillingAdjustmentResponse(BaseModel):
    id: uuid.UUID
    billing_period_id: uuid.UUID
    adjustment_type: str
    amount_usd: Decimal
    description: str | None
    reference_id: str | None
    created_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingAdjustmentList(BaseModel):
    items: list[BillingAdjustmentResponse]
    total_credits_usd: Decimal
    total_surcharges_usd: Decimal
    net_adjustment_usd: Decimal


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
    gross_cost_usd: Decimal
    net_cost_usd: Decimal
    total_adjustments_usd: Decimal
    by_application: list[BreakdownApp]
    adjustments: list[BillingAdjustmentResponse] = []

    # Legacy alias so existing callers that read total_cost_usd still work
    @property
    def total_cost_usd(self) -> Decimal:
        return self.gross_cost_usd


class UsageSnapshotResponse(BaseModel):
    id: str
    billing_period_id: str
    signature: str
    signing_key_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
