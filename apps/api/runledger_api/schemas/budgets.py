"""
Pydantic schemas for budget CRUD and hot-path check endpoints.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ── Budget ────────────────────────────────────────────────────────────────────


class BudgetCreate(BaseModel):
    scope_type: str = Field(..., pattern="^(workspace|end_user|feature_tag|app)$")
    scope_id: str | None = None
    period_type: str = Field(..., pattern="^(daily|monthly|total)$")
    limit_usd: Decimal = Field(..., gt=0)
    action: str = Field(..., pattern="^(notify|block|downgrade)$")
    downgrade_to_model: str | None = None


class BudgetResponse(BaseModel):
    id: str
    scope_type: str
    scope_id: str | None
    period_type: str
    limit_usd: Decimal
    action: str
    downgrade_to_model: str | None
    is_active: bool
    created_at: datetime
    current_spend_usd: Decimal
    pct_used: Decimal

    model_config = {"from_attributes": True}


class BudgetList(BaseModel):
    items: list[BudgetResponse]


# ── Budget check (hot path) ───────────────────────────────────────────────────


class BudgetCheckResponse(BaseModel):
    allowed: bool
    action: str | None = None
    budget_id: str | None = None
    downgrade_model: str | None = None


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
