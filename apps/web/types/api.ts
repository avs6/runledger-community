export interface RunListItem {
  id: string
  status: 'running' | 'succeeded' | 'failed' | 'cancelled'
  end_user_id: string | null
  session_id: string | null
  feature_tag: string | null
  deployment_version: string | null
  total_cost_usd: string | null
  total_input_tokens: number | null
  total_output_tokens: number | null
  started_at: string
  ended_at: string | null
  duration_ms: number | null
  primary_model: string | null
}

export interface RunListResponse {
  items: RunListItem[]
  next_cursor: string | null
  total: number
}

export interface SpanDetail {
  id: string
  run_id: string
  parent_span_id: string | null
  span_type: 'chain' | 'llm' | 'tool' | 'agent' | 'retrieval' | 'run'
  name: string
  started_at: string
  ended_at: string | null
  status: string
  cost_usd: string | null
  metadata: Record<string, unknown> | null
}

export interface ProviderCallDetail {
  id: string
  span_id: string | null
  run_id: string
  provider: string
  model: string
  input_tokens: number | null
  output_tokens: number | null
  cached_input_tokens: number | null
  latency_ms: number | null
  cost_usd: string | null
  status: string
  error_type: string | null
  created_at: string
}

export interface ToolCallDetail {
  id: string
  span_id: string | null
  run_id: string
  tool_name: string
  tool_type: string
  risk_score: number | null
  duration_ms: number | null
  status: string
  created_at: string
}

export interface RunDetailResponse {
  id: string
  status: string
  end_user_id: string | null
  session_id: string | null
  feature_tag: string | null
  deployment_version: string | null
  total_cost_usd: string | null
  total_input_tokens: number | null
  total_output_tokens: number | null
  started_at: string
  ended_at: string | null
  duration_ms: number | null
  spans: SpanDetail[]
  provider_calls: ProviderCallDetail[]
  tool_calls: ToolCallDetail[]
  // Phase 19 — present only when capture policy is SAMPLED or FULL
  input_payload: Array<{ role: string; content: string }> | null
  output_payload: unknown | null
  span_payloads: Record<string, { input?: unknown; output?: unknown }> | null
}

export interface GraphNodeData {
  span_type: string
  status: string
  cost_usd: string | null
  input_tokens: number | null
  output_tokens: number | null
  latency_ms: number | null
  model: string | null
  provider: string | null
  error_type: string | null
  started_at: string | null
  ended_at: string | null
  duration_ms: number | null
  metadata: Record<string, unknown> | null
}

export interface GraphNode {
  id: string
  label: string
  data: GraphNodeData
}

export interface GraphEdge {
  id: string
  source: string
  target: string
}

