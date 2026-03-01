"""
Pydantic schemas for the unit-economics and change-impact API (Phase 9).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

# ── Per-run economics ─────────────────────────────────────────────────────────


class SpanTypeCost(BaseModel):
    span_type: str
    cost_usd: Decimal


class ModelCost(BaseModel):
    model: str
    provider: str
    cost_usd: Decimal
    call_count: int


class RunEconomics(BaseModel):
    run_id: str
    total_cost_usd: Decimal
    cost_by_span_type: list[SpanTypeCost]
    cost_by_model: list[ModelCost]
    retry_cost: Decimal  # cost of child LLM spans (parent_span_id IS NOT NULL, span_type='llm')


# ── Workflow rankings ──────────────────────────────────────────────────────────


class WorkflowSummary(BaseModel):
    feature_tag: str | None
    application_id: str | None
    run_count: int
    avg_cost_usd: Decimal
    p95_cost_usd: Decimal
    total_cost_usd: Decimal
    call_count: int


class WorkflowTopList(BaseModel):
    metric: str
    items: list[WorkflowSummary]


# ── Version comparison ────────────────────────────────────────────────────────


class SpanTypeDelta(BaseModel):
    span_type: str
    baseline_cost: Decimal
    comparison_cost: Decimal
    delta_pct: Decimal | None


class VersionSummary(BaseModel):
    version: str
    run_count: int
    avg_cost_usd: Decimal
    avg_input_tokens: Decimal
    avg_output_tokens: Decimal
    avg_latency_ms: Decimal | None


class VersionCompareResult(BaseModel):
    baseline: VersionSummary
    comparison: VersionSummary
    cost_delta_pct: Decimal | None
    token_delta_pct: Decimal | None
    latency_delta_pct: Decimal | None
    by_span_type: list[SpanTypeDelta]


# ── Regression detection ──────────────────────────────────────────────────────


class RegressionItem(BaseModel):
    feature_tag: str | None
    current_avg_cost: Decimal
    prior_avg_cost: Decimal
    change_pct: Decimal
    run_count: int
    prior_run_count: int


class RegressionList(BaseModel):
    items: list[RegressionItem]
    from_dt: str
    to_dt: str


# ── Annotations ───────────────────────────────────────────────────────────────


class AnnotationCreate(BaseModel):
    note: str
    annotation_date: date
    version: str | None = None


class AnnotationResponse(BaseModel):
    id: str
    note: str
    annotation_date: date
    version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnotationList(BaseModel):
    items: list[AnnotationResponse]
