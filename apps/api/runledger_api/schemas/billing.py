"""
Pydantic request/response schemas for the billing endpoints.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, model_validator

# ── Requests ──────────────────────────────────────────────────────────────────


class BillingPeriodCreate(BaseModel):
    period_start: date
    period_end: date
    # ISO-4217 code. exchange_rate_to_usd = USD per 1 unit of this currency; totals are
    # reported in USD and converted to this currency on close and in signed exports.
    currency: str = Field("USD", pattern="^[A-Z]{3}$")
    exchange_rate_to_usd: Decimal = Field(Decimal("1.0"), gt=0, le=Decimal("100000"))

    @model_validator(mode="after")
    def _dates(self) -> BillingPeriodCreate:
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        if (self.period_end - self.period_start).days > 366:
            raise ValueError("a billing period can span at most one year")
        return self


class BillingPeriodUpdate(BaseModel):
    """Edit an open period. Closed periods are frozen; reopen them first."""

    period_start: date | None = None
    period_end: date | None = None
    currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")
    exchange_rate_to_usd: Decimal | None = Field(default=None, gt=0, le=Decimal("100000"))


class BillingPeriodReopen(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class ChargebackRuleCreate(BaseModel):
    """Map one dimension value to a cost center.

    direct: the value's whole cost goes to the cost center (weight 1).
    shared_weight: the value's cost is split; weights for one value sum to at most 1.
    """

    allocation_type: str = Field("shared_weight", pattern="^(direct|shared_weight)$")
    dimension: str = Field(
        ...,
        pattern="^(feature_tag|end_user|application|api_key|access_group|model|provider|intent)$",
    )
    dimension_value: str = Field(..., min_length=1, max_length=255)
    weight: Decimal = Field(..., gt=0, le=1)
    cost_center_id: uuid.UUID
    require_approval: bool = False


class ChargebackRuleUpdate(BaseModel):
    """Edit a rule. ``status`` only toggles active/inactive; approval-gated rules are
    approved through Approvals, and editing one sends it back for approval."""

    allocation_type: str | None = Field(default=None, pattern="^(direct|shared_weight)$")
    dimension: str | None = Field(
        default=None,
        pattern="^(feature_tag|end_user|application|api_key|access_group|model|provider|intent)$",
    )
    dimension_value: str | None = Field(default=None, min_length=1, max_length=255)
    weight: Decimal | None = Field(default=None, gt=0, le=1)
    cost_center_id: uuid.UUID | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


class CostCenterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    parent_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=2000)


class CostCenterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    parent_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=2000)


class BillingAdjustmentCreate(BaseModel):
    adjustment_type: str = Field(..., pattern="^(credit|refund|prepaid_deduction|surcharge)$")
    amount_usd: Decimal = Field(..., gt=0)
    description: str | None = None
    reference_id: str | None = None


class BillingAdjustmentUpdate(BaseModel):
    adjustment_type: str | None = Field(
        default=None, pattern="^(credit|refund|prepaid_deduction|surcharge)$"
    )
    amount_usd: Decimal | None = Field(default=None, gt=0)
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
    closed_by: str | None = None
    reopened_at: datetime | None = None
    reopen_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingPeriodList(BaseModel):
    items: list[BillingPeriodResponse]


class ChargebackRuleResponse(BaseModel):
    id: uuid.UUID
    allocation_type: str
    dimension: str
    dimension_value: str | None = None
    weight: Decimal
    cost_center_id: uuid.UUID | None = None
    status: str = "active"
    approval_id: uuid.UUID | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChargebackRuleList(BaseModel):
    items: list[ChargebackRuleResponse]


class ChargebackBreakdownItem(BaseModel):
    dimension: str
    # The raw value a chargeback rule matches (id for applications/keys/groups,
    # the tag/model/provider text otherwise); dimension_value is its display label.
    dimension_key: str | None = None
    dimension_value: str
    cost_usd: Decimal
    pct_of_total: Decimal
    budget_usd: Decimal | None = None
    variance_usd: Decimal | None = None
    call_count: int = 0
    run_count: int = 0
    allocation_status: str = "allocated"
    coverage_status: str = "unbudgeted"


class ChargebackReport(BaseModel):
    period: str
    dimension: str
    total_cost_usd: Decimal
    covered_cost_usd: Decimal
    unallocated_cost_usd: Decimal
    breakdown: list[ChargebackBreakdownItem]


class ChargebackReportList(BaseModel):
    items: list[ChargebackReport]


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
    # True when served from the closed period's frozen snapshot.
    frozen: bool = False

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


# ── Shared-cost policies ───────────────────────────────────────────────────────

_VALID_FORMULA_TYPES = {"equal_split", "proportional", "fixed_weight"}


class SharedCostAllocation(BaseModel):
    """One allocation target within a shared-cost policy."""

    label: str
    cost_center_id: uuid.UUID | None = None
    weight: Decimal | None = None  # required for fixed_weight
    denominator_value: Decimal | None = None  # used for proportional


class SharedCostPolicyCreate(BaseModel):
    name: str
    description: str | None = None
    formula_type: str = Field(..., pattern="^(equal_split|proportional|fixed_weight)$")
    allocations: list[SharedCostAllocation] = []
    is_active: bool = True


class SharedCostPolicyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    formula_type: str | None = Field(
        default=None, pattern="^(equal_split|proportional|fixed_weight)$"
    )
    allocations: list[SharedCostAllocation] | None = None
    is_active: bool | None = None


class SharedCostPolicyResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    formula_type: str
    allocations: list[Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SharedCostPolicyList(BaseModel):
    items: list[SharedCostPolicyResponse]
    total: int


class SharedCostAllocationResult(BaseModel):
    """Result of running compute_shared_cost_allocation()."""

    policy_id: uuid.UUID
    policy_name: str
    pool_usd: Decimal
    formula_type: str
    allocations: list[dict[str, Any]]  # [{label, cost_center_id, allocated_usd}]


# ── Cost centers, cost-center report, applied allocations ─────────────────────


class CostCenterReportRow(BaseModel):
    cost_center_id: uuid.UUID
    name: str
    code: str | None = None
    direct_usd: Decimal  # from chargeback rules
    shared_usd: Decimal  # from applied shared-cost policies
    total_usd: Decimal


class CostCenterReport(BaseModel):
    period: str
    rule_dimension: str | None
    total_billable_usd: Decimal
    assigned_usd: Decimal
    unassigned_usd: Decimal
    shared_usd: Decimal
    unassigned_shared_usd: Decimal = Decimal(0)
    rows: list[CostCenterReportRow]


class SharedCostApply(BaseModel):
    period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    pool_usd: Decimal = Field(..., gt=0)


class CostAllocationResponse(BaseModel):
    id: uuid.UUID
    period: str
    policy_id: uuid.UUID
    cost_center_id: uuid.UUID | None
    label: str
    pool_usd: Decimal
    amount_usd: Decimal
    created_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CostAllocationList(BaseModel):
    items: list[CostAllocationResponse]
    total_usd: Decimal


# ── Signing ──────────────────────────────────────────────────────────────────


class BillingSigningKey(BaseModel):
    workspace_id: uuid.UUID
    signing_key_id: str
    key: str
    algorithm: str = "HMAC-SHA256 over canonical JSON (sorted keys)"


class BillingVerifyRequest(BaseModel):
    payload: dict[str, Any]
    signature: str
    signing_key_id: str


class BillingVerifyResult(BaseModel):
    valid: bool
    signing_key_id: str
