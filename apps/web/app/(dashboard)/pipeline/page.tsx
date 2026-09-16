'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  GitBranch, RefreshCw, Activity, Shield, DollarSign, Cpu,
  Eye, EyeOff, Play, ChevronDown, ChevronUp, Zap, Database,
  BarChart2, Clock, ArrowRight, Circle, Send, X,
} from 'lucide-react'
import {
  listGatewayRoutes, updateGatewayRoute,
  listGatewayRequests, getGatewayStats,
  getResponseCacheConfigs, updateResponseCacheConfig,
  listRoutingPolicies, updateRoutingPolicy,
  getPipelineStudioPosture,
} from '@/lib/api'
import { num } from '@/lib/utils'
import type {
  GatewayRoute, GatewayRequestLog, GatewayStats,
  ResponseCacheConfigResponse, RoutingPolicy,
  PipelineStudioPosture,
} from '@/types/api'

/* ────────────────────────────────────────────────────────────────── */
/*  Helpers                                                          */
/* ────────────────────────────────────────────────────────────────── */

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500'

const btnCls = (color: string) =>
  `flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium shadow-sm transition ${color}`

const stages = [
  { id: 'ingest', label: 'Ingest', icon: '📥', color: 'blue', desc: 'API key resolution, request parsing' },
  { id: 'routing', label: 'Routing', icon: '🔀', color: 'indigo', desc: 'Route selection, group matching, policy evaluation' },
  { id: 'enforcement', label: 'Enforcement', icon: '🛡️', color: 'red', desc: 'Guardrails, tool policies, scope validation' },
  { id: 'execution', label: 'Execution', icon: '⚡', color: 'emerald', desc: 'Rust data plane → provider direct HTTP' },
  { id: 'reporting', label: 'Reporting', icon: '📊', color: 'amber', desc: 'Metering, audit, analytics, cache write-back' },
]

type Tab = 'routes' | 'guardrails' | 'cache' | 'policies'

function statusDot(ok: boolean) {
  return (
    <span className={`inline-block h-2 w-2 rounded-full ${ok ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'}`} />
  )
}

/* ────────────────────────────────────────────────────────────────── */
/*  Pipeline Flow Graph                                              */
/* ────────────────────────────────────────────────────────────────── */

