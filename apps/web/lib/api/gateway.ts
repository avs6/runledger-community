/** Gateway routes, policies, cache, providers, pricing and quota tiers. */
import type { GatewayRoutingGroup, GatewayRoutingGroupList, GatewayRoutingStrategyComparison, GatewayRoute, GatewayRequestList, GatewayRouteList, GatewayStats, RoutingPolicy, RoutingPolicyList, RoutingPolicyType, Budget, ProviderPricingList, ProviderPricingResponse } from '@/types/api'
import { apiFetch, TimeWindow, _analyticsQs } from './client'

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

export async function deleteProviderPricing(apiKey: string, pricingId: string): Promise<void> {
  await apiFetch<void>(`/providers/pricing/${pricingId}`, apiKey, { method: 'DELETE' })
}

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

export async function triggerPricingSync(
  apiKey: string,
  options?: { force?: boolean; dry_run?: boolean; providers?: string[] }
): Promise<{ inserted: number; updated: number; skipped: number; errors: string[] }> {
  return apiFetch('/pricing/sync', apiKey, {
    method: 'POST',
    body: JSON.stringify(options ?? { force: true }),
  })
}

// ── Model calls enrichment could not price ────────────────────────────────────

export async function getUnpricedUsage(
  apiKey: string,
  days = 30,
): Promise<import('@/types/api').UnpricedUsage> {
  return apiFetch(`/providers/pricing/unpriced?days=${days}`, apiKey)
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
  apiKey: string,
  params: { q?: string; sort?: string; limit?: number; offset?: number; include_inactive?: boolean } = {}
): Promise<import('@/types/api').BudgetTierList> {
  const qs = new URLSearchParams()
  if (params.q) qs.set('q', params.q)
  if (params.sort) qs.set('sort', params.sort)
  if (params.limit != null) qs.set('limit', String(params.limit))
  if (params.offset != null) qs.set('offset', String(params.offset))
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').BudgetTierList>(`/budget-tiers${query}`, apiKey)
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
