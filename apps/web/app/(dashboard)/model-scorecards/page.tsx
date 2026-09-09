'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { toast } from 'sonner'
import {
  Trophy, Star, ArrowUpDown, ChevronDown, ChevronRight,
  Lightbulb, AlertTriangle, RefreshCw, Sparkles,
} from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts'
import {
  getModelScorecards, getModelScoreTrends,
  getOptimizationOrgGatewayPosture, getOptimizationObservePosture,
  getOptimizationFinOpsPosture, getBuildInternalPosture,
  getModelScorecardsIntelPosture,
} from '@/lib/api'
import { getDashboardWindow } from '@/components/dashboard/DashboardScopeBar'
import type {
  ModelScorecard, ModelScoreTrend,
  OptimizationOrgGatewayPosture, OptimizationObservePosture,
  OptimizationFinOpsPosture, BuildInternalPosture,
  ModelScorecardsIntelPosture,
} from '@/types/api'
import { num } from '@/lib/utils'

type SortKey = keyof ModelScorecard
type SortDir = 'asc' | 'desc'
type RangeKey = '7d' | '30d' | '90d'

function fmt(v: string | null | undefined) { return v == null || v === '' ? '—' : v }
function fmtUsd(v: string | number) { return `$${Number(v).toFixed(2)}` }
function fmtNum(v: string | number) { return Number(v).toLocaleString() }
function fmtPct(v: string | number) { return `${(Number(v) * 100).toFixed(1)}%` }
function sortValue(row: ModelScorecard, key: SortKey): number | string { const v = row[key]; if (v == null || v === '') return -Infinity; const n = Number(v); return isNaN(n) ? String(v).toLowerCase() : n }

const PAGE_SIZE = 15

