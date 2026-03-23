"""Pydantic schemas for outcome CRUD and ROI analytics."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


# ── CRUD ──────────────────────────────────────────────────────────────────────

class OutcomeCreate(BaseModel):
    outcome_type: str = Field(..., min_length=1, max_length=128)
    success: bool
    run_id: uuid.UUID | None = None
    session_id: str | None = None
    end_user_id: str | None = None
    value_usd: Decimal | None = Field(None, ge=0)
    labels: dict[str, Any] = Field(default_factory=dict)


class OutcomeResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    run_id: uuid.UUID | None
    session_id: str | None
    end_user_id: str | None
    outcome_type: str
    success: bool
    value_usd: Decimal | None
    labels: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class OutcomeList(BaseModel):
    items: list[OutcomeResponse]
    total: int


# ── Analytics ─────────────────────────────────────────────────────────────────

class OutcomeSummaryItem(BaseModel):
    outcome_type: str
    count: int
    success_count: int
    success_rate: Decimal
    total_cost_usd: Decimal
    cost_per_success_usd: Decimal | None   # None when no successes
    total_value_usd: Decimal | None
    roi: Decimal | None                    # (total_value - total_cost) / total_cost * 100


class OutcomeSummary(BaseModel):
    items: list[OutcomeSummaryItem]
    window_days: int


class OutcomeTrendPoint(BaseModel):
    day: date
    outcome_type: str
    success_rate: Decimal
    cost_per_success_usd: Decimal | None
    count: int
    roi: Decimal | None


class OutcomeTrend(BaseModel):
    items: list[OutcomeTrendPoint]


class WorkflowROIItem(BaseModel):
    feature_tag: str
    outcome_type: str
    run_count: int
    success_count: int
    success_rate: Decimal
    total_cost_usd: Decimal
    total_value_usd: Decimal | None
    roi: Decimal | None
    cost_per_success_usd: Decimal | None


class WorkflowROIList(BaseModel):
    items: list[WorkflowROIItem]


class QualityOutcomeCorrelation(BaseModel):
    """Correlation between avg score and success rate per outcome type."""
    outcome_type: str
    avg_score: Decimal | None
    success_rate: Decimal
    sample_count: int
