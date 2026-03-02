"""Pydantic schemas for quality score events and analytics."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ScoreCreate(BaseModel):
    run_id: uuid.UUID | None = None
    span_id: uuid.UUID | None = None
    session_id: str | None = None
    end_user_id: str | None = None
    name: str
    value: Decimal = Field(..., ge=0, le=100)
    label: str | None = None
    source: str = Field("human", pattern="^(human|llm|rule|telemetry)$")
    confidence: Decimal | None = Field(None, ge=0, le=1)
    evidence: dict[str, Any] | None = None


class ScoreResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    run_id: uuid.UUID | None
    span_id: uuid.UUID | None
    session_id: str | None
    end_user_id: str | None
    name: str
    value: Decimal
    label: str | None
    source: str
    confidence: Decimal | None
    evidence: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScoreList(BaseModel):
    items: list[ScoreResponse]


class ScoreSummaryItem(BaseModel):
    name: str
    avg_value: Decimal
    p50: Decimal | None
    p90: Decimal | None
    sample_count: int
    prev_avg_value: Decimal | None
    change_pct: Decimal | None  # None when prior has 0 samples


class ScoreSummary(BaseModel):
    items: list[ScoreSummaryItem]


class ScoreRegressionItem(BaseModel):
    name: str
    current_avg: Decimal
    prior_avg: Decimal
    change_pct: Decimal  # negative = degradation
    sample_count: int
