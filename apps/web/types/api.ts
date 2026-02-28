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
  status: 'pass' | 'fail'
  provider_calls_sum: string
  usage_daily_sum: string
  delta_pct: string
  orphaned_calls: number
  duplicate_calls: number
  issues: string[]
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

export interface ExperimentConfig { model: string; label?: string }
export interface DatasetResponse { id: string; name: string; source: string; run_ids: string[]; run_count: number; created_at: string }
export interface DatasetList { items: DatasetResponse[] }
export interface ExperimentResponse { id: string; dataset_id: string; name: string; configs: ExperimentConfig[]; status: string; estimated_cost_usd: string | null; created_at: string }
export interface ExperimentList { items: ExperimentResponse[] }
export interface ConfigResult { model: string; label?: string; run_count: number; total_input_tokens: number; total_output_tokens: number; projected_cost_usd: string; avg_cost_per_run: string; pricing_found: boolean }
export interface ConfigDelta { config_a: string; config_b: string; cost_delta_pct: string | null }
export interface ExperimentResults { experiment_id: string; experiment_name: string; status: string; dataset_run_count: number; configs: ConfigResult[]; deltas: ConfigDelta[]; completed_at: string | null }
