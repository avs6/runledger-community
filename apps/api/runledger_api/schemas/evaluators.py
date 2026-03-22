"""Pydantic schemas for evaluator CRUD and run results."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvaluatorCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    type: str = Field("rule", pattern="^(llm_judge|rule)$")
    config: dict[str, Any] = Field(default_factory=dict)


class EvaluatorUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    config: dict[str, Any] | None = None
    status: str | None = Field(None, pattern="^(active|inactive)$")


class EvaluatorResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    type: str
    config: dict[str, Any]
    status: str
    last_run_at: datetime | None
    last_run_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluatorList(BaseModel):
    items: list[EvaluatorResponse]


class EvaluatorRunRequest(BaseModel):
    """Trigger a batch evaluation run for specific runs."""
    run_ids: list[uuid.UUID] | None = None   # None = evaluate all recent runs
    limit: int = Field(100, ge=1, le=1000)


class EvaluatorRunResult(BaseModel):
    evaluator_id: uuid.UUID
    evaluated: int
    scores_created: int
    errors: int


# ── Cost-quality analytics ────────────────────────────────────────────────────

class CostQualityPoint(BaseModel):
    model: str
    avg_cost_usd: str
    avg_score: str | None
    run_count: int


class CostQualityResponse(BaseModel):
    items: list[CostQualityPoint]


class BestValueModel(BaseModel):
    model: str
    avg_cost_usd: str
    avg_score: str
    value_score: str   # avg_score / avg_cost_usd (normalised)
    run_count: int


class BestValueResponse(BaseModel):
    items: list[BestValueModel]


# ── Judge drift ───────────────────────────────────────────────────────────────

class JudgeDriftItem(BaseModel):
    evaluator_id: uuid.UUID
    evaluator_name: str
    current_avg: str
    prior_avg: str
    change_pct: str   # positive = improved, negative = degraded


class JudgeDriftResponse(BaseModel):
    items: list[JudgeDriftItem]
