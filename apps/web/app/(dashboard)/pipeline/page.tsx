'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  GitBranch, RefreshCw, Activity, Shield, DollarSign, Cpu,
  Play, ChevronDown, ChevronUp, Zap, Database,
  Clock, ArrowRight, Send, X, Radio, Layers,
  AlertTriangle, CheckCircle2, XCircle, Timer,
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

/* ── Helpers ─────────────────────────────────────────────────────── */

const inputCls =
  'w-full rounded-lg border border-slate-700 bg-slate-900 text-slate-100 px-3 py-2 text-sm placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent'

const stages = [
  { id: 'ingest', label: 'Ingest', icon: Layers, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20', activeBg: 'bg-blue-500/20 border-blue-500/40 ring-1 ring-blue-500/30', desc: 'API key · parsing' },
  { id: 'routing', label: 'Routing', icon: GitBranch, color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/20', activeBg: 'bg-indigo-500/20 border-indigo-500/40 ring-1 ring-indigo-500/30', desc: 'Route · policy' },
  { id: 'enforcement', label: 'Enforce', icon: Shield, color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/20', activeBg: 'bg-rose-500/20 border-rose-500/40 ring-1 ring-rose-500/30', desc: 'Guardrails · scope' },
  { id: 'execution', label: 'Execute', icon: Zap, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', activeBg: 'bg-emerald-500/20 border-emerald-500/40 ring-1 ring-emerald-500/30', desc: 'Rust → provider' },
  { id: 'reporting', label: 'Report', icon: Activity, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', activeBg: 'bg-amber-500/20 border-amber-500/40 ring-1 ring-amber-500/30', desc: 'Metrics · audit' },
]

type Tab = 'routes' | 'guardrails' | 'cache' | 'policies'

/* ── Toggle Switch ───────────────────────────────────────────────── */

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
        ${checked ? 'bg-indigo-500' : 'bg-slate-600'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <span
        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition
          ${checked ? 'translate-x-4' : 'translate-x-0'}`}
      />
    </button>
  )
}

/* ── Pipeline Flow ───────────────────────────────────────────────── */

function PipelineGraph({
  activeStage,
  setActiveStage,
  requestCount,
  onStageSelect,
}: {
  activeStage: string | null
  setActiveStage: (s: string | null) => void
  requestCount: number
  onStageSelect: (s: string) => void
}) {
  return (
    <div className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <Radio className="h-4 w-4 text-indigo-400" />
          Request Pipeline
        </h2>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          {requestCount} requests
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        {stages.map((stage, i) => {
          const selected = activeStage === stage.id
          const Icon = stage.icon
          return (
            <div key={stage.id} className="flex items-center gap-2 flex-1">
              {i > 0 && (
                <div className="flex-shrink-0 flex items-center">
                  <div className="w-6 h-px bg-slate-700" />
                  <ArrowRight className="h-3 w-3 text-slate-600 -ml-1" />
                </div>
              )}
              <button
                onClick={() => {
                  setActiveStage(selected ? null : stage.id)
                  onStageSelect(stage.id)
                }}
                className={`flex-1 rounded-xl px-3 py-3.5 text-center transition-all cursor-pointer border
                  ${selected ? stage.activeBg : `${stage.bg} hover:brightness-125`}`}
              >
                <Icon className={`h-5 w-5 mx-auto ${stage.color}`} />
                <p className="mt-1.5 text-xs font-semibold text-white">{stage.label}</p>
                <p className="mt-0.5 text-[10px] text-slate-400">{stage.desc}</p>
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── Routes Panel ────────────────────────────────────────────────── */

function RoutesPanel({
  routes,
  onToggle,
  onFeatureToggle,
  toggling,
}: {
  routes: GatewayRoute[]
  onToggle: (id: string, active: boolean) => void
  onFeatureToggle: (id: string, feature: 'semantic_cache_enabled' | 'context_compiler_enabled' | 'intelligent_routing_enabled', enabled: boolean) => void
  toggling: Set<string>
}) {
  if (routes.length === 0) return <p className="text-sm text-slate-500 italic py-6 text-center">No routes configured</p>
  return (
    <div className="space-y-2">
      {routes.map((r) => (
        <div
          key={r.id}
          className="rounded-xl border border-slate-700/50 bg-slate-800/40 p-3.5 hover:bg-slate-800/60 transition"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <span className={`inline-block h-2 w-2 rounded-full flex-shrink-0 ${r.is_active ? 'bg-emerald-500' : 'bg-slate-600'}`} />
              <div className="min-w-0">
                <span className="text-sm font-medium text-white block truncate">{r.alias}</span>
                <p className="text-xs text-slate-400 truncate">{r.provider} · {r.target_model}</p>
              </div>
            </div>
            <Toggle
              checked={r.is_active}
              onChange={(v) => onToggle(r.id, v)}
              disabled={toggling.has(r.id)}
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {([
              ['intelligent_routing_enabled', 'Routing', 'emerald'],
              ['semantic_cache_enabled', 'Cache', 'blue'],
              ['context_compiler_enabled', 'Compiler', 'violet'],
            ] as const).map(([feature, label, color]) => {
              const enabled = Boolean(r[feature])
              const cls = enabled
                ? color === 'emerald'
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                  : color === 'blue'
                  ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
                  : 'bg-violet-500/15 text-violet-400 border-violet-500/30'
                : 'bg-slate-800 text-slate-500 border-slate-700'
              return (
                <button
                  key={feature}
                  type="button"
                  onClick={() => onFeatureToggle(r.id, feature, !enabled)}
                  disabled={toggling.has(`${r.id}:${feature}`)}
                  className={`rounded-md border px-2 py-1 text-[11px] font-medium transition hover:brightness-125 disabled:opacity-50 ${cls}`}
                >
                  {label}
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

/* ── Cache Panel ─────────────────────────────────────────────────── */

function CachePanel({
  configs,
  onToggle,
  toggling,
}: {
  configs: ResponseCacheConfigResponse[]
  onToggle: (id: string, enabled: boolean) => void
  toggling: Set<string>
}) {
  if (configs.length === 0) return <p className="text-sm text-slate-500 italic py-6 text-center">No cache configs</p>
  return (
    <div className="space-y-2">
      {configs.map((c) => (
        <div
          key={c.id}
          className="flex items-center justify-between rounded-xl border border-slate-700/50 bg-slate-800/40 p-3.5 hover:bg-slate-800/60 transition"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <span className={`inline-block h-2 w-2 rounded-full flex-shrink-0 ${c.is_enabled ? 'bg-emerald-500' : 'bg-slate-600'}`} />
              <span className="text-sm font-medium text-white truncate">{c.name}</span>
            </div>
            <p className="text-xs text-slate-400 mt-1 ml-[18px]">
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

/* ── Policies Panel ──────────────────────────────────────────────── */

function PoliciesPanel({
  policies,
  onToggle,
  toggling,
}: {
  policies: RoutingPolicy[]
  onToggle: (id: string, active: boolean) => void
  toggling: Set<string>
}) {
  if (policies.length === 0) return <p className="text-sm text-slate-500 italic py-6 text-center">No routing policies</p>
  return (
    <div className="space-y-2">
      {policies.map((p) => (
        <div
          key={p.id}
          className="flex items-center justify-between rounded-xl border border-slate-700/50 bg-slate-800/40 p-3.5 hover:bg-slate-800/60 transition"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <span className={`inline-block h-2 w-2 rounded-full flex-shrink-0 ${p.is_active ? 'bg-emerald-500' : 'bg-slate-600'}`} />
              <span className="text-sm font-medium text-white truncate">{p.alias}</span>
            </div>
            <p className="text-xs text-slate-400 mt-1 ml-[18px]">
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

/* ── Status Badge ────────────────────────────────────────────────── */

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { icon: typeof CheckCircle2; cls: string }> = {
    success: { icon: CheckCircle2, cls: 'text-emerald-400 bg-emerald-500/10' },
    cache_hit: { icon: Database, cls: 'text-blue-400 bg-blue-500/10' },
    error: { icon: XCircle, cls: 'text-red-400 bg-red-500/10' },
    timeout: { icon: Timer, cls: 'text-amber-400 bg-amber-500/10' },
    blocked: { icon: AlertTriangle, cls: 'text-red-400 bg-red-500/10' },
  }
  const c = config[status] || { icon: Activity, cls: 'text-slate-400 bg-slate-500/10' }
  const Icon = c.icon
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${c.cls}`}>
      <Icon className="h-3 w-3" />
      {status.replace(/_/g, ' ')}
    </span>
  )
}

/* ── Request Feed ────────────────────────────────────────────────── */

function RequestFeed({
  requests,
  expandedId,
  setExpandedId,
}: {
  requests: GatewayRequestLog[]
  expandedId: string | null
  setExpandedId: (id: string | null) => void
}) {
  if (requests.length === 0) {
    return (
      <div className="py-12 text-center">
        <Activity className="h-8 w-8 text-slate-600 mx-auto mb-3" />
        <p className="text-sm text-slate-500">No recent requests</p>
        <p className="text-xs text-slate-600 mt-1">Inject a test request or send traffic through the gateway</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-slate-800/50">
      {requests.map((req) => {
        const expanded = expandedId === req.id
        return (
          <div key={req.id}>
            <button
              onClick={() => setExpandedId(expanded ? null : req.id)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-800/40 transition"
            >
              <StatusBadge status={req.status} />
              <span className="text-sm font-medium text-white truncate flex-1">{req.model_requested}</span>
              <span className="text-xs text-slate-400 tabular-nums">{req.latency_ms}ms</span>
              <span className="text-xs text-slate-500 tabular-nums w-12 text-right">{(req.input_tokens ?? 0) + (req.output_tokens ?? 0)} t</span>
              <span className="text-xs text-slate-500 tabular-nums w-16 text-right">
                {new Date(req.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              {expanded ? <ChevronUp className="h-3.5 w-3.5 text-slate-500" /> : <ChevronDown className="h-3.5 w-3.5 text-slate-500" />}
            </button>
            {expanded && (
              <div className="mx-4 mb-3 rounded-xl border border-slate-700/50 bg-slate-900/60 p-4 space-y-4">
                <p className="text-xs font-semibold text-slate-300">Request Trace</p>
                <div className="flex items-center gap-1">
                  {stages.map((stage, i) => {
                    const isHit = stage.id === 'execution' && req.cache_hit
                    const isBlocked = req.status === 'blocked' && stage.id === 'enforcement'
                    const Icon = stage.icon
                    return (
                      <div key={stage.id} className="flex items-center gap-1 flex-1">
                        {i > 0 && <ArrowRight className="h-3 w-3 text-slate-600 flex-shrink-0" />}
                        <div className={`flex-1 rounded-lg px-2 py-2 text-center border text-[10px] font-medium
                          ${isBlocked
                            ? 'bg-red-500/15 border-red-500/30 text-red-400'
                            : isHit
                            ? 'bg-blue-500/15 border-blue-500/30 text-blue-400'
                            : 'bg-slate-800/60 border-slate-700/50 text-slate-400'
                          }`}>
                          <Icon className="h-3.5 w-3.5 mx-auto mb-0.5" />
                          {stage.label}
                          {isHit && <span className="block text-[9px] text-blue-300">HIT</span>}
                          {isBlocked && <span className="block text-[9px] text-red-300">BLOCKED</span>}
                        </div>
                      </div>
                    )
                  })}
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-slate-500 block mb-0.5">Requested</span>
                    <p className="font-medium text-white">{req.model_requested}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-0.5">Used</span>
                    <p className="font-medium text-white">{req.model_used || req.model_requested}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-0.5">Tokens</span>
                    <p className="font-medium text-white">{num(req.input_tokens)} in / {num(req.output_tokens)} out</p>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-0.5">Decision</span>
                    <p className="font-medium text-white">{req.decision_reason || 'direct'}</p>
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

/* ── Inject Panel ────────────────────────────────────────────────── */

function InjectPanel({
  open,
  onClose,
  apiKey,
  routes,
  onSent,
}: {
  open: boolean
  onClose: () => void
  apiKey: string
  routes: GatewayRoute[]
  onSent: () => void
}) {
  const modelOptions = Array.from(
    new Map(
      routes
        .filter((route) => route.is_active)
        .flatMap((route) => [
          [route.alias, `${route.alias} (${route.provider} → ${route.target_model})`],
          [route.target_model, `${route.target_model} (${route.provider})`],
        ])
    )
  )
  const [model, setModel] = useState(modelOptions[0]?.[0] ?? 'gpt-4o')
  const [prompt, setPrompt] = useState('Say hello in one sentence.')
  const [streamEnabled, setStreamEnabled] = useState(true)
  const [cacheEnabled, setCacheEnabled] = useState(true)
  const [semanticCacheEnabled, setSemanticCacheEnabled] = useState(false)
  const [contextCompilerEnabled, setContextCompilerEnabled] = useState(false)
  const [intelligentRoutingEnabled, setIntelligentRoutingEnabled] = useState(false)
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; text: string; done: boolean } | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const resultRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!modelOptions.some(([value]) => value === model) && modelOptions[0]) {
      setModel(modelOptions[0][0])
    }
  }, [model, modelOptions])

  function cancel() {
    abortRef.current?.abort()
    abortRef.current = null
    setSending(false)
  }

  async function send() {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setSending(true)
    setResult(null)
    try {
      const res = await fetch('/api/gateway/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: prompt }],
          max_tokens: 100,
          stream: streamEnabled,
          cache: cacheEnabled,
          semantic_cache: semanticCacheEnabled,
          context_compiler: contextCompilerEnabled,
          intelligent_routing: intelligentRoutingEnabled,
          metadata: { feature_tag: 'pipeline-designer' },
        }),
        signal: controller.signal,
      })

      if (!res.ok) {
        const contentType = res.headers.get('content-type') || ''
        const data = contentType.includes('application/json') ? await res.json() : await res.text()
        setResult({ ok: false, text: `Error ${res.status}: ${typeof data === 'string' ? data.slice(0, 500) : JSON.stringify(data)}`, done: true })
        setSending(false)
        return
      }

      const contentType = res.headers.get('content-type') || ''
      if (streamEnabled && contentType.includes('text/event-stream') && res.body) {
        setResult({ ok: true, text: '', done: false })
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let accumulated = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const payload = line.slice(6).trim()
            if (payload === '[DONE]') continue
            try {
              const chunk = JSON.parse(payload)
              const delta = chunk.choices?.[0]?.delta?.content
              if (delta) {
                accumulated += delta
                setResult({ ok: true, text: accumulated, done: false })
                if (resultRef.current) resultRef.current.scrollTop = resultRef.current.scrollHeight
              }
            } catch { /* skip malformed chunks */ }
          }
        }
        setResult({ ok: true, text: accumulated || '(empty response)', done: true })
        toast.success('Request traced through pipeline')
        onSent()
      } else {
        const data = await res.json().catch(() => res.text())
        const content = typeof data === 'string'
          ? data
          : data.choices?.[0]?.message?.content || JSON.stringify(data)
        setResult({ ok: true, text: content, done: true })
        toast.success('Request traced through pipeline')
        onSent()
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        setResult({ ok: false, text: `Network error: ${e.message}`, done: true })
      }
    } finally {
      setSending(false)
      abortRef.current = null
    }
  }

  if (!open) return null

  return (
    <div className="rounded-2xl border border-indigo-500/20 bg-slate-800/60 backdrop-blur p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Send className="h-4 w-4 text-indigo-400" />
          Inject Test Request
        </h3>
        <button onClick={onClose} className="text-slate-400 hover:text-white transition">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="text-xs text-slate-400 block mb-1.5">Model</label>
          <select className={inputCls} value={model} onChange={(e) => setModel(e.target.value)}>
            {modelOptions.length === 0 && <option value="gpt-4o">gpt-4o</option>}
            {modelOptions.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-400 block mb-1.5">Prompt</label>
          <input className={inputCls} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Say hello" />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {([
          ['Stream', streamEnabled, setStreamEnabled],
          ['Exact Cache', cacheEnabled, setCacheEnabled],
          ['Semantic Cache', semanticCacheEnabled, setSemanticCacheEnabled],
          ['Compiler', contextCompilerEnabled, setContextCompilerEnabled],
          ['Routing', intelligentRoutingEnabled, setIntelligentRoutingEnabled],
        ] as const).map(([label, checked, setter]) => (
          <button
            key={String(label)}
            type="button"
            onClick={() => (setter as (v: boolean) => void)(!checked)}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition
              ${checked
                ? label === 'Stream'
                  ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                  : 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
                : 'bg-slate-800 text-slate-400 border-slate-700 hover:border-slate-600'
              }`}
          >
            {label as string}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={sending ? cancel : send}
          className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition flex-shrink-0
            ${sending
              ? 'bg-red-500/80 text-white hover:bg-red-600'
              : 'bg-indigo-500 text-white hover:bg-indigo-600 shadow-lg shadow-indigo-500/20'
            }`}
        >
          {sending ? (
            <>
              <X className="h-3.5 w-3.5" />
              Cancel
            </>
          ) : (
            <>
              <Play className="h-3.5 w-3.5" />
              Send & Trace
            </>
          )}
        </button>
      </div>

      {result && (
        <div
          ref={resultRef}
          className={`rounded-xl border p-4 text-sm max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed
            ${result.ok
              ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-200'
              : 'border-red-500/20 bg-red-500/5 text-red-300'
            }`}
        >
          {result.text}
          {sending && result.ok && (
            <span className="inline-block w-2 h-4 bg-emerald-400 ml-0.5 animate-pulse rounded-sm" />
          )}
        </div>
      )}
    </div>
  )
}

/* ── Stat Card ───────────────────────────────────────────────────── */

function StatCard({ label, value, sub, icon: Icon }: { label: string; value: string | number; sub?: string; icon: typeof Activity }) {
  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-4 py-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="h-3.5 w-3.5 text-slate-500" />
        <p className="text-xs text-slate-400">{label}</p>
      </div>
      <p className="text-xl font-semibold text-white tabular-nums">{value}{sub && <span className="text-sm text-slate-500 font-normal">{sub}</span>}</p>
    </div>
  )
}

/* ── Main Page ───────────────────────────────────────────────────── */

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
      const updated = await updateGatewayRoute(apiKey, id, { is_active: active })
      setRoutes((prev) => prev.map((r) => (r.id === id ? updated : r)))
      toast.success(`Route ${active ? 'enabled' : 'disabled'}`)
    } catch {
      toast.error('Failed to update route')
    } finally {
      setToggling((s) => { const n = new Set(s); n.delete(id); return n })
    }
  }

  async function toggleRouteFeature(
    id: string,
    feature: 'semantic_cache_enabled' | 'context_compiler_enabled' | 'intelligent_routing_enabled',
    enabled: boolean,
  ) {
    const key = `${id}:${feature}`
    setToggling((s) => new Set(s).add(key))
    try {
      const updated = await updateGatewayRoute(apiKey, id, { [feature]: enabled })
      setRoutes((prev) => prev.map((r) => (r.id === id ? updated : r)))
      toast.success(`${feature.replace(/_/g, ' ')} ${enabled ? 'enabled' : 'disabled'}`)
    } catch {
      toast.error('Failed to update route feature')
    } finally {
      setToggling((s) => { const n = new Set(s); n.delete(key); return n })
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
  const avgLatencyMs = stats?.avg_latency_ms

  const tabs: { id: Tab; label: string; icon: typeof Activity; count: number }[] = [
    { id: 'routes', label: 'Routes', icon: GitBranch, count: routes.length },
    { id: 'guardrails', label: 'Guardrails', icon: Shield, count: posture?.enforcement_overlay?.guardrail_rules ?? 0 },
    { id: 'cache', label: 'Cache', icon: Database, count: cacheConfigs.length },
    { id: 'policies', label: 'Policies', icon: Zap, count: policies.length },
  ]

  function selectStage(stage: string) {
    if (stage === 'routing' || stage === 'execution') setActiveTab('routes')
    if (stage === 'reporting') setActiveTab('cache')
    if (stage === 'enforcement') setActiveTab('guardrails')
  }

  return (
    <div className="mx-auto max-w-[1600px] space-y-6 px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="flex items-center justify-center h-9 w-9 rounded-xl bg-indigo-500/15 border border-indigo-500/20">
              <Cpu className="h-5 w-5 text-indigo-400" />
            </div>
            Pipeline Designer
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Trace requests, toggle features, inject routing, observe everything.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setInjectOpen(!injectOpen)}
            className="flex items-center gap-2 rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 transition shadow-lg shadow-indigo-500/20"
          >
            <Send className="h-3.5 w-3.5" />
            Inject Request
          </button>
          <button
            onClick={() => { setLoading(true); fetchAll() }}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Inject Panel */}
      <InjectPanel open={injectOpen} onClose={() => setInjectOpen(false)} apiKey={apiKey} routes={routes} onSent={fetchAll} />

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Active Routes" value={activeRoutes} sub={`/${routes.length}`} icon={GitBranch} />
        <StatCard label="Total Requests" value={num(totalRequests)} icon={Activity} />
        <StatCard label="Cache Hit Rate" value={`${(Number(cacheRate) * 100).toFixed(1)}%`} icon={Database} />
        <StatCard label="Avg Latency" value={avgLatencyMs == null ? '—' : `${Number(avgLatencyMs).toFixed(0)}ms`} icon={Clock} />
      </div>

      {/* Pipeline Flow */}
      <PipelineGraph activeStage={activeStage} setActiveStage={setActiveStage} requestCount={requests.length} onStageSelect={selectStage} />

      {/* Main Content */}
      <div className="grid gap-6 xl:grid-cols-5">
        {/* Control Panels */}
        <div className="xl:col-span-2 space-y-4">
          <div className="rounded-2xl border border-slate-700/50 bg-slate-800/30 overflow-hidden">
            <div className="flex border-b border-slate-700/50">
              {tabs.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-3 text-xs font-medium transition
                    ${activeTab === t.id
                      ? 'text-indigo-300 border-b-2 border-indigo-500 bg-indigo-500/5'
                      : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800/50'}`}
                >
                  <t.icon className="h-3.5 w-3.5" />
                  {t.label}
                  <span className="rounded-full bg-slate-700/60 px-1.5 py-0.5 text-[10px] tabular-nums">{t.count}</span>
                </button>
              ))}
            </div>
            <div className="p-3 max-h-[520px] overflow-y-auto">
              {activeTab === 'routes' && <RoutesPanel routes={routes} onToggle={toggleRoute} onFeatureToggle={toggleRouteFeature} toggling={toggling} />}
              {activeTab === 'guardrails' && (
                <div className="py-6 space-y-3 text-center">
                  <Shield className="h-8 w-8 text-slate-600 mx-auto" />
                  <div>
                    <p className="text-sm text-slate-300">
                      {posture?.enforcement_overlay?.guardrail_rules ?? 0} rules · {posture?.enforcement_overlay?.blocked_events_30d ?? 0} blocked (30d)
                    </p>
                    <p className="text-xs text-slate-500 mt-1">{posture?.enforcement_overlay?.tool_policies ?? 0} tool policies</p>
                  </div>
                  <Link href="/guardrails" className="inline-flex items-center gap-1 text-sm text-indigo-400 hover:text-indigo-300 transition">
                    Manage guardrails <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              )}
              {activeTab === 'cache' && <CachePanel configs={cacheConfigs} onToggle={toggleCache} toggling={toggling} />}
              {activeTab === 'policies' && <PoliciesPanel policies={policies} onToggle={togglePolicy} toggling={toggling} />}
            </div>
          </div>

          {posture && (
            <div className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-4">
              <h3 className="text-xs font-semibold text-white mb-3">Runtime</h3>
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                {[
                  ['Data Plane', posture.pipeline_model.execution_runtime.data_plane],
                  ['Control Plane', posture.pipeline_model.execution_runtime.control_plane],
                  ['Providers', posture.pipeline_model.routing_nodes.distinct_providers],
                  ['Groups', posture.pipeline_model.routing_nodes.routing_groups],
                ].map(([label, value]) => (
                  <div key={String(label)} className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">{label as string}</span>
                    <span className="font-medium text-white">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Live Feed */}
        <div className="xl:col-span-3">
          <div className="rounded-2xl border border-slate-700/50 bg-slate-800/30 overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-700/50 px-4 py-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                Live Request Feed
              </h3>
              <span className="text-xs text-slate-500">{requests.length} requests · 5s poll</span>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              <RequestFeed
                requests={requests}
                expandedId={expandedRequest}
                setExpandedId={setExpandedRequest}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
