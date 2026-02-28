"""
Pydantic response schemas for the analytics API.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    total_cost_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int
    run_count: int
    call_count: int
    prev_cost_usd: Decimal
    cost_delta_pct: Decimal | None  # None when prev_cost is zero


class SpendPoint(BaseModel):
    period: str  # ISO-8601 datetime or date string
    cost_usd: Decimal
    input_tokens: int
    output_tokens: int
    call_count: int


class SpendOverTime(BaseModel):
    granularity: str
    points: list[SpendPoint]


class ModelSpend(BaseModel):
    provider: str
    model: str
    cost_usd: Decimal
    input_tokens: int
    output_tokens: int
    call_count: int


class SpendByModel(BaseModel):
    items: list[ModelSpend]


class UserSpend(BaseModel):
    end_user_id: str
    cost_usd: Decimal
    run_count: int
    call_count: int
    avg_cost_per_run: Decimal
    last_active: str | None
    first_seen: str | None = None


class SpendByUser(BaseModel):
    items: list[UserSpend]


class FeatureSpend(BaseModel):
    feature_tag: str | None
    cost_usd: Decimal
    run_count: int
    call_count: int


class SpendByFeature(BaseModel):
    items: list[FeatureSpend]


class UserSpendDetail(BaseModel):
    end_user_id: str
    cost_usd: Decimal
    run_count: int
    call_count: int
    avg_cost_per_run: Decimal
    last_active: str | None
    spend_over_time: list[SpendPoint]
    models_used: list[ModelSpend]
    features_used: list[FeatureSpend]


class CohortSummary(BaseModel):
    cohort_tier: str  # "P0" | "P1" | "P2" | "P3"
    user_count: int
    avg_cost_usd: Decimal
    total_cost_usd: Decimal


class CohortList(BaseModel):
    items: list[CohortSummary]
    window_days: int


class AnomalyItem(BaseModel):
    end_user_id: str
    detected_at: date
    daily_spend: Decimal
    mean_spend: Decimal
    zscore: Decimal
    reason: str
    created_at: datetime
    model_config = {"from_attributes": True}


class AnomalyList(BaseModel):
    items: list[AnomalyItem]
