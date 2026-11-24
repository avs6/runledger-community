"""
Pydantic schemas for budget CRUD and hot-path check endpoints.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

# ── Budget ────────────────────────────────────────────────────────────────────

SCOPE_PATTERN = "^(workspace|end_user|feature_tag|app|access_group|api_key|provider_profile|model)$"
PERIOD_PATTERN = "^(daily|weekly|monthly|total)$"
ACTION_PATTERN = "^(notify|block|downgrade|throttle|fallback)$"


class BudgetCreate(BaseModel):
    scope_type: str = Field(
        ...,
        pattern=SCOPE_PATTERN,
    )
    scope_id: str | None = Field(None, max_length=255)
    # Optional key filter, only for scope_type=model ("this key's spend on gpt-4*").
    api_key_id: str | None = None
    period_type: str = Field(..., pattern=PERIOD_PATTERN)
    limit_usd: Decimal = Field(..., gt=0)
    action: str = Field(..., pattern=ACTION_PATTERN)
    downgrade_to_model: str | None = None


class BudgetUpdate(BaseModel):
    scope_type: str | None = Field(
        None,
        pattern=SCOPE_PATTERN,
    )
    scope_id: str | None = Field(None, max_length=255)
    api_key_id: str | None = None
    period_type: str | None = Field(None, pattern=PERIOD_PATTERN)
    limit_usd: Decimal | None = Field(None, gt=0)
    action: str | None = Field(None, pattern=ACTION_PATTERN)
    downgrade_to_model: str | None = None
    is_active: bool | None = None


class BudgetResponse(BaseModel):
    id: str
    scope_type: str
    scope_id: str | None
    scope_display_name: str | None = None
    api_key_id: str | None = None
    period_type: str
    limit_usd: Decimal
    action: str
    downgrade_to_model: str | None
    is_active: bool
    created_at: datetime
    current_spend_usd: Decimal
    pct_used: Decimal
    breakdown: list[BudgetUserBreakdownEntry] | None = None

    model_config = {"from_attributes": True}


class BudgetUserBreakdownEntry(BaseModel):
    end_user_id: str
    cost_usd: Decimal
    run_count: int
    call_count: int
    pct_of_total: Decimal


class BudgetList(BaseModel):
    items: list[BudgetResponse]


class BudgetRollupWorkspace(BaseModel):
    workspace_id: str
    workspace_name: str
    budget_count: int
    active_budget_count: int
    limit_usd: Decimal
    current_spend_usd: Decimal
    remaining_usd: Decimal
    pct_used: Decimal
    exceeded_count: int
    at_risk_count: int


class BudgetRollupResponse(BaseModel):
    scope: str
    workspace_count: int
    budget_count: int
    active_budget_count: int
    limit_usd: Decimal
    current_spend_usd: Decimal
    remaining_usd: Decimal
    pct_used: Decimal
    exceeded_count: int
    at_risk_count: int
    workspaces: list[BudgetRollupWorkspace]


# ── Budget check (hot path) ───────────────────────────────────────────────────


class BudgetCheckResponse(BaseModel):
    allowed: bool
    action: str | None = None
    budget_id: str | None = None
    downgrade_model: str | None = None
    throttled: bool = False
    fallback_model: str | None = None
    # Why a request is refused when it isn't a budget row: "budget_tier:<name>" or
    # "runaway_hold:run:<id>" / "runaway_hold:session:<id>".
    reason: str | None = None


# ── Runaway holds (review cd:B-09) ────────────────────────────────────────────


class RunawayHoldCreate(BaseModel):
    subject_type: str = Field(..., pattern="^(run|session)$")
    subject_id: str = Field(..., min_length=1, max_length=255)
    minutes: int = Field(60, ge=1, le=7 * 24 * 60)
    reason: str = Field("manual", max_length=32)


class RunawayHoldResponse(BaseModel):
    id: str
    subject_type: str
    subject_id: str
    reason: str
    details: dict[str, Any]
    created_at: datetime
    expires_at: datetime
    released_at: datetime | None
    active: bool


class RunawayHoldList(BaseModel):
    items: list[RunawayHoldResponse]


# ── Burn-down and simulation (ENH) ────────────────────────────────────────────


class BudgetBurndownPoint(BaseModel):
    date: str
    spend_usd: Decimal
    cumulative_usd: Decimal
    forecast: bool = False


class BudgetBurndownResponse(BaseModel):
    budget_id: str
    period_type: str
    period_start: datetime | None
    period_end: datetime | None
    limit_usd: Decimal
    current_spend_usd: Decimal
    daily_run_rate_usd: Decimal
    projected_period_spend_usd: Decimal | None
    forecast_breach_date: str | None
    already_breached: bool
    points: list[BudgetBurndownPoint]


class BudgetSimulateRequest(BaseModel):
    scope_type: str = Field(..., pattern=SCOPE_PATTERN)
    scope_id: str | None = Field(None, max_length=255)
    api_key_id: str | None = None
    period_type: str = Field(..., pattern=PERIOD_PATTERN)
    limit_usd: Decimal = Field(..., gt=0)
    action: str = Field("block", pattern=ACTION_PATTERN)
    days: int = Field(30, ge=1, le=90)


class BudgetSimulatePeriod(BaseModel):
    period_key: str
    spend_usd: Decimal
    call_count: int
    breached_at: datetime | None
    affected_calls: int
    affected_cost_usd: Decimal


class BudgetSimulateResponse(BaseModel):
    days: int
    window_start: datetime
    window_end: datetime
    total_spend_usd: Decimal
    total_calls: int
    periods: list[BudgetSimulatePeriod]
    breach_count: int
    affected_calls: int
    affected_cost_usd: Decimal
    first_breach_at: datetime | None
    summary: str


# ── Breach ────────────────────────────────────────────────────────────────────


class BreachResponse(BaseModel):
    id: str
    budget_id: str
    occurred_at: datetime
    spend_at_breach_usd: Decimal | None
    action_taken: str | None
    notified_at: datetime | None

    model_config = {"from_attributes": True}


class BreachList(BaseModel):
    items: list[BreachResponse]


# ── Notification channel ──────────────────────────────────────────────────────


class NotificationCreate(BaseModel):
    channel: str = Field(..., pattern="^(webhook|slack)$")
    destination_url: str
    events: list[str] = Field(default_factory=lambda: ["budget.breach", "runaway.detected"])


class NotificationResponse(BaseModel):
    id: str
    channel: str
    destination_url: str
    events: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationList(BaseModel):
    items: list[NotificationResponse]


class NotificationUpdate(BaseModel):
    destination_url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


class NotificationTestResult(BaseModel):
    ok: bool
    error: str | None = None


class NotificationDeliveryResponse(BaseModel):
    id: str
    notification_id: str
    event_type: str
    attempt: int
    status: str
    response_status: int | None
    error_detail: str | None
    delivered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationDeliveryList(BaseModel):
    items: list[NotificationDeliveryResponse]


# ── Billing summary ──────────────────────────────────────────────────────────


class BillingPeriodSummary(BaseModel):
    period: str
    total_cost_usd: Decimal
    billable_cost_usd: Decimal
    non_billable_cost_usd: Decimal
    total_calls: int
    billable_calls: int


class BillingSummaryResponse(BaseModel):
    workspace_id: str
    periods: list[BillingPeriodSummary]
