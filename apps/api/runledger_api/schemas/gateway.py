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


class GatewayRuntimeAuthKeySnapshot(BaseModel):
    api_key_id: uuid.UUID
    workspace_id: uuid.UUID
    key_prefix: str
    key_hash: str
    name: str | None = None
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    is_session: bool = False
    is_active: bool = True
    ownership_type: str
    owner_reference: str | None = None
    budget_tier_id: uuid.UUID | None = None
    guardrail_config: dict[str, Any] = Field(default_factory=dict)


class GatewayRuntimeAuthSnapshot(BaseModel):
    mode: str
    api_keys: list[GatewayRuntimeAuthKeySnapshot] = Field(default_factory=list)


class GatewayRuntimeWorkspaceSnapshot(BaseModel):
    workspace_id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    status: str
    is_restricted: bool = False
    guardrail_bypass: bool = False


class GatewayRuntimeRoutingGroupSnapshot(BaseModel):
    routing_group_id: uuid.UUID
    workspace_id: uuid.UUID
    alias: str
    name: str
    description: str | None = None
    match_tags: list[str] = Field(default_factory=list)
    default_tags: list[str] = Field(default_factory=list)
    strategy_type: str
    strategy_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class GatewayRuntimeRouteControlsSnapshot(BaseModel):
    daily_cost_limit_usd: Decimal | None = None
    monthly_cost_limit_usd: Decimal | None = None
    per_user_rpm_limit: int | None = None
    pii_redaction_enabled: bool = False


class GatewayRuntimeRouteSnapshot(BaseModel):
    route_id: uuid.UUID
    workspace_id: uuid.UUID
    routing_group_id: uuid.UUID | None = None
    alias: str
    provider: str
    target_model: str
    base_url: str | None = None
    api_key_env_var: str | None = None
    priority: int
    config: dict[str, Any] = Field(default_factory=dict)
    required_tags: list[str] = Field(default_factory=list)
    excluded_tags: list[str] = Field(default_factory=list)
    region: str | None = None
    retry_count: int
    timeout_ms: int | None = None
    cooldown_seconds: int
    cooldown_until: datetime | None = None
    mirror_config: dict[str, Any] = Field(default_factory=dict)
    fallback_config: dict[str, Any] = Field(default_factory=dict)
    semantic_cache_enabled: bool = False
    context_compiler_enabled: bool = False
    context_compiler_config: dict[str, Any] = Field(default_factory=dict)
    intelligent_routing_enabled: bool = False
    routing_config: dict[str, Any] = Field(default_factory=dict)
    health_auto_disable: bool = True
    deployment_status: str
    health_summary: str | None = None
    runtime_controls: GatewayRuntimeRouteControlsSnapshot
    created_at: datetime
    last_health_check_at: datetime | None = None


class GatewayRuntimePolicySnapshot(BaseModel):
    policy_id: uuid.UUID
    workspace_id: uuid.UUID
    alias: str
    policy_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class GatewayRuntimeSnapshotResponse(BaseModel):
    version: str
    published_at: datetime
    last_config_change_at: datetime
    workspace: GatewayRuntimeWorkspaceSnapshot
    auth: GatewayRuntimeAuthSnapshot
    routing_groups: list[GatewayRuntimeRoutingGroupSnapshot] = Field(default_factory=list)
    routes: list[GatewayRuntimeRouteSnapshot] = Field(default_factory=list)
    routing_policies: list[GatewayRuntimePolicySnapshot] = Field(default_factory=list)


class GatewayRuntimeEvent(BaseModel):
    event_type: str
    request_id: uuid.UUID | None = None
    workspace_id: uuid.UUID
    route_id: uuid.UUID | None = None
    model_requested: str | None = None
    model_used: str | None = None
    provider: str | None = None
    status: str | None = None
    decision_reason: str | None = None
    cache_hit: bool | None = None
    semantic_cache_hit: bool | None = None
    stream: bool | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: Decimal | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    action: str | None = None
    source: str | None = None
    policy_version: int | None = None
    detail: dict[str, Any] | None = None
    deployment_status: str | None = None
    consecutive_failures: int | None = Field(default=None, ge=0)
    health_summary: str | None = None


class GatewayRuntimeEventBatchRequest(BaseModel):
    workspace_id: uuid.UUID
    source_service: str = "runledger-gateway-rs"
    events: list[GatewayRuntimeEvent] = Field(default_factory=list)


