"""
Pydantic response schemas for the analytics API.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from typing import Any

from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    total_cost_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int
    run_count: int
    call_count: int
    prev_cost_usd: Decimal
    cost_delta_pct: Decimal | None  # None when prev_cost is zero


class SpendPoint(BaseModel):
    period: str  # ISO-8601 datetime or date string
    cost_usd: Decimal
    input_tokens: int
    output_tokens: int
    call_count: int


class SpendOverTime(BaseModel):
    granularity: str
    points: list[SpendPoint]


class ModelSpend(BaseModel):
    provider: str
    model: str
    cost_usd: Decimal
    input_tokens: int
    output_tokens: int
    call_count: int


class SpendByModel(BaseModel):
    items: list[ModelSpend]


class UserSpend(BaseModel):
    end_user_id: str
    cost_usd: Decimal
    run_count: int
    call_count: int
    avg_cost_per_run: Decimal
    last_active: str | None
    first_seen: str | None = None


class SpendByUser(BaseModel):
    items: list[UserSpend]


class FeatureSpend(BaseModel):
    feature_tag: str | None
    cost_usd: Decimal
    run_count: int
    call_count: int


class SpendByFeature(BaseModel):
    items: list[FeatureSpend]


class UserSpendDetail(BaseModel):
    end_user_id: str
    cost_usd: Decimal
    run_count: int
    call_count: int
    avg_cost_per_run: Decimal
    last_active: str | None
    spend_over_time: list[SpendPoint]
    models_used: list[ModelSpend]
    features_used: list[FeatureSpend]


class CohortSummary(BaseModel):
    cohort_tier: str  # "P0" | "P1" | "P2" | "P3"
    user_count: int
    avg_cost_usd: Decimal
    total_cost_usd: Decimal


class CohortList(BaseModel):
    items: list[CohortSummary]
    window_days: int


class AnomalyItem(BaseModel):
    end_user_id: str
    detected_at: date
    daily_spend: Decimal
    mean_spend: Decimal
    zscore: Decimal
    reason: str
    created_at: datetime
    model_config = {"from_attributes": True}


class AnomalyList(BaseModel):
    items: list[AnomalyItem]


# ── Phase 3: Scoped summaries ────────────────────────────────────────────────


class IntentCount(BaseModel):
    intent: str
    count: int
    cost_usd: Decimal


class ScopedSummary(BaseModel):
    scope: str
    total_cost_usd: Decimal
    total_savings_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int
    run_count: int
    call_count: int
    workspace_count: int
    active_users: int
    avg_cost_per_run: Decimal | None
    top_intents: list[IntentCount]
    top_models: list[ModelSpend]
    cost_delta_pct: Decimal | None


# ── Phase 3: Savings analytics ───────────────────────────────────────────────


class SavingsByCategory(BaseModel):
    category: str
    savings_usd: Decimal
    call_count: int


class SavingsTimeline(BaseModel):
    period: str
    savings_usd: Decimal
    baseline_cost_usd: Decimal
    actual_cost_usd: Decimal


class SavingsResponse(BaseModel):
    total_savings_usd: Decimal
    total_baseline_usd: Decimal
    total_actual_usd: Decimal
    savings_rate_pct: Decimal | None
    by_category: list[SavingsByCategory]
    timeline: list[SavingsTimeline]


# ── Phase 3: Optimization opportunities ─────────────────────────────────────


class OptimizationOpportunity(BaseModel):
    optimization_type: str
    potential_savings_usd: Decimal
    affected_calls: int
    description: str


class OptimizationOpportunitiesResponse(BaseModel):
    items: list[OptimizationOpportunity]
    total_potential_savings_usd: Decimal


# ── Phase 3: Trends ─────────────────────────────────────────────────────────


class TrendPoint(BaseModel):
    period: str
    cost_usd: Decimal
    run_count: int
    call_count: int
    tokens: int
    avg_latency_ms: Decimal | None
    savings_usd: Decimal


class TrendMetric(BaseModel):
    name: str
    current: Decimal
    previous: Decimal
    change_pct: Decimal | None


class TrendsResponse(BaseModel):
    points: list[TrendPoint]
    metrics: list[TrendMetric]
    granularity: str


# ── Phase 3: Request explorer ────────────────────────────────────────────────


class RequestRecord(BaseModel):
    id: str
    run_id: str
    provider: str
    model: str
    intent: str | None
    end_user_id: str | None
    cost_usd: Decimal | None
    baseline_cost_usd: Decimal | None
    savings_usd: Decimal | None
    optimization_applied: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    status: str
    created_at: str
    tags: list[str] = []


class RequestExplorerResponse(BaseModel):
    items: list[RequestRecord]
    total: int
    page: int
    page_size: int


class InvestigationOrgIdentityPosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, int | str]
    user_context: dict[str, int]
    api_key_context: dict[str, int]
    telemetry_context: dict[str, int]
    mcp_context: dict[str, int]


class InvestigationGatewayRuntimePosture(BaseModel):
    workspace_id: str
    period_days: int
    provider_context: dict[str, int]
    route_context: dict[str, int]
    guardrail_context: dict[str, int]
    cache_context: dict[str, int | float]
    rate_limit_context: dict[str, int]


class InvestigationGovernancePosture(BaseModel):
    workspace_id: str
    period_days: int
    filtered_runs: int
    tags: list[str]
    tool_governance: dict[str, int]
    security: dict[str, int]
    alert_rules: dict[str, int]
    audit_log: dict[str, int]
    governance_pack: dict[str, int]


class EconomicsFinopsPosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_context: dict[str, int | float]
    billing_context: dict[str, int]
    notification_context: dict[str, int]
    ledger_context: dict[str, int]
    spend_context: dict[str, float | int]


class OutcomesFinopsPosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_context: dict[str, int | float]
    billing_context: dict[str, int]
    spend_context: dict[str, float | int]


class MonitoringFinopsPosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_context: dict[str, int | float]
    billing_context: dict[str, int]
    notification_context: dict[str, int]
    ledger_context: dict[str, int]


class OverviewGatewayPosture(BaseModel):
    workspace_id: str
    period_days: int
    provider_context: dict[str, int]
    route_context: dict[str, int]
    guardrail_context: dict[str, int]


class OverviewGovernancePosture(BaseModel):
    workspace_id: str
    period_days: int
    security_context: dict[str, int]
    alert_context: dict[str, int]
    audit_context: dict[str, int]
    governance_context: dict[str, int]


class OverviewOrgPosture(BaseModel):
    workspace_id: str
    period_days: int
    user_context: dict[str, int]
    api_key_context: dict[str, int]
    telemetry_context: dict[str, int]
    mcp_context: dict[str, int]
    hub_context: dict[str, int]


class OverviewScopePosture(BaseModel):
    workspace_id: str
    period_days: int
    access_group_context: dict[str, int]
    cache_context: dict[str, int | float]
    rate_limit_context: dict[str, int]
    tool_context: dict[str, int]


class ModelUsageGatewayPosture(BaseModel):
    workspace_id: str
    period_days: int
    gateway_context: dict[str, int]
    investigation_context: dict[str, int]
    tag_context: dict[str, int]


class EconomicsGatewayPosture(BaseModel):
    workspace_id: str
    period_days: int
    provider_context: dict[str, int]
    gateway_context: dict[str, int]
    investigation_context: dict[str, int]


class MonitoringOpsPosture(BaseModel):
    workspace_id: str
    period_days: int
    gateway_context: dict[str, int]
    governance_context: dict[str, int]
    org_context: dict[str, int]
    investigation_context: dict[str, int]


class TelemetryOpsPosture(BaseModel):
    workspace_id: str
    period_days: int
    gateway_context: dict[str, int]
    governance_context: dict[str, int]
    org_context: dict[str, int]
    investigation_context: dict[str, int]


class UserAnalyticsOrgPosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, int | str]
    user_context: dict[str, int]
    workspace_context: dict[str, int]


class InvestigationFinopsBudgetPosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_context: dict[str, int | float]
    billing_context: dict[str, int]
    spend_context: dict[str, float | int]


class OverviewFinopsBudgetPosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_context: dict[str, int | float]
    billing_context: dict[str, int]
    spend_context: dict[str, float | int]
    notification_context: dict[str, int]


class ModelBudgetUtilizationItem(BaseModel):
    model: str
    spend_30d: float
    request_count: int
    budget_limit_usd: float | None
    budget_action: str | None
    period_type: str | None
    is_active: bool


class ModelBudgetUtilization(BaseModel):
    workspace_id: str
    period_days: int
    models: list[ModelBudgetUtilizationItem]
    total_model_budgets: int
    active_model_budgets: int
    billing_periods: int
    open_billing_periods: int
    chargeback_rules: int


class ToolRegistryFinopsPosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_context: dict[str, int | float]
    chargeback_context: dict[str, int | float]
    spend_context: dict[str, float | int]


class ApprovalsAlertFinopsPosture(BaseModel):
    workspace_id: str
    period_days: int
    approval_context: dict[str, int]
    budget_context: dict[str, int | float]
    alert_context: dict[str, int]


class TagsFinopsBudgetPosture(BaseModel):
    workspace_id: str
    period_days: int
    tag_context: dict[str, int]
    budget_context: dict[str, int | float]
    chargeback_context: dict[str, int]
    spend_context: dict[str, float | int]


class ToolGovernanceOrgPosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, int | str]
    user_context: dict[str, int]
    access_group_context: dict[str, int]
    api_key_context: dict[str, int]
    registry_context: dict[str, int]
    policy_context: dict[str, int]
    mcp_context: dict[str, int]


class ToolGovernanceGatewayPosture(BaseModel):
    workspace_id: str
    period_days: int
    provider_context: dict[str, int]
    guardrail_context: dict[str, int]
    cache_context: dict[str, int | float]
    rate_limit_context: dict[str, int]
    run_context: dict[str, int]
    monitoring_context: dict[str, int]


class ExceptionWorkflowsOrgPosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, int | str]
    user_context: dict[str, int]
    access_group_context: dict[str, int]
    api_key_context: dict[str, int]
    approval_context: dict[str, int]
    alert_context: dict[str, int]
    mcp_context: dict[str, int]


class ExceptionWorkflowsGatewayPosture(BaseModel):
    workspace_id: str
    period_days: int
    provider_context: dict[str, int]
    guardrail_context: dict[str, int]
    cache_context: dict[str, int | float]
    rate_limit_context: dict[str, int]
    run_context: dict[str, int]
    monitoring_context: dict[str, int]


class DataProtectionOrgPosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, int | str]
    user_context: dict[str, int]
    access_group_context: dict[str, int]
    api_key_context: dict[str, int]
    capture_context: dict[str, int]
    security_context: dict[str, int]
    tag_context: dict[str, int]
    mcp_context: dict[str, int]


class DataProtectionGatewayPosture(BaseModel):
    workspace_id: str
    period_days: int
    provider_context: dict[str, int]
    guardrail_context: dict[str, int]
    cache_context: dict[str, int | float]
    rate_limit_context: dict[str, int]
    run_context: dict[str, int]
    monitoring_context: dict[str, int]


class EvidenceAuditCrossPosture(BaseModel):
    workspace_id: str
    period_days: int
    finops_context: dict[str, int | float]
    org_context: dict[str, int | str]
    gateway_context: dict[str, int]
    observe_context: dict[str, int]


class GovernanceInternalPosture(BaseModel):
    workspace_id: str
    period_days: int
    tool_registry_context: dict[str, int]
    tool_policies_context: dict[str, int]
    approvals_context: dict[str, int]
    data_capture_context: dict[str, int]
    security_context: dict[str, int]
    alert_rules_context: dict[str, int]
    audit_context: dict[str, int]
    tags_context: dict[str, int]


class ToolRegistryRuntimePosture(BaseModel):
    workspace_id: str
    period_days: int
    workspace_scope: dict[str, int]
    api_key_scope: dict[str, int]
    mcp_scope: dict[str, int]
    gateway_runtime: dict[str, int]
    observe_evidence: dict[str, int]
    budget_linkage: dict[str, int]


class ToolPoliciesRuntimePosture(BaseModel):
    workspace_id: str
    period_days: int
    scope_context: dict[str, int]
    gateway_enforcement: dict[str, int]
    observe_evidence: dict[str, int]
    budget_context: dict[str, int]
    ledger_context: dict[str, int]


class ApprovalsRuntimePosture(BaseModel):
    workspace_id: str
    period_days: int
    requester_context: dict[str, int]
    gateway_escalation: dict[str, int]
    observe_evidence: dict[str, int]
    monitoring_context: dict[str, int]
    budget_context: dict[str, int]


class DataCaptureRuntimePosture(BaseModel):
    workspace_id: str
    period_days: int
    capture_scope: dict[str, int]
    gateway_evidence: dict[str, int]
    observe_evidence: dict[str, int]
    budget_context: dict[str, int]
    ledger_context: dict[str, int]


class SecurityRuntimePosture(BaseModel):
    workspace_id: str
    period_days: int
    identity_context: dict[str, int]
    gateway_posture: dict[str, int]
    observe_evidence: dict[str, int]
    monitoring_context: dict[str, int]
    finops_context: dict[str, int]


class AlertRulesRuntimePosture(BaseModel):
    workspace_id: str
    period_days: int
    ops_context: dict[str, int]
    gateway_runtime: dict[str, int]
    observe_evidence: dict[str, int]
    finops_context: dict[str, int]


class AuditLogRuntimePosture(BaseModel):
    workspace_id: str
    period_days: int
    evidence_scope: dict[str, int]
    gateway_lineage: dict[str, int]
    observe_lineage: dict[str, int]
    finops_lineage: dict[str, int]


class GovernancePackRuntimePosture(BaseModel):
    workspace_id: str
    period_days: int
    scope_context: dict[str, int]
    governance_sources: dict[str, int]
    monitoring_evidence: dict[str, int]
    finops_evidence: dict[str, int]


class TagsRuntimePosture(BaseModel):
    workspace_id: str
    period_days: int
    taxonomy_scope: dict[str, int]
    governance_attribution: dict[str, int]
    observe_attribution: dict[str, int]
    finops_attribution: dict[str, int]


# ── Phase 8: Engineering metrics ─────────────────────────────────────────────


class CostByDimension(BaseModel):
    name: str
    cost_usd: Decimal
    call_count: int


class QualityFunnel(BaseModel):
    total_requests: int
    successful: int
    routed: int
    cached: int
    with_outcome: int
    positive_outcome: int


class LifecycleStage(BaseModel):
    stage: str
    count: int
    pct: Decimal


class EngineeringMetrics(BaseModel):
    avg_latency_ms: Decimal | None
    p95_latency_ms: Decimal | None
    error_pct: Decimal
    retry_pct: Decimal
    cache_pct: Decimal
    total_requests: int
    total_tokens: int
    avg_cost_per_request: Decimal | None
    cost_by_feature: list[CostByDimension]
    cost_by_model: list[CostByDimension]
    cost_by_tool: list[CostByDimension]
    quality_funnel: QualityFunnel
    lifecycle_stages: list[LifecycleStage]


# ── Optimization Simulator ────────────────────────────────────────────────────


class SimulationRequest(BaseModel):
    intent: str | None = None
    current_model: str | None = None
    proposed_model: str | None = None
    current_provider: str | None = None
    proposed_provider: str | None = None
    enable_cache: bool = False
    enable_compression: bool = False
    workspace_id: str | None = None
    from_dt: datetime | None = None
    to_dt: datetime | None = None


class SimulationImpact(BaseModel):
    label: str
    current_value: str
    projected_value: str
    delta_pct: Decimal | None


class ModelScorecard(BaseModel):
    model: str
    provider: str | None = None
    total_cost_usd: Decimal
    call_count: int
    avg_cost_per_call: Decimal
    avg_latency_ms: Decimal | None
    p95_latency_ms: Decimal | None
    error_rate: Decimal
    cache_hit_rate: Decimal | None
    avg_quality_score: Decimal | None
    input_tokens: int
    output_tokens: int


class ModelScorecardList(BaseModel):
    items: list[ModelScorecard]
    from_dt: datetime | None = None
    to_dt: datetime | None = None


class BudgetOrgScopePosture(BaseModel):
    workspace_id: str
    budget_id: str
    scope_type: str
    scope_id: str | None
    scope_display_name: str | None
    org_context: dict[str, Any]
    hub_context: dict[str, Any]
    scope_entity: dict[str, Any]


class BudgetDetailObservePosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_context: dict[str, int | float]
    spend_context: dict[str, float | int]
    user_budget_context: dict[str, int | float]
    engineering_context: dict[str, int | float]


class BudgetOverrideGovernancePosture(BaseModel):
    workspace_id: str
    period_days: int
    approval_context: dict[str, int]
    alert_context: dict[str, int]
    audit_context: dict[str, int]
    governance_context: dict[str, int]
    tag_context: dict[str, int]


class BudgetDetailBuildPosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_context: dict[str, int | float]
    build_context: dict[str, int]
    experiment_context: dict[str, int]
    spend_context: dict[str, float]


class BudgetControlPlatformPosture(BaseModel):
    period_days: int
    platform_totals: dict[str, int | float]
    org_budgets: list[dict[str, str | int | float]]
    override_context: dict[str, int]
    spend_context: dict[str, float]


class BillingOrgScopePosture(BaseModel):
    workspace_id: str
    period_days: int
    billing_context: dict[str, int | float]
    org_context: dict[str, int]
    attribution_context: dict[str, int | float]
    spend_context: dict[str, float]


class FinOpsInternalPosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_context: dict[str, int | float]
    billing_context: dict[str, int | float]
    chargeback_context: dict[str, int]
    ledger_context: dict[str, int]
    override_context: dict[str, int]
    notification_context: dict[str, int]


class BudgetControlObservePosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_policy: dict[str, int | float]
    override_status: dict[str, int]
    notification_summary: dict[str, int | float]
    spend_context: dict[str, float]


class BudgetControlBuildPosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_policy: dict[str, int | float]
    override_context: dict[str, int]
    scope_context: dict[str, int]
    spend_context: dict[str, float]


class BillingCrossFeaturePosture(BaseModel):
    workspace_id: str
    period_days: int
    gateway_context: dict[str, int | float]
    safety_context: dict[str, int]
    platform_context: dict[str, int]
    spend_context: dict[str, float]


class ChargebackCrossFeaturePosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, int]
    gateway_context: dict[str, int | float]
    safety_context: dict[str, int]
    platform_context: dict[str, int]
    spend_context: dict[str, float]


class LedgerCrossFeaturePosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, int]
    observe_context: dict[str, int | float]
    safety_context: dict[str, int]
    platform_context: dict[str, int]
    ledger_context: dict[str, int | str]


class BudgetScopeGovernancePosture(BaseModel):
    workspace_id: str
    period_days: int
    identity_context: dict[str, int]
    runtime_context: dict[str, int | float]
    governance_context: dict[str, int]
    spend_context: dict[str, float]


class BudgetDetailDrillbackPosture(BaseModel):
    workspace_id: str
    period_days: int
    scope_context: dict[str, int]
    runtime_context: dict[str, int | float]
    evidence_context: dict[str, int]
    workflow_context: dict[str, int]
    spend_context: dict[str, float]


class BudgetOverrideExceptionPosture(BaseModel):
    workspace_id: str
    period_days: int
    override_context: dict[str, int | float]
    approval_context: dict[str, int]
    runtime_context: dict[str, int]
    monitoring_context: dict[str, int]
    spend_context: dict[str, float]


class BillingReconciliationPosture(BaseModel):
    workspace_id: str
    period_days: int
    identity_context: dict[str, int]
    provider_context: dict[str, int | float]
    optimization_context: dict[str, int | float]
    evidence_context: dict[str, int]
    spend_context: dict[str, float]


class BillingDetailEvidencePosture(BaseModel):
    workspace_id: str
    period_days: int
    identity_context: dict[str, int]
    gateway_context: dict[str, int | float]
    observe_context: dict[str, int]
    build_context: dict[str, int]
    spend_context: dict[str, float]


class ChargebackAttributionPosture(BaseModel):
    workspace_id: str
    period_days: int
    identity_context: dict[str, int]
    runtime_context: dict[str, int | float]
    monitoring_context: dict[str, int]
    optimization_context: dict[str, int | float]
    spend_context: dict[str, float]


class PlaygroundOrgGatewayPosture(BaseModel):
    workspace_id: str
    period_days: int
    workspace_context: dict[str, str | int]
    api_key_context: dict[str, str | int]
    ai_hub_context: dict[str, int]
    provider_context: dict[str, int]
    guardrail_context: dict[str, int]
    cache_context: dict[str, int | float]
    rate_limit_context: dict[str, int]


class PromptsOrgGatewayPosture(BaseModel):
    workspace_id: str
    period_days: int
    workspace_context: dict[str, str | int]
    ai_hub_context: dict[str, int]
    provider_context: dict[str, int]
    gateway_context: dict[str, int]
    prompt_model_context: dict[str, int]


class EvalReplayOrgGatewayPosture(BaseModel):
    workspace_id: str
    period_days: int
    workspace_context: dict[str, str | int]
    access_group_context: dict[str, int]
    api_key_context: dict[str, int]
    ai_hub_context: dict[str, int]
    provider_context: dict[str, int]
    gateway_context: dict[str, int]
    guardrail_context: dict[str, int]


class EvalReplayObservePosture(BaseModel):
    workspace_id: str
    period_days: int
    runs_context: dict[str, int]
    request_flow_context: dict[str, int]
    model_usage_context: dict[str, int | float]
    cost_savings_context: dict[str, int | float]


class OptimizationOrgGatewayPosture(BaseModel):
    workspace_id: str
    period_days: int
    workspace_context: dict[str, str | int]
    api_key_context: dict[str, int]
    ai_hub_context: dict[str, int]
    provider_context: dict[str, int]
    gateway_context: dict[str, int]
    guardrail_context: dict[str, int]
    cache_context: dict[str, int]
    rate_limit_context: dict[str, int]


class OptimizationObservePosture(BaseModel):
    workspace_id: str
    period_days: int
    runs_context: dict[str, int]
    request_flow_context: dict[str, int]
    model_usage_context: dict[str, int | float]
    cost_savings_context: dict[str, int | float]


class OptimizationFinOpsPosture(BaseModel):
    workspace_id: str
    period_days: int
    budget_context: dict[str, int | float]
    billing_context: dict[str, int]
    chargeback_context: dict[str, int]


class BuildInternalPosture(BaseModel):
    workspace_id: str
    period_days: int
    playground_context: dict[str, int]
    prompts_context: dict[str, int]
    workflows_context: dict[str, int]
    evaluation_context: dict[str, int]
    replay_context: dict[str, int]
    optimization_context: dict[str, int | float]
    scorecards_context: dict[str, int]


class PromptsListObservePosture(BaseModel):
    workspace_id: str
    period_days: int
    observe_context: dict[str, int | float]
    eval_context: dict[str, int]


class PromptDetailHubFinOpsPosture(BaseModel):
    workspace_id: str
    period_days: int
    hub_context: dict[str, int]
    chargeback_context: dict[str, int | float]


class AgentsListPosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, str | int]
    provider_context: dict[str, int]
    observe_context: dict[str, int]
    finops_context: dict[str, int | float]
    eval_context: dict[str, int]


class AgentDetailGovernancePosture(BaseModel):
    workspace_id: str
    period_days: int
    guardrail_context: dict[str, int]
    observe_context: dict[str, int]
    safety_context: dict[str, int]
    eval_context: dict[str, int]


class WorkflowsListPosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, str | int]
    gateway_context: dict[str, int]
    observe_context: dict[str, int | float]
    eval_context: dict[str, int]


class WorkflowDetailLoopPosture(BaseModel):
    workspace_id: str
    period_days: int
    runs_context: dict[str, int]
    chargeback_context: dict[str, int | float]
    optimization_context: dict[str, int]
    eval_context: dict[str, int]


class WorkflowRunEvidencePosture(BaseModel):
    workspace_id: str
    period_days: int
    gateway_context: dict[str, int]
    observe_context: dict[str, int]
    finops_context: dict[str, int | float]
    safety_context: dict[str, int]


class DatasetsEvalAssetPosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, str | int]
    observe_context: dict[str, int]
    finops_context: dict[str, int | float]
    build_context: dict[str, int]


class EvalStudioParentPosture(BaseModel):
    workspace_id: str
    period_days: int
    billing_context: dict[str, int]
    chargeback_context: dict[str, int | float]
    eval_self_context: dict[str, int]


class ExperimentsComparisonPosture(BaseModel):
    workspace_id: str
    period_days: int
    billing_context: dict[str, int]
    chargeback_context: dict[str, int | float]
    comparison_context: dict[str, int]


class ReplayLabModePosture(BaseModel):
    workspace_id: str
    period_days: int
    chargeback_context: dict[str, int | float]
    replay_context: dict[str, int]


class ReplayResultAnalysisPosture(BaseModel):
    workspace_id: str
    period_days: int
    gateway_context: dict[str, int]
    observe_context: dict[str, int]
    cost_context: dict[str, int | float]


class RunbooksRemediationPosture(BaseModel):
    workspace_id: str
    period_days: int
    observe_context: dict[str, int]
    alert_context: dict[str, int]
    cost_context: dict[str, int | float]
    optimization_context: dict[str, int]


class OptOppsRationalePosture(BaseModel):
    workspace_id: str
    period_days: int
    cost_context: dict[str, int | float]
    optimization_context: dict[str, int]


class OptSimDecisionPosture(BaseModel):
    workspace_id: str
    period_days: int
    cost_context: dict[str, int | float]
    optimization_context: dict[str, int]


class ModelScorecardsIntelPosture(BaseModel):
    workspace_id: str
    period_days: int
    model_context: dict[str, int]
    cost_context: dict[str, int | float]
    optimization_context: dict[str, int]


class VectorStoresLifecyclePosture(BaseModel):
    workspace_id: str
    period_days: int
    workspace_context: dict[str, str]
    observe_context: dict[str, int]
    cost_context: dict[str, int | float]
    build_context: dict[str, int]


class VectorStoreDetailEvidencePosture(BaseModel):
    workspace_id: str
    period_days: int
    observe_context: dict[str, int]
    cost_context: dict[str, int | float]
    build_context: dict[str, int]


class PlaygroundObservePosture(BaseModel):
    workspace_id: str
    period_days: int
    runs_context: dict[str, int]
    request_flow_context: dict[str, int]
    model_usage_context: dict[str, int | float]
    cost_savings_context: dict[str, int | float]


class PromptDetailObservePosture(BaseModel):
    workspace_id: str
    period_days: int
    prompt_name: str
    analytics_context: dict[str, int]
    model_usage_context: dict[str, int | float]
    cost_context: dict[str, int | float]
    request_context: dict[str, int]


class WorkflowDetailCrossFeaturePosture(BaseModel):
    workspace_id: str
    period_days: int
    org_context: dict[str, str | int]
    gateway_context: dict[str, int | float]
    observe_context: dict[str, int | float]
    finops_context: dict[str, int | float]


class SimulationResult(BaseModel):
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


class PlatformLifecyclePosture(BaseModel):
    period_days: int
    finops_context: dict[str, int]
    gateway_context: dict[str, int]
    governance_context: dict[str, int]
    org_access_context: dict[str, int]


class PlatformSettingsConvergencePosture(BaseModel):
    period_days: int
    telemetry_context: dict[str, int]
    audit_context: dict[str, int]
    compliance_context: dict[str, int]
    ops_context: dict[str, int]


class PlatformAdminObservePosture(BaseModel):
    period_days: int
    monitoring_context: dict[str, int]
    telemetry_context: dict[str, int]
    governance_context: dict[str, int]
    build_context: dict[str, int]