export interface RunGraphResponse {
  run_id: string
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface RunFlowRecord {
  id: string
  workspace_id: string
  workspace_name: string
  tenant_id: string
  tenant_name: string
  status: string
  end_user_id: string | null
  feature_tag: string | null
  primary_model: string | null
  provider: string | null
  route: string
  outcome: string
  prompt: string
  skill: string
  agent: string
  tool: string
  team: string
  application: string
  cost_band: string
  total_cost_usd: string
  total_input_tokens: number
  total_output_tokens: number
  cached_input_tokens: number
  latency_ms: number | null
  success: boolean
  savings_usd: string
  savings_category: string | null
  savings_reason: string | null
  started_at: string
}

export interface RunFlowResponse {
  scope: 'workspace' | 'org' | 'platform'
  mode: string
  metric: string
  sampled_runs: number
  total_runs: number
  workspace_count: number
  generated_at: string
  items: RunFlowRecord[]
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface AnalyticsSummary {
  total_cost_usd: string
  total_input_tokens: number
  total_output_tokens: number
  run_count: number
  call_count: number
  prev_cost_usd: string
  cost_delta_pct: string | null
}

export interface SpendPoint {
  period: string
  cost_usd: string
  input_tokens: number
  output_tokens: number
  call_count: number
}

export interface SpendOverTime {
  granularity: string
  points: SpendPoint[]
}

export interface ModelSpend {
  provider: string
  model: string
  cost_usd: string
  input_tokens: number
  output_tokens: number
  call_count: number
}

export interface SpendByModel {
  items: ModelSpend[]
}

export interface UserSpend {
  end_user_id: string
  cost_usd: string
  run_count: number
  call_count: number
  avg_cost_per_run: string
  last_active: string | null
  first_seen?: string | null
}

export interface SpendByUser {
  items: UserSpend[]
}

export interface FeatureSpend {
  feature_tag: string | null
  cost_usd: string
  run_count: number
  call_count: number
}

export interface SpendByFeature {
  items: FeatureSpend[]
}

export interface UserSpendDetail {
  end_user_id: string
  cost_usd: string
  run_count: number
  call_count: number
  avg_cost_per_run: string
  last_active: string | null
  spend_over_time: SpendPoint[]
  models_used: ModelSpend[]
  features_used: FeatureSpend[]
}

// ── Budgets ───────────────────────────────────────────────────────────────────

export interface Budget {
  id: string
  scope_type: 'workspace' | 'end_user' | 'feature_tag' | 'app'
  scope_id: string | null
  period_type: 'daily' | 'monthly' | 'total'
  limit_usd: string
  action: 'notify' | 'block' | 'downgrade'
  downgrade_to_model: string | null
  is_active: boolean
  created_at: string
  current_spend_usd: string
  pct_used: string
}

export interface BudgetList {
  items: Budget[]
}

export interface BudgetRollupWorkspace {
  workspace_id: string
  workspace_name: string
  budget_count: number
  active_budget_count: number
  limit_usd: string
  current_spend_usd: string
  remaining_usd: string
  pct_used: string
  exceeded_count: number
  at_risk_count: number
}

export interface BudgetRollupResponse {
  scope: 'workspace' | 'org' | 'platform'
  workspace_count: number
  budget_count: number
  active_budget_count: number
  limit_usd: string
  current_spend_usd: string
  remaining_usd: string
  pct_used: string
  exceeded_count: number
  at_risk_count: number
  workspaces: BudgetRollupWorkspace[]
}

export interface BudgetCheckResponse {
  allowed: boolean
  action?: string
  budget_id?: string
  downgrade_model?: string
}

export interface Breach {
  id: string
  budget_id: string
  occurred_at: string
  spend_at_breach_usd: string | null
  action_taken: string | null
  notified_at: string | null
}

export interface BreachList {
  items: Breach[]
}

// ── Billing ───────────────────────────────────────────────────────────────────

export interface BillingPeriod {
  id: string
  period_start: string
  period_end: string
  status: 'open' | 'closing' | 'closed'
  total_cost_usd: string | null
  snapshot_hash: string | null
  closed_at: string | null
  created_at: string
}

export interface BillingPeriodList {
  items: BillingPeriod[]
}

export interface ChargebackRule {
  id: string
  allocation_type: 'cost_center' | 'team' | 'env'
  dimension: string
  weight: string
  created_at: string
}

export interface ReconciliationResult {
  period_id: string
  status: 'pass' | 'warning' | 'fail'
  provider_calls_sum: string
  usage_daily_sum: string
  delta_pct: string
  orphaned_calls: number
  duplicate_calls: number
  issues: string[]
  warnings?: string[]
}

export interface BreakdownUser {
  end_user_id: string | null
  cost_usd: string
  run_count: number
}

export interface BreakdownApp {
  application_id: string | null
  cost_usd: string
  users: BreakdownUser[]
}

export interface PeriodBreakdown {
  period_id: string
  total_cost_usd: string
  by_application: BreakdownApp[]
}

export interface UsageSnapshot {
  id: string
  billing_period_id: string
  signature: string
  signing_key_id: string
  created_at: string
}

// ── Economics (Phase 9) ────────────────────────────────────────────────────────

export interface SpanTypeCost {
  span_type: string
  cost_usd: string
}

export interface ModelCost {
  model: string
  provider: string
  cost_usd: string
  call_count: number
}

export interface RunEconomics {
  run_id: string
  total_cost_usd: string
  cost_by_span_type: SpanTypeCost[]
  cost_by_model: ModelCost[]
  retry_cost: string
}

export interface WorkflowSummary {
  feature_tag: string | null
  application_id: string | null
  run_count: number
  avg_cost_usd: string
  p95_cost_usd: string
  total_cost_usd: string
  call_count: number
}

export interface WorkflowTopList {
  metric: string
  items: WorkflowSummary[]
}

export interface SpanTypeDelta {
  span_type: string
  baseline_cost: string
  comparison_cost: string
  delta_pct: string | null
}

export interface VersionSummary {
  version: string
  run_count: number
  avg_cost_usd: string
  avg_input_tokens: string
  avg_output_tokens: string
  avg_latency_ms: string | null
}

export interface VersionCompareResult {
  baseline: VersionSummary
  comparison: VersionSummary
  cost_delta_pct: string | null
  token_delta_pct: string | null
  latency_delta_pct: string | null
  by_span_type: SpanTypeDelta[]
}

export interface RegressionItem {
  feature_tag: string | null
  current_avg_cost: string
  prior_avg_cost: string
  change_pct: string
  run_count: number
  prior_run_count: number
}

export interface RegressionList {
  items: RegressionItem[]
  from_dt: string
  to_dt: string
}

export interface Annotation {
  id: string
  note: string
  annotation_date: string
  version: string | null
  created_at: string
}

export interface AnnotationList {
  items: Annotation[]
}

// ── Phase 10 — Users analytics extensions ─────────────────────────────────────

export interface CohortSummary { cohort_tier: string; user_count: number; avg_cost_usd: string; total_cost_usd: string }
export interface CohortList { items: CohortSummary[]; window_days: number }
export interface AnomalyItem { end_user_id: string; detected_at: string; daily_spend: string; mean_spend: string; zscore: string; reason: string; created_at: string }
export interface AnomalyList { items: AnomalyItem[] }

// ── Phase 10 — Replay ─────────────────────────────────────────────────────────

export interface ExperimentConfig { model: string; label?: string | null; prompt_name?: string | null; prompt_version?: number | null }
export interface DatasetResponse { id: string; name: string; source: string; run_ids: string[]; run_count: number; created_at: string }
export interface DatasetList { items: DatasetResponse[] }
export interface ExperimentResponse { id: string; dataset_id: string; name: string; configs: ExperimentConfig[]; status: string; estimated_cost_usd: string | null; created_at: string }
export interface ExperimentList { items: ExperimentResponse[] }
export interface ConfigResult { model: string; label?: string | null; run_count: number; total_input_tokens: number; total_output_tokens: number; projected_cost_usd: string; avg_cost_per_run: string; pricing_found: boolean; prompt_name?: string | null; prompt_version?: number | null; prompt_content_preview?: string | null }
export interface ConfigDelta { config_a: string; config_b: string; cost_delta_pct: string | null }
export interface ExperimentResults { experiment_id: string; experiment_name: string; status: string; dataset_run_count: number; configs: ConfigResult[]; deltas: ConfigDelta[]; completed_at: string | null }

// ── Phase 11 — Ledger ──────────────────────────────────────────────────────────

export interface LedgerSnapshotResponse { id: string; workspace_id: string; snapshot_date: string; total_cost_usd: string; model_breakdown: Record<string, string>; call_count: number; hash: string; key_id: string; created_at: string }
export interface LedgerSnapshotList { items: LedgerSnapshotResponse[] }
export interface LedgerVerifyResult { snapshot_date: string; status: 'ok' | 'tampered' | 'not_found'; stored_hash: string | null; computed_hash: string | null; match: boolean }

// ── Phase 11 — Tools ──────────────────────────────────────────────────────────

export interface ToolRegistryResponse { id: string; workspace_id: string; tool_name: string; policy: string; description: string | null; created_at: string; updated_at: string }
export interface ToolRegistryList { items: ToolRegistryResponse[] }
export interface SecurityEventResponse { id: string; workspace_id: string; event_type: string; tool_name: string | null; end_user_id: string | null; run_id: string | null; details: Record<string, unknown>; detected_at: string }
export interface SecurityEventList { items: SecurityEventResponse[] }

// ── Phase 11 — Privacy ────────────────────────────────────────────────────────

export interface CapturePolicyResponse { id: string; workspace_id: string; privacy_mode: string; sampled_rate: string | null; updated_at: string; created_at: string }

// ── Phase 12 — Settings ────────────────────────────────────────────────────────

export interface ApiKeyResponse { id: string; workspace_id: string; workspace_name?: string | null; key_prefix: string; name: string | null; scopes: string[]; is_session: boolean; created_at: string; created_by: string | null }
export interface ApiKeyCreateResponse extends ApiKeyResponse { key: string }

// ── Phase 12 — Providers ───────────────────────────────────────────────────────

export interface ProviderPricingResponse { id: string; provider: string; model: string; input_cost_per_1m: string; output_cost_per_1m: string; cached_input_cost_per_1m: string | null; tags: string[]; display_name: string | null; effective_from: string; effective_to: string | null; workspace_id: string | null; created_at: string }
export interface ProviderPricingList { items: ProviderPricingResponse[] }
export interface PricingImportResult { inserted: number; updated: number; unchanged: number; total: number; providers: string[]; tags: string[]; errors: string[] }

// ── Phase 14 — Integrations ────────────────────────────────────────────────────

export interface ExportRow { date: string; provider: string; model: string; cost_usd: string; input_tokens: number; output_tokens: number; call_count: number }
export interface AnalyticsExport { items: ExportRow[] }
export interface SlackTestResponse { ok: boolean; error: string | null }

// ── Budget notification types ──────────────────────────────────────────────────
export interface NotificationResponse { id: string; channel: string; destination_url: string; events: string[]; is_active: boolean; created_at: string }
export interface NotificationList { items: NotificationResponse[] }

// ── Chargeback rule types ──────────────────────────────────────────────────────
export interface ChargebackRuleResponse { id: string; allocation_type: string; dimension: string; weight: string; created_at: string }
export interface ChargebackRuleList { items: ChargebackRuleResponse[] }

// ── Admin / multi-tenancy types ─────────────────────────────────────────────────
export type TenantStatus = 'active' | 'suspended' | 'archived'
export type WorkspaceStatus = 'active' | 'suspended' | 'archived'
export type MemberStatus = 'active' | 'invited' | 'suspended'

export interface TenantResponse {
  id: string
  name: string
  plan: string
  status: TenantStatus
  is_default: boolean
  owner_user_id: string | null
  created_at: string
  workspace_count: number
  member_count: number
}
export interface AdminWorkspaceResponse {
  id: string
  tenant_id: string
  name: string
  status: WorkspaceStatus
  is_restricted: boolean
  created_at: string
}

export interface AuditEventResponse {
  id: string
  actor_user_id: string | null
  target_user_id: string | null
  scope_type: string
  scope_id: string
  action: string
  old_value: string | null
  new_value: string | null
  created_at: string
}

// ── Phase 17 — Evaluations & Scores ───────────────────────────────────────────

export interface ScoreEvent {
  id: string
  workspace_id: string
  run_id: string | null
  span_id: string | null
  session_id: string | null
  end_user_id: string | null
  name: string
  value: string
  label: string | null
  source: string
  confidence: string | null
  evidence: Record<string, unknown> | null
  created_at: string
}

export interface ScoreList {
  items: ScoreEvent[]
}

export interface ScoreSummaryItem {
  name: string
  avg_value: string
  p50: string | null
  p90: string | null
  sample_count: number
  prev_avg_value: string | null
  change_pct: string | null
}

export interface ScoreSummary {
  items: ScoreSummaryItem[]
}

export interface ScoreRegressionItem {
  name: string
  current_avg: string
  prior_avg: string
  change_pct: string
  sample_count: number
}

// ── Phase 18 — Prompt Management ──────────────────────────────────────────────

export interface PromptResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  default_environment: string
  created_at: string
  updated_at: string
}

export interface PromptList {
  items: PromptResponse[]
}

export interface PromptVersion {
  id: string
  prompt_id: string
  version: number
  content: string
  variables: Array<{ name: string; type?: string; description?: string }>
  commit_message: string | null
  environment: string
  model_hint: string | null
  created_at: string
}

export interface VersionList {
  items: PromptVersion[]
}

export interface VersionMetrics {
  version: number
  environment: string
  run_count: number
  avg_cost_usd: number | null
  avg_score: number | null
  commit_message: string | null
  created_at: string
}

export interface PromptMetrics {
  items: VersionMetrics[]
}

// ── Phase 19 — Sessions ────────────────────────────────────────────────────────

export interface SessionItem {
  session_id: string
  end_user_id: string | null
  run_count: number
  total_cost_usd: string | null
  started_at: string
  ended_at: string | null
  avg_score: string | null
}

export interface SessionList {
  items: SessionItem[]
  total: number
}

export interface SessionRunItem {
  id: string
  status: string
  feature_tag: string | null
  deployment_version: string | null
  total_cost_usd: string | null
  started_at: string
  ended_at: string | null
  duration_ms: number | null
  turn_number: number
}

export interface SessionDetail {
  session_id: string
  end_user_id: string | null
  run_count: number
  total_cost_usd: string | null
  started_at: string
  ended_at: string | null
  runs: SessionRunItem[]
}

export interface TurnCost {
  turn_number: number
  run_id: string
  cost_usd: string | null
  cumulative_cost_usd: string
}

export interface TurnCostResponse {
  session_id: string
  turns: TurnCost[]
}

// ── Phase 21A — Alert Rules ────────────────────────────────────────────────────

export interface AlertRule {
  id: string
  workspace_id: string
  name: string
  metric: 'error_rate' | 'p95_latency' | 'avg_score' | 'spend_velocity'
  operator: 'gt' | 'lt'
  threshold: string
  window_minutes: number
  action: string
  channel_id: string | null
  is_active: boolean
  email_enabled: boolean
  created_at: string
}

export interface AlertRuleList {
  items: AlertRule[]
}

export interface AlertFiring {
  id: string
  rule_id: string
  workspace_id: string
  fired_at: string
  metric_value: string
  resolved_at: string | null
  rule_name: string
}

export interface AlertHistoryList {
  items: AlertFiring[]
}

// ── Phase 21B — Model Gateway ──────────────────────────────────────────────────

export interface GatewayRoute {
  id: string
  workspace_id: string
  alias: string
  provider: string
  target_model: string
  base_url: string | null
  api_key_env_var: string | null
  priority: number
  is_active: boolean
  config: Record<string, string> | null
  // Phase 30 runtime controls
  daily_cost_limit_usd: string | null
  monthly_cost_limit_usd: string | null
  pii_redaction_enabled: boolean
  semantic_cache_enabled: boolean
  context_compiler_enabled: boolean
  context_compiler_config: Record<string, unknown> | null
  intelligent_routing_enabled: boolean
  routing_config: Record<string, unknown> | null
  per_user_rpm_limit: number | null
  health_auto_disable: boolean
  last_health_check_at: string | null
  consecutive_health_failures: number
  disabled_reason: string | null
  created_at: string
}

export interface GatewayRouteList {
  items: GatewayRoute[]
}

export interface GatewayRouteStats {
  route_id: string | null
  alias: string
  total_requests: number
  cache_hits: number
  cache_hit_rate: string
  avg_latency_ms: string | null
  error_count: number
}

export interface GatewayStats {
  total_requests: number
  cache_hits: number
  cache_hit_rate: string
  avg_latency_ms: string | null
  routes: GatewayRouteStats[]
}

export interface GatewayRequestLog {
  id: string
  workspace_id: string
  route_id: string | null
  model_requested: string
  model_used: string | null
  cache_hit: boolean
  input_tokens: number | null
  output_tokens: number | null
  latency_ms: number | null
  status: string
  decision_reason: string | null
  created_at: string
}

export interface GatewayRequestList {
  items: GatewayRequestLog[]
  total: number
}

export type RoutingPolicyType =
  | 'manual'
  | 'cost_optimized'
  | 'latency_optimized'
  | 'quality_optimized'
  | 'weighted'
  | 'canary'
  | 'budget_aware'
  | 'complexity_based'
  | 'outcome_optimized'

export interface RoutingPolicy {
  id: string
  workspace_id: string
  alias: string
  policy_type: RoutingPolicyType
  config: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RoutingPolicyList {
  items: RoutingPolicy[]
}

export interface RoutingRecommendationModel {
  model: string
  route_id: string | null
  sample_count: number
  success_rate: number
  cost_per_success: number | null
  improvement_vs_current: number | null
}

export interface RoutingRecommendationResponse {
  alias: string
  window_days: number
  workflow_type: string | null
  total_outcomes_sampled: number
  models: RoutingRecommendationModel[]
  best_model: string | null
  recommended_route_id: string | null
  message: string
}

// ── Optimization flywheel (Phase 7) ─────────────────────────────────────────────

export interface FlywheelSettings {
  enabled: boolean
  apply_mode: string // approval | auto | off
  quality_metric: Record<string, unknown>
  min_quality: string
  segment_by: string // outcome_type | task_class | alias
  action_space: string[]
  min_sample_size: number
  lookback_days: number
  updated_at: string
}

export interface FlywheelRecommendation {
  id: string
  segment_by: string
  segment_key: string
  kind: string // switch | explore | guardrail
  current_config: Record<string, unknown>
  proposed_config: Record<string, unknown>
  est_cost_delta_pct: string | null
  est_cost_delta_per_req: string | null
  current_quality: string | null
  proposed_quality: string | null
  min_quality: string
  sample_size: number
  confidence: string // high | medium | low
  rationale: string | null
  status: string // pending | applied | dismissed | rolled_back | superseded
  apply_mode: string
  applied_route_id: string | null
  created_at: string
  updated_at: string
  applied_at: string | null
}

export interface FlywheelRecommendationList {
  items: FlywheelRecommendation[]
  total: number
}

export interface FlywheelRunResponse {
  status: string
  recommendations: number
  auto_applied: number
}

// ── Org Dashboard ──────────────────────────────────────────────────────────────

export interface OrgDashboardWorkspace {
  id: string
  name: string
  status: string
  cost_usd: string
  run_count: number
  member_count: number
}

export interface OrgDashboardModel {
  model: string
  cost_usd: string
  call_count: number
}

export interface OrgDashboardRun {
  id: string
  workspace_name: string
  status: string
  feature_tag: string | null
  total_cost_usd: string | null
  started_at: string | null
}

export interface OrgDashboard {
  tenant_name: string
  workspace_count: number
  member_count: number
  total_cost_usd: string
  run_count: number
  total_tokens: number
  cost_delta_pct: string | null
  workspaces: OrgDashboardWorkspace[]
  top_models: OrgDashboardModel[]
  recent_runs: OrgDashboardRun[]
}


export interface SubscriptionResponse {
  tenant_id: string
  plan: string
  status: string
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  current_period_start: string | null
  current_period_end: string | null
  events_limit: number
  events_used: number
  usage_pct: number
}

// ── Evaluators ────────────────────────────────────────────────────────────────

export interface EvaluatorResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  type: 'llm_judge' | 'rule'
  config: Record<string, unknown>
  status: 'active' | 'inactive'
  last_run_at: string | null
  last_run_count: number
  created_at: string
}

export interface EvaluatorList {
  items: EvaluatorResponse[]
}

export interface EvaluatorRunResult {
  evaluator_id: string
  evaluated: number
  scores_created: number
  errors: number
}

// ── Cost-quality analytics ────────────────────────────────────────────────────

export interface CostQualityPoint {
  model: string
  avg_cost_usd: string
  avg_score: string | null
  run_count: number
}

export interface CostQualityResponse {
  items: CostQualityPoint[]
}

export interface BestValueModel {
  model: string
  avg_cost_usd: string
  avg_score: string
  value_score: string
  run_count: number
}

export interface BestValueResponse {
  items: BestValueModel[]
}

// ── Provider Invoice Reconciliation ───────────────────────────────────────────

export interface InvoiceResponse {
  id: string
  workspace_id: string
  provider: string
  period_start: string
  period_end: string
  currency: string
  total_amount: string
  line_count: number
  matched_count: number
  unmatched_amount: string | null
  status: string
  filename: string | null
  created_at: string
}

export interface InvoiceList {
  items: InvoiceResponse[]
}

export interface InvoiceLineResponse {
  id: string
  invoice_id: string
  provider_request_id: string | null
  model: string | null
  input_tokens: number | null
  output_tokens: number | null
  amount: string
  occurred_at: string | null
  match_status: 'exact' | 'fuzzy' | 'unmatched' | 'disputed'
  matched_call_id: string | null
  token_delta: number | null
  cost_delta: string | null
  dispute_note: string | null
  raw: Record<string, unknown>
}

export interface InvoiceLineList {
  items: InvoiceLineResponse[]
  total: number
}

export interface TokenMismatchBucket {
  bucket: string
  count: number
  amount: string
}

export interface ReconciliationSummary {
  invoice_id: string
  provider: string
  period_start: string
  period_end: string
  total_amount: string
  line_count: number
  matched_exact: number
  matched_fuzzy: number
  unmatched: number
  disputed: number
  matched_pct: string
  unmatched_amount: string
  runledger_total: string
  delta_amount: string
  delta_pct: string | null
  token_mismatch_buckets: TokenMismatchBucket[]
  status: string
}

// ── Outcomes ──────────────────────────────────────────────────────────────────

export interface OutcomeResponse {
  id: string
  workspace_id: string
  run_id: string | null
  session_id: string | null
  end_user_id: string | null
  outcome_type: string
  success: boolean
  value_usd: string | null
  labels: Record<string, unknown>
  created_at: string
}

export interface OutcomeList {
  items: OutcomeResponse[]
  total: number
}

export interface OutcomeSummaryItem {
  outcome_type: string
  count: number
  success_count: number
  success_rate: string
  total_cost_usd: string
  cost_per_success_usd: string | null
  total_value_usd: string | null
  roi: string | null
}

export interface OutcomeSummary {
  items: OutcomeSummaryItem[]
  window_days: number
}

export interface OutcomeTrendPoint {
  day: string
  outcome_type: string
  success_rate: string
  cost_per_success_usd: string | null
  count: number
  roi: string | null
}

export interface OutcomeTrend {
  items: OutcomeTrendPoint[]
}

export interface WorkflowROIItem {
  feature_tag: string
  outcome_type: string
  run_count: number
  success_count: number
  success_rate: string
  total_cost_usd: string
  total_value_usd: string | null
  roi: string | null
  cost_per_success_usd: string | null
}

export interface WorkflowROIList {
  items: WorkflowROIItem[]
}

export interface QualityOutcomeCorrelation {
  outcome_type: string
  avg_score: string | null
  success_rate: string
  sample_count: number
}

// ── Approvals ─────────────────────────────────────────────────────────────────

export type ApprovalRequestType =
  | 'budget_increase'
  | 'prompt_promote'
  | 'tool_allow'
  | 'capture_policy_full'
  | 'shadow_routing'
  | 'premium_model_use'
  | 'external_mcp_tool'
  | 'long_agent_session'
  | 'sensitive_export'
  | 'route_policy_change'

export type ApprovalStatus = 'pending' | 'approved' | 'denied' | 'cancelled'

export interface ApprovalResponse {
  id: string
  workspace_id: string
  request_type: ApprovalRequestType
  request: Record<string, unknown>
  status: ApprovalStatus
  requested_by: string | null
  decided_by: string | null
  decided_at: string | null
  decision_note: string | null
  created_at: string
}

export interface ApprovalList {
  items: ApprovalResponse[]
  total: number
}

export interface ApprovalSummary {
  pending: number
  approved: number
  denied: number
  cancelled: number
}

// ── Audit Log ─────────────────────────────────────────────────────────────────

export interface AuditEvent {
  id: string
  workspace_id: string
  actor_user_id: string | null
  actor_api_key_prefix: string | null
  action: string
  target_type: string | null
  target_id: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  created_at: string
}

export interface AuditEventList {
  items: AuditEvent[]
  total: number
  limit: number
  offset: number
}

// ── OTLP ──────────────────────────────────────────────────────────────────────

export interface OtlpWindowStats {
  batches: number
  traces: number
  spans: number
}

export interface OtlpStats {
  last_24h: OtlpWindowStats
  last_7d: OtlpWindowStats
}

export interface OtlpBatchResponse {
  id: string
  created_at: string | null
  trace_count: number
  span_count: number
  status: string
  error: string | null
  content_type: string
}

export interface OtlpBatchList {
  items: OtlpBatchResponse[]
  total: number
  limit: number
  offset: number
}

// ── Retention ─────────────────────────────────────────────────────────────────

export type RetentionResourceType = 'runs' | 'spans' | 'payloads' | 'provider_calls'
export type RetentionActionType = 'delete' | 'scrub'
export type RetentionScopeType = 'workspace' | 'end_user'

export interface RetentionPolicy {
  id: string
  workspace_id: string
  resource_type: RetentionResourceType
  action: RetentionActionType
  scope: RetentionScopeType
  scope_value: string | null
  max_age_days: number | null
  is_active: boolean
  created_at: string
  last_run_at: string | null
  last_purged_count: number | null
}

export interface RetentionPolicyList {
  items: RetentionPolicy[]
  total: number
}

export interface PurgeResult {
  resource_type: string
  action: string
  scope: string
  scope_value: string | null
  affected_rows: number
  dry_run: boolean
  cutoff: string | null
}

// ── Phase 28: Warehouse Export ────────────────────────────────────────────────

export type WarehouseProvider = 's3' | 'gcs' | 'r2'
export type WarehouseFormat = 'jsonl' | 'parquet'
export type ExportJobStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface WarehouseDestination {
  id: string
  workspace_id: string
  name: string
  provider: WarehouseProvider
  bucket: string
  prefix: string
  region: string | null
  endpoint_url: string | null
  access_key_id: string
  format: WarehouseFormat
  resources: string[]
  is_active: boolean
  created_at: string
  last_export_at: string | null
}

export interface WarehouseDestinationList {
  items: WarehouseDestination[]
  total: number
}

export interface WarehouseDestinationCreate {
  name: string
  provider: WarehouseProvider
  bucket: string
  prefix?: string
  region?: string | null
  endpoint_url?: string | null
  access_key_id: string
  secret_access_key: string
  format?: WarehouseFormat
  resources?: string[]
  is_active?: boolean
}

export interface WarehouseDestinationUpdate {
  name?: string
  prefix?: string
  region?: string | null
  endpoint_url?: string | null
  access_key_id?: string
  secret_access_key?: string
  format?: WarehouseFormat
  resources?: string[]
  is_active?: boolean
}

export interface ConnectionTestResult {
  ok: boolean
  error: string | null
}

export interface ExportJob {
  id: string
  workspace_id: string
  destination_id: string
  export_date: string
  status: ExportJobStatus
  resources: string[]
  file_keys: Record<string, string> | null
  row_counts: Record<string, number> | null
  error: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface ExportJobList {
  items: ExportJob[]
  total: number
}

// ── Email Preferences ──────────────────────────────────────────────────────────

export interface EmailPreference {
  id: string
  workspace_id: string
  report_frequency: string
  report_hour: number
  report_timezone: string
  report_recipient_mode: string
  report_recipients: string | null
  report_last_sent_at: string | null
  alerts_enabled: boolean
  approvals_enabled: boolean
  reconciliation_enabled: boolean
  budget_alerts_enabled: boolean
  billing_closed_enabled: boolean
  score_regression_enabled: boolean
  dispute_flagged_enabled: boolean
  created_at: string
  updated_at: string
}

export interface EmailLogItem {
  id: string
  to_email: string
  subject: string
  event_type: string
  status: string
  error_message: string | null
  sent_at: string
}

export interface EmailLogList {
  items: EmailLogItem[]
  total: number
}

export interface OpsFeatureStatus {
  email_enabled: boolean
  email_reports_enabled: boolean
  backup_enabled: boolean
  smtp_configured: boolean
}


export interface BillingWebhookConfig {
  id: string
  workspace_id: string
  url: string
  label: string
  enabled: boolean
  created_at: string
}

export interface BillingWebhookConfigList {
  items: BillingWebhookConfig[]
}

export interface BillingWebhookDelivery {
  id: string
  webhook_config_id: string
  billing_period_id: string
  attempt: number
  status: 'pending' | 'success' | 'failed'
  response_status: number | null
  delivered_at: string | null
  created_at: string
}

export interface BillingWebhookDeliveryList {
  items: BillingWebhookDelivery[]
}

// ── Kafka Export ───────────────────────────────────────────────────────────────

export type KafkaSecurityProtocol = 'PLAINTEXT' | 'SSL' | 'SASL_PLAINTEXT' | 'SASL_SSL'
export type KafkaSaslMechanism = 'PLAIN' | 'SCRAM-SHA-256' | 'SCRAM-SHA-512'
export type KafkaEventType =
  | 'run.started'
  | 'run.completed'
  | 'run.failed'
  | 'gateway.request.completed'
  | 'gateway.request.rejected'
  | 'budget.threshold_crossed'
  | 'alert.fired'
  | 'budget.breached'
  | 'optimization.applied'
  | 'route.changed'
  | 'mcp.tool.called'
  | 'mcp.tool.blocked'
  | 'approval.requested'
  | 'approval.decided'
  | 'email.report.sent'
  | 'backup.completed'
  | 'backup.failed'
  | 'compliance.export.ready'

export interface KafkaExportConfig {
  id: string
  workspace_id: string
  label: string
  bootstrap_servers: string
  topic_prefix: string
  security_protocol: KafkaSecurityProtocol
  sasl_mechanism: KafkaSaslMechanism | null
  sasl_username: string | null
  ssl_ca_cert: string | null
  event_types: KafkaEventType[]
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface KafkaExportConfigList {
  items: KafkaExportConfig[]
}

export interface KafkaExportDelivery {
  id: string
  config_id: string
  event_type: string
  topic: string
  status: 'pending' | 'success' | 'failed'
  error_detail: string | null
  attempt: number
  delivered_at: string | null
  created_at: string
}

export interface KafkaExportDeliveryList {
  items: KafkaExportDelivery[]
}

export interface KafkaTestResult {
  ok: boolean
  error: string | null
  topic: string | null
}

// ── Eval Experiments & Datasets ────────────────────────────────────────────────

export interface DatasetItem {
  input: string
  expected_output: string | null
  metadata: Record<string, unknown>
}

export interface EvalDataset {
  id: string
  workspace_id: string
  name: string
  description: string | null
  source: string
  item_count: number
  items: DatasetItem[]
  created_at: string
  updated_at: string
}

export interface EvalDatasetList {
  items: EvalDataset[]
}

export interface ExperimentModelConfig {
  model: string
  provider: string
  label: string | null
}

export interface EvalExperiment {
  id: string
  workspace_id: string
  dataset_id: string | null
  name: string
  description: string | null
  prompt_name: string | null
  prompt_version: number | null
  evaluator_ids: string[]
  models: ExperimentModelConfig[]
  status: 'pending' | 'running' | 'completed' | 'failed'
  results: Record<string, unknown> | null
  run_count: number
  scores_created: number
  started_at: string | null
  completed_at: string | null
  created_by: string | null
  created_at: string
}

export interface EvalExperimentList {
  items: EvalExperiment[]
}

// ── GitHub Sync ────────────────────────────────────────────────────────────────

export interface GithubConfig {
  id: string
  workspace_id: string
  repo: string
  branch: string
  path_prefix: string
  auto_sync: boolean
  last_sync_at: string | null
  last_sync_status: string | null
  last_sync_message: string | null
  created_at: string
}

export interface GithubSyncResult {
  pushed: number
  pulled: number
  skipped: number
  errors: string[]
  synced_at: string
}

// ── Phase 3: Scoped summary ─────────────────────────────────────────────────

export interface IntentCount {
  intent: string
  count: number
  cost_usd: string
}

export interface ScopedSummary {
  scope: string
  total_cost_usd: string
  total_savings_usd: string
  total_input_tokens: number
  total_output_tokens: number
  run_count: number
  call_count: number
  workspace_count: number
  active_users: number
  avg_cost_per_run: string | null
  top_intents: IntentCount[]
  top_models: ModelSpend[]
  cost_delta_pct: string | null
}

// ── Phase 3: Savings analytics ──────────────────────────────────────────────

export interface SavingsByCategory {
  category: string
  savings_usd: string
  call_count: number
}

export interface SavingsTimeline {
  period: string
  savings_usd: string
  baseline_cost_usd: string
  actual_cost_usd: string
}

export interface SavingsResponse {
  total_savings_usd: string
  total_baseline_usd: string
  total_actual_usd: string
  savings_rate_pct: string | null
  by_category: SavingsByCategory[]
  timeline: SavingsTimeline[]
}

// ── Phase 3: Optimization opportunities ─────────────────────────────────────

export interface OptimizationOpportunity {
  optimization_type: string
  potential_savings_usd: string
  affected_calls: number
  description: string
}

export interface OptimizationOpportunitiesResponse {
  items: OptimizationOpportunity[]
  total_potential_savings_usd: string
}

// ── Phase 3: Trends ─────────────────────────────────────────────────────────

export interface TrendPoint {
  period: string
  cost_usd: string
  run_count: number
  call_count: number
  tokens: number
  avg_latency_ms: string | null
  savings_usd: string
}

export interface TrendMetric {
  name: string
  current: string
  previous: string
  change_pct: string | null
}

export interface TrendsResponse {
  points: TrendPoint[]
  metrics: TrendMetric[]
  granularity: string
}

// ── Phase 3: Request explorer ───────────────────────────────────────────────

export interface RequestRecord {
  id: string
  run_id: string
  provider: string
  model: string
  intent: string | null
  cost_usd: string | null
  baseline_cost_usd: string | null
  savings_usd: string | null
  optimization_applied: string | null
  input_tokens: number | null
  output_tokens: number | null
  latency_ms: number | null
  status: string
  created_at: string
}

export interface RequestExplorerResponse {
  items: RequestRecord[]
  total: number
  page: number
  page_size: number
}

// ── Phase 8: Engineering metrics ────────────────────────────────────────────

export interface CostByDimension {
  name: string
  cost_usd: string
  call_count: number
}

export interface QualityFunnel {
  total_requests: number
  successful: number
  routed: number
  cached: number
  with_outcome: number
  positive_outcome: number
}

export interface LifecycleStage {
  stage: string
  count: number
  pct: string
}

export interface EngineeringMetrics {
  avg_latency_ms: string | null
  p95_latency_ms: string | null
  error_pct: string
  retry_pct: string
  cache_pct: string
  total_requests: number
  total_tokens: number
  avg_cost_per_request: string | null
  cost_by_feature: CostByDimension[]
  cost_by_model: CostByDimension[]
  cost_by_tool: CostByDimension[]
  quality_funnel: QualityFunnel
  lifecycle_stages: LifecycleStage[]
}

// ── Optimization Simulator ────────────────────────────────────────────────────

export interface SimulationRequest {
  intent?: string | null
  current_model?: string | null
  proposed_model?: string | null
  current_provider?: string | null
  proposed_provider?: string | null
  enable_cache?: boolean
  enable_compression?: boolean
  workspace_id?: string | null
  from_dt?: string | null
  to_dt?: string | null
}

export interface SimulationImpact {
  label: string
  current_value: string
  projected_value: string
  delta_pct: string | null
}

export interface SimulationResult {
  affected_requests: number
  current_cost_usd: string
  projected_cost_usd: string
  projected_savings_usd: string
  savings_pct: string
  current_avg_latency_ms: string | null
  projected_latency_ms: string | null
  latency_delta_pct: string | null
  quality_risk: string
  confidence: string
  impacts: SimulationImpact[]
  description: string
}

// ── Phase 13: Policy Dry Run ─────────────────────────────────────────────────

export interface PolicyDryRunDetail {
  budget_remaining_usd: string | null
  budget_limit_usd: string | null
  budget_period: string | null
  tool_registered: boolean | null
  tool_policy_setting: string | null
  gateway_routes_found: number | null
  gateway_route_aliases: string[] | null
  score_latest_value: string | null
  score_gate_threshold: string | null
}

export interface PolicyCheckResponse {
  allowed: boolean
  reasons: string[]
  detail: PolicyDryRunDetail | null
}

export interface PolicyDryRunReport {
  id: string
  workspace_id: string
  total_checked: number
  would_block: number
  would_allow: number
  would_reroute: number
  items: PolicyDryRunReportItem[]
  created_at: string
}

export interface PolicyDryRunReportItem {
  request_id: string
  action: 'block' | 'allow' | 'reroute'
  reasons: string[]
  model: string | null
  end_user_id: string | null
  cost_usd: string | null
}

// ── Phase 13: Runbooks ───────────────────────────────────────────────────────

export interface RunbookResponse {
  id: string
  workspace_id: string
  run_id: string
  severity: string
  summary: Record<string, unknown>
  generated_at: string
}

export interface RunbookList {
  items: RunbookResponse[]
  total: number
}

// ── Phase 13: Model Scorecards ───────────────────────────────────────────────

export interface ModelScorecard {
  model: string
  provider: string | null
  total_cost_usd: string
  call_count: number
  avg_cost_per_call: string
  avg_latency_ms: string | null
  p95_latency_ms: string | null
  error_rate: string
  cache_hit_rate: string | null
  avg_quality_score: string | null
  input_tokens: number
  output_tokens: number
  acceptance_rate: string | null
  hallucination_flags: number | null
  retry_rate: string | null
  user_feedback_score: string | null
  eval_score: string | null
  recommendation: string | null
}

export interface ModelScorecardList {
  items: ModelScorecard[]
  from_dt: string | null
  to_dt: string | null
}

export interface ModelScoreTrend {
  date: string
  model: string
  avg_quality_score: string | null
  error_rate: string
  avg_latency_ms: string | null
  cost_usd: string
}

export interface ModelScoreTrendList {
  items: ModelScoreTrend[]
}

// ── Phase 13: Onboarding ─────────────────────────────────────────────────────

export interface OnboardingStatus {
  has_org: boolean
  has_workspace: boolean
  has_api_key: boolean
  has_first_run: boolean
  has_gateway_route: boolean
  has_budget: boolean
  has_alert_rule: boolean
  completed: number
  total: number
  pct: number
}

// ── Phase 13: Chargeback Reports ────────────────────────────────────────────

export interface ChargebackReport {
  period: string
  total_cost_usd: string
  breakdown: ChargebackBreakdownItem[]
}

export interface ChargebackBreakdownItem {
  dimension: string
  dimension_value: string
  cost_usd: string
  pct_of_total: string
  budget_usd: string | null
  variance_usd: string | null
}

export interface ChargebackReportList {
  items: ChargebackReport[]
}

// ── Phase 13: Data Capture Policy Studio ────────────────────────────────────

export interface CapturePolicyScope {
  scope_type: 'org' | 'workspace' | 'api_key' | 'model_route' | 'user' | 'intent' | 'agent'
  scope_id: string
  privacy_mode: string
  sampled_rate: string | null
}

export interface RetentionPreview {
  privacy_mode: string
  estimated_storage_mb_per_month: string
  fields_captured: string[]
  fields_redacted: string[]
  compliance_notes: string[]
}

export interface PiiTestResult {
  input_text: string
  detected_pii: PiiDetection[]
  redacted_text: string
}

export interface PiiDetection {
  type: string
  value: string
  start: number
  end: number
  confidence: string
}

// ── Phase 13: Auto-Approval Policies ────────────────────────────────────────

export interface AutoApprovalPolicy {
  id: string
  request_type: ApprovalRequestType
  condition: string
  created_at: string
  created_by: string | null
}

export interface AutoApprovalPolicyList {
  items: AutoApprovalPolicy[]
}

// ── Phase 13: Governance Audit Pack ─────────────────────────────────────────

export interface GovernanceAuditPack {
  generated_at: string
  period_from: string
  period_to: string
  summary: GovernanceAuditSummary
  model_usage: GovernanceModelUsage[]
  policy_enforcements: GovernancePolicyAction[]
  approvals: GovernanceApprovalRecord[]
  data_capture_policies: GovernanceCapturePolicy[]
  budget_alerts: GovernanceBudgetAlert[]
}

export interface GovernanceAuditSummary {
  total_requests: number
  total_cost_usd: string
  models_used: number
  users_active: number
  policies_enforced: number
  approvals_processed: number
  alerts_fired: number
}

export interface GovernanceModelUsage {
  model: string
  provider: string | null
  request_count: number
  cost_usd: string
  first_used: string
  last_used: string
}

export interface GovernancePolicyAction {
  policy_type: string
  action: string
  count: number
  last_triggered: string
}

export interface GovernanceApprovalRecord {
  request_type: string
  status: string
  requested_by: string | null
  decided_by: string | null
  created_at: string
}

export interface GovernanceCapturePolicy {
  scope: string
  privacy_mode: string
  retention_days: number | null
}

export interface GovernanceBudgetAlert {
  budget_name: string
  threshold_pct: number
  triggered_at: string
  current_spend_usd: string
  limit_usd: string
}

// -- Phase 14: Guardrails, Content Safety & Policy Engine --

export interface GuardrailRuleResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  mode: string
  rule_type: string
  logic: string | null
  config: Record<string, unknown>
  severity: string
  priority: number
  status: string
  template_id: string | null
  created_at: string
  updated_at: string
}

export interface GuardrailRuleList {
  items: GuardrailRuleResponse[]
  total: number
}

export interface GuardrailRuleCreate {
  name: string
  description?: string | null
  mode?: string
  rule_type?: string
  logic?: string | null
  config?: Record<string, unknown>
  severity?: string
  priority?: number
  status?: string
  template_id?: string | null
}

export interface GuardrailRuleUpdate {
  name?: string | null
  description?: string | null
  mode?: string | null
  logic?: string | null
  config?: Record<string, unknown> | null
  severity?: string | null
  priority?: number | null
  status?: string | null
}

export interface GuardrailTestInput {
  texts: string[]
  images?: string[]
  tools?: Record<string, unknown>[]
  tool_calls?: Record<string, unknown>[]
  structured_messages?: Record<string, unknown>[]
  model?: string | null
  user_id?: string | null
  team_id?: string | null
  end_user_id?: string | null
  metadata?: Record<string, unknown>
}

export interface GuardrailTestResult {
  guardrail_id: string
  guardrail_name: string
  decision: string
  reason: string | null
  latency_ms: number
  modified_texts: string[] | null
  modified_images: string[] | null
  modified_tool_calls: Record<string, unknown>[] | null
  error: string | null
}

export interface GuardrailTestResponse {
  results: GuardrailTestResult[]
  overall_decision: string
  total_latency_ms: number
}

export interface GuardrailEventResponse {
  id: string
  workspace_id: string
  guardrail_rule_id: string
  guardrail_name: string
  mode: string
  decision: string
  reason: string | null
  latency_ms: number
  request_metadata: Record<string, unknown>
  gateway_request_id: string | null
  created_at: string
}

export interface GuardrailEventList {
  items: GuardrailEventResponse[]
  total: number
}

export interface GuardrailStats {
  total_evaluations: number
  total_blocks: number
  total_modifications: number
  total_allows: number
  block_rate: number
  avg_latency_ms: number
  top_triggered: { name: string; count: number }[]
  by_decision: Record<string, number>
}

export interface ContentFilterStatus {
  filter_name: string
  description: string
  severity: string
  enabled: boolean
  category: string
}

export interface ContentFilterListResponse {
  filters: ContentFilterStatus[]
}

export interface ContentFilterConfig {
  filter_name: string
  severity?: string
  enabled?: boolean
}

export interface GuardrailTemplate {
  template_id: string
  name: string
  description: string
  mode: string
  default_logic: string
  default_config: Record<string, unknown>
  category: string
}

export interface PartnerGuardrailResponse {
  id: string
  workspace_id: string
  provider: string
  name: string
  mode: string
  endpoint_url: string | null
  config: Record<string, unknown>
  timeout_ms: number
  fallback_action: string
  priority: number
  status: string
  last_health_check: string | null
  health_status: string | null
  total_calls: number
  total_cost_usd: number
  created_at: string
  updated_at: string
}

export interface PartnerGuardrailList {
  items: PartnerGuardrailResponse[]
  total: number
}

export interface GuardrailTestCaseResponse {
  id: string
  workspace_id: string
  guardrail_rule_id: string
  name: string
  input_text: string
  input_metadata: Record<string, unknown>
  expected_decision: string
  created_at: string
}

export interface GuardrailTestCaseList {
  items: GuardrailTestCaseResponse[]
  total: number
}

export interface GuardrailRegressionResult {
  test_case_id: string
  test_case_name: string
  expected_decision: string
  actual_decision: string
  passed: boolean
  latency_ms: number
  reason: string | null
}

export interface GuardrailRegressionReport {
  guardrail_rule_id: string
  guardrail_name: string
  total_cases: number
  passed: number
  failed: number
  results: GuardrailRegressionResult[]
}
