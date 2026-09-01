export interface RunListItem {
  id: string
  api_key_id: string | null
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
  api_key_id: string | null
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
  primary_model: string | null
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

export interface GovernanceToolEvidence {
  tool_name: string
  tool_type: string
  status: string
  risk_score: number | null
  registry_policy: string | null
  registry_runtime_enforcement: boolean
  matched_policy_count: number
  matched_policy_names: string[]
  matched_policy_actions: string[]
}

export interface GovernanceSecurityEvidence {
  id: string
  event_type: string
  tool_name: string | null
  end_user_id: string | null
  detected_at: string
  details: Record<string, unknown>
}

export interface GovernanceAlertEvidence {
  id: string
  rule_id: string
  rule_name: string
  fired_at: string
  metric_value: string
  resolved_at: string | null
}

export interface GovernanceAuditEvidence {
  id: string
  action: string
  target_type: string | null
  target_id: string | null
  created_at: string
}

export interface RunGovernanceContextResponse {
  run_id: string
  tags: string[]
  tool_evidence: GovernanceToolEvidence[]
  security_events: GovernanceSecurityEvidence[]
  alert_evidence: GovernanceAlertEvidence[]
  audit_events: GovernanceAuditEvidence[]
  governance_pack_summary: Record<string, number>
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
  scope_type:
    | 'workspace'
    | 'end_user'
    | 'feature_tag'
    | 'app'
    | 'access_group'
    | 'api_key'
    | 'provider_profile'
  scope_id: string | null
  scope_display_name: string | null
  period_type: 'daily' | 'monthly' | 'total'
  limit_usd: string
  action: 'notify' | 'block' | 'downgrade' | 'throttle' | 'fallback'
  downgrade_to_model: string | null
  is_active: boolean
  created_at: string
  current_spend_usd: string
  pct_used: string
  breakdown?: BudgetUserBreakdown[]
}

export interface BudgetUserBreakdown {
  end_user_id: string
  cost_usd: string
  run_count: number
  call_count: number
  pct_of_total: string
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
  net_cost_usd: string | null
  currency: string
  exchange_rate_to_usd: string
  snapshot_hash: string | null
  closed_at: string | null
  created_at: string
}

export interface BillingPeriodList {
  items: BillingPeriod[]
}

export interface ChargebackRule {
  id: string
  allocation_type: 'cost_center' | 'env'
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
  warnings: string[]
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
  gross_cost_usd: string
  net_cost_usd: string
  total_adjustments_usd: string
  total_cost_usd: string
  by_application: BreakdownApp[]
  adjustments: BillingAdjustment[]
}

export interface UsageSnapshot {
  id: string
  billing_period_id: string
  signature: string
  signing_key_id: string
  created_at: string
}

export interface BillingAdjustment {
  id: string
  billing_period_id: string
  adjustment_type: 'credit' | 'refund' | 'prepaid_deduction' | 'surcharge'
  amount_usd: string
  description: string | null
  reference_id: string | null
  created_by: string | null
  created_at: string
}

export interface BillingAdjustmentList {
  items: BillingAdjustment[]
  total_credits_usd: string
  total_surcharges_usd: string
  net_adjustment_usd: string
}

export interface SharedCostAllocation {
  label: string
  cost_center_id: string | null
  weight: string | null
  denominator_value: string | null
}

export interface SharedCostPolicy {
  id: string
  workspace_id: string
  name: string
  description: string | null
  formula_type: 'equal_split' | 'proportional' | 'fixed_weight'
  allocations: SharedCostAllocation[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SharedCostPolicyList {
  items: SharedCostPolicy[]
  total: number
}

export interface SharedCostAllocationPreview {
  label: string
  cost_center_id: string | null
  allocated_usd: string
}

export interface SharedCostAllocationResult {
  policy_id: string
  policy_name: string
  pool_usd: string
  formula_type: 'equal_split' | 'proportional' | 'fixed_weight'
  allocations: SharedCostAllocationPreview[]
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
export interface LedgerVerificationSummary { total_snapshots: number; ok_count: number; tampered_count: number; pending_count: number; latest_status: string | null }
export interface LedgerClosedPeriodSummary { id: string; period_start: string; period_end: string; total_cost_usd: string | null; net_cost_usd: string | null; closed_at: string | null }
export interface LedgerChargebackSummary { period: string; dimension: string; total_cost_usd: string; covered_cost_usd: string; unallocated_cost_usd: string; breakdown_count: number }
export interface LedgerBackupEvidenceSummary { id: string; bucket: string; manifest_key: string | null; checksum: string | null; integrity_status: string; artifact_count: number; created_at: string }
export interface LedgerClosureSummary { generated_at: string; readiness_status: string; evidence_score: number; missing_evidence: string[]; latest_snapshot: LedgerSnapshotResponse | null; verification: LedgerVerificationSummary; latest_closed_period: LedgerClosedPeriodSummary | null; chargeback: LedgerChargebackSummary | null; latest_backup_snapshot: LedgerBackupEvidenceSummary | null; recent_audit_event_count: number }

// ── Phase 11 — Tools ──────────────────────────────────────────────────────────

export interface ToolRegistryResponse { id: string; workspace_id: string; tool_name: string; policy: string; runtime_enforcement: boolean; description: string | null; created_at: string; updated_at: string }
export interface ToolRegistryList { items: ToolRegistryResponse[] }
export interface SecurityEventResponse { id: string; workspace_id: string; event_type: string; tool_name: string | null; end_user_id: string | null; run_id: string | null; details: Record<string, unknown>; detected_at: string }
export interface SecurityEventList { items: SecurityEventResponse[] }

// ── Phase 11 — Privacy ────────────────────────────────────────────────────────

export interface CapturePolicyResponse { id: string; workspace_id: string; privacy_mode: string; sampled_rate: string | null; updated_at: string; created_at: string }

// ── Phase 12 — Settings ────────────────────────────────────────────────────────

export interface ApiKeyResponse { id: string; workspace_id: string; workspace_name?: string | null; budget_tier_id: string | null; key_prefix: string; name: string | null; scopes: string[]; is_session: boolean; created_at: string; created_by: string | null; ownership_type: string; owner_reference: string | null }
export interface ApiKeyCreateResponse extends ApiKeyResponse { key: string }
export interface ApiKeyUpdateRequest { name?: string | null; ownership_type?: string | null; owner_reference?: string | null; scopes?: string[] }

// ── Phase 12 — Providers ───────────────────────────────────────────────────────

export interface ProviderPricingResponse { id: string; provider: string; model: string; input_cost_per_1m: string; output_cost_per_1m: string; cached_input_cost_per_1m: string | null; tags: string[]; display_name: string | null; effective_from: string; effective_to: string | null; workspace_id: string | null; budget_count: number; active_budget_count: number; created_at: string }
export interface ProviderPricingList { items: ProviderPricingResponse[] }
export interface PricingImportResult { inserted: number; updated: number; unchanged: number; total: number; providers: string[]; tags: string[]; errors: string[] }

// ── Phase 14 — Integrations ────────────────────────────────────────────────────

export interface ExportRow { date: string; provider: string; model: string; cost_usd: string; input_tokens: number; output_tokens: number; call_count: number }
export interface AnalyticsExport { items: ExportRow[] }
export interface SlackTestResponse { ok: boolean; error: string | null }

// ── Budget notification types ──────────────────────────────────────────────────
export interface NotificationResponse { id: string; channel: string; destination_url: string; events: string[]; is_active: boolean; created_at: string }
export interface NotificationList { items: NotificationResponse[] }
export interface NotificationTestResult { ok: boolean; error: string | null }
export interface NotificationDelivery { id: string; notification_id: string; event_type: string; attempt: number; status: string; response_status: number | null; error_detail: string | null; delivered_at: string | null; created_at: string }
export interface NotificationDeliveryList { items: NotificationDelivery[] }
export interface PlatformWebhookDefaultStatus { channel: string; ok: boolean; error: string | null }
export interface PlatformWebhookDefaults { generic_webhook_configured: boolean; slack_webhook_configured: boolean; events: string[]; generic_webhook_url: string | null; slack_webhook_url: string | null; created_at?: string | null; updated_at?: string | null }
export interface PlatformWebhookDefaultsTestResult { ok: boolean; message: string; results: PlatformWebhookDefaultStatus[] }

// ── Chargeback rule types ──────────────────────────────────────────────────────
export interface ChargebackRuleResponse {
  id: string
  allocation_type: string
  dimension: string
  weight: string
  cost_center_id: string | null
  status: 'active' | 'inactive' | 'pending_approval' | 'denied'
  approval_id: string | null
  created_at: string
}
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
  page: number
  page_size: number
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
  metric: 'error_rate' | 'p95_latency' | 'avg_score' | 'spend_velocity' | 'model_availability' | 'gateway_overhead_p95' | 'budget_utilization' | 'budget_breach_count'
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
  routing_group_id: string | null
  alias: string
  routing_group_name: string | null
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
  fallback_config: Record<string, unknown> | null
  required_tags: string[]
  excluded_tags: string[]
  retry_count: number
  timeout_ms: number | null
  cooldown_seconds: number
  cooldown_until: string | null
  region: string | null
  mirror_config: Record<string, unknown> | null
  health_auto_disable: boolean
  last_health_check_at: string | null
  consecutive_health_failures: number
  disabled_reason: string | null
  deployment_status: string
  health_summary: string | null
  created_at: string
}

export interface GatewayRouteList {
  items: GatewayRoute[]
}

export type GatewayRoutingGroupStrategy = 'manual' | 'latency_optimized' | 'round_robin'

export interface GatewayRoutingGroupRouteSummary {
  id: string
  alias: string
  provider: string
  target_model: string
  priority: number
  region: string | null
  required_tags: string[]
  excluded_tags: string[]
  is_active: boolean
}

export interface GatewayRoutingGroup {
  id: string
  workspace_id: string
  alias: string
  name: string
  description: string | null
  match_tags: string[]
  default_tags: string[]
  strategy_type: GatewayRoutingGroupStrategy
  strategy_config: Record<string, unknown> | null
  is_active: boolean
  route_count: number
  routes: GatewayRoutingGroupRouteSummary[]
  created_at: string
  updated_at: string
}

export interface GatewayRoutingGroupList {
  items: GatewayRoutingGroup[]
}

export interface GatewayRoutingStrategyComparisonItem {
  routing_group_id: string | null
  alias: string
  group_name: string
  strategy_type: GatewayRoutingGroupStrategy
  total_requests: number
  cache_hit_rate: string
  avg_latency_ms: string | null
  error_rate: string
  active_routes: number
  default_tags: string[]
  match_tags: string[]
}

export interface GatewayRoutingStrategyComparison {
  items: GatewayRoutingStrategyComparisonItem[]
}

export interface GatewayDeploymentHealthItem {
  route_id: string
  alias: string
  provider: string
  target_model: string
  deployment_status: string
  health_summary: string | null
  last_health_check_at: string | null
  consecutive_health_failures: number
}

export interface GatewayDeploymentHealthList {
  items: GatewayDeploymentHealthItem[]
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

export interface GatewayRateLimitTier {
  key: string
  name: string
  description: string
  rpm: number
  endpoints: string[]
}

export interface GatewayRateLimitOverview {
  tiers: GatewayRateLimitTier[]
  route_rate_limited_count: number
  route_rate_limited_aliases: string[]
  passthrough_rate_limited_count: number
  passthrough_rate_limited_slugs: string[]
  budget_tier_rate_limited_count: number
  model_budget_rate_limited_count: number
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

export interface GatewayPassThroughEndpoint {
  id: string
  workspace_id: string
  slug: string
  path_prefix: string
  upstream_base_url: string
  auth_type: string | null
  auth_config: Record<string, unknown>
  header_config: Record<string, unknown>
  default_query: Record<string, unknown>
  timeout_ms: number
  rate_limit_rpm: number | null
  cost_per_call_usd: string | null
  is_active: boolean
  created_at: string
}

export interface GatewayPassThroughEndpointList {
  items: GatewayPassThroughEndpoint[]
}

export interface GatewayPassThroughTestResult {
  ok: boolean
  status_code: number
  latency_ms: number
  target_url: string
  response_preview: string | null
  headers: Record<string, string>
}

export interface GatewayPassThroughEndpointStats {
  endpoint_id: string
  slug: string
  total_requests: number
  success_count: number
  error_count: number
  avg_latency_ms: string | null
  p50_latency_ms: string | null
  p95_latency_ms: string | null
  p99_latency_ms: string | null
  last_hour_requests: number
  rate_limit_rpm: number | null
  rate_limit_utilization_pct: string | null
  estimated_total_cost_usd: string | null
  estimated_24h_cost_usd: string | null
}

export interface GatewayPassThroughEndpointStatsList {
  items: GatewayPassThroughEndpointStats[]
}

export interface GatewayBenchmarkComparisonItem {
  alias: string
  request_count: number
  throughput_rpm: string
  p50_gateway_overhead_ms: string | null
  p95_gateway_overhead_ms: string | null
  p99_gateway_overhead_ms: string | null
  avg_provider_latency_ms: string | null
  avg_end_to_end_latency_ms: string | null
  avg_gateway_overhead_ms: string | null
  overhead_vs_provider_pct: string | null
}

export interface GatewayBenchmarkComparisonList {
  items: GatewayBenchmarkComparisonItem[]
}

export type RoutingPolicyType =
  | 'manual'
  | 'cost_optimized'
  | 'latency_optimized'
  | 'quality_optimized'
  | 'weighted'
  | 'canary'
  | 'ab_test'
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

export interface RoutingPolicyVariantMetrics {
  route_id: string
  label: string
  allocation_pct: string
  total_requests: number
  success_rate: string
  error_rate: string
  avg_latency_ms: string | null
  avg_input_tokens: string | null
  avg_output_tokens: string | null
}

export interface RoutingPolicyAnalysis {
  policy_id: string
  alias: string
  policy_type: RoutingPolicyType
  winner_route_id: string | null
  winner_label: string | null
  confidence: string
  significance_p_value: string | null
  auto_promoted: boolean
  summary: string
  variants: RoutingPolicyVariantMetrics[]
}

export interface RoutingPolicyActionResult {
  policy_id: string
  policy_type: RoutingPolicyType
  summary: string
  config: Record<string, unknown>
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

export interface OrgFinanceWorkspaceSummary {
  workspace_id: string
  workspace_name: string
  spend_30d_usd: string
  active_budget_count: number
  total_budget_limit_usd: string
  active_override_count: number
  active_notification_count: number
  open_billing_periods: number
  closed_billing_periods: number
  overdue_billing_periods: number
  chargeback_rule_count: number
  chargeback_status: string
  ledger_readiness_status: string
  ledger_evidence_score: number
}

export interface OrgFinanceSummary {
  workspaces: OrgFinanceWorkspaceSummary[]
  org_spend_30d_usd: string
  org_total_budget_limit_usd: string
  active_budget_count: number
  active_override_count: number
  active_notification_count: number
  open_billing_period_count: number
  closed_billing_period_count: number
  overdue_billing_period_count: number
  chargeback_rule_count: number
  chargeback_ready_workspace_count: number
  ledger_readiness_status: string
  ledger_ready_workspace_count: number
  ledger_partial_workspace_count: number
  ledger_at_risk_workspace_count: number
}


export interface OrgRuntimeWorkspaceSummary {
  workspace_id: string
  workspace_name: string
  active_route_count: number
  distinct_provider_count: number
  routing_policy_count: number
  active_guardrail_count: number
  rate_limited_route_count: number
}

export interface OrgRuntimeSummary {
  workspaces: OrgRuntimeWorkspaceSummary[]
  total_active_routes: number
  total_distinct_providers: number
  total_routing_policies: number
  total_active_guardrails: number
  total_rate_limited_routes: number
}

export interface OrgObserveWorkspaceSummary {
  workspace_id: string
  workspace_name: string
  run_count_30d: number
  request_count_30d: number
  distinct_model_count: number
  error_count_30d: number
  active_alert_rule_count: number
}

export interface OrgObserveSummary {
  workspaces: OrgObserveWorkspaceSummary[]
  total_run_count_30d: number
  total_request_count_30d: number
  total_distinct_models: number
  total_error_count_30d: number
  total_active_alert_rules: number
}

export interface OrgGovernanceSummary {
  tool_count: number
  tool_policy_count: number
  approval_count: number
  audit_event_count: number
  tag_count: number
  mcp_server_count: number
  search_tool_count: number
}

export interface UserBudgetExposure {
  budget_id: string
  scope_type: string
  scope_id: string | null
  period_type: string
  limit_usd: string
  is_active: boolean
}

export interface UserFinanceSummary {
  user_id: string
  email: string
  full_name: string | null
  spend_30d_usd: string
  spend_total_usd: string
  run_count_30d: number
  call_count_30d: number
  budgets: UserBudgetExposure[]
}

export interface UserGovernanceSummary {
  user_id: string
  email: string
  full_name: string | null
  approval_count: number
  recent_approvals: {
    id: string
    request_type: string
    status: string
    created_at: string
  }[]
  audit_event_count: number
  recent_audit_events: {
    id: string
    action: string
    target_type: string | null
    created_at: string
  }[]
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
  metrics: number
  logs: number
}

export interface OtlpStats {
  last_24h: OtlpWindowStats
  last_7d: OtlpWindowStats
}

export interface OtlpBatchResponse {
  id: string
  created_at: string | null
  signal_type: 'trace' | 'metric' | 'log'
  trace_count: number
  span_count: number
  metric_count: number
  log_record_count: number
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

export interface OtlpBatchResourceMap {
  service_name: string | null
  attribute_keys: string[]
  attribute_count: number
}

export interface OtlpBatchDetail extends OtlpBatchResponse {
  encoding: string | null
  raw_payload_bytes: number
  resource_map_count: number
  resource_maps: OtlpBatchResourceMap[]
  raw_payload_preview: string | null
}

export interface OtlpInsightPoint {
  timestamp: string
  batches: number
  traces: number
  spans: number
  metrics: number
  logs: number
}

export interface OtlpSignalBreakdown {
  signal_type: 'trace' | 'metric' | 'log'
  batches: number
  traces: number
  spans: number
  metrics: number
  logs: number
}

export interface OtlpServiceBreakdown {
  service_name: string
  resource_count: number
}

export interface OtlpStatusBreakdown {
  status: string
  count: number
}

export interface OtlpSemanticDimension {
  key: string
  resource_count: number
}

export interface OtlpAttributeCoverage {
  service_name_pct: number
  session_id_pct: number
  end_user_id_pct: number
  feature_tag_pct: number
  deployment_version_pct: number
  workspace_name_pct: number
  organization_name_pct: number
}

export interface OtlpInsights {
  window: {
    resource_maps_seen: number
    workspace_attribution_mode: string
    workspace_name_hint: string
  }
  timeseries_24h: OtlpInsightPoint[]
  signal_breakdown: OtlpSignalBreakdown[]
  top_services: OtlpServiceBreakdown[]
  attribute_coverage: OtlpAttributeCoverage
  semantic_dimensions: OtlpSemanticDimension[]
  status_breakdown: OtlpStatusBreakdown[]
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
  report_template: string
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

export interface OrgEmailFeatureStatus {
  email_enabled: boolean
  email_reports_enabled: boolean
  smtp_configured: boolean
}

export interface OpsFeatureStatus {
  email_enabled: boolean
  email_reports_enabled: boolean
  backup_enabled: boolean
  smtp_configured: boolean
  redis_durable: boolean
  redis_durability_mode: string
  compliance_export_enabled: boolean
  compliance_export_configured: boolean
  object_lifecycle_enabled: boolean
  abuse_protection_enabled: boolean
  local_tls_enabled: boolean
  deployment_profile: string
  feature_flags: string[]
}

export interface OpsQueueStatusItem {
  queue: string
  depth: number
  role: 'default' | 'priority' | 'low'
  description: string
  status: 'idle' | 'active' | 'busy'
}

export interface OpsQueueStatus {
  items: OpsQueueStatusItem[]
  total_depth: number
  busy_queues: number
}

export interface OpsStorageStatus {
  backup: {
    bucket: string | null
    lifecycle_enabled: boolean
    retention_days: number
    noncurrent_retention_days: number
  }
  compliance_exports: {
    enabled: boolean
    bucket: string | null
    prefix: string
    storage_class: string
    retention_days: number
  }
}

export interface OpsFeatureFlagItem {
  name: string
  enabled: boolean
}

export interface OpsFeatureFlagsResponse {
  enabled: string[]
  items: OpsFeatureFlagItem[]
}

export interface OpsPolicyCheck {
  category: string
  name: string
  status: 'pass' | 'warn' | 'fail'
  detail: string
}

export interface OpsPolicyEvaluation {
  mode: string
  summary: {
    pass: number
    warn: number
    fail: number
  }
  checks: OpsPolicyCheck[]
}

export interface BackupRun {
  id: string
  workspace_id: string
  trigger_mode: 'manual' | 'scheduled'
  status: 'queued' | 'running' | 'success' | 'failed'
  backup_scope: string
  target: string | null
  command: string | null
  triggered_by: string | null
  size_bytes: number | null
  checksum: string | null
  output_excerpt: string | null
  error_detail: string | null
  details: Record<string, unknown> | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface BackupRunList {
  items: BackupRun[]
  total: number
}

export interface BackupActionResult {
  ok: boolean
  message: string
  details: Record<string, unknown> | null
}

export interface BackupTargetConfig {
  id: string
  workspace_id: string
  provider: 's3'
  bucket: string
  prefix: string | null
  region: string | null
  endpoint_url: string | null
  access_key_id: string | null
  secret_access_key: string | null
  force_path_style: boolean
  schedule_enabled: boolean
  cadence: 'daily' | 'weekly' | 'monthly'
  run_hour_utc: number
  retention_days: number
  include_memory_db: boolean
  include_qdrant: boolean
  include_kuzu: boolean
  include_skills: boolean
  encryption_mode: 'none' | 'server_side'
  last_verified_at: string | null
  created_at: string
  updated_at: string
}

export interface BackupSnapshot {
  id: string
  workspace_id: string
  backup_run_id: string
  snapshot_type: string
  bucket: string
  prefix: string | null
  manifest_key: string | null
  checksum: string | null
  total_size_bytes: number | null
  artifact_count: number
  artifacts: Record<string, unknown> | null
  integrity_status: string
  verified_at: string | null
  created_at: string
}

export interface BackupSnapshotList {
  items: BackupSnapshot[]
  total: number
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
  single_topic_mode: boolean
  single_topic_name: string | null
  dead_letter_topic: string | null
  redaction_mode: 'none' | 'metadata_only'
  max_retries: number
  retry_backoff_seconds: number
  event_types: KafkaEventType[]
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface WorkspaceSecuritySettings {
  id: string
  workspace_id: string
  required_metadata_fields: string[]
  required_metadata_mode: 'warn' | 'reject' | string
  data_residency_regions: string[]
  callback_config: Record<string, unknown>
  brand_config: Record<string, unknown>
  oidc_session_config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface OIDCProviderResponse {
  id: string
  workspace_id: string
  name: string
  issuer_url: string
  audience: string | null
  discovery_url: string | null
  jwks_uri: string | null
  claim_mappings: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface OIDCProviderList {
  items: OIDCProviderResponse[]
}

export interface IpAclRuleResponse {
  id: string
  workspace_id: string | null
  api_key_id: string | null
  scope_type: string
  team_name: string | null
  cidr: string
  action: 'allow' | 'deny' | string
  priority: number
  description: string | null
  created_at: string
}

export interface IpAclRuleList {
  items: IpAclRuleResponse[]
}

export interface IpAclTestResponse {
  ip: string
  allowed: boolean
}

export interface KeyRotationEventResponse {
  id: string
  api_key_id: string
  rotated_from_prefix: string
  rotated_to_prefix: string
  triggered_by: string | null
  grace_expires_at: string | null
  created_at: string
}

export interface KeyRotationEventList {
  items: KeyRotationEventResponse[]
}

export interface RotateApiKeyResponse {
  key_id: string
  key_prefix: string
  key: string
  expires_old_at: string | null
}

export interface KafkaExportConfigList {
  items: KafkaExportConfig[]
}

export interface KafkaExportDelivery {
  id: string
  config_id: string
  event_type: string
  topic: string
  idempotency_key: string | null
  status: 'pending' | 'retry_scheduled' | 'success' | 'failed'
  error_detail: string | null
  attempt: number
  next_retry_at: string | null
  last_error_at: string | null
  dead_letter_topic: string | null
  dead_lettered_at: string | null
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
  end_user_id: string | null
  cost_usd: string | null
  baseline_cost_usd: string | null
  savings_usd: string | null
  optimization_applied: string | null
  input_tokens: number | null
  output_tokens: number | null
  latency_ms: number | null
  status: string
  created_at: string
  tags: string[]
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
  has_budget_notification: boolean
  has_billing_period: boolean
  has_provider_profile: boolean
  has_guardrail: boolean
  has_rate_limit: boolean
  has_mcp_server: boolean
  has_search_tool: boolean
  has_tool_policy: boolean
  has_approval_config: boolean
  has_data_capture: boolean
  has_security_config: boolean
  has_tag: boolean
  completed: number
  total: number
  pct: number
}

export interface DemoModeStatus {
  status: 'idle' | 'queued' | 'running' | 'completed' | 'failed' | 'busy'
  action: 'seed' | 'reset' | null
  profile: 'full' | 'quick' | 'manual' | null
  message: string
  pid: number | null
  started_at: string | null
  finished_at: string | null
  updated_at: string
  runbook_path: string
  available_profiles: DemoProfileOption[]
}

export interface DemoProfileOption {
  id: 'full' | 'quick' | 'manual'
  label: string
  kind: 'automated' | 'manual'
  description: string
  entrypoint: string
  runbook_path: string
}

export interface DemoModeTriggerResponse {
  status: string
  message: string
  state: DemoModeStatus
}

// ── Phase 13: Chargeback Reports ────────────────────────────────────────────

export interface ChargebackReport {
  period: string
  dimension: string
  total_cost_usd: string
  covered_cost_usd: string
  unallocated_cost_usd: string
  breakdown: ChargebackBreakdownItem[]
}

export interface ChargebackBreakdownItem {
  dimension: string
  dimension_value: string
  cost_usd: string
  pct_of_total: string
  budget_usd: string | null
  variance_usd: string | null
  call_count: number
  run_count: number
  allocation_status: 'allocated' | 'unallocated'
  coverage_status: 'budgeted' | 'unbudgeted'
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
  skip_system_messages: boolean
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
  skip_system_messages?: boolean
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
  skip_system_messages?: boolean | null
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
  model: string | null
  user_id: string | null
  error: string | null
  is_false_positive: boolean
  feedback_reason: string | null
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
  total_errors: number
  block_rate: number
  false_positive_rate: number
  avg_latency_ms: number
  total_latency_overhead_ms: number
  top_triggered: { name: string; count: number }[]
  by_decision: Record<string, number>
  by_model: { model: string; total: number; blocks: number; block_rate: number }[]
  by_user: { user_id: string; total: number; blocks: number; block_rate: number }[]
  by_guardrail: { name: string; total: number; blocks: number; avg_latency_ms: number }[]
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

export interface GuardrailFeedbackInput {
  is_false_positive: boolean
  reason?: string | null
}

export interface GuardrailAlertResponse {
  id: string
  workspace_id: string
  alert_type: string
  severity: string
  title: string
  description: string | null
  metric_value: number | null
  threshold_value: number | null
  guardrail_rule_id: string | null
  guardrail_name: string | null
  alert_metadata: Record<string, unknown>
  status: string
  acknowledged_at: string | null
  created_at: string
}

export interface GuardrailAlertList {
  items: GuardrailAlertResponse[]
  total: number
}

// ── Phase 15: ML Intelligence Layer ────────────────────────────────────

export interface MLAnomalyResponse {
  id: string
  workspace_id: string
  anomaly_type: string
  dimension: string
  dimension_key: string | null
  detected_at: string
  severity: string
  detection_method: string
  current_value: string
  expected_value: string
  deviation_score: string
  context: Record<string, unknown>
  is_suppressed: boolean
  suppressed_reason: string | null
  correlation_group_id: string | null
  acknowledged_at: string | null
  created_at: string
}

export interface MLAnomalyList {
  items: MLAnomalyResponse[]
  total: number
}

export interface CorrelatedAnomalyGroup {
  correlation_group_id: string
  dimensions: string[]
  max_severity: string
  anomalies: MLAnomalyResponse[]
  detected_at: string
}

export interface CorrelatedGroupList {
  items: CorrelatedAnomalyGroup[]
  total: number
}

export interface MLAnomalySummary {
  total: number
  by_severity: Record<string, number>
  by_type: Record<string, number>
  suppressed: number
  acknowledged: number
}

export interface ForecastPoint {
  date: string
  predicted: number
  lower: number
  upper: number
}

export interface BudgetOverlay {
  budget_limit: string | null
  projected_spend: number
  days_to_exhaustion: number | null
  exhaustion_date: string | null
  breach_probability: number | null
}

export interface ForecastResponse {
  id: string
  workspace_id: string
  forecast_type: string
  dimension_key: string | null
  method: string
  horizon_days: number
  forecast_from: string
  points: ForecastPoint[]
  accuracy_metrics: Record<string, unknown>
  budget_overlay: BudgetOverlay | null
  created_at: string
}

export interface TopKItem {
  rank: number
  key: string
  current_value: number
  previous_value: number | null
  rank_change: number | null
  pct_change: number | null
}

export interface TopKChange {
  key: string
  change_type: string
  detail: string
}

export interface TopKResponse {
  dimension: string
  metric: string
  k: number
  period: Record<string, string>
  items: TopKItem[]
  significant_changes: TopKChange[]
}

export interface PatternResponse {
  id: string
  workspace_id: string
  dimension: string
  dimension_key: string | null
  pattern: string
  confidence: string
  evidence: Record<string, unknown>
  detected_at: string
}

export interface PatternList {
  items: PatternResponse[]
}

export interface ComplexityScore {
  run_id: string
  score: number
  predicted_cost: number
  actual_cost: number
  complexity_tier: string
}

export interface ComplexityScoreList {
  items: ComplexityScore[]
  distribution: Record<string, number>
}

export interface FeatureImportance {
  feature: string
  importance: number
}

export interface FeatureImportanceList {
  items: FeatureImportance[]
  model_version: number
  trained_at: string | null
  sample_count: number
}

export interface CostPerOutcome {
  outcome_type: string
  total_cost: number
  outcome_count: number
  cost_per_outcome: number
  avg_quality_score: number | null
  model: string | null
}

export interface ParetoPoint {
  key: string
  cost: number
  quality: number
  is_optimal: boolean
}

export interface CostOutcomeResponse {
  items: CostPerOutcome[]
  pareto_frontier: ParetoPoint[]
}

export interface AdaptiveThresholdSuggestion {
  rule_id: string
  rule_name: string
  metric: string
  current_threshold: string
  suggested_upper: number
  suggested_lower: number
  baseline: number
  confidence: number
}

export interface AdaptiveThresholdList {
  items: AdaptiveThresholdSuggestion[]
}

export interface ModelHealth {
  id: string
  model_type: string
  dimension: string
  dimension_key: string | null
  version: number
  trained_at: string | null
  sample_count: number
  staleness_hours: number
  metrics: Record<string, unknown>
  status: string
}

export interface MLDashboard {
  models: ModelHealth[]
  anomaly_summary: MLAnomalySummary
  total_forecasts: number
  total_patterns: number
  last_anomaly_run: string | null
  last_forecast_run: string | null
}

// ── Advanced Budget Engine ──────────────────────────────────────────────────

export interface BudgetTier {
  id: string
  name: string
  max_spend_usd: number | null
  period_type: 'daily' | 'monthly' | 'total'
  rpm_limit: number | null
  tpm_limit: number | null
  allowed_models: string[] | null
  is_default: boolean
  is_active: boolean
  created_at: string
  key_count: number
}

export interface BudgetTierList {
  items: BudgetTier[]
}

export interface ModelBudget {
  id: string
  api_key_id: string
  model_pattern: string
  max_spend_usd: number | null
  period_type: 'daily' | 'monthly' | 'total'
  rpm_limit: number | null
  tpm_limit: number | null
  action: string
  is_active: boolean
  created_at: string
}

export interface ModelBudgetList {
  items: ModelBudget[]
}

export interface BudgetOverride {
  id: string
  budget_id: string
  original_limit_usd: number
  override_limit_usd: number
  starts_at: string
  expires_at: string
  reason: string | null
  approved_by: string | null
  status: 'pending' | 'active' | 'expired' | 'revoked'
  approval_id: string | null
  approval_status: 'pending' | 'approved' | 'denied' | 'cancelled' | null
  created_at: string
}

export interface BudgetOverrideList {
  items: BudgetOverride[]
}

export interface BillingPeriodSummary {
  period: string
  total_cost_usd: number
  billable_cost_usd: number
  non_billable_cost_usd: number
  total_calls: number
  billable_calls: number
}

export interface BillingSummaryResponse {
  workspace_id: string
  periods: BillingPeriodSummary[]
}

export interface RateLimitInfo {
  limit_requests: number
  remaining_requests: number
  limit_tokens?: number
  remaining_tokens?: number
  reset: number
}

// ── Agent Registry ─────────────────────────────────────────────────────────

export interface AgentResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  agent_type: string
  owner: string | null
  default_model: string | null
  default_tools: string[]
  budget_envelope: number | null
  policy_profile: string | null
  status: string
  config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AgentListResponse {
  agents: AgentResponse[]
  total: number
}

export interface AgentStats {
  agent_id: string
  total_runs: number
  completed_runs: number
  failed_runs: number
  total_cost: number
  total_tokens: number
  avg_duration_ms: number | null
  success_rate: number | null
  last_run_at: string | null
  models_used: string[]
  tools_used: string[]
}

// ── Workflow Definitions & Runs ────────────────────────────────────────────

export interface WorkflowDefinitionResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  steps_schema: Record<string, unknown>[]
  status: string
  config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface WorkflowDefinitionListResponse {
  workflows: WorkflowDefinitionResponse[]
  total: number
}

export interface WorkflowStepResponse {
  id: string
  run_id: string
  step_index: number
  name: string
  step_type: string
  agent_id: string | null
  model: string | null
  tool: string | null
  status: string
  cost: number
  tokens: number
  duration_ms: number | null
  input_data: Record<string, unknown> | null
  output_data: Record<string, unknown> | null
  error: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface WorkflowRunResponse {
  id: string
  workspace_id: string
  workflow_id: string
  agent_id: string | null
  parent_run_id: string | null
  status: string
  total_cost: number
  total_tokens: number
  total_duration_ms: number | null
  trigger: string | null
  input_data: Record<string, unknown>
  output_data: Record<string, unknown> | null
  error: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  steps: WorkflowStepResponse[]
}

export interface WorkflowRunListResponse {
  runs: WorkflowRunResponse[]
  total: number
}

export interface WorkflowRunSummary {
  id: string
  workspace_id: string
  workflow_id: string
  agent_id: string | null
  parent_run_id: string | null
  status: string
  total_cost: number
  total_tokens: number
  total_duration_ms: number | null
  trigger: string | null
  error: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface WorkflowRunSummaryListResponse {
  runs: WorkflowRunSummary[]
  total: number
}

export interface StepCostBreakdown {
  step_name: string
  step_type: string
  total_cost: number
  avg_cost: number
  invocation_count: number
}

export interface WorkflowCostAttribution {
  workflow_id: string
  workflow_name: string
  total_runs: number
  total_cost: number
  avg_cost_per_run: number
  cost_by_step: StepCostBreakdown[]
}

// ── Agent Memory ──────────────────────────────────────────────────────────

export interface AgentMemoryResponse {
  id: string
  workspace_id: string
  agent_id: string
  key: string
  value: string
  memory_type: string
  metadata: Record<string, unknown>
  size_bytes: number
  access_count: number
  has_pii: boolean
  retention_days: number | null
  expires_at: string | null
  last_accessed_at: string | null
  created_at: string
  updated_at: string
}

export interface AgentMemoryListResponse {
  memories: AgentMemoryResponse[]
  total: number
}

export interface AgentMemoryStats {
  agent_id: string
  total_memories: number
  total_size_bytes: number
  by_type: Record<string, number>
  pii_count: number
  expired_count: number
  most_accessed: AgentMemoryResponse[]
}

export interface AgentMemoryAuditResponse {
  id: string
  workspace_id: string
  agent_id: string
  memory_id: string | null
  action: string
  key: string | null
  details: Record<string, unknown>
  actor: string | null
  created_at: string
}

export interface AgentMemoryAuditListResponse {
  events: AgentMemoryAuditResponse[]
  total: number
}

// ── Vector Store Management ───────────────────────────────────────────────

export interface VectorCollectionResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  qdrant_collection: string
  embedding_model: string | null
  dimensions: number | null
  distance_metric: string
  document_count: number
  size_bytes: number
  total_queries: number
  total_query_cost: number
  total_embed_cost: number
  status: string
  config: Record<string, unknown>
  last_queried_at: string | null
  created_at: string
  updated_at: string
}

export interface VectorCollectionListResponse {
  collections: VectorCollectionResponse[]
  total: number
}

export interface VectorCollectionStats {
  collection_id: string
  name: string
  document_count: number
  size_bytes: number
  total_queries: number
  total_query_cost: number
  total_embed_cost: number
  total_cost: number
  avg_query_latency_ms: number | null
  avg_results_per_query: number | null
}

export interface VectorQueryResponse {
  id: string
  workspace_id: string
  collection_id: string
  query_text: string
  top_k: number
  threshold: number | null
  result_count: number
  best_score: number | null
  latency_ms: number | null
  embed_cost: number
  query_cost: number
  results: Record<string, unknown>[] | null
  created_at: string
}

export interface VectorQueryListResponse {
  queries: VectorQueryResponse[]
  total: number
}

export interface VectorSearchTestResponse {
  query: string
  results: { score: number; payload: Record<string, unknown> }[]
  result_count: number
  latency_ms: number | null
  embed_cost: number
  query_cost: number
}

// ── API Playground ────────────────────────────────────────────────────────

export interface PlaygroundSessionResponse {
  id: string
  workspace_id: string
  name: string | null
  system_prompt: string | null
  mode: string
  is_favorite: boolean
  config: Record<string, unknown>
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface PlaygroundSessionListResponse {
  sessions: PlaygroundSessionResponse[]
  total: number
}

export interface PlaygroundRequestResponse {
  id: string
  workspace_id: string
  session_id: string | null
  model: string
  provider: string | null
  system_prompt: string | null
  user_prompt: string
  parameters: Record<string, unknown>
  response_text: string | null
  input_tokens: number | null
  output_tokens: number | null
  cost_usd: number | null
  latency_ms: number | null
  status: string
  route_decision: string | null
  error: string | null
  gateway_request_id: string | null
  created_at: string
}

export interface PlaygroundRequestListResponse {
  requests: PlaygroundRequestResponse[]
  total: number
}

export interface PlaygroundCompareResponse {
  results: PlaygroundRequestResponse[]
}

// ── MCP Server Registry ──────────────────────────────────────────────────

export interface McpServerResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  transport: string
  url: string | null
  command: string | null
  args: string[]
  env: Record<string, string>
  auth_type: string | null
  discovered_tools: Record<string, unknown>[]
  discovered_resources: Record<string, unknown>[]
  discovered_prompts: Record<string, unknown>[]
  health_status: string
  last_health_check: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  tool_count: number
  resource_count: number
  prompt_count: number
}

export interface McpServerList {
  items: McpServerResponse[]
}

export interface McpPermissionResponse {
  id: string
  workspace_id: string
  mcp_server_id: string
  scope_type: string
  scope_id: string
  allowed_tools: string[]
  created_at: string
}

export interface McpPermissionList {
  items: McpPermissionResponse[]
}

export interface McpToolCallResponse {
  id: string
  mcp_server_id: string
  tool_name: string
  arguments: Record<string, unknown>
  result: unknown
  cost_usd: number | null
  latency_ms: number | null
  status: string
  error: string | null
  created_at: string
}

export interface McpToolCallList {
  items: McpToolCallResponse[]
}

export interface McpToolListItem {
  server_id: string
  server_name: string
  tool_name: string
  description: string | null
}

export interface McpToolListResponse {
  items: McpToolListItem[]
}

// ── Plugins ──────────────────────────────────────────────────────────────

export interface PluginResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  plugin_type: string
  hooks: string[]
  config: Record<string, unknown>
  priority: number
  is_active: boolean
  version: string | null
  author: string | null
  install_count: number
  created_at: string
  updated_at: string
}

export interface PluginList {
  items: PluginResponse[]
}

export interface PluginExecutionResponse {
  id: string
  plugin_id: string
  hook: string
  latency_ms: number | null
  status: string
  error: string | null
  created_at: string
}

export interface PluginExecutionList {
  items: PluginExecutionResponse[]
}

// ── AI Hub ───────────────────────────────────────────────────────────────

export interface HubModelResponse {
  id: string
  workspace_id: string
  name: string
  provider: string
  description: string | null
  capabilities: string[]
  context_window: number | null
  input_cost_per_1k: number | null
  output_cost_per_1k: number | null
  tags: string[]
  is_featured: boolean
  is_deprecated: boolean
  deprecation_notice: string | null
  is_public: boolean
  access_request_count: number
  created_at: string
  updated_at: string
}

export interface HubProviderSyncResponse {
  status: string
  provider: string
  models_added: number
  total_templates: number
}

export interface HubModelList {
  items: HubModelResponse[]
}

export interface HubModelCostPosture {
  model_id: string
  model_name: string
  provider: string
  input_cost_per_1k: number | null
  output_cost_per_1k: number | null
  active_budget_count: number
  total_budget_limit_usd: string
  current_spend_usd: string
  billing_period_count: number
  chargeback_cost_usd: string
  budgets: Array<{
    id: string
    period_type: string
    limit_usd: string
    current_spend_usd: string
    action: string
  }>
  billing_periods: Array<{
    id: string
    period_start: string
    period_end: string
    status: string
  }>
}

export interface HubModelGovernanceStatus {
  model_id: string
  model_name: string
  provider: string
  tags: string[]
  approval_count: number
  recent_approvals: Array<{
    id: string
    request_type: string
    status: string
    requested_by: string
    created_at: string
  }>
  audit_event_count: number
  recent_audit_events: Array<{
    id: string
    action: string
    target_type: string
    created_at: string
  }>
  tool_policy_count: number
  is_deprecated: boolean
  deprecation_notice: string | null
  access_request_count: number
}

export interface HubOrgSummary {
  total_models: number
  featured_models: number
  deprecated_models: number
  total_access_requests: number
  providers: string[]
  workspaces: Array<{
    workspace_id: string
    workspace_name: string
    model_count: number
    featured_count: number
    deprecated_count: number
  }>
}

// ── Projects ─────────────────────────────────────────────────────────────

// ── Team Models ──────────────────────────────────────────────────────────

// Workspace control surfaces

export interface TagResponse {
  id: string
  workspace_id: string
  category: string
  key: string
  value: string
  description: string | null
  parent_tag_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TagTreeNode extends TagResponse {
  children: TagTreeNode[]
}

export interface TagListResponse {
  items: TagResponse[]
  total: number
}

export interface TagTreeResponse {
  items: TagTreeNode[]
  total: number
}

export interface AutoTaggingRuleResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  match_type: string
  match_field: string
  match_pattern: string
  tag_key: string
  tag_value: string
  priority: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AutoTaggingRuleListResponse {
  items: AutoTaggingRuleResponse[]
  total: number
}

export interface AutoTaggingSimulationMatch {
  rule_id: string
  rule_name: string
  tag_key: string
  tag_value: string
  priority: number
}

export interface AutoTaggingSimulationResponse {
  matched: AutoTaggingSimulationMatch[]
  applied_tags: Record<string, string>
}

export interface SearchToolResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  tool_type: string
  endpoint_url: string | null
  auth_type: string | null
  auth_config: Record<string, unknown>
  rate_limit_rpm: number | null
  cost_per_query: number
  is_active: boolean
  total_queries: number
  total_cost_usd: number
  avg_quality_score: number | null
  config: Record<string, unknown>
  created_at: string
  updated_at: string
  policy_count: number
}

export interface SearchToolListResponse {
  items: SearchToolResponse[]
  total: number
}

export interface ToolPolicyResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  tool_name: string
  action: 'allow' | 'audit' | 'block' | 'require_approval' | 'deny' | string
  condition_type: string | null
  condition_config: Record<string, unknown>
  scope_type: string
  scope_id: string | null
  priority: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ToolPolicyListResponse {
  items: ToolPolicyResponse[]
  total: number
}

export interface SearchToolPolicySummary {
  tool_id: string
  tool_name: string
  policies: ToolPolicyResponse[]
}

export interface ToolPolicySimulationResponse {
  tool_name: string
  final_action: string
  matched_policy_ids: string[]
  matched_policy_names: string[]
  reasons: string[]
}

export interface ToolUsageAnalyticsItem {
  tool_name: string
  total_calls: number
  allowed_calls: number
  denied_calls: number
  audited_calls: number
  success_count: number
  failure_count: number
  avg_duration_ms: number | null
  avg_risk_score: number | null
}

export interface ToolUsageAnalyticsResponse {
  items: ToolUsageAnalyticsItem[]
  total_calls: number
  unique_tools: number
}

export interface AccessGroupResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  permissions: Record<string, unknown>
  budget_usd: number | null
  budget_period: string | null
  guardrail_profile: string | null
  is_active: boolean
  member_count: number
  created_at: string
  updated_at: string
}

export interface AccessGroupListResponse {
  items: AccessGroupResponse[]
  total: number
}

export interface AccessGroupMemberResponse {
  id: string
  group_id: string
  user_id: string
  role: string
  created_at: string
}

export interface AccessGroupMemberListResponse {
  items: AccessGroupMemberResponse[]
  total: number
}

export interface AccessGroupDashboardItem {
  id: string
  name: string
  member_count: number
  budget_usd: number | null
  budget_period: string | null
  guardrail_profile: string | null
  dashboard_filters: Record<string, unknown>
  is_active: boolean
}

export interface AccessGroupDashboardResponse {
  groups: AccessGroupDashboardItem[]
  selected_group_id: string | null
}

export interface ResponseCacheConfigResponse {
  id: string
  workspace_id: string
  name: string
  is_enabled: boolean
  ttl_seconds: number
  max_entries: number
  eviction_policy: string
  similarity_threshold: number
  embedding_model: string | null
  scope_models: string[]
  total_hits: number
  total_misses: number
  total_savings_usd: number
  config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ResponseCacheConfigCreate {
  name: string
  is_enabled?: boolean
  ttl_seconds?: number
  max_entries?: number
  eviction_policy?: string
  similarity_threshold?: number
  embedding_model?: string | null
  scope_models?: string[]
  config?: Record<string, unknown>
}

export interface ResponseCacheConfigUpdate {
  name?: string
  is_enabled?: boolean
  ttl_seconds?: number
  max_entries?: number
  eviction_policy?: string
  similarity_threshold?: number
  embedding_model?: string | null
  scope_models?: string[]
  config?: Record<string, unknown>
}

export interface ResponseCacheConfigListResponse {
  items: ResponseCacheConfigResponse[]
  total: number
}

export interface ResponseCacheStatsResponse {
  config_count: number
  enabled_config_count: number
  total_hits: number
  total_misses: number
  hit_rate: number | null
  total_savings_usd: number
  live_entry_count: number
  top_models: { model: string; hit_count: number }[]
}

export interface ApiKeyObserveFootprint {
  api_key_id: string
  key_prefix: string
  run_count: number
  total_cost_usd: string
  total_input_tokens: number
  total_output_tokens: number
  models_used: { model: string; provider: string; cost_usd: string; call_count: number }[]
  recent_runs: { id: string; status: string; feature_tag: string | null; cost_usd: string; started_at: string }[]
}

export interface WorkspaceObservePosture {
  workspace_id: string
  workspace_name: string
  run_count_30d: number
  total_cost_30d: string
  active_sessions_30d: number
  distinct_models_30d: number
  distinct_users_30d: number
  error_count_30d: number
  top_models: { model: string; provider: string; cost_usd: string; call_count: number }[]
  budget_count: number
  active_billing_periods: number
}

export interface WorkspaceGovernancePosture {
  workspace_id: string
  tool_policy_count: number
  approval_count: number
  pending_approval_count: number
  audit_event_count: number
  alert_rule_count: number
  active_alert_count: number
  tag_count: number
  chargeback_rule_count: number
}

export interface AccessGroupGatewayPosture {
  access_group_id: string
  workspace_id: string
  guardrail_profile: string | null
  route_count: number
  active_route_count: number
  distinct_providers: number
  routing_policy_count: number
  guardrail_count: number
  active_guardrail_count: number
  passthrough_count: number
}

export interface ApiKeyGatewayPosture {
  api_key_id: string
  workspace_id: string
  route_count: number
  active_route_count: number
  distinct_providers: number
  guardrail_count: number
  active_guardrail_count: number
  rate_limited_route_count: number
}

export interface TelemetryDownstreamPosture {
  workspace_id: string
  batch_count_30d: number
  finops: {
    budget_count: number
    active_billing_periods: number
    chargeback_rule_count: number
    budget_notification_count: number
  }
  safety: {
    tool_policy_count: number
    approval_count: number
    audit_event_count: number
    alert_rule_count: number
    active_alert_count: number
    tag_count: number
  }
}

export interface McpRegistryPosture {
  workspace_id: string
  server_count: number
  active_server_count: number
  tool_call_count_30d: number
  distinct_tools_used: number
  error_call_count: number
  gateway: {
    route_count: number
    guardrail_count: number
  }
  governance: {
    approval_count: number
    audit_event_count: number
    chargeback_rule_count: number
  }
}

export interface BudgetPerformancePosture {
  workspace_id: string
  budget_id: string
  cache: {
    total_requests_30d: number
    cache_hits_30d: number
    cache_hit_rate_pct: number
    estimated_savings_pct: number
  }
  rate_limits: {
    rate_limited_routes: number
    total_active_routes: number
    containment_coverage_pct: number
  }
  overrides: {
    override_count: number
    active_overrides: number
  }
  billing: {
    billing_period_count: number
  }
  chargeback: {
    chargeback_rule_count: number
  }
}

export interface BudgetOrgScopePosture {
  workspace_id: string
  budget_id: string
  scope_type: string
  scope_id: string | null
  scope_display_name: string | null
  org_context: {
    workspace_users: number
    workspace_api_keys: number
    workspace_access_groups: number
    total_active_budgets: number
    total_spend_30d_usd: number
  }
  hub_context: {
    hub_model_count: number
    distinct_models_30d: number
  }
  scope_entity: Record<string, unknown>
}

export interface BudgetDetailObservePosture {
  workspace_id: string
  period_days: number
  budget_context: {
    budgets: number
    active_budgets: number
    total_limit_usd: number
    breach_count: number
  }
  spend_context: {
    total_spend_30d: number
    total_runs_30d: number
    avg_cost_per_run: number
    distinct_models_30d: number
  }
  user_budget_context: {
    users_with_budgets: number
    active_users_30d: number
    user_scoped_budget_total: number
    user_scoped_spend: number
  }
  engineering_context: {
    feature_scoped_budgets: number
    active_budgets: number
    breach_count: number
    total_limit_usd: number
  }
}

export interface BudgetOverrideGovernancePosture {
  workspace_id: string
  period_days: number
  approval_context: {
    pending_approvals: number
    approved_30d: number
    denied_30d: number
    overrides_with_approval: number
  }
  alert_context: {
    budget_alert_rules: number
    active_budget_alerts: number
  }
  audit_context: {
    override_audit_events_30d: number
    total_overrides: number
    active_overrides: number
  }
  governance_context: {
    approval_coverage_pct: number
    active_overrides: number
  }
  tag_context: {
    budget_tags: number
    override_tags: number
  }
}

export interface BillingPeriodPerformancePosture {
  workspace_id: string
  cache: {
    total_requests_30d: number
    cache_hits_30d: number
    cache_hit_rate_pct: number
    estimated_savings_pct: number
  }
  rate_limits: {
    rate_limited_routes: number
    total_active_routes: number
    containment_coverage_pct: number
  }
  billing: {
    open_periods: number
    total_periods: number
    active_budget_count: number
  }
  chargeback: {
    chargeback_rule_count: number
  }
}

export interface UserGatewayPosture {
  workspace_id: string
  user_id: string
  gateway: {
    active_routes: number
    rate_limited_routes: number
    routing_policies: number
    requests_30d: number
  }
  guardrails: {
    active_rules: number
  }
  identity: {
    api_keys: number
  }
}

export interface GatewayFinopsPosture {
  workspace_id: string
  routes: {
    total_active: number
    with_cost_caps: number
    with_rate_limits: number
    distinct_models: number
    routing_policies: number
  }
  spend: {
    total_30d_usd: number
    total_requests_30d: number
  }
  budgets: {
    active_count: number
    override_count: number
    active_overrides: number
  }
  notifications: {
    active_channels: number
  }
  billing: {
    open_periods: number
    total_periods: number
  }
  chargeback: {
    rule_count: number
  }
}

export interface GatewaySafetyPosture {
  workspace_id: string
  period_days: number
  gateway_context: {
    active_routes: number
    cache_enabled_routes: number
    rate_limited_routes: number
    guardrail_rules: number
    active_guardrails: number
    guardrail_blocks_30d: number
  }
  tool_governance: {
    tool_policy_count: number
    active_tool_policies: number
    mcp_server_count: number
  }
  approvals: {
    total_30d: number
    pending: number
  }
  audit: {
    total_events_30d: number
    gateway_events_30d: number
  }
  alert_rules: {
    total: number
    active: number
  }
  tags: {
    total: number
  }
}

export interface GatewayBuildPosture {
  workspace_id: string
  gateway_context: {
    active_routes: number
    routing_policies: number
    guardrail_rules: number
    active_guardrails: number
  }
  prompts: {
    total: number
  }
  agents: {
    total: number
  }
  workflows: {
    total: number
    runs: number
  }
  evaluation: {
    datasets: number
    experiments: number
  }
  replay: {
    datasets: number
    experiments: number
  }
}

export interface PerformanceControlsOrgPosture {
  workspace_id: string
  cache_context: {
    profiles: number
    enabled_profiles: number
    cache_enabled_routes: number
    api_keys: number
  }
  rate_limit_context: {
    routes_with_rpm: number
    passthrough_with_rpm: number
    active_routes: number
    access_groups: number
  }
  platform_context: {
    workspace_scoped: boolean
    cache_profiles_configured: boolean
    throttle_configured: boolean
  }
}

export interface GatewayInternalPosture {
  workspace_id: string
  gateway_family: {
    active_routes: number
    providers: number
    routing_policies: number
    passthrough_endpoints: number
  }
  guardrail_context: {
    rules: number
    active: number
  }
  cache_context: {
    profiles: number
    cache_enabled_routes: number
  }
  throttle_context: {
    rate_limited_routes: number
  }
  platform_visibility: {
    workspace_scoped: boolean
    provider_count: number
    guardrails_active: boolean
    cache_configured: boolean
    throttle_configured: boolean
  }
}

export interface GatewayControlPlanePosture {
  workspace_id: string
  org_context: {
    users: number
    access_groups: number
    api_keys: number
  }
  gateway_context: {
    active_routes: number
    routing_policies: number
    provider_profiles: number
    active_guardrails: number
  }
  observe_context: {
    monitoring_alerts: number
  }
  governance_context: {
    approvals_pending: number
    audit_events_30d: number
  }
}

export interface ProviderProfileRuntimePosture {
  workspace_id: string
  provider_profiles: number
  finops_context: {
    budget_notifications: number
    ledger_snapshots: number
  }
  org_context: {
    users: number
    workspace_scoped: boolean
  }
  observe_context: {
    monitoring_alerts: number
  }
  governance_context: {
    mcp_servers: number
    search_tools: number
    capture_policies: number
  }
}

export interface GuardrailsObservePosture {
  workspace_id: string
  period_days: number
  rules: {
    total_rules: number
    active_rules: number
  }
  evaluations: {
    total: number
    blocks: number
    modifications: number
    allows: number
    block_rate: number
    modification_rate: number
    distinct_rules_fired: number
    distinct_models: number
  }
  mode_breakdown: {
    pre_call: number
    post_call: number
  }
  feedback: {
    false_positive_count: number
  }
  performance: {
    avg_latency_ms: number | null
    max_latency_ms: number | null
  }
}

export interface ResponseCacheEconomicsPosture {
  workspace_id: string
  cache_context: {
    profiles: number
    cache_enabled_routes: number
    active_routes: number
  }
  finops_context: {
    budgets: number
    budget_overrides: number
    budget_notifications: number
    billing_periods: number
    ledger_snapshots: number
  }
  governance_context: {
    audit_events_30d: number
  }
  org_context: {
    users: number
  }
}

export interface RateLimitScopePosture {
  workspace_id: string
  throttle_context: {
    routes_with_rpm: number
    active_routes: number
    passthrough_with_rpm: number
    routing_policies: number
  }
  scope_context: {
    access_groups: number
    monitoring_alerts: number
  }
  finops_context: {
    budgets: number
    budget_notifications: number
    chargeback_rules: number
    ledger_snapshots: number
  }
}

export interface InvestigationAccessGroupPosture {
  workspace_id: string
  period_days: number
  access_group_context: {
    access_groups: number
    total_members: number
  }
  investigation_context: {
    runs_30d: number
    requests_30d: number
    active_users: number
    active_routes: number
  }
}

export interface InvestigationFinopsBudgetPosture {
  workspace_id: string
  period_days: number
  budget_context: {
    budgets: number
    active_budgets: number
    total_limit_usd: number
    breach_count: number
    overrides: number
    active_overrides: number
  }
  billing_context: {
    billing_periods: number
    open_billing_periods: number
    chargeback_rules: number
  }
  spend_context: {
    total_spend_30d: number
    total_runs_30d: number
  }
}

export interface EconomicsFinopsPosture {
  workspace_id: string
  period_days: number
  budget_context: {
    budgets: number
    active_budgets: number
    total_limit_usd: number
    breach_count: number
    overrides: number
    active_overrides: number
  }
  billing_context: {
    billing_periods: number
    open_billing_periods: number
    chargeback_rules: number
  }
  notification_context: {
    notifications: number
    active_notifications: number
  }
  ledger_context: {
    ledger_snapshots: number
    ledger_snapshots_30d: number
  }
  spend_context: {
    total_spend_30d: number
    total_runs_30d: number
  }
}

export interface OutcomesFinopsPosture {
  workspace_id: string
  period_days: number
  budget_context: {
    budgets: number
    active_budgets: number
    total_limit_usd: number
    breach_count: number
  }
  billing_context: {
    billing_periods: number
    open_billing_periods: number
    chargeback_rules: number
  }
  spend_context: {
    total_spend_30d: number
    outcomes_30d: number
  }
}

export interface MonitoringFinopsPosture {
  workspace_id: string
  period_days: number
  budget_context: {
    budgets: number
    active_budgets: number
    breach_count: number
    overrides: number
    active_overrides: number
  }
  billing_context: {
    billing_periods: number
    open_billing_periods: number
    chargeback_rules: number
  }
  notification_context: {
    notifications: number
    active_notifications: number
  }
  ledger_context: {
    ledger_snapshots: number
  }
}

export interface OverviewGatewayPosture {
  workspace_id: string
  period_days: number
  provider_context: {
    distinct_providers: number
    active_routes: number
    total_routes: number
    routing_policies: number
  }
  route_context: {
    passthrough_endpoints: number
  }
  guardrail_context: {
    active_rules: number
    events_30d: number
    blocks_30d: number
  }
}

export interface OverviewGovernancePosture {
  workspace_id: string
  period_days: number
  security_context: {
    security_events: number
    security_events_30d: number
  }
  alert_context: {
    alert_rules: number
    active_alert_rules: number
    active_firings: number
  }
  audit_context: {
    audit_events_30d: number
  }
  governance_context: {
    tags: number
    active_tags: number
    approvals: number
    capture_policies: number
  }
}

export interface OverviewOrgPosture {
  workspace_id: string
  period_days: number
  user_context: {
    workspace_users: number
  }
  api_key_context: {
    api_keys: number
    active_api_keys: number
  }
  telemetry_context: {
    telemetry_batches: number
    telemetry_batches_30d: number
  }
  mcp_context: {
    mcp_servers: number
    active_mcp_servers: number
  }
  hub_context: {
    hub_models: number
    active_hub_models: number
  }
}

export interface OverviewScopePosture {
  workspace_id: string
  period_days: number
  access_group_context: {
    access_groups: number
    active_access_groups: number
    total_members: number
  }
  cache_context: {
    cache_configs: number
    enabled_configs: number
    total_hits: number
    total_savings_usd: number
  }
  rate_limit_context: {
    routes_with_limits: number
    routes_without_limits: number
  }
  tool_context: {
    tool_registry_entries: number
    tool_policies: number
    active_tool_policies: number
    pending_approvals: number
    capture_policies: number
  }
}

export interface MonitoringOpsPosture {
  workspace_id: string
  period_days: number
  gateway_context: {
    distinct_providers: number
    active_routes: number
    guardrail_rules: number
    guardrail_events_30d: number
    cache_configs: number
    rate_limit_routes: number
  }
  governance_context: {
    tool_registry: number
    tool_policies: number
    capture_policies: number
    audit_events_30d: number
    approvals: number
    tags: number
  }
  org_context: {
    workspace_users: number
    mcp_servers: number
    active_mcp_servers: number
  }
  investigation_context: {
    runs_30d: number
    gateway_requests_30d: number
  }
}

export interface TelemetryOpsPosture {
  workspace_id: string
  period_days: number
  gateway_context: {
    active_routes: number
    distinct_models: number
    gateway_requests_30d: number
  }
  governance_context: {
    capture_policies: number
    security_events_30d: number
    alert_rules: number
    active_alert_rules: number
    audit_events_30d: number
    approvals: number
    tags: number
  }
  org_context: {
    workspace_users: number
    telemetry_batches_30d: number
  }
  investigation_context: {
    runs_30d: number
    provider_calls_30d: number
  }
}

export interface UserAnalyticsOrgPosture {
  workspace_id: string
  period_days: number
  org_context: {
    org_name: string
    workspace_count: number
    workspace_users: number
  }
  user_context: {
    total_end_users: number
    active_end_users_30d: number
    api_keys: number
    active_api_keys: number
  }
  workspace_context: {
    telemetry_batches_30d: number
  }
}

export interface ModelUsageGatewayPosture {
  workspace_id: string
  period_days: number
  gateway_context: {
    active_routes: number
    total_routes: number
    distinct_models: number
    routing_policies: number
  }
  investigation_context: {
    runs_30d: number
    gateway_requests_30d: number
    provider_calls_30d: number
  }
  tag_context: {
    tags: number
    active_tags: number
  }
}

export interface EconomicsGatewayPosture {
  workspace_id: string
  period_days: number
  provider_context: {
    distinct_providers: number
    gateway_requests_30d: number
  }
  gateway_context: {
    active_routes: number
    distinct_models: number
    routing_policies: number
  }
  investigation_context: {
    runs_30d: number
    provider_calls_30d: number
    monitoring_alerts_30d: number
  }
}

export interface InvestigationGatewayRuntimePosture {
  workspace_id: string
  period_days: number
  provider_context: {
    distinct_providers: number
    active_routes: number
    total_routes: number
    routing_policies: number
  }
  route_context: {
    gateway_requests_30d: number
    cache_hits_30d: number
    passthrough_endpoints: number
  }
  guardrail_context: {
    active_rules: number
    events_30d: number
    blocks_30d: number
  }
  cache_context: {
    enabled_configs: number
    cache_entries: number
    total_hits: number
    savings_usd: number
  }
  rate_limit_context: {
    routes_with_rpm_limits: number
    routes_with_cost_limits: number
  }
}

export interface InvestigationGovernancePosture {
  workspace_id: string
  period_days: number
  filtered_runs: number
  tags: string[]
  tool_governance: {
    registered_tools: number
    active_tool_policies: number
    filtered_tool_calls: number
  }
  security: {
    events: number
    runs_with_events: number
  }
  alert_rules: {
    active: number
    recent_firings: number
  }
  audit_log: {
    events_30d: number
    governance_events: number
  }
  governance_pack: {
    approvals: number
    capture_policies: number
    tags: number
  }
}

export interface InvestigationOrgIdentityPosture {
  workspace_id: string
  period_days: number
  org_context: {
    workspace_name: string
    workspace_users: number
  }
  user_context: {
    workspace_users: number
    distinct_end_users_30d: number
    runs_30d: number
  }
  api_key_context: {
    total_keys: number
    active_keys: number
    keys_with_traffic_30d: number
  }
  telemetry_context: {
    batches_30d: number
    runs_30d: number
  }
  mcp_context: {
    servers: number
    tool_calls_30d: number
  }
}

export interface OverviewFinopsBudgetPosture {
  workspace_id: string
  period_days: number
  budget_context: {
    budgets: number
    active_budgets: number
    total_limit_usd: number
    breach_count: number
    overrides: number
    active_overrides: number
  }
  billing_context: {
    billing_periods: number
    open_billing_periods: number
    chargeback_rules: number
  }
  spend_context: {
    total_spend_30d: number
    total_runs_30d: number
  }
  notification_context: {
    notifications: number
    active_notifications: number
  }
}

export interface ModelBudgetUtilizationItem {
  model: string
  spend_30d: number
  request_count: number
  budget_limit_usd: number | null
  budget_action: string | null
  period_type: string | null
  is_active: boolean
}

export interface ModelBudgetUtilization {
  workspace_id: string
  period_days: number
  models: ModelBudgetUtilizationItem[]
  total_model_budgets: number
  active_model_budgets: number
  billing_periods: number
  open_billing_periods: number
  chargeback_rules: number
}

export interface GuardrailsFinopsPosture {
  workspace_id: string
  period_days: number
  guardrail_context: {
    active_rules: number
    evaluations_30d: number
    blocks_30d: number
    active_routes: number
  }
  finops_context: {
    budgets: number
    budget_notifications: number
    billing_periods: number
    chargeback_rules: number
  }
}

export interface GatewayObservePosture {
  workspace_id: string
  period_days: number
  routes: {
    active_routes: number
    cache_enabled: number
    rate_limited: number
  }
  traffic: {
    total_requests: number
    cache_hits: number
    cache_misses: number
    cache_hit_rate: number
    throttled_requests: number
    throttle_rate: number
    errors: number
  }
  runs: {
    run_count: number
    distinct_users: number
    distinct_models: number
  }
  cost: {
    total_cost_usd: number
    total_savings_usd: number
  }
  tokens: {
    input_tokens: number
    output_tokens: number
  }
  performance: {
    avg_latency_ms: number | null
  }
}

export interface ProviderProfileFinopsPosture {
  workspace_id: string
  profile_id: string
  provider: string
  model: string
  budgets: {
    budget_count: number
    active_budget_count: number
    total_limit_usd: number
    breach_count: number
  }
  overrides: {
    override_count: number
    active_override_count: number
  }
  billing: {
    billing_period_count: number
    open_billing_periods: number
  }
  chargeback: {
    chargeback_rule_count: number
  }
}

export interface ProviderProfileObservePosture {
  workspace_id: string
  profile_id: string
  provider: string
  model: string
  period_days: number
  runs: {
    run_count: number
    request_count: number
    error_count: number
  }
  cost: {
    total_cost_usd: number
    total_savings_usd: number
  }
  tokens: {
    input_tokens: number
    output_tokens: number
  }
  performance: {
    avg_latency_ms: number | null
  }
}

export interface AiHubRuntimePosture {
  workspace_id: string
  model_count: number
  featured_count: number
  deprecated_count: number
  observe: {
    run_count_30d: number
    distinct_models_used: number
  }
  finops: {
    budget_count: number
    budget_notification_count: number
  }
  gateway: {
    guardrail_count: number
  }
}

export interface ToolRegistryFinopsPosture {
  workspace_id: string
  period_days: number
  budget_context: {
    total_budgets: number
    tool_scoped_budgets: number
    total_budget_limit_usd: number
  }
  chargeback_context: {
    chargeback_rules: number
    tool_dimension_rules: number
  }
  spend_context: {
    tool_spend_30d: number
    tool_call_count_30d: number
    total_spend_30d: number
  }
}

export interface ApprovalsAlertFinopsPosture {
  workspace_id: string
  period_days: number
  approval_context: {
    budget_increase_total: number
    budget_increase_pending: number
    budget_increase_approved: number
  }
  budget_context: {
    total_budgets: number
    total_budget_limit_usd: number
    active_overrides: number
    breach_count_30d: number
  }
  alert_context: {
    budget_alert_rules: number
    total_alert_rules: number
    recent_firings_30d: number
  }
}

export interface TagsFinopsBudgetPosture {
  workspace_id: string
  period_days: number
  tag_context: {
    total_tags: number
    active_tags: number
    active_auto_rules: number
    distinct_tags_with_spend: number
  }
  budget_context: {
    total_budgets: number
    tag_scoped_budgets: number
    total_budget_limit_usd: number
  }
  chargeback_context: {
    total_chargeback_rules: number
    tag_dimension_rules: number
  }
  spend_context: {
    tagged_spend_30d: number
    tagged_call_count: number
    total_spend_30d: number
  }
}

export interface ToolGovernanceOrgPosture {
  workspace_id: string
  period_days: number
  org_context: {
    org_name: string
    workspace_count: number
  }
  user_context: {
    total_users: number
  }
  access_group_context: {
    total_groups: number
    tool_policy_groups: number
  }
  api_key_context: {
    total_keys: number
  }
  registry_context: {
    total_entries: number
    active_entries: number
  }
  policy_context: {
    total_policies: number
    active_policies: number
    org_scope: number
    workspace_scope: number
    access_group_scope: number
  }
  mcp_context: {
    total_servers: number
    active_servers: number
  }
}

export interface ToolGovernanceGatewayPosture {
  workspace_id: string
  period_days: number
  provider_context: {
    total_providers: number
    total_routes: number
  }
  guardrail_context: {
    total_guardrails: number
    guardrail_events_30d: number
  }
  cache_context: {
    cache_configs: number
  }
  rate_limit_context: {
    rate_limited_routes: number
  }
  run_context: {
    tool_runs_30d: number
    total_runs_30d: number
  }
  monitoring_context: {
    total_alert_rules: number
    alert_firings_30d: number
  }
}

export interface ExceptionWorkflowsOrgPosture {
  workspace_id: string
  period_days: number
  org_context: {
    org_name: string
    workspace_count: number
  }
  user_context: {
    total_users: number
  }
  access_group_context: {
    total_groups: number
  }
  api_key_context: {
    total_keys: number
  }
  approval_context: {
    total_approvals: number
    pending_approvals: number
    approvals_30d: number
  }
  alert_context: {
    total_alert_rules: number
    active_alert_rules: number
    alert_firings_30d: number
  }
  mcp_context: {
    total_servers: number
    active_servers: number
  }
}

export interface ExceptionWorkflowsGatewayPosture {
  workspace_id: string
  period_days: number
  provider_context: {
    total_providers: number
    total_routes: number
  }
  guardrail_context: {
    total_guardrails: number
    guardrail_events_30d: number
  }
  cache_context: {
    cache_configs: number
  }
  rate_limit_context: {
    rate_limited_routes: number
  }
  run_context: {
    tool_runs_30d: number
    total_runs_30d: number
  }
  monitoring_context: {
    total_alert_rules: number
    alert_firings_30d: number
  }
}

export interface DataProtectionOrgPosture {
  workspace_id: string
  period_days: number
  org_context: {
    org_name: string
    workspace_count: number
  }
  user_context: {
    total_users: number
  }
  access_group_context: {
    total_groups: number
  }
  api_key_context: {
    total_keys: number
  }
  capture_context: {
    total_policies: number
    active_policies: number
  }
  security_context: {
    security_events_30d: number
  }
  tag_context: {
    total_tags: number
    active_tags: number
  }
  mcp_context: {
    total_servers: number
    active_servers: number
  }
}

export interface DataProtectionGatewayPosture {
  workspace_id: string
  period_days: number
  provider_context: {
    total_providers: number
    total_routes: number
  }
  guardrail_context: {
    total_guardrails: number
    guardrail_events_30d: number
  }
  cache_context: {
    cache_configs: number
  }
  rate_limit_context: {
    rate_limited_routes: number
  }
  run_context: {
    total_runs_30d: number
    tool_runs_30d: number
  }
  monitoring_context: {
    total_alert_rules: number
    alert_firings_30d: number
  }
}

export interface EvidenceAuditCrossPosture {
  workspace_id: string
  period_days: number
  finops_context: {
    active_budgets: number
    billing_periods: number
    chargeback_rules: number
    ledger_snapshots: number
  }
  org_context: {
    org_name: string
    workspace_users: number
    active_api_keys: number
  }
  gateway_context: {
    total_providers: number
    total_routes: number
    rate_limited_routes: number
  }
  observe_context: {
    audit_events_30d: number
    total_runs_30d: number
    total_alert_rules: number
    alert_firings_30d: number
  }
}

export interface GovernanceInternalPosture {
  workspace_id: string
  period_days: number
  tool_registry_context: {
    total_tools: number
    enforced_tools: number
  }
  tool_policies_context: {
    total_policies: number
    active_policies: number
  }
  approvals_context: {
    pending_approvals: number
    total_approvals_30d: number
  }
  data_capture_context: {
    capture_policies: number
    security_events_30d: number
  }
  security_context: {
    security_events_30d: number
  }
  alert_rules_context: {
    active_alert_rules: number
    alert_firings_30d: number
  }
  audit_context: {
    audit_events_30d: number
  }
  tags_context: {
    total_tags: number
    active_tags: number
  }
}

export interface ToolRegistryRuntimePosture {
  workspace_id: string
  period_days: number
  workspace_scope: { total_workspaces: number; workspace_scoped_tools: number }
  api_key_scope: { active_keys: number; keys_with_tool_calls_30d: number }
  mcp_scope: { active_mcp_servers: number; mcp_tool_calls_30d: number }
  gateway_runtime: { model_routes: number; cache_configs_active: number; rate_limited_routes: number }
  observe_evidence: { tool_runs_30d: number; tool_requests_30d: number }
  budget_linkage: { tool_scoped_budgets: number; budget_notifications_30d: number }
}

export interface ToolPoliciesRuntimePosture {
  workspace_id: string
  period_days: number
  scope_context: { total_workspaces: number; workspace_scoped_policies: number; access_group_scoped_policies: number; active_api_keys: number }
  gateway_enforcement: { model_routes: number; guardrail_rules: number; guardrail_events_30d: number }
  observe_evidence: { policy_violations_30d: number; request_flows_30d: number; monitoring_alerts_30d: number }
  budget_context: { total_budgets: number; budget_notifications_30d: number }
  ledger_context: { ledger_snapshots: number; ledger_entries_30d: number }
}

export interface ApprovalsRuntimePosture {
  workspace_id: string
  period_days: number
  requester_context: { workspace_users: number; active_api_keys: number; total_workspaces: number }
  gateway_escalation: { model_routes: number; guardrail_rules: number }
  observe_evidence: { runs_30d: number; approval_linked_runs_30d: number }
  monitoring_context: { active_alert_rules: number; alert_firings_30d: number }
  budget_context: { total_budgets: number; budget_increase_approvals_30d: number }
}

export interface DataCaptureRuntimePosture {
  workspace_id: string
  period_days: number
  capture_scope: { total_workspaces: number; capture_policies: number; active_api_keys: number; security_events_30d: number }
  gateway_evidence: { provider_calls_30d: number; model_routes: number; cache_configs_active: number }
  observe_evidence: { runs_30d: number; audit_events_30d: number }
  budget_context: { total_budgets: number; budget_notifications_30d: number }
  ledger_context: { ledger_snapshots: number; ledger_entries_30d: number }
}

export interface SecurityRuntimePosture {
  workspace_id: string
  period_days: number
  identity_context: { workspace_users: number; total_workspaces: number; active_api_keys: number; security_events_30d: number }
  gateway_posture: { model_routes: number; guardrail_rules: number; guardrail_events_30d: number }
  observe_evidence: { runs_30d: number; provider_calls_30d: number }
  monitoring_context: { active_alert_rules: number; alert_firings_30d: number }
  finops_context: { chargeback_rules: number; ledger_snapshots: number; ledger_entries_30d: number }
}
export interface AlertRulesRuntimePosture {
  workspace_id: string
  period_days: number
  ops_context: { active_alert_rules: number; alert_firings_30d: number; total_workspaces: number }
  gateway_runtime: { model_routes: number; guardrail_rules: number; rate_limited_routes: number }
  observe_evidence: { runs_30d: number; provider_calls_30d: number }
  finops_context: { chargeback_rules: number; active_budgets: number; budget_notifications_30d: number }
}

export interface AuditLogRuntimePosture {
  workspace_id: string
  period_days: number
  evidence_scope: { audit_events_30d: number; workspace_users: number; active_api_keys: number }
  gateway_lineage: { guardrail_rules: number; cache_configs: number; rate_limited_routes: number }
  observe_lineage: { runs_30d: number; provider_calls_30d: number }
  finops_lineage: { active_budgets: number; ledger_snapshots_30d: number }
}

export interface GovernancePackRuntimePosture {
  workspace_id: string
  period_days: number
  scope_context: { total_workspaces: number; workspace_users: number; active_budgets: number }
  governance_sources: { guardrail_rules: number; audit_events_30d: number; active_tags: number }
  monitoring_evidence: { alert_firings_30d: number; guardrail_events_30d: number }
  finops_evidence: { budget_notifications_30d: number; ledger_snapshots_30d: number }
}

export interface TagsRuntimePosture {
  workspace_id: string
  period_days: number
  taxonomy_scope: { active_tags: number; total_tags: number; workspace_users: number }
  governance_attribution: { tool_policies: number; audit_events_30d: number; guardrail_rules: number }
  observe_attribution: { runs_30d: number; provider_calls_30d: number }
  finops_attribution: { active_budgets: number; chargeback_rules: number }
}
