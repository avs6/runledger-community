import type {
  AlertFiring,
  AlertHistoryList,
  AlertRule,
  AlertRuleList,
  GatewayRoutingGroup,
  GatewayRoutingGroupList,
  GatewayRoutingStrategyComparison,
  GatewayRoute,
  GatewayRequestList,
  GatewayRouteList,
  GatewayStats,
  RoutingPolicy,
  RoutingPolicyList,
  RoutingPolicyType,
  AdminWorkspaceResponse,
  AnalyticsExport,
  AnalyticsSummary,
  Annotation,
  AnnotationList,
  AnomalyList,
  ApiKeyCreateResponse,
  ApiKeyResponse,
  BillingAdjustment,
  BillingAdjustmentList,
  BillingPeriod,
  BillingPeriodList,
  BreachList,
  ChargebackReportList,
  ChargebackRuleList,
  ChargebackRuleResponse,
  Budget,
  BudgetList,
  BudgetRollupResponse,
  CapturePolicyResponse,
  CapturePolicyScope,
  RetentionPreview,
  PiiTestResult,
  CohortList,
  DatasetList,
  DatasetResponse,
  ExperimentList,
  ExperimentResponse,
  ExperimentResults,
  LedgerSnapshotList,
  NotificationList,
  NotificationDeliveryList,
  NotificationResponse,
  NotificationTestResult,
  PlatformWebhookDefaults,
  PlatformWebhookDefaultsTestResult,
  LedgerSnapshotResponse,
  LedgerClosureSummary,
  LedgerVerifyResult,
  PeriodBreakdown,
  PromptList,
  PromptMetrics,
  PromptResponse,
  PromptVersion,
  ProviderPricingList,
  ProviderPricingResponse,
  ReconciliationResult,
  RegressionList,
  RunDetailResponse,
  RunEconomics,
  RunGraphResponse,
  RunListItem,
  RunListResponse,
  ScoreEvent,
  ScoreList,
  ScoreSummary,
  SessionDetail,
  SessionList,
  SharedCostAllocationResult,
  SharedCostPolicy,
  SharedCostPolicyList,
  TurnCostResponse,
  VersionList,
  SecurityEventList,
  SlackTestResponse,
  SpendByFeature,
  SpendByModel,
  SpendByUser,
  SpendOverTime,
  TenantResponse,
  TenantStatus,
  ToolRegistryList,
  ToolRegistryResponse,
  UserSpendDetail,
  UsageSnapshot,
  VersionCompareResult,
  WorkflowTopList,
  OtlpStats,
  OtlpBatchList,
  OtlpBatchDetail,
  OtlpInsights,
  AuditEventList,
  RetentionPolicy,
  RetentionPolicyList,
  RetentionResourceType,
  RetentionActionType,
  RetentionScopeType,
  PurgeResult,
  EmailPreference,
  EmailLogList,
  OrgEmailFeatureStatus,
  OpsFeatureStatus,
  OpsFeatureFlagsResponse,
  OpsPolicyEvaluation,
  OpsQueueStatus,
  OpsStorageStatus,
  BackupRun,
  BackupRunList,
  BackupActionResult,
  BackupTargetConfig,
  BackupSnapshotList,
  EvalDataset,
  EvalDatasetList,
  EvalExperiment,
  EvalExperimentList,
  ExperimentModelConfig,
  GithubConfig,
  GithubSyncResult,
  DatasetItem,
  ScopedSummary,
  SavingsResponse,
  OptimizationOpportunitiesResponse,
  TrendsResponse,
  RequestExplorerResponse,
  EngineeringMetrics,
  SimulationRequest,
  SimulationResult,
  PolicyCheckResponse,
  PolicyDryRunReport,
  RunbookList,
  RunbookResponse,
  ModelScorecardList,
  ModelScoreTrendList,
  OnboardingStatus,
} from '@/types/api'

// Server-side (SSR/RSC): use API_URL — an internal Docker/Railway URL not visible to the browser.
// Client-side (browser): use NEXT_PUBLIC_API_URL — baked at build time, must be browser-reachable.
const API_URL =
  typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')

async function apiFetch<T>(path: string, apiKey: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
      ...init?.headers,
    },
    cache: 'no-store',
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

async function adminFetch<T>(path: string, adminSecret: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Secret': adminSecret,
      ...init?.headers,
    },
    cache: 'no-store',
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export async function getRuns(
  apiKey: string,
  params: {
    limit?: number
    cursor?: string
    status?: string
    feature_tag?: string
    end_user_id?: string
    search?: string
    from?: string
    to?: string
    model?: string
    min_cost?: string
    max_cost?: string
    access_group_id?: string
    tag?: string
    tool_name?: string
    security_event_only?: boolean
    api_key_id?: string
  } = {}
): Promise<RunListResponse> {
  const qs = new URLSearchParams()
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.cursor) qs.set('cursor', params.cursor)
  if (params.status) qs.set('status', params.status)
  if (params.feature_tag) qs.set('feature_tag', params.feature_tag)
  if (params.end_user_id) qs.set('end_user_id', params.end_user_id)
  if (params.search) qs.set('search', params.search)
  if (params.from) qs.set('from', params.from)
  if (params.to) qs.set('to', params.to)
  if (params.model) qs.set('model', params.model)
  if (params.min_cost) qs.set('min_cost', params.min_cost)
  if (params.max_cost) qs.set('max_cost', params.max_cost)
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.tag) qs.set('tag', params.tag)
  if (params.tool_name) qs.set('tool_name', params.tool_name)
  if (params.security_event_only) qs.set('security_event_only', 'true')
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)

  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<RunListResponse>(`/runs${query}`, apiKey)
}

export async function getRun(
  apiKey: string,
  runId: string,
  params: { access_group_id?: string } = {}
): Promise<RunDetailResponse> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<RunDetailResponse>(`/runs/${runId}${query}`, apiKey)
}

export async function getRunGraph(
  apiKey: string,
  runId: string,
  params: { access_group_id?: string } = {}
): Promise<RunGraphResponse> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<RunGraphResponse>(`/runs/${runId}/graph${query}`, apiKey)
}

export async function getRunGovernanceContext(
  apiKey: string,
  runId: string,
  params: { access_group_id?: string } = {}
): Promise<import('@/types/api').RunGovernanceContextResponse> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').RunGovernanceContextResponse>(`/runs/${runId}/governance${query}`, apiKey)
}

export async function cancelRun(apiKey: string, runId: string): Promise<RunListItem> {
  return apiFetch<RunListItem>(`/runs/${runId}/cancel`, apiKey, { method: 'PATCH' })
}

export async function getRunFlow(
  apiKey: string,
  params: {
    scope?: 'workspace' | 'org' | 'platform'
    mode?: string
    metric?: string
    limit?: number
    from?: string
    to?: string
    access_group_id?: string
    tag?: string
    tool_name?: string
    security_event_only?: boolean
    api_key_id?: string
    end_user_id?: string
  } = {}
): Promise<import('@/types/api').RunFlowResponse> {
  const qs = new URLSearchParams()
  if (params.scope) qs.set('scope', params.scope)
  if (params.mode) qs.set('mode', params.mode)
  if (params.metric) qs.set('metric', params.metric)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.from) qs.set('from', params.from)
  if (params.to) qs.set('to', params.to)
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.tag) qs.set('tag', params.tag)
  if (params.tool_name) qs.set('tool_name', params.tool_name)
  if (params.security_event_only) qs.set('security_event_only', 'true')
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  if (params.end_user_id) qs.set('end_user_id', params.end_user_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').RunFlowResponse>(`/runs/flow${query}`, apiKey)
}

// ── Analytics helpers ─────────────────────────────────────────────────────────

interface TimeWindow {
  from?: string
  to?: string
  [key: string]: string | number | boolean | undefined
}

function _analyticsQs(params: TimeWindow & Record<string, string | number | boolean | undefined>): string {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined) qs.set(k, String(v))
  })
  const s = qs.toString()
  return s ? `?${s}` : ''
}

export async function getAnalyticsSummary(
  apiKey: string,
  window: TimeWindow = {}
): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>(
    `/analytics/summary${_analyticsQs(window)}`,
    apiKey
  )
}

export async function getSpendOverTime(
  apiKey: string,
  granularity: 'minute' | '5min' | 'hourly' | 'daily' = 'daily',
  window: TimeWindow = {}
): Promise<SpendOverTime> {
  return apiFetch<SpendOverTime>(
    `/analytics/spend-over-time${_analyticsQs({ granularity, ...window })}`,
    apiKey
  )
}

export async function getSpendByModel(
  apiKey: string,
  window: TimeWindow = {}
): Promise<SpendByModel> {
  return apiFetch<SpendByModel>(
    `/analytics/spend-by-model${_analyticsQs(window)}`,
    apiKey
  )
}

export async function getSpendByFeature(
  apiKey: string,
  window: TimeWindow = {}
): Promise<SpendByFeature> {
  return apiFetch<SpendByFeature>(
    `/analytics/spend-by-feature${_analyticsQs(window)}`,
    apiKey
  )
}

export async function getSpendByUser(
  apiKey: string,
  limit?: number,
  window: TimeWindow = {}
): Promise<SpendByUser> {
  return apiFetch<SpendByUser>(
    `/analytics/spend-by-user${_analyticsQs({
      ...(limit !== undefined ? { limit: String(limit) } : {}),
      ...window,
    })}`,
    apiKey
  )
}

export async function getUserSpend(
  apiKey: string,
  userId: string,
  window: TimeWindow = {}
): Promise<UserSpendDetail> {
  return apiFetch<UserSpendDetail>(
    `/analytics/users/${encodeURIComponent(userId)}${_analyticsQs(window)}`,
    apiKey
  )
}

// ── Budget helpers ─────────────────────────────────────────────────────────────

export async function getBudgets(
  apiKey: string,
  params: { scope_type?: string; scope_id?: string; include_inactive?: boolean } = {}
): Promise<BudgetList> {
  const qs = new URLSearchParams()
  if (params.scope_type) qs.set('scope_type', params.scope_type)
  if (params.scope_id) qs.set('scope_id', params.scope_id)
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<BudgetList>(`/budgets${query}`, apiKey)
}

export async function getBudgetRollup(
  apiKey: string,
  scope: 'workspace' | 'org' | 'platform' = 'workspace'
): Promise<BudgetRollupResponse> {
  return apiFetch<BudgetRollupResponse>(`/budgets/rollup?scope=${scope}`, apiKey)
}

