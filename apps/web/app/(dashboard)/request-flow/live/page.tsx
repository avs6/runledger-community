'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import {
  Activity, ArrowRight, CheckCircle2, XCircle, Loader2,
  GitBranch, Shield, Zap, Layers, Clock, Radio,
  ChevronDown, ChevronUp, AlertTriangle, Database,
  Pause, Play, Filter, RefreshCw,
} from 'lucide-react'
import { getRuns, getRun, getRunGovernanceContext } from '@/lib/api'
import { num } from '@/lib/utils'
import type {
  RunListItem, RunDetailResponse, RunGovernanceContextResponse,
  ProviderCallDetail, ToolCallDetail, SpanDetail,
} from '@/types/api'

/* ── Pipeline stages ─────────────────────────────────────────────── */

const stages = [
  { id: 'ingest', label: 'Ingest', icon: Layers, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
  { id: 'routing', label: 'Route', icon: GitBranch, color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/20' },
  { id: 'enforce', label: 'Enforce', icon: Shield, color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/20' },
  { id: 'execute', label: 'Execute', icon: Zap, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
  { id: 'report', label: 'Report', icon: Activity, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
]

function stageForRun(run: RunListItem): number {
  if (run.status === 'running') return 3
  if (run.status === 'failed') return 2
  return 4
}

/* ── Status rendering ────────────────────────────────────────────── */

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'succeeded':
      return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
    case 'failed':
      return <XCircle className="h-3.5 w-3.5 text-red-400" />
    case 'running':
      return <Loader2 className="h-3.5 w-3.5 text-blue-400 animate-spin" />
    case 'cancelled':
      return <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
    default:
      return <Activity className="h-3.5 w-3.5 text-slate-400" />
  }
}

function statusColor(status: string): string {
  switch (status) {
    case 'succeeded': return 'text-emerald-400 bg-emerald-500/10'
    case 'failed': return 'text-red-400 bg-red-500/10'
    case 'running': return 'text-blue-400 bg-blue-500/10'
    case 'cancelled': return 'text-amber-400 bg-amber-500/10'
    default: return 'text-slate-400 bg-slate-500/10'
  }
}

/* ── Mini pipeline trace ─────────────────────────────────────────── */

function MiniPipeline({ run }: { run: RunListItem }) {
  const reached = stageForRun(run)
  const failed = run.status === 'failed'
  const running = run.status === 'running'
  return (
    <div className="flex items-center gap-0.5">
      {stages.map((stage, i) => {
        const Icon = stage.icon
        const isActive = i <= reached
        const isFail = failed && i === reached
        const isRunning = running && i === reached
        return (
          <div key={stage.id} className="flex items-center gap-0.5">
            {i > 0 && (
              <div className={`w-3 h-px ${isActive ? 'bg-slate-500' : 'bg-slate-800'}`} />
            )}
            <div
              className={`rounded px-1 py-0.5 border text-[9px] font-medium flex items-center gap-0.5
                ${isFail
                  ? 'bg-red-500/15 border-red-500/30 text-red-400'
                  : isRunning
                  ? 'bg-blue-500/15 border-blue-500/30 text-blue-400'
                  : isActive
                  ? `${stage.bg} ${stage.color}`
                  : 'bg-slate-900/40 border-slate-800 text-slate-600'
                }`}
              title={stage.label}
            >
              <Icon className="h-2.5 w-2.5" />
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ── Detail label helper ──────────────────────────────────────────── */

function DetailLabel({ children }: { children: React.ReactNode }) {
  return <span className="text-slate-500 block mb-0.5 text-[11px]">{children}</span>
}

function DetailValue({ children, mono }: { children: React.ReactNode; mono?: boolean }) {
  return <p className={`font-medium text-white ${mono ? 'font-mono text-[10px]' : ''} truncate`}>{children}</p>
}

function SectionHeader({ icon: Icon, label, color }: { icon: typeof Shield; label: string; color: string }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <Icon className={`h-3.5 w-3.5 ${color}`} />
      <span className="text-xs font-semibold text-slate-300">{label}</span>
    </div>
  )
}

function Badge({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <span className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium ${color}`}>
      {children}
    </span>
  )
}

/* ── Expanded run detail ─────────────────────────────────────────── */

function RunDetail({ run, apiKey }: { run: RunListItem; apiKey: string }) {
  const reached = stageForRun(run)
  const failed = run.status === 'failed'
  const [detail, setDetail] = useState<RunDetailResponse | null>(null)
  const [governance, setGovernance] = useState<RunGovernanceContextResponse | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(true)

  useEffect(() => {
    if (!apiKey) return
    setLoadingDetail(true)
    Promise.all([
      getRun(apiKey, run.id).catch(() => null),
      getRunGovernanceContext(apiKey, run.id).catch(() => null),
    ]).then(([d, g]) => {
      setDetail(d)
      setGovernance(g)
      setLoadingDetail(false)
    })
  }, [apiKey, run.id])

  const providerCalls = detail?.provider_calls ?? []
  const toolCalls = detail?.tool_calls ?? []
  const spans = detail?.spans ?? []
  const securityEvents = governance?.security_events ?? []
  const toolEvidence = governance?.tool_evidence ?? []
  const alertEvidence = governance?.alert_evidence ?? []
  const auditEvents = governance?.audit_events ?? []
  const tags = governance?.tags ?? []

  const hasCacheHit = providerCalls.some(p => (p.cached_input_tokens ?? 0) > 0)
  const totalCached = providerCalls.reduce((s, p) => s + (p.cached_input_tokens ?? 0), 0)
  const hasGovernanceActivity = securityEvents.length > 0 || toolEvidence.length > 0 || alertEvidence.length > 0

  return (
    <div className="mx-4 mb-3 rounded-xl border border-slate-700/50 bg-slate-900/60 p-4 space-y-5">
      {/* Pipeline Trace */}
      <div>
        <p className="text-xs font-semibold text-slate-300 mb-3">Pipeline Trace</p>
        <div className="flex items-center gap-1">
          {stages.map((stage, i) => {
            const Icon = stage.icon
            const isActive = i <= reached
            const isFail = failed && i === reached
            return (
              <div key={stage.id} className="flex items-center gap-1 flex-1">
                {i > 0 && <ArrowRight className="h-3 w-3 text-slate-600 flex-shrink-0" />}
                <div className={`flex-1 rounded-lg px-2 py-2 text-center border text-[10px] font-medium
                  ${isFail
                    ? 'bg-red-500/15 border-red-500/30 text-red-400'
                    : isActive
                    ? `${stage.bg} ${stage.color}`
                    : 'bg-slate-800/60 border-slate-700/50 text-slate-600'
                  }`}>
                  <Icon className="h-3.5 w-3.5 mx-auto mb-0.5" />
                  {stage.label}
                  {isFail && <span className="block text-[9px] text-red-300">FAILED</span>}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div><DetailLabel>Feature</DetailLabel><DetailValue>{run.feature_tag || 'untagged'}</DetailValue></div>
        <div><DetailLabel>Model</DetailLabel><DetailValue>{run.primary_model || '—'}</DetailValue></div>
        <div><DetailLabel>Tokens</DetailLabel><DetailValue>{run.total_input_tokens != null ? `${num(run.total_input_tokens)} in / ${num(run.total_output_tokens ?? 0)} out` : '—'}</DetailValue></div>
        <div><DetailLabel>Cost</DetailLabel><DetailValue>{run.total_cost_usd != null ? `$${Number(run.total_cost_usd).toFixed(6)}` : '—'}</DetailValue></div>
        <div><DetailLabel>Duration</DetailLabel><DetailValue>{run.duration_ms != null ? `${num(run.duration_ms)}ms` : '—'}</DetailValue></div>
        <div><DetailLabel>User</DetailLabel><DetailValue>{run.end_user_id || '—'}</DetailValue></div>
        <div><DetailLabel>Session</DetailLabel><DetailValue>{run.session_id || '—'}</DetailValue></div>
        <div><DetailLabel>Run ID</DetailLabel><DetailValue mono>{run.id}</DetailValue></div>
      </div>

      {loadingDetail ? (
        <div className="flex items-center gap-2 text-xs text-slate-500 py-2">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Loading pipeline details…
        </div>
      ) : (
        <>
          {/* Provider Calls — Route & Execution */}
          {providerCalls.length > 0 && (
            <div className="rounded-lg border border-slate-700/40 bg-slate-800/40 p-3">
              <SectionHeader icon={Zap} label={`Provider Calls (${providerCalls.length})`} color="text-emerald-400" />
              <div className="space-y-2">
                {providerCalls.map((pc, i) => (
                  <div key={pc.id || i} className="flex items-center gap-3 flex-wrap">
                    <Badge color={pc.status === 'success' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}>
                      {pc.status}
                    </Badge>
                    <span className="text-xs font-medium text-white">{pc.provider}</span>
                    <span className="text-xs text-slate-300">{pc.model}</span>
                    <span className="text-[11px] text-slate-400 tabular-nums">{pc.input_tokens ?? 0} in / {pc.output_tokens ?? 0} out</span>
                    {(pc.cached_input_tokens ?? 0) > 0 && (
                      <Badge color="bg-blue-500/10 text-blue-400 border-blue-500/20">
                        {pc.cached_input_tokens} cached
                      </Badge>
                    )}
                    {pc.latency_ms != null && (
                      <span className="text-[11px] text-slate-500 tabular-nums">{pc.latency_ms}ms</span>
                    )}
                    {pc.cost_usd != null && (
                      <span className="text-[11px] text-slate-500">${Number(pc.cost_usd).toFixed(6)}</span>
                    )}
                    {pc.error_type && (
                      <Badge color="bg-red-500/10 text-red-400 border-red-500/20">{pc.error_type}</Badge>
                    )}
                  </div>
                ))}
              </div>
              {hasCacheHit && (
                <div className="mt-2 flex items-center gap-2">
                  <Badge color="bg-blue-500/10 text-blue-400 border-blue-500/20">
                    <Database className="h-2.5 w-2.5 mr-1" />
                    Cache: {totalCached} tokens saved
                  </Badge>
                </div>
              )}
            </div>
          )}

          {/* Spans — Routing info */}
          {spans.length > 0 && (
            <div className="rounded-lg border border-slate-700/40 bg-slate-800/40 p-3">
              <SectionHeader icon={GitBranch} label={`Spans (${spans.length})`} color="text-indigo-400" />
              <div className="space-y-1.5">
                {spans.map((span) => (
                  <div key={span.id} className="flex items-center gap-3 flex-wrap">
                    <Badge color={
                      span.status === 'succeeded' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : span.status === 'failed' ? 'bg-red-500/10 text-red-400 border-red-500/20'
                      : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
                    }>
                      {span.span_type}
                    </Badge>
                    <span className="text-xs font-medium text-white">{span.name}</span>
                    {span.cost_usd != null && (
                      <span className="text-[11px] text-slate-500">${Number(span.cost_usd).toFixed(6)}</span>
                    )}
                    <span className="text-[11px] text-slate-500">
                      {span.started_at ? new Date(span.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''}
                      {span.ended_at ? ` → ${new Date(span.ended_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}` : ' (running)'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tool Calls — Execution details */}
          {toolCalls.length > 0 && (
            <div className="rounded-lg border border-slate-700/40 bg-slate-800/40 p-3">
              <SectionHeader icon={Zap} label={`Tool Calls (${toolCalls.length})`} color="text-violet-400" />
              <div className="space-y-1.5">
                {toolCalls.map((tc) => (
                  <div key={tc.id} className="flex items-center gap-3 flex-wrap">
                    <Badge color={tc.status === 'success' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}>
                      {tc.status}
                    </Badge>
                    <span className="text-xs font-medium text-white">{tc.tool_name}</span>
                    <Badge color="bg-slate-500/10 text-slate-400 border-slate-500/20">{tc.tool_type}</Badge>
                    {tc.risk_score != null && tc.risk_score > 0 && (
                      <Badge color={tc.risk_score > 50
                        ? 'bg-red-500/10 text-red-400 border-red-500/20'
                        : tc.risk_score > 25
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
                      }>
                        risk: {tc.risk_score}
                      </Badge>
                    )}
                    {tc.duration_ms != null && (
                      <span className="text-[11px] text-slate-500 tabular-nums">{tc.duration_ms}ms</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Enforcement — Guardrails & Governance */}
          {(hasGovernanceActivity || tags.length > 0) && (
            <div className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3">
              <SectionHeader icon={Shield} label="Enforcement & Governance" color="text-rose-400" />

              {tags.length > 0 && (
                <div className="mb-3">
                  <span className="text-[11px] text-slate-500 block mb-1">Tags</span>
                  <div className="flex flex-wrap gap-1">
                    {tags.map(tag => (
                      <Badge key={tag} color="bg-indigo-500/10 text-indigo-400 border-indigo-500/20">{tag}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {toolEvidence.length > 0 && (
                <div className="mb-3">
                  <span className="text-[11px] text-slate-500 block mb-1">Tool Policies</span>
                  <div className="space-y-1.5">
                    {toolEvidence.map((te, i) => (
                      <div key={i} className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-medium text-white">{te.tool_name}</span>
                        <Badge color="bg-slate-500/10 text-slate-400 border-slate-500/20">{te.tool_type}</Badge>
                        {te.risk_score != null && te.risk_score > 0 && (
                          <Badge color={te.risk_score > 50 ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}>
                            risk: {te.risk_score}
                          </Badge>
                        )}
                        {te.matched_policy_count > 0 && (
                          <Badge color="bg-rose-500/10 text-rose-400 border-rose-500/20">
                            {te.matched_policy_count} {te.matched_policy_count === 1 ? 'policy' : 'policies'}
                          </Badge>
                        )}
                        {te.matched_policy_names.map(name => (
                          <Badge key={name} color="bg-rose-500/10 text-rose-300 border-rose-500/20">{name}</Badge>
                        ))}
                        {te.matched_policy_actions.map(action => (
                          <Badge key={action} color="bg-amber-500/10 text-amber-400 border-amber-500/20">{action}</Badge>
                        ))}
                        {te.registry_runtime_enforcement && (
                          <Badge color="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">enforced</Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {securityEvents.length > 0 && (
                <div className="mb-3">
                  <span className="text-[11px] text-slate-500 block mb-1">Security Events</span>
                  <div className="space-y-1.5">
                    {securityEvents.map((se) => (
                      <div key={se.id} className="flex items-center gap-2 flex-wrap">
                        <Badge color="bg-red-500/10 text-red-400 border-red-500/20">
                          <AlertTriangle className="h-2.5 w-2.5 mr-1" />
                          {se.event_type}
                        </Badge>
                        {se.tool_name && <span className="text-xs text-white">{se.tool_name}</span>}
                        {se.end_user_id && <span className="text-[11px] text-slate-500">{se.end_user_id}</span>}
                        <span className="text-[11px] text-slate-500">
                          {new Date(se.detected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {alertEvidence.length > 0 && (
                <div>
                  <span className="text-[11px] text-slate-500 block mb-1">Alert Rules Triggered</span>
                  <div className="space-y-1.5">
                    {alertEvidence.map((ae) => (
                      <div key={ae.id} className="flex items-center gap-2 flex-wrap">
                        <Badge color="bg-amber-500/10 text-amber-400 border-amber-500/20">
                          {ae.rule_name}
                        </Badge>
                        <span className="text-[11px] text-slate-400">metric: {ae.metric_value}</span>
                        <span className="text-[11px] text-slate-500">
                          {new Date(ae.fired_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                        {ae.resolved_at && (
                          <Badge color="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">resolved</Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* No governance activity */}
          {!hasGovernanceActivity && tags.length === 0 && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Shield className="h-3.5 w-3.5" />
              No guardrails triggered, no security events
            </div>
          )}
        </>
      )}
    </div>
  )
}

/* ── Stats bar ───────────────────────────────────────────────────── */

function StatCard({ label, value, icon: Icon }: { label: string; value: string | number; icon: typeof Activity }) {
  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-4 py-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="h-3.5 w-3.5 text-slate-500" />
        <p className="text-xs text-slate-400">{label}</p>
      </div>
      <p className="text-xl font-semibold text-white tabular-nums">{value}</p>
    </div>
  )
}

/* ── Main page ───────────────────────────────────────────────────── */

export default function LivePipelinePage() {
  const { data: session } = useSession()
  const apiKey = session?.apiKey || ''

  const [runs, setRuns] = useState<RunListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [paused, setPaused] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [modelFilter, setModelFilter] = useState<string>('all')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchRuns = useCallback(async () => {
    if (!apiKey) return
    try {
      const data = await getRuns(apiKey, { limit: 100 })
      setRuns(data.items)
      setLastUpdated(new Date())
    } catch { /* swallow */ }
    finally { setLoading(false) }
  }, [apiKey])

  useEffect(() => {
    fetchRuns()
    if (!paused) {
      pollRef.current = setInterval(fetchRuns, 2000)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [fetchRuns, paused])

  const models = Array.from(new Set(runs.map(r => r.primary_model).filter(Boolean))) as string[]
  const statuses = Array.from(new Set(runs.map(r => r.status)))

  const filtered = runs.filter(r => {
    if (statusFilter !== 'all' && r.status !== statusFilter) return false
    if (modelFilter !== 'all' && r.primary_model !== modelFilter) return false
    return true
  })

  const succeeded = runs.filter(r => r.status === 'succeeded').length
  const failed = runs.filter(r => r.status === 'failed').length
  const running = runs.filter(r => r.status === 'running').length
  const totalTokens = runs.reduce((s, r) => s + (r.total_input_tokens ?? 0) + (r.total_output_tokens ?? 0), 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="flex items-center justify-center h-9 w-9 rounded-xl bg-emerald-500/15 border border-emerald-500/20">
              <Radio className="h-5 w-5 text-emerald-400" />
            </div>
            Live Pipeline
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Real-time view of requests flowing through the pipeline.
            {lastUpdated && (
              <span className="ml-2 text-slate-500">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPaused(!paused)}
            className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition
              ${paused
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20'
                : 'border-amber-500/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20'
              }`}
          >
            {paused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
            {paused ? 'Resume' : 'Pause'}
          </button>
          <button
            onClick={() => { setLoading(true); fetchRuns() }}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <Link
            href="/pipeline"
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 transition"
          >
            Pipeline Designer
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <StatCard label="Total" value={runs.length} icon={Activity} />
        <StatCard label="Succeeded" value={succeeded} icon={CheckCircle2} />
        <StatCard label="Failed" value={failed} icon={XCircle} />
        <StatCard label="Running" value={running} icon={Loader2} />
        <StatCard label="Tokens" value={num(totalTokens).toLocaleString()} icon={Database} />
      </div>

      {/* Pipeline overview bar */}
      <div className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              {!paused && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              )}
              <span className={`relative inline-flex rounded-full h-2 w-2 ${paused ? 'bg-amber-500' : 'bg-emerald-500'}`} />
            </span>
            Request Pipeline
          </h2>
          <span className="text-xs text-slate-500">{paused ? 'Paused' : 'Polling every 2s'}</span>
        </div>
        <div className="flex items-center justify-between gap-2">
          {stages.map((stage, i) => {
            const Icon = stage.icon
            return (
              <div key={stage.id} className="flex items-center gap-2 flex-1">
                {i > 0 && (
                  <div className="flex-shrink-0 flex items-center">
                    <div className="w-6 h-px bg-slate-700" />
                    <ArrowRight className="h-3 w-3 text-slate-600 -ml-1" />
                  </div>
                )}
                <div className={`flex-1 rounded-xl px-3 py-3.5 text-center border ${stage.bg}`}>
                  <Icon className={`h-5 w-5 mx-auto ${stage.color}`} />
                  <p className="mt-1.5 text-xs font-semibold text-white">{stage.label}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Filters + Feed */}
      <div className="rounded-2xl border border-slate-700/50 bg-slate-800/30 overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-700/50 px-4 py-3 flex-wrap gap-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              {!paused && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              )}
              <span className={`relative inline-flex rounded-full h-2 w-2 ${paused ? 'bg-amber-500' : 'bg-emerald-500'}`} />
            </span>
            Live Feed
          </h3>
          <div className="flex items-center gap-2">
            <Filter className="h-3.5 w-3.5 text-slate-500" />
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 text-xs text-slate-300 px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="all">All statuses</option>
              {statuses.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select
              value={modelFilter}
              onChange={e => setModelFilter(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 text-xs text-slate-300 px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="all">All models</option>
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <span className="text-xs text-slate-500 tabular-nums">{filtered.length} runs</span>
          </div>
        </div>

        <div className="max-h-[700px] overflow-y-auto">
          {filtered.length === 0 && (
            <div className="py-16 text-center">
              <Activity className="h-8 w-8 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-500">No requests yet</p>
              <p className="text-xs text-slate-600 mt-1">Send traffic through the API or use the Pipeline Designer to inject test requests</p>
            </div>
          )}
          <div className="divide-y divide-slate-800/50">
            {filtered.map(run => {
              const expanded = expandedId === run.id
              const totalTok = (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0)
              return (
                <div key={run.id}>
                  <button
                    onClick={() => setExpandedId(expanded ? null : run.id)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-800/40 transition"
                  >
                    <StatusIcon status={run.status} />
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${statusColor(run.status)}`}>
                      {run.status}
                    </span>
                    <span className="text-xs text-slate-400 truncate max-w-[120px]">{run.feature_tag || 'untagged'}</span>
                    <span className="text-sm font-medium text-white truncate flex-1">{run.primary_model || '—'}</span>
                    <MiniPipeline run={run} />
                    <span className="text-xs text-slate-400 tabular-nums w-16 text-right">{run.duration_ms != null ? `${num(run.duration_ms)}ms` : '—'}</span>
                    <span className="text-xs text-slate-500 tabular-nums w-12 text-right">{totalTok > 0 ? `${num(totalTok)}t` : '—'}</span>
                    <span className="text-xs text-slate-500 tabular-nums w-16 text-right">
                      {new Date(run.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                    {expanded ? <ChevronUp className="h-3.5 w-3.5 text-slate-500" /> : <ChevronDown className="h-3.5 w-3.5 text-slate-500" />}
                  </button>
                  {expanded && <RunDetail run={run} apiKey={apiKey} />}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
