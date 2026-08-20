"""
Pydantic schemas for budget CRUD and hot-path check endpoints.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ── Budget ────────────────────────────────────────────────────────────────────


class BudgetCreate(BaseModel):
    scope_type: str = Field(
        ...,
        pattern="^(workspace|end_user|feature_tag|app|access_group|api_key|provider_profile)$",
    )
    scope_id: str | None = None
    period_type: str = Field(..., pattern="^(daily|monthly|total)$")
    limit_usd: Decimal = Field(..., gt=0)
    action: str = Field(..., pattern="^(notify|block|downgrade|throttle|fallback)$")
    downgrade_to_model: str | None = None


class BudgetUpdate(BaseModel):
    scope_type: str | None = Field(
        None,
        pattern="^(workspace|end_user|feature_tag|app|access_group|api_key|provider_profile)$",
    )
    scope_id: str | None = None
    period_type: str | None = Field(None, pattern="^(daily|monthly|total)$")
    limit_usd: Decimal | None = Field(None, gt=0)
    action: str | None = Field(None, pattern="^(notify|block|downgrade|throttle|fallback)$")
    downgrade_to_model: str | None = None
    is_active: bool | None = None


class BudgetResponse(BaseModel):
    id: str
    scope_type: str
    scope_id: str | None
    scope_display_name: str | None = None
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
