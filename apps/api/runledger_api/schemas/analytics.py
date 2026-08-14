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


# ── Phase 3: Scoped summaries ────────────────────────────────────────────────


class IntentCount(BaseModel):
    intent: str
    count: int
    cost_usd: Decimal


class ScopedSummary(BaseModel):
    scope: str
    total_cost_usd: Decimal
    total_savings_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int
    run_count: int
    call_count: int
    workspace_count: int
    active_users: int
    avg_cost_per_run: Decimal | None
    top_intents: list[IntentCount]
    top_models: list[ModelSpend]
    cost_delta_pct: Decimal | None


# ── Phase 3: Savings analytics ───────────────────────────────────────────────


class SavingsByCategory(BaseModel):
    category: str
    savings_usd: Decimal
    call_count: int


class SavingsTimeline(BaseModel):
    period: str
    savings_usd: Decimal
    baseline_cost_usd: Decimal
    actual_cost_usd: Decimal


class SavingsResponse(BaseModel):
    total_savings_usd: Decimal
    total_baseline_usd: Decimal
    total_actual_usd: Decimal
    savings_rate_pct: Decimal | None
    by_category: list[SavingsByCategory]
    timeline: list[SavingsTimeline]


# ── Phase 3: Optimization opportunities ─────────────────────────────────────


class OptimizationOpportunity(BaseModel):
    optimization_type: str
    potential_savings_usd: Decimal
    affected_calls: int
    description: str


class OptimizationOpportunitiesResponse(BaseModel):
    items: list[OptimizationOpportunity]
    total_potential_savings_usd: Decimal


# ── Phase 3: Trends ─────────────────────────────────────────────────────────


class TrendPoint(BaseModel):
    period: str
    cost_usd: Decimal
    run_count: int
    call_count: int
    tokens: int
    avg_latency_ms: Decimal | None
    savings_usd: Decimal


class TrendMetric(BaseModel):
    name: str
    current: Decimal
    previous: Decimal
    change_pct: Decimal | None


class TrendsResponse(BaseModel):
    points: list[TrendPoint]
    metrics: list[TrendMetric]
    granularity: str


# ── Phase 3: Request explorer ────────────────────────────────────────────────


class RequestRecord(BaseModel):
    id: str
    run_id: str
    provider: str
    model: str
    intent: str | None
    end_user_id: str | None
    cost_usd: Decimal | None
    baseline_cost_usd: Decimal | None
    savings_usd: Decimal | None
    optimization_applied: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    status: str
    created_at: str


class RequestExplorerResponse(BaseModel):
    items: list[RequestRecord]
    total: int
    page: int
    page_size: int


# ── Phase 8: Engineering metrics ─────────────────────────────────────────────


class CostByDimension(BaseModel):
    name: str
    cost_usd: Decimal
    call_count: int


class QualityFunnel(BaseModel):
    total_requests: int
    successful: int
    routed: int
    cached: int
    with_outcome: int
    positive_outcome: int


class LifecycleStage(BaseModel):
    stage: str
    count: int
    pct: Decimal


class EngineeringMetrics(BaseModel):
    avg_latency_ms: Decimal | None
    p95_latency_ms: Decimal | None
    error_pct: Decimal
    retry_pct: Decimal
    cache_pct: Decimal
    total_requests: int
    total_tokens: int
    avg_cost_per_request: Decimal | None
    cost_by_feature: list[CostByDimension]
    cost_by_model: list[CostByDimension]
    cost_by_tool: list[CostByDimension]
    quality_funnel: QualityFunnel
    lifecycle_stages: list[LifecycleStage]


# ── Optimization Simulator ────────────────────────────────────────────────────


class SimulationRequest(BaseModel):
    intent: str | None = None
    current_model: str | None = None
    proposed_model: str | None = None
    current_provider: str | None = None
    proposed_provider: str | None = None
    enable_cache: bool = False
    enable_compression: bool = False
    workspace_id: str | None = None
    from_dt: datetime | None = None
    to_dt: datetime | None = None


class SimulationImpact(BaseModel):
    label: str
    current_value: str
    projected_value: str
    delta_pct: Decimal | None


class ModelScorecard(BaseModel):
    model: str
    provider: str | None = None
    total_cost_usd: Decimal
    call_count: int
    avg_cost_per_call: Decimal
    avg_latency_ms: Decimal | None
    p95_latency_ms: Decimal | None
    error_rate: Decimal
    cache_hit_rate: Decimal | None
    avg_quality_score: Decimal | None
    input_tokens: int
    output_tokens: int


class ModelScorecardList(BaseModel):
    items: list[ModelScorecard]
    from_dt: datetime | None = None
    to_dt: datetime | None = None


class SimulationResult(BaseModel):
    affected_requests: int
    current_cost_usd: Decimal
    projected_cost_usd: Decimal
    projected_savings_usd: Decimal
    savings_pct: Decimal
    current_avg_latency_ms: Decimal | None
    projected_latency_ms: Decimal | None
    latency_delta_pct: Decimal | None
    quality_risk: str
    confidence: str
    impacts: list[SimulationImpact]
    description: str
