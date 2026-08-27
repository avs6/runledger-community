from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    metric: str = Field(
        ...,
        pattern="^(error_rate|p95_latency|avg_score|spend_velocity|model_availability|gateway_overhead_p95|budget_utilization|budget_breach_count)$",
    )
    operator: str = Field(..., pattern="^(gt|lt)$")
    threshold: Decimal = Field(..., ge=0)
    window_minutes: int = Field(60, ge=5, le=1440)
    channel_id: uuid.UUID | None = None
    email_enabled: bool = False


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    metric: str | None = Field(
        None,
        pattern="^(error_rate|p95_latency|avg_score|spend_velocity|model_availability|gateway_overhead_p95|budget_utilization|budget_breach_count)$",
    )
    operator: str | None = Field(None, pattern="^(gt|lt)$")
    threshold: Decimal | None = None
    window_minutes: int | None = Field(None, ge=5, le=1440)
    is_active: bool | None = None
    channel_id: uuid.UUID | None = None
    email_enabled: bool | None = None


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    metric: str
    operator: str
    threshold: Decimal
    window_minutes: int
    action: str
    channel_id: uuid.UUID | None
    is_active: bool
    email_enabled: bool
    created_at: datetime


class AlertRuleList(BaseModel):
    items: list[AlertRuleResponse]


class AlertFiringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_id: uuid.UUID
    workspace_id: uuid.UUID
    fired_at: datetime
    metric_value: Decimal
    resolved_at: datetime | None
    rule_name: str


class AlertHistoryList(BaseModel):
    items: list[AlertFiringResponse]