export default function ModelScorecardsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const [data, setData] = useState<ModelScorecard[]>([])
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<SortKey>('total_cost_usd')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [range, setRange] = useState<RangeKey>('7d')
  const [expandedModel, setExpandedModel] = useState<string | null>(null)
  const [trendData, setTrendData] = useState<ModelScoreTrend[]>([])
  const [trendLoading, setTrendLoading] = useState(false)
  const [page, setPage] = useState(0)

  const [orgGatewayPosture, setOrgGatewayPosture] = useState<OptimizationOrgGatewayPosture | null>(null)
  const [observePosture, setObservePosture] = useState<OptimizationObservePosture | null>(null)
  const [finOpsPosture, setFinOpsPosture] = useState<OptimizationFinOpsPosture | null>(null)
  const [buildPosture, setBuildPosture] = useState<BuildInternalPosture | null>(null)
  const [intelPosture, setIntelPosture] = useState<ModelScorecardsIntelPosture | null>(null)

  const fetchScorecards = useCallback(() => {
    if (!apiKey) return
    setLoading(true)
    const win = getDashboardWindow(range)
    getModelScorecards(apiKey, { from: win.from, to: win.to })
      .then(res => { setData(res.items); setPage(0) })
      .catch(() => toast.error('Failed to load model scorecards'))
      .finally(() => setLoading(false))
  }, [apiKey, range])

  useEffect(() => {
    fetchScorecards()
    if (apiKey) {
      getOptimizationOrgGatewayPosture(apiKey).then(setOrgGatewayPosture).catch(() => {})
      getOptimizationObservePosture(apiKey).then(setObservePosture).catch(() => {})
      getOptimizationFinOpsPosture(apiKey).then(setFinOpsPosture).catch(() => {})
      getBuildInternalPosture(apiKey).then(setBuildPosture).catch(() => {})
      getModelScorecardsIntelPosture(apiKey).then(setIntelPosture).catch(() => {})
    }
  }, [fetchScorecards, apiKey])

  useEffect(() => {
    if (!expandedModel || !apiKey) { setTrendData([]); return }
    setTrendLoading(true)
    const win = getDashboardWindow(range)
    getModelScoreTrends(apiKey, expandedModel, { from: win.from, to: win.to })
      .then(res => setTrendData(res.items))
      .catch(() => toast.error('Failed to load trend data'))
      .finally(() => setTrendLoading(false))
  }, [expandedModel, apiKey, range])

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const sorted = [...data].sort((a, b) => {
    const av = sortValue(a, sortKey); const bv = sortValue(b, sortKey)
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortDir === 'asc' ? cmp : -cmp
  })

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const chartData = trendData.map(t => ({
    date: t.date.slice(0, 10),
    quality: t.avg_quality_score != null ? Number(t.avg_quality_score) : null,
    errorRate: Number(t.error_rate) * 100,
  }))

  const totalCost = data.reduce((s, r) => s + Number(r.total_cost_usd), 0)
  const totalCalls = data.reduce((s, r) => s + Number(r.call_count), 0)
  const avgErrorRate = data.length > 0 ? data.reduce((s, r) => s + Number(r.error_rate ?? 0), 0) / data.length : 0

  function Th({ label, col }: { label: string; col: SortKey }) {
    return (
      <th onClick={() => toggleSort(col)} className="cursor-pointer select-none whitespace-nowrap px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500 hover:text-slate-900 dark:hover:text-slate-100">
        <span className="inline-flex items-center gap-0.5">{label}<ArrowUpDown className="h-2.5 w-2.5 opacity-40" />{sortKey === col && <span className="text-[8px]">{sortDir === 'asc' ? '▲' : '▼'}</span>}</span>
      </th>
    )
  }

  return (
    <div className="space-y-3">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg shadow-amber-500/25">
            <Trophy className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Model Scorecards</h1>
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">Compare models across cost, latency, quality, and reliability.</p>
          </div>
        </div>
        <div className="flex gap-1.5">
          {[
            { label: 'Model Usage', href: '/model-usage' },
            { label: 'Eval Studio', href: '/evaluation' },
            { label: 'Optimization', href: '/optimization-opportunities' },
            { label: 'Playground', href: '/playground' },
          ].map(({ label, href }) => (
            <Link key={label} href={href} className="rounded-full bg-amber-100 dark:bg-amber-900/30 px-2.5 py-1 text-[10px] font-semibold text-amber-700 dark:text-amber-300 hover:bg-amber-200 dark:hover:bg-amber-800/40 transition-colors">{label}</Link>
          ))}
        </div>
      </div>

      {/* ── KPI strip ──────────────────────────────────── */}
      <div className="grid grid-cols-8 gap-2">
        {[
          { label: 'Models', value: data.length },
          { label: 'Total Cost', value: fmtUsd(totalCost), accent: true },
          { label: 'Total Calls', value: totalCalls.toLocaleString() },
          { label: 'Avg Error Rate', value: fmtPct(avgErrorRate) },
          { label: 'Hub Models', value: intelPosture?.model_context.hub_models ?? '—' },
          { label: 'Budgets', value: finOpsPosture?.budget_context.active_budgets ?? '—' },
          { label: 'Spend 30d', value: finOpsPosture ? `$${num(finOpsPosture.budget_context.spend_30d).toFixed(2)}` : '—', accent: true },
          { label: 'Score Events', value: intelPosture?.optimization_context.score_events_30d ?? '—' },
        ].map(({ label, value, accent }) => (
          <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
            <p className={`text-sm font-bold ${accent ? 'text-amber-600 dark:text-amber-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* ── Posture chips ──────────────────────────────── */}
      <div className="grid grid-cols-3 gap-2">
        {orgGatewayPosture && (
          <div className="rounded-lg border border-blue-200/60 dark:border-blue-800/40 bg-blue-50/30 dark:bg-blue-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-1">Org & Gateway</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-[10px] text-blue-700 dark:text-blue-300">{orgGatewayPosture.provider_context.distinct_providers} providers</span>
              <span className="rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-[10px] text-blue-700 dark:text-blue-300">{orgGatewayPosture.provider_context.active_routes} routes</span>
              <span className="rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-[10px] text-blue-700 dark:text-blue-300">{orgGatewayPosture.cache_context.cache_configs} caches</span>
              <Link href="/gateway" className="text-[10px] text-blue-600 hover:underline dark:text-blue-400">Gateway</Link>
            </div>
          </div>
        )}
        {observePosture && (
          <div className="rounded-lg border border-cyan-200/60 dark:border-cyan-800/40 bg-cyan-50/30 dark:bg-cyan-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 mb-1">Observe</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-cyan-100 dark:bg-cyan-900/40 px-2 py-0.5 text-[10px] text-cyan-700 dark:text-cyan-300">{observePosture.runs_context.runs_30d} runs</span>
              <span className="rounded-full bg-cyan-100 dark:bg-cyan-900/40 px-2 py-0.5 text-[10px] text-cyan-700 dark:text-cyan-300">{observePosture.model_usage_context.distinct_models_30d} models</span>
              <span className="rounded-full bg-cyan-100 dark:bg-cyan-900/40 px-2 py-0.5 text-[10px] text-cyan-700 dark:text-cyan-300">${num(observePosture.cost_savings_context.total_cost_30d).toFixed(2)}</span>
              <Link href="/analytics" className="text-[10px] text-cyan-600 hover:underline dark:text-cyan-400">Analytics</Link>
            </div>
          </div>
        )}
        {buildPosture && (
          <div className="rounded-lg border border-rose-200/60 dark:border-rose-800/40 bg-rose-50/30 dark:bg-rose-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-1">Build & Improve</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-[10px] text-rose-700 dark:text-rose-300">{buildPosture.evaluation_context.experiments} experiments</span>
              <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-[10px] text-rose-700 dark:text-rose-300">{buildPosture.scorecards_context.score_events_30d} scores</span>
              <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-[10px] text-rose-700 dark:text-rose-300">{buildPosture.prompts_context.total_prompts} prompts</span>
              <Link href="/evaluation" className="text-[10px] text-rose-600 hover:underline dark:text-rose-400">Eval Studio</Link>
            </div>
          </div>
        )}
      </div>

      {/* ── Range + table ──────────────────────────────── */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-slate-500 dark:text-slate-400">Range:</span>
        {(['7d', '30d', '90d'] as RangeKey[]).map(r => (
          <button key={r} onClick={() => setRange(r)}
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition ${range === r ? 'bg-amber-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'}`}>
            {r}
          </button>
        ))}
        {loading && <RefreshCw className="h-3.5 w-3.5 animate-spin text-slate-400" />}
      </div>

      {sorted.length === 0 && !loading ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-900/60 px-6 py-14 text-center">
          <Trophy className="h-8 w-8 text-slate-400" />
          <h2 className="mt-3 text-sm font-bold text-slate-700 dark:text-slate-200">No model data yet</h2>
          <p className="mt-1 max-w-md text-xs text-slate-500">Start sending requests through the gateway to populate scorecards.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <th className="w-6 px-2 py-1.5" />
                  <Th label="Model" col="model" />
                  <Th label="Cost" col="total_cost_usd" />
                  <Th label="Calls" col="call_count" />
                  <Th label="$/Call" col="avg_cost_per_call" />
                  <Th label="Avg ms" col="avg_latency_ms" />
                  <Th label="P95 ms" col="p95_latency_ms" />
                  <Th label="Err %" col="error_rate" />
                  <Th label="Cache %" col="cache_hit_rate" />
                  <Th label="Quality" col="avg_quality_score" />
                  <Th label="Tokens" col="input_tokens" />
                  <Th label="Accept" col="acceptance_rate" />
                  <Th label="Halluc." col="hallucination_flags" />
                  <Th label="Retry" col="retry_rate" />
                  <Th label="Feedback" col="user_feedback_score" />
                  <Th label="Eval" col="eval_score" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {paged.map(row => {
                  const errorRate = Number(row.error_rate ?? 0)
                  const cacheRate = Number(row.cache_hit_rate ?? 0)
                  const totalTokens = Number(row.input_tokens ?? 0) + Number(row.output_tokens ?? 0)
                  const hallucinationFlags = row.hallucination_flags ?? 0
                  const isExpanded = expandedModel === row.model
                  return (
                    <>{/* eslint-disable-next-line react/jsx-key */}
                      <tr key={row.model} className="cursor-pointer hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition" onClick={() => setExpandedModel(prev => prev === row.model ? null : row.model)}>
                        <td className="px-2 py-1.5 text-slate-400">{isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}</td>
                        <td className="px-3 py-1.5">
                          <Link href={`/runs?model=${encodeURIComponent(row.model)}`} className="font-semibold text-slate-900 dark:text-white hover:text-amber-600 dark:hover:text-amber-400 hover:underline" onClick={(e) => e.stopPropagation()}>{row.model}</Link>
                          {row.provider && <span className="ml-1.5 text-[9px] text-slate-400">{row.provider}</span>}
                        </td>
                        <td className="px-3 py-1.5 font-mono text-slate-700 dark:text-slate-300 tabular-nums">{fmtUsd(row.total_cost_usd)}</td>
                        <td className="px-3 py-1.5 tabular-nums text-slate-700 dark:text-slate-300">{fmtNum(row.call_count)}</td>
                        <td className="px-3 py-1.5 font-mono tabular-nums text-slate-700 dark:text-slate-300">{fmtUsd(row.avg_cost_per_call)}</td>
                        <td className="px-3 py-1.5 tabular-nums text-slate-700 dark:text-slate-300">{fmt(row.avg_latency_ms)}</td>
                        <td className="px-3 py-1.5 tabular-nums text-slate-700 dark:text-slate-300">{fmt(row.p95_latency_ms)}</td>
                        <td className="px-3 py-1.5"><span className={errorRate > 0.05 ? 'font-medium text-rose-600 dark:text-rose-400' : 'text-slate-700 dark:text-slate-300'}>{fmtPct(row.error_rate)}</span></td>
                        <td className="px-3 py-1.5"><span className={cacheRate > 0.5 ? 'font-medium text-emerald-600 dark:text-emerald-400' : 'text-slate-700 dark:text-slate-300'}>{row.cache_hit_rate != null ? fmtPct(row.cache_hit_rate) : '—'}</span></td>
                        <td className="px-3 py-1.5">{row.avg_quality_score != null ? <span className="inline-flex items-center gap-0.5 text-slate-700 dark:text-slate-300"><Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />{Number(row.avg_quality_score).toFixed(2)}</span> : '—'}</td>
                        <td className="px-3 py-1.5 tabular-nums text-slate-700 dark:text-slate-300">{fmtNum(totalTokens)}</td>
                        <td className="px-3 py-1.5 text-slate-700 dark:text-slate-300">{row.acceptance_rate != null ? fmtPct(row.acceptance_rate) : '—'}</td>
                        <td className="px-3 py-1.5"><span className={hallucinationFlags > 0 ? 'inline-flex items-center gap-0.5 font-medium text-rose-600 dark:text-rose-400' : 'text-slate-700 dark:text-slate-300'}>{hallucinationFlags > 0 && <AlertTriangle className="h-3 w-3" />}{hallucinationFlags}</span></td>
                        <td className="px-3 py-1.5 text-slate-700 dark:text-slate-300">{row.retry_rate != null ? fmtPct(row.retry_rate) : '—'}</td>
                        <td className="px-3 py-1.5">{row.user_feedback_score != null ? <span className="inline-flex items-center gap-0.5 text-slate-700 dark:text-slate-300"><Star className="h-3 w-3 fill-amber-400 text-amber-400" />{Number(row.user_feedback_score).toFixed(1)}/5</span> : '—'}</td>
                        <td className="px-3 py-1.5 text-slate-700 dark:text-slate-300">{row.eval_score != null ? Number(row.eval_score).toFixed(2) : '—'}</td>
                      </tr>
                      {isExpanded && (
                        <tr key={`${row.model}-expanded`}>
                          <td colSpan={16} className="bg-slate-50/60 dark:bg-slate-800/30 px-4 py-3">
                            {row.recommendation && (
                              <div className="mb-3 flex items-start gap-2 rounded-lg border border-blue-200/60 dark:border-blue-800/40 bg-blue-50/60 dark:bg-blue-950/30 px-3 py-2">
                                <Lightbulb className="mt-0.5 h-3.5 w-3.5 text-blue-500" />
                                <div>
                                  <p className="text-[9px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">Routing Recommendation</p>
                                  <p className="mt-0.5 text-xs text-blue-800 dark:text-blue-200">{row.recommendation}</p>
                                </div>
                              </div>
                            )}
                            <div>
                              <h3 className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">Score Trends</h3>
                              {trendLoading ? (
                                <div className="flex items-center gap-2 py-6 text-xs text-slate-400"><RefreshCw className="h-3.5 w-3.5 animate-spin" />Loading…</div>
                              ) : chartData.length === 0 ? (
                                <p className="py-6 text-xs text-slate-400 text-center">No trend data for this range.</p>
                              ) : (
                                <div className="h-48 w-full">
                                  <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                                      <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                                      <XAxis dataKey="date" tick={{ fontSize: 10 }} className="fill-slate-500" />
                                      <YAxis yAxisId="left" tick={{ fontSize: 10 }} stroke="#3b82f6" />
                                      <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} stroke="#ef4444" />
                                      <Tooltip contentStyle={{ backgroundColor: 'rgba(255,255,255,0.95)', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '11px' }} />
                                      <Line yAxisId="left" type="monotone" dataKey="quality" stroke="#3b82f6" strokeWidth={2} dot={{ r: 2 }} name="Quality" connectNulls />
                                      <Line yAxisId="right" type="monotone" dataKey="errorRate" stroke="#ef4444" strokeWidth={2} dot={{ r: 2 }} name="Error %" />
                                    </LineChart>
                                  </ResponsiveContainer>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-2 border-t border-slate-100 dark:border-slate-800">
              <p className="text-[10px] text-slate-400">{page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, sorted.length)} of {sorted.length}</p>
              <div className="flex gap-1">
                <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="rounded-lg bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:text-slate-300 disabled:opacity-40">Prev</button>
                <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="rounded-lg bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:text-slate-300 disabled:opacity-40">Next</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Footer context cards ───────────────────────── */}
      <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 px-4 py-3">
        <div className="flex items-start gap-2">
          <Sparkles className="mt-0.5 h-4 w-4 text-amber-600" />
          <div>
            <p className="text-xs font-bold text-slate-800 dark:text-white">Model Intelligence Flow</p>
            <p className="mt-0.5 text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Start in <Link href="/model-usage" className="text-amber-600 dark:text-amber-400 hover:underline font-medium">Model Usage</Link> to see where traffic and spend concentrate, then use scorecards to compare quality, latency, cache, retries, and recommendation signals model by model. Move to <Link href="/evaluation" className="text-amber-600 dark:text-amber-400 hover:underline font-medium">Evaluation Studio</Link> for explicit experiments before changing <Link href="/gateway?tab=routing" className="text-amber-600 dark:text-amber-400 hover:underline font-medium">routing</Link>.
            </p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {[
                { label: '1. Model Usage', href: '/model-usage' },
                { label: '2. Scorecards', href: '/model-scorecards' },
                { label: '3. Eval Studio', href: '/evaluation' },
                { label: '4. Optimization', href: '/optimization-opportunities' },
                { label: '5. Gateway Routing', href: '/gateway?tab=routing' },
              ].map(({ label, href }) => (
                <Link key={label} href={href} className="rounded-full bg-amber-100 dark:bg-amber-900/30 px-2.5 py-1 text-[10px] font-semibold text-amber-700 dark:text-amber-300 hover:bg-amber-200 dark:hover:bg-amber-800/40 transition-colors">{label}</Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
