import type {
  AlertFiring,
  AlertHistoryList,
  AlertRule,
  AlertRuleList,
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
  BillingPeriod,
  BillingPeriodList,
  BreachList,
  ChargebackRuleList,
  ChargebackRuleResponse,
  Budget,
  BudgetList,
  CapturePolicyResponse,
  CohortList,
  DatasetList,
  DatasetResponse,
  ExperimentList,
  ExperimentResponse,
  ExperimentResults,
  LedgerSnapshotList,
  NotificationList,
  NotificationResponse,
  LedgerSnapshotResponse,
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
  RunListResponse,
  ScoreEvent,
  ScoreList,
  ScoreSummary,
  SessionDetail,
  SessionList,
  TurnCostResponse,
  VersionList,
  SecurityEventList,
  SlackTestResponse,
  SpendByFeature,
  SpendByModel,
  SpendByUser,
  SpendOverTime,
  TenantResponse,
  ToolRegistryList,
  ToolRegistryResponse,
  UserSpendDetail,
  UsageSnapshot,
  VersionCompareResult,
  WorkflowTopList,
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

  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<RunListResponse>(`/runs${query}`, apiKey)
}

export async function getRun(apiKey: string, runId: string): Promise<RunDetailResponse> {
  return apiFetch<RunDetailResponse>(`/runs/${runId}`, apiKey)
}

export async function getRunGraph(apiKey: string, runId: string): Promise<RunGraphResponse> {
  return apiFetch<RunGraphResponse>(`/runs/${runId}/graph`, apiKey)
}

// ── Analytics helpers ─────────────────────────────────────────────────────────

interface TimeWindow {
  from?: string
  to?: string
  [key: string]: string | undefined
}

function _analyticsQs(params: TimeWindow & Record<string, string | undefined>): string {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined) qs.set(k, v)
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
  granularity: 'hourly' | 'daily' = 'daily',
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

export async function getBudgets(apiKey: string): Promise<BudgetList> {
  return apiFetch<BudgetList>('/budgets', apiKey)
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

// ── Billing helpers ────────────────────────────────────────────────────────────

export async function getBillingPeriods(apiKey: string): Promise<BillingPeriodList> {
  return apiFetch<BillingPeriodList>('/billing/periods', apiKey)
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
  id: string
): Promise<ReconciliationResult> {
  return apiFetch<ReconciliationResult>(`/billing/periods/${id}/reconciliation`, apiKey)
}

export async function getPeriodBreakdown(
  apiKey: string,
  id: string
): Promise<PeriodBreakdown> {
  return apiFetch<PeriodBreakdown>(`/billing/periods/${id}/breakdown`, apiKey)
}

export async function exportPeriodCsv(apiKey: string, id: string): Promise<string> {
  const res = await fetch(`${API_URL}/billing/periods/${id}/export?format=csv`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.text()
}

export async function exportPeriodSignedJson(apiKey: string, id: string): Promise<object> {
  return apiFetch<object>(`/billing/periods/${id}/export?format=signed_json`, apiKey)
}

export async function listChargebackRules(apiKey: string): Promise<ChargebackRuleList> {
  return apiFetch<ChargebackRuleList>('/billing/chargeback-rules', apiKey)
}

export async function createChargebackRule(
  apiKey: string,
  body: { allocation_type: string; dimension: string; weight: string }
): Promise<ChargebackRuleResponse> {
  return apiFetch<ChargebackRuleResponse>('/billing/chargeback-rules', apiKey, {
    method: 'POST',
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

export async function listExperiments(apiKey: string): Promise<ExperimentList> {
  return apiFetch<ExperimentList>('/replay/experiments', apiKey)
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

// ── Phase 11 — Tool registry helpers ──────────────────────────────────────────

export async function listToolRegistry(apiKey: string): Promise<ToolRegistryList> {
  return apiFetch<ToolRegistryList>('/tools/registry', apiKey)
}

export async function upsertToolRegistry(
  apiKey: string,
  body: { tool_name: string; policy?: string; description?: string | null }
): Promise<ToolRegistryResponse> {
  return apiFetch<ToolRegistryResponse>('/tools/registry', apiKey, {
    method: 'POST',
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

// ── Phase 12 — Settings API key helpers ────────────────────────────────────────

export async function listApiKeys(apiKey: string): Promise<ApiKeyResponse[]> {
  return apiFetch<ApiKeyResponse[]>('/settings/api-keys', apiKey)
}

export async function createApiKey(
  apiKey: string,
  body: { name?: string | null; environment?: string; scopes?: string[]; created_by?: string | null }
): Promise<ApiKeyCreateResponse> {
  return apiFetch<ApiKeyCreateResponse>('/settings/api-keys', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
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
  }
): Promise<ProviderPricingResponse> {
  return apiFetch<ProviderPricingResponse>(`/providers/pricing/${pricingId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
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
    limit?: number
  } = {}
): Promise<ScoreList> {
  const qs = new URLSearchParams()
  if (params.run_id) qs.set('run_id', params.run_id)
  if (params.name) qs.set('name', params.name)
  if (params.source) qs.set('source', params.source)
  if (params.from) qs.set('from', params.from)
  if (params.to) qs.set('to', params.to)
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
    end_user_id?: string
    from?: string
    to?: string
    limit?: number
  } = {}
): Promise<SessionList> {
  const qs = new URLSearchParams()
  if (params.end_user_id) qs.set('end_user_id', params.end_user_id)
  if (params.from) qs.set('from', params.from)
  if (params.to) qs.set('to', params.to)
  if (params.limit) qs.set('limit', String(params.limit))
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
    threshold?: number
    window_minutes?: number
    is_active?: boolean
    channel_id?: string | null
  }
): Promise<AlertRule> {
  return apiFetch<AlertRule>(`/alerts/rules/${ruleId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
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
    provider: string
    target_model: string
    base_url?: string | null
    api_key_env_var?: string | null
    priority?: number
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
    target_model?: string
    base_url?: string | null
    api_key_env_var?: string | null
    priority?: number
    is_active?: boolean
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

export async function getGatewayStats(apiKey: string): Promise<GatewayStats> {
  return apiFetch<GatewayStats>('/gateway/stats', apiKey)
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

// ── Org Dashboard ─────────────────────────────────────────────────────────────

export async function getOrgDashboard(apiKey: string): Promise<import('@/types/api').OrgDashboard> {
  return apiFetch<import('@/types/api').OrgDashboard>('/org/dashboard', apiKey)
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
