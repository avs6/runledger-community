"""Pydantic schemas for the ML intelligence layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

# ── Anomaly schemas ─────────────────────────────────────────────────────

AnomalyType = Literal[
    "cost_spike", "latency_regression", "error_rate_spike",
    "token_spike", "cache_hit_drop",
]

AnomalySeverity = Literal["low", "medium", "high", "critical"]

DetectionMethod = Literal["zscore", "ewma", "stl", "isolation_forest"]


class AnomalyResponse(BaseModel):
    id: str
    workspace_id: str
    anomaly_type: str
    dimension: str
    dimension_key: str | None
    detected_at: datetime
    severity: str
    detection_method: str
    current_value: str
    expected_value: str
    deviation_score: str
    context: dict[str, Any]
    is_suppressed: bool
    suppressed_reason: str | None
    correlation_group_id: str | None = None
    acknowledged_at: datetime | None
    created_at: datetime


class AnomalyList(BaseModel):
    items: list[AnomalyResponse]
    total: int


class AnomalySummary(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    suppressed: int
    acknowledged: int


class CorrelatedAnomalyGroup(BaseModel):
    correlation_group_id: str
    dimensions: list[str]
    max_severity: str
    anomalies: list[AnomalyResponse]
    detected_at: datetime


class CorrelatedGroupList(BaseModel):
    items: list[CorrelatedAnomalyGroup]
    total: int


class AnomalyAcknowledge(BaseModel):
    acknowledged: bool


# ── Forecast schemas ────────────────────────────────────────────────────

ForecastMethod = Literal["linear", "holt_winters"]


class ForecastPoint(BaseModel):
    date: str
    predicted: float
    lower: float
    upper: float


class BudgetOverlay(BaseModel):
    budget_limit: str | None
    projected_spend: float
    days_to_exhaustion: int | None
    exhaustion_date: str | None
    breach_probability: float | None


class ForecastResponse(BaseModel):
    id: str
    workspace_id: str
    forecast_type: str
    dimension_key: str | None
    method: str
    horizon_days: int
    forecast_from: str
    points: list[ForecastPoint]
    accuracy_metrics: dict[str, Any]
    budget_overlay: BudgetOverlay | None = None
    created_at: datetime


class ForecastList(BaseModel):
    items: list[ForecastResponse]


class ForecastGenerateRequest(BaseModel):
    forecast_type: str = "cost_daily"
    horizon_days: int = 14
    dimension_key: str | None = None


# ── Top-K schemas ───────────────────────────────────────────────────────

TopKDimension = Literal["model", "user", "intent", "feature_tag", "provider"]
TopKMetric = Literal["cost", "tokens", "call_count", "latency_p95", "error_rate"]


class TopKItem(BaseModel):
    rank: int
    key: str
    current_value: float
    previous_value: float | None
    rank_change: int | None
    pct_change: float | None


class TopKChange(BaseModel):
    key: str
    change_type: str  # new_entrant, exited, rank_up, rank_down, magnitude_spike
    detail: str


class TopKResponse(BaseModel):
    dimension: str
    metric: str
    k: int
    period: dict[str, str]
    items: list[TopKItem]
    significant_changes: list[TopKChange]


# ── Pattern schemas ─────────────────────────────────────────────────────

PatternType = Literal["steady", "growing", "declining", "spiky", "seasonal", "one_shot"]


class PatternResponse(BaseModel):
    id: str
    workspace_id: str
    dimension: str
    dimension_key: str | None
    pattern: str
    confidence: str
    evidence: dict[str, Any]
    detected_at: datetime


class PatternList(BaseModel):
    items: list[PatternResponse]


# ── Complexity scoring schemas ──────────────────────────────────────────

class ComplexityScore(BaseModel):
    run_id: str
    score: float
    predicted_cost: float
    actual_cost: float
    complexity_tier: str  # simple, medium, complex, reasoning


class ComplexityScoreList(BaseModel):
    items: list[ComplexityScore]
    distribution: dict[str, int]


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class FeatureImportanceList(BaseModel):
    items: list[FeatureImportance]
    model_version: int
    trained_at: datetime | None
    sample_count: int


# ── Cost-per-outcome schemas ───────────────────────────────────────────

class CostPerOutcome(BaseModel):
    outcome_type: str
    total_cost: float
    outcome_count: int
    cost_per_outcome: float
    avg_quality_score: float | None
    model: str | None


class ParetoPoint(BaseModel):
    key: str  # model or route name
    cost: float
    quality: float
    is_optimal: bool


class CostOutcomeResponse(BaseModel):
    items: list[CostPerOutcome]
    pareto_frontier: list[ParetoPoint]


# ── Adaptive alert schemas ─────────────────────────────────────────────

class AdaptiveThresholdSuggestion(BaseModel):
    rule_id: str
    rule_name: str
    metric: str
    current_threshold: str
    suggested_upper: float
    suggested_lower: float
    baseline: float
    confidence: float


class AdaptiveThresholdList(BaseModel):
    items: list[AdaptiveThresholdSuggestion]


# ── ML dashboard / observability schemas ───────────────────────────────

class ModelHealth(BaseModel):
    id: str
    model_type: str
    dimension: str
    dimension_key: str | None
    version: int
    trained_at: datetime | None
    sample_count: int
    staleness_hours: float
    metrics: dict[str, Any]
    status: str  # healthy, stale, degraded


class MLDashboard(BaseModel):
    models: list[ModelHealth]
    anomaly_summary: AnomalySummary
    total_forecasts: int
    total_patterns: int
    last_anomaly_run: datetime | None
    last_forecast_run: datetime | None
