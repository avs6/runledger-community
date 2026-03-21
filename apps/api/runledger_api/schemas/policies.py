"""Schemas for unified policy checks (budgets + tools + gateway + eval gates)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class ScoreGateRequest(BaseModel):
    name: str
    min_value: Decimal = Field(..., ge=0, le=100)
    source: str | None = Field(None, pattern="^(human|llm|rule|telemetry)$")
    run_id: uuid.UUID | None = None


class PolicyCheckRequest(BaseModel):
    end_user_id: str | None = None
    feature_tag: str | None = None
    tool_name: str | None = None
    model_alias: str | None = None
    score_gate: ScoreGateRequest | None = None


class PolicyCheckResponse(BaseModel):
    allowed: bool
    decision: str = Field(..., pattern="^(allow|downgrade|block)$")
    reasons: list[str] = Field(default_factory=list)
    budget_action: str | None = None
    budget_id: str | None = None
    downgrade_model: str | None = None
    tool_policy: str | None = None
    gateway_route_available: bool | None = None
    score_gate_passed: bool | None = None
