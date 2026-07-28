"""Pydantic schemas for the Model Gateway endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

# ── Route schemas ──────────────────────────────────────────────────────────────


class GatewayRouteCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=128, description="Model alias clients use")
    provider: str = Field(
        ...,
        pattern="^(openai|anthropic|ollama|vllm|local|groq|mistral|azure|bedrock|vertex|custom)$",
    )
    target_model: str = Field(..., min_length=1, max_length=128)
    base_url: str | None = None
    api_key_env_var: str | None = None
    priority: int = Field(10, ge=1, le=100)
    config: dict[str, Any] | None = None
    # Phase 30 runtime controls
    daily_cost_limit_usd: Decimal | None = None
    monthly_cost_limit_usd: Decimal | None = None
    pii_redaction_enabled: bool = False
    semantic_cache_enabled: bool = False
    context_compiler_enabled: bool = False
    context_compiler_config: dict[str, Any] | None = None
    per_user_rpm_limit: int | None = Field(None, ge=1)
    health_auto_disable: bool = True


class GatewayRouteUpdate(BaseModel):
    alias: str | None = None
    target_model: str | None = None
    base_url: str | None = None
    api_key_env_var: str | None = None
    priority: int | None = Field(None, ge=1, le=100)
    is_active: bool | None = None
    config: dict[str, Any] | None = None
    # Phase 30 runtime controls
    daily_cost_limit_usd: Decimal | None = None
    monthly_cost_limit_usd: Decimal | None = None
    pii_redaction_enabled: bool | None = None
    semantic_cache_enabled: bool | None = None
    context_compiler_enabled: bool | None = None
    context_compiler_config: dict[str, Any] | None = None
    per_user_rpm_limit: int | None = Field(None, ge=1)
    health_auto_disable: bool | None = None


class GatewayRouteResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    alias: str
    provider: str
    target_model: str
    base_url: str | None
    api_key_env_var: str | None
    priority: int
    is_active: bool
    config: dict[str, Any] | None = None
    # Phase 30 runtime controls
    daily_cost_limit_usd: Decimal | None = None
    monthly_cost_limit_usd: Decimal | None = None
    pii_redaction_enabled: bool = False
    semantic_cache_enabled: bool = False
    context_compiler_enabled: bool = False
    context_compiler_config: dict[str, Any] | None = None
    per_user_rpm_limit: int | None = None
    health_auto_disable: bool = True
    last_health_check_at: datetime | None = None
    consecutive_health_failures: int = 0
    disabled_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GatewayRouteList(BaseModel):
    items: list[GatewayRouteResponse]


# ── Completion request / response ──────────────────────────────────────────────


class GatewayMessage(BaseModel):
    role: str
    content: str | list[Any]  # str for text; list for multimodal content parts


class GatewayCompletionRequest(BaseModel):
    model: str = Field(..., description="Alias or model name to route")
    messages: list[GatewayMessage]
    # Core sampling params
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    # Determinism / output control
    seed: int | None = None
    stop: str | list[str] | None = None
    response_format: dict[str, Any] | None = None
    # Tool / function calling
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    # Gateway-specific
    stream: bool = False
    cache: bool = Field(True, description="Enable prompt cache lookup for this request")
    semantic_cache: bool = Field(
        False,
        description="Enable semantic (near-duplicate) cache lookup via semantic-cache-svc. "
        "Default off; fail-open (skipped if the service is unavailable).",
    )
    context_compiler: bool = Field(
        False,
        description="Run the Context Compiler on this request (dedup / tool-output compression / "
        "rerank / compaction) before routing. Default off; fail-open.",
    )


# ── Stats schema ───────────────────────────────────────────────────────────────


class GatewayRouteStats(BaseModel):
    route_id: uuid.UUID | None
    alias: str
    total_requests: int
    cache_hits: int
    cache_hit_rate: Decimal
    avg_latency_ms: Decimal | None
    error_count: int


class GatewayStats(BaseModel):
    total_requests: int
    cache_hits: int
    cache_hit_rate: Decimal
    avg_latency_ms: Decimal | None
    routes: list[GatewayRouteStats]


# ── Request log schema ─────────────────────────────────────────────────────────


class GatewayRequestResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    route_id: uuid.UUID | None
    model_requested: str
    model_used: str | None
    cache_hit: bool
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    status: str
    decision_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GatewayRequestList(BaseModel):
    items: list[GatewayRequestResponse]
    total: int


# ── Routing policy schemas ─────────────────────────────────────────────────────

VALID_POLICY_TYPES = {
    "manual",
    "cost_optimized",
    "latency_optimized",
    "quality_optimized",
    "weighted",
    "canary",
    "budget_aware",
    "complexity_based",
    "outcome_optimized",
}


class RoutingPolicyCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=128)
    policy_type: str = Field("manual", description="Strategy for route selection")
    config: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:  # noqa: ANN401
        if self.policy_type not in VALID_POLICY_TYPES:
            raise ValueError(f"policy_type must be one of {sorted(VALID_POLICY_TYPES)}")


class RoutingPolicyUpdate(BaseModel):
    policy_type: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class RoutingPolicyResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    alias: str
    policy_type: str
    config: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoutingPolicyList(BaseModel):
    items: list[RoutingPolicyResponse]


# ── Routing recommendation schemas ─────────────────────────────────────────────


class RoutingRecommendationModel(BaseModel):
    """Per-model outcome stats for the recommendation response."""

    model: str
    route_id: uuid.UUID | None
    sample_count: int
    success_rate: float
    cost_per_success: float | None
    # Relative improvement vs the current top-priority route (positive = cheaper per success)
    improvement_vs_current: float | None


class RoutingRecommendationResponse(BaseModel):
    """
    Outcome-based routing recommendation for an alias.

    Aggregates outcome success/cost data per model over the last ``window_days``
    and surfaces which route delivers the best cost-per-success.
    """

    alias: str
    window_days: int
    workflow_type: str | None
    total_outcomes_sampled: int
    models: list[RoutingRecommendationModel]
    # Model name + route_id for the recommended (lowest cost-per-success) option
    best_model: str | None
    recommended_route_id: uuid.UUID | None
    # Human-readable summary, e.g. "gpt-4o-mini has a 12% better cost-per-success than gpt-4o"
    message: str
