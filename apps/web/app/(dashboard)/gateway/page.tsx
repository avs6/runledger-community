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
  getGatewayStats, listRoutingPolicies, createRoutingPolicy, updateRoutingPolicy,
  deleteRoutingPolicy, listGatewayRequests, listProviderPricing, getRoutingRecommendation,
} from '@/lib/api'
import type {
  GatewayRoute, GatewayStats, GatewayRequestLog,
  RoutingPolicy, RoutingPolicyType, ProviderPricingResponse,
  RoutingRecommendationResponse,
} from '@/types/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

export default function GatewayPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { isWorkspaceAdmin, isOrgAdmin, isPlatformAdmin } = useRole()
  const canManage = isWorkspaceAdmin || isOrgAdmin || isPlatformAdmin

  const [gatewayRoutes, setGatewayRoutes] = useState<GatewayRoute[]>([])
  const [gatewayStats, setGatewayStats] = useState<GatewayStats | null>(null)
  const [newRouteAlias, setNewRouteAlias] = useState('')
  const [newRouteProvider, setNewRouteProvider] = useState('openai')
  const [newRouteTargetModel, setNewRouteTargetModel] = useState('')
  const [newRouteBaseUrl, setNewRouteBaseUrl] = useState('')
  const [newRouteApiKeyEnvVar, setNewRouteApiKeyEnvVar] = useState('OPENAI_API_KEY')
  const [newRoutePriority, setNewRoutePriority] = useState('10')
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
  const [creatingRoute, setCreatingRoute] = useState(false)
  const [showRouteForm, setShowRouteForm] = useState(false)

  const [routingPolicies, setRoutingPolicies] = useState<RoutingPolicy[]>([])
  const [policyAlias, setPolicyAlias] = useState('')
  const [policyType, setPolicyType] = useState<RoutingPolicyType>('manual')
  const [policyConfigStr, setPolicyConfigStr] = useState('{}')
  const [creatingPolicy, setCreatingPolicy] = useState(false)
  const [policyConfigError, setPolicyConfigError] = useState('')
  const [showPolicyForm, setShowPolicyForm] = useState(false)

  const [routingLog, setRoutingLog] = useState<GatewayRequestLog[]>([])
  const [loadingLog, setLoadingLog] = useState(false)

  // Outcome-based routing recommendations
  const [recommendations, setRecommendations] = useState<Record<string, RoutingRecommendationResponse>>({})
  const [loadingRec, setLoadingRec] = useState<Record<string, boolean>>({})
  const [expandedRec, setExpandedRec] = useState<string | null>(null)

  const [pricing, setPricing] = useState<ProviderPricingResponse[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [routesData, statsData, policiesData, pricingData] = await Promise.all([
        listGatewayRoutes(apiKey, true).catch(() => ({ items: [] })),
        getGatewayStats(apiKey).catch(() => ({ total_requests: 0, cache_hits: 0, cache_hit_rate: '0', avg_latency_ms: null, routes: [] })),
        listRoutingPolicies(apiKey).catch(() => ({ items: [] })),
        listProviderPricing(apiKey).catch(() => ({ items: [] })),
      ])
      setGatewayRoutes(routesData.items)
      setGatewayStats(statsData as any)
      setRoutingPolicies(policiesData.items)
      setPricing(pricingData.items)
    } catch {
      toast.error('Failed to load gateway data')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { load() }, [load])

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
              stages: { compress: newRouteCompress },
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
      })
      setGatewayRoutes((prev) => [...prev, route])
      setNewRouteAlias('')
      setNewRouteTargetModel('')
      setNewRouteBaseUrl('')
      setNewRouteApiKeyEnvVar('OPENAI_API_KEY')
      setNewRoutePriority('10')
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
      setNewRouteIntelligent(false)
      setNewRouteRoutingError('')
      setNewRoutePerUserRpm('')
      setShowRouteForm(false)
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
                    <td className="px-4 py-2.5 font-mono text-sm font-semibold dark:text-slate-200">{route.alias}</td>
                    <td className="px-4 py-2.5 text-xs capitalize text-slate-600 dark:text-slate-300">{route.provider}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">{route.target_model}</td>
                    <td className="px-4 py-2.5 text-center text-xs text-slate-500 dark:text-slate-400">{route.priority}</td>
                    <td className="px-4 py-2.5 text-center">
                      <div className="flex flex-col items-center gap-1">
                        <button
                          onClick={() => canManage && handleToggleRoute(route)}
                          disabled={!canManage}
                          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors ${route.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'} ${canManage ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}`}
                          title={route.disabled_reason ?? undefined}
                        >
                          {route.is_active ? 'Active' : 'Disabled'}
                        </button>
                        {route.disabled_reason && (
                          <span className="text-xs text-red-500 dark:text-red-400 max-w-[120px] truncate" title={route.disabled_reason}>
                            {route.disabled_reason}
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
                          onClick={() => handleLoadRecommendation(p.alias)}
                          disabled={loadingRec[p.alias]}
                          title="View outcome-based routing recommendation"
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition-colors ${expandedRec === p.alias ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400 hover:bg-violet-50 hover:text-violet-600 dark:hover:bg-violet-900/20 dark:hover:text-violet-300'}`}
                        >
                          <Sparkles className="h-3 w-3" />
                          {loadingRec[p.alias] ? '…' : expandedRec === p.alias ? 'Hide' : 'Analyze'}
                        </button>
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
                        <td colSpan={canManage ? 6 : 5} className="px-4 py-0 bg-violet-50/50 dark:bg-violet-900/10">
                          <RecommendationPanel rec={recommendations[p.alias]} />
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
    </div>
  )
}

// ── Recommendation panel ──────────────────────────────────────────────────────

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