export async function createBudget(
  apiKey: string,
  body: {
    scope_type: string
    scope_id?: string | null
    period_type: string
    limit_usd: number
    action: string
    downgrade_to_model?: string | null
  }
): Promise<Budget> {
  return apiFetch<Budget>('/budgets', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getBudget(apiKey: string, id: string): Promise<Budget> {
  return apiFetch<Budget>(`/budgets/${id}`, apiKey)
}

export async function updateBudget(
  apiKey: string,
  id: string,
  body: Partial<{
    scope_type: string
    scope_id: string | null
    period_type: string
    limit_usd: number
    action: string
    downgrade_to_model: string | null
    is_active: boolean
  }>
): Promise<Budget> {
  return apiFetch<Budget>(`/budgets/${id}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteBudget(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/budgets/${id}`, apiKey, { method: 'DELETE' })
}

export async function getBudgetBreaches(apiKey: string, id: string): Promise<BreachList> {
  return apiFetch<BreachList>(`/budgets/${id}/breaches`, apiKey)
}

export async function listBudgetNotifications(apiKey: string): Promise<NotificationList> {
  return apiFetch<NotificationList>('/budgets/notifications', apiKey)
}

export async function createBudgetNotification(
  apiKey: string,
  body: { channel: string; destination_url: string; events?: string[] }
): Promise<NotificationResponse> {
  return apiFetch<NotificationResponse>('/budgets/notifications', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateBudgetNotification(
  apiKey: string,
  id: string,
  body: { destination_url?: string; events?: string[]; is_active?: boolean }
): Promise<NotificationResponse> {
  return apiFetch<NotificationResponse>(`/budgets/notifications/${id}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteBudgetNotification(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/budgets/notifications/${id}`, apiKey, { method: 'DELETE' })
}

export async function testBudgetNotification(apiKey: string, id: string): Promise<NotificationTestResult> {
  return apiFetch<NotificationTestResult>(`/budgets/notifications/${id}/test`, apiKey, {
    method: 'POST',
  })
}

export async function listBudgetNotificationDeliveries(
  apiKey: string,
  id: string,
  limit = 20
): Promise<NotificationDeliveryList> {
  return apiFetch<NotificationDeliveryList>(`/budgets/notifications/${id}/deliveries?limit=${limit}`, apiKey)
}

export async function getPlatformWebhookDefaults(apiKey: string): Promise<PlatformWebhookDefaults> {
  return apiFetch<PlatformWebhookDefaults>('/settings/webhooks/defaults', apiKey)
}

export async function updatePlatformWebhookDefaults(
  apiKey: string,
  body: { generic_webhook_url?: string | null; slack_webhook_url?: string | null; events: string[] }
): Promise<PlatformWebhookDefaults> {
  return apiFetch<PlatformWebhookDefaults>('/settings/webhooks/defaults', apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function testPlatformWebhookDefaults(apiKey: string): Promise<PlatformWebhookDefaultsTestResult> {
  return apiFetch<PlatformWebhookDefaultsTestResult>('/settings/webhooks/defaults/test', apiKey, {
    method: 'POST',
  })
}

// ── Billing helpers ────────────────────────────────────────────────────────────

export async function getBillingPeriods(
  apiKey: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<BillingPeriodList> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<BillingPeriodList>(`/billing/periods${query}`, apiKey)
}

export async function getBillingPeriod(apiKey: string, id: string): Promise<BillingPeriod> {
  return apiFetch<BillingPeriod>(`/billing/periods/${id}`, apiKey)
}

export async function createBillingPeriod(
  apiKey: string,
  body: { period_start: string; period_end: string }
): Promise<BillingPeriod> {
  return apiFetch<BillingPeriod>('/billing/periods', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function closeBillingPeriod(apiKey: string, id: string): Promise<UsageSnapshot> {
  return apiFetch<UsageSnapshot>(`/billing/periods/${id}/close`, apiKey, { method: 'POST' })
}

export async function getReconciliation(
  apiKey: string,
  id: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<ReconciliationResult> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<ReconciliationResult>(`/billing/periods/${id}/reconciliation${query}`, apiKey)
}

export async function getPeriodBreakdown(
  apiKey: string,
  id: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<PeriodBreakdown> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<PeriodBreakdown>(`/billing/periods/${id}/breakdown${query}`, apiKey)
}

export async function listBillingAdjustments(
  apiKey: string,
  id: string
): Promise<BillingAdjustmentList> {
  return apiFetch<BillingAdjustmentList>(`/billing/periods/${id}/adjustments`, apiKey)
}

export async function createBillingAdjustment(
  apiKey: string,
  id: string,
  body: {
    adjustment_type: 'credit' | 'refund' | 'prepaid_deduction' | 'surcharge'
    amount_usd: string
    description?: string | null
    reference_id?: string | null
  }
): Promise<BillingAdjustment> {
  return apiFetch<BillingAdjustment>(`/billing/periods/${id}/adjustments`, apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateBillingAdjustment(
  apiKey: string,
  periodId: string,
  adjustmentId: string,
  body: {
    adjustment_type?: 'credit' | 'refund' | 'prepaid_deduction' | 'surcharge'
    amount_usd?: string
    description?: string | null
    reference_id?: string | null
  }
): Promise<BillingAdjustment> {
  return apiFetch<BillingAdjustment>(
    `/billing/periods/${periodId}/adjustments/${adjustmentId}`,
    apiKey,
    {
      method: 'PUT',
      body: JSON.stringify(body),
    }
  )
}

export async function deleteBillingAdjustment(
  apiKey: string,
  periodId: string,
  adjustmentId: string
): Promise<void> {
  await apiFetch<void>(`/billing/periods/${periodId}/adjustments/${adjustmentId}`, apiKey, {
    method: 'DELETE',
  })
}

export async function exportPeriodCsv(
  apiKey: string,
  id: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<string> {
  const query = new URLSearchParams({ format: 'csv' })
  if (params.access_group_id) query.set('access_group_id', params.access_group_id)
  if (params.api_key_id) query.set('api_key_id', params.api_key_id)
  const res = await fetch(`${API_URL}/billing/periods/${id}/export?${query.toString()}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.text()
}

export async function exportPeriodSignedJson(
  apiKey: string,
  id: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<object> {
  const query = new URLSearchParams({ format: 'signed_json' })
  if (params.access_group_id) query.set('access_group_id', params.access_group_id)
  if (params.api_key_id) query.set('api_key_id', params.api_key_id)
  return apiFetch<object>(`/billing/periods/${id}/export?${query.toString()}`, apiKey)
}

export async function listSharedCostPolicies(
  apiKey: string,
  activeOnly = false
): Promise<SharedCostPolicyList> {
  const qs = activeOnly ? '?active_only=true' : ''
  return apiFetch<SharedCostPolicyList>(`/billing/shared-cost-policies${qs}`, apiKey)
}

export async function createSharedCostPolicy(
  apiKey: string,
  body: {
    name: string
    description?: string | null
    formula_type: 'equal_split' | 'proportional' | 'fixed_weight'
    allocations: Array<{
      label: string
      cost_center_id?: string | null
      weight?: string | null
      denominator_value?: string | null
    }>
    is_active?: boolean
  }
): Promise<SharedCostPolicy> {
  return apiFetch<SharedCostPolicy>('/billing/shared-cost-policies', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateSharedCostPolicy(
  apiKey: string,
  policyId: string,
  body: {
    name?: string
    description?: string | null
    formula_type?: 'equal_split' | 'proportional' | 'fixed_weight'
    allocations?: Array<{
      label: string
      cost_center_id?: string | null
      weight?: string | null
      denominator_value?: string | null
    }>
    is_active?: boolean
  }
): Promise<SharedCostPolicy> {
  return apiFetch<SharedCostPolicy>(`/billing/shared-cost-policies/${policyId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteSharedCostPolicy(apiKey: string, policyId: string): Promise<void> {
  await apiFetch<void>(`/billing/shared-cost-policies/${policyId}`, apiKey, {
    method: 'DELETE',
  })
}

export async function previewSharedCostAllocation(
  apiKey: string,
  policyId: string,
  poolUsd: string
): Promise<SharedCostAllocationResult> {
  return apiFetch<SharedCostAllocationResult>(
    `/billing/shared-cost-policies/${policyId}/allocate`,
    apiKey,
    {
      method: 'POST',
      body: JSON.stringify({ pool_usd: poolUsd }),
    }
  )
}

export async function listBillingWebhooks(
  apiKey: string
): Promise<import('@/types/api').BillingWebhookConfigList> {
  const result = await listBudgetNotifications(apiKey)
  return {
    items: result.items
      .filter((item) => item.channel === 'webhook')
      .map((item) => ({
        id: item.id,
        workspace_id: '',
        url: item.destination_url,
        label: item.channel,
        enabled: item.is_active,
        created_at: item.created_at,
      })),
  }
}

export async function createBillingWebhook(
  apiKey: string,
  body: { url: string; secret: string; label?: string }
): Promise<import('@/types/api').BillingWebhookConfig> {
  const result = await createBudgetNotification(apiKey, {
    channel: 'webhook',
    destination_url: body.url,
    events: ['budget.breach', 'runaway.detected'],
  })
  return {
    id: result.id,
    workspace_id: '',
    url: result.destination_url,
    label: body.label ?? 'webhook',
    enabled: result.is_active,
    created_at: result.created_at,
  }
}

export async function deleteBillingWebhook(apiKey: string, id: string): Promise<void> {
  await deleteBudgetNotification(apiKey, id)
}

export async function listWebhookDeliveries(
  apiKey: string,
  webhookId: string
): Promise<import('@/types/api').BillingWebhookDeliveryList> {
  void apiKey
  void webhookId
  return { items: [] }
}

export async function listChargebackRules(apiKey: string): Promise<ChargebackRuleList> {
  return apiFetch<ChargebackRuleList>('/billing/chargeback-rules', apiKey)
}

export async function createChargebackRule(
  apiKey: string,
  body: { allocation_type: string; dimension: string; weight: string; cost_center_id?: string | null; require_approval?: boolean }
): Promise<ChargebackRuleResponse> {
  return apiFetch<ChargebackRuleResponse>('/billing/chargeback-rules', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateChargebackRule(
  apiKey: string,
  ruleId: string,
  body: {
    allocation_type?: string
    dimension?: string
    weight?: string
    cost_center_id?: string | null
    status?: 'active' | 'inactive' | 'pending_approval' | 'denied'
  }
): Promise<ChargebackRuleResponse> {
  return apiFetch<ChargebackRuleResponse>(`/billing/chargeback-rules/${ruleId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

// ── Economics helpers (Phase 9) ────────────────────────────────────────────────

export async function getRunEconomics(apiKey: string, runId: string): Promise<RunEconomics> {
  return apiFetch<RunEconomics>(`/analytics/economics/${encodeURIComponent(runId)}`, apiKey)
}

export async function getTopWorkflows(
  apiKey: string,
  params: { metric?: string; limit?: number; from?: string; to?: string } = {}
): Promise<WorkflowTopList> {
  return apiFetch<WorkflowTopList>(
    `/analytics/workflows/top${_analyticsQs({
      ...(params.metric ? { metric: params.metric } : {}),
      ...(params.limit !== undefined ? { limit: String(params.limit) } : {}),
      ...(params.from ? { from: params.from } : {}),
      ...(params.to ? { to: params.to } : {}),
    })}`,
    apiKey
  )
}

export async function getVersionCompare(
  apiKey: string,
  baseline: string,
  comparison: string,
  params: { from?: string; to?: string } = {}
): Promise<VersionCompareResult> {
  return apiFetch<VersionCompareResult>(
    `/analytics/compare${_analyticsQs({
      baseline_version: baseline,
      comparison_version: comparison,
      ...params,
    })}`,
    apiKey
  )
}

export async function getRegressions(
  apiKey: string,
  params: { from?: string; to?: string } = {}
): Promise<RegressionList> {
  return apiFetch<RegressionList>(
    `/analytics/regressions${_analyticsQs(params)}`,
    apiKey
  )
}

export async function createAnnotation(
  apiKey: string,
  body: { note: string; annotation_date: string; version?: string | null }
): Promise<Annotation> {
  return apiFetch<Annotation>('/analytics/annotations', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getAnnotations(
  apiKey: string,
  params: { from?: string; to?: string; version?: string } = {}
): Promise<AnnotationList> {
  return apiFetch<AnnotationList>(
    `/analytics/annotations${_analyticsQs(params)}`,
    apiKey
  )
}

// ── Phase 10 — Users analytics extensions ─────────────────────────────────────

export async function getUserCohorts(
  apiKey: string,
  params: { from?: string; to?: string } = {}
): Promise<CohortList> {
  return apiFetch<CohortList>(
    `/analytics/users/cohorts${_analyticsQs(params)}`,
    apiKey
  )
}

export async function getUserAnomalies(apiKey: string): Promise<AnomalyList> {
  return apiFetch<AnomalyList>('/analytics/users/anomalies', apiKey)
}

// ── Phase 10 — Replay helpers ─────────────────────────────────────────────────

export async function createDataset(
  apiKey: string,
  body: { name: string; run_ids: string[]; source?: string }
): Promise<DatasetResponse> {
  return apiFetch<DatasetResponse>('/replay/datasets', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listDatasets(apiKey: string): Promise<DatasetList> {
  return apiFetch<DatasetList>('/replay/datasets', apiKey)
}

export async function createExperiment(
  apiKey: string,
  body: { dataset_id: string; name: string; configs: { model: string; label?: string }[] }
): Promise<ExperimentResponse> {
  return apiFetch<ExperimentResponse>('/replay/experiments', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listExperiments(
  apiKey: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<ExperimentList> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<ExperimentList>(`/replay/experiments${query}`, apiKey)
}

export async function runExperiment(apiKey: string, id: string): Promise<ExperimentResponse> {
  return apiFetch<ExperimentResponse>(`/replay/experiments/${id}/run`, apiKey, { method: 'POST' })
}

export async function getExperimentResults(
  apiKey: string,
  id: string
): Promise<ExperimentResults> {
  return apiFetch<ExperimentResults>(`/replay/experiments/${id}/results`, apiKey)
}

// ── Phase 11 — Ledger helpers ──────────────────────────────────────────────────

export async function listLedgerSnapshots(apiKey: string): Promise<LedgerSnapshotList> {
  return apiFetch<LedgerSnapshotList>('/ledger/snapshots', apiKey)
}

export async function generateLedgerSnapshot(apiKey: string): Promise<LedgerSnapshotResponse> {
  return apiFetch<LedgerSnapshotResponse>('/ledger/snapshots/generate', apiKey, { method: 'POST' })
}

export async function verifyLedgerSnapshot(
  apiKey: string,
  snapshotDate: string
): Promise<LedgerVerifyResult> {
  return apiFetch<LedgerVerifyResult>(`/ledger/verify/${snapshotDate}`, apiKey)
}

export async function getLedgerClosureSummary(apiKey: string): Promise<LedgerClosureSummary> {
  return apiFetch<LedgerClosureSummary>('/ledger/closure-summary', apiKey)
}

// ── Phase 11 — Tool registry helpers ──────────────────────────────────────────

export async function listToolRegistry(apiKey: string): Promise<ToolRegistryList> {
  return apiFetch<ToolRegistryList>('/tools/registry', apiKey)
}

export async function upsertToolRegistry(
  apiKey: string,
  body: { tool_name: string; policy?: string; runtime_enforcement?: boolean; description?: string | null }
): Promise<ToolRegistryResponse> {
  return apiFetch<ToolRegistryResponse>('/tools/registry', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateToolRegistry(
  apiKey: string,
  toolName: string,
  body: { policy?: string; runtime_enforcement?: boolean; description?: string | null }
): Promise<ToolRegistryResponse> {
  return apiFetch<ToolRegistryResponse>(`/tools/registry/${encodeURIComponent(toolName)}`, apiKey, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function deleteToolRegistry(apiKey: string, toolName: string): Promise<void> {
  await apiFetch<void>(`/tools/registry/${encodeURIComponent(toolName)}`, apiKey, {
    method: 'DELETE',
  })
}

export async function getSecurityEvents(apiKey: string): Promise<SecurityEventList> {
  return apiFetch<SecurityEventList>('/tools/security-events', apiKey)
}

// ── Phase 11 — Privacy helpers ─────────────────────────────────────────────────

export async function getCapturePolicy(
  apiKey: string
): Promise<CapturePolicyResponse | null> {
  const res = await fetch(`${API_URL}/privacy/capture-policy`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (res.status === 404) return null
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<CapturePolicyResponse>
}

export async function upsertCapturePolicy(
  apiKey: string,
  body: { privacy_mode: string; sampled_rate?: number | null }
): Promise<CapturePolicyResponse> {
  return apiFetch<CapturePolicyResponse>('/privacy/capture-policy', apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

// ── Phase 13 — Data Capture Policy Studio helpers ──────────────────────────────

export async function getRetentionPreview(
  apiKey: string,
  privacyMode: string
): Promise<RetentionPreview> {
  return apiFetch<RetentionPreview>(`/settings/capture-policy/retention-preview?privacy_mode=${encodeURIComponent(privacyMode)}`, apiKey)
}

export async function testPiiRedaction(
  apiKey: string,
  text: string
): Promise<PiiTestResult> {
  return apiFetch<PiiTestResult>('/settings/capture-policy/test-pii', apiKey, {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

export async function listCapturePolicyScopes(
  apiKey: string
): Promise<{ items: CapturePolicyScope[] }> {
  return apiFetch<{ items: CapturePolicyScope[] }>('/settings/capture-policy/scopes', apiKey)
}

export async function upsertCapturePolicyScope(
  apiKey: string,
  scope: { scope_type: string; scope_id: string; privacy_mode: string; sampled_rate: number | null }
): Promise<CapturePolicyScope> {
  return apiFetch<CapturePolicyScope>('/settings/capture-policy/scopes', apiKey, {
    method: 'PUT',
    body: JSON.stringify(scope),
  })
}

export async function deleteCapturePolicyScope(
  apiKey: string,
  scopeType: string,
  scopeId: string
): Promise<void> {
  const query = new URLSearchParams({ scope_type: scopeType, scope_id: scopeId }).toString()
  await apiFetch<void>(`/settings/capture-policy/scopes?${query}`, apiKey, {
    method: 'DELETE',
  })
}

// ── Phase 12 — Settings API key helpers ────────────────────────────────────────

export async function listApiKeys(apiKey: string): Promise<ApiKeyResponse[]> {
  return apiFetch<ApiKeyResponse[]>('/settings/api-keys', apiKey)
}

export async function createApiKey(
  apiKey: string,
  body: { name?: string | null; workspace_id?: string; scopes?: string[]; ownership_type?: string; owner_reference?: string | null }
): Promise<ApiKeyCreateResponse> {
  return apiFetch<ApiKeyCreateResponse>('/settings/api-keys', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getApiKeyDetail(apiKey: string, keyId: string): Promise<ApiKeyResponse> {
  return apiFetch<ApiKeyResponse>(`/settings/api-keys/${keyId}`, apiKey)
}

export async function updateApiKey(
  apiKey: string,
  keyId: string,
  body: import('@/types/api').ApiKeyUpdateRequest
): Promise<ApiKeyResponse> {
  return apiFetch<ApiKeyResponse>(`/settings/api-keys/${keyId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

// Workspaces in the caller's org (org-admin) — used to pick where a key is minted.
export async function listOrgWorkspaces(
  apiKey: string
): Promise<{ id: string; name: string }[]> {
  return apiFetch<{ id: string; name: string }[]>('/org/workspaces', apiKey)
}

// ── Identity registry (org-admin) — Users page ────────────────────────────────
export interface OrgUser {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  email_verified: boolean
  org_role: string | null
  last_login_at: string | null
  created_at: string
}

export async function listOrgUsers(apiKey: string): Promise<OrgUser[]> {
  return apiFetch<OrgUser[]>('/users/all', apiKey)
}

export async function createOrgUser(
  apiKey: string,
  body: { email: string; full_name?: string | null; temporary_password?: string; skip_verification?: boolean }
): Promise<OrgUser> {
  return apiFetch<OrgUser>('/users', apiKey, { method: 'POST', body: JSON.stringify(body) })
}

export async function updateOrgUser(
  apiKey: string,
  userId: string,
  body: { full_name?: string | null; password?: string; is_active?: boolean; email_verified?: boolean }
): Promise<OrgUser> {
  return apiFetch<OrgUser>(`/users/${userId}`, apiKey, { method: 'PUT', body: JSON.stringify(body) })
}

export async function getUserFinance(apiKey: string, userId: string): Promise<import('@/types/api').UserFinanceSummary> {
  return apiFetch<import('@/types/api').UserFinanceSummary>(`/users/${userId}/finance`, apiKey)
}

export async function getUserGovernance(apiKey: string, userId: string): Promise<import('@/types/api').UserGovernanceSummary> {
  return apiFetch<import('@/types/api').UserGovernanceSummary>(`/users/${userId}/governance`, apiKey)
}

// Platform-admin: create a new organization (adds you as its org admin).
export async function createOrganization(
  apiKey: string,
  body: {
    name: string
    admin_email: string
    admin_password: string
    admin_full_name?: string | null
    skip_verification?: boolean
  }
): Promise<{ id: string; name: string }> {
  return apiFetch<{ id: string; name: string }>('/org/tenants', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listPlatformOrganizations(apiKey: string): Promise<TenantResponse[]> {
  return apiFetch<TenantResponse[]>('/org/tenants', apiKey)
}

export async function updatePlatformOrganization(
  apiKey: string,
  tenantId: string,
  body: { name?: string; plan?: string; status?: TenantStatus }
): Promise<TenantResponse> {
  return apiFetch<TenantResponse>(`/org/tenants/${tenantId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deletePlatformOrganization(
  apiKey: string,
  tenantId: string,
  confirmation: string
): Promise<void> {
  await apiFetch<void>(`/org/tenants/${tenantId}`, apiKey, {
    method: 'DELETE',
    body: JSON.stringify({ confirmation }),
  })
}

export async function revokeApiKey(apiKey: string, keyId: string): Promise<void> {
  await apiFetch<void>(`/settings/api-keys/${keyId}`, apiKey, { method: 'DELETE' })
}

export async function repriceProvider(
  apiKey: string,
  body: { provider: string; model?: string | null }
): Promise<{ reset: number }> {
  return apiFetch<{ reset: number }>('/providers/reprice', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// ── Phase 12 — Provider pricing helpers ────────────────────────────────────────

export async function listProviderPricing(apiKey: string): Promise<ProviderPricingList> {
  return apiFetch<ProviderPricingList>('/providers/pricing', apiKey)
}

export async function createProviderPricing(
  apiKey: string,
  body: {
    provider: string
    model: string
    input_cost_per_1m: string
    output_cost_per_1m: string
    cached_input_cost_per_1m?: string | null
    tags?: string[]
    display_name?: string | null
  }
): Promise<ProviderPricingResponse> {
  return apiFetch<ProviderPricingResponse>('/providers/pricing', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateProviderPricing(
  apiKey: string,
  pricingId: string,
  body: {
    input_cost_per_1m?: string
    output_cost_per_1m?: string
    cached_input_cost_per_1m?: string | null
    tags?: string[]
    display_name?: string | null
  }
): Promise<ProviderPricingResponse> {
  return apiFetch<ProviderPricingResponse>(`/providers/pricing/${pricingId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function importProviderPricing(
  apiKey: string,
  file: File,
): Promise<import('@/types/api').PricingImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_URL}/providers/pricing/import`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}` }, // no Content-Type — browser sets multipart boundary
    body: form,
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json()
}

export async function getPricingExampleYaml(apiKey: string): Promise<string> {
  const res = await fetch(`${API_URL}/providers/pricing/example`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API ${res.status}`)
  return res.text()
}

export async function deleteProviderPricing(apiKey: string, pricingId: string): Promise<void> {
  await apiFetch<void>(`/providers/pricing/${pricingId}`, apiKey, { method: 'DELETE' })
}

// ── Phase 14 — Integrations helpers ────────────────────────────────────────────

export async function exportAnalytics(
  apiKey: string,
  format: 'csv' | 'json' = 'json',
  from?: string,
  to?: string
): Promise<AnalyticsExport | string> {
  const qs = new URLSearchParams({ format })
  if (from) qs.set('from', from)
  if (to) qs.set('to', to)

  const res = await fetch(`${API_URL}/analytics/export?${qs.toString()}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }

  if (format === 'csv') {
    return res.text()
  }

  return res.json() as Promise<AnalyticsExport>
}

export async function testSlackWebhook(
  apiKey: string,
  webhookUrl: string
): Promise<SlackTestResponse> {
  return apiFetch<SlackTestResponse>('/integrations/slack/test', apiKey, {
    method: 'POST',
    body: JSON.stringify({ webhook_url: webhookUrl }),
  })
}

// ── Admin helpers (X-Admin-Secret) ────────────────────────────────────────────

export async function listTenants(adminSecret: string): Promise<TenantResponse[]> {
  return adminFetch<TenantResponse[]>('/admin/tenants', adminSecret)
}

export async function createTenant(
  adminSecret: string,
  body: { slug: string; name: string; plan?: string }
): Promise<TenantResponse> {
  return adminFetch<TenantResponse>('/admin/tenants', adminSecret, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listAdminWorkspaces(
  adminSecret: string,
  tenantId: string
): Promise<AdminWorkspaceResponse[]> {
  return adminFetch<AdminWorkspaceResponse[]>(`/admin/tenants/${tenantId}/workspaces`, adminSecret)
}

export async function createAdminWorkspace(
  adminSecret: string,
  body: { tenant_id: string; name: string }
): Promise<AdminWorkspaceResponse> {
  return adminFetch<AdminWorkspaceResponse>('/admin/workspaces', adminSecret, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function createGlobalPricing(
  adminSecret: string,
  body: {
    provider: string
    model: string
    input_cost_per_1m: string
    output_cost_per_1m: string
    cached_input_cost_per_1m?: string | null
  }
): Promise<ProviderPricingResponse> {
  return adminFetch<ProviderPricingResponse>('/admin/global-pricing', adminSecret, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateGlobalPricing(
  adminSecret: string,
  pricingId: string,
  body: {
    input_cost_per_1m?: string
    output_cost_per_1m?: string
    cached_input_cost_per_1m?: string | null
  }
): Promise<ProviderPricingResponse> {
  return adminFetch<ProviderPricingResponse>(`/admin/global-pricing/${pricingId}`, adminSecret, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteGlobalPricing(adminSecret: string, pricingId: string): Promise<void> {
  await adminFetch<void>(`/admin/global-pricing/${pricingId}`, adminSecret, { method: 'DELETE' })
}

// ── Phase 17 — Evaluations & Scores ───────────────────────────────────────────

export async function submitScore(
  apiKey: string,
  body: {
    name: string
    value: number
    run_id?: string | null
    span_id?: string | null
    label?: string | null
    source?: string
    confidence?: number | null
    evidence?: Record<string, unknown> | null
  }
): Promise<ScoreEvent> {
  return apiFetch<ScoreEvent>('/evaluations/scores', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listScores(
  apiKey: string,
  params: {
    run_id?: string
    name?: string
    source?: string
    from?: string
    to?: string
    access_group_id?: string
    api_key_id?: string
    limit?: number
  } = {}
): Promise<ScoreList> {
  const qs = new URLSearchParams()
  if (params.run_id) qs.set('run_id', params.run_id)
  if (params.name) qs.set('name', params.name)
  if (params.source) qs.set('source', params.source)
  if (params.from) qs.set('from', params.from)
  if (params.to) qs.set('to', params.to)
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  if (params.limit) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<ScoreList>(`/evaluations/scores${query}`, apiKey)
}

export async function getScoreSummary(apiKey: string): Promise<ScoreSummary> {
  return apiFetch<ScoreSummary>('/analytics/scores/summary', apiKey)
}

// ── Phase 18 — Prompt Management ───────────────────────────────────────────────

export async function listPrompts(apiKey: string): Promise<PromptList> {
  return apiFetch<PromptList>('/prompts', apiKey)
}

export async function createPrompt(
  apiKey: string,
  body: { name: string; description?: string | null; default_environment?: string }
): Promise<PromptResponse> {
  return apiFetch<PromptResponse>('/prompts', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getPrompt(apiKey: string, name: string): Promise<PromptResponse> {
  return apiFetch<PromptResponse>(`/prompts/${encodeURIComponent(name)}`, apiKey)
}

export async function deletePrompt(apiKey: string, name: string): Promise<void> {
  return apiFetch<void>(`/prompts/${encodeURIComponent(name)}`, apiKey, {
    method: 'DELETE',
  })
}

export async function createVersion(
  apiKey: string,
  name: string,
  body: {
    content: string
    variables?: Array<{ name: string; type?: string; description?: string }>
    commit_message?: string | null
    environment?: string
    model_hint?: string | null
  }
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(
    `/prompts/${encodeURIComponent(name)}/versions`,
    apiKey,
    { method: 'POST', body: JSON.stringify(body) }
  )
}

export async function listVersions(
  apiKey: string,
  name: string,
  environment?: string
): Promise<VersionList> {
  const qs = environment ? `?environment=${encodeURIComponent(environment)}` : ''
  return apiFetch<VersionList>(
    `/prompts/${encodeURIComponent(name)}/versions${qs}`,
    apiKey
  )
}

export async function getLatestVersion(
  apiKey: string,
  name: string,
  environment = 'production'
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(
    `/prompts/${encodeURIComponent(name)}/latest?environment=${environment}`,
    apiKey
  )
}

export async function promoteVersion(
  apiKey: string,
  name: string,
  body: {
    source_environment?: string
    target_environment?: string
    commit_message?: string | null
  }
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(
    `/prompts/${encodeURIComponent(name)}/promote`,
    apiKey,
    { method: 'POST', body: JSON.stringify(body) }
  )
}

export async function getPromptMetrics(
  apiKey: string,
  name: string
): Promise<PromptMetrics> {
  return apiFetch<PromptMetrics>(
    `/prompts/${encodeURIComponent(name)}/metrics`,
    apiKey
  )
}

// ── Phase 19 — Sessions ────────────────────────────────────────────────────────

export async function listSessions(
  apiKey: string,
  params: {
    q?: string
    end_user_id?: string
    from?: string
    to?: string
    min_turns?: number
    min_cost?: string
    max_cost?: string
    page?: number
    page_size?: number
  } = {}
): Promise<SessionList> {
  const qs = new URLSearchParams()
  if (params.q) qs.set('q', params.q)
  if (params.end_user_id) qs.set('end_user_id', params.end_user_id)
  if (params.from) qs.set('from', params.from)
  if (params.to) qs.set('to', params.to)
  if (params.min_turns) qs.set('min_turns', String(params.min_turns))
  if (params.min_cost) qs.set('min_cost', params.min_cost)
  if (params.max_cost) qs.set('max_cost', params.max_cost)
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<SessionList>(`/sessions${query}`, apiKey)
}

export async function getSession(
  apiKey: string,
  sessionId: string
): Promise<SessionDetail> {
  return apiFetch<SessionDetail>(`/sessions/${encodeURIComponent(sessionId)}`, apiKey)
}

export async function getSessionCostOverTurns(
  apiKey: string,
  sessionId: string
): Promise<TurnCostResponse> {
  return apiFetch<TurnCostResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/cost-over-turns`,
    apiKey
  )
}

// ── Phase 21A — Alert Rules ────────────────────────────────────────────────────

export async function listAlertRules(
  apiKey: string,
  includeInactive = false
): Promise<AlertRuleList> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return apiFetch<AlertRuleList>(`/alerts/rules${qs}`, apiKey)
}

export async function createAlertRule(
  apiKey: string,
  body: {
    name: string
    metric: string
    operator: string
    threshold: number
    window_minutes?: number
    channel_id?: string | null
    email_enabled?: boolean
  }
): Promise<AlertRule> {
  return apiFetch<AlertRule>('/alerts/rules', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateAlertRule(
  apiKey: string,
  ruleId: string,
  body: {
    name?: string
    metric?: string
    operator?: string
    threshold?: number
    window_minutes?: number
    is_active?: boolean
    channel_id?: string | null
    email_enabled?: boolean
  }
): Promise<AlertRule> {
  return apiFetch<AlertRule>(`/alerts/rules/${ruleId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function emailAnalyticsReport(
  apiKey: string,
  windowDays = 7
): Promise<{ queued: boolean; recipients: number }> {
  return apiFetch<{ queued: boolean; recipients: number }>(
    `/analytics/email-report?window_days=${windowDays}`,
    apiKey,
    { method: 'POST' }
  )
}

export async function deleteAlertRule(apiKey: string, ruleId: string): Promise<void> {
  await apiFetch<void>(`/alerts/rules/${ruleId}`, apiKey, { method: 'DELETE' })
}

export async function listAlertHistory(
  apiKey: string,
  limit = 50
): Promise<AlertHistoryList> {
  return apiFetch<AlertHistoryList>(`/alerts/history?limit=${limit}`, apiKey)
}

// suppress unused import warnings for AlertFiring
export type { AlertFiring }

// ── Phase 21B — Model Gateway ──────────────────────────────────────────────────

export async function listGatewayRoutes(
  apiKey: string,
  includeInactive = false
): Promise<GatewayRouteList> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return apiFetch<GatewayRouteList>(`/gateway/routes${qs}`, apiKey)
}

export async function createGatewayRoute(
  apiKey: string,
  body: {
    alias: string
    routing_group_id?: string | null
    provider: string
    target_model: string
    base_url?: string | null
    api_key_env_var?: string | null
    priority?: number
    config?: Record<string, string> | null
    daily_cost_limit_usd?: number | null
    monthly_cost_limit_usd?: number | null
    pii_redaction_enabled?: boolean
    semantic_cache_enabled?: boolean
    context_compiler_enabled?: boolean
    context_compiler_config?: Record<string, unknown> | null
    intelligent_routing_enabled?: boolean
    routing_config?: Record<string, unknown> | null
    per_user_rpm_limit?: number | null
    fallback_config?: Record<string, unknown> | null
    required_tags?: string[]
    excluded_tags?: string[]
    retry_count?: number
    timeout_ms?: number | null
    cooldown_seconds?: number
    region?: string | null
    mirror_config?: Record<string, unknown> | null
    health_auto_disable?: boolean
  }
): Promise<GatewayRoute> {
  return apiFetch<GatewayRoute>('/gateway/routes', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateGatewayRoute(
  apiKey: string,
  routeId: string,
  body: {
    alias?: string
    routing_group_id?: string | null
    target_model?: string
    base_url?: string | null
    api_key_env_var?: string | null
    priority?: number
    is_active?: boolean
    config?: Record<string, unknown> | null
    daily_cost_limit_usd?: number | null
    monthly_cost_limit_usd?: number | null
    pii_redaction_enabled?: boolean
    semantic_cache_enabled?: boolean
    context_compiler_enabled?: boolean
    context_compiler_config?: Record<string, unknown> | null
    intelligent_routing_enabled?: boolean
    routing_config?: Record<string, unknown> | null
    per_user_rpm_limit?: number | null
    fallback_config?: Record<string, unknown> | null
    required_tags?: string[]
    excluded_tags?: string[]
    retry_count?: number
    timeout_ms?: number | null
    cooldown_seconds?: number
    region?: string | null
    mirror_config?: Record<string, unknown> | null
    health_auto_disable?: boolean
  }
): Promise<GatewayRoute> {
  return apiFetch<GatewayRoute>(`/gateway/routes/${routeId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteGatewayRoute(apiKey: string, routeId: string): Promise<void> {
  await apiFetch<void>(`/gateway/routes/${routeId}`, apiKey, { method: 'DELETE' })
}

export async function listGatewayRoutingGroups(
  apiKey: string,
  params?: { alias?: string; include_inactive?: boolean }
): Promise<GatewayRoutingGroupList> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
  ).toString() : ''
  return apiFetch<GatewayRoutingGroupList>(`/gateway/routing-groups${qs}`, apiKey)
}

export async function createGatewayRoutingGroup(
  apiKey: string,
  body: {
    alias: string
    name: string
    description?: string | null
    match_tags?: string[]
    default_tags?: string[]
    strategy_type?: 'manual' | 'latency_optimized' | 'round_robin'
    strategy_config?: Record<string, unknown> | null
    is_active?: boolean
  }
): Promise<GatewayRoutingGroup> {
  return apiFetch<GatewayRoutingGroup>('/gateway/routing-groups', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateGatewayRoutingGroup(
  apiKey: string,
  groupId: string,
  body: Partial<{
    alias: string
    name: string
    description: string | null
    match_tags: string[]
    default_tags: string[]
    strategy_type: 'manual' | 'latency_optimized' | 'round_robin'
    strategy_config: Record<string, unknown> | null
    is_active: boolean
  }>
): Promise<GatewayRoutingGroup> {
  return apiFetch<GatewayRoutingGroup>(`/gateway/routing-groups/${groupId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteGatewayRoutingGroup(apiKey: string, groupId: string): Promise<void> {
  await apiFetch<void>(`/gateway/routing-groups/${groupId}`, apiKey, { method: 'DELETE' })
}

export async function getGatewayRoutingStrategyComparison(
  apiKey: string
): Promise<GatewayRoutingStrategyComparison> {
  return apiFetch<GatewayRoutingStrategyComparison>('/gateway/routing-groups/strategy-comparison', apiKey)
}

export async function getGatewayStats(apiKey: string): Promise<GatewayStats> {
  return apiFetch<GatewayStats>('/gateway/stats', apiKey)
}

export async function getGatewayRateLimitOverview(
  apiKey: string,
): Promise<import('@/types/api').GatewayRateLimitOverview> {
  return apiFetch<import('@/types/api').GatewayRateLimitOverview>(
    '/gateway/rate-limits/overview',
    apiKey,
  )
}

export async function listGatewayRequests(
  apiKey: string,
  params?: { alias?: string; status?: string; limit?: number; offset?: number }
): Promise<GatewayRequestList> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
  ).toString() : ''
  return apiFetch<GatewayRequestList>(`/gateway/requests${qs}`, apiKey)
}

export async function listGatewayPassThroughEndpoints(
  apiKey: string,
  includeInactive = false
): Promise<import('@/types/api').GatewayPassThroughEndpointList> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return apiFetch<import('@/types/api').GatewayPassThroughEndpointList>(`/gateway/passthrough${qs}`, apiKey)
}

export async function createGatewayPassThroughEndpoint(
  apiKey: string,
  body: {
    slug: string
    path_prefix?: string
    upstream_base_url: string
    auth_type?: string | null
    auth_config?: Record<string, unknown>
    header_config?: Record<string, unknown>
    default_query?: Record<string, unknown>
    timeout_ms?: number
    rate_limit_rpm?: number | null
    cost_per_call_usd?: number | null
    is_active?: boolean
  }
): Promise<import('@/types/api').GatewayPassThroughEndpoint> {
  return apiFetch<import('@/types/api').GatewayPassThroughEndpoint>('/gateway/passthrough', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateGatewayPassThroughEndpoint(
  apiKey: string,
  endpointId: string,
  body: {
    path_prefix?: string
    upstream_base_url?: string
    auth_type?: string | null
    auth_config?: Record<string, unknown> | null
    header_config?: Record<string, unknown> | null
    default_query?: Record<string, unknown> | null
    timeout_ms?: number | null
    rate_limit_rpm?: number | null
    cost_per_call_usd?: number | null
    is_active?: boolean
  }
): Promise<import('@/types/api').GatewayPassThroughEndpoint> {
  return apiFetch<import('@/types/api').GatewayPassThroughEndpoint>(`/gateway/passthrough/${endpointId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteGatewayPassThroughEndpoint(apiKey: string, endpointId: string): Promise<void> {
  await apiFetch<void>(`/gateway/passthrough/${endpointId}`, apiKey, { method: 'DELETE' })
}

export async function testGatewayPassThroughEndpoint(
  apiKey: string,
  endpointId: string,
  body?: {
    method?: string
    path?: string | null
    query?: Record<string, string>
    headers?: Record<string, string>
    body_json?: Record<string, unknown> | null
  }
): Promise<import('@/types/api').GatewayPassThroughTestResult> {
  return apiFetch<import('@/types/api').GatewayPassThroughTestResult>(
    `/gateway/passthrough/${endpointId}/test`,
    apiKey,
    {
      method: 'POST',
      body: JSON.stringify(body ?? {}),
    },
  )
}

export async function listGatewayPassThroughStats(
  apiKey: string,
): Promise<import('@/types/api').GatewayPassThroughEndpointStatsList> {
  return apiFetch<import('@/types/api').GatewayPassThroughEndpointStatsList>(
    '/gateway/passthrough/stats',
    apiKey,
  )
}

export async function getGatewayBenchmarkComparison(
  apiKey: string,
  params?: { days?: number; alias?: string }
): Promise<import('@/types/api').GatewayBenchmarkComparisonList> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
  ).toString() : ''
  return apiFetch<import('@/types/api').GatewayBenchmarkComparisonList>(
    `/gateway/benchmarks/compare${qs}`,
    apiKey,
  )
}

// ── Routing policies ──────────────────────────────────────────────────────────

export async function listRoutingPolicies(apiKey: string): Promise<RoutingPolicyList> {
  return apiFetch<RoutingPolicyList>('/gateway/policies', apiKey)
}

export async function createRoutingPolicy(
  apiKey: string,
  body: { alias: string; policy_type: RoutingPolicyType; config: Record<string, unknown> }
): Promise<RoutingPolicy> {
  return apiFetch<RoutingPolicy>('/gateway/policies', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function updateRoutingPolicy(
  apiKey: string,
  policyId: string,
  body: { policy_type?: RoutingPolicyType; config?: Record<string, unknown>; is_active?: boolean }
): Promise<RoutingPolicy> {
  return apiFetch<RoutingPolicy>(`/gateway/policies/${policyId}`, apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deleteRoutingPolicy(apiKey: string, policyId: string): Promise<void> {
  await apiFetch<void>(`/gateway/policies/${policyId}`, apiKey, { method: 'DELETE' })
}

export async function getRoutingPolicyAnalysis(
  apiKey: string,
  policyId: string,
): Promise<import('@/types/api').RoutingPolicyAnalysis> {
  return apiFetch<import('@/types/api').RoutingPolicyAnalysis>(
    `/gateway/policies/${policyId}/analysis`,
    apiKey,
  )
}

export async function promoteRoutingPolicyWinner(
  apiKey: string,
  policyId: string,
  routeId?: string,
): Promise<import('@/types/api').RoutingPolicyActionResult> {
  return apiFetch<import('@/types/api').RoutingPolicyActionResult>(
    `/gateway/policies/${policyId}/promote`,
    apiKey,
    {
      method: 'POST',
      body: JSON.stringify(routeId ? { route_id: routeId } : {}),
    },
  )
}

export async function advanceCanaryRollout(
  apiKey: string,
  policyId: string,
): Promise<import('@/types/api').RoutingPolicyActionResult> {
  return apiFetch<import('@/types/api').RoutingPolicyActionResult>(
    `/gateway/policies/${policyId}/rollout/advance`,
    apiKey,
    { method: 'POST' },
  )
}

export async function rollbackRoutingPolicy(
  apiKey: string,
  policyId: string,
): Promise<import('@/types/api').RoutingPolicyActionResult> {
  return apiFetch<import('@/types/api').RoutingPolicyActionResult>(
    `/gateway/policies/${policyId}/rollback`,
    apiKey,
    { method: 'POST' },
  )
}

export async function getSecuritySettings(apiKey: string): Promise<import('@/types/api').WorkspaceSecuritySettings> {
  return apiFetch<import('@/types/api').WorkspaceSecuritySettings>('/security/settings', apiKey)
}

export async function updateSecuritySettings(
  apiKey: string,
  body: {
    required_metadata_fields?: string[]
    required_metadata_mode?: string
    data_residency_regions?: string[]
    callback_config?: Record<string, unknown>
    brand_config?: Record<string, unknown>
    oidc_session_config?: Record<string, unknown>
  }
): Promise<import('@/types/api').WorkspaceSecuritySettings> {
  return apiFetch<import('@/types/api').WorkspaceSecuritySettings>('/security/settings', apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function listOidcProviders(apiKey: string): Promise<import('@/types/api').OIDCProviderList> {
  return apiFetch<import('@/types/api').OIDCProviderList>('/security/oidc-providers', apiKey)
}

export async function createOidcProvider(
  apiKey: string,
  body: {
    name: string
    issuer_url: string
    audience?: string | null
    discovery_url?: string | null
    jwks_uri?: string | null
    claim_mappings?: Record<string, unknown>
    is_active?: boolean
  }
): Promise<import('@/types/api').OIDCProviderResponse> {
  return apiFetch<import('@/types/api').OIDCProviderResponse>('/security/oidc-providers', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateOidcProvider(
  apiKey: string,
  providerId: string,
  body: {
    name?: string
    issuer_url?: string
    audience?: string | null
    discovery_url?: string | null
    jwks_uri?: string | null
    claim_mappings?: Record<string, unknown> | null
    is_active?: boolean
  }
): Promise<import('@/types/api').OIDCProviderResponse> {
  return apiFetch<import('@/types/api').OIDCProviderResponse>(`/security/oidc-providers/${providerId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteOidcProvider(apiKey: string, providerId: string): Promise<void> {
  await apiFetch<void>(`/security/oidc-providers/${providerId}`, apiKey, { method: 'DELETE' })
}

export async function listIpAclRules(apiKey: string): Promise<import('@/types/api').IpAclRuleList> {
  return apiFetch<import('@/types/api').IpAclRuleList>('/security/ip-acl', apiKey)
}

export async function createIpAclRule(
  apiKey: string,
  body: {
    scope_type: string
    api_key_id?: string | null
    team_name?: string | null
    cidr: string
    action: string
    priority?: number
    description?: string | null
  }
): Promise<import('@/types/api').IpAclRuleResponse> {
  return apiFetch<import('@/types/api').IpAclRuleResponse>('/security/ip-acl', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateIpAclRule(
  apiKey: string,
  ruleId: string,
  body: {
    api_key_id?: string | null
    team_name?: string | null
    cidr?: string
    action?: string
    priority?: number
    description?: string | null
  }
): Promise<import('@/types/api').IpAclRuleResponse> {
  return apiFetch<import('@/types/api').IpAclRuleResponse>(`/security/ip-acl/${ruleId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteIpAclRule(apiKey: string, ruleId: string): Promise<void> {
  await apiFetch<void>(`/security/ip-acl/${ruleId}`, apiKey, { method: 'DELETE' })
}

export async function testIpAcl(
  apiKey: string,
  body: { ip: string; api_key_id?: string | null; team_name?: string | null }
): Promise<import('@/types/api').IpAclTestResponse> {
  return apiFetch<import('@/types/api').IpAclTestResponse>('/security/ip-acl/test', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getApiKeyRotationHistory(
  apiKey: string,
  keyId: string
): Promise<import('@/types/api').KeyRotationEventList> {
  return apiFetch<import('@/types/api').KeyRotationEventList>(`/security/api-keys/${keyId}/rotation-history`, apiKey)
}

export async function rotateApiKey(
  apiKey: string,
  keyId: string,
  graceHours = 24
): Promise<import('@/types/api').RotateApiKeyResponse> {
  return apiFetch<import('@/types/api').RotateApiKeyResponse>(`/security/api-keys/${keyId}/rotate`, apiKey, {
    method: 'POST',
    body: JSON.stringify({ grace_hours: graceHours }),
  })
}

export async function getRoutingRecommendation(
  apiKey: string,
  alias: string,
  opts?: { window_days?: number; workflow_type?: string; min_sample_size?: number }
): Promise<import('@/types/api').RoutingRecommendationResponse> {
  const params = new URLSearchParams()
  if (opts?.window_days) params.set('window_days', String(opts.window_days))
  if (opts?.workflow_type) params.set('workflow_type', opts.workflow_type)
  if (opts?.min_sample_size) params.set('min_sample_size', String(opts.min_sample_size))
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch<import('@/types/api').RoutingRecommendationResponse>(
    `/gateway/recommendations/${encodeURIComponent(alias)}${qs}`,
    apiKey,
  )
}

// ── Optimization flywheel (Phase 7) ────────────────────────────────────────────

export async function getFlywheelSettings(
  apiKey: string,
): Promise<import('@/types/api').FlywheelSettings> {
  return apiFetch<import('@/types/api').FlywheelSettings>('/gateway/flywheel/settings', apiKey)
}

export async function updateFlywheelSettings(
  apiKey: string,
  body: Partial<import('@/types/api').FlywheelSettings>,
): Promise<import('@/types/api').FlywheelSettings> {
  return apiFetch<import('@/types/api').FlywheelSettings>('/gateway/flywheel/settings', apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function listFlywheelRecommendations(
  apiKey: string,
  params: { status?: string; access_group_id?: string; api_key_id?: string } = {}
): Promise<import('@/types/api').FlywheelRecommendationList> {
  const qs = new URLSearchParams()
  qs.set('status', params.status ?? 'pending')
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  return apiFetch<import('@/types/api').FlywheelRecommendationList>(
    `/gateway/flywheel/recommendations?${qs.toString()}`,
    apiKey,
  )
}

export async function applyFlywheelRecommendation(
  apiKey: string,
  recId: string,
): Promise<import('@/types/api').FlywheelRecommendation> {
  return apiFetch<import('@/types/api').FlywheelRecommendation>(
    `/gateway/flywheel/recommendations/${recId}/apply`,
    apiKey,
    { method: 'POST' },
  )
}

export async function dismissFlywheelRecommendation(
  apiKey: string,
  recId: string,
): Promise<import('@/types/api').FlywheelRecommendation> {
  return apiFetch<import('@/types/api').FlywheelRecommendation>(
    `/gateway/flywheel/recommendations/${recId}/dismiss`,
    apiKey,
    { method: 'POST' },
  )
}

export async function runFlywheel(
  apiKey: string,
): Promise<import('@/types/api').FlywheelRunResponse> {
  return apiFetch<import('@/types/api').FlywheelRunResponse>('/gateway/flywheel/run', apiKey, {
    method: 'POST',
  })
}

// ── Org Dashboard ─────────────────────────────────────────────────────────────

export async function getOrgDashboard(
  apiKey: string,
  window: TimeWindow = {},
): Promise<import('@/types/api').OrgDashboard> {
  return apiFetch<import('@/types/api').OrgDashboard>(
    `/org/dashboard${_analyticsQs(window)}`,
    apiKey,
  )
}

export async function getOrgFinance(
  apiKey: string,
): Promise<import('@/types/api').OrgFinanceSummary> {
  return apiFetch<import('@/types/api').OrgFinanceSummary>('/org/finance', apiKey)
}

export async function getOrgRuntime(
  apiKey: string,
): Promise<import('@/types/api').OrgRuntimeSummary> {
  return apiFetch<import('@/types/api').OrgRuntimeSummary>('/org/runtime', apiKey)
}

export async function getOrgObserve(
  apiKey: string,
): Promise<import('@/types/api').OrgObserveSummary> {
  return apiFetch<import('@/types/api').OrgObserveSummary>('/org/observe', apiKey)
}

export async function getOrgGovernance(
  apiKey: string,
): Promise<import('@/types/api').OrgGovernanceSummary> {
  return apiFetch<import('@/types/api').OrgGovernanceSummary>('/org/governance', apiKey)
}

// ── SaaS / Billing ────────────────────────────────────────────────────────────

export async function getSubscription(apiKey: string): Promise<import('@/types/api').SubscriptionResponse> {
  return apiFetch<import('@/types/api').SubscriptionResponse>('/billing/subscription', apiKey)
}

export async function createCheckout(apiKey: string, plan: string, successUrl: string, cancelUrl: string): Promise<{ checkout_url: string }> {
  return apiFetch<{ checkout_url: string }>('/billing/checkout', apiKey, {
    method: 'POST',
    body: JSON.stringify({ plan, success_url: successUrl, cancel_url: cancelUrl }),
  })
}

// ── Evaluators ────────────────────────────────────────────────────────────────

export async function listEvaluators(apiKey: string): Promise<import('@/types/api').EvaluatorList> {
  return apiFetch<import('@/types/api').EvaluatorList>('/evaluations/evaluators', apiKey)
}

export async function createEvaluator(
  apiKey: string,
  body: { name: string; description?: string; type: string; config: Record<string, unknown> }
): Promise<import('@/types/api').EvaluatorResponse> {
  return apiFetch<import('@/types/api').EvaluatorResponse>('/evaluations/evaluators', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deleteEvaluator(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/evaluations/evaluators/${id}`, apiKey, { method: 'DELETE' })
}

export async function runEvaluator(
  apiKey: string,
  id: string,
  body?: { limit?: number }
): Promise<import('@/types/api').EvaluatorRunResult> {
  return apiFetch<import('@/types/api').EvaluatorRunResult>(`/evaluations/evaluators/${id}/run`, apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? { limit: 100 }),
  })
}

// ── Cost-quality analytics ────────────────────────────────────────────────────

export async function getCostQuality(
  apiKey: string,
  params?: { score_name?: string; from?: string; to?: string }
): Promise<import('@/types/api').CostQualityResponse> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
  ).toString() : ''
  return apiFetch<import('@/types/api').CostQualityResponse>(`/analytics/scores/cost-quality${qs}`, apiKey)
}

export async function getBestValueModels(
  apiKey: string,
  params?: { score_name?: string; from?: string; to?: string }
): Promise<import('@/types/api').BestValueResponse> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
  ).toString() : ''
  return apiFetch<import('@/types/api').BestValueResponse>(`/analytics/scores/best-value${qs}`, apiKey)
}

// ── Provider Invoice Reconciliation ───────────────────────────────────────────

export async function listInvoices(
  apiKey: string,
  params?: { provider?: string; status?: string }
): Promise<import('@/types/api').InvoiceList> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
  ).toString() : ''
  return apiFetch<import('@/types/api').InvoiceList>(`/invoices${qs}`, apiKey)
}

export async function getInvoiceSummary(
  apiKey: string,
  invoiceId: string
): Promise<import('@/types/api').ReconciliationSummary> {
  return apiFetch<import('@/types/api').ReconciliationSummary>(`/invoices/${invoiceId}`, apiKey)
}

export async function uploadInvoice(
  apiKey: string,
  file: File,
  periodStart: string,
  periodEnd: string,
  provider?: string
): Promise<import('@/types/api').InvoiceResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const qs = new URLSearchParams({ period_start: periodStart, period_end: periodEnd })
  if (provider) qs.set('provider', provider)
  const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
  const res = await fetch(`${API_URL}/invoices/upload?${qs}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}` },
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Upload failed: ${res.status}`)
  }
  return res.json()
}

export async function reconcileInvoice(
  apiKey: string,
  invoiceId: string
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/invoices/${invoiceId}/reconcile`, apiKey, {
    method: 'POST',
  })
}

export async function deleteInvoice(apiKey: string, invoiceId: string): Promise<void> {
  await apiFetch<void>(`/invoices/${invoiceId}`, apiKey, { method: 'DELETE' })
}

export async function listInvoiceLines(
  apiKey: string,
  invoiceId: string,
  params?: { match_status?: string; limit?: number; offset?: number }
): Promise<import('@/types/api').InvoiceLineList> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
  ).toString() : ''
  return apiFetch<import('@/types/api').InvoiceLineList>(`/invoices/${invoiceId}/lines${qs}`, apiKey)
}

export async function disputeInvoiceLine(
  apiKey: string,
  invoiceId: string,
  lineId: string,
  note: string
): Promise<import('@/types/api').InvoiceLineResponse> {
  return apiFetch<import('@/types/api').InvoiceLineResponse>(
    `/invoices/${invoiceId}/lines/${lineId}/dispute`,
    apiKey,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    }
  )
}

// ── Outcomes ──────────────────────────────────────────────────────────────────

export async function getOutcomeSummary(
  apiKey: string,
  windowDays = 30
): Promise<import('@/types/api').OutcomeSummary> {
  return apiFetch<import('@/types/api').OutcomeSummary>(
    `/outcomes/summary?window_days=${windowDays}`,
    apiKey
  )
}

export async function getOutcomeTrend(
  apiKey: string,
  windowDays = 30,
  outcomeType?: string
): Promise<import('@/types/api').OutcomeTrend> {
  const params = new URLSearchParams({ window_days: String(windowDays) })
  if (outcomeType) params.set('outcome_type', outcomeType)
  return apiFetch<import('@/types/api').OutcomeTrend>(`/outcomes/trend?${params}`, apiKey)
}

export async function getWorkflowROI(
  apiKey: string,
  windowDays = 30
): Promise<import('@/types/api').WorkflowROIList> {
  return apiFetch<import('@/types/api').WorkflowROIList>(
    `/outcomes/workflows?window_days=${windowDays}`,
    apiKey
  )
}

export async function getQualityCorrelation(
  apiKey: string,
  windowDays = 30
): Promise<import('@/types/api').QualityOutcomeCorrelation[]> {
  return apiFetch<import('@/types/api').QualityOutcomeCorrelation[]>(
    `/outcomes/quality-correlation?window_days=${windowDays}`,
    apiKey
  )
}

export async function listOutcomes(
  apiKey: string,
  params?: { outcome_type?: string; success?: boolean; run_id?: string; end_user_id?: string; limit?: number; offset?: number }
): Promise<import('@/types/api').OutcomeList> {
  const q = new URLSearchParams()
  if (params?.outcome_type) q.set('outcome_type', params.outcome_type)
  if (params?.success !== undefined) q.set('success', String(params.success))
  if (params?.run_id) q.set('run_id', params.run_id)
  if (params?.end_user_id) q.set('end_user_id', params.end_user_id)
  if (params?.limit) q.set('limit', String(params.limit))
  if (params?.offset !== undefined) q.set('offset', String(params.offset))
  return apiFetch<import('@/types/api').OutcomeList>(
    `/outcomes${q.toString() ? '?' + q.toString() : ''}`,
    apiKey
  )
}

export async function getOutcome(
  apiKey: string,
  outcomeId: string
): Promise<import('@/types/api').OutcomeResponse> {
  return apiFetch<import('@/types/api').OutcomeResponse>(`/outcomes/${encodeURIComponent(outcomeId)}`, apiKey)
}

export async function createOutcome(
  apiKey: string,
  body: {
    outcome_type: string
    success: boolean
    run_id?: string | null
    session_id?: string | null
    end_user_id?: string | null
    value_usd?: string | number | null
    labels?: Record<string, unknown>
  }
): Promise<import('@/types/api').OutcomeResponse> {
  return apiFetch<import('@/types/api').OutcomeResponse>('/outcomes', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateOutcome(
  apiKey: string,
  outcomeId: string,
  body: {
    outcome_type: string
    success: boolean
    run_id?: string | null
    session_id?: string | null
    end_user_id?: string | null
    value_usd?: string | number | null
    labels?: Record<string, unknown>
  }
): Promise<import('@/types/api').OutcomeResponse> {
  return apiFetch<import('@/types/api').OutcomeResponse>(`/outcomes/${encodeURIComponent(outcomeId)}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteOutcome(apiKey: string, outcomeId: string): Promise<void> {
  await apiFetch<void>(`/outcomes/${encodeURIComponent(outcomeId)}`, apiKey, { method: 'DELETE' })
}

// ── Approvals ─────────────────────────────────────────────────────────────────

export async function getApprovalSummary(
  apiKey: string
): Promise<import('@/types/api').ApprovalSummary> {
  return apiFetch<import('@/types/api').ApprovalSummary>('/approvals/summary', apiKey)
}

export async function listApprovals(
  apiKey: string,
  params?: { status?: string; request_type?: string; requested_by?: string; access_group_id?: string; api_key_prefix?: string; limit?: number }
): Promise<import('@/types/api').ApprovalList> {
  const q = new URLSearchParams()
  if (params?.status) q.set('status', params.status)
  if (params?.request_type) q.set('request_type', params.request_type)
  if (params?.requested_by) q.set('requested_by', params.requested_by)
  if (params?.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params?.api_key_prefix) q.set('api_key_prefix', params.api_key_prefix)
  if (params?.limit) q.set('limit', String(params.limit))
  return apiFetch<import('@/types/api').ApprovalList>(
    `/approvals${q.toString() ? '?' + q.toString() : ''}`,
    apiKey
  )
}

export async function createApproval(
  apiKey: string,
  body: { request_type: string; request?: Record<string, unknown>; reason?: string }
): Promise<import('@/types/api').ApprovalResponse> {
  return apiFetch<import('@/types/api').ApprovalResponse>('/approvals', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function approveApproval(
  apiKey: string,
  id: string,
  note?: string
): Promise<import('@/types/api').ApprovalResponse> {
  return apiFetch<import('@/types/api').ApprovalResponse>(`/approvals/${id}/approve`, apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note: note ?? null }),
  })
}

export async function denyApproval(
  apiKey: string,
  id: string,
  note?: string
): Promise<import('@/types/api').ApprovalResponse> {
  return apiFetch<import('@/types/api').ApprovalResponse>(`/approvals/${id}/deny`, apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note: note ?? null }),
  })
}

export async function cancelApproval(
  apiKey: string,
  id: string
): Promise<import('@/types/api').ApprovalResponse> {
  return apiFetch<import('@/types/api').ApprovalResponse>(`/approvals/${id}`, apiKey, {
    method: 'DELETE',
  })
}

// ── Phase 13: Auto-Approval Policies ────────────────────────────────────────

export async function listAutoApprovalPolicies(
  apiKey: string
): Promise<import('@/types/api').AutoApprovalPolicyList> {
  return apiFetch<import('@/types/api').AutoApprovalPolicyList>('/approvals/auto-policies', apiKey)
}

export async function createAutoApprovalPolicy(
  apiKey: string,
  body: { request_type: string; condition: string }
): Promise<import('@/types/api').AutoApprovalPolicy> {
  return apiFetch<import('@/types/api').AutoApprovalPolicy>('/approvals/auto-policies', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateAutoApprovalPolicy(
  apiKey: string,
  policyId: string,
  body: { request_type?: string; condition?: string }
): Promise<import('@/types/api').AutoApprovalPolicy> {
  return apiFetch<import('@/types/api').AutoApprovalPolicy>(`/approvals/auto-policies/${policyId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteAutoApprovalPolicy(
  apiKey: string,
  policyId: string
): Promise<void> {
  await apiFetch<void>(`/approvals/auto-policies/${policyId}`, apiKey, { method: 'DELETE' })
}

// ── OTLP ──────────────────────────────────────────────────────────────────────

export async function getOtlpStats(apiKey: string): Promise<OtlpStats> {
  return apiFetch<OtlpStats>('/v1/traces/stats', apiKey)
}

export async function listOtlpBatches(
  apiKey: string,
  limit = 20,
  offset = 0
): Promise<OtlpBatchList> {
  return apiFetch<OtlpBatchList>(
    `/v1/traces/batches?limit=${limit}&offset=${offset}`,
    apiKey
  )
}

export async function getOtlpBatchDetail(
  apiKey: string,
  batchId: string
): Promise<OtlpBatchDetail> {
  return apiFetch<OtlpBatchDetail>(`/v1/traces/batches/${batchId}`, apiKey)
}

export async function listAuditEvents(
  apiKey: string,
  params: {
    action?: string
    actor_user_id?: string
    target_type?: string
    target_id?: string
    access_group_id?: string
    api_key_prefix?: string
    limit?: number
    offset?: number
  } = {}
): Promise<AuditEventList> {
  const q = new URLSearchParams()
  if (params.action) q.set('action', params.action)
  if (params.actor_user_id) q.set('actor_user_id', params.actor_user_id)
  if (params.target_type) q.set('target_type', params.target_type)
  if (params.target_id) q.set('target_id', params.target_id)
  if (params.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params.api_key_prefix) q.set('api_key_prefix', params.api_key_prefix)
  q.set('limit', String(params.limit ?? 50))
  q.set('offset', String(params.offset ?? 0))
  return apiFetch<AuditEventList>(`/audit/events?${q.toString()}`, apiKey)
}

export async function getAuditEvent(
  apiKey: string,
  eventId: string
): Promise<import('@/types/api').AuditEvent> {
  return apiFetch<import('@/types/api').AuditEvent>(`/audit/events/${eventId}`, apiKey)
}

export async function listRetentionPolicies(apiKey: string): Promise<RetentionPolicyList> {
  return apiFetch<RetentionPolicyList>('/retention/policies', apiKey)
}

export async function createRetentionPolicy(
  apiKey: string,
  body: {
    resource_type: RetentionResourceType
    action: RetentionActionType
    scope?: RetentionScopeType
    scope_value?: string | null
    max_age_days?: number | null
    is_active?: boolean
  }
): Promise<RetentionPolicy> {
  return apiFetch<RetentionPolicy>('/retention/policies', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateRetentionPolicy(
  apiKey: string,
  policyId: string,
  body: { max_age_days?: number | null; is_active?: boolean; scope_value?: string | null }
): Promise<RetentionPolicy> {
  return apiFetch<RetentionPolicy>(`/retention/policies/${policyId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteRetentionPolicy(apiKey: string, policyId: string): Promise<void> {
  await apiFetch<void>(`/retention/policies/${policyId}`, apiKey, { method: 'DELETE' })
}

export async function purgeRetention(
  apiKey: string,
  body: {
    policy_id?: string | null
    resource_type?: RetentionResourceType | null
    action?: RetentionActionType | null
    scope?: RetentionScopeType
    scope_value?: string | null
    max_age_days?: number | null
    dry_run?: boolean
  }
): Promise<PurgeResult> {
  return apiFetch<PurgeResult>('/retention/purge', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// ── Phase 28: Warehouse Export ────────────────────────────────────────────────
import type {
  WarehouseDestination,
  WarehouseDestinationList,
  WarehouseDestinationCreate,
  WarehouseDestinationUpdate,
  ConnectionTestResult,
  ExportJob,
  ExportJobList,
} from '@/types/api'

export async function listWarehouseDestinations(
  apiKey: string,
  includeInactive = false
): Promise<WarehouseDestinationList> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return apiFetch<WarehouseDestinationList>(`/warehouse/destinations${qs}`, apiKey)
}

export async function createWarehouseDestination(
  apiKey: string,
  body: WarehouseDestinationCreate
): Promise<WarehouseDestination> {
  return apiFetch<WarehouseDestination>('/warehouse/destinations', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateWarehouseDestination(
  apiKey: string,
  id: string,
  body: WarehouseDestinationUpdate
): Promise<WarehouseDestination> {
  return apiFetch<WarehouseDestination>(`/warehouse/destinations/${id}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteWarehouseDestination(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/warehouse/destinations/${id}`, apiKey, { method: 'DELETE' })
}

export async function testWarehouseDestination(
  apiKey: string,
  id: string
): Promise<ConnectionTestResult> {
  return apiFetch<ConnectionTestResult>(`/warehouse/destinations/${id}/test`, apiKey, {
    method: 'POST',
  })
}

export async function listExportJobs(
  apiKey: string,
  destinationId?: string
): Promise<ExportJobList> {
  const qs = destinationId ? `?destination_id=${destinationId}` : ''
  return apiFetch<ExportJobList>(`/warehouse/jobs${qs}`, apiKey)
}

export async function triggerExportJob(
  apiKey: string,
  body: { destination_id: string; export_date?: string; resources?: string[] }
): Promise<ExportJob> {
  return apiFetch<ExportJob>('/warehouse/jobs', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getExportJob(apiKey: string, jobId: string): Promise<ExportJob> {
  return apiFetch<ExportJob>(`/warehouse/jobs/${jobId}`, apiKey)
}

// ── Email Preferences ──────────────────────────────────────────────────────────

export async function getEmailPreferences(apiKey: string): Promise<EmailPreference> {
  return apiFetch<EmailPreference>('/settings/email/preferences', apiKey)
}

export async function updateEmailPreferences(
  apiKey: string,
  data: Partial<EmailPreference>
): Promise<EmailPreference> {
  return apiFetch<EmailPreference>('/settings/email/preferences', apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function testEmailSend(
  apiKey: string
): Promise<{ ok: boolean; error: string | null }> {
  return apiFetch<{ ok: boolean; error: string | null }>('/settings/email/test', apiKey, {
    method: 'POST',
  })
}

export async function getEmailLog(apiKey: string): Promise<EmailLogList> {
  return apiFetch<EmailLogList>('/settings/email/log', apiKey)
}

export async function getBackupHistory(apiKey: string, limit = 20): Promise<BackupRunList> {
  return apiFetch<BackupRunList>(`/settings/backups/history?limit=${limit}`, apiKey)
}

export async function getBackupConfig(apiKey: string): Promise<BackupTargetConfig | null> {
  return apiFetch<BackupTargetConfig | null>('/settings/backups/config', apiKey)
}

export async function updateBackupConfig(
  apiKey: string,
  data: {
    provider: 's3'
    bucket: string
    prefix?: string | null
    region?: string | null
    endpoint_url?: string | null
    access_key_id?: string | null
    secret_access_key?: string | null
    force_path_style?: boolean
    schedule_enabled?: boolean
    cadence?: 'daily' | 'weekly' | 'monthly'
    run_hour_utc?: number
    retention_days?: number
    include_memory_db?: boolean
    include_qdrant?: boolean
    include_kuzu?: boolean
    include_skills?: boolean
    encryption_mode?: 'none' | 'server_side'
  },
): Promise<BackupTargetConfig> {
  return apiFetch<BackupTargetConfig>('/settings/backups/config', apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function getBackupSnapshots(apiKey: string, limit = 20): Promise<BackupSnapshotList> {
  return apiFetch<BackupSnapshotList>(`/settings/backups/snapshots?limit=${limit}`, apiKey)
}

export async function runBackupNow(apiKey: string): Promise<BackupRun> {
  return apiFetch<BackupRun>('/settings/backups/run', apiKey, {
    method: 'POST',
  })
}

export async function testBackupConnection(apiKey: string): Promise<BackupActionResult> {
  return apiFetch<BackupActionResult>('/settings/backups/test', apiKey, {
    method: 'POST',
  })
}

export async function runRestoreDrill(apiKey: string): Promise<BackupRun> {
  return apiFetch<BackupRun>('/settings/backups/restore-drill', apiKey, {
    method: 'POST',
  })
}

export async function getBackupStatus(apiKey: string): Promise<BackupActionResult> {
  return apiFetch<BackupActionResult>('/settings/backups/status', apiKey)
}

export async function testEmailReport(apiKey: string): Promise<{ ok: boolean; recipient?: string; error?: string }> {
  return apiFetch<{ ok: boolean; recipient?: string; error?: string }>('/settings/email/test-report', apiKey, {
    method: 'POST',
  })
}

export async function getOrgEmailFeatureStatus(apiKey: string): Promise<OrgEmailFeatureStatus> {
  return apiFetch<OrgEmailFeatureStatus>('/settings/email/status', apiKey)
}

export async function getOpsFeatureStatus(apiKey: string): Promise<OpsFeatureStatus> {
  return apiFetch<OpsFeatureStatus>('/settings/ops/status', apiKey)
}

export async function getOpsQueueStatus(apiKey: string): Promise<OpsQueueStatus> {
  return apiFetch<OpsQueueStatus>('/settings/ops/queues', apiKey)
}

export async function getOpsStorageStatus(apiKey: string): Promise<OpsStorageStatus> {
  return apiFetch<OpsStorageStatus>('/settings/ops/storage', apiKey)
}

export async function getOpsFeatureFlags(apiKey: string): Promise<OpsFeatureFlagsResponse> {
  return apiFetch<OpsFeatureFlagsResponse>('/settings/ops/feature-flags', apiKey)
}

export async function getOpsPolicyEvaluation(apiKey: string): Promise<OpsPolicyEvaluation> {
  return apiFetch<OpsPolicyEvaluation>('/settings/ops/policy-evaluation', apiKey)
}

// ── Kafka Export ───────────────────────────────────────────────────────────────

import type {
  KafkaExportConfig,
  KafkaExportConfigList,
  KafkaExportDeliveryList,
  KafkaTestResult,
} from '@/types/api'

export async function listKafkaExportConfigs(apiKey: string): Promise<KafkaExportConfigList> {
  return apiFetch<KafkaExportConfigList>('/integrations/kafka/configs', apiKey)
}

export async function createKafkaExportConfig(
  apiKey: string,
  data: {
    label: string
    bootstrap_servers: string
    topic_prefix: string
    security_protocol: string
    sasl_mechanism?: string | null
    sasl_username?: string | null
    sasl_password?: string | null
    ssl_ca_cert?: string | null
    single_topic_mode?: boolean
    single_topic_name?: string | null
    dead_letter_topic?: string | null
    redaction_mode?: 'none' | 'metadata_only'
    max_retries?: number
    retry_backoff_seconds?: number
    event_types: string[]
  }
): Promise<KafkaExportConfig> {
  return apiFetch<KafkaExportConfig>('/integrations/kafka/configs', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateKafkaExportConfig(
  apiKey: string,
  configId: string,
  data: Partial<{
    label: string
    bootstrap_servers: string
    topic_prefix: string
    security_protocol: string
    sasl_mechanism: string | null
    sasl_username: string | null
    sasl_password: string | null
    ssl_ca_cert: string | null
    single_topic_mode: boolean
    single_topic_name: string | null
    dead_letter_topic: string | null
    redaction_mode: 'none' | 'metadata_only'
    max_retries: number
    retry_backoff_seconds: number
    event_types: string[]
    enabled: boolean
  }>
): Promise<KafkaExportConfig> {
  return apiFetch<KafkaExportConfig>(`/integrations/kafka/configs/${configId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteKafkaExportConfig(apiKey: string, configId: string): Promise<void> {
  return apiFetch<void>(`/integrations/kafka/configs/${configId}`, apiKey, { method: 'DELETE' })
}

export async function testKafkaExportConfig(
  apiKey: string,
  configId: string
): Promise<KafkaTestResult> {
  return apiFetch<KafkaTestResult>(`/integrations/kafka/configs/${configId}/test`, apiKey, {
    method: 'POST',
  })
}

export async function triggerPricingSync(
  apiKey: string,
  options?: { force?: boolean; dry_run?: boolean; providers?: string[] }
): Promise<{ inserted: number; updated: number; skipped: number; errors: string[] }> {
  return apiFetch('/pricing/sync', apiKey, {
    method: 'POST',
    body: JSON.stringify(options ?? { force: true }),
  })
}

export async function listKafkaExportDeliveries(
  apiKey: string,
  configId: string,
  limit = 20
): Promise<KafkaExportDeliveryList> {
  return apiFetch<KafkaExportDeliveryList>(
    `/integrations/kafka/configs/${configId}/deliveries?limit=${limit}`,
    apiKey
  )
}

export async function getOtlpInsights(apiKey: string): Promise<OtlpInsights> {
  return apiFetch<OtlpInsights>('/v1/traces/insights', apiKey)
}

export async function retryKafkaExportDelivery(
  apiKey: string,
  configId: string,
  deliveryId: string
): Promise<import('@/types/api').KafkaExportDelivery> {
  return apiFetch<import('@/types/api').KafkaExportDelivery>(
    `/integrations/kafka/configs/${configId}/deliveries/${deliveryId}/retry`,
    apiKey,
    { method: 'POST' }
  )
}

// ── Eval Datasets ──────────────────────────────────────────────────────────────

export async function listEvalDatasets(apiKey: string, limit = 50): Promise<EvalDatasetList> {
  return apiFetch<EvalDatasetList>(`/datasets?limit=${limit}`, apiKey)
}

export async function createEvalDataset(
  apiKey: string,
  data: { name: string; description?: string; source?: string; items?: DatasetItem[] }
): Promise<EvalDataset> {
  return apiFetch<EvalDataset>('/datasets', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function getEvalDataset(apiKey: string, id: string): Promise<EvalDataset> {
  return apiFetch<EvalDataset>(`/datasets/${id}`, apiKey)
}

export async function updateEvalDataset(
  apiKey: string,
  id: string,
  data: { name?: string; description?: string; items?: DatasetItem[] }
): Promise<EvalDataset> {
  return apiFetch<EvalDataset>(`/datasets/${id}`, apiKey, { method: 'PUT', body: JSON.stringify(data) })
}

export async function deleteEvalDataset(apiKey: string, id: string): Promise<void> {
  return apiFetch<void>(`/datasets/${id}`, apiKey, { method: 'DELETE' })
}

// ── Eval Experiments ───────────────────────────────────────────────────────────

export async function listEvalExperiments(
  apiKey: string,
  params: { limit?: number; access_group_id?: string; api_key_id?: string } = {}
): Promise<EvalExperimentList> {
  const qs = new URLSearchParams()
  qs.set('limit', String(params.limit ?? 50))
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  return apiFetch<EvalExperimentList>(`/experiments?${qs.toString()}`, apiKey)
}

export async function createEvalExperiment(
  apiKey: string,
  data: {
    name: string
    description?: string
    dataset_id?: string
    prompt_name?: string
    prompt_version?: number
    evaluator_ids?: string[]
    models?: ExperimentModelConfig[]
  }
): Promise<EvalExperiment> {
  return apiFetch<EvalExperiment>('/experiments', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function getEvalExperiment(apiKey: string, id: string): Promise<EvalExperiment> {
  return apiFetch<EvalExperiment>(`/experiments/${id}`, apiKey)
}

export async function deleteEvalExperiment(apiKey: string, id: string): Promise<void> {
  return apiFetch<void>(`/experiments/${id}`, apiKey, { method: 'DELETE' })
}

export async function runEvalExperiment(apiKey: string, id: string): Promise<EvalExperiment> {
  return apiFetch<EvalExperiment>(`/experiments/${id}/run`, apiKey, { method: 'POST' })
}

// ── GitHub Sync ────────────────────────────────────────────────────────────────

export async function getGithubConfig(apiKey: string): Promise<GithubConfig | null> {
  try {
    return await apiFetch<GithubConfig>('/prompts/github-config', apiKey)
  } catch {
    return null
  }
}

export async function saveGithubConfig(
  apiKey: string,
  data: { repo: string; branch: string; path_prefix: string; token?: string; auto_sync?: boolean },
  exists: boolean
): Promise<GithubConfig> {
  return apiFetch<GithubConfig>('/prompts/github-config', apiKey, {
    method: exists ? 'PUT' : 'POST',
    body: JSON.stringify(data),
  })
}

export async function pushToGithub(apiKey: string): Promise<GithubSyncResult> {
  return apiFetch<GithubSyncResult>('/prompts/sync/push', apiKey, { method: 'POST' })
}

export async function pullFromGithub(apiKey: string): Promise<GithubSyncResult> {
  return apiFetch<GithubSyncResult>('/prompts/sync/pull', apiKey, { method: 'POST' })
}

// ── Phase 3: Scoped summary ────────────────────────────────────────────────

export async function getScopedSummary(
  apiKey: string,
  scope: 'workspace' | 'org' | 'platform' = 'workspace',
  window: TimeWindow & { access_group_id?: string } = {}
): Promise<ScopedSummary> {
  return apiFetch<ScopedSummary>(
    `/analytics/scoped-summary${_analyticsQs({ scope, ...window })}`,
    apiKey
  )
}

export async function getSavingsAnalytics(
  apiKey: string,
  window: TimeWindow = {}
): Promise<SavingsResponse> {
  return apiFetch<SavingsResponse>(
    `/analytics/savings${_analyticsQs(window)}`,
    apiKey
  )
}

export async function getOptimizationOpportunities(
  apiKey: string,
  window: TimeWindow & { access_group_id?: string; api_key_id?: string } = {}
): Promise<OptimizationOpportunitiesResponse> {
  return apiFetch<OptimizationOpportunitiesResponse>(
    `/analytics/optimization-opportunities${_analyticsQs(window)}`,
    apiKey
  )
}

export async function getTrends(
  apiKey: string,
  granularity: 'hourly' | 'daily' | 'weekly' = 'daily',
  window: TimeWindow = {}
): Promise<TrendsResponse> {
  return apiFetch<TrendsResponse>(
    `/analytics/trends${_analyticsQs({ granularity, ...window })}`,
    apiKey
  )
}

export async function getRequestExplorer(
  apiKey: string,
  params: {
    q?: string
    status?: string
    model?: string
    provider?: string
    intent?: string
    end_user_id?: string
    optimization?: string
    page?: number
    page_size?: number
    access_group_id?: string
    tag?: string
    tool_name?: string
    security_event_only?: boolean
  } & TimeWindow = {}
): Promise<RequestExplorerResponse> {
  const qs: Record<string, string | undefined> = {}
  if (params.from) qs.from = params.from
  if (params.to) qs.to = params.to
  if (params.q) qs.q = params.q
  if (params.status) qs.status = params.status
  if (params.model) qs.model = params.model
  if (params.provider) qs.provider = params.provider
  if (params.intent) qs.intent = params.intent
  if (params.end_user_id) qs.end_user_id = params.end_user_id
  if (params.optimization) qs.optimization = params.optimization
  if (params.access_group_id) qs.access_group_id = params.access_group_id
  if (params.tag) qs.tag = params.tag
  if (params.tool_name) qs.tool_name = params.tool_name
  if (params.security_event_only) qs.security_event_only = 'true'
  if (params.page) qs.page = String(params.page)
  if (params.page_size) qs.page_size = String(params.page_size)
  return apiFetch<RequestExplorerResponse>(
    `/analytics/request-explorer${_analyticsQs(qs)}`,
    apiKey
  )
}

export async function getInvestigationGovernancePosture(
  apiKey: string,
  params: {
    from?: string
    to?: string
    access_group_id?: string
    tag?: string
    tool_name?: string
    security_event_only?: boolean
  } = {}
): Promise<import('@/types/api').InvestigationGovernancePosture> {
  const qs: Record<string, string | undefined> = {}
  if (params.from) qs.from = params.from
  if (params.to) qs.to = params.to
  if (params.access_group_id) qs.access_group_id = params.access_group_id
  if (params.tag) qs.tag = params.tag
  if (params.tool_name) qs.tool_name = params.tool_name
  if (params.security_event_only) qs.security_event_only = 'true'
  return apiFetch<import('@/types/api').InvestigationGovernancePosture>(
    `/analytics/investigation-governance-posture${_analyticsQs(qs)}`,
    apiKey
  )
}

export async function getEconomicsFinopsPosture(
  apiKey: string,
): Promise<import('@/types/api').EconomicsFinopsPosture> {
  return apiFetch<import('@/types/api').EconomicsFinopsPosture>(
    '/analytics/economics-finops-posture',
    apiKey
  )
}

export async function getOutcomesFinopsPosture(
  apiKey: string,
): Promise<import('@/types/api').OutcomesFinopsPosture> {
  return apiFetch<import('@/types/api').OutcomesFinopsPosture>(
    '/analytics/outcomes-finops-posture',
    apiKey
  )
}

export async function getMonitoringFinopsPosture(
  apiKey: string,
): Promise<import('@/types/api').MonitoringFinopsPosture> {
  return apiFetch<import('@/types/api').MonitoringFinopsPosture>(
    '/analytics/monitoring-finops-posture',
    apiKey
  )
}

export async function getOverviewGatewayPosture(apiKey: string): Promise<import('@/types/api').OverviewGatewayPosture> {
  return apiFetch<import('@/types/api').OverviewGatewayPosture>(
    '/analytics/overview-gateway-posture',
    apiKey,
  )
}

export async function getOverviewGovernancePosture(apiKey: string): Promise<import('@/types/api').OverviewGovernancePosture> {
  return apiFetch<import('@/types/api').OverviewGovernancePosture>(
    '/analytics/overview-governance-posture',
    apiKey,
  )
}

export async function getOverviewOrgPosture(apiKey: string): Promise<import('@/types/api').OverviewOrgPosture> {
  return apiFetch<import('@/types/api').OverviewOrgPosture>(
    '/analytics/overview-org-posture',
    apiKey,
  )
}

export async function getOverviewScopePosture(apiKey: string): Promise<import('@/types/api').OverviewScopePosture> {
  return apiFetch<import('@/types/api').OverviewScopePosture>(
    '/analytics/overview-scope-posture',
    apiKey,
  )
}

export async function getMonitoringOpsPosture(apiKey: string): Promise<import('@/types/api').MonitoringOpsPosture> {
  return apiFetch<import('@/types/api').MonitoringOpsPosture>(
    '/analytics/monitoring-ops-posture',
    apiKey,
  )
}

export async function getTelemetryOpsPosture(apiKey: string): Promise<import('@/types/api').TelemetryOpsPosture> {
  return apiFetch<import('@/types/api').TelemetryOpsPosture>(
    '/analytics/telemetry-ops-posture',
    apiKey,
  )
}

export async function getUserAnalyticsOrgPosture(apiKey: string): Promise<import('@/types/api').UserAnalyticsOrgPosture> {
  return apiFetch<import('@/types/api').UserAnalyticsOrgPosture>(
    '/analytics/user-analytics-org-posture',
    apiKey,
  )
}

export async function getModelUsageGatewayPosture(apiKey: string): Promise<import('@/types/api').ModelUsageGatewayPosture> {
  return apiFetch<import('@/types/api').ModelUsageGatewayPosture>(
    '/analytics/model-usage-gateway-posture',
    apiKey,
  )
}

export async function getEconomicsGatewayPosture(apiKey: string): Promise<import('@/types/api').EconomicsGatewayPosture> {
  return apiFetch<import('@/types/api').EconomicsGatewayPosture>(
    '/analytics/economics-gateway-posture',
    apiKey,
  )
}

export async function getInvestigationGatewayRuntimePosture(
  apiKey: string,
  params: { access_group_id?: string } = {}
): Promise<import('@/types/api').InvestigationGatewayRuntimePosture> {
  const qs: Record<string, string | undefined> = {}
  if (params.access_group_id) qs.access_group_id = params.access_group_id
  return apiFetch<import('@/types/api').InvestigationGatewayRuntimePosture>(
    `/analytics/investigation-gateway-runtime-posture${_analyticsQs(qs)}`,
    apiKey
  )
}

export async function getInvestigationOrgIdentityPosture(
  apiKey: string,
): Promise<import('@/types/api').InvestigationOrgIdentityPosture> {
  return apiFetch<import('@/types/api').InvestigationOrgIdentityPosture>(
    '/analytics/investigation-org-identity-posture',
    apiKey
  )
}

export async function getInvestigationFinopsBudgetPosture(
  apiKey: string,
  params: {
    access_group_id?: string
  } = {}
): Promise<import('@/types/api').InvestigationFinopsBudgetPosture> {
  const qs: Record<string, string | undefined> = {}
  if (params.access_group_id) qs.access_group_id = params.access_group_id
  return apiFetch<import('@/types/api').InvestigationFinopsBudgetPosture>(
    `/analytics/investigation-finops-budget-posture${_analyticsQs(qs)}`,
    apiKey
  )
}

export async function getOverviewFinopsBudgetPosture(
  apiKey: string,
): Promise<import('@/types/api').OverviewFinopsBudgetPosture> {
  return apiFetch<import('@/types/api').OverviewFinopsBudgetPosture>(
    '/analytics/overview-finops-budget-posture',
    apiKey
  )
}

export async function getModelBudgetUtilization(
  apiKey: string,
): Promise<import('@/types/api').ModelBudgetUtilization> {
  return apiFetch<import('@/types/api').ModelBudgetUtilization>(
    '/analytics/model-budget-utilization',
    apiKey
  )
}

export async function getEngineeringMetrics(
  apiKey: string,
  window: TimeWindow = {}
): Promise<EngineeringMetrics> {
  return apiFetch<EngineeringMetrics>(
    `/analytics/engineering${_analyticsQs(window)}`,
    apiKey
  )
}

export async function simulateOptimization(
  apiKey: string,
  request: SimulationRequest
): Promise<SimulationResult> {
  return apiFetch<SimulationResult>(
    '/analytics/simulate-optimization',
    apiKey,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  )
}

// ── Phase 13: Audit Export ───────────────────────────────────────────────────

export async function exportAuditEvents(
  apiKey: string,
  format: 'csv' | 'json' = 'csv',
  action?: string,
  targetType?: string
): Promise<string> {
  const qs = new URLSearchParams({ format })
  if (action) qs.set('action', action)
  if (targetType) qs.set('target_type', targetType)
  const API = typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
  const res = await fetch(`${API}/audit/events/export?${qs}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}

// ── Phase 13: Policy Dry Run ─────────────────────────────────────────────────

export async function policyDryRun(
  apiKey: string,
  body: {
    end_user_id?: string
    feature_tag?: string
    tool_name?: string
    model_alias?: string
    dry_run: true
  }
): Promise<PolicyCheckResponse> {
  return apiFetch<PolicyCheckResponse>('/policies/check', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getPolicyDryRunReport(
  apiKey: string,
  params?: { from?: string; to?: string; limit?: number }
): Promise<PolicyDryRunReport> {
  const q = new URLSearchParams()
  if (params?.from) q.set('from', params.from)
  if (params?.to) q.set('to', params.to)
  if (params?.limit) q.set('limit', String(params.limit))
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<PolicyDryRunReport>(`/policies/dry-run-report${qs}`, apiKey)
}

export async function promotePolicy(
  apiKey: string,
  body: { policy_type: string; enforce: boolean }
): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>('/policies/promote', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// ── Phase 13: Runbooks ───────────────────────────────────────────────────────

export async function generateRunbook(
  apiKey: string,
  runId: string
): Promise<RunbookResponse> {
  return apiFetch<RunbookResponse>(`/runs/${runId}/runbook`, apiKey, {
    method: 'POST',
  })
}

export async function listRunbooks(
  apiKey: string,
  params?: { severity?: string; limit?: number; offset?: number }
): Promise<RunbookList> {
  const q = new URLSearchParams()
  if (params?.severity) q.set('severity', params.severity)
  if (params?.limit) q.set('limit', String(params.limit))
  if (params?.offset) q.set('offset', String(params.offset))
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<RunbookList>(`/runs/runbooks/list${qs}`, apiKey)
}

export async function exportRunbook(
  apiKey: string,
  runbookId: string,
  format: 'markdown' | 'json' = 'markdown'
): Promise<string> {
  const API = typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
  const res = await fetch(`${API}/runs/runbooks/${runbookId}/export?format=${format}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}

// ── Phase 13: Model Scorecards ───────────────────────────────────────────────

export async function getModelScorecards(
  apiKey: string,
  window: TimeWindow & { access_group_id?: string; api_key_id?: string } = {}
): Promise<ModelScorecardList> {
  return apiFetch<ModelScorecardList>(
    `/analytics/model-scorecards${_analyticsQs(window)}`,
    apiKey
  )
}

export async function getModelScoreTrends(
  apiKey: string,
  model: string,
  window: TimeWindow = {}
): Promise<ModelScoreTrendList> {
  const q = new URLSearchParams({ model })
  if (window.from) q.set('from', window.from)
  if (window.to) q.set('to', window.to)
  return apiFetch<ModelScoreTrendList>(`/analytics/model-score-trends?${q}`, apiKey)
}

// ── Phase 13: Onboarding & Demo ──────────────────────────────────────────────

export async function getOnboardingStatus(apiKey: string): Promise<OnboardingStatus> {
  return apiFetch<OnboardingStatus>('/settings/onboarding-status', apiKey)
}

export async function triggerDemoSeed(
  apiKey: string,
  profile: 'full' | 'quick' = 'full'
): Promise<import('@/types/api').DemoModeTriggerResponse> {
  return apiFetch<import('@/types/api').DemoModeTriggerResponse>(`/settings/demo-seed?profile=${profile}`, apiKey, {
    method: 'POST',
  })
}

export async function getDemoModeStatus(
  apiKey: string
): Promise<import('@/types/api').DemoModeStatus> {
  return apiFetch<import('@/types/api').DemoModeStatus>('/settings/demo-status', apiKey)
}

export async function triggerDemoReset(
  apiKey: string
): Promise<import('@/types/api').DemoModeTriggerResponse> {
  return apiFetch<import('@/types/api').DemoModeTriggerResponse>('/settings/demo-reset', apiKey, {
    method: 'POST',
  })
}

// ── Phase 13: Chargeback Rules ───────────────────────────────────────────────

export async function deleteChargebackRule(
  apiKey: string,
  ruleId: string
): Promise<void> {
  await apiFetch<void>(`/billing/chargeback-rules/${ruleId}`, apiKey, { method: 'DELETE' })
}

export async function getChargebackReport(
  apiKey: string,
  params?: { period?: string; dimension?: string; format?: 'json' | 'csv'; access_group_id?: string; api_key_id?: string }
): Promise<ChargebackReportList> {
  const q = new URLSearchParams()
  if (params?.period) q.set('period', params.period)
  if (params?.dimension) q.set('dimension', params.dimension)
  if (params?.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params?.api_key_id) q.set('api_key_id', params.api_key_id)
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<ChargebackReportList>(`/billing/chargeback-report${qs}`, apiKey)
}

export async function exportChargebackReport(
  apiKey: string,
  params?: { period?: string; dimension?: string; format?: 'csv' | 'json'; access_group_id?: string; api_key_id?: string }
): Promise<string> {
  const q = new URLSearchParams({ format: params?.format ?? 'csv' })
  if (params?.period) q.set('period', params.period)
  if (params?.dimension) q.set('dimension', params.dimension)
  if (params?.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params?.api_key_id) q.set('api_key_id', params.api_key_id)
  const API = typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
  const res = await fetch(`${API}/billing/chargeback-report/export?${q}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}

// ── Phase 13: Route Recommendations ─────────────────────────────────────────

export async function createRouteRecommendation(
  apiKey: string,
  body: { experiment_id: string; config_index: number; reason: string }
): Promise<{ status: string; recommendation_id: string }> {
  return apiFetch<{ status: string; recommendation_id: string }>('/gateway/route-recommendations', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// ── Phase 13: Governance Audit Pack ─────────────────────────────────────────

export async function getGovernanceAuditPack(
  apiKey: string,
  params?: { from?: string; to?: string; org_id?: string; workspace_id?: string; user_id?: string; access_group_id?: string; api_key_id?: string }
): Promise<import('@/types/api').GovernanceAuditPack> {
  const q = new URLSearchParams()
  if (params?.from) q.set('from', params.from)
  if (params?.to) q.set('to', params.to)
  if (params?.org_id) q.set('org_id', params.org_id)
  if (params?.workspace_id) q.set('workspace_id', params.workspace_id)
  if (params?.user_id) q.set('user_id', params.user_id)
  if (params?.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params?.api_key_id) q.set('api_key_id', params.api_key_id)
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<import('@/types/api').GovernanceAuditPack>(`/governance/audit-pack${qs}`, apiKey)
}

export async function exportGovernanceAuditPack(
  apiKey: string,
  params?: { from?: string; to?: string; format?: 'json' | 'csv' }
): Promise<string> {
  const q = new URLSearchParams({ format: params?.format ?? 'json' })
  if (params?.from) q.set('from', params.from)
  if (params?.to) q.set('to', params.to)
  const API = typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
  const res = await fetch(`${API}/governance/audit-pack/export?${q}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}

// -- Phase 14: Guardrails, Content Safety & Policy Engine --

export async function listGuardrailRules(
  apiKey: string,
  params?: { rule_type?: string; status?: string; mode?: string; limit?: number; offset?: number }
): Promise<import('@/types/api').GuardrailRuleList> {
  const q = new URLSearchParams()
  if (params?.rule_type) q.set('rule_type', params.rule_type)
  if (params?.status) q.set('status', params.status)
  if (params?.mode) q.set('mode', params.mode)
  if (params?.limit) q.set('limit', String(params.limit))
  if (params?.offset) q.set('offset', String(params.offset))
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<import('@/types/api').GuardrailRuleList>(`/guardrails${qs}`, apiKey)
}

export async function createGuardrailRule(
  apiKey: string,
  body: import('@/types/api').GuardrailRuleCreate
): Promise<import('@/types/api').GuardrailRuleResponse> {
  return apiFetch<import('@/types/api').GuardrailRuleResponse>('/guardrails', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function getGuardrailRule(
  apiKey: string,
  id: string
): Promise<import('@/types/api').GuardrailRuleResponse> {
  return apiFetch<import('@/types/api').GuardrailRuleResponse>(`/guardrails/${id}`, apiKey)
}

export async function updateGuardrailRule(
  apiKey: string,
  id: string,
  body: import('@/types/api').GuardrailRuleUpdate
): Promise<import('@/types/api').GuardrailRuleResponse> {
  return apiFetch<import('@/types/api').GuardrailRuleResponse>(`/guardrails/${id}`, apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deleteGuardrailRule(apiKey: string, id: string): Promise<void> {
  return apiFetch<void>(`/guardrails/${id}`, apiKey, { method: 'DELETE' })
}

export async function testGuardrailRule(
  apiKey: string,
  id: string,
  body: import('@/types/api').GuardrailTestInput
): Promise<import('@/types/api').GuardrailTestResponse> {
  return apiFetch<import('@/types/api').GuardrailTestResponse>(`/guardrails/${id}/test`, apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function testAllGuardrails(
  apiKey: string,
  body: import('@/types/api').GuardrailTestInput
): Promise<import('@/types/api').GuardrailTestResponse> {
  return apiFetch<import('@/types/api').GuardrailTestResponse>('/guardrails/test', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function listGuardrailTemplates(
  apiKey: string
): Promise<import('@/types/api').GuardrailTemplate[]> {
  return apiFetch<import('@/types/api').GuardrailTemplate[]>('/guardrails/templates', apiKey)
}

export async function listContentFilters(
  apiKey: string
): Promise<import('@/types/api').ContentFilterListResponse> {
  return apiFetch<import('@/types/api').ContentFilterListResponse>('/guardrails/filters', apiKey)
}

export async function activateContentFilters(
  apiKey: string,
  body: { filters: import('@/types/api').ContentFilterConfig[] }
): Promise<import('@/types/api').ContentFilterListResponse> {
  return apiFetch<import('@/types/api').ContentFilterListResponse>('/guardrails/filters', apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function getGuardrailStats(
  apiKey: string,
  hours?: number
): Promise<import('@/types/api').GuardrailStats> {
  const qs = hours ? `?hours=${hours}` : ''
  return apiFetch<import('@/types/api').GuardrailStats>(`/guardrails/stats${qs}`, apiKey)
}

export async function listGuardrailEvents(
  apiKey: string,
  params?: {
    decision?: string
    guardrail_name?: string
    mode?: string
    violations_only?: boolean
    false_positive?: boolean
    limit?: number
    offset?: number
  }
): Promise<import('@/types/api').GuardrailEventList> {
  const q = new URLSearchParams()
  if (params?.decision) q.set('decision', params.decision)
  if (params?.guardrail_name) q.set('guardrail_name', params.guardrail_name)
  if (params?.mode) q.set('mode', params.mode)
  if (params?.violations_only !== undefined) q.set('violations_only', String(params.violations_only))
  if (params?.false_positive !== undefined) q.set('false_positive', String(params.false_positive))
  if (params?.limit) q.set('limit', String(params.limit))
  if (params?.offset) q.set('offset', String(params.offset))
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<import('@/types/api').GuardrailEventList>(`/guardrails/events${qs}`, apiKey)
}

export async function listPartnerGuardrails(
  apiKey: string,
  params?: { provider?: string }
): Promise<import('@/types/api').PartnerGuardrailList> {
  const q = new URLSearchParams()
  if (params?.provider) q.set('provider', params.provider)
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<import('@/types/api').PartnerGuardrailList>(`/guardrails/partners${qs}`, apiKey)
}

export async function createPartnerGuardrail(
  apiKey: string,
  body: Record<string, unknown>
): Promise<import('@/types/api').PartnerGuardrailResponse> {
  return apiFetch<import('@/types/api').PartnerGuardrailResponse>('/guardrails/partners', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function updatePartnerGuardrail(
  apiKey: string,
  id: string,
  body: Record<string, unknown>
): Promise<import('@/types/api').PartnerGuardrailResponse> {
  return apiFetch<import('@/types/api').PartnerGuardrailResponse>(`/guardrails/partners/${id}`, apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deletePartnerGuardrail(apiKey: string, id: string): Promise<void> {
  return apiFetch<void>(`/guardrails/partners/${id}`, apiKey, { method: 'DELETE' })
}

export async function healthCheckPartner(
  apiKey: string,
  id: string
): Promise<import('@/types/api').PartnerGuardrailResponse> {
  return apiFetch<import('@/types/api').PartnerGuardrailResponse>(
    `/guardrails/partners/${id}/health`,
    apiKey,
    { method: 'POST' }
  )
}

export async function listGuardrailTestCases(
  apiKey: string,
  params?: { guardrail_rule_id?: string }
): Promise<import('@/types/api').GuardrailTestCaseList> {
  const q = new URLSearchParams()
  if (params?.guardrail_rule_id) q.set('guardrail_rule_id', params.guardrail_rule_id)
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<import('@/types/api').GuardrailTestCaseList>(`/guardrails/test-cases${qs}`, apiKey)
}

export async function createGuardrailTestCase(
  apiKey: string,
  body: Record<string, unknown>
): Promise<import('@/types/api').GuardrailTestCaseResponse> {
  return apiFetch<import('@/types/api').GuardrailTestCaseResponse>('/guardrails/test-cases', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deleteGuardrailTestCase(apiKey: string, id: string): Promise<void> {
  return apiFetch<void>(`/guardrails/test-cases/${id}`, apiKey, { method: 'DELETE' })
}

export async function runGuardrailRegression(
  apiKey: string,
  guardrailId: string
): Promise<import('@/types/api').GuardrailRegressionReport> {
  return apiFetch<import('@/types/api').GuardrailRegressionReport>(
    `/guardrails/${guardrailId}/regression`,
    apiKey,
    { method: 'POST' }
  )
}

export async function submitGuardrailFeedback(
  apiKey: string,
  eventId: string,
  body: import('@/types/api').GuardrailFeedbackInput
): Promise<import('@/types/api').GuardrailEventResponse> {
  return apiFetch<import('@/types/api').GuardrailEventResponse>(
    `/guardrails/events/${eventId}/feedback`,
    apiKey,
    { method: 'POST', body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } }
  )
}

export async function listGuardrailAlerts(
  apiKey: string,
  params?: { alert_type?: string; status?: string; limit?: number; offset?: number }
): Promise<import('@/types/api').GuardrailAlertList> {
  const sp = new URLSearchParams()
  if (params?.alert_type) sp.set('alert_type', params.alert_type)
  if (params?.status) sp.set('status', params.status)
  if (params?.limit) sp.set('limit', String(params.limit))
  if (params?.offset) sp.set('offset', String(params.offset))
  const qs = sp.toString()
  return apiFetch<import('@/types/api').GuardrailAlertList>(
    `/guardrails/alerts${qs ? `?${qs}` : ''}`,
    apiKey
  )
}

export async function evaluateGuardrailAlerts(
  apiKey: string,
  windowHours?: number,
  baselineHours?: number
): Promise<Record<string, unknown>[]> {
  const sp = new URLSearchParams()
  if (windowHours) sp.set('window_hours', String(windowHours))
  if (baselineHours) sp.set('baseline_hours', String(baselineHours))
  const qs = sp.toString()
  return apiFetch<Record<string, unknown>[]>(
    `/guardrails/alerts/evaluate${qs ? `?${qs}` : ''}`,
    apiKey,
    { method: 'POST' }
  )
}

export async function acknowledgeGuardrailAlert(
  apiKey: string,
  alertId: string
): Promise<import('@/types/api').GuardrailAlertResponse> {
  return apiFetch<import('@/types/api').GuardrailAlertResponse>(
    `/guardrails/alerts/${alertId}/acknowledge`,
    apiKey,
    { method: 'POST' }
  )
}

// ── Phase 15: ML Intelligence Layer ────────────────────────────────────

export async function listAnomalies(
  apiKey: string,
  params: { anomaly_type?: string; severity?: string; suppressed?: boolean } & TimeWindow = {}
): Promise<import('@/types/api').MLAnomalyList> {
  const qs = _analyticsQs(params)
  const extra = [
    params.anomaly_type ? `anomaly_type=${params.anomaly_type}` : '',
    params.severity ? `severity=${params.severity}` : '',
    params.suppressed !== undefined ? `suppressed=${params.suppressed}` : '',
  ].filter(Boolean).join('&')
  const sep = qs.includes('?') ? '&' : '?'
  return apiFetch<import('@/types/api').MLAnomalyList>(`/intelligence/anomalies${qs}${extra ? sep + extra : ''}`, apiKey)
}

export async function getAnomalySummary(
  apiKey: string,
  hours: number = 24
): Promise<import('@/types/api').MLAnomalySummary> {
  return apiFetch<import('@/types/api').MLAnomalySummary>(`/intelligence/anomalies/summary?hours=${hours}`, apiKey)
}

export async function acknowledgeAnomaly(
  apiKey: string,
  anomalyId: string
): Promise<import('@/types/api').MLAnomalyResponse> {
  return apiFetch<import('@/types/api').MLAnomalyResponse>(
    `/intelligence/anomalies/${anomalyId}/acknowledge`,
    apiKey,
    { method: 'POST' }
  )
}

export async function trainIsolationForest(
  apiKey: string,
  days: number = 60
): Promise<{ status: string; sample_count?: number; features?: number; reason?: string }> {
  return apiFetch(`/intelligence/anomalies/train-isolation-forest?days=${days}`, apiKey, { method: 'POST' })
}

export async function listCorrelatedAnomalyGroups(
  apiKey: string,
  hours: number = 168
): Promise<import('@/types/api').CorrelatedGroupList> {
  return apiFetch<import('@/types/api').CorrelatedGroupList>(`/intelligence/anomalies/correlated?hours=${hours}`, apiKey)
}

export async function getCostForecast(
  apiKey: string
): Promise<import('@/types/api').ForecastResponse | null> {
  return apiFetch<import('@/types/api').ForecastResponse | null>(`/intelligence/forecasts/cost`, apiKey)
}

export async function getTokenForecast(
  apiKey: string
): Promise<import('@/types/api').ForecastResponse | null> {
  return apiFetch<import('@/types/api').ForecastResponse | null>(`/intelligence/forecasts/tokens`, apiKey)
}

export async function generateForecast(
  apiKey: string,
  body: { forecast_type?: string; horizon_days?: number; dimension_key?: string | null }
): Promise<{ status: string; forecast_id?: string }> {
  return apiFetch<{ status: string; forecast_id?: string }>(
    `/intelligence/forecasts/generate`,
    apiKey,
    { method: 'POST', body: JSON.stringify(body) }
  )
}

export async function getTopK(
  apiKey: string,
  params: { dimension: string; metric?: string; k?: number } & TimeWindow
): Promise<import('@/types/api').TopKResponse> {
  const qs = _analyticsQs(params)
  const extra = [
    `dimension=${params.dimension}`,
    params.metric ? `metric=${params.metric}` : '',
    params.k ? `k=${params.k}` : '',
  ].filter(Boolean).join('&')
  const sep = qs.includes('?') ? '&' : '?'
  return apiFetch<import('@/types/api').TopKResponse>(`/intelligence/top-k${qs}${extra ? sep + extra : ''}`, apiKey)
}

export async function listPatterns(
  apiKey: string,
  dimension?: string
): Promise<import('@/types/api').PatternList> {
  const qs = dimension ? `?dimension=${dimension}` : ''
  return apiFetch<import('@/types/api').PatternList>(`/intelligence/patterns${qs}`, apiKey)
}

export async function getComplexityScores(
  apiKey: string,
  hours: number = 24
): Promise<import('@/types/api').ComplexityScoreList> {
  return apiFetch<import('@/types/api').ComplexityScoreList>(`/intelligence/complexity/scores?hours=${hours}`, apiKey)
}

export async function getFeatureImportances(
  apiKey: string
): Promise<import('@/types/api').FeatureImportanceList> {
  return apiFetch<import('@/types/api').FeatureImportanceList>(`/intelligence/complexity/importances`, apiKey)
}

export async function getCostPerOutcome(
  apiKey: string,
  params: TimeWindow = {}
): Promise<import('@/types/api').CostOutcomeResponse> {
  return apiFetch<import('@/types/api').CostOutcomeResponse>(`/intelligence/cost-per-outcome${_analyticsQs(params)}`, apiKey)
}

export async function getAdaptiveSuggestions(
  apiKey: string
): Promise<import('@/types/api').AdaptiveThresholdList> {
  return apiFetch<import('@/types/api').AdaptiveThresholdList>(`/intelligence/alerts/adaptive-suggestions`, apiKey)
}

export async function enableAdaptiveAlert(
  apiKey: string,
  ruleId: string
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(
    `/intelligence/alerts/${ruleId}/enable-adaptive`,
    apiKey,
    { method: 'POST' }
  )
}

export async function getMLDashboard(
  apiKey: string
): Promise<import('@/types/api').MLDashboard> {
  return apiFetch<import('@/types/api').MLDashboard>(`/intelligence/dashboard`, apiKey)
}

export async function listMLModels(
  apiKey: string
): Promise<import('@/types/api').ModelHealth[]> {
  return apiFetch<import('@/types/api').ModelHealth[]>(`/intelligence/models`, apiKey)
}

// ── Advanced Budget Engine ──────────────────────────────────────────────────

export async function listBudgetTiers(
  apiKey: string
): Promise<import('@/types/api').BudgetTierList> {
  return apiFetch<import('@/types/api').BudgetTierList>(`/budget-tiers`, apiKey)
}

export async function createBudgetTier(
  apiKey: string,
  body: { name: string; max_spend_usd?: number; period_type?: string; rpm_limit?: number; tpm_limit?: number; allowed_models?: string[]; is_default?: boolean }
): Promise<import('@/types/api').BudgetTier> {
  return apiFetch<import('@/types/api').BudgetTier>(`/budget-tiers`, apiKey, { method: 'POST', body: JSON.stringify(body) })
}

export async function getBudgetTier(
  apiKey: string,
  tierId: string
): Promise<import('@/types/api').BudgetTier> {
  return apiFetch<import('@/types/api').BudgetTier>(`/budget-tiers/${tierId}`, apiKey)
}

export async function updateBudgetTier(
  apiKey: string,
  tierId: string,
  body: { name?: string; max_spend_usd?: number | null; period_type?: string; rpm_limit?: number | null; tpm_limit?: number | null; allowed_models?: string[] | null; is_default?: boolean }
): Promise<import('@/types/api').BudgetTier> {
  return apiFetch<import('@/types/api').BudgetTier>(`/budget-tiers/${tierId}`, apiKey, { method: 'PUT', body: JSON.stringify(body) })
}

export async function deleteBudgetTier(
  apiKey: string,
  tierId: string
): Promise<void> {
  await apiFetch<void>(`/budget-tiers/${tierId}`, apiKey, { method: 'DELETE' })
}

export async function assignTierToKey(
  apiKey: string,
  keyId: string,
  tierId: string | null
): Promise<{ key_id: string; budget_tier_id: string | null }> {
  const qs = tierId ? `?tier_id=${tierId}` : ''
  return apiFetch(`/budget-tiers/assign/${keyId}${qs}`, apiKey, { method: 'PUT' })
}

export async function listModelBudgets(
  apiKey: string,
  keyId: string
): Promise<import('@/types/api').ModelBudgetList> {
  return apiFetch<import('@/types/api').ModelBudgetList>(`/api-keys/${keyId}/model-budgets`, apiKey)
}

export async function createModelBudget(
  apiKey: string,
  keyId: string,
  body: { model_pattern: string; max_spend_usd?: number; period_type?: string; rpm_limit?: number; tpm_limit?: number; action?: string }
): Promise<import('@/types/api').ModelBudget> {
  return apiFetch<import('@/types/api').ModelBudget>(`/api-keys/${keyId}/model-budgets`, apiKey, { method: 'POST', body: JSON.stringify(body) })
}

export async function updateModelBudget(
  apiKey: string,
  keyId: string,
  budgetId: string,
  body: { model_pattern?: string; max_spend_usd?: number | null; period_type?: string; rpm_limit?: number | null; tpm_limit?: number | null; action?: string; is_active?: boolean }
): Promise<import('@/types/api').ModelBudget> {
  return apiFetch<import('@/types/api').ModelBudget>(`/api-keys/${keyId}/model-budgets/${budgetId}`, apiKey, { method: 'PUT', body: JSON.stringify(body) })
}

export async function deleteModelBudget(
  apiKey: string,
  keyId: string,
  budgetId: string
): Promise<void> {
  await apiFetch<void>(`/api-keys/${keyId}/model-budgets/${budgetId}`, apiKey, { method: 'DELETE' })
}

export async function createBudgetOverride(
  apiKey: string,
  budgetId: string,
  body: {
    override_limit_usd: number
    starts_at: string
    expires_at: string
    reason?: string
    require_approval?: boolean
  }
): Promise<import('@/types/api').BudgetOverride> {
  return apiFetch<import('@/types/api').BudgetOverride>(`/budgets/${budgetId}/override`, apiKey, { method: 'POST', body: JSON.stringify(body) })
}

export async function listBudgetOverrides(
  apiKey: string,
  budgetId: string
): Promise<import('@/types/api').BudgetOverrideList> {
  return apiFetch<import('@/types/api').BudgetOverrideList>(`/budgets/${budgetId}/overrides`, apiKey)
}

export async function revokeBudgetOverride(
  apiKey: string,
  budgetId: string,
  overrideId: string
): Promise<import('@/types/api').BudgetOverride> {
  return apiFetch<import('@/types/api').BudgetOverride>(`/budgets/${budgetId}/override/${overrideId}/revoke`, apiKey, { method: 'POST' })
}

export async function getBillingSummary(
  apiKey: string,
  months?: number
): Promise<import('@/types/api').BillingSummaryResponse> {
  const qs = months ? `?months=${months}` : ''
  return apiFetch<import('@/types/api').BillingSummaryResponse>(`/budgets/billing-summary${qs}`, apiKey)
}

export async function exportBilling(
  apiKey: string,
  format: 'csv' | 'json' = 'json',
  months?: number
): Promise<Blob> {
  const params = new URLSearchParams({ format })
  if (months) params.set('months', String(months))
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8201'}/budgets/billing-export?${params}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
  })
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)
  return res.blob()
}

// ── Agent Registry ─────────────────────────────────────────────────────────

export async function getAgents(
  apiKey: string,
  params: { status?: string; agent_type?: string; access_group_id?: string; api_key_id?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').AgentListResponse> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.agent_type) qs.set('agent_type', params.agent_type)
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').AgentListResponse>(`/agents${query}`, apiKey)
}

export async function getAgent(
  apiKey: string,
  agentId: string
): Promise<import('@/types/api').AgentResponse> {
  return apiFetch<import('@/types/api').AgentResponse>(`/agents/${agentId}`, apiKey)
}

export async function getAgentStats(
  apiKey: string,
  agentId: string
): Promise<import('@/types/api').AgentStats> {
  return apiFetch<import('@/types/api').AgentStats>(`/agents/${agentId}/stats`, apiKey)
}

export async function getAgentRuns(
  apiKey: string,
  agentId: string,
  params: { status?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').WorkflowRunSummaryListResponse> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').WorkflowRunSummaryListResponse>(`/agents/${agentId}/runs${query}`, apiKey)
}

export async function createAgent(
  apiKey: string,
  data: {
    name: string
    description?: string
    agent_type?: string
    owner?: string
    default_model?: string
    default_tools?: string[]
    budget_envelope?: number
    policy_profile?: string
    config?: Record<string, unknown>
  }
): Promise<import('@/types/api').AgentResponse> {
  return apiFetch<import('@/types/api').AgentResponse>('/agents', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateAgent(
  apiKey: string,
  agentId: string,
  data: Record<string, unknown>
): Promise<import('@/types/api').AgentResponse> {
  return apiFetch<import('@/types/api').AgentResponse>(`/agents/${agentId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function retireAgent(
  apiKey: string,
  agentId: string
): Promise<void> {
  return apiFetch<void>(`/agents/${agentId}`, apiKey, { method: 'DELETE' })
}

// ── Workflow Definitions & Runs ────────────────────────────────────────────

export async function getWorkflows(
  apiKey: string,
  params: { status?: string; access_group_id?: string; api_key_id?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').WorkflowDefinitionListResponse> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').WorkflowDefinitionListResponse>(`/workflows${query}`, apiKey)
}

export async function getWorkflow(
  apiKey: string,
  workflowId: string
): Promise<import('@/types/api').WorkflowDefinitionResponse> {
  return apiFetch<import('@/types/api').WorkflowDefinitionResponse>(`/workflows/${workflowId}`, apiKey)
}

export async function getWorkflowRuns(
  apiKey: string,
  workflowId: string,
  params: { status?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').WorkflowRunListResponse> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').WorkflowRunListResponse>(`/workflows/${workflowId}/runs${query}`, apiKey)
}

export async function getWorkflowRun(
  apiKey: string,
  workflowId: string,
  runId: string
): Promise<import('@/types/api').WorkflowRunResponse> {
  return apiFetch<import('@/types/api').WorkflowRunResponse>(`/workflows/${workflowId}/runs/${runId}`, apiKey)
}

export async function getWorkflowCost(
  apiKey: string,
  workflowId: string
): Promise<import('@/types/api').WorkflowCostAttribution> {
  return apiFetch<import('@/types/api').WorkflowCostAttribution>(`/workflows/${workflowId}/cost`, apiKey)
}

// ── Agent Memory ──────────────────────────────────────────────────────────

export async function getAgentMemories(
  apiKey: string,
  agentId: string,
  params: { memory_type?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').AgentMemoryListResponse> {
  const qs = new URLSearchParams()
  if (params.memory_type) qs.set('memory_type', params.memory_type)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').AgentMemoryListResponse>(`/agents/${agentId}/memory${query}`, apiKey)
}

export async function registerMcpServer(
  apiKey: string,
  data: { name: string; transport: string; url?: string; command?: string; args?: string[]; env?: Record<string, string>; auth_type?: string; auth_config?: Record<string, unknown>; description?: string }
): Promise<import('@/types/api').McpServerResponse> {
  return apiFetch<import('@/types/api').McpServerResponse>('/mcp-registry', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function listMcpServers(apiKey: string, includeInactive = false): Promise<import('@/types/api').McpServerList> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return apiFetch<import('@/types/api').McpServerList>(`/mcp-registry${qs}`, apiKey)
}

export async function getMcpServer(apiKey: string, id: string): Promise<import('@/types/api').McpServerResponse> {
  return apiFetch<import('@/types/api').McpServerResponse>(`/mcp-registry/${id}`, apiKey)
}

export async function updateMcpServer(
  apiKey: string,
  id: string,
  data: {
    name?: string
    description?: string
    transport?: string
    url?: string
    command?: string
    args?: string[]
    env?: Record<string, string>
    auth_type?: string
    auth_config?: Record<string, unknown>
    is_active?: boolean
  }
): Promise<import('@/types/api').McpServerResponse> {
  return apiFetch<import('@/types/api').McpServerResponse>(`/mcp-registry/${id}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function seedDefaultMcpServers(apiKey: string): Promise<{ status: string; servers_added: number; total: number }> {
  return apiFetch<{ status: string; servers_added: number; total: number }>('/mcp-registry/seed-defaults', apiKey, { method: 'POST' })
}

export async function getAgentMemoryStats(
  apiKey: string,
  agentId: string
): Promise<import('@/types/api').AgentMemoryStats> {
  return apiFetch<import('@/types/api').AgentMemoryStats>(`/agents/${agentId}/memory/stats`, apiKey)
}

export async function getAgentMemoryAudit(
  apiKey: string,
  agentId: string,
  params: { limit?: number; offset?: number } = {}
): Promise<import('@/types/api').AgentMemoryAuditListResponse> {
  const qs = new URLSearchParams()
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').AgentMemoryAuditListResponse>(`/agents/${agentId}/memory/audit${query}`, apiKey)
}

export async function searchAgentMemory(
  apiKey: string,
  agentId: string,
  data: { query: string; memory_type?: string; limit?: number }
): Promise<import('@/types/api').AgentMemoryListResponse> {
  return apiFetch<import('@/types/api').AgentMemoryListResponse>(`/agents/${agentId}/memory/search`, apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteAgentMemory(
  apiKey: string,
  agentId: string,
  key: string
): Promise<void> {
  return apiFetch<void>(`/agents/${agentId}/memory/${encodeURIComponent(key)}`, apiKey, { method: 'DELETE' })
}

// ── Vector Store Management ───────────────────────────────────────────────

export async function getVectorCollections(
  apiKey: string,
  params: { status?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').VectorCollectionListResponse> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').VectorCollectionListResponse>(`/vector-stores${query}`, apiKey)
}

export async function getVectorCollection(
  apiKey: string,
  collectionId: string
): Promise<import('@/types/api').VectorCollectionResponse> {
  return apiFetch<import('@/types/api').VectorCollectionResponse>(`/vector-stores/${collectionId}`, apiKey)
}

export async function getVectorCollectionStats(
  apiKey: string,
  collectionId: string
): Promise<import('@/types/api').VectorCollectionStats> {
  return apiFetch<import('@/types/api').VectorCollectionStats>(`/vector-stores/${collectionId}/stats`, apiKey)
}

export async function getVectorQueries(
  apiKey: string,
  collectionId: string,
  params: { limit?: number; offset?: number } = {}
): Promise<import('@/types/api').VectorQueryListResponse> {
  const qs = new URLSearchParams()
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').VectorQueryListResponse>(`/vector-stores/${collectionId}/queries${query}`, apiKey)
}

export async function testVectorSearch(
  apiKey: string,
  collectionId: string,
  data: { query: string; top_k?: number; threshold?: number }
): Promise<import('@/types/api').VectorSearchTestResponse> {
  return apiFetch<import('@/types/api').VectorSearchTestResponse>(`/vector-stores/${collectionId}/search-test`, apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ── API Playground ────────────────────────────────────────────────────────

export async function getPlaygroundSessions(
  apiKey: string,
  params: { favorites_only?: boolean; access_group_id?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').PlaygroundSessionListResponse> {
  const qs = new URLSearchParams()
  if (params.favorites_only) qs.set('favorites_only', 'true')
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').PlaygroundSessionListResponse>(`/playground/sessions${query}`, apiKey)
}

export async function getPlaygroundHistory(
  apiKey: string,
  params: { session_id?: string; model?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').PlaygroundRequestListResponse> {
  const qs = new URLSearchParams()
  if (params.session_id) qs.set('session_id', params.session_id)
  if (params.model) qs.set('model', params.model)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').PlaygroundRequestListResponse>(`/playground/history${query}`, apiKey)
}

export async function sendPlaygroundRequest(
  apiKey: string,
  data: {
    model: string
    provider?: string
    system_prompt?: string
    user_prompt: string
    session_id?: string
    parameters?: Record<string, unknown>
  }
): Promise<import('@/types/api').PlaygroundRequestResponse> {
  return apiFetch<import('@/types/api').PlaygroundRequestResponse>('/playground/send', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function comparePlaygroundModels(
  apiKey: string,
  data: {
    models: string[]
    system_prompt?: string
    user_prompt: string
    parameters?: Record<string, unknown>
  }
): Promise<import('@/types/api').PlaygroundCompareResponse> {
  return apiFetch<import('@/types/api').PlaygroundCompareResponse>('/playground/compare', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteMcpServer(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/mcp-registry/${id}`, apiKey, { method: 'DELETE' })
}

export async function listMcpTools(apiKey: string): Promise<import('@/types/api').McpToolListResponse> {
  return apiFetch<import('@/types/api').McpToolListResponse>('/mcp-registry/tools', apiKey)
}

export async function callMcpTool(apiKey: string, data: { server_id: string; tool_name: string; arguments?: Record<string, unknown> }): Promise<import('@/types/api').McpToolCallResponse> {
  return apiFetch<import('@/types/api').McpToolCallResponse>('/mcp-registry/tools/call', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function listMcpToolCalls(apiKey: string, limit = 50): Promise<import('@/types/api').McpToolCallList> {
  return apiFetch<import('@/types/api').McpToolCallList>(`/mcp-registry/tool-calls?limit=${limit}`, apiKey)
}

export async function syncHubProvider(
  apiKey: string,
  data: { provider: string; token?: string; endpoint_url?: string }
): Promise<import('@/types/api').HubProviderSyncResponse> {
  return apiFetch<import('@/types/api').HubProviderSyncResponse>('/hub/sync-provider', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function seedDefaultPlugins(apiKey: string): Promise<{ status: string; plugins_added: number; total: number }> {
  return apiFetch<{ status: string; plugins_added: number; total: number }>('/plugins/seed-defaults', apiKey, { method: 'POST' })
}

export async function grantMcpPermission(apiKey: string, data: { mcp_server_id: string; scope_type: string; scope_id?: string; allowed_tools: string[] }): Promise<import('@/types/api').McpPermissionResponse> {
  return apiFetch<import('@/types/api').McpPermissionResponse>('/mcp-registry/permissions', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function listMcpPermissions(apiKey: string): Promise<import('@/types/api').McpPermissionList> {
  return apiFetch<import('@/types/api').McpPermissionList>('/mcp-registry/permissions', apiKey)
}

export async function revokeMcpPermission(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/mcp-registry/permissions/${id}`, apiKey, { method: 'DELETE' })
}

// ── Plugins ──────────────────────────────────────────────────────────────

export async function createPlugin(
  apiKey: string,
  data: { name: string; plugin_type: string; hooks?: string[]; config?: Record<string, unknown>; priority?: number; version?: string; author?: string; description?: string }
): Promise<import('@/types/api').PluginResponse> {
  return apiFetch<import('@/types/api').PluginResponse>('/plugins', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function listPlugins(apiKey: string, includeInactive = false): Promise<import('@/types/api').PluginList> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return apiFetch<import('@/types/api').PluginList>(`/plugins${qs}`, apiKey)
}

export async function getPlugin(apiKey: string, id: string): Promise<import('@/types/api').PluginResponse> {
  return apiFetch<import('@/types/api').PluginResponse>(`/plugins/${id}`, apiKey)
}

export async function updatePlugin(apiKey: string, id: string, data: Record<string, unknown>): Promise<import('@/types/api').PluginResponse> {
  return apiFetch<import('@/types/api').PluginResponse>(`/plugins/${id}`, apiKey, { method: 'PUT', body: JSON.stringify(data) })
}

export async function deletePlugin(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/plugins/${id}`, apiKey, { method: 'DELETE' })
}

export async function listPluginExecutions(apiKey: string, pluginId: string, limit = 50): Promise<import('@/types/api').PluginExecutionList> {
  return apiFetch<import('@/types/api').PluginExecutionList>(`/plugins/${pluginId}/executions?limit=${limit}`, apiKey)
}

// ── AI Hub ───────────────────────────────────────────────────────────────

export async function addHubModel(
  apiKey: string,
  data: { name: string; provider: string; description?: string; capabilities?: string[]; context_window?: number; input_cost_per_1k?: number; output_cost_per_1k?: number; tags?: string[]; is_featured?: boolean; is_public?: boolean }
): Promise<import('@/types/api').HubModelResponse> {
  return apiFetch<import('@/types/api').HubModelResponse>('/hub/models', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function listHubModels(apiKey: string, params: { featured_only?: boolean; provider?: string; tag?: string } = {}): Promise<import('@/types/api').HubModelList> {
  const qs = new URLSearchParams()
  if (params.featured_only) qs.set('featured_only', 'true')
  if (params.provider) qs.set('provider', params.provider)
  if (params.tag) qs.set('tag', params.tag)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').HubModelList>(`/hub/models${query}`, apiKey)
}

export async function getHubModel(apiKey: string, id: string): Promise<import('@/types/api').HubModelResponse> {
  return apiFetch<import('@/types/api').HubModelResponse>(`/hub/models/${id}`, apiKey)
}

export async function updateHubModel(apiKey: string, id: string, data: Record<string, unknown>): Promise<import('@/types/api').HubModelResponse> {
  return apiFetch<import('@/types/api').HubModelResponse>(`/hub/models/${id}`, apiKey, { method: 'PUT', body: JSON.stringify(data) })
}

export async function deleteHubModel(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/hub/models/${id}`, apiKey, { method: 'DELETE' })
}

export async function requestHubAccess(apiKey: string, id: string): Promise<{ status: string; model_id: string; total_requests: number }> {
  return apiFetch<{ status: string; model_id: string; total_requests: number }>(`/hub/models/${id}/request-access`, apiKey, { method: 'POST' })
}

export async function getHubModelCostPosture(apiKey: string, modelId: string): Promise<import('@/types/api').HubModelCostPosture> {
  return apiFetch<import('@/types/api').HubModelCostPosture>(`/hub/models/${modelId}/cost-posture`, apiKey)
}

export async function getHubModelGovernance(apiKey: string, modelId: string): Promise<import('@/types/api').HubModelGovernanceStatus> {
  return apiFetch<import('@/types/api').HubModelGovernanceStatus>(`/hub/models/${modelId}/governance`, apiKey)
}

export async function getHubOrgSummary(apiKey: string): Promise<import('@/types/api').HubOrgSummary> {
  return apiFetch<import('@/types/api').HubOrgSummary>('/hub/org-summary', apiKey)
}

// ── Projects ─────────────────────────────────────────────────────────────

// ── Team Models ──────────────────────────────────────────────────────────

// Workspace control surfaces

export async function getTags(
  apiKey: string,
  params: { category?: string; include_inactive?: boolean } = {}
): Promise<import('@/types/api').TagListResponse> {
  const qs = new URLSearchParams()
  if (params.category) qs.set('category', params.category)
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').TagListResponse>(`/tags${query}`, apiKey)
}

export async function getTagTree(
  apiKey: string,
  params: { category?: string } = {}
): Promise<import('@/types/api').TagTreeResponse> {
  const qs = new URLSearchParams()
  if (params.category) qs.set('category', params.category)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').TagTreeResponse>(`/tags/tree${query}`, apiKey)
}

export async function getAutoTagRules(
  apiKey: string
): Promise<import('@/types/api').AutoTaggingRuleListResponse> {
  return apiFetch<import('@/types/api').AutoTaggingRuleListResponse>('/tags/auto-rules', apiKey)
}

export async function createTag(
  apiKey: string,
  data: {
    category: string
    key: string
    value: string
    description?: string | null
    parent_tag_id?: string | null
    is_active?: boolean
  }
): Promise<import('@/types/api').TagResponse> {
  return apiFetch<import('@/types/api').TagResponse>('/tags', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTag(
  apiKey: string,
  tagId: string,
  data: Partial<{
    category: string
    key: string
    value: string
    description: string | null
    parent_tag_id: string | null
    is_active: boolean
  }>
): Promise<import('@/types/api').TagResponse> {
  return apiFetch<import('@/types/api').TagResponse>(`/tags/${tagId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTag(apiKey: string, tagId: string): Promise<void> {
  await apiFetch<void>(`/tags/${tagId}`, apiKey, { method: 'DELETE' })
}

export async function createAutoTagRule(
  apiKey: string,
  data: {
    name: string
    description?: string | null
    match_type: 'equals' | 'contains' | 'regex' | 'prefix' | 'suffix'
    match_field: string
    match_pattern: string
    tag_key: string
    tag_value: string
    priority?: number
    is_active?: boolean
  }
): Promise<import('@/types/api').AutoTaggingRuleResponse> {
  return apiFetch<import('@/types/api').AutoTaggingRuleResponse>('/tags/auto-rules', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateAutoTagRule(
  apiKey: string,
  ruleId: string,
  data: Partial<{
    name: string
    description: string | null
    match_type: 'equals' | 'contains' | 'regex' | 'prefix' | 'suffix'
    match_field: string
    match_pattern: string
    tag_key: string
    tag_value: string
    priority: number
    is_active: boolean
  }>
): Promise<import('@/types/api').AutoTaggingRuleResponse> {
  return apiFetch<import('@/types/api').AutoTaggingRuleResponse>(`/tags/auto-rules/${ruleId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteAutoTagRule(apiKey: string, ruleId: string): Promise<void> {
  await apiFetch<void>(`/tags/auto-rules/${ruleId}`, apiKey, { method: 'DELETE' })
}

export async function simulateAutoTagging(
  apiKey: string,
  data: { fields: Record<string, string> }
): Promise<import('@/types/api').AutoTaggingSimulationResponse> {
  return apiFetch<import('@/types/api').AutoTaggingSimulationResponse>('/tags/auto-rules/simulate', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getSearchTools(
  apiKey: string,
  params: { include_inactive?: boolean } = {}
): Promise<import('@/types/api').SearchToolListResponse> {
  const qs = new URLSearchParams()
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').SearchToolListResponse>(`/search-tools${query}`, apiKey)
}

export async function createSearchTool(
  apiKey: string,
  data: {
    name: string
    description?: string | null
    tool_type: string
    endpoint_url?: string | null
    auth_type?: string | null
    auth_config?: Record<string, unknown>
    rate_limit_rpm?: number | null
    cost_per_query?: number
    is_active?: boolean
    avg_quality_score?: number | null
    config?: Record<string, unknown>
  }
): Promise<import('@/types/api').SearchToolResponse> {
  return apiFetch<import('@/types/api').SearchToolResponse>('/search-tools', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateSearchTool(
  apiKey: string,
  toolId: string,
  data: Partial<{
    name: string
    description: string | null
    tool_type: string
    endpoint_url: string | null
    auth_type: string | null
    auth_config: Record<string, unknown>
    rate_limit_rpm: number | null
    cost_per_query: number
    is_active: boolean
    avg_quality_score: number | null
    config: Record<string, unknown>
  }>
): Promise<import('@/types/api').SearchToolResponse> {
  return apiFetch<import('@/types/api').SearchToolResponse>(`/search-tools/${toolId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteSearchTool(apiKey: string, toolId: string): Promise<void> {
  await apiFetch<void>(`/search-tools/${toolId}`, apiKey, {
    method: 'DELETE',
  })
}

export async function getSearchToolPolicies(
  apiKey: string,
  toolId: string
): Promise<import('@/types/api').SearchToolPolicySummary> {
  return apiFetch<import('@/types/api').SearchToolPolicySummary>(`/search-tools/${toolId}/policies`, apiKey)
}

export async function getToolPolicies(
  apiKey: string,
  params: { tool_name?: string; include_inactive?: boolean } = {}
): Promise<import('@/types/api').ToolPolicyListResponse> {
  const qs = new URLSearchParams()
  if (params.tool_name) qs.set('tool_name', params.tool_name)
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').ToolPolicyListResponse>(`/tool-policies${query}`, apiKey)
}

export async function createToolPolicy(
  apiKey: string,
  data: {
    name: string
    description?: string
    tool_name: string
    action: string
    condition_type?: string
    condition_config?: Record<string, unknown>
    scope_type?: string
    scope_id?: string
    priority?: number
  }
): Promise<import('@/types/api').ToolPolicyResponse> {
  return apiFetch<import('@/types/api').ToolPolicyResponse>('/tool-policies', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateToolPolicy(
  apiKey: string,
  id: string,
  data: Partial<{
    name: string
    description: string
    tool_name: string
    action: string
    condition_type: string | null
    condition_config: Record<string, unknown>
    scope_type: string
    scope_id: string | null
    priority: number
    is_active: boolean
  }>
): Promise<import('@/types/api').ToolPolicyResponse> {
  return apiFetch<import('@/types/api').ToolPolicyResponse>(`/tool-policies/${id}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteToolPolicy(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/tool-policies/${id}`, apiKey, { method: 'DELETE' })
}

export async function simulateToolPolicy(
  apiKey: string,
  data: {
    tool_name: string
    tool_type?: string
    risk_score?: number
    end_user_id?: string
    feature_tag?: string
    context?: Record<string, unknown>
  }
): Promise<import('@/types/api').ToolPolicySimulationResponse> {
  return apiFetch<import('@/types/api').ToolPolicySimulationResponse>('/tool-policies/simulate', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getToolPolicyAnalytics(
  apiKey: string,
  limit = 500
): Promise<import('@/types/api').ToolUsageAnalyticsResponse> {
  return apiFetch<import('@/types/api').ToolUsageAnalyticsResponse>(`/tool-policies/analytics?limit=${limit}`, apiKey)
}

export async function getAccessGroups(
  apiKey: string,
  params: { include_inactive?: boolean } = {}
): Promise<import('@/types/api').AccessGroupListResponse> {
  const qs = new URLSearchParams()
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').AccessGroupListResponse>(`/access-groups${query}`, apiKey)
}

export async function getAccessGroupMembers(
  apiKey: string,
  groupId: string
): Promise<import('@/types/api').AccessGroupMemberListResponse> {
  return apiFetch<import('@/types/api').AccessGroupMemberListResponse>(`/access-groups/${groupId}/members`, apiKey)
}

export async function getAccessGroupDashboard(
  apiKey: string,
  groupId?: string
): Promise<import('@/types/api').AccessGroupDashboardResponse> {
  const query = groupId ? `?group_id=${encodeURIComponent(groupId)}` : ''
  return apiFetch<import('@/types/api').AccessGroupDashboardResponse>(`/access-groups/dashboard${query}`, apiKey)
}

export async function createAccessGroup(
  apiKey: string,
  data: {
    name: string
    description?: string
    budget_usd?: number
    budget_period?: string
    guardrail_profile?: string
    is_active?: boolean
    permissions?: Record<string, any>
  }
): Promise<import('@/types/api').AccessGroupResponse> {
  return apiFetch<import('@/types/api').AccessGroupResponse>('/access-groups', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateAccessGroup(
  apiKey: string,
  groupId: string,
  data: {
    name?: string
    description?: string
    budget_usd?: number
    budget_period?: string
    guardrail_profile?: string
    is_active?: boolean
    permissions?: Record<string, any>
  }
): Promise<import('@/types/api').AccessGroupResponse> {
  return apiFetch<import('@/types/api').AccessGroupResponse>(`/access-groups/${groupId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteAccessGroup(
  apiKey: string,
  groupId: string
): Promise<void> {
  await apiFetch(`/access-groups/${groupId}`, apiKey, {
    method: 'DELETE',
  })
}

export async function addAccessGroupMember(
  apiKey: string,
  groupId: string,
  data: { user_id: string; role?: string }
): Promise<import('@/types/api').AccessGroupMemberResponse> {
  return apiFetch<import('@/types/api').AccessGroupMemberResponse>(`/access-groups/${groupId}/members`, apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function removeAccessGroupMember(
  apiKey: string,
  groupId: string,
  userId: string
): Promise<void> {
  await apiFetch(`/access-groups/${groupId}/members/${userId}`, apiKey, {
    method: 'DELETE',
  })
}

export async function getResponseCacheConfigs(
  apiKey: string
): Promise<import('@/types/api').ResponseCacheConfigListResponse> {
  return apiFetch<import('@/types/api').ResponseCacheConfigListResponse>('/response-cache', apiKey)
}

export async function createResponseCacheConfig(
  apiKey: string,
  body: import('@/types/api').ResponseCacheConfigCreate
): Promise<import('@/types/api').ResponseCacheConfigResponse> {
  return apiFetch<import('@/types/api').ResponseCacheConfigResponse>('/response-cache', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function getResponseCacheConfig(
  apiKey: string,
  configId: string,
): Promise<import('@/types/api').ResponseCacheConfigResponse> {
  return apiFetch<import('@/types/api').ResponseCacheConfigResponse>(
    `/response-cache/${configId}`,
    apiKey,
  )
}

export async function updateResponseCacheConfig(
  apiKey: string,
  configId: string,
  body: import('@/types/api').ResponseCacheConfigUpdate,
): Promise<import('@/types/api').ResponseCacheConfigResponse> {
  return apiFetch<import('@/types/api').ResponseCacheConfigResponse>(
    `/response-cache/${configId}`,
    apiKey,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  )
}

export async function deleteResponseCacheConfig(apiKey: string, configId: string): Promise<void> {
  await apiFetch<void>(`/response-cache/${configId}`, apiKey, { method: 'DELETE' })
}

export async function getResponseCacheStats(
  apiKey: string
): Promise<import('@/types/api').ResponseCacheStatsResponse> {
  return apiFetch<import('@/types/api').ResponseCacheStatsResponse>('/response-cache/stats', apiKey)
}

export async function getApiKeyObserveFootprint(apiKey: string, apiKeyId: string): Promise<import('@/types/api').ApiKeyObserveFootprint> {
  return apiFetch<import('@/types/api').ApiKeyObserveFootprint>(`/analytics/api-key-footprint/${apiKeyId}`, apiKey)
}

export async function getWorkspaceObservePosture(apiKey: string): Promise<import('@/types/api').WorkspaceObservePosture> {
  return apiFetch<import('@/types/api').WorkspaceObservePosture>('/analytics/workspace-posture', apiKey)
}

export async function getWorkspaceGovernancePosture(apiKey: string): Promise<import('@/types/api').WorkspaceGovernancePosture> {
  return apiFetch<import('@/types/api').WorkspaceGovernancePosture>('/analytics/workspace-governance-posture', apiKey)
}

export async function getAccessGroupGatewayPosture(apiKey: string, accessGroupId: string): Promise<import('@/types/api').AccessGroupGatewayPosture> {
  return apiFetch<import('@/types/api').AccessGroupGatewayPosture>(`/analytics/access-group-gateway-posture?access_group_id=${accessGroupId}`, apiKey)
}

export async function getApiKeyGatewayPosture(apiKey: string, apiKeyId: string): Promise<import('@/types/api').ApiKeyGatewayPosture> {
  return apiFetch<import('@/types/api').ApiKeyGatewayPosture>(`/analytics/api-key-gateway-posture?api_key_id=${apiKeyId}`, apiKey)
}

export async function getTelemetryDownstreamPosture(apiKey: string): Promise<import('@/types/api').TelemetryDownstreamPosture> {
  return apiFetch<import('@/types/api').TelemetryDownstreamPosture>('/analytics/telemetry-downstream-posture', apiKey)
}

export async function getMcpRegistryPosture(apiKey: string): Promise<import('@/types/api').McpRegistryPosture> {
  return apiFetch<import('@/types/api').McpRegistryPosture>('/analytics/mcp-registry-posture', apiKey)
}

export async function getAiHubRuntimePosture(apiKey: string): Promise<import('@/types/api').AiHubRuntimePosture> {
  return apiFetch<import('@/types/api').AiHubRuntimePosture>('/analytics/ai-hub-runtime-posture', apiKey)
}

export async function getProviderProfileFinopsPosture(apiKey: string, profileId: string): Promise<import('@/types/api').ProviderProfileFinopsPosture> {
  return apiFetch<import('@/types/api').ProviderProfileFinopsPosture>(`/analytics/provider-profile-finops-posture?profile_id=${profileId}`, apiKey)
}

export async function getProviderProfileObservePosture(apiKey: string, profileId: string): Promise<import('@/types/api').ProviderProfileObservePosture> {
  return apiFetch<import('@/types/api').ProviderProfileObservePosture>(`/analytics/provider-profile-observe-posture?profile_id=${profileId}`, apiKey)
}

export async function getBudgetPerformancePosture(apiKey: string, budgetId: string): Promise<import('@/types/api').BudgetPerformancePosture> {
  return apiFetch<import('@/types/api').BudgetPerformancePosture>(`/analytics/budget-performance-posture/${budgetId}`, apiKey)
}

export async function getBudgetOrgScopePosture(apiKey: string, budgetId: string): Promise<import('@/types/api').BudgetOrgScopePosture> {
  return apiFetch<import('@/types/api').BudgetOrgScopePosture>(`/analytics/budget-org-scope-posture/${budgetId}`, apiKey)
}

export async function getBudgetDetailObservePosture(apiKey: string): Promise<import('@/types/api').BudgetDetailObservePosture> {
  return apiFetch<import('@/types/api').BudgetDetailObservePosture>('/analytics/budget-detail-observe-posture', apiKey)
}

export async function getBudgetOverrideGovernancePosture(apiKey: string): Promise<import('@/types/api').BudgetOverrideGovernancePosture> {
  return apiFetch<import('@/types/api').BudgetOverrideGovernancePosture>('/analytics/budget-override-governance-posture', apiKey)
}

export async function getBudgetDetailBuildPosture(apiKey: string): Promise<import('@/types/api').BudgetDetailBuildPosture> {
  return apiFetch<import('@/types/api').BudgetDetailBuildPosture>('/analytics/budget-detail-build-posture', apiKey)
}

export async function getBudgetControlPlatformPosture(apiKey: string): Promise<import('@/types/api').BudgetControlPlatformPosture> {
  return apiFetch<import('@/types/api').BudgetControlPlatformPosture>('/analytics/budget-control-platform-posture', apiKey)
}

export async function getBillingPeriodPerformancePosture(apiKey: string): Promise<import('@/types/api').BillingPeriodPerformancePosture> {
  return apiFetch<import('@/types/api').BillingPeriodPerformancePosture>('/analytics/billing-period-performance-posture', apiKey)
}

export async function getBillingOrgScopePosture(apiKey: string): Promise<import('@/types/api').BillingOrgScopePosture> {
  return apiFetch<import('@/types/api').BillingOrgScopePosture>('/analytics/billing-org-scope-posture', apiKey)
}

export async function getFinOpsInternalPosture(apiKey: string): Promise<import('@/types/api').FinOpsInternalPosture> {
  return apiFetch<import('@/types/api').FinOpsInternalPosture>('/analytics/finops-internal-posture', apiKey)
}

export async function getBudgetControlObservePosture(apiKey: string): Promise<import('@/types/api').BudgetControlObservePosture> {
  return apiFetch<import('@/types/api').BudgetControlObservePosture>('/analytics/budget-control-observe-posture', apiKey)
}

export async function getBudgetControlBuildPosture(apiKey: string): Promise<import('@/types/api').BudgetControlBuildPosture> {
  return apiFetch<import('@/types/api').BudgetControlBuildPosture>('/analytics/budget-control-build-posture', apiKey)
}

export async function getBillingCrossFeaturePosture(apiKey: string): Promise<import('@/types/api').BillingCrossFeaturePosture> {
  return apiFetch<import('@/types/api').BillingCrossFeaturePosture>('/analytics/billing-cross-feature-posture', apiKey)
}

export async function getChargebackCrossFeaturePosture(apiKey: string): Promise<import('@/types/api').ChargebackCrossFeaturePosture> {
  return apiFetch<import('@/types/api').ChargebackCrossFeaturePosture>('/analytics/chargeback-cross-feature-posture', apiKey)
}

export async function getLedgerCrossFeaturePosture(apiKey: string): Promise<import('@/types/api').LedgerCrossFeaturePosture> {
  return apiFetch<import('@/types/api').LedgerCrossFeaturePosture>('/analytics/ledger-cross-feature-posture', apiKey)
}

export async function getBudgetScopeGovernancePosture(apiKey: string): Promise<import('@/types/api').BudgetScopeGovernancePosture> {
  return apiFetch<import('@/types/api').BudgetScopeGovernancePosture>('/analytics/budget-scope-governance-posture', apiKey)
}

export async function getBudgetDetailDrillbackPosture(apiKey: string): Promise<import('@/types/api').BudgetDetailDrillbackPosture> {
  return apiFetch<import('@/types/api').BudgetDetailDrillbackPosture>('/analytics/budget-detail-drillback-posture', apiKey)
}

export async function getBudgetOverrideExceptionPosture(apiKey: string): Promise<import('@/types/api').BudgetOverrideExceptionPosture> {
  return apiFetch<import('@/types/api').BudgetOverrideExceptionPosture>('/analytics/budget-override-exception-posture', apiKey)
}

export async function getBillingReconciliationPosture(apiKey: string): Promise<import('@/types/api').BillingReconciliationPosture> {
  return apiFetch<import('@/types/api').BillingReconciliationPosture>('/analytics/billing-reconciliation-posture', apiKey)
}

export async function getBillingDetailEvidencePosture(apiKey: string): Promise<import('@/types/api').BillingDetailEvidencePosture> {
  return apiFetch<import('@/types/api').BillingDetailEvidencePosture>('/analytics/billing-detail-evidence-posture', apiKey)
}

export async function getChargebackAttributionPosture(apiKey: string): Promise<import('@/types/api').ChargebackAttributionPosture> {
  return apiFetch<import('@/types/api').ChargebackAttributionPosture>('/analytics/chargeback-attribution-posture', apiKey)
}

export async function getGatewayFinopsPosture(apiKey: string): Promise<import('@/types/api').GatewayFinopsPosture> {
  return apiFetch<import('@/types/api').GatewayFinopsPosture>('/analytics/gateway-finops-posture', apiKey)
}

export async function getUserGatewayPosture(apiKey: string, userId: string): Promise<import('@/types/api').UserGatewayPosture> {
  return apiFetch<import('@/types/api').UserGatewayPosture>(`/analytics/user-gateway-posture?user_id=${userId}`, apiKey)
}

export async function getGatewayObservePosture(apiKey: string): Promise<import('@/types/api').GatewayObservePosture> {
  return apiFetch<import('@/types/api').GatewayObservePosture>('/analytics/gateway-observe-posture', apiKey)
}

export async function getGuardrailsObservePosture(apiKey: string): Promise<import('@/types/api').GuardrailsObservePosture> {
  return apiFetch<import('@/types/api').GuardrailsObservePosture>('/analytics/guardrails-observe-posture', apiKey)
}

export async function getResponseCacheEconomicsPosture(apiKey: string): Promise<import('@/types/api').ResponseCacheEconomicsPosture> {
  return apiFetch<import('@/types/api').ResponseCacheEconomicsPosture>('/analytics/response-cache-economics-posture', apiKey)
}

export async function getRateLimitScopePosture(apiKey: string): Promise<import('@/types/api').RateLimitScopePosture> {
  return apiFetch<import('@/types/api').RateLimitScopePosture>('/analytics/rate-limit-scope-posture', apiKey)
}

export async function getInvestigationAccessGroupPosture(apiKey: string): Promise<import('@/types/api').InvestigationAccessGroupPosture> {
  return apiFetch<import('@/types/api').InvestigationAccessGroupPosture>('/analytics/investigation-access-group-posture', apiKey)
}

export async function getGuardrailsFinopsPosture(apiKey: string): Promise<import('@/types/api').GuardrailsFinopsPosture> {
  return apiFetch<import('@/types/api').GuardrailsFinopsPosture>('/analytics/guardrails-finops-posture', apiKey)
}

export async function getGatewaySafetyPosture(apiKey: string): Promise<import('@/types/api').GatewaySafetyPosture> {
  return apiFetch<import('@/types/api').GatewaySafetyPosture>('/analytics/gateway-safety-posture', apiKey)
}

export async function getGatewayBuildPosture(apiKey: string): Promise<import('@/types/api').GatewayBuildPosture> {
  return apiFetch<import('@/types/api').GatewayBuildPosture>('/analytics/gateway-build-posture', apiKey)
}

export async function getPerformanceControlsOrgPosture(apiKey: string): Promise<import('@/types/api').PerformanceControlsOrgPosture> {
  return apiFetch<import('@/types/api').PerformanceControlsOrgPosture>('/analytics/performance-controls-org-posture', apiKey)
}

export async function getGatewayInternalPosture(apiKey: string): Promise<import('@/types/api').GatewayInternalPosture> {
  return apiFetch<import('@/types/api').GatewayInternalPosture>('/analytics/gateway-internal-posture', apiKey)
}

export async function getGatewayControlPlanePosture(apiKey: string): Promise<import('@/types/api').GatewayControlPlanePosture> {
  return apiFetch<import('@/types/api').GatewayControlPlanePosture>('/analytics/gateway-control-plane-posture', apiKey)
}

export async function getProviderProfileRuntimePosture(apiKey: string): Promise<import('@/types/api').ProviderProfileRuntimePosture> {
  return apiFetch<import('@/types/api').ProviderProfileRuntimePosture>('/analytics/provider-profile-runtime-posture', apiKey)
}

export async function getToolRegistryFinopsPosture(apiKey: string): Promise<import('@/types/api').ToolRegistryFinopsPosture> {
  return apiFetch<import('@/types/api').ToolRegistryFinopsPosture>('/analytics/tool-registry-finops-posture', apiKey)
}

export async function getApprovalsAlertFinopsPosture(apiKey: string): Promise<import('@/types/api').ApprovalsAlertFinopsPosture> {
  return apiFetch<import('@/types/api').ApprovalsAlertFinopsPosture>('/analytics/approvals-alert-finops-posture', apiKey)
}

export async function getTagsFinopsBudgetPosture(apiKey: string): Promise<import('@/types/api').TagsFinopsBudgetPosture> {
  return apiFetch<import('@/types/api').TagsFinopsBudgetPosture>('/analytics/tags-finops-budget-posture', apiKey)
}

export async function getToolGovernanceOrgPosture(apiKey: string): Promise<import('@/types/api').ToolGovernanceOrgPosture> {
  return apiFetch<import('@/types/api').ToolGovernanceOrgPosture>('/analytics/tool-governance-org-posture', apiKey)
}

export async function getToolGovernanceGatewayPosture(apiKey: string): Promise<import('@/types/api').ToolGovernanceGatewayPosture> {
  return apiFetch<import('@/types/api').ToolGovernanceGatewayPosture>('/analytics/tool-governance-gateway-posture', apiKey)
}

export async function getExceptionWorkflowsOrgPosture(apiKey: string): Promise<import('@/types/api').ExceptionWorkflowsOrgPosture> {
  return apiFetch<import('@/types/api').ExceptionWorkflowsOrgPosture>('/analytics/exception-workflows-org-posture', apiKey)
}

export async function getExceptionWorkflowsGatewayPosture(apiKey: string): Promise<import('@/types/api').ExceptionWorkflowsGatewayPosture> {
  return apiFetch<import('@/types/api').ExceptionWorkflowsGatewayPosture>('/analytics/exception-workflows-gateway-posture', apiKey)
}

export async function getDataProtectionOrgPosture(apiKey: string): Promise<import('@/types/api').DataProtectionOrgPosture> {
  return apiFetch<import('@/types/api').DataProtectionOrgPosture>('/analytics/data-protection-org-posture', apiKey)
}

export async function getDataProtectionGatewayPosture(apiKey: string): Promise<import('@/types/api').DataProtectionGatewayPosture> {
  return apiFetch<import('@/types/api').DataProtectionGatewayPosture>('/analytics/data-protection-gateway-posture', apiKey)
}

export async function getEvidenceAuditCrossPosture(apiKey: string): Promise<import('@/types/api').EvidenceAuditCrossPosture> {
  return apiFetch<import('@/types/api').EvidenceAuditCrossPosture>('/analytics/evidence-audit-cross-posture', apiKey)
}

export async function getGovernanceInternalPosture(apiKey: string): Promise<import('@/types/api').GovernanceInternalPosture> {
  return apiFetch<import('@/types/api').GovernanceInternalPosture>('/analytics/governance-internal-posture', apiKey)
}

export async function getToolRegistryRuntimePosture(apiKey: string): Promise<import('@/types/api').ToolRegistryRuntimePosture> {
  return apiFetch<import('@/types/api').ToolRegistryRuntimePosture>('/analytics/tool-registry-runtime-posture', apiKey)
}

export async function getToolPoliciesRuntimePosture(apiKey: string): Promise<import('@/types/api').ToolPoliciesRuntimePosture> {
  return apiFetch<import('@/types/api').ToolPoliciesRuntimePosture>('/analytics/tool-policies-runtime-posture', apiKey)
}

export async function getApprovalsRuntimePosture(apiKey: string): Promise<import('@/types/api').ApprovalsRuntimePosture> {
  return apiFetch<import('@/types/api').ApprovalsRuntimePosture>('/analytics/approvals-runtime-posture', apiKey)
}

export async function getDataCaptureRuntimePosture(apiKey: string): Promise<import('@/types/api').DataCaptureRuntimePosture> {
  return apiFetch<import('@/types/api').DataCaptureRuntimePosture>('/analytics/data-capture-runtime-posture', apiKey)
}

export async function getSecurityRuntimePosture(apiKey: string): Promise<import('@/types/api').SecurityRuntimePosture> {
  return apiFetch<import('@/types/api').SecurityRuntimePosture>('/analytics/security-runtime-posture', apiKey)
}
export async function getAlertRulesRuntimePosture(apiKey: string): Promise<import('@/types/api').AlertRulesRuntimePosture> {
  return apiFetch<import('@/types/api').AlertRulesRuntimePosture>('/analytics/alert-rules-runtime-posture', apiKey)
}
export async function getAuditLogRuntimePosture(apiKey: string): Promise<import('@/types/api').AuditLogRuntimePosture> {
  return apiFetch<import('@/types/api').AuditLogRuntimePosture>('/analytics/audit-log-runtime-posture', apiKey)
}
export async function getGovernancePackRuntimePosture(apiKey: string): Promise<import('@/types/api').GovernancePackRuntimePosture> {
  return apiFetch<import('@/types/api').GovernancePackRuntimePosture>('/analytics/governance-pack-runtime-posture', apiKey)
}
export async function getTagsRuntimePosture(apiKey: string): Promise<import('@/types/api').TagsRuntimePosture> {
  return apiFetch<import('@/types/api').TagsRuntimePosture>('/analytics/tags-runtime-posture', apiKey)
}

export async function getPlaygroundOrgGatewayPosture(apiKey: string): Promise<import('@/types/api').PlaygroundOrgGatewayPosture> {
  return apiFetch<import('@/types/api').PlaygroundOrgGatewayPosture>('/analytics/playground-org-gateway-posture', apiKey)
}

export async function getPromptsOrgGatewayPosture(apiKey: string): Promise<import('@/types/api').PromptsOrgGatewayPosture> {
  return apiFetch<import('@/types/api').PromptsOrgGatewayPosture>('/analytics/prompts-org-gateway-posture', apiKey)
}

export async function getPlaygroundObservePosture(apiKey: string): Promise<import('@/types/api').PlaygroundObservePosture> {
  return apiFetch<import('@/types/api').PlaygroundObservePosture>('/analytics/playground-observe-posture', apiKey)
}

export async function getPromptDetailObservePosture(apiKey: string, promptName?: string): Promise<import('@/types/api').PromptDetailObservePosture> {
  const qs = promptName ? `?prompt_name=${encodeURIComponent(promptName)}` : ''
  return apiFetch<import('@/types/api').PromptDetailObservePosture>(`/analytics/prompt-detail-observe-posture${qs}`, apiKey)
}

export async function getWorkflowDetailCrossFeaturePosture(apiKey: string): Promise<import('@/types/api').WorkflowDetailCrossFeaturePosture> {
  return apiFetch<import('@/types/api').WorkflowDetailCrossFeaturePosture>('/analytics/workflow-detail-cross-feature-posture', apiKey)
}

export async function getEvalReplayOrgGatewayPosture(apiKey: string): Promise<import('@/types/api').EvalReplayOrgGatewayPosture> {
  return apiFetch<import('@/types/api').EvalReplayOrgGatewayPosture>('/analytics/eval-replay-org-gateway-posture', apiKey)
}

export async function getEvalReplayObservePosture(apiKey: string): Promise<import('@/types/api').EvalReplayObservePosture> {
  return apiFetch<import('@/types/api').EvalReplayObservePosture>('/analytics/eval-replay-observe-posture', apiKey)
}

export async function getOptimizationOrgGatewayPosture(apiKey: string): Promise<import('@/types/api').OptimizationOrgGatewayPosture> {
  return apiFetch<import('@/types/api').OptimizationOrgGatewayPosture>('/analytics/optimization-org-gateway-posture', apiKey)
}

export async function getOptimizationObservePosture(apiKey: string): Promise<import('@/types/api').OptimizationObservePosture> {
  return apiFetch<import('@/types/api').OptimizationObservePosture>('/analytics/optimization-observe-posture', apiKey)
}

export async function getOptimizationFinOpsPosture(apiKey: string): Promise<import('@/types/api').OptimizationFinOpsPosture> {
  return apiFetch<import('@/types/api').OptimizationFinOpsPosture>('/analytics/optimization-finops-posture', apiKey)
}

export async function getBuildInternalPosture(apiKey: string): Promise<import('@/types/api').BuildInternalPosture> {
  return apiFetch<import('@/types/api').BuildInternalPosture>('/analytics/build-internal-posture', apiKey)
}

export async function getPromptsListObservePosture(apiKey: string): Promise<import('@/types/api').PromptsListObservePosture> {
  return apiFetch<import('@/types/api').PromptsListObservePosture>('/analytics/prompts-list-observe-posture', apiKey)
}

export async function getPromptDetailHubFinOpsPosture(apiKey: string): Promise<import('@/types/api').PromptDetailHubFinOpsPosture> {
  return apiFetch<import('@/types/api').PromptDetailHubFinOpsPosture>('/analytics/prompt-detail-hub-finops-posture', apiKey)
}

export async function getAgentsListPosture(apiKey: string): Promise<import('@/types/api').AgentsListPosture> {
  return apiFetch<import('@/types/api').AgentsListPosture>('/analytics/agents-list-posture', apiKey)
}

export async function getAgentDetailGovernancePosture(apiKey: string): Promise<import('@/types/api').AgentDetailGovernancePosture> {
  return apiFetch<import('@/types/api').AgentDetailGovernancePosture>('/analytics/agent-detail-governance-posture', apiKey)
}

export async function getWorkflowsListPosture(apiKey: string): Promise<import('@/types/api').WorkflowsListPosture> {
  return apiFetch<import('@/types/api').WorkflowsListPosture>('/analytics/workflows-list-posture', apiKey)
}

export async function getWorkflowDetailLoopPosture(apiKey: string): Promise<import('@/types/api').WorkflowDetailLoopPosture> {
  return apiFetch<import('@/types/api').WorkflowDetailLoopPosture>('/analytics/workflow-detail-loop-posture', apiKey)
}

export async function getWorkflowRunEvidencePosture(apiKey: string): Promise<import('@/types/api').WorkflowRunEvidencePosture> {
  return apiFetch<import('@/types/api').WorkflowRunEvidencePosture>('/analytics/workflow-run-evidence-posture', apiKey)
}

export async function getDatasetsEvalAssetPosture(apiKey: string): Promise<import('@/types/api').DatasetsEvalAssetPosture> {
  return apiFetch<import('@/types/api').DatasetsEvalAssetPosture>('/analytics/datasets-eval-asset-posture', apiKey)
}

export async function getEvalStudioParentPosture(apiKey: string): Promise<import('@/types/api').EvalStudioParentPosture> {
  return apiFetch<import('@/types/api').EvalStudioParentPosture>('/analytics/eval-studio-parent-posture', apiKey)
}

export async function getExperimentsComparisonPosture(apiKey: string): Promise<import('@/types/api').ExperimentsComparisonPosture> {
  return apiFetch<import('@/types/api').ExperimentsComparisonPosture>('/analytics/experiments-comparison-posture', apiKey)
}

export async function getReplayLabModePosture(apiKey: string): Promise<import('@/types/api').ReplayLabModePosture> {
  return apiFetch<import('@/types/api').ReplayLabModePosture>('/analytics/replay-lab-mode-posture', apiKey)
}

export async function getReplayResultAnalysisPosture(apiKey: string): Promise<import('@/types/api').ReplayResultAnalysisPosture> {
  return apiFetch<import('@/types/api').ReplayResultAnalysisPosture>('/analytics/replay-result-analysis-posture', apiKey)
}

export async function getRunbooksRemediationPosture(apiKey: string): Promise<import('@/types/api').RunbooksRemediationPosture> {
  return apiFetch<import('@/types/api').RunbooksRemediationPosture>('/analytics/runbooks-remediation-posture', apiKey)
}

export async function getOptOppsRationalePosture(apiKey: string): Promise<import('@/types/api').OptOppsRationalePosture> {
  return apiFetch<import('@/types/api').OptOppsRationalePosture>('/analytics/opt-opps-rationale-posture', apiKey)
}

export async function getOptSimDecisionPosture(apiKey: string): Promise<import('@/types/api').OptSimDecisionPosture> {
  return apiFetch<import('@/types/api').OptSimDecisionPosture>('/analytics/opt-sim-decision-posture', apiKey)
}

export async function getModelScorecardsIntelPosture(apiKey: string): Promise<import('@/types/api').ModelScorecardsIntelPosture> {
  return apiFetch<import('@/types/api').ModelScorecardsIntelPosture>('/analytics/model-scorecards-intel-posture', apiKey)
}

export async function getVectorStoresLifecyclePosture(apiKey: string): Promise<import('@/types/api').VectorStoresLifecyclePosture> {
  return apiFetch<import('@/types/api').VectorStoresLifecyclePosture>('/analytics/vector-stores-lifecycle-posture', apiKey)
}

export async function getVectorStoreDetailEvidencePosture(apiKey: string): Promise<import('@/types/api').VectorStoreDetailEvidencePosture> {
  return apiFetch<import('@/types/api').VectorStoreDetailEvidencePosture>('/analytics/vector-store-detail-evidence-posture', apiKey)
}

export async function getPlatformLifecyclePosture(apiKey: string): Promise<import('@/types/api').PlatformLifecyclePosture> {
  return apiFetch<import('@/types/api').PlatformLifecyclePosture>('/analytics/platform-lifecycle-posture', apiKey)
}

export async function getPlatformSettingsConvergencePosture(apiKey: string): Promise<import('@/types/api').PlatformSettingsConvergencePosture> {
  return apiFetch<import('@/types/api').PlatformSettingsConvergencePosture>('/analytics/platform-settings-convergence-posture', apiKey)
}

export async function getPlatformAdminObservePosture(apiKey: string): Promise<import('@/types/api').PlatformAdminObservePosture> {
  return apiFetch<import('@/types/api').PlatformAdminObservePosture>('/analytics/platform-admin-observe-posture', apiKey)
}

export async function getGatewayRuntimeBoundaryPosture(apiKey: string): Promise<import('@/types/api').GatewayRuntimeBoundaryPosture> {
  return apiFetch<import('@/types/api').GatewayRuntimeBoundaryPosture>('/analytics/gateway-runtime-boundary-posture', apiKey)
}

export async function getSidecarCollapsePosture(apiKey: string): Promise<import('@/types/api').SidecarCollapsePosture> {
  return apiFetch<import('@/types/api').SidecarCollapsePosture>('/analytics/sidecar-collapse-posture', apiKey)
}

export async function getConsumerMigrationPosture(apiKey: string): Promise<import('@/types/api').ConsumerMigrationPosture> {
  return apiFetch<import('@/types/api').ConsumerMigrationPosture>('/analytics/consumer-migration-posture', apiKey)
}

export async function getRuntimeScopeModelPosture(apiKey: string): Promise<import('@/types/api').RuntimeScopeModelPosture> {
  return apiFetch<import('@/types/api').RuntimeScopeModelPosture>('/analytics/runtime-scope-model-posture', apiKey)
}

export async function getScopeEnforcementEvidencePosture(apiKey: string): Promise<import('@/types/api').ScopeEnforcementEvidencePosture> {
  return apiFetch<import('@/types/api').ScopeEnforcementEvidencePosture>('/analytics/scope-enforcement-evidence-posture', apiKey)
}

export async function getPipelineStudioPosture(apiKey: string): Promise<import('@/types/api').PipelineStudioPosture> {
  return apiFetch<import('@/types/api').PipelineStudioPosture>('/analytics/pipeline-studio-posture', apiKey)
}

export async function getApiExplorerPosture(apiKey: string): Promise<import('@/types/api').ApiExplorerPosture> {
  return apiFetch<import('@/types/api').ApiExplorerPosture>('/analytics/api-explorer-posture', apiKey)
}

export async function getDesignSystemPosture(apiKey: string): Promise<import('@/types/api').DesignSystemPosture> {
  return apiFetch<import('@/types/api').DesignSystemPosture>('/analytics/design-system-posture', apiKey)
}
