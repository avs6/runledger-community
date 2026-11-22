/** Runs, sessions, analytics, outcomes and related context. */
import type { AnalyticsSummary, Annotation, AnnotationList, AnomalyList, CohortList, RegressionList, RunDetailResponse, RunEconomics, RunGraphResponse, RunListItem, RunListResponse, ScoreSummary, SessionDetail, SessionList, TurnCostResponse, SpendByFeature, SpendByModel, SpendByUser, SpendOverTime, UserSpendDetail, VersionCompareResult, WorkflowTopList, OtlpStats, OtlpBatchList, OtlpBatchDetail, OtlpInsights, ScopedSummary, SavingsResponse, OptimizationOpportunitiesResponse, TrendsResponse, RequestExplorerResponse, EngineeringMetrics, SimulationRequest, SimulationResult, RunbookList, RunbookResponse, ModelScorecardList, ModelScoreTrendList } from '@/types/api'
import { apiFetch, TimeWindow, _analyticsQs, ContextEntity } from './client'

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

export async function getScoreSummary(apiKey: string): Promise<ScoreSummary> {
  return apiFetch<ScoreSummary>('/analytics/scores/summary', apiKey)
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

export async function getOtlpInsights(apiKey: string): Promise<OtlpInsights> {
  return apiFetch<OtlpInsights>('/v1/traces/insights', apiKey)
}

// ── OTLP metrics (daily rollups) and GenAI usage reconciliation ──────────────

export async function listOtlpMetricSeries(
  apiKey: string,
  days = 7,
  name?: string,
  limit = 100,
): Promise<import('@/types/api').OtlpMetricSeriesList> {
  const qs = new URLSearchParams({ days: String(days), limit: String(limit) })
  if (name) qs.set('name', name)
  return apiFetch(`/v1/metrics/series?${qs}`, apiKey)
}

export async function getOtlpMetricUsage(
  apiKey: string,
  days = 7,
): Promise<import('@/types/api').OtlpMetricUsage> {
  return apiFetch(`/v1/metrics/usage?days=${days}`, apiKey)
}

// ── Ingest dead letters (events the pipeline could not apply) ────────────────

export async function listIngestDeadLetters(
  apiKey: string,
  status: 'pending' | 'replayed' | 'discarded' = 'pending',
  limit = 50,
  offset = 0,
): Promise<import('@/types/api').IngestDeadLetterList> {
  const qs = new URLSearchParams({ status, limit: String(limit), offset: String(offset) })
  return apiFetch(`/ingest/v1/dead-letters?${qs}`, apiKey)
}

export async function replayIngestDeadLetter(apiKey: string, id: string): Promise<{ requeued: number }> {
  return apiFetch(`/ingest/v1/dead-letters/${id}/replay`, apiKey, { method: 'POST' })
}

export async function replayAllIngestDeadLetters(apiKey: string): Promise<{ requeued: number }> {
  return apiFetch('/ingest/v1/dead-letters/replay', apiKey, { method: 'POST' })
}

export async function discardIngestDeadLetter(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/ingest/v1/dead-letters/${id}`, apiKey, { method: 'DELETE' })
}

// ── Signed ingest secret (per workspace) ──────────────────────────────────────

export async function getIngestSigningSecret(
  apiKey: string,
): Promise<import('@/types/api').IngestSigningSecret> {
  return apiFetch('/ingest/v1/signing-secret', apiKey)
}

export async function rotateIngestSigningSecret(
  apiKey: string,
): Promise<import('@/types/api').IngestSigningSecret> {
  return apiFetch('/ingest/v1/signing-secret/rotate', apiKey, { method: 'POST' })
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

export async function getApiKeyObserveFootprint(apiKey: string, apiKeyId: string): Promise<import('@/types/api').ApiKeyObserveFootprint> {
  return apiFetch<import('@/types/api').ApiKeyObserveFootprint>(`/analytics/api-key-footprint/${apiKeyId}`, apiKey)
}

// ── Account, sessions & invitations ─────────────────────────────────────────

/** Extract the API's `detail` message from an apiFetch error ("API 403: {...}"). */

export async function getEntityContext(
  apiKey: string,
  entity: ContextEntity,
  id?: string | null
): Promise<import('@/types/api').EntityContext> {
  const qs = new URLSearchParams({ entity })
  if (id) qs.set('id', id)
  return apiFetch<import('@/types/api').EntityContext>(`/context?${qs.toString()}`, apiKey)
}
