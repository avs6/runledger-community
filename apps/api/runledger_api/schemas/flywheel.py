"""Pydantic schemas for the optimization flywheel (Phase 7)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FlywheelSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    apply_mode: str
    quality_metric: dict[str, Any]
    min_quality: Decimal
    segment_by: str
    action_space: list[str]
    min_sample_size: int
    lookback_days: int
    updated_at: datetime


class FlywheelSettingsUpdate(BaseModel):
    enabled: bool | None = None
    apply_mode: str | None = Field(default=None, description="approval | auto | off")
    quality_metric: dict[str, Any] | None = None
    min_quality: Decimal | None = None
    segment_by: str | None = Field(default=None, description="outcome_type | task_class | alias")
    action_space: list[str] | None = None
    min_sample_size: int | None = None
    lookback_days: int | None = None


class FlywheelRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    segment_by: str
    segment_key: str
    kind: str
    current_config: dict[str, Any]
    proposed_config: dict[str, Any]
    est_cost_delta_pct: Decimal | None
    est_cost_delta_per_req: Decimal | None
    current_quality: Decimal | None
    proposed_quality: Decimal | None
    min_quality: Decimal
    sample_size: int
    confidence: str
    rationale: str | None
    status: str
    apply_mode: str
    applied_route_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    applied_at: datetime | None


class FlywheelRecommendationList(BaseModel):
    items: list[FlywheelRecommendationResponse]
    total: int


class FlywheelRunResponse(BaseModel):
    status: str
    recommendations: int
    auto_applied: int = 0
