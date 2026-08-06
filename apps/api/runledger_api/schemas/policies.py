"""Schemas for unified policy checks (budgets + tools + gateway + eval gates)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

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
    dry_run: bool = False


class PolicyDryRunDetail(BaseModel):
    budget_remaining_usd: Decimal | None = None
    budget_limit_usd: Decimal | None = None
    budget_period: str | None = None
    tool_registered: bool | None = None
    tool_policy_setting: str | None = None
    gateway_routes_found: int | None = None
    gateway_route_aliases: list[str] | None = None
    score_latest_value: Decimal | None = None
    score_gate_threshold: Decimal | None = None


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
    detail: PolicyDryRunDetail | None = None


class FinopsSimulationRequest(BaseModel):
    intent: str | None = None
    current_model: str | None = None
    proposed_model: str | None = None
    current_provider: str | None = None
    proposed_provider: str | None = None
    enable_cache: bool = False
    enable_compression: bool = False
    from_dt: datetime | None = None
    to_dt: datetime | None = None
    end_user_id: str | None = None
    feature_tag: str | None = None
    tool_name: str | None = None
    model_alias: str | None = None


class SimulationImpact(BaseModel):
    label: str
    current_value: str
    projected_value: str
    delta_pct: Decimal | None


class FinopsSimulationResponse(BaseModel):
    policy: PolicyCheckResponse
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


class ToolCostBreakdownItem(BaseModel):
    source: Literal["mcp_tracked", "search_tool_estimated", "unpriced_tool_activity"]
    tool_name: str
    classification: str
    call_count: int
    total_cost_usd: Decimal
    avg_cost_usd: Decimal | None = None


class ToolCostAccountingResponse(BaseModel):
    items: list[ToolCostBreakdownItem]
    total_calls: int
    tracked_calls: int
    estimated_calls: int
    total_cost_usd: Decimal
