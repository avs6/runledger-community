'use client'

import { useEffect, useState, useCallback, createContext, useContext } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import { listGatewayRoutes, createGatewayRoute, updateGatewayRoute, deleteGatewayRoute, listGatewayRoutingGroups, createGatewayRoutingGroup, updateGatewayRoutingGroup, deleteGatewayRoutingGroup, getGatewayRoutingStrategyComparison, getGatewayStats, listRoutingPolicies, createRoutingPolicy, updateRoutingPolicy, getRoutingPolicyAnalysis, promoteRoutingPolicyWinner, advanceCanaryRollout, rollbackRoutingPolicy, deleteRoutingPolicy, listGatewayRequests, listProviderPricing, getRoutingRecommendation, getGatewayRateLimitOverview, getResponseCacheConfigs, getResponseCacheStats, createResponseCacheConfig, getResponseCacheConfig, updateResponseCacheConfig, deleteResponseCacheConfig, apiErrorMessage } from '@/lib/api'
import type { GatewayRoute, GatewayRoutingGroup, GatewayRoutingGroupStrategy, GatewayRoutingStrategyComparisonItem, GatewayStats, GatewayRequestLog, RoutingPolicy, RoutingPolicyAnalysis, RoutingPolicyType, ProviderPricingResponse, RoutingRecommendationResponse, GatewayRateLimitOverview, ResponseCacheConfigResponse, ResponseCacheStatsResponse } from '@/types/api'
import { parseCsvTags, RouteEditState, RoutingGroupEditState, RoutingPolicyEditState, CacheConfigEditState } from './shared'

/** Gateway page state and actions, shared with the tab components through context (review Wave 0.2). */

export const TABS = ['overview', 'routes', 'policies', 'cache', 'rate-limits', 'advanced'] as const
export type Tab = (typeof TABS)[number]

