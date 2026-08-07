'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  Network, RefreshCw, Plus, Trash2, Activity,
  ChevronDown, ChevronUp, BarChart2, TrendingDown, Sparkles,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import {
  listGatewayRoutes, createGatewayRoute, updateGatewayRoute, deleteGatewayRoute,
  listGatewayRoutingGroups, createGatewayRoutingGroup, updateGatewayRoutingGroup, deleteGatewayRoutingGroup, getGatewayRoutingStrategyComparison,
  getGatewayStats, listRoutingPolicies, createRoutingPolicy, updateRoutingPolicy, getRoutingPolicyAnalysis, promoteRoutingPolicyWinner, advanceCanaryRollout, rollbackRoutingPolicy,
  deleteRoutingPolicy, listGatewayRequests, listProviderPricing, getRoutingRecommendation,
  getFlywheelSettings, updateFlywheelSettings, listFlywheelRecommendations,
  applyFlywheelRecommendation, dismissFlywheelRecommendation, runFlywheel,
  listGatewayPassThroughEndpoints, createGatewayPassThroughEndpoint, updateGatewayPassThroughEndpoint, deleteGatewayPassThroughEndpoint, testGatewayPassThroughEndpoint, listGatewayPassThroughStats, getGatewayBenchmarkComparison,
} from '@/lib/api'
import type {
  GatewayRoute, GatewayRoutingGroup, GatewayRoutingGroupStrategy, GatewayRoutingStrategyComparisonItem, GatewayStats, GatewayRequestLog,
  RoutingPolicy, RoutingPolicyAnalysis, RoutingPolicyType, ProviderPricingResponse,
  RoutingRecommendationResponse,
  FlywheelSettings, FlywheelRecommendation, GatewayPassThroughEndpoint, GatewayPassThroughEndpointStats, GatewayPassThroughTestResult, GatewayBenchmarkComparisonItem,
} from '@/types/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