class GatewayRuntimeEventBatchResponse(BaseModel):
    accepted: int


class GatewayRuntimeApiKeyResolveRequest(BaseModel):
    raw_key: str = Field(..., min_length=1)


class GatewayRuntimeApiKeyResolveResponse(BaseModel):
    api_key_id: uuid.UUID | None = None
    workspace_id: uuid.UUID
    tenant_id: uuid.UUID
    auth_mode: str = "api_key"
    key_prefix: str
    ownership_type: str
    owner_reference: str | None = None
    budget_tier_id: uuid.UUID | None = None
    guardrail_config: dict[str, Any] = Field(default_factory=dict)
    scopes: list[str] = Field(default_factory=list)


class GatewayRuntimeExecutionStep(BaseModel):
    route_id: uuid.UUID
    alias: str
    provider: str
    target_model: str
    execution_mode: str = "direct_http"
    base_url: str | None = None
    api_key_env_var: str | None = None
    priority: int
    timeout_ms: int | None = None
    retry_count: int = 0
    region: str | None = None
    deployment_status: str = "unknown"
    trigger: str = "primary"
    required_error_triggers: list[str] = Field(default_factory=list)
    decision_reason: str | None = None
    request_method: str = "POST"
    request_url: str | None = None
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: dict[str, Any] = Field(default_factory=dict)


class GatewayRuntimePreflightRequest(BaseModel):
    raw_key: str = Field(..., min_length=1)
    body: GatewayCompletionRequest
    end_user_id: str | None = None
    tags_header: str | None = None
    region_header: str | None = None
    timeout_ms: int | None = Field(default=None, ge=1000, le=300000)
    completion_timeout_ms: int | None = Field(default=None, ge=1000, le=300000)
    stream_timeout_ms: int | None = Field(default=None, ge=1000, le=300000)
    client_ip: str | None = None


class GatewayRuntimePreflightResponse(BaseModel):
    api_key_id: uuid.UUID | None = None
    workspace_id: uuid.UUID
    tenant_id: uuid.UUID
    auth_mode: str = "api_key"
    model_requested: str
    route_alias: str
    preferred_region: str | None = None
    request_tags: list[str] = Field(default_factory=list)
    missing_metadata: list[str] = Field(default_factory=list)
    cache_hit_kind: str | None = None
    cached_response: dict[str, Any] | None = None
    prepared_messages: list[dict[str, Any]] = Field(default_factory=list)
    effective_tools: list[dict[str, Any]] | None = None
    effective_reasoning_effort: str | None = None
    compiler_enabled: bool = False
    compiler_config: dict[str, Any] | None = None
    semantic_cache_enabled: bool = False
    guardrails_enabled: bool = True
    ir_decision: dict[str, Any] | None = None
    decision_reason: str | None = None
    execution_steps: list[GatewayRuntimeExecutionStep] = Field(default_factory=list)


class GatewayRuntimeFinalizeRequest(BaseModel):
    workspace_id: uuid.UUID
    route_id: uuid.UUID
    model_requested: str
    prepared_messages: list[dict[str, Any]] = Field(default_factory=list)
    response_json: dict[str, Any]
    latency_ms: int | None = Field(default=None, ge=0)
    total_wall_ms: int | None = Field(default=None, ge=0)
    decision_reason: str | None = None
    end_user_id: str | None = None
    cache: bool = True
    semantic_cache_enabled: bool = False
    guardrails_enabled: bool = True
    compiler_enabled: bool = False
    compiler_config: dict[str, Any] | None = None
    ir_decision: dict[str, Any] | None = None


class GatewayRuntimeFinalizeResponse(BaseModel):
    ok: bool = True


class GatewayRuntimeProviderExecuteRequest(BaseModel):
    route_id: uuid.UUID
    request_body: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False
    timeout_ms: int | None = Field(default=None, ge=1000, le=300000)


class GatewayRuntimeRouteResultRequest(BaseModel):
    route_id: uuid.UUID
    success: bool
    transient: bool = False
    error_detail: str | None = None


class GatewayRuntimeMirrorRequest(BaseModel):
    workspace_id: uuid.UUID
    route_id: uuid.UUID
    model_requested: str
    request_body: dict[str, Any] = Field(default_factory=dict)
    response_json: dict[str, Any]
    request_tags: list[str] = Field(default_factory=list)
    preferred_region: str | None = None


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
