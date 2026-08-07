"""Pydantic schemas for the Model Gateway endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

# ── Route schemas ──────────────────────────────────────────────────────────────


VALID_ROUTING_GROUP_STRATEGIES = {
    "manual",
    "latency_optimized",
    "round_robin",
}


class GatewayRoutingGroupCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    match_tags: list[str] = Field(default_factory=list)
    default_tags: list[str] = Field(default_factory=list)
    strategy_type: str = Field("manual")
    strategy_config: dict[str, Any] | None = None
    is_active: bool = True

    def model_post_init(self, __context: Any) -> None:  # noqa: ANN401
        if self.strategy_type not in VALID_ROUTING_GROUP_STRATEGIES:
            raise ValueError(
                f"strategy_type must be one of {sorted(VALID_ROUTING_GROUP_STRATEGIES)}"
            )


class GatewayRoutingGroupUpdate(BaseModel):
    alias: str | None = None
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = None
    match_tags: list[str] | None = None
    default_tags: list[str] | None = None
    strategy_type: str | None = None
    strategy_config: dict[str, Any] | None = None
    is_active: bool | None = None

    def model_post_init(self, __context: Any) -> None:  # noqa: ANN401
        if self.strategy_type is not None and self.strategy_type not in VALID_ROUTING_GROUP_STRATEGIES:
            raise ValueError(
                f"strategy_type must be one of {sorted(VALID_ROUTING_GROUP_STRATEGIES)}"
            )


class GatewayRoutingGroupRouteSummary(BaseModel):
    id: uuid.UUID
    alias: str
    provider: str
    target_model: str
    priority: int
    region: str | None = None
    required_tags: list[str] = Field(default_factory=list)
    excluded_tags: list[str] = Field(default_factory=list)
    is_active: bool

    model_config = {"from_attributes": True}


class GatewayRoutingGroupResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    alias: str
    name: str
    description: str | None = None
    match_tags: list[str] = Field(default_factory=list)
    default_tags: list[str] = Field(default_factory=list)
    strategy_type: str = "manual"
    strategy_config: dict[str, Any] | None = None
    is_active: bool
    route_count: int = 0
    routes: list[GatewayRoutingGroupRouteSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GatewayRoutingGroupList(BaseModel):
    items: list[GatewayRoutingGroupResponse]


class GatewayRoutingStrategyComparisonItem(BaseModel):
    routing_group_id: uuid.UUID | None
    alias: str
    group_name: str
    strategy_type: str
    total_requests: int
    cache_hit_rate: Decimal
    avg_latency_ms: Decimal | None
    error_rate: Decimal
    active_routes: int
    default_tags: list[str] = Field(default_factory=list)
    match_tags: list[str] = Field(default_factory=list)


class GatewayRoutingStrategyComparison(BaseModel):
    items: list[GatewayRoutingStrategyComparisonItem]


class GatewayRouteCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=128, description="Model alias clients use")
    routing_group_id: uuid.UUID | None = None
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
    intelligent_routing_enabled: bool = False
    routing_config: dict[str, Any] | None = None
    per_user_rpm_limit: int | None = Field(None, ge=1)
    fallback_config: dict[str, Any] | None = None
    required_tags: list[str] = Field(default_factory=list)
    excluded_tags: list[str] = Field(default_factory=list)
    retry_count: int = Field(1, ge=0, le=5)
    timeout_ms: int | None = Field(None, ge=1000, le=300000)
    cooldown_seconds: int = Field(0, ge=0, le=3600)
    region: str | None = None
    mirror_config: dict[str, Any] | None = None
    health_auto_disable: bool = True


class GatewayRouteUpdate(BaseModel):
    alias: str | None = None
    routing_group_id: uuid.UUID | None = None
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
    intelligent_routing_enabled: bool | None = None
    routing_config: dict[str, Any] | None = None
    per_user_rpm_limit: int | None = Field(None, ge=1)
    fallback_config: dict[str, Any] | None = None
    required_tags: list[str] | None = None
    excluded_tags: list[str] | None = None
    retry_count: int | None = Field(None, ge=0, le=5)
    timeout_ms: int | None = Field(None, ge=1000, le=300000)
    cooldown_seconds: int | None = Field(None, ge=0, le=3600)
    region: str | None = None
    mirror_config: dict[str, Any] | None = None
    health_auto_disable: bool | None = None


class GatewayRouteResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    routing_group_id: uuid.UUID | None = None
    alias: str
    routing_group_name: str | None = None
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
    intelligent_routing_enabled: bool = False
    routing_config: dict[str, Any] | None = None
    per_user_rpm_limit: int | None = None
    fallback_config: dict[str, Any] | None = None
    required_tags: list[str] = Field(default_factory=list)
    excluded_tags: list[str] = Field(default_factory=list)
    retry_count: int = 1
    timeout_ms: int | None = None
    cooldown_seconds: int = 0
    cooldown_until: datetime | None = None
    region: str | None = None
    mirror_config: dict[str, Any] | None = None
    health_auto_disable: bool = True
    last_health_check_at: datetime | None = None
    consecutive_health_failures: int = 0
    disabled_reason: str | None = None
    deployment_status: str = "unknown"
    health_summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GatewayRouteList(BaseModel):
    items: list[GatewayRouteResponse]


class GatewayDeploymentHealthItem(BaseModel):
    route_id: uuid.UUID
    alias: str
    provider: str
    target_model: str
    deployment_status: str
    health_summary: str | None = None
    last_health_check_at: datetime | None = None
    consecutive_health_failures: int = 0


class GatewayDeploymentHealthList(BaseModel):
    items: list[GatewayDeploymentHealthItem]


# ── Completion request / response ──────────────────────────────────────────────


class GatewayMessage(BaseModel):
    role: str
    content: str | list[Any]  # str for text; list for multimodal content parts


class GatewayCompletionRequest(BaseModel):
    model: str = Field(..., description="Alias or model name to route")
    messages: list[GatewayMessage]
    metadata: dict[str, Any] | None = None
    fallback_aliases: list[str] | None = None
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
    intelligent_routing: bool = Field(
        False,
        description="Classify this request (complexity × risk) and route it to a model tier. "
        "Default off; fail-open to the requested alias.",
    )
    reasoning_effort: str | None = Field(
        None,
        description="Override reasoning effort (low|medium|high) passed to reasoning models.",
    )
    guardrails: list[str] | None = Field(
        None,
        description="Optional list of guardrail rule IDs to run. If omitted, all active guardrails run.",
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


class GatewayPassThroughEndpointCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=80)
    path_prefix: str = "/"
    upstream_base_url: str
    auth_type: str | None = None
    auth_config: dict[str, Any] = Field(default_factory=dict)
    header_config: dict[str, Any] = Field(default_factory=dict)
    default_query: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = Field(30000, ge=1000, le=300000)
    rate_limit_rpm: int | None = Field(None, ge=1)
    cost_per_call_usd: Decimal | None = None
    is_active: bool = True


class GatewayPassThroughEndpointUpdate(BaseModel):
    path_prefix: str | None = None
    upstream_base_url: str | None = None
    auth_type: str | None = None
    auth_config: dict[str, Any] | None = None
    header_config: dict[str, Any] | None = None
    default_query: dict[str, Any] | None = None
    timeout_ms: int | None = Field(None, ge=1000, le=300000)
    rate_limit_rpm: int | None = Field(None, ge=1)
    cost_per_call_usd: Decimal | None = None
    is_active: bool | None = None


class GatewayPassThroughEndpointResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    slug: str
    path_prefix: str
    upstream_base_url: str
    auth_type: str | None = None
    auth_config: dict[str, Any] = Field(default_factory=dict)
    header_config: dict[str, Any] = Field(default_factory=dict)
    default_query: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int
    rate_limit_rpm: int | None = None
    cost_per_call_usd: Decimal | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class GatewayPassThroughEndpointList(BaseModel):
    items: list[GatewayPassThroughEndpointResponse]


class GatewayPassThroughTestRequest(BaseModel):
    method: str = Field("GET", min_length=3, max_length=16)
    path: str | None = None
    query: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body_json: dict[str, Any] | None = None


class GatewayPassThroughTestResponse(BaseModel):
    ok: bool
    status_code: int
    latency_ms: int
    target_url: str
    response_preview: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class GatewayPassThroughEndpointStats(BaseModel):
    endpoint_id: uuid.UUID
    slug: str
    total_requests: int
    success_count: int
    error_count: int
    avg_latency_ms: Decimal | None = None
    p50_latency_ms: Decimal | None = None
    p95_latency_ms: Decimal | None = None
    p99_latency_ms: Decimal | None = None
    last_hour_requests: int
    rate_limit_rpm: int | None = None
    rate_limit_utilization_pct: Decimal | None = None
    estimated_total_cost_usd: Decimal | None = None
    estimated_24h_cost_usd: Decimal | None = None


class GatewayPassThroughEndpointStatsList(BaseModel):
    items: list[GatewayPassThroughEndpointStats]


class GatewayBenchmarkComparisonItem(BaseModel):
    alias: str
    request_count: int
    throughput_rpm: Decimal
    p50_gateway_overhead_ms: Decimal | None = None
    p95_gateway_overhead_ms: Decimal | None = None
    p99_gateway_overhead_ms: Decimal | None = None
    avg_provider_latency_ms: Decimal | None = None
    avg_end_to_end_latency_ms: Decimal | None = None
    avg_gateway_overhead_ms: Decimal | None = None
    overhead_vs_provider_pct: Decimal | None = None


class GatewayBenchmarkComparisonList(BaseModel):
    items: list[GatewayBenchmarkComparisonItem]


# ── Routing policy schemas ─────────────────────────────────────────────────────

VALID_POLICY_TYPES = {
    "manual",
    "cost_optimized",
    "latency_optimized",
    "quality_optimized",
    "weighted",
    "canary",
    "ab_test",
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


class RoutingPolicyVariantMetrics(BaseModel):
    route_id: uuid.UUID
    label: str
    allocation_pct: Decimal
    total_requests: int
    success_rate: Decimal
    error_rate: Decimal
    avg_latency_ms: Decimal | None = None
    avg_input_tokens: Decimal | None = None
    avg_output_tokens: Decimal | None = None


class RoutingPolicyAnalysisResponse(BaseModel):
    policy_id: uuid.UUID
    alias: str
    policy_type: str
    winner_route_id: uuid.UUID | None = None
    winner_label: str | None = None
    confidence: str = "insufficient_data"
    significance_p_value: Decimal | None = None
    auto_promoted: bool = False
    summary: str
    variants: list[RoutingPolicyVariantMetrics]


class RoutingPolicyPromotionRequest(BaseModel):
    route_id: uuid.UUID | None = None


class RoutingPolicyActionResponse(BaseModel):
    policy_id: uuid.UUID
    policy_type: str
    summary: str
    config: dict[str, Any]


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