function parseCsvTags(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export default function GatewayPage() {
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
  const [creatingRoute, setCreatingRoute] = useState(false)
  const [showRouteForm, setShowRouteForm] = useState(false)

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

  const [routingPolicies, setRoutingPolicies] = useState<RoutingPolicy[]>([])
  const [policyAlias, setPolicyAlias] = useState('')
  const [policyType, setPolicyType] = useState<RoutingPolicyType>('manual')
  const [policyConfigStr, setPolicyConfigStr] = useState('{}')
  const [creatingPolicy, setCreatingPolicy] = useState(false)
  const [policyConfigError, setPolicyConfigError] = useState('')
  const [showPolicyForm, setShowPolicyForm] = useState(false)
  const [policyAnalysis, setPolicyAnalysis] = useState<Record<string, RoutingPolicyAnalysis>>({})
  const [loadingPolicyAnalysis, setLoadingPolicyAnalysis] = useState<Record<string, boolean>>({})

  const [routingLog, setRoutingLog] = useState<GatewayRequestLog[]>([])
  const [loadingLog, setLoadingLog] = useState(false)

  // Outcome-based routing recommendations
  const [recommendations, setRecommendations] = useState<Record<string, RoutingRecommendationResponse>>({})
  const [loadingRec, setLoadingRec] = useState<Record<string, boolean>>({})
  const [expandedRec, setExpandedRec] = useState<string | null>(null)

  const [pricing, setPricing] = useState<ProviderPricingResponse[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!apiKey || !canManage) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const [routesData, groupsData, comparisonData, statsData, policiesData, pricingData] = await Promise.all([
        listGatewayRoutes(apiKey, true).catch(() => ({ items: [] })),
        listGatewayRoutingGroups(apiKey, { include_inactive: true }).catch(() => ({ items: [] })),
        getGatewayRoutingStrategyComparison(apiKey).catch(() => ({ items: [] })),
        getGatewayStats(apiKey).catch(() => ({ total_requests: 0, cache_hits: 0, cache_hit_rate: '0', avg_latency_ms: null, routes: [] })),
        listRoutingPolicies(apiKey).catch(() => ({ items: [] })),
        listProviderPricing(apiKey).catch(() => ({ items: [] })),
      ])
      setGatewayRoutes(routesData.items)
      setRoutingGroups(groupsData.items)
      setStrategyComparison(comparisonData.items)
      setGatewayStats(statsData as any)
      setRoutingPolicies(policiesData.items)
      setPricing(pricingData.items)
    } catch {
      toast.error('Failed to load gateway data')
    } finally {
      setLoading(false)
    }
  }, [apiKey, canManage])

  useEffect(() => { load() }, [load])

  if (!canManage) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Model Gateway</h1>
        <p className="mt-4 text-sm text-slate-500">Model Gateway configuration is an organization-admin function.</p>
      </div>
    )
  }

  function getRouteFallbackAliases(route: GatewayRoute): string[] {
    const aliases = route.fallback_config?.aliases
    if (!Array.isArray(aliases)) return []
    return aliases.filter((alias): alias is string => typeof alias === 'string' && alias.trim().length > 0)
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
    const fallbackAliases = newRouteFallbackAliases
      .split(',')
      .map((alias) => alias.trim())
      .filter(Boolean)
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
        per_user_rpm_limit: newRoutePerUserRpm ? parseInt(newRoutePerUserRpm, 10) : null,
        fallback_config: fallbackAliases.length > 0 ? { aliases: fallbackAliases } : null,
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
      setShowRouteForm(false)
      await load()
      toast.success('Gateway route created')
    } catch {
      toast.error('Failed to create gateway route')
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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <RefreshCw className="h-5 w-5 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Network className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            <h1 className="text-2xl font-bold tracking-tight dark:text-white">Model Gateway</h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            OpenAI-compatible proxy with caching, fallback, and intelligent routing. Point your app&apos;s{' '}
            <code className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">base_url</code> to{' '}
            <code className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">/gateway</code>.
          </p>
        </div>
        <button
          onClick={load}
          className="shrink-0 flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      {/* Stats strip */}
      {gatewayStats && gatewayStats.total_requests > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: 'Total Requests', value: gatewayStats.total_requests.toLocaleString() },
            { label: 'Cache Hits', value: gatewayStats.cache_hits.toLocaleString() },
            { label: 'Cache Hit Rate', value: `${(parseFloat(gatewayStats.cache_hit_rate) * 100).toFixed(1)}%` },
            { label: 'Avg Latency', value: gatewayStats.avg_latency_ms ? `${parseFloat(gatewayStats.avg_latency_ms).toFixed(0)}ms` : '—' },
          ].map((s) => (
            <div key={s.label} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-4 py-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">{s.label}</p>
              <p className="text-xl font-semibold dark:text-white mt-0.5">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Routes ── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold dark:text-white">Routing Groups</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Independent group state for tagged traffic, default tags for untagged requests, and per-group routing strategy.
            </p>
          </div>
          <button
            onClick={() => setShowGroupForm((value) => !value)}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
          >
            {showGroupForm ? <ChevronUp className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
            {showGroupForm ? 'Cancel' : 'Add Group'}
          </button>
        </div>

        {showGroupForm && (
          <form onSubmit={handleCreateRoutingGroup} className="grid gap-3 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-900/10 p-4 sm:grid-cols-2 lg:grid-cols-3">
            <input value={newGroupAlias} onChange={(e) => setNewGroupAlias(e.target.value)} className={inputCls} placeholder="Alias (e.g. gpt-4o)" required />
            <input value={newGroupName} onChange={(e) => setNewGroupName(e.target.value)} className={inputCls} placeholder="Group name" required />
            <select value={newGroupStrategyType} onChange={(e) => setNewGroupStrategyType(e.target.value as GatewayRoutingGroupStrategy)} className={inputCls}>
              <option value="manual">manual</option>
              <option value="latency_optimized">latency_optimized</option>
              <option value="round_robin">round_robin</option>
            </select>
            <input value={newGroupMatchTags} onChange={(e) => setNewGroupMatchTags(e.target.value)} className={inputCls} placeholder="Match tags (csv)" />
            <input value={newGroupDefaultTags} onChange={(e) => setNewGroupDefaultTags(e.target.value)} className={inputCls} placeholder="Default tags (csv)" />
            <input value={newGroupDescription} onChange={(e) => setNewGroupDescription(e.target.value)} className={inputCls} placeholder="Description" />
            <textarea value={newGroupStrategyConfig} onChange={(e) => { setNewGroupStrategyConfig(e.target.value); setNewGroupStrategyError('') }} className={`${inputCls} min-h-[96px] font-mono text-xs sm:col-span-2 lg:col-span-3`} placeholder='{"notes":"optional"}' />
            {newGroupStrategyError && <p className="text-xs text-red-500 sm:col-span-2 lg:col-span-3">{newGroupStrategyError}</p>}
            <div className="sm:col-span-2 lg:col-span-3">
              <button type="submit" disabled={creatingGroup} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {creatingGroup ? 'Creating…' : 'Create routing group'}
              </button>
            </div>
          </form>
        )}

        <div className="grid gap-3 lg:grid-cols-2">
          {routingGroups.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400 lg:col-span-2">
              No routing groups configured yet.
            </div>
          ) : routingGroups.map((group) => (
            <div key={group.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm dark:text-slate-100">{group.alias}</span>
                    <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">{group.name}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">{group.strategy_type}</span>
                    <button onClick={() => void handleToggleRoutingGroup(group)} className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${group.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                      {group.is_active ? 'active' : 'inactive'}
                    </button>
                  </div>
                  {group.description && <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{group.description}</p>}
                  <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                    <span className="rounded-full bg-sky-100 px-2 py-0.5 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">match: {group.match_tags.length ? group.match_tags.join(', ') : 'none'}</span>
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">default: {group.default_tags.length ? group.default_tags.join(', ') : 'none'}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600 dark:bg-slate-700 dark:text-slate-300">routes: {group.route_count}</span>
                  </div>
                </div>
                <button onClick={() => void handleDeleteRoutingGroup(group.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold dark:text-white">Routing Strategy Comparison</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Compare routing groups by throughput, cache performance, latency, and errors.
          </p>
        </div>
        {strategyComparison.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
            Comparison data will appear after requests hit grouped routes.
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {strategyComparison.map((item) => (
              <div key={`${item.alias}-${item.group_name}`} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-mono text-sm dark:text-slate-100">{item.alias}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{item.group_name}</p>
                  </div>
                  <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-semibold text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">{item.strategy_type}</span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900/40">
                    <p className="text-slate-400">Requests</p>
                    <p className="font-semibold dark:text-white">{item.total_requests.toLocaleString()}</p>
                  </div>
                  <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900/40">
                    <p className="text-slate-400">Active routes</p>
                    <p className="font-semibold dark:text-white">{item.active_routes}</p>
                  </div>
                  <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900/40">
                    <p className="text-slate-400">Cache hit</p>
                    <p className="font-semibold dark:text-white">{(parseFloat(item.cache_hit_rate) * 100).toFixed(1)}%</p>
                  </div>
                  <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900/40">
                    <p className="text-slate-400">Errors</p>
                    <p className="font-semibold dark:text-white">{(parseFloat(item.error_rate) * 100).toFixed(1)}%</p>
                  </div>
                </div>
                <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                  Avg latency: {item.avg_latency_ms ? `${parseFloat(item.avg_latency_ms).toFixed(0)}ms` : '—'}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold dark:text-white">Provider Routes</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Each route maps an alias to a provider model with priority and fallback.</p>
          </div>
          {canManage && (
            <button
              onClick={() => setShowRouteForm((v) => !v)}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
            >
              {showRouteForm ? <ChevronUp className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              {showRouteForm ? 'Cancel' : 'Add Route'}
            </button>
          )}
        </div>

        {showRouteForm && canManage && (
          <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-900/10 p-4">
            <form onSubmit={handleCreateRoute} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 dark:text-gray-400">Alias (route name) *</label>
                <input type="text" placeholder="e.g. gpt-4o" value={newRouteAlias} onChange={(e) => setNewRouteAlias(e.target.value)} className={inputCls} required />
              </div>
              <div className="flex flex-col gap-1 sm:col-span-2">
                <label className="text-xs text-gray-500 dark:text-gray-400">Provider &amp; Model *</label>
                <select
                  className={inputCls}
                  value={`${newRouteProvider}::${newRouteTargetModel}`}
                  onChange={(e) => {
                    const [prov, model] = e.target.value.split('::')
                    setNewRouteProvider(prov)
                    setNewRouteTargetModel(model ?? '')
                  }}
                  required
                >
                  <option value="::">— select model —</option>
                  {pricing.length > 0 ? (
                    (() => {
                      const grouped: Record<string, typeof pricing> = {}
                      pricing.forEach((p) => { ;(grouped[p.provider] ??= []).push(p) })
                      return Object.entries(grouped).map(([prov, models]) => (
                        <optgroup key={prov} label={prov}>
                          {models.map((m) => (
                            <option key={m.id} value={`${m.provider}::${m.model}`}>{m.model}</option>
                          ))}
                        </optgroup>
                      ))
                    })()
                  ) : (
                    <>
                      <optgroup label="openai">
                        <option value="openai::gpt-4o">gpt-4o</option>
                        <option value="openai::gpt-4o-mini">gpt-4o-mini</option>
                      </optgroup>
                      <optgroup label="anthropic">
                        <option value="anthropic::claude-sonnet-4-6">claude-sonnet-4-6</option>
                      </optgroup>
                      <optgroup label="azure">
                        <option value="azure::gpt-4o">gpt-4o (Azure)</option>
                        <option value="azure::gpt-4o-mini">gpt-4o-mini (Azure)</option>
                      </optgroup>
                      <optgroup label="bedrock">
                        <option value="bedrock::anthropic.claude-3-5-sonnet-20241022-v2:0">claude-3-5-sonnet (Bedrock)</option>
                        <option value="bedrock::amazon.nova-pro-v1:0">nova-pro (Bedrock)</option>
                        <option value="bedrock::meta.llama3-2-90b-instruct-v1:0">llama3-2-90b (Bedrock)</option>
                      </optgroup>
                      <optgroup label="vertex">
                        <option value="vertex::gemini-2.0-flash">gemini-2.0-flash (Vertex)</option>
                        <option value="vertex::gemini-1.5-pro">gemini-1.5-pro (Vertex)</option>
                      </optgroup>
                    </>
                  )}
                </select>
              </div>
              <input type="text" placeholder="Base URL (optional)" value={newRouteBaseUrl} onChange={(e) => setNewRouteBaseUrl(e.target.value)} className={inputCls} />
              <input type="text" placeholder="API key env var (e.g. OPENAI_API_KEY)" value={newRouteApiKeyEnvVar} onChange={(e) => setNewRouteApiKeyEnvVar(e.target.value)} className={inputCls} />
              <select value={newRouteRoutingGroupId} onChange={(e) => setNewRouteRoutingGroupId(e.target.value)} className={inputCls}>
                <option value="">No routing group</option>
                {routingGroups
                  .filter((group) => group.alias === newRouteAlias.trim() || newRouteAlias.trim().length === 0)
                  .map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.alias} / {group.name}
                    </option>
                  ))}
              </select>
              <div className="flex flex-col gap-1 sm:col-span-2 lg:col-span-3">
                <label className="text-xs text-gray-500 dark:text-gray-400">
                  Provider Config JSON <span className="text-gray-400">(optional — Azure: deployment_name/api_version; Bedrock: region; Vertex: project/location)</span>
                </label>
                <textarea
                  placeholder='e.g. {"deployment_name": "my-gpt4o", "api_version": "2024-02-01"}'
                  value={newRouteConfigStr}
                  onChange={(e) => { setNewRouteConfigStr(e.target.value); setNewRouteConfigError('') }}
                  className={`${inputCls} min-h-[60px] resize-y font-mono text-xs`}
                  rows={2}
                />
                {newRouteConfigError && <p className="text-xs text-red-500">{newRouteConfigError}</p>}
              </div>
              <div className="flex items-center gap-2">
                <input type="number" placeholder="Priority" value={newRoutePriority} onChange={(e) => setNewRoutePriority(e.target.value)} className={`w-24 ${inputCls}`} min={1} max={100} />
              </div>
              <input type="text" placeholder="Region (e.g. us-east-1)" value={newRouteRegion} onChange={(e) => setNewRouteRegion(e.target.value)} className={inputCls} />
              <input type="text" placeholder="Required tags (csv)" value={newRouteRequiredTags} onChange={(e) => setNewRouteRequiredTags(e.target.value)} className={inputCls} />
              <input type="text" placeholder="Excluded tags (csv)" value={newRouteExcludedTags} onChange={(e) => setNewRouteExcludedTags(e.target.value)} className={inputCls} />
              {/* Runtime controls row */}
              <div className="sm:col-span-2 lg:col-span-3 border-t border-indigo-100 dark:border-indigo-900 pt-3 mt-1">
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">Runtime Controls</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-500 dark:text-gray-400">Daily Cost Cap (USD)</label>
                    <input type="number" placeholder="e.g. 10.00" step="0.01" min="0" value={newRouteDailyCap} onChange={(e) => setNewRouteDailyCap(e.target.value)} className={inputCls} />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-500 dark:text-gray-400">Monthly Cost Cap (USD)</label>
                    <input type="number" placeholder="e.g. 100.00" step="0.01" min="0" value={newRouteMonthlyCap} onChange={(e) => setNewRouteMonthlyCap(e.target.value)} className={inputCls} />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-500 dark:text-gray-400">Per-User RPM Limit</label>
                    <input type="number" placeholder="e.g. 60" min="1" value={newRoutePerUserRpm} onChange={(e) => setNewRoutePerUserRpm(e.target.value)} className={inputCls} />
                  </div>
                  <div className="flex flex-col gap-1 sm:col-span-2">
                    <label className="text-xs text-gray-500 dark:text-gray-400">Fallback Chain Aliases</label>
                    <input
                      type="text"
                      placeholder="e.g. gpt-4o-mini, gpt-4.1-mini"
                      value={newRouteFallbackAliases}
                      onChange={(e) => setNewRouteFallbackAliases(e.target.value)}
                      className={inputCls}
                    />
                    <p className="text-[11px] text-slate-400 dark:text-slate-500">
                      Comma-separated route aliases to try if this endpoint is unhealthy or fails.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 mt-4">
                    <input
                      id="pii-redact"
                      type="checkbox"
                      checked={newRoutePiiRedaction}
                      onChange={(e) => setNewRoutePiiRedaction(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <label htmlFor="pii-redact" className="text-xs text-gray-600 dark:text-gray-300 cursor-pointer">PII Redaction</label>
                  </div>
                  <div className="flex items-center gap-2 mt-4">
                    <input
                      id="semantic-cache"
                      type="checkbox"
                      checked={newRouteSemanticCache}
                      onChange={(e) => setNewRouteSemanticCache(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <label htmlFor="semantic-cache" className="text-xs text-gray-600 dark:text-gray-300 cursor-pointer" title="Also serve near-duplicate prompts from the semantic cache">Semantic Cache</label>
                  </div>
                  <div className="flex items-center gap-2 mt-4">
                    <input
                      id="context-compiler"
                      type="checkbox"
                      checked={newRouteContextCompiler}
                      onChange={(e) => setNewRouteContextCompiler(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <label htmlFor="context-compiler" className="text-xs text-gray-600 dark:text-gray-300 cursor-pointer" title="Shrink oversized requests before routing: dedup, tool-output compression, rerank, compaction">Context Compiler</label>
                  </div>
                  {newRouteContextCompiler && (
                    <div className="mt-2 flex flex-col gap-2 rounded-lg border border-indigo-200 dark:border-indigo-800 p-2">
                      <div className="flex flex-col gap-1">
                        <label className="text-[11px] text-gray-500 dark:text-gray-400">Compaction model (local)</label>
                        <select className={inputCls} value={newRouteCompilerModel} onChange={(e) => setNewRouteCompilerModel(e.target.value)}>
                          <option value="">— default —</option>
                          {pricing.filter((p) => ['ollama', 'vllm', 'local'].includes(p.provider)).map((m) => (
                            <option key={m.id} value={m.model}>{m.model}</option>
                          ))}
                        </select>
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[11px] text-gray-500 dark:text-gray-400">Reranker model</label>
                        <select className={inputCls} value={newRouteRerankerModel} onChange={(e) => setNewRouteRerankerModel(e.target.value)}>
                          <option value="flashrank">flashrank (fast, default)</option>
                          <option value="bge-reranker-base">BGE reranker (quality)</option>
                          <option value="jina-tiny">jina tiny</option>
                        </select>
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[11px] text-gray-500 dark:text-gray-400">Engage threshold (tokens · 0 = always)</label>
                        <input type="number" min="0" value={newRouteCompilerThreshold} onChange={(e) => setNewRouteCompilerThreshold(e.target.value)} className={inputCls} />
                      </div>
                      <div className="flex items-center gap-2 border-t border-indigo-200 dark:border-indigo-800 pt-2">
                        <input id="tool-filter" type="checkbox" checked={newRouteToolFilter} onChange={(e) => setNewRouteToolFilter(e.target.checked)} className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                        <label htmlFor="tool-filter" className="text-[11px] text-gray-600 dark:text-gray-300 cursor-pointer" title="Keep only the tools relevant to the request">Tool filtering</label>
                        {newRouteToolFilter && (
                          <input type="number" min="1" value={newRouteToolK} onChange={(e) => setNewRouteToolK(e.target.value)} className={`w-16 ${inputCls}`} title="Keep top-k tools" />
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <input id="skills" type="checkbox" checked={newRouteSkills} onChange={(e) => setNewRouteSkills(e.target.checked)} className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                        <label htmlFor="skills" className="text-[11px] text-gray-600 dark:text-gray-300 cursor-pointer" title="Inject matched skill bodies from the registry">Skill injection</label>
                        {newRouteSkills && (
                          <input type="number" min="1" value={newRouteSkillK} onChange={(e) => setNewRouteSkillK(e.target.value)} className={`w-16 ${inputCls}`} title="Max skills injected" />
                        )}
                      </div>
                      <div className="flex items-center gap-2 border-t border-indigo-200 dark:border-indigo-800 pt-2">
                        <input
                          id="compress"
                          type="checkbox"
                          checked={newRouteCompress}
                          onChange={(e) => setNewRouteCompress(e.target.checked)}
                          className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <label htmlFor="compress" className="text-[11px] text-gray-600 dark:text-gray-300 cursor-pointer" title="LLMLingua-2 prompt compression — lossy, opt-in">Prompt compression (LLMLingua-2)</label>
                      </div>
                      {newRouteCompress && (
                        <>
                          <div className="flex flex-col gap-1">
                            <label className="text-[11px] text-gray-500 dark:text-gray-400">Compression model</label>
                            <select className={inputCls} value={newRouteCompressModel} onChange={(e) => setNewRouteCompressModel(e.target.value)}>
                              <option value="bert-base-multilingual">bert-base-multilingual (fast, default)</option>
                              <option value="xlm-roberta-large">xlm-roberta-large (quality)</option>
                            </select>
                          </div>
                          <div className="flex flex-col gap-1">
                            <label className="text-[11px] text-gray-500 dark:text-gray-400">Keep rate (0.1–1.0 · lower = more aggressive)</label>
                            <input type="number" min="0.1" max="1" step="0.05" value={newRouteCompressRate} onChange={(e) => setNewRouteCompressRate(e.target.value)} className={inputCls} />
                          </div>
                          <div className="flex flex-col gap-1">
                            <label className="text-[11px] text-gray-500 dark:text-gray-400">Compress when</label>
                            <select className={inputCls} value={newRouteCompressWhen} onChange={(e) => setNewRouteCompressWhen(e.target.value)}>
                              <option value="over_budget">only over token budget</option>
                              <option value="over_pct">over a % of the budget</option>
                              <option value="always">always</option>
                            </select>
                          </div>
                          {newRouteCompressWhen === 'over_pct' && (
                            <div className="flex flex-col gap-1">
                              <label className="text-[11px] text-gray-500 dark:text-gray-400">Budget fraction to trigger (e.g. 0.8)</label>
                              <input type="number" min="0.1" max="1" step="0.05" value={newRouteCompressPct} onChange={(e) => setNewRouteCompressPct(e.target.value)} className={inputCls} />
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
              <div className="sm:col-span-2 lg:col-span-3 border-t border-indigo-100 dark:border-indigo-900 pt-3 mt-1">
                <div className="flex items-center gap-2">
                  <input
                    id="intelligent-routing"
                    type="checkbox"
                    checked={newRouteIntelligent}
                    onChange={(e) => setNewRouteIntelligent(e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <label htmlFor="intelligent-routing" className="text-xs text-gray-600 dark:text-gray-300 cursor-pointer" title="Classify complexity × risk and route to a model tier; also sets reasoning effort">Intelligent Routing</label>
                </div>
                {newRouteIntelligent && (
                  <div className="mt-2 flex flex-col gap-1">
                    <label className="text-[11px] text-gray-500 dark:text-gray-400">Routing config (JSON) — tiers, matrix, classifier_mode, llm_model, reasoning_effort, on_failure</label>
                    <textarea
                      rows={12}
                      value={newRouteRoutingConfigStr}
                      onChange={(e) => { setNewRouteRoutingConfigStr(e.target.value); setNewRouteRoutingError('') }}
                      className={`${inputCls} font-mono text-[11px]`}
                    />
                    {newRouteRoutingError && <p className="text-xs text-red-500">{newRouteRoutingError}</p>}
                  </div>
                )}
              </div>
              <div className="sm:col-span-2 lg:col-span-3">
                <button type="submit" disabled={creatingRoute || !newRouteAlias || !newRouteTargetModel} className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
                  {creatingRoute ? 'Adding…' : 'Add Route'}
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          {gatewayRoutes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <Network className="h-8 w-8 text-slate-300 dark:text-slate-600" />
              <p className="text-sm text-slate-500 dark:text-slate-400">No routes configured yet.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Alias</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Provider</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Model</th>
                  <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Priority</th>
                  <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  {canManage && <th className="px-4 py-2.5" />}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                {gatewayRoutes.map((route) => (
                  <tr key={route.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    {(() => {
                      const fallbackAliases = getRouteFallbackAliases(route)
                      return (
                        <>
                    <td className="px-4 py-2.5">
                      <div className="flex flex-col gap-1">
                        <span className="font-mono text-sm font-semibold dark:text-slate-200">{route.alias}</span>
                        <div className="flex flex-wrap gap-1">
                          {route.routing_group_name && (
                            <span className="rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                              {route.routing_group_name}
                            </span>
                          )}
                          {route.region && (
                            <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                              {route.region}
                            </span>
                          )}
                          {route.required_tags.length > 0 && (
                            <span className="rounded-full bg-sky-100 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">
                              needs {route.required_tags.join(', ')}
                            </span>
                          )}
                          {route.excluded_tags.length > 0 && (
                            <span className="rounded-full bg-rose-100 px-1.5 py-0.5 text-[10px] font-medium text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">
                              avoids {route.excluded_tags.join(', ')}
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-xs capitalize text-slate-600 dark:text-slate-300">{route.provider}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">{route.target_model}</td>
                    <td className="px-4 py-2.5 text-center text-xs text-slate-500 dark:text-slate-400">{route.priority}</td>
                    <td className="px-4 py-2.5 text-center">
                      <div className="flex flex-col items-center gap-1">
                        <button
                          onClick={() => canManage && handleToggleRoute(route)}
                          disabled={!canManage}
                          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize transition-colors ${getDeploymentStatusTone(route.deployment_status)} ${canManage ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}`}
                          title={route.disabled_reason ?? undefined}
                        >
                          {route.deployment_status}
                        </button>
                        <span className="text-[11px] text-slate-500 dark:text-slate-400">
                          {route.is_active ? 'Route enabled' : 'Route disabled'}
                        </span>
                        {route.health_summary && (
                          <span className="max-w-[160px] text-[11px] text-center text-slate-400 dark:text-slate-500" title={route.health_summary}>
                            {route.health_summary}
                          </span>
                        )}
                        {route.disabled_reason && (
                          <span className="text-xs text-red-500 dark:text-red-400 max-w-[120px] truncate" title={route.disabled_reason}>
                            {route.disabled_reason}
                          </span>
                        )}
                        {fallbackAliases.length > 0 && (
                          <span
                            className="rounded-full bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300 px-1.5 py-0.5 text-[10px] font-medium"
                            title={`Fallback chain: ${fallbackAliases.join(', ')}`}
                          >
                            Fallback {fallbackAliases.length}
                          </span>
                        )}
                        {route.pii_redaction_enabled && (
                          <span className="rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 text-[10px] font-medium">PII</span>
                        )}
                        {canManage ? (
                          <button
                            onClick={() => handleToggleSemanticCache(route)}
                            title={route.semantic_cache_enabled ? 'Semantic cache ON — click to turn off' : 'Semantic cache OFF — click to turn on'}
                            className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium transition-colors cursor-pointer hover:opacity-80 ${route.semantic_cache_enabled ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300' : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500'}`}
                          >
                            Cache {route.semantic_cache_enabled ? 'ON' : 'OFF'}
                          </button>
                        ) : route.semantic_cache_enabled && (
                          <span className="rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 px-1.5 py-0.5 text-[10px] font-medium">Cache</span>
                        )}
                        {canManage ? (
                          <button
                            onClick={() => handleToggleContextCompiler(route)}
                            title={route.context_compiler_enabled ? 'Context compiler ON — click to turn off' : 'Context compiler OFF — click to turn on'}
                            className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium transition-colors cursor-pointer hover:opacity-80 ${route.context_compiler_enabled ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300' : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500'}`}
                          >
                            Compiler {route.context_compiler_enabled ? 'ON' : 'OFF'}
                          </button>
                        ) : route.context_compiler_enabled && (
                          <span className="rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 px-1.5 py-0.5 text-[10px] font-medium">Compiler</span>
                        )}
                        {canManage ? (
                          <button
                            onClick={() => handleToggleIntelligentRouting(route)}
                            title={route.intelligent_routing_enabled ? 'Intelligent routing ON — click to turn off' : 'Intelligent routing OFF — click to turn on'}
                            className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium transition-colors cursor-pointer hover:opacity-80 ${route.intelligent_routing_enabled ? 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300' : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500'}`}
                          >
                            Routing {route.intelligent_routing_enabled ? 'ON' : 'OFF'}
                          </button>
                        ) : route.intelligent_routing_enabled && (
                          <span className="rounded-full bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 px-1.5 py-0.5 text-[10px] font-medium">Routing</span>
                        )}
                      </div>
                    </td>
                    {canManage && (
                      <td className="px-4 py-2.5 text-right">
                        <button onClick={() => handleDeleteRoute(route.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    )}
                        </>
                      )
                    })()}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* ── Routing Policies ── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold dark:text-white">Routing Policies</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Intelligent routing strategies backed by live telemetry — cost, latency, quality.</p>
          </div>
          {canManage && (
            <button
              onClick={() => setShowPolicyForm((v) => !v)}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
            >
              {showPolicyForm ? <ChevronUp className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              {showPolicyForm ? 'Cancel' : 'Add Policy'}
            </button>
          )}
        </div>

        {showPolicyForm && canManage && (
          <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-900/10 p-4">
            <form onSubmit={handleCreatePolicy} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <input type="text" placeholder="Alias (e.g. local)" value={policyAlias} onChange={(e) => setPolicyAlias(e.target.value)} className={inputCls} required />
              <select value={policyType} onChange={(e) => setPolicyType(e.target.value as RoutingPolicyType)} className={inputCls}>
                <option value="manual">manual — priority order</option>
                <option value="cost_optimized">cost_optimized — cheapest above quality floor</option>
                <option value="latency_optimized">latency_optimized — lowest p95</option>
                <option value="quality_optimized">quality_optimized — highest score</option>
                <option value="weighted">weighted — random split by weight</option>
                <option value="canary">canary — % to canary route</option>
                <option value="ab_test">ab_test — traffic split with winner analysis</option>
                <option value="budget_aware">budget_aware — fallback when budget % hit</option>
                <option value="complexity_based">complexity_based — branch on token count</option>
                <option value="outcome_optimized">outcome_optimized — lowest cost-per-success</option>
              </select>
              <div>
                <input
                  type="text"
                  placeholder='Config JSON e.g. {"quality_floor": 0.6}'
                  value={policyConfigStr}
                  onChange={(e) => { setPolicyConfigStr(e.target.value); setPolicyConfigError('') }}
                  className={`${inputCls} font-mono text-xs`}
                />
                {policyConfigError && <p className="mt-1 text-xs text-red-500">{policyConfigError}</p>}
              </div>
              <button type="submit" disabled={creatingPolicy || !policyAlias} className="sm:col-span-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
                {creatingPolicy ? 'Creating…' : 'Add Policy'}
              </button>
            </form>
          </div>
        )}

        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          {routingPolicies.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 gap-2">
              <Activity className="h-7 w-7 text-slate-300 dark:text-slate-600" />
              <p className="text-sm text-slate-500 dark:text-slate-400">No routing policies yet.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Alias</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Strategy</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Config</th>
                  <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Insights</th>
                  <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                  {canManage && <th className="px-4 py-2.5" />}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                {routingPolicies.map((p) => (
                  <>
                    <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="px-4 py-2.5 font-mono text-sm font-semibold dark:text-slate-200">{p.alias}</td>
                      <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">{p.policy_type}</td>
                      <td className="px-4 py-2.5 font-mono text-xs text-slate-400 max-w-[200px] truncate" title={JSON.stringify(p.config)}>
                        {Object.keys(p.config).length ? JSON.stringify(p.config) : '—'}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <button
                          onClick={() => canManage && handleTogglePolicy(p)}
                          disabled={!canManage}
                          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors ${p.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'} ${canManage ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}`}
                        >
                          {p.is_active ? 'Active' : 'Disabled'}
                        </button>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <button
                          onClick={() => {
                            void handleLoadRecommendation(p.alias)
                            void handleLoadPolicyAnalysis(p.id)
                          }}
                          disabled={loadingRec[p.alias] || loadingPolicyAnalysis[p.id]}
                          title="View outcome-based routing recommendation"
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition-colors ${expandedRec === p.alias ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400 hover:bg-violet-50 hover:text-violet-600 dark:hover:bg-violet-900/20 dark:hover:text-violet-300'}`}
                        >
                          <Sparkles className="h-3 w-3" />
                          {loadingRec[p.alias] || loadingPolicyAnalysis[p.id] ? '…' : expandedRec === p.alias ? 'Hide' : 'Analyze'}
                        </button>
                      </td>
                      <td className="px-4 py-2.5">
                        <div className="flex flex-wrap items-center justify-center gap-2">
                          {(p.policy_type === 'ab_test' || p.policy_type === 'canary') && (
                            <button
                              onClick={() => void handlePromotePolicy(p.id)}
                              className="rounded-lg border border-indigo-200 px-2 py-1 text-[11px] font-medium text-indigo-700 hover:bg-indigo-50 dark:border-indigo-900/40 dark:text-indigo-300 dark:hover:bg-indigo-950/30"
                            >
                              Promote
                            </button>
                          )}
                          {p.policy_type === 'canary' && (
                            <button
                              onClick={() => void handleAdvanceCanary(p.id)}
                              className="rounded-lg border border-emerald-200 px-2 py-1 text-[11px] font-medium text-emerald-700 hover:bg-emerald-50 dark:border-emerald-900/40 dark:text-emerald-300 dark:hover:bg-emerald-950/30"
                            >
                              Advance
                            </button>
                          )}
                          {(p.policy_type === 'canary' || p.policy_type === 'ab_test') && (
                            <button
                              onClick={() => void handleRollbackPolicy(p.id)}
                              className="rounded-lg border border-amber-200 px-2 py-1 text-[11px] font-medium text-amber-700 hover:bg-amber-50 dark:border-amber-900/40 dark:text-amber-300 dark:hover:bg-amber-950/30"
                            >
                              Roll back
                            </button>
                          )}
                        </div>
                      </td>
                      {canManage && (
                        <td className="px-4 py-2.5 text-right">
                          <button onClick={() => handleDeletePolicy(p.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      )}
                    </tr>
                    {expandedRec === p.alias && recommendations[p.alias] && (
                      <tr key={`${p.id}-rec`}>
                        <td colSpan={canManage ? 7 : 6} className="px-4 py-0 bg-violet-50/50 dark:bg-violet-900/10">
                          <div className="py-3 space-y-4">
                            <RecommendationPanel rec={recommendations[p.alias]} />
                            {policyAnalysis[p.id] && (
                              <PolicyAnalysisPanel analysis={policyAnalysis[p.id]} />
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* ── Routing Log ── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold dark:text-white">Routing Log</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Which route was selected and why — including the full policy decision.</p>
          </div>
          <button
            onClick={handleLoadRoutingLog}
            disabled={loadingLog}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
          >
            <BarChart2 className="h-3.5 w-3.5" />
            {loadingLog ? 'Loading…' : 'Load recent'}
          </button>
        </div>

        {routingLog.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Time</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Alias</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Model Used</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Latency</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Decision Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                {routingLog.map((req) => (
                  <tr key={req.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-3 py-2 text-slate-400 whitespace-nowrap">{new Date(req.created_at).toLocaleTimeString()}</td>
                    <td className="px-3 py-2 font-mono dark:text-slate-200">{req.model_requested}</td>
                    <td className="px-3 py-2 font-mono text-slate-500 dark:text-slate-400">{req.model_used ?? '—'}</td>
                    <td className="px-3 py-2 dark:text-slate-300">{req.latency_ms != null ? `${req.latency_ms}ms` : '—'}</td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                        req.status === 'success' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' :
                        req.status === 'cache_hit' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' :
                        'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                      }`}>
                        {req.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-indigo-600 dark:text-indigo-400 max-w-[280px] truncate" title={req.decision_reason ?? ''}>
                      {req.decision_reason ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {routingLog.length === 0 && !loadingLog && (
          <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
            Click &quot;Load recent&quot; to fetch the last 50 gateway requests.
          </div>
        )}
      </section>

      {/* ── Optimization flywheel ── */}
      {apiKey && <BenchmarkPanel apiKey={apiKey} />}
      {apiKey && <PassThroughPanel apiKey={apiKey} canManage={canManage} />}
      {apiKey && <FlywheelPanel apiKey={apiKey} canManage={canManage} />}
    </div>
  )
}

// ── Recommendation panel ──────────────────────────────────────────────────────

function BenchmarkPanel({ apiKey }: { apiKey: string }) {
  const [days, setDays] = useState('7')
  const [items, setItems] = useState<GatewayBenchmarkComparisonItem[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getGatewayBenchmarkComparison(apiKey, { days: parseInt(days, 10) || 7 })
      setItems(data.items)
    } catch {
      toast.error('Failed to load benchmark comparison')
    } finally {
      setLoading(false)
    }
  }, [apiKey, days])

  useEffect(() => { void load() }, [load])

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold dark:text-white">Performance And Benchmarking</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Gateway overhead, throughput, and direct-provider comparison by alias over a rolling window.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select value={days} onChange={(e) => setDays(e.target.value)} className={inputCls}>
            <option value="1">Last 24h</option>
            <option value="7">Last 7d</option>
            <option value="30">Last 30d</option>
          </select>
          <button
            onClick={() => void load()}
            disabled={loading}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
          No benchmark data yet. Drive traffic through one or more aliases to populate overhead and throughput metrics.
        </div>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {items.map((item) => (
            <div key={item.alias} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800/40">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <BarChart2 className="h-4 w-4 text-indigo-500" />
                    <span className="font-mono text-sm text-slate-800 dark:text-slate-100">{item.alias}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {item.request_count} requests in the last {days === '1' ? '24 hours' : `${days} days`}
                  </p>
                </div>
                <div className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                  {item.throughput_rpm ? `${parseFloat(item.throughput_rpm).toFixed(2)} rpm` : '0 rpm'}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-3">
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">P50 overhead</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.p50_gateway_overhead_ms ? `${parseFloat(item.p50_gateway_overhead_ms).toFixed(0)}ms` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">P95 overhead</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.p95_gateway_overhead_ms ? `${parseFloat(item.p95_gateway_overhead_ms).toFixed(0)}ms` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">P99 overhead</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.p99_gateway_overhead_ms ? `${parseFloat(item.p99_gateway_overhead_ms).toFixed(0)}ms` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">Provider latency</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.avg_provider_latency_ms ? `${parseFloat(item.avg_provider_latency_ms).toFixed(0)}ms` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">End-to-end</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.avg_end_to_end_latency_ms ? `${parseFloat(item.avg_end_to_end_latency_ms).toFixed(0)}ms` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">Overhead vs provider</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.overhead_vs_provider_pct ? `${(parseFloat(item.overhead_vs_provider_pct) * 100).toFixed(1)}%` : '—'}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function PassThroughPanel({ apiKey, canManage }: { apiKey: string; canManage: boolean }) {
  const [items, setItems] = useState<GatewayPassThroughEndpoint[]>([])
  const [stats, setStats] = useState<Record<string, GatewayPassThroughEndpointStats>>({})
  const [testingId, setTestingId] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, GatewayPassThroughTestResult>>({})
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [slug, setSlug] = useState('')
  const [pathPrefix, setPathPrefix] = useState('/')
  const [upstreamBaseUrl, setUpstreamBaseUrl] = useState('')
  const [authType, setAuthType] = useState('')
  const [timeoutMs, setTimeoutMs] = useState('30000')
  const [rateLimitRpm, setRateLimitRpm] = useState('')
  const [costPerCallUsd, setCostPerCallUsd] = useState('')
  const [headerConfigStr, setHeaderConfigStr] = useState('{}')
  const [defaultQueryStr, setDefaultQueryStr] = useState('{}')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [data, statsData] = await Promise.all([
        listGatewayPassThroughEndpoints(apiKey, true),
        listGatewayPassThroughStats(apiKey).catch(() => ({ items: [] })),
      ])
      setItems(data.items)
      setStats(
        Object.fromEntries(
          statsData.items.map((item) => [item.endpoint_id, item]),
        ),
      )
    } catch {
      toast.error('Failed to load pass-through endpoints')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { void load() }, [load])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    let headerConfig: Record<string, unknown> = {}
    let defaultQuery: Record<string, unknown> = {}
    try {
      headerConfig = JSON.parse(headerConfigStr || '{}')
      defaultQuery = JSON.parse(defaultQueryStr || '{}')
    } catch {
      toast.error('Header and query config must be valid JSON')
      return
    }
    setCreating(true)
    try {
      const created = await createGatewayPassThroughEndpoint(apiKey, {
        slug: slug.trim(),
        path_prefix: pathPrefix.trim() || '/',
        upstream_base_url: upstreamBaseUrl.trim(),
        auth_type: authType.trim() || null,
        timeout_ms: parseInt(timeoutMs, 10) || 30000,
        rate_limit_rpm: rateLimitRpm ? parseInt(rateLimitRpm, 10) : null,
        cost_per_call_usd: costPerCallUsd ? parseFloat(costPerCallUsd) : null,
        header_config: headerConfig,
        default_query: defaultQuery,
      })
      setItems((prev) => [created, ...prev])
      setSlug('')
      setPathPrefix('/')
      setUpstreamBaseUrl('')
      setAuthType('')
      setTimeoutMs('30000')
      setRateLimitRpm('')
      setCostPerCallUsd('')
      setHeaderConfigStr('{}')
      setDefaultQueryStr('{}')
      toast.success('Pass-through endpoint created')
    } catch {
      toast.error('Failed to create pass-through endpoint')
    } finally {
      setCreating(false)
    }
  }

  async function handleToggle(item: GatewayPassThroughEndpoint) {
    try {
      const updated = await updateGatewayPassThroughEndpoint(apiKey, item.id, { is_active: !item.is_active })
      setItems((prev) => prev.map((cur) => (cur.id === item.id ? updated : cur)))
    } catch {
      toast.error('Failed to update pass-through endpoint')
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this pass-through endpoint?')) return
    try {
      await deleteGatewayPassThroughEndpoint(apiKey, id)
      setItems((prev) => prev.filter((item) => item.id !== id))
    } catch {
      toast.error('Failed to delete pass-through endpoint')
    }
  }

  async function handleTest(item: GatewayPassThroughEndpoint) {
    setTestingId(item.id)
    try {
      const result = await testGatewayPassThroughEndpoint(apiKey, item.id, {
        method: 'GET',
        path: '',
      })
      setTestResults((prev) => ({ ...prev, [item.id]: result }))
      toast.success(result.ok ? `Test succeeded (${result.status_code})` : `Test returned ${result.status_code}`)
    } catch {
      toast.error('Failed to test pass-through endpoint')
    } finally {
      setTestingId(null)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold dark:text-white">Pass-Through Endpoints</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Register non-LLM upstream APIs behind the gateway with shared auth, timeout, and rate policy.
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {canManage && (
        <form onSubmit={handleCreate} className="grid gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4 sm:grid-cols-2">
          <input value={slug} onChange={(e) => setSlug(e.target.value)} className={inputCls} placeholder="slug (search-proxy)" required />
          <input value={pathPrefix} onChange={(e) => setPathPrefix(e.target.value)} className={inputCls} placeholder="/v1" />
          <input value={upstreamBaseUrl} onChange={(e) => setUpstreamBaseUrl(e.target.value)} className={inputCls + ' sm:col-span-2'} placeholder="https://upstream.example.com" required />
          <input value={authType} onChange={(e) => setAuthType(e.target.value)} className={inputCls} placeholder="bearer | api_key | none" />
          <input value={timeoutMs} onChange={(e) => setTimeoutMs(e.target.value)} className={inputCls} placeholder="30000" />
          <input value={rateLimitRpm} onChange={(e) => setRateLimitRpm(e.target.value)} className={inputCls} placeholder="Rate limit RPM" />
          <input value={costPerCallUsd} onChange={(e) => setCostPerCallUsd(e.target.value)} className={inputCls} placeholder="Cost per call USD" />
          <textarea value={headerConfigStr} onChange={(e) => setHeaderConfigStr(e.target.value)} className={inputCls + ' min-h-[96px] sm:col-span-2'} placeholder='{"x-api-version":"2026-08"}' />
          <textarea value={defaultQueryStr} onChange={(e) => setDefaultQueryStr(e.target.value)} className={inputCls + ' min-h-[96px] sm:col-span-2'} placeholder='{"region":"us"}' />
          <div className="sm:col-span-2">
            <button type="submit" disabled={creating} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {creating ? 'Creating...' : 'Add endpoint'}
            </button>
          </div>
        </form>
      )}

      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
          No pass-through endpoints configured yet.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
              {(() => {
                const itemStats = stats[item.id]
                const testResult = testResults[item.id]
                return (
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm dark:text-slate-100">{item.slug}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">{item.path_prefix}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${item.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                      {item.is_active ? 'active' : 'inactive'}
                    </span>
                  </div>
                  <p className="mt-1 text-xs font-mono text-slate-500 dark:text-slate-400 break-all">{item.upstream_base_url}</p>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500 dark:text-slate-400">
                    <span>auth {item.auth_type ?? 'none'}</span>
                    <span>timeout {item.timeout_ms}ms</span>
                    <span>rpm {item.rate_limit_rpm ?? 'unlimited'}</span>
                    <span>cost {item.cost_per_call_usd ? `$${item.cost_per_call_usd}` : 'unset'}</span>
                  </div>
                  {itemStats && (
                    <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-4">
                      <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                        <p className="text-slate-400">Requests</p>
                        <p className="font-semibold text-slate-700 dark:text-slate-100">{itemStats.total_requests}</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                        <p className="text-slate-400">P95</p>
                        <p className="font-semibold text-slate-700 dark:text-slate-100">{itemStats.p95_latency_ms ? `${parseFloat(itemStats.p95_latency_ms).toFixed(0)}ms` : '—'}</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                        <p className="text-slate-400">Rate use</p>
                        <p className="font-semibold text-slate-700 dark:text-slate-100">
                          {itemStats.rate_limit_utilization_pct ? `${(parseFloat(itemStats.rate_limit_utilization_pct) * 100).toFixed(1)}%` : '—'}
                        </p>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                        <p className="text-slate-400">24h cost</p>
                        <p className="font-semibold text-slate-700 dark:text-slate-100">
                          {itemStats.estimated_24h_cost_usd ? `$${parseFloat(itemStats.estimated_24h_cost_usd).toFixed(4)}` : '—'}
                        </p>
                      </div>
                    </div>
                  )}
                  {testResult && (
                    <div className={`mt-3 rounded-lg px-3 py-2 text-xs ${testResult.ok ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-300' : 'bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-300'}`}>
                      <p className="font-medium">Last test: {testResult.status_code} in {testResult.latency_ms}ms</p>
                      <p className="mt-1 break-all">{testResult.target_url}</p>
                    </div>
                  )}
                </div>
                {canManage && (
                  <div className="flex shrink-0 gap-2">
                    <button onClick={() => void handleTest(item)} className="rounded-lg border border-indigo-200 px-3 py-1.5 text-xs text-indigo-700 hover:bg-indigo-50 dark:border-indigo-900/40 dark:text-indigo-300 dark:hover:bg-indigo-950/30">
                      {testingId === item.id ? 'Testing...' : 'Test'}
                    </button>
                    <button onClick={() => void handleToggle(item)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                      {item.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button onClick={() => void handleDelete(item.id)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                      Delete
                    </button>
                  </div>
                )}
              </div>
                )
              })()}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function RecommendationPanel({ rec }: { rec: RoutingRecommendationResponse }) {
  const hasData = rec.total_outcomes_sampled > 0 && rec.models.some((m) => m.cost_per_success !== null)

  return (
    <div className="py-3 space-y-2">
      {/* Summary message */}
      <div className={`flex items-start gap-2 rounded-lg px-3 py-2 text-sm ${hasData ? 'bg-violet-100 dark:bg-violet-900/20 text-violet-800 dark:text-violet-200' : 'bg-slate-100 dark:bg-slate-700/40 text-slate-500 dark:text-slate-400'}`}>
        <TrendingDown className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{rec.message}</span>
      </div>

      {/* Per-model table */}
      {hasData && (
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="text-left text-slate-400 dark:text-slate-500 border-b border-slate-200 dark:border-slate-700">
              <th className="py-1.5 pr-4 font-medium">Model</th>
              <th className="py-1.5 pr-4 font-medium text-right">Outcomes</th>
              <th className="py-1.5 pr-4 font-medium text-right">Success rate</th>
              <th className="py-1.5 pr-4 font-medium text-right">Cost / success</th>
              <th className="py-1.5 font-medium text-right">vs current</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {rec.models.map((m, i) => {
              const isBest = m.model === rec.best_model
              const imp = m.improvement_vs_current
              return (
                <tr key={m.model} className={isBest ? 'font-semibold' : ''}>
                  <td className="py-1.5 pr-4 dark:text-slate-200 font-mono">
                    {m.model}
                    {isBest && i === 0 && (
                      <span className="ml-1.5 rounded-full bg-violet-100 dark:bg-violet-900/30 px-1.5 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">best</span>
                    )}
                  </td>
                  <td className="py-1.5 pr-4 text-right text-slate-500 dark:text-slate-400">{m.sample_count}</td>
                  <td className="py-1.5 pr-4 text-right text-slate-600 dark:text-slate-300">
                    {m.success_rate > 0 ? `${(m.success_rate * 100).toFixed(1)}%` : '—'}
                  </td>
                  <td className="py-1.5 pr-4 text-right dark:text-slate-200">
                    {m.cost_per_success != null ? `$${m.cost_per_success.toFixed(4)}` : '—'}
                  </td>
                  <td className="py-1.5 text-right">
                    {imp != null ? (
                      <span className={`${imp > 0 ? 'text-emerald-600 dark:text-emerald-400' : imp < 0 ? 'text-red-500 dark:text-red-400' : 'text-slate-400'}`}>
                        {imp > 0 ? `↓${(imp * 100).toFixed(1)}%` : imp < 0 ? `↑${(Math.abs(imp) * 100).toFixed(1)}%` : '—'}
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      <p className="text-[11px] text-slate-400 dark:text-slate-500">
        Last {rec.window_days} days · {rec.total_outcomes_sampled} outcomes sampled
        {rec.workflow_type ? ` · type: ${rec.workflow_type}` : ''}
      </p>
    </div>
  )
}

// ── Optimization flywheel ─────────────────────────────────────────────────────

function PolicyAnalysisPanel({ analysis }: { analysis: RoutingPolicyAnalysis }) {
  return (
    <div className="space-y-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 p-4 dark:bg-slate-900/20">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">Traffic Analysis</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
          confidence {analysis.confidence}
        </span>
        {analysis.winner_label && (
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
            winner {analysis.winner_label}
          </span>
        )}
        {analysis.significance_p_value && (
          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-medium text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
            p={parseFloat(analysis.significance_p_value).toFixed(4)}
          </span>
        )}
        {analysis.auto_promoted && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
            auto-promoted
          </span>
        )}
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">{analysis.summary}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-400 dark:border-slate-700 dark:text-slate-500">
              <th className="py-1.5 pr-4 font-medium">Variant</th>
              <th className="py-1.5 pr-4 font-medium text-right">Alloc</th>
              <th className="py-1.5 pr-4 font-medium text-right">Requests</th>
              <th className="py-1.5 pr-4 font-medium text-right">Success</th>
              <th className="py-1.5 pr-4 font-medium text-right">Errors</th>
              <th className="py-1.5 font-medium text-right">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {analysis.variants.map((variant) => (
              <tr key={variant.route_id}>
                <td className="py-1.5 pr-4 font-mono text-slate-700 dark:text-slate-200">{variant.label}</td>
                <td className="py-1.5 pr-4 text-right text-slate-500 dark:text-slate-400">
                  {(parseFloat(variant.allocation_pct) * 100).toFixed(1)}%
                </td>
                <td className="py-1.5 pr-4 text-right text-slate-500 dark:text-slate-400">{variant.total_requests}</td>
                <td className="py-1.5 pr-4 text-right text-slate-600 dark:text-slate-300">
                  {(parseFloat(variant.success_rate) * 100).toFixed(1)}%
                </td>
                <td className="py-1.5 pr-4 text-right text-slate-600 dark:text-slate-300">
                  {(parseFloat(variant.error_rate) * 100).toFixed(1)}%
                </td>
                <td className="py-1.5 text-right text-slate-600 dark:text-slate-300">
                  {variant.avg_latency_ms ? `${parseFloat(variant.avg_latency_ms).toFixed(0)}ms` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const KIND_STYLE: Record<string, string> = {
  switch: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  explore: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  guardrail: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
}

function pctStr(v: string | null): string {
  if (v == null) return '—'
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return `${n > 0 ? '↑' : '↓'}${Math.abs(n * 100).toFixed(1)}%`
}

function FlywheelPanel({ apiKey, canManage }: { apiKey: string; canManage: boolean }) {
  const [settings, setSettings] = useState<FlywheelSettings | null>(null)
  const [recs, setRecs] = useState<FlywheelRecommendation[]>([])
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, r] = await Promise.all([
        getFlywheelSettings(apiKey).catch(() => null),
        listFlywheelRecommendations(apiKey, 'pending').catch(() => ({ items: [], total: 0 })),
      ])
      if (s) setSettings(s)
      setRecs(r.items)
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { void load() }, [load])

  async function patch(body: Partial<FlywheelSettings>) {
    if (!canManage) return
    try {
      const s = await updateFlywheelSettings(apiKey, body)
      setSettings(s)
      toast.success('Flywheel settings saved')
    } catch {
      toast.error('Failed to save settings')
    }
  }

  async function handleRun() {
    setRunning(true)
    try {
      const res = await runFlywheel(apiKey)
      toast.success(`Analysis ${res.status} · ${res.recommendations} recommendation(s)`)
      await load()
    } catch {
      toast.error('Flywheel run failed (is the service configured?)')
    } finally {
      setRunning(false)
    }
  }

  async function handleApply(id: string) {
    setBusyId(id)
    try {
      await applyFlywheelRecommendation(apiKey, id)
      toast.success('Recommendation applied')
      setRecs((cur) => cur.filter((r) => r.id !== id))
    } catch {
      toast.error('Failed to apply')
    } finally {
      setBusyId(null)
    }
  }

  async function handleDismiss(id: string) {
    setBusyId(id)
    try {
      await dismissFlywheelRecommendation(apiKey, id)
      setRecs((cur) => cur.filter((r) => r.id !== id))
    } catch {
      toast.error('Failed to dismiss')
    } finally {
      setBusyId(null)
    }
  }

  const metricType = (settings?.quality_metric?.type as string) ?? 'blend'

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold dark:text-white flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-indigo-500" />
            Optimization Flywheel
            {settings?.enabled ? (
              <span className="rounded-full bg-indigo-100 dark:bg-indigo-900/30 px-2 py-0.5 text-[10px] font-medium text-indigo-700 dark:text-indigo-300">ON</span>
            ) : (
              <span className="rounded-full bg-slate-100 dark:bg-slate-700 px-2 py-0.5 text-[10px] font-medium text-slate-500 dark:text-slate-400">OFF</span>
            )}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Learns the cheapest optimization config per segment that still holds your quality SLA, then recommends (or auto-applies) it.
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={running || !settings?.enabled}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
          title={settings?.enabled ? 'Run the analysis now' : 'Enable the flywheel first'}
        >
          <RefreshCw className={`h-3.5 w-3.5 ${running ? 'animate-spin' : ''}`} />
          {running ? 'Analyzing…' : 'Run now'}
        </button>
      </div>

      {/* Settings */}
      {settings && (
        <div className="grid gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={settings.enabled}
              disabled={!canManage}
              onChange={(e) => patch({ enabled: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300"
            />
            <span className="dark:text-slate-200">Enabled</span>
          </label>

          <label className="text-sm">
            <span className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Apply mode</span>
            <select
              value={settings.apply_mode}
              disabled={!canManage}
              onChange={(e) => patch({ apply_mode: e.target.value })}
              className={inputCls + ' w-full'}
            >
              <option value="approval">Approval-gated</option>
              <option value="auto">Auto-apply (guardrailed)</option>
              <option value="off">Off (analyze only)</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Segment by</span>
            <select
              value={settings.segment_by}
              disabled={!canManage}
              onChange={(e) => patch({ segment_by: e.target.value })}
              className={inputCls + ' w-full'}
            >
              <option value="outcome_type">Outcome type</option>
              <option value="task_class">Task class (complexity×risk)</option>
              <option value="alias">Alias</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Quality metric</span>
            <select
              value={metricType}
              disabled={!canManage}
              onChange={(e) => patch({ quality_metric: { ...settings.quality_metric, type: e.target.value } })}
              className={inputCls + ' w-full'}
            >
              <option value="blend">Blend (outcome + eval)</option>
              <option value="outcome_success">Outcome success-rate</option>
              <option value="eval_score">Eval / judge score</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Min quality (SLA)</span>
            <input
              type="number" step="0.05" min="0" max="1"
              defaultValue={Number(settings.min_quality)}
              disabled={!canManage}
              onBlur={(e) => patch({ min_quality: e.target.value })}
              className={inputCls + ' w-full'}
            />
          </label>

          <label className="text-sm">
            <span className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Min sample size</span>
            <input
              type="number" min="1"
              defaultValue={settings.min_sample_size}
              disabled={!canManage}
              onBlur={(e) => patch({ min_sample_size: Number(e.target.value) })}
              className={inputCls + ' w-full'}
            />
          </label>
        </div>
      )}

      {/* Recommendations */}
      {loading ? (
        <div className="py-6 text-center text-sm text-slate-400">Loading…</div>
      ) : recs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
          No pending recommendations. {settings?.enabled ? 'Run the analysis once enough traffic has accumulated.' : 'Enable the flywheel to start learning.'}
        </div>
      ) : (
        <div className="space-y-2">
          {recs.map((r) => (
            <div key={r.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${KIND_STYLE[r.kind] ?? 'bg-slate-100 text-slate-600'}`}>{r.kind}</span>
                    <span className="font-mono text-sm dark:text-slate-200 truncate">{r.segment_key}</span>
                    <span className="text-[10px] text-slate-400">· {r.confidence} confidence · n={r.sample_size}</span>
                  </div>
                  <p className="mt-1.5 text-xs text-slate-600 dark:text-slate-300">{r.rationale}</p>
                  <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-slate-500 dark:text-slate-400">
                    <span>cost <span className={Number(r.est_cost_delta_pct) < 0 ? 'text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-red-500 dark:text-red-400 font-semibold'}>{pctStr(r.est_cost_delta_pct)}</span></span>
                    <span>quality {r.current_quality != null ? Number(r.current_quality).toFixed(2) : '—'} → {r.proposed_quality != null ? Number(r.proposed_quality).toFixed(2) : '—'} (SLA {Number(r.min_quality).toFixed(2)})</span>
                    <span className="font-mono truncate">{JSON.stringify(r.proposed_config)}</span>
                  </div>
                </div>
                {canManage && (
                  <div className="flex shrink-0 gap-2">
                    <button
                      onClick={() => handleApply(r.id)}
                      disabled={busyId === r.id}
                      className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {r.segment_by === 'alias' ? 'Apply' : 'Accept'}
                    </button>
                    <button
                      onClick={() => handleDismiss(r.id)}
                      disabled={busyId === r.id}
                      className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
                    >
                      Dismiss
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-[11px] text-slate-400 dark:text-slate-500">
        Recommendations are observational — cost from your own gateway traffic, quality from outcomes/evals by model.
        Only <span className="font-mono">alias</span>-segmented proposals patch a route directly; others are advisory.
      </p>
    </section>
  )
}