export function useGatewayState() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { isOrgAdmin, isPlatformAdmin } = useRole()
  const canManage = isOrgAdmin || isPlatformAdmin

  const [gatewayRoutes, setGatewayRoutes] = useState<GatewayRoute[]>([])
  const [gatewayStats, setGatewayStats] = useState<GatewayStats | null>(null)
  const [newRouteAlias, setNewRouteAlias] = useState('')
  const [newRouteProvider, setNewRouteProvider] = useState('openai')
  const [newRouteTargetModel, setNewRouteTargetModel] = useState('')
  const [newRouteBaseUrl, setNewRouteBaseUrl] = useState('')
  const [newRouteApiKeyEnvVar, setNewRouteApiKeyEnvVar] = useState('OPENAI_API_KEY')
  const [newRoutePriority, setNewRoutePriority] = useState('10')
  const [newRouteRoutingGroupId, setNewRouteRoutingGroupId] = useState('')
  const [newRouteRequiredTags, setNewRouteRequiredTags] = useState('')
  const [newRouteExcludedTags, setNewRouteExcludedTags] = useState('')
  const [newRouteRegion, setNewRouteRegion] = useState('')
  const [newRouteConfigStr, setNewRouteConfigStr] = useState('')
  const [newRouteConfigError, setNewRouteConfigError] = useState('')
  const [newRouteDailyCap, setNewRouteDailyCap] = useState('')
  const [newRouteMonthlyCap, setNewRouteMonthlyCap] = useState('')
  const [newRoutePiiRedaction, setNewRoutePiiRedaction] = useState(false)
  const [newRouteSemanticCache, setNewRouteSemanticCache] = useState(false)
  const [newRouteContextCompiler, setNewRouteContextCompiler] = useState(false)
  const [newRouteCompilerModel, setNewRouteCompilerModel] = useState('')
  const [newRouteRerankerModel, setNewRouteRerankerModel] = useState('flashrank')
  const [newRouteCompilerThreshold, setNewRouteCompilerThreshold] = useState('2000')
  const [newRouteCompress, setNewRouteCompress] = useState(false)
  const [newRouteCompressModel, setNewRouteCompressModel] = useState('bert-base-multilingual')
  const [newRouteCompressRate, setNewRouteCompressRate] = useState('0.5')
  const [newRouteCompressWhen, setNewRouteCompressWhen] = useState('over_budget')
  const [newRouteCompressPct, setNewRouteCompressPct] = useState('0.8')
  const [newRouteToolFilter, setNewRouteToolFilter] = useState(true)
  const [newRouteToolK, setNewRouteToolK] = useState('8')
  const [newRouteSkills, setNewRouteSkills] = useState(false)
  const [newRouteSkillK, setNewRouteSkillK] = useState('2')
  const [newRouteIntelligent, setNewRouteIntelligent] = useState(false)
  const [newRouteRoutingConfigStr, setNewRouteRoutingConfigStr] = useState(() =>
    JSON.stringify(
      {
        classifier_mode: 'hybrid',
        llm_model: 'llama3.1:8b',
        tiers: { cheap: 'gpt-4o-mini', mid: 'gpt-4o', frontier: 'o1' },
        matrix: {
          simple: { low: 'cheap', high: 'mid' },
          medium: { low: 'mid', high: 'frontier' },
          complex: { low: 'frontier', high: 'frontier' },
        },
        reasoning_effort: true,
        on_failure: 'passthrough',
      },
      null,
      2,
    ),
  )
  const [newRouteRoutingError, setNewRouteRoutingError] = useState('')
  const [newRoutePerUserRpm, setNewRoutePerUserRpm] = useState('')
  const [newRouteFallbackAliases, setNewRouteFallbackAliases] = useState('')
  const [newRouteContextFallback, setNewRouteContextFallback] = useState('')
  const [newRoutePolicyFallback, setNewRoutePolicyFallback] = useState('')
  const [newRouteMirrorAlias, setNewRouteMirrorAlias] = useState('')
  const [newRouteMirrorPct, setNewRouteMirrorPct] = useState('')
  const [creatingRoute, setCreatingRoute] = useState(false)
  const [showRouteForm, setShowRouteForm] = useState(false)
  const [routeEditState, setRouteEditState] = useState<RouteEditState | null>(null)
  const [savingRouteEdit, setSavingRouteEdit] = useState(false)
  const [routeEditError, setRouteEditError] = useState('')

  const [routingGroups, setRoutingGroups] = useState<GatewayRoutingGroup[]>([])
  const [strategyComparison, setStrategyComparison] = useState<GatewayRoutingStrategyComparisonItem[]>([])
  const [showGroupForm, setShowGroupForm] = useState(false)
  const [creatingGroup, setCreatingGroup] = useState(false)
  const [newGroupAlias, setNewGroupAlias] = useState('')
  const [newGroupName, setNewGroupName] = useState('')
  const [newGroupDescription, setNewGroupDescription] = useState('')
  const [newGroupMatchTags, setNewGroupMatchTags] = useState('')
  const [newGroupDefaultTags, setNewGroupDefaultTags] = useState('')
  const [newGroupStrategyType, setNewGroupStrategyType] = useState<GatewayRoutingGroupStrategy>('manual')
  const [newGroupStrategyConfig, setNewGroupStrategyConfig] = useState('{}')
  const [newGroupStrategyError, setNewGroupStrategyError] = useState('')
  const [groupEditState, setGroupEditState] = useState<RoutingGroupEditState | null>(null)
  const [savingGroupEdit, setSavingGroupEdit] = useState(false)
  const [groupEditError, setGroupEditError] = useState('')

  const [routingPolicies, setRoutingPolicies] = useState<RoutingPolicy[]>([])
  const [policyAlias, setPolicyAlias] = useState('')
  const [policyType, setPolicyType] = useState<RoutingPolicyType>('manual')
  const [policyConfigStr, setPolicyConfigStr] = useState('{}')
  const [creatingPolicy, setCreatingPolicy] = useState(false)
  const [policyConfigError, setPolicyConfigError] = useState('')
  const [showPolicyForm, setShowPolicyForm] = useState(false)
  const [policyEditState, setPolicyEditState] = useState<RoutingPolicyEditState | null>(null)
  const [savingPolicyEdit, setSavingPolicyEdit] = useState(false)
  const [policyEditError, setPolicyEditError] = useState('')
  const [policyAnalysis, setPolicyAnalysis] = useState<Record<string, RoutingPolicyAnalysis>>({})
  const [loadingPolicyAnalysis, setLoadingPolicyAnalysis] = useState<Record<string, boolean>>({})

  const [routingLog, setRoutingLog] = useState<GatewayRequestLog[]>([])
  const [loadingLog, setLoadingLog] = useState(false)

  // Outcome-based routing recommendations
  const [recommendations, setRecommendations] = useState<Record<string, RoutingRecommendationResponse>>({})
  const [loadingRec, setLoadingRec] = useState<Record<string, boolean>>({})
  const [expandedRec, setExpandedRec] = useState<string | null>(null)

  const [pricing, setPricing] = useState<ProviderPricingResponse[]>([])
  const [rateLimitOverview, setRateLimitOverview] = useState<GatewayRateLimitOverview | null>(null)
  const [cacheConfigs, setCacheConfigs] = useState<ResponseCacheConfigResponse[]>([])
  const [cacheStats, setCacheStats] = useState<ResponseCacheStatsResponse | null>(null)
  const [showCacheForm, setShowCacheForm] = useState(false)
  const [creatingCacheConfig, setCreatingCacheConfig] = useState(false)
  const [cacheEditState, setCacheEditState] = useState<CacheConfigEditState | null>(null)
  const [savingCacheEdit, setSavingCacheEdit] = useState(false)
  const [cacheConfigError, setCacheConfigError] = useState('')
  const [expandedCacheId, setExpandedCacheId] = useState<string | null>(null)
  const [cacheDetails, setCacheDetails] = useState<Record<string, ResponseCacheConfigResponse>>({})
  const [loadingCacheDetail, setLoadingCacheDetail] = useState<Record<string, boolean>>({})
  const [newCacheName, setNewCacheName] = useState('')
  const [newCacheEnabled, setNewCacheEnabled] = useState(true)
  const [newCacheTtlSeconds, setNewCacheTtlSeconds] = useState('3600')
  const [newCacheMaxEntries, setNewCacheMaxEntries] = useState('10000')
  const [newCacheEvictionPolicy, setNewCacheEvictionPolicy] = useState('lru')
  const [newCacheSimilarityThreshold, setNewCacheSimilarityThreshold] = useState('0.95')
  const [newCacheEmbeddingModel, setNewCacheEmbeddingModel] = useState('')
  const [newCacheScopeModels, setNewCacheScopeModels] = useState('')
  const [newCacheConfigStr, setNewCacheConfigStr] = useState('{}')
  const [loading, setLoading] = useState(true)

  const searchParams = useSearchParams()
  const router = useRouter()
  const activeTab = (TABS.includes(searchParams.get('tab') as Tab) ? searchParams.get('tab') as Tab : 'overview') as Tab
  const setTab = useCallback((t: Tab) => { router.replace(`/gateway?tab=${t}`, { scroll: false }) }, [router])

  const load = useCallback(async () => {
    if (!apiKey || !canManage) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const [routesData, groupsData, comparisonData, statsData, policiesData, pricingData, rateLimitOverviewData, cacheConfigsData, cacheStatsData] = await Promise.all([
        listGatewayRoutes(apiKey, true).catch(() => ({ items: [] })),
        listGatewayRoutingGroups(apiKey, { include_inactive: true }).catch(() => ({ items: [] })),
        getGatewayRoutingStrategyComparison(apiKey).catch(() => ({ items: [] })),
        getGatewayStats(apiKey).catch(() => ({ total_requests: 0, cache_hits: 0, cache_hit_rate: '0', avg_latency_ms: null, routes: [] })),
        listRoutingPolicies(apiKey).catch(() => ({ items: [] })),
        listProviderPricing(apiKey).catch(() => ({ items: [] })),
        getGatewayRateLimitOverview(apiKey).catch(() => null),
        getResponseCacheConfigs(apiKey).catch(() => ({ items: [], total: 0 })),
        getResponseCacheStats(apiKey).catch(() => ({
          config_count: 0,
          enabled_config_count: 0,
          total_hits: 0,
          total_misses: 0,
          hit_rate: null,
          total_savings_usd: 0,
          live_entry_count: 0,
          top_models: [],
        })),
      ])
      setGatewayRoutes(routesData.items)
      setRoutingGroups(groupsData.items)
      setStrategyComparison(comparisonData.items)
      setGatewayStats(statsData as any)
      setRoutingPolicies(policiesData.items)
      setPricing(pricingData.items)
      setRateLimitOverview(rateLimitOverviewData)
      setCacheConfigs(cacheConfigsData.items)
      setCacheStats(cacheStatsData as ResponseCacheStatsResponse)
    } catch {
      toast.error('Failed to load gateway data')
    } finally {
      setLoading(false)
    }
  }, [apiKey, canManage])

  useEffect(() => { load() }, [load])



  function getRouteFallbackAliases(route: GatewayRoute): string[] {
    const aliases = route.fallback_config?.aliases
    if (!Array.isArray(aliases)) return []
    return aliases.filter((alias): alias is string => typeof alias === 'string' && alias.trim().length > 0)
  }

  // Error-triggered fallbacks: fallback_config.fallbacks = [{ alias, on: [trigger] }].
  // Plain fallbacks only absorb transient failures; a 400/413 for a too-long prompt or a
  // content-policy refusal only falls through to a rule whose trigger matches.
  function fallbackRules(config: Record<string, unknown> | null | undefined): Record<string, unknown>[] {
    const rules = config?.fallbacks
    return Array.isArray(rules) ? rules.filter((r): r is Record<string, unknown> => !!r && typeof r === 'object') : []
  }

  function isSingleTrigger(rule: Record<string, unknown>, trigger: string): boolean {
    return Array.isArray(rule.on) && rule.on.length === 1 && rule.on[0] === trigger
  }

  function getTriggerFallback(config: Record<string, unknown> | null | undefined, trigger: string): string {
    const rule = fallbackRules(config).find((r) => isSingleTrigger(r, trigger))
    return typeof rule?.alias === 'string' ? rule.alias : ''
  }

  // Mirror (shadow) traffic: mirror_config = { alias, sample_pct (0–1) }. The UI takes a
  // percentage; the gateway samples and sends the shadow call in the background.
  function getMirror(config: Record<string, unknown> | null | undefined): { alias: string; pct: string } {
    const alias = typeof config?.alias === 'string' ? config.alias : ''
    const pct = typeof config?.sample_pct === 'number' ? String(Math.round(config.sample_pct * 1000) / 10) : ''
    return { alias, pct }
  }

  function buildMirrorConfig(alias: string, pct: string): Record<string, unknown> | null {
    const value = Number(pct)
    if (!alias.trim() || !Number.isFinite(value) || value <= 0) return null
    return { alias: alias.trim(), sample_pct: Math.min(value, 100) / 100 }
  }

  function buildFallbackConfig(
    aliasesCsv: string,
    contextAlias: string,
    policyAlias: string,
    existing: Record<string, unknown> | null,
  ): Record<string, unknown> | null {
    const aliases = parseCsvTags(aliasesCsv)
    // Keep any other rules (other triggers, per-step overrides) set through the API.
    const kept = fallbackRules(existing).filter(
      (r) => !isSingleTrigger(r, 'context_window') && !isSingleTrigger(r, 'content_policy'),
    )
    const fallbacks = [
      ...kept,
      ...(contextAlias.trim() ? [{ alias: contextAlias.trim(), on: ['context_window'] }] : []),
      ...(policyAlias.trim() ? [{ alias: policyAlias.trim(), on: ['content_policy'] }] : []),
    ]
    const config: Record<string, unknown> = { ...(existing ?? {}) }
    delete config.aliases
    delete config.fallbacks
    if (aliases.length > 0) config.aliases = aliases
    if (fallbacks.length > 0) config.fallbacks = fallbacks
    return Object.keys(config).length > 0 ? config : null
  }

  function beginCacheEdit(config: ResponseCacheConfigResponse) {
    setRouteEditState(null)
    setGroupEditState(null)
    setPolicyEditState(null)
    setCacheConfigError('')
    setCacheEditState({
      id: config.id,
      name: config.name,
      isEnabled: config.is_enabled,
      ttlSeconds: String(config.ttl_seconds),
      maxEntries: String(config.max_entries),
      evictionPolicy: config.eviction_policy,
      similarityThreshold: String(config.similarity_threshold),
      embeddingModel: config.embedding_model ?? '',
      scopeModels: config.scope_models.join(', '),
      configStr: JSON.stringify(config.config ?? {}, null, 2),
    })
  }

  function beginRouteEdit(route: GatewayRoute) {
    setGroupEditState(null)
    setPolicyEditState(null)
    setRouteEditError('')
    setRouteEditState({
      id: route.id,
      alias: route.alias,
      targetModel: route.target_model,
      baseUrl: route.base_url ?? '',
      apiKeyEnvVar: route.api_key_env_var ?? '',
      routingGroupId: route.routing_group_id ?? '',
      priority: String(route.priority),
      region: route.region ?? '',
      requiredTags: route.required_tags.join(', '),
      excludedTags: route.excluded_tags.join(', '),
      dailyCostLimitUsd: route.daily_cost_limit_usd ?? '',
      monthlyCostLimitUsd: route.monthly_cost_limit_usd ?? '',
      perUserRpmLimit: route.per_user_rpm_limit != null ? String(route.per_user_rpm_limit) : '',
      fallbackAliases: getRouteFallbackAliases(route).join(', '),
      contextWindowFallback: getTriggerFallback(route.fallback_config, 'context_window'),
      contentPolicyFallback: getTriggerFallback(route.fallback_config, 'content_policy'),
      existingFallbackConfig: route.fallback_config,
      mirrorAlias: getMirror(route.mirror_config).alias,
      mirrorSamplePct: getMirror(route.mirror_config).pct,
      routeConfigStr: route.config ? JSON.stringify(route.config, null, 2) : '{}',
      routingConfigStr: route.routing_config ? JSON.stringify(route.routing_config, null, 2) : '{}',
      piiRedactionEnabled: route.pii_redaction_enabled,
      semanticCacheEnabled: route.semantic_cache_enabled,
      contextCompilerEnabled: route.context_compiler_enabled,
      intelligentRoutingEnabled: route.intelligent_routing_enabled,
    })
  }

  async function handleCreateCacheConfig(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !newCacheName.trim()) return
    let config: Record<string, unknown> = {}
    try {
      config = JSON.parse(newCacheConfigStr || '{}')
    } catch {
      setCacheConfigError('Cache config must be valid JSON')
      return
    }
    setCreatingCacheConfig(true)
    setCacheConfigError('')
    try {
      const created = await createResponseCacheConfig(apiKey, {
        name: newCacheName.trim(),
        is_enabled: newCacheEnabled,
        ttl_seconds: parseInt(newCacheTtlSeconds, 10) || 3600,
        max_entries: parseInt(newCacheMaxEntries, 10) || 10000,
        eviction_policy: newCacheEvictionPolicy.trim() || 'lru',
        similarity_threshold: parseFloat(newCacheSimilarityThreshold) || 0.95,
        embedding_model: newCacheEmbeddingModel.trim() || null,
        scope_models: parseCsvTags(newCacheScopeModels),
        config,
      })
      setCacheConfigs((prev) => [created, ...prev])
      setNewCacheName('')
      setNewCacheEnabled(true)
      setNewCacheTtlSeconds('3600')
      setNewCacheMaxEntries('10000')
      setNewCacheEvictionPolicy('lru')
      setNewCacheSimilarityThreshold('0.95')
      setNewCacheEmbeddingModel('')
      setNewCacheScopeModels('')
      setNewCacheConfigStr('{}')
      setShowCacheForm(false)
      toast.success('Response cache profile created')
      await load()
    } catch {
      toast.error('Failed to create response cache profile')
    } finally {
      setCreatingCacheConfig(false)
    }
  }

  async function handleLoadCacheDetails(configId: string) {
    if (!apiKey) return
    if (expandedCacheId === configId) {
      setExpandedCacheId(null)
      return
    }
    setExpandedCacheId(configId)
    if (cacheDetails[configId]) return
    setLoadingCacheDetail((prev) => ({ ...prev, [configId]: true }))
    try {
      const detail = await getResponseCacheConfig(apiKey, configId)
      setCacheDetails((prev) => ({ ...prev, [configId]: detail }))
    } catch {
      toast.error('Failed to load cache profile details')
      setExpandedCacheId(null)
    } finally {
      setLoadingCacheDetail((prev) => ({ ...prev, [configId]: false }))
    }
  }

  async function handleSaveCacheEdit() {
    if (!apiKey || !cacheEditState) return
    let config: Record<string, unknown> = {}
    try {
      config = JSON.parse(cacheEditState.configStr || '{}')
    } catch {
      setCacheConfigError('Cache config must be valid JSON')
      return
    }
    setSavingCacheEdit(true)
    setCacheConfigError('')
    try {
      const updated = await updateResponseCacheConfig(apiKey, cacheEditState.id, {
        name: cacheEditState.name.trim(),
        is_enabled: cacheEditState.isEnabled,
        ttl_seconds: parseInt(cacheEditState.ttlSeconds, 10) || 3600,
        max_entries: parseInt(cacheEditState.maxEntries, 10) || 10000,
        eviction_policy: cacheEditState.evictionPolicy.trim() || 'lru',
        similarity_threshold: parseFloat(cacheEditState.similarityThreshold) || 0.95,
        embedding_model: cacheEditState.embeddingModel.trim() || null,
        scope_models: parseCsvTags(cacheEditState.scopeModels),
        config,
      })
      setCacheConfigs((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      setCacheDetails((prev) => ({ ...prev, [updated.id]: updated }))
      setCacheEditState(null)
      toast.success('Response cache profile updated')
      await load()
    } catch {
      toast.error('Failed to update response cache profile')
    } finally {
      setSavingCacheEdit(false)
    }
  }

  async function handleDeleteCacheConfig(configId: string) {
    if (!apiKey || !confirm('Delete this response cache profile?')) return
    try {
      await deleteResponseCacheConfig(apiKey, configId)
      setCacheConfigs((prev) => prev.filter((item) => item.id !== configId))
      setCacheDetails((prev) => {
        const next = { ...prev }
        delete next[configId]
        return next
      })
      if (expandedCacheId === configId) setExpandedCacheId(null)
      if (cacheEditState?.id === configId) setCacheEditState(null)
      toast.success('Response cache profile deleted')
      await load()
    } catch {
      toast.error('Failed to delete response cache profile')
    }
  }

  async function handleSaveRouteEdit() {
    if (!apiKey || !routeEditState) return
    let routeConfig: Record<string, unknown> | null = null
    let routingConfig: Record<string, unknown> | null = null
    try {
      routeConfig = routeEditState.routeConfigStr.trim() ? JSON.parse(routeEditState.routeConfigStr) : null
      routingConfig = routeEditState.routingConfigStr.trim() ? JSON.parse(routeEditState.routingConfigStr) : null
    } catch {
      setRouteEditError('Route config and routing config must be valid JSON')
      return
    }
    setSavingRouteEdit(true)
    setRouteEditError('')
    try {
      const updated = await updateGatewayRoute(apiKey, routeEditState.id, {
        alias: routeEditState.alias.trim(),
        routing_group_id: routeEditState.routingGroupId || null,
        target_model: routeEditState.targetModel.trim(),
        base_url: routeEditState.baseUrl.trim() || null,
        api_key_env_var: routeEditState.apiKeyEnvVar.trim() || null,
        priority: parseInt(routeEditState.priority, 10) || 10,
        config: routeConfig,
        daily_cost_limit_usd: routeEditState.dailyCostLimitUsd ? parseFloat(routeEditState.dailyCostLimitUsd) : null,
        monthly_cost_limit_usd: routeEditState.monthlyCostLimitUsd ? parseFloat(routeEditState.monthlyCostLimitUsd) : null,
        pii_redaction_enabled: routeEditState.piiRedactionEnabled,
        semantic_cache_enabled: routeEditState.semanticCacheEnabled,
        context_compiler_enabled: routeEditState.contextCompilerEnabled,
        intelligent_routing_enabled: routeEditState.intelligentRoutingEnabled,
        routing_config: routeEditState.intelligentRoutingEnabled ? routingConfig : null,
        mirror_config: buildMirrorConfig(routeEditState.mirrorAlias, routeEditState.mirrorSamplePct),
        per_user_rpm_limit: routeEditState.perUserRpmLimit ? parseInt(routeEditState.perUserRpmLimit, 10) : null,
        fallback_config: buildFallbackConfig(
          routeEditState.fallbackAliases,
          routeEditState.contextWindowFallback,
          routeEditState.contentPolicyFallback,
          routeEditState.existingFallbackConfig,
        ),
        required_tags: parseCsvTags(routeEditState.requiredTags),
        excluded_tags: parseCsvTags(routeEditState.excludedTags),
        region: routeEditState.region.trim() || null,
      })
      setGatewayRoutes((prev) => prev.map((route) => (route.id === updated.id ? updated : route)))
      setRouteEditState(null)
      toast.success('Gateway route updated')
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to update route'))
    } finally {
      setSavingRouteEdit(false)
    }
  }

  function beginGroupEdit(group: GatewayRoutingGroup) {
    setRouteEditState(null)
    setPolicyEditState(null)
    setGroupEditError('')
    setGroupEditState({
      id: group.id,
      alias: group.alias,
      name: group.name,
      description: group.description ?? '',
      matchTags: group.match_tags.join(', '),
      defaultTags: group.default_tags.join(', '),
      strategyType: group.strategy_type,
      strategyConfigStr: group.strategy_config ? JSON.stringify(group.strategy_config, null, 2) : '{}',
      isActive: group.is_active,
    })
  }

  async function handleSaveGroupEdit() {
    if (!apiKey || !groupEditState) return
    let strategyConfig: Record<string, unknown> | null = null
    try {
      strategyConfig = groupEditState.strategyConfigStr.trim() ? JSON.parse(groupEditState.strategyConfigStr) : null
    } catch {
      setGroupEditError('Strategy config must be valid JSON')
      return
    }
    setSavingGroupEdit(true)
    setGroupEditError('')
    try {
      await updateGatewayRoutingGroup(apiKey, groupEditState.id, {
        alias: groupEditState.alias.trim(),
        name: groupEditState.name.trim(),
        description: groupEditState.description.trim() || null,
        match_tags: parseCsvTags(groupEditState.matchTags),
        default_tags: parseCsvTags(groupEditState.defaultTags),
        strategy_type: groupEditState.strategyType,
        strategy_config: strategyConfig,
        is_active: groupEditState.isActive,
      })
      setGroupEditState(null)
      toast.success('Routing group updated')
      await load()
    } catch {
      toast.error('Failed to update routing group')
    } finally {
      setSavingGroupEdit(false)
    }
  }

  function beginPolicyEdit(policy: RoutingPolicy) {
    setRouteEditState(null)
    setGroupEditState(null)
    setPolicyEditError('')
    setPolicyEditState({
      id: policy.id,
      policyType: policy.policy_type,
      configStr: JSON.stringify(policy.config ?? {}, null, 2),
      isActive: policy.is_active,
    })
  }

  async function handleSavePolicyEdit() {
    if (!apiKey || !policyEditState) return
    let config: Record<string, unknown> = {}
    try {
      config = JSON.parse(policyEditState.configStr || '{}')
    } catch {
      setPolicyEditError('Policy config must be valid JSON')
      return
    }
    setSavingPolicyEdit(true)
    setPolicyEditError('')
    try {
      const updated = await updateRoutingPolicy(apiKey, policyEditState.id, {
        policy_type: policyEditState.policyType,
        config,
        is_active: policyEditState.isActive,
      })
      setRoutingPolicies((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      setPolicyEditState(null)
      toast.success('Routing policy updated')
    } catch {
      toast.error('Failed to update policy')
    } finally {
      setSavingPolicyEdit(false)
    }
  }

  function getDeploymentStatusTone(status: string): string {
    switch (status) {
      case 'healthy':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
      case 'degraded':
        return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
      case 'down':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
      default:
        return 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'
    }
  }

  async function handleCreateRoute(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !newRouteAlias || !newRouteTargetModel) return
    setNewRouteConfigError('')
    let config: Record<string, string> | null = null
    if (newRouteConfigStr.trim()) {
      try {
        config = JSON.parse(newRouteConfigStr.trim())
      } catch {
        setNewRouteConfigError('Config must be valid JSON')
        return
      }
    }
    let routingConfig: Record<string, unknown> | null = null
    if (newRouteIntelligent && newRouteRoutingConfigStr.trim()) {
      try {
        routingConfig = JSON.parse(newRouteRoutingConfigStr.trim())
      } catch {
        setNewRouteRoutingError('Routing config must be valid JSON')
        return
      }
    }
    setCreatingRoute(true)
    try {
      const route = await createGatewayRoute(apiKey, {
        alias: newRouteAlias.trim(),
        routing_group_id: newRouteRoutingGroupId || null,
        provider: newRouteProvider,
        target_model: newRouteTargetModel.trim(),
        base_url: newRouteBaseUrl.trim() || null,
        api_key_env_var: newRouteApiKeyEnvVar.trim() || null,
        priority: parseInt(newRoutePriority, 10) || 10,
        config,
        daily_cost_limit_usd: newRouteDailyCap ? parseFloat(newRouteDailyCap) : null,
        monthly_cost_limit_usd: newRouteMonthlyCap ? parseFloat(newRouteMonthlyCap) : null,
        pii_redaction_enabled: newRoutePiiRedaction,
        semantic_cache_enabled: newRouteSemanticCache,
        context_compiler_enabled: newRouteContextCompiler,
        context_compiler_config: newRouteContextCompiler
          ? {
              model: newRouteCompilerModel || undefined,
              reranker_model: newRouteRerankerModel,
              token_threshold: parseInt(newRouteCompilerThreshold, 10) || 0,
              tool_k: parseInt(newRouteToolK, 10) || 8,
              skill_k: parseInt(newRouteSkillK, 10) || 2,
              stages: { compress: newRouteCompress, tools: newRouteToolFilter, skills: newRouteSkills },
              ...(newRouteCompress
                ? {
                    compression_model: newRouteCompressModel,
                    compression_rate: parseFloat(newRouteCompressRate) || 0.5,
                    compress_when: newRouteCompressWhen,
                    compress_budget_pct: parseFloat(newRouteCompressPct) || 0.8,
                  }
                : {}),
            }
          : null,
        intelligent_routing_enabled: newRouteIntelligent,
        routing_config: routingConfig,
        mirror_config: buildMirrorConfig(newRouteMirrorAlias, newRouteMirrorPct),
        per_user_rpm_limit: newRoutePerUserRpm ? parseInt(newRoutePerUserRpm, 10) : null,
        fallback_config: buildFallbackConfig(newRouteFallbackAliases, newRouteContextFallback, newRoutePolicyFallback, null),
        required_tags: parseCsvTags(newRouteRequiredTags),
        excluded_tags: parseCsvTags(newRouteExcludedTags),
        region: newRouteRegion.trim() || null,
      })
      setGatewayRoutes((prev) => [...prev, route])
      setNewRouteAlias('')
      setNewRouteTargetModel('')
      setNewRouteBaseUrl('')
      setNewRouteApiKeyEnvVar('OPENAI_API_KEY')
      setNewRoutePriority('10')
      setNewRouteRoutingGroupId('')
      setNewRouteRequiredTags('')
      setNewRouteExcludedTags('')
      setNewRouteRegion('')
      setNewRouteConfigStr('')
      setNewRouteDailyCap('')
      setNewRouteMonthlyCap('')
      setNewRoutePiiRedaction(false)
      setNewRouteSemanticCache(false)
      setNewRouteContextCompiler(false)
      setNewRouteCompilerModel('')
      setNewRouteRerankerModel('flashrank')
      setNewRouteCompilerThreshold('2000')
      setNewRouteCompress(false)
      setNewRouteCompressModel('bert-base-multilingual')
      setNewRouteCompressRate('0.5')
      setNewRouteCompressWhen('over_budget')
      setNewRouteCompressPct('0.8')
      setNewRouteToolFilter(true)
      setNewRouteToolK('8')
      setNewRouteSkills(false)
      setNewRouteSkillK('2')
      setNewRouteIntelligent(false)
      setNewRouteRoutingError('')
      setNewRoutePerUserRpm('')
      setNewRouteFallbackAliases('')
      setNewRouteContextFallback('')
      setNewRoutePolicyFallback('')
      setNewRouteMirrorAlias('')
      setNewRouteMirrorPct('')
      setShowRouteForm(false)
      await load()
      toast.success('Gateway route created')
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to create gateway route'))
    } finally {
      setCreatingRoute(false)
    }
  }

  async function handleToggleRoute(route: GatewayRoute) {
    if (!apiKey) return
    try {
      const updated = await updateGatewayRoute(apiKey, route.id, { is_active: !route.is_active })
      setGatewayRoutes((prev) => prev.map((r) => (r.id === route.id ? updated : r)))
      toast.success(updated.is_active ? 'Route enabled' : 'Route disabled')
    } catch {
      toast.error('Failed to update route')
    }
  }

  async function handleToggleSemanticCache(route: GatewayRoute) {
    if (!apiKey) return
    try {
      const updated = await updateGatewayRoute(apiKey, route.id, {
        semantic_cache_enabled: !route.semantic_cache_enabled,
      })
      setGatewayRoutes((prev) => prev.map((r) => (r.id === route.id ? updated : r)))
      toast.success(updated.semantic_cache_enabled ? 'Semantic cache on' : 'Semantic cache off')
    } catch {
      toast.error('Failed to update route')
    }
  }

  async function handleToggleContextCompiler(route: GatewayRoute) {
    if (!apiKey) return
    try {
      const updated = await updateGatewayRoute(apiKey, route.id, {
        context_compiler_enabled: !route.context_compiler_enabled,
      })
      setGatewayRoutes((prev) => prev.map((r) => (r.id === route.id ? updated : r)))
      toast.success(updated.context_compiler_enabled ? 'Context compiler on' : 'Context compiler off')
    } catch {
      toast.error('Failed to update route')
    }
  }

  async function handleToggleIntelligentRouting(route: GatewayRoute) {
    if (!apiKey) return
    try {
      const updated = await updateGatewayRoute(apiKey, route.id, {
        intelligent_routing_enabled: !route.intelligent_routing_enabled,
      })
      setGatewayRoutes((prev) => prev.map((r) => (r.id === route.id ? updated : r)))
      toast.success(updated.intelligent_routing_enabled ? 'Intelligent routing on' : 'Intelligent routing off')
    } catch {
      toast.error('Failed to update route')
    }
  }

  async function handleDeleteRoute(routeId: string) {
    if (!apiKey || !confirm('Delete this gateway route?')) return
    try {
      await deleteGatewayRoute(apiKey, routeId)
      setGatewayRoutes((prev) => prev.filter((r) => r.id !== routeId))
      toast.success('Gateway route deleted')
    } catch {
      toast.error('Failed to delete route')
    }
  }

  async function handleCreateRoutingGroup(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !newGroupAlias.trim() || !newGroupName.trim()) return
    setNewGroupStrategyError('')
    let strategyConfig: Record<string, unknown> | null = null
    if (newGroupStrategyConfig.trim()) {
      try {
        strategyConfig = JSON.parse(newGroupStrategyConfig)
      } catch {
        setNewGroupStrategyError('Strategy config must be valid JSON')
        return
      }
    }
    setCreatingGroup(true)
    try {
      await createGatewayRoutingGroup(apiKey, {
        alias: newGroupAlias.trim(),
        name: newGroupName.trim(),
        description: newGroupDescription.trim() || null,
        match_tags: parseCsvTags(newGroupMatchTags),
        default_tags: parseCsvTags(newGroupDefaultTags),
        strategy_type: newGroupStrategyType,
        strategy_config: strategyConfig,
      })
      setNewGroupAlias('')
      setNewGroupName('')
      setNewGroupDescription('')
      setNewGroupMatchTags('')
      setNewGroupDefaultTags('')
      setNewGroupStrategyType('manual')
      setNewGroupStrategyConfig('{}')
      setShowGroupForm(false)
      await load()
      toast.success('Routing group created')
    } catch {
      toast.error('Failed to create routing group')
    } finally {
      setCreatingGroup(false)
    }
  }

  async function handleToggleRoutingGroup(group: GatewayRoutingGroup) {
    if (!apiKey) return
    try {
      await updateGatewayRoutingGroup(apiKey, group.id, { is_active: !group.is_active })
      await load()
      toast.success(group.is_active ? 'Routing group disabled' : 'Routing group enabled')
    } catch {
      toast.error('Failed to update routing group')
    }
  }

  async function handleDeleteRoutingGroup(groupId: string) {
    if (!apiKey || !confirm('Delete this routing group? Routes will be detached.')) return
    try {
      await deleteGatewayRoutingGroup(apiKey, groupId)
      await load()
      toast.success('Routing group deleted')
    } catch {
      toast.error('Failed to delete routing group')
    }
  }

  async function handleCreatePolicy(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !policyAlias) return
    setPolicyConfigError('')
    let config: Record<string, unknown> = {}
    try {
      config = JSON.parse(policyConfigStr || '{}')
    } catch {
      setPolicyConfigError('Config must be valid JSON')
      return
    }
    setCreatingPolicy(true)
    try {
      const p = await createRoutingPolicy(apiKey, { alias: policyAlias.trim(), policy_type: policyType, config })
      setRoutingPolicies((prev) => [...prev, p])
      setPolicyAlias('')
      setPolicyConfigStr('{}')
      setShowPolicyForm(false)
      toast.success('Routing policy created')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      toast.error(msg.includes('409') ? `A policy for alias '${policyAlias}' already exists` : 'Failed to create policy')
    } finally {
      setCreatingPolicy(false)
    }
  }

  async function handleTogglePolicy(p: RoutingPolicy) {
    if (!apiKey) return
    try {
      const updated = await updateRoutingPolicy(apiKey, p.id, { is_active: !p.is_active })
      setRoutingPolicies((prev) => prev.map((x) => (x.id === p.id ? updated : x)))
    } catch {
      toast.error('Failed to update policy')
    }
  }

  async function handleDeletePolicy(id: string) {
    if (!apiKey || !confirm('Delete this routing policy?')) return
    try {
      await deleteRoutingPolicy(apiKey, id)
      setRoutingPolicies((prev) => prev.filter((p) => p.id !== id))
      toast.success('Policy deleted')
    } catch {
      toast.error('Failed to delete policy')
    }
  }

  async function handleLoadPolicyAnalysis(policyId: string) {
    if (!apiKey) return
    setLoadingPolicyAnalysis((prev) => ({ ...prev, [policyId]: true }))
    try {
      const data = await getRoutingPolicyAnalysis(apiKey, policyId)
      setPolicyAnalysis((prev) => ({ ...prev, [policyId]: data }))
      if (data.auto_promoted) {
        await load()
      }
    } catch {
      toast.error('Failed to load policy analysis')
    } finally {
      setLoadingPolicyAnalysis((prev) => ({ ...prev, [policyId]: false }))
    }
  }

  async function handlePromotePolicy(policyId: string) {
    if (!apiKey) return
    try {
      const result = await promoteRoutingPolicyWinner(apiKey, policyId)
      toast.success(result.summary)
      await load()
      await handleLoadPolicyAnalysis(policyId)
    } catch {
      toast.error('Failed to promote winner')
    }
  }

  async function handleAdvanceCanary(policyId: string) {
    if (!apiKey) return
    try {
      const result = await advanceCanaryRollout(apiKey, policyId)
      toast.success(result.summary)
      await load()
    } catch {
      toast.error('Failed to advance canary rollout')
    }
  }

  async function handleRollbackPolicy(policyId: string) {
    if (!apiKey) return
    try {
      const result = await rollbackRoutingPolicy(apiKey, policyId)
      toast.success(result.summary)
      await load()
      await handleLoadPolicyAnalysis(policyId)
    } catch {
      toast.error('Failed to roll back policy')
    }
  }

  async function handleLoadRecommendation(alias: string) {
    if (!apiKey) return
    if (expandedRec === alias) {
      setExpandedRec(null)
      return
    }
    setExpandedRec(alias)
    if (recommendations[alias]) return  // already loaded
    setLoadingRec((prev) => ({ ...prev, [alias]: true }))
    try {
      const rec = await getRoutingRecommendation(apiKey, alias, { window_days: 30, min_sample_size: 1 })
      setRecommendations((prev) => ({ ...prev, [alias]: rec }))
    } catch {
      toast.error(`Failed to load recommendation for '${alias}'`)
      setExpandedRec(null)
    } finally {
      setLoadingRec((prev) => ({ ...prev, [alias]: false }))
    }
  }

  async function handleLoadRoutingLog() {
    if (!apiKey) return
    setLoadingLog(true)
    try {
      const data = await listGatewayRequests(apiKey, { limit: 50 })
      setRoutingLog(data.items)
    } catch {
      toast.error('Failed to load routing log')
    } finally {
      setLoadingLog(false)
    }
  }

  return {
    session,
    apiKey,
    isOrgAdmin,
    isPlatformAdmin,
    canManage,
    gatewayRoutes,
    setGatewayRoutes,
    gatewayStats,
    setGatewayStats,
    newRouteAlias,
    setNewRouteAlias,
    newRouteProvider,
    setNewRouteProvider,
    newRouteTargetModel,
    setNewRouteTargetModel,
    newRouteBaseUrl,
    setNewRouteBaseUrl,
    newRouteApiKeyEnvVar,
    setNewRouteApiKeyEnvVar,
    newRoutePriority,
    setNewRoutePriority,
    newRouteRoutingGroupId,
    setNewRouteRoutingGroupId,
    newRouteRequiredTags,
    setNewRouteRequiredTags,
    newRouteExcludedTags,
    setNewRouteExcludedTags,
    newRouteRegion,
    setNewRouteRegion,
    newRouteConfigStr,
    setNewRouteConfigStr,
    newRouteConfigError,
    setNewRouteConfigError,
    newRouteDailyCap,
    setNewRouteDailyCap,
    newRouteMonthlyCap,
    setNewRouteMonthlyCap,
    newRoutePiiRedaction,
    setNewRoutePiiRedaction,
    newRouteSemanticCache,
    setNewRouteSemanticCache,
    newRouteContextCompiler,
    setNewRouteContextCompiler,
    newRouteCompilerModel,
    setNewRouteCompilerModel,
    newRouteRerankerModel,
    setNewRouteRerankerModel,
    newRouteCompilerThreshold,
    setNewRouteCompilerThreshold,
    newRouteCompress,
    setNewRouteCompress,
    newRouteCompressModel,
    setNewRouteCompressModel,
    newRouteCompressRate,
    setNewRouteCompressRate,
    newRouteCompressWhen,
    setNewRouteCompressWhen,
    newRouteCompressPct,
    setNewRouteCompressPct,
    newRouteToolFilter,
    setNewRouteToolFilter,
    newRouteToolK,
    setNewRouteToolK,
    newRouteSkills,
    setNewRouteSkills,
    newRouteSkillK,
    setNewRouteSkillK,
    newRouteIntelligent,
    setNewRouteIntelligent,
    newRouteRoutingConfigStr,
    setNewRouteRoutingConfigStr,
    newRouteRoutingError,
    setNewRouteRoutingError,
    newRoutePerUserRpm,
    setNewRoutePerUserRpm,
    newRouteFallbackAliases,
    setNewRouteFallbackAliases,
    newRouteContextFallback,
    setNewRouteContextFallback,
    newRoutePolicyFallback,
    setNewRoutePolicyFallback,
    newRouteMirrorAlias,
    setNewRouteMirrorAlias,
    newRouteMirrorPct,
    setNewRouteMirrorPct,
    creatingRoute,
    setCreatingRoute,
    showRouteForm,
    setShowRouteForm,
    routeEditState,
    setRouteEditState,
    savingRouteEdit,
    setSavingRouteEdit,
    routeEditError,
    setRouteEditError,
    routingGroups,
    setRoutingGroups,
    strategyComparison,
    setStrategyComparison,
    showGroupForm,
    setShowGroupForm,
    creatingGroup,
    setCreatingGroup,
    newGroupAlias,
    setNewGroupAlias,
    newGroupName,
    setNewGroupName,
    newGroupDescription,
    setNewGroupDescription,
    newGroupMatchTags,
    setNewGroupMatchTags,
    newGroupDefaultTags,
    setNewGroupDefaultTags,
    newGroupStrategyType,
    setNewGroupStrategyType,
    newGroupStrategyConfig,
    setNewGroupStrategyConfig,
    newGroupStrategyError,
    setNewGroupStrategyError,
    groupEditState,
    setGroupEditState,
    savingGroupEdit,
    setSavingGroupEdit,
    groupEditError,
    setGroupEditError,
    routingPolicies,
    setRoutingPolicies,
    policyAlias,
    setPolicyAlias,
    policyType,
    setPolicyType,
    policyConfigStr,
    setPolicyConfigStr,
    creatingPolicy,
    setCreatingPolicy,
    policyConfigError,
    setPolicyConfigError,
    showPolicyForm,
    setShowPolicyForm,
    policyEditState,
    setPolicyEditState,
    savingPolicyEdit,
    setSavingPolicyEdit,
    policyEditError,
    setPolicyEditError,
    policyAnalysis,
    setPolicyAnalysis,
    loadingPolicyAnalysis,
    setLoadingPolicyAnalysis,
    routingLog,
    setRoutingLog,
    loadingLog,
    setLoadingLog,
    recommendations,
    setRecommendations,
    loadingRec,
    setLoadingRec,
    expandedRec,
    setExpandedRec,
    pricing,
    setPricing,
    rateLimitOverview,
    setRateLimitOverview,
    cacheConfigs,
    setCacheConfigs,
    cacheStats,
    setCacheStats,
    showCacheForm,
    setShowCacheForm,
    creatingCacheConfig,
    setCreatingCacheConfig,
    cacheEditState,
    setCacheEditState,
    savingCacheEdit,
    setSavingCacheEdit,
    cacheConfigError,
    setCacheConfigError,
    expandedCacheId,
    setExpandedCacheId,
    cacheDetails,
    setCacheDetails,
    loadingCacheDetail,
    setLoadingCacheDetail,
    newCacheName,
    setNewCacheName,
    newCacheEnabled,
    setNewCacheEnabled,
    newCacheTtlSeconds,
    setNewCacheTtlSeconds,
    newCacheMaxEntries,
    setNewCacheMaxEntries,
    newCacheEvictionPolicy,
    setNewCacheEvictionPolicy,
    newCacheSimilarityThreshold,
    setNewCacheSimilarityThreshold,
    newCacheEmbeddingModel,
    setNewCacheEmbeddingModel,
    newCacheScopeModels,
    setNewCacheScopeModels,
    newCacheConfigStr,
    setNewCacheConfigStr,
    loading,
    setLoading,
    searchParams,
    router,
    activeTab,
    setTab,
    load,
    getRouteFallbackAliases,
    fallbackRules,
    isSingleTrigger,
    getTriggerFallback,
    getMirror,
    buildMirrorConfig,
    buildFallbackConfig,
    beginCacheEdit,
    beginRouteEdit,
    handleCreateCacheConfig,
    handleLoadCacheDetails,
    handleSaveCacheEdit,
    handleDeleteCacheConfig,
    handleSaveRouteEdit,
    beginGroupEdit,
    handleSaveGroupEdit,
    beginPolicyEdit,
    handleSavePolicyEdit,
    getDeploymentStatusTone,
    handleCreateRoute,
    handleToggleRoute,
    handleToggleSemanticCache,
    handleToggleContextCompiler,
    handleToggleIntelligentRouting,
    handleDeleteRoute,
    handleCreateRoutingGroup,
    handleToggleRoutingGroup,
    handleDeleteRoutingGroup,
    handleCreatePolicy,
    handleTogglePolicy,
    handleDeletePolicy,
    handleLoadPolicyAnalysis,
    handlePromotePolicy,
    handleAdvanceCanary,
    handleRollbackPolicy,
    handleLoadRecommendation,
    handleLoadRoutingLog,
  }
}

export type GatewayState = ReturnType<typeof useGatewayState>

export const GatewayContext = createContext<GatewayState | null>(null)

export function useGateway(): GatewayState {
  const value = useContext(GatewayContext)
  if (!value) throw new Error('useGateway must be used inside GatewayContext')
  return value
}