function PipelineGraph({
  activeStage,
  setActiveStage,
  requestCount,
}: {
  activeStage: string | null
  setActiveStage: (s: string | null) => void
  requestCount: number
}) {
  return (
    <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-gradient-to-r from-slate-50 to-indigo-50/30 dark:from-slate-800/60 dark:to-indigo-900/20 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold dark:text-white flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-indigo-500" />
          Request Pipeline
        </h2>
        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          {requestCount} requests flowing
        </div>
      </div>

      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {stages.map((stage, i) => {
          const selected = activeStage === stage.id
          return (
            <div key={stage.id} className="flex items-center gap-1">
              {i > 0 && (
                <div className="flex-shrink-0 w-10 h-px relative">
                  <div className="absolute inset-0 bg-slate-300 dark:bg-slate-600" />
                  <div
                    className="absolute inset-y-0 left-0 bg-indigo-500 animate-pulse"
                    style={{ width: '60%', animationDelay: `${i * 200}ms` }}
                  />
                  <ArrowRight className="absolute -right-1 top-1/2 -translate-y-1/2 h-3 w-3 text-indigo-400" />
                </div>
              )}
              <button
                onClick={() => setActiveStage(selected ? null : stage.id)}
                className={`flex-shrink-0 rounded-xl px-5 py-4 text-center min-w-[130px] transition-all cursor-pointer
                  ${selected
                    ? 'ring-2 ring-indigo-500 bg-white dark:bg-slate-800 shadow-lg scale-105'
                    : 'bg-white/80 dark:bg-slate-800/60 hover:bg-white dark:hover:bg-slate-800 hover:shadow-md'
                  }
                  border border-slate-200 dark:border-slate-700`}
              >
                <span className="text-2xl block">{stage.icon}</span>
                <p className="mt-1.5 text-xs font-semibold dark:text-white">{stage.label}</p>
                <p className="mt-0.5 text-[10px] text-slate-400 leading-tight">{stage.desc}</p>
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ────────────────────────────────────────────────────────────────── */
/*  Toggle Switch                                                    */
/* ────────────────────────────────────────────────────────────────── */

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors
        ${checked ? 'bg-indigo-500' : 'bg-slate-300 dark:bg-slate-600'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <span
        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition
          ${checked ? 'translate-x-4' : 'translate-x-0'}`}
      />
    </button>
  )
}

/* ────────────────────────────────────────────────────────────────── */
/*  Routes Panel                                                     */
/* ────────────────────────────────────────────────────────────────── */

function RoutesPanel({
  routes,
  onToggle,
  toggling,
}: {
  routes: GatewayRoute[]
  onToggle: (id: string, active: boolean) => void
  toggling: Set<string>
}) {
  return (
    <div className="space-y-2">
      {routes.length === 0 && <p className="text-xs text-slate-400 italic">No routes configured</p>}
      {routes.map((r) => (
        <div
          key={r.id}
          className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/50 px-3 py-2"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {statusDot(r.is_active)}
              <span className="text-xs font-medium dark:text-white truncate">{r.alias}</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5 truncate">
              {r.provider} · {r.target_model}
              {r.intelligent_routing_enabled && ' · IR'}
              {r.semantic_cache_enabled && ' · Cache'}
            </p>
          </div>
          <Toggle
            checked={r.is_active}
            onChange={(v) => onToggle(r.id, v)}
            disabled={toggling.has(r.id)}
          />
        </div>
      ))}
    </div>
  )
}

/* ────────────────────────────────────────────────────────────────── */
/*  Cache Panel                                                      */
/* ────────────────────────────────────────────────────────────────── */

function CachePanel({
  configs,
  onToggle,
  toggling,
}: {
  configs: ResponseCacheConfigResponse[]
  onToggle: (id: string, enabled: boolean) => void
  toggling: Set<string>
}) {
  return (
    <div className="space-y-2">
      {configs.length === 0 && <p className="text-xs text-slate-400 italic">No cache configs</p>}
      {configs.map((c) => (
        <div
          key={c.id}
          className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/50 px-3 py-2"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {statusDot(c.is_enabled)}
              <span className="text-xs font-medium dark:text-white truncate">{c.name}</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">
              TTL {c.ttl_seconds}s · {c.eviction_policy} · {num(c.total_hits)} hits
            </p>
          </div>
          <Toggle
            checked={c.is_enabled}
            onChange={(v) => onToggle(c.id, v)}
            disabled={toggling.has(c.id)}
          />
        </div>
      ))}
    </div>
  )
}

/* ────────────────────────────────────────────────────────────────── */
/*  Policies Panel                                                   */
/* ────────────────────────────────────────────────────────────────── */

function PoliciesPanel({
  policies,
  onToggle,
  toggling,
}: {
  policies: RoutingPolicy[]
  onToggle: (id: string, active: boolean) => void
  toggling: Set<string>
}) {
  return (
    <div className="space-y-2">
      {policies.length === 0 && <p className="text-xs text-slate-400 italic">No routing policies</p>}
      {policies.map((p) => (
        <div
          key={p.id}
          className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/50 px-3 py-2"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {statusDot(p.is_active)}
              <span className="text-xs font-medium dark:text-white truncate">{p.alias}</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">
              {p.policy_type.replace(/_/g, ' ')}
            </p>
          </div>
          <Toggle
            checked={p.is_active}
            onChange={(v) => onToggle(p.id, v)}
            disabled={toggling.has(p.id)}
          />
        </div>
      ))}
    </div>
  )
}

/* ────────────────────────────────────────────────────────────────── */
/*  Live Request Feed                                                */
/* ────────────────────────────────────────────────────────────────── */

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    success: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400',
    cache_hit: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400',
    error: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
    timeout: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400',
    blocked: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${colors[status] || 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

function RequestFeed({
  requests,
  expandedId,
  setExpandedId,
}: {
  requests: GatewayRequestLog[]
  expandedId: string | null
  setExpandedId: (id: string | null) => void
}) {
  return (
    <div className="space-y-1">
      {requests.length === 0 && (
        <p className="text-xs text-slate-400 italic py-4 text-center">No recent requests</p>
      )}
      {requests.map((req) => {
        const expanded = expandedId === req.id
        return (
          <div key={req.id}>
            <button
              onClick={() => setExpandedId(expanded ? null : req.id)}
              className="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-800/60 transition"
            >
              <span className="flex-shrink-0">{statusBadge(req.status)}</span>
              <span className="text-xs font-medium dark:text-white truncate flex-1">{req.model_requested}</span>
              <span className="text-[10px] text-slate-400 flex-shrink-0">{req.latency_ms}ms</span>
              <span className="text-[10px] text-slate-400 flex-shrink-0">{(req.input_tokens ?? 0) + (req.output_tokens ?? 0)} tok</span>
              <span className="text-[10px] text-slate-400 flex-shrink-0 w-14 text-right">
                {new Date(req.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              {expanded ? <ChevronUp className="h-3 w-3 text-slate-400" /> : <ChevronDown className="h-3 w-3 text-slate-400" />}
            </button>
            {expanded && (
              <div className="ml-3 mb-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 p-3 space-y-3">
                <div className="text-xs font-semibold dark:text-white mb-2">Request Trace</div>
                <div className="flex items-center gap-1 overflow-x-auto">
                  {stages.map((stage, i) => {
                    const isHit = stage.id === 'execution' && req.cache_hit
                    return (
                      <div key={stage.id} className="flex items-center gap-1">
                        {i > 0 && <ArrowRight className="h-3 w-3 text-slate-300 dark:text-slate-600 flex-shrink-0" />}
                        <div className={`flex-shrink-0 rounded-md px-2.5 py-1.5 text-center text-[10px] font-medium border
                          ${req.status === 'blocked' && stage.id === 'enforcement'
                            ? 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-700 dark:text-red-400'
                            : isHit
                            ? 'bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-400'
                            : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300'
                          }`}>
                          <span className="block text-sm">{stage.icon}</span>
                          {stage.label}
                          {isHit && <span className="block text-[9px]">CACHE HIT</span>}
                          {req.status === 'blocked' && stage.id === 'enforcement' && <span className="block text-[9px]">BLOCKED</span>}
                        </div>
                      </div>
                    )
                  })}
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                  <div>
                    <span className="text-slate-400">Model requested</span>
                    <p className="font-medium dark:text-white">{req.model_requested}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Model used</span>
                    <p className="font-medium dark:text-white">{req.model_used || req.model_requested}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Input / Output</span>
                    <p className="font-medium dark:text-white">{num(req.input_tokens)} / {num(req.output_tokens)}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Decision</span>
                    <p className="font-medium dark:text-white">{req.decision_reason || 'direct'}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ────────────────────────────────────────────────────────────────── */
/*  Inject Request Panel                                             */
/* ────────────────────────────────────────────────────────────────── */

function InjectPanel({
  open,
  onClose,
  apiKey,
  onSent,
}: {
  open: boolean
  onClose: () => void
  apiKey: string
  onSent: () => void
}) {
  const [model, setModel] = useState('gpt-4o')
  const [prompt, setPrompt] = useState('Say hello in one sentence.')
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<string | null>(null)

  async function send() {
    setSending(true)
    setResult(null)
    try {
      const res = await fetch('/api/v1/gateway/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: prompt }],
          max_tokens: 100,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        setResult(`Error ${res.status}: ${JSON.stringify(data)}`)
      } else {
        const content = data.choices?.[0]?.message?.content || JSON.stringify(data)
        setResult(content)
        toast.success('Request traced through pipeline')
        onSent()
      }
    } catch (e: any) {
      setResult(`Network error: ${e.message}`)
    } finally {
      setSending(false)
    }
  }

  if (!open) return null

  return (
    <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-white dark:bg-slate-800/80 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold dark:text-white flex items-center gap-2">
          <Send className="h-4 w-4 text-indigo-500" />
          Inject Test Request
        </h3>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="text-[11px] text-slate-500 dark:text-slate-400 block mb-1">Model</label>
          <input className={inputCls} value={model} onChange={(e) => setModel(e.target.value)} placeholder="gpt-4o" />
        </div>
        <div>
          <label className="text-[11px] text-slate-500 dark:text-slate-400 block mb-1">Prompt</label>
          <input className={inputCls} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Say hello" />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={send}
          disabled={sending}
          className={btnCls('border-indigo-300 dark:border-indigo-700 bg-indigo-500 text-white hover:bg-indigo-600')}
        >
          {sending ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
          {sending ? 'Sending...' : 'Send & Trace'}
        </button>
        {result && (
          <div className="flex-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-3 py-2 text-xs dark:text-slate-300 max-h-20 overflow-y-auto">
            {result}
          </div>
        )}
      </div>
    </div>
  )
}

/* ────────────────────────────────────────────────────────────────── */
/*  Main Page                                                        */
/* ────────────────────────────────────────────────────────────────── */

export default function PipelineDesignerPage() {
  const { data: session } = useSession()
  const apiKey = session?.apiKey || ''

  const [loading, setLoading] = useState(true)
  const [activeStage, setActiveStage] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('routes')
  const [expandedRequest, setExpandedRequest] = useState<string | null>(null)
  const [injectOpen, setInjectOpen] = useState(false)

  const [posture, setPosture] = useState<PipelineStudioPosture | null>(null)
  const [routes, setRoutes] = useState<GatewayRoute[]>([])
  const [cacheConfigs, setCacheConfigs] = useState<ResponseCacheConfigResponse[]>([])
  const [policies, setPolicies] = useState<RoutingPolicy[]>([])
  const [requests, setRequests] = useState<GatewayRequestLog[]>([])
  const [stats, setStats] = useState<GatewayStats | null>(null)
  const [toggling, setToggling] = useState<Set<string>>(new Set())

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchAll = useCallback(async () => {
    if (!apiKey) return
    try {
      const [p, r, cc, pol, req, st] = await Promise.all([
        getPipelineStudioPosture(apiKey).catch(() => null),
        listGatewayRoutes(apiKey, true).catch(() => ({ items: [] })),
        getResponseCacheConfigs(apiKey).catch(() => ({ items: [] })),
        listRoutingPolicies(apiKey).catch(() => ({ items: [] })),
        listGatewayRequests(apiKey, { limit: 50 }).catch(() => ({ items: [] })),
        getGatewayStats(apiKey).catch(() => null),
      ])
      if (p) setPosture(p)
      setRoutes((r as any).items || [])
      setCacheConfigs((cc as any).items || [])
      setPolicies((pol as any).items || [])
      setRequests((req as any).items || [])
      if (st) setStats(st)
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    fetchAll()
    pollRef.current = setInterval(fetchAll, 5000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [fetchAll])

  async function toggleRoute(id: string, active: boolean) {
    setToggling((s) => new Set(s).add(id))
    try {
      await updateGatewayRoute(apiKey, id, { is_active: active })
      setRoutes((prev) => prev.map((r) => (r.id === id ? { ...r, is_active: active } : r)))
      toast.success(`Route ${active ? 'enabled' : 'disabled'}`)
    } catch {
      toast.error('Failed to update route')
    } finally {
      setToggling((s) => { const n = new Set(s); n.delete(id); return n })
    }
  }

  async function toggleCache(id: string, enabled: boolean) {
    setToggling((s) => new Set(s).add(id))
    try {
      await updateResponseCacheConfig(apiKey, id, { is_enabled: enabled })
      setCacheConfigs((prev) => prev.map((c) => (c.id === id ? { ...c, is_enabled: enabled } : c)))
      toast.success(`Cache ${enabled ? 'enabled' : 'disabled'}`)
    } catch {
      toast.error('Failed to update cache config')
    } finally {
      setToggling((s) => { const n = new Set(s); n.delete(id); return n })
    }
  }

  async function togglePolicy(id: string, active: boolean) {
    setToggling((s) => new Set(s).add(id))
    try {
      await updateRoutingPolicy(apiKey, id, { is_active: active })
      setPolicies((prev) => prev.map((p) => (p.id === id ? { ...p, is_active: active } : p)))
      toast.success(`Policy ${active ? 'enabled' : 'disabled'}`)
    } catch {
      toast.error('Failed to update policy')
    } finally {
      setToggling((s) => { const n = new Set(s); n.delete(id); return n })
    }
  }

  const activeRoutes = routes.filter((r) => r.is_active).length
  const totalRequests = stats?.total_requests ?? 0
  const cacheRate = stats?.cache_hit_rate ?? 0

  const tabs: { id: Tab; label: string; icon: typeof Activity; count: number }[] = [
    { id: 'routes', label: 'Routes', icon: GitBranch, count: routes.length },
    { id: 'guardrails', label: 'Guardrails', icon: Shield, count: posture?.enforcement_overlay?.guardrail_rules ?? 0 },
    { id: 'cache', label: 'Cache', icon: Database, count: cacheConfigs.length },
    { id: 'policies', label: 'Policies', icon: Zap, count: policies.length },
  ]

  return (
    <div className="mx-auto max-w-[1600px] space-y-5 px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold dark:text-white flex items-center gap-2">
            <Cpu className="h-6 w-6 text-indigo-500" />
            Pipeline Designer
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Interactive pipeline designer — trace requests, toggle features, inject routing, observe everything.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setInjectOpen(!injectOpen)}
            className={btnCls('border-indigo-300 dark:border-indigo-700 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/50')}
          >
            <Send className="h-3.5 w-3.5" />
            Inject Request
          </button>
          <button
            onClick={() => { setLoading(true); fetchAll() }}
            disabled={loading}
            className={btnCls('border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700')}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Inject Panel */}
      <InjectPanel open={injectOpen} onClose={() => setInjectOpen(false)} apiKey={apiKey} onSent={fetchAll} />

      {/* Stats Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-6 gap-3">
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-400">Active Routes</p>
          <p className="text-lg font-semibold dark:text-white">{activeRoutes}<span className="text-xs text-slate-400 font-normal">/{routes.length}</span></p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-400">Total Requests</p>
          <p className="text-lg font-semibold dark:text-white">{num(totalRequests)}</p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-400">Cache Hit Rate</p>
          <p className="text-lg font-semibold dark:text-white">{(cacheRate * 100).toFixed(1)}%</p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-400">Avg Latency</p>
          <p className="text-lg font-semibold dark:text-white">{stats?.avg_latency_ms?.toFixed(0) ?? '—'}ms</p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-400">Guardrails</p>
          <p className="text-lg font-semibold dark:text-white">{posture?.enforcement_overlay?.guardrail_rules ?? 0}</p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-400">Policies</p>
          <p className="text-lg font-semibold dark:text-white">{policies.filter((p) => p.is_active).length}<span className="text-xs text-slate-400 font-normal">/{policies.length}</span></p>
        </div>
      </div>

      {/* Pipeline Flow Graph */}
      <PipelineGraph activeStage={activeStage} setActiveStage={setActiveStage} requestCount={requests.length} />

      {/* Main Content: Control Panels + Live Feed */}
      <div className="grid gap-5 xl:grid-cols-3">
        {/* Feature Control Panels */}
        <div className="xl:col-span-1 space-y-4">
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 overflow-hidden">
            <div className="flex border-b border-slate-200 dark:border-slate-700">
              {tabs.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2.5 text-[11px] font-medium transition
                    ${activeTab === t.id
                      ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border-b-2 border-indigo-500'
                      : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'}`}
                >
                  <t.icon className="h-3 w-3" />
                  {t.label}
                  <span className="rounded-full bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 text-[10px]">{t.count}</span>
                </button>
              ))}
            </div>
            <div className="p-3 max-h-[500px] overflow-y-auto">
              {activeTab === 'routes' && <RoutesPanel routes={routes} onToggle={toggleRoute} toggling={toggling} />}
              {activeTab === 'guardrails' && (
                <div className="space-y-2">
                  <p className="text-xs text-slate-400">
                    {posture?.enforcement_overlay?.guardrail_rules ?? 0} rules · {posture?.enforcement_overlay?.blocked_events_30d ?? 0} blocked (30d) · {posture?.enforcement_overlay?.tool_policies ?? 0} tool policies
                  </p>
                  <Link href="/guardrails" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400 block">
                    Manage guardrails →
                  </Link>
                </div>
              )}
              {activeTab === 'cache' && <CachePanel configs={cacheConfigs} onToggle={toggleCache} toggling={toggling} />}
              {activeTab === 'policies' && <PoliciesPanel policies={policies} onToggle={togglePolicy} toggling={toggling} />}
            </div>
          </div>

          {/* Architecture Summary */}
          {posture && (
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4 space-y-3">
              <h3 className="text-xs font-semibold dark:text-white">Runtime Architecture</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Data Plane</span>
                  <span className="font-medium dark:text-white">{posture.pipeline_model.execution_runtime.data_plane}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Control Plane</span>
                  <span className="font-medium dark:text-white">{posture.pipeline_model.execution_runtime.control_plane}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Providers</span>
                  <span className="font-medium dark:text-white">{posture.pipeline_model.routing_nodes.distinct_providers}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Routing Groups</span>
                  <span className="font-medium dark:text-white">{posture.pipeline_model.routing_nodes.routing_groups}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Live Request Feed */}
        <div className="xl:col-span-2">
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 px-4 py-3">
              <h3 className="text-sm font-semibold dark:text-white flex items-center gap-2">
                <Activity className="h-4 w-4 text-emerald-500" />
                Live Request Feed
                <span className="text-[10px] text-slate-400 font-normal">Auto-refreshing every 5s</span>
              </h3>
              <span className="text-[11px] text-slate-400">{requests.length} requests</span>
            </div>
            <div className="max-h-[600px] overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800">
              <RequestFeed
                requests={requests}
                expandedId={expandedRequest}
                setExpandedId={setExpandedRequest}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Overlay Stats */}
      {posture && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-800/40 p-4 space-y-2">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-blue-500" />
              <h3 className="text-xs font-semibold dark:text-white">Traffic (7d)</h3>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span className="text-slate-500">Requests</span><span className="font-medium dark:text-white">{num(posture.traffic_overlay.requests_7d)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Cache hits</span><span className="font-medium dark:text-white">{num(posture.traffic_overlay.cache_hits_7d)}</span></div>
            </div>
          </div>
          <div className="rounded-xl border border-red-200 dark:border-red-800 bg-white dark:bg-slate-800/40 p-4 space-y-2">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-red-500" />
              <h3 className="text-xs font-semibold dark:text-white">Enforcement (30d)</h3>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span className="text-slate-500">Events</span><span className="font-medium dark:text-white">{num(posture.enforcement_overlay.guardrail_events_30d)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Blocked</span><span className="font-medium dark:text-white">{num(posture.enforcement_overlay.blocked_events_30d)}</span></div>
            </div>
          </div>
          <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-white dark:bg-slate-800/40 p-4 space-y-2">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-amber-500" />
              <h3 className="text-xs font-semibold dark:text-white">FinOps</h3>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span className="text-slate-500">Budgets</span><span className="font-medium dark:text-white">{posture.finops_overlay.budgets}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Cost tracking</span><span className="font-medium dark:text-white">{posture.finops_overlay.cost_tracking}</span></div>
            </div>
          </div>
          <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-white dark:bg-slate-800/40 p-4 space-y-2">
            <div className="flex items-center gap-2">
              <BarChart2 className="h-4 w-4 text-emerald-500" />
              <h3 className="text-xs font-semibold dark:text-white">Build</h3>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span className="text-slate-500">Agents</span><span className="font-medium dark:text-white">{posture.build_overlay.agents}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Workflows</span><span className="font-medium dark:text-white">{posture.build_overlay.workflows}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex flex-wrap gap-3">
        <Link href="/gateway" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Model Gateway</Link>
        <Link href="/pipeline-studio" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Pipeline Studio</Link>
        <Link href="/analytics" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Analytics</Link>
        <Link href="/guardrails" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Guardrails</Link>
        <Link href="/governance" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Governance</Link>
        <Link href="/budgets" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Budgets</Link>
        <Link href="/workflows" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Workflows</Link>
        <Link href="/agents" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Agents</Link>
        <Link href="/audit" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Audit Log</Link>
      </div>
    </div>
  )
}
