'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import {
  AlertTriangle, ArrowRight, BarChart3, Beaker, CheckCircle2,
  Clock, Cpu, DollarSign, FlaskConical, Gauge, Lightbulb, Layers,
  PiggyBank, Play, RefreshCw, Route, ShieldCheck, Sparkles,
  TrendingDown, Zap,
} from 'lucide-react'
import { applyFlywheelRecommendation, dismissFlywheelRecommendation, getOptimizationOpportunities, getPlaygroundModels, runFlywheel, simulateOptimization } from '@/lib/api'
import type { OptimizationOpportunity, SimulationResult } from '@/types/api'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { useRole } from '@/components/rbac/useRole'
import { num } from '@/lib/utils'

type ViewTab = 'opportunities' | 'simulator'

function money(v: string | number) { const n = typeof v === 'string' ? parseFloat(v) : v; if (!Number.isFinite(n)) return '$0'; if (Math.abs(num(n)) >= 1) return `$${num(n).toFixed(2)}`; if (Math.abs(num(n)) >= 0.001) return `$${num(n).toFixed(4)}`; return `$${num(n).toFixed(6)}` }
function pct(v: string | number | null) { if (v === null) return 'n/a'; const n = typeof v === 'string' ? parseFloat(v) : v; if (!Number.isFinite(n)) return 'n/a'; return `${num(n) >= 0 ? '+' : ''}${num(n).toFixed(1)}%` }

const INTENTS = ['', 'reasoning', 'code_generation', 'search', 'translation', 'email', 'summarization', 'chat', 'planning', 'research', 'classification', 'vision', 'workflow']
const RANGES = [{ value: '7d', label: '7 days' }, { value: '30d', label: '30 days' }, { value: '90d', label: '90 days' }]

function rangeWindow(range: string) {
  const now = new Date(); const from = new Date(now)
  if (range === '7d') from.setDate(from.getDate() - 7)
  else if (range === '30d') from.setDate(from.getDate() - 30)
  else from.setDate(from.getDate() - 90)
  return { from: from.toISOString(), to: now.toISOString() }
}

const inputCls = 'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500'

const riskColors: Record<string, { bg: string; text: string; icon: typeof CheckCircle2 }> = {
  low: { bg: 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-800', text: 'text-emerald-700 dark:text-emerald-300', icon: CheckCircle2 },
  medium: { bg: 'bg-amber-50 dark:bg-amber-950/60 border-amber-200 dark:border-amber-800', text: 'text-amber-700 dark:text-amber-300', icon: AlertTriangle },
  high: { bg: 'bg-rose-50 dark:bg-rose-950/60 border-rose-200 dark:border-rose-800', text: 'text-rose-700 dark:text-rose-300', icon: AlertTriangle },
  unknown: { bg: 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700', text: 'text-slate-600 dark:text-slate-300', icon: Gauge },
}

export default function OptimizationPage() {
  const { data: session } = useSession()
  const router = useRouter()
  const searchParams = useSearchParams()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''

  const initialTab = searchParams.get('tab') === 'simulator' ? 'simulator' : 'opportunities'
  const [tab, setTab] = useState<ViewTab>(initialTab)

  // Shared postures

  // Opportunities: pending Flywheel recommendations (one engine, review B-20)
  const { canWrite } = useRole()
  const { confirm, dialog } = useConfirm()
  const [opps, setOpps] = useState<OptimizationOpportunity[]>([])
  const [oppsLoading, setOppsLoading] = useState(true)
  const [oppsError, setOppsError] = useState<string | null>(null)
  const [acting, setActing] = useState<string | null>(null)
  const [targets, setTargets] = useState<string[]>([])

  // Simulator state
  const [currentModel, setCurrentModel] = useState('')
  const [proposedModel, setProposedModel] = useState('')
  const [intent, setIntent] = useState('')
  const [enableCache, setEnableCache] = useState(false)
  const [enableCompression, setEnableCompression] = useState(false)
  const [simRange, setSimRange] = useState('30d')
  const [simRunning, setSimRunning] = useState(false)
  const [simResult, setSimResult] = useState<SimulationResult | null>(null)

  const loadOpps = useCallback(async () => {
    if (!apiKey) {
      setOppsLoading(false)
      return
    }
    setOppsLoading(true)
    try {
      const res = await getOptimizationOpportunities(apiKey)
      setOpps(res.items)
      setOppsError(null)
    } catch (err) {
      setOppsError(err instanceof Error ? err.message : 'Failed to load opportunities')
    } finally {
      setOppsLoading(false)
    }
  }, [apiKey])

  useEffect(() => { void loadOpps() }, [loadOpps])

  useEffect(() => {
    if (!apiKey) return
    getPlaygroundModels(apiKey)
      .then((m) => setTargets(Array.from(new Set(m.items.flatMap((a) => a.targets))).sort()))
      .catch(() => setTargets([]))
  }, [apiKey])

  async function handleAnalyze() {
    setActing('analyze')
    try {
      await runFlywheel(apiKey)
      toast.success('Flywheel analysis finished')
      await loadOpps()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Analysis failed')
    } finally { setActing(null) }
  }

  async function handleApply(o: OptimizationOpportunity) {
    if (!o.recommendation_id) return
    const ok = await confirm({
      title: o.applies_to_route ? `Apply to route alias "${o.segment_key}"?` : 'Acknowledge this recommendation?',
      description: o.applies_to_route
        ? `The alias's primary route is changed to ${JSON.stringify(o.proposed_config)}. The change is audited and can be rolled back from Gateway → Flywheel.`
        : 'This segment is not an alias, so no route changes; the recommendation is marked applied.',
      confirmLabel: 'Apply',
    })
    if (!ok) return
    setActing(o.recommendation_id)
    try {
      await applyFlywheelRecommendation(apiKey, o.recommendation_id)
      toast.success('Recommendation applied')
      await loadOpps()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Apply failed')
    } finally { setActing(null) }
  }

  async function handleDismiss(o: OptimizationOpportunity) {
    if (!o.recommendation_id) return
    setActing(o.recommendation_id)
    try {
      await dismissFlywheelRecommendation(apiKey, o.recommendation_id)
      await loadOpps()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Dismiss failed')
    } finally { setActing(null) }
  }

  function handleTabChange(next: ViewTab) {
    setTab(next)
    router.replace(`/optimization-opportunities?tab=${next}`)
  }

  const totalProjected = opps.reduce((s, o) => s + Number(o.potential_savings_usd || 0), 0)
  const routeChanges = opps.filter((o) => o.applies_to_route).length

  const canRunSim = Boolean(apiKey) && (proposedModel || enableCache || enableCompression)

  async function handleRunSim() {
    if (!apiKey || !canRunSim) return
    setSimRunning(true); setSimResult(null)
    const win = rangeWindow(simRange)
    try {
      const res = await simulateOptimization(apiKey, {
        current_model: currentModel || null,
        proposed_model: proposedModel || null,
        intent: intent || null,
        enable_cache: enableCache,
        enable_compression: enableCompression,
        from_dt: win.from,
        to_dt: win.to,
      })
      setSimResult(res)
      if (res.affected_requests === 0) toast.info('No matching requests for those filters')
    } catch { toast.error('Simulation failed — check API connection') }
    finally { setSimRunning(false) }
  }

  const risk = simResult ? riskColors[simResult.quality_risk] ?? riskColors.unknown : null
  const RiskIcon = risk?.icon ?? Gauge

  return (
    <div className="space-y-3">
      {dialog}
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/25">
            <Lightbulb className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Optimization</h1>
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">Flywheel recommendations learned from your runs, cost and quality, applied to gateway routes with audit and rollback; plus what-if simulations priced from real pricing rows.</p>
          </div>
        </div>
        <div className="flex gap-1.5">
          {[
            { label: 'Gateway', href: '/gateway' },
            { label: 'Eval Studio', href: '/evaluation' },
            { label: 'Scorecards', href: '/model-scorecards' },
            { label: 'Cost & Savings', href: '/cost-savings' },
          ].map(({ label, href }) => (
            <Link key={label} href={href} className="rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-2.5 py-1 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300 hover:bg-emerald-200 dark:hover:bg-emerald-800/40 transition-colors">{label}</Link>
          ))}
        </div>
      </div>

      {/* ── KPI strip ──────────────────────────────────── */}
      <div className="grid grid-cols-8 gap-2">
        {[
          { label: 'Opportunities', value: opps.length },
          { label: 'Est. savings', value: money(totalProjected), accent: true },
          { label: 'Route changes', value: routeChanges },
        ].map(({ label, value, accent }) => (
          <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
            <p className={`text-sm font-bold ${accent ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-2">
      </div>

      {/* ── Tab bar ─────────────────────────────────────── */}
      <div className="flex gap-0.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-0.5">
        {([
          { id: 'opportunities' as ViewTab, label: 'Opportunities', icon: <Lightbulb className="h-3.5 w-3.5" />, count: opps.length },
          { id: 'simulator' as ViewTab, label: 'Simulator', icon: <FlaskConical className="h-3.5 w-3.5" /> },
        ]).map((t) => (
          <button key={t.id} onClick={() => handleTabChange(t.id)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
              tab === t.id ? 'bg-white dark:bg-slate-900 text-emerald-700 dark:text-emerald-300 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white'
            }`}>
            {t.icon}{t.label}
            {t.count !== undefined && t.count > 0 && (
              <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${tab === t.id ? 'bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300' : 'bg-slate-200 dark:bg-slate-700 text-slate-500'}`}>{t.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Opportunities tab ──────────────────────────── */}
      {tab === 'opportunities' && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            {canWrite && (
              <button type="button" onClick={() => void handleAnalyze()} disabled={acting !== null}
                className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">
                <RefreshCw className={`h-3 w-3 ${acting === 'analyze' ? 'animate-spin' : ''}`} /> Analyze now
              </button>
            )}
            {oppsLoading && <RefreshCw className="h-3.5 w-3.5 animate-spin text-slate-400" aria-label="Loading" />}
          </div>

          {oppsError ? (
            <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-700 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300">
              {oppsError} <button type="button" onClick={() => void loadOpps()} className="ml-2 underline">Retry</button>
            </div>
          ) : opps.length === 0 && !oppsLoading ? (
            <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-900/60 p-10 text-center">
              <Sparkles className="mx-auto h-7 w-7 text-emerald-500" />
              <h2 className="mt-3 text-sm font-bold text-slate-800 dark:text-white">No pending recommendations</h2>
              <p className="mx-auto mt-1 max-w-lg text-xs text-slate-500">The Flywheel proposes a change when a cheaper configuration holds your quality bar on enough observed requests. Run an experiment and use &quot;Recommend route&quot;, or analyze now.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {opps.map((o) => (
                <div key={o.recommendation_id ?? o.description} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                        <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">{o.optimization_type}</span>
                        {o.confidence && <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:text-slate-300">{o.confidence} confidence</span>}
                        {!o.applies_to_route && <span className="rounded-full bg-amber-100 dark:bg-amber-900/40 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300">advisory</span>}
                      </div>
                      <p className="text-xs text-slate-700 dark:text-slate-200 leading-relaxed">{o.description}</p>
                      <p className="mt-1 text-[10px] text-slate-500">Current {JSON.stringify(o.current_config)} → proposed {JSON.stringify(o.proposed_config)}</p>
                    </div>
                    <div className="shrink-0 text-right space-y-1.5">
                      <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-3 py-2">
                        <p className="text-[9px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Est. savings</p>
                        <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300 tabular-nums">{money(o.potential_savings_usd)}</p>
                        <p className="text-[10px] text-emerald-600 dark:text-emerald-400">{pct(o.est_cost_delta_pct)} per request · {o.affected_calls} observed</p>
                      </div>
                      {canWrite && o.recommendation_id && (
                        <div className="flex justify-end gap-1">
                          <button type="button" onClick={() => void handleDismiss(o)} disabled={acting !== null}
                            className="rounded-lg bg-slate-100 dark:bg-slate-800 px-2 py-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 disabled:opacity-50">Dismiss</button>
                          <button type="button" onClick={() => void handleApply(o)} disabled={acting !== null}
                            className="rounded-lg bg-emerald-600 px-2 py-1 text-[10px] font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">Apply</button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 px-4 py-3">
            <div className="flex items-start gap-2">
              <Route className="mt-0.5 h-4 w-4 text-emerald-600" />
              <div>
                <h3 className="text-xs font-bold text-slate-800 dark:text-white">How recommendations are generated</h3>
                <p className="mt-0.5 text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">The Flywheel groups observed runs by segment (alias, task class or outcome), compares the cost and quality of the configurations it has seen, and proposes the cheapest one that holds your minimum quality on enough samples. Experiments can add recommendations too. Applying an alias recommendation changes that alias&apos;s primary route; it is audited and can be rolled back.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Simulator tab ──────────────────────────────── */}
      {tab === 'simulator' && (
        <div className="space-y-3">
          <div className="rounded-xl border border-emerald-200/60 dark:border-emerald-800/40 bg-emerald-50/30 dark:bg-emerald-950/20 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Layers className="h-4 w-4 text-emerald-600" />
              <h2 className="text-xs font-bold text-slate-800 dark:text-white">Simulation Parameters</h2>
              <span className="text-[10px] text-slate-400 ml-auto">Select at least one change (model swap, cache, or compression)</span>
            </div>
            <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Current model</label>
                <select value={currentModel} onChange={e => setCurrentModel(e.target.value)} className={inputCls}>
                  <option value="">Any (all models)</option>
                  {targets.map(m => <option key={`c-${m}`} value={m}>{m}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Proposed model *</label>
                <select value={proposedModel} onChange={e => setProposedModel(e.target.value)} className={inputCls}>
                  <option value="">No change</option>
                  {targets.map(m => <option key={`p-${m}`} value={m}>{m}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Intent filter</label>
                <select value={intent} onChange={e => setIntent(e.target.value)} className={inputCls}>
                  <option value="">All intents</option>
                  {INTENTS.filter(Boolean).map(i => <option key={i} value={i}>{i}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Time range</label>
                <select value={simRange} onChange={e => setSimRange(e.target.value)} className={inputCls}>
                  {RANGES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
            </div>
            <div className="flex items-center gap-4 mt-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={enableCache} onChange={e => setEnableCache(e.target.checked)} className="h-3.5 w-3.5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500" />
                <span className="text-xs text-slate-700 dark:text-slate-300">Enable caching</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={enableCompression} onChange={e => setEnableCompression(e.target.checked)} className="h-3.5 w-3.5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500" />
                <span className="text-xs text-slate-700 dark:text-slate-300">Prompt compression</span>
              </label>
              <button type="button" onClick={() => void handleRunSim()} disabled={!canRunSim || simRunning}
                className="ml-auto flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-40 transition">
                {simRunning ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                {simRunning ? 'Simulating…' : 'Run Simulation'}
              </button>
            </div>
          </div>

          {simResult && simResult.affected_requests > 0 && (
            <>
              <div className="grid gap-2 grid-cols-4">
                <div className="rounded-lg border border-emerald-200/60 dark:border-emerald-800/40 bg-gradient-to-br from-emerald-50/80 to-emerald-100/30 dark:from-emerald-950/40 dark:to-emerald-900/20 p-3">
                  <div className="flex items-center justify-between"><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Projected savings</p><PiggyBank className="h-4 w-4 text-emerald-600" /></div>
                  <p className="mt-1 text-xl font-bold text-slate-900 dark:text-white tabular-nums">{money(simResult.projected_savings_usd)}</p>
                  <p className="text-[10px] font-semibold text-emerald-600 flex items-center gap-0.5"><TrendingDown className="h-3 w-3" />{parseFloat(simResult.savings_pct).toFixed(1)}% reduction</p>
                </div>
                <div className="rounded-lg border border-blue-200/60 dark:border-blue-800/40 bg-gradient-to-br from-blue-50/80 to-blue-100/30 dark:from-blue-950/40 dark:to-blue-900/20 p-3">
                  <div className="flex items-center justify-between"><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Current cost</p><DollarSign className="h-4 w-4 text-blue-600" /></div>
                  <p className="mt-1 text-xl font-bold text-slate-900 dark:text-white tabular-nums">{money(simResult.current_cost_usd)}</p>
                  <p className="text-[10px] text-slate-500"><ArrowRight className="h-3 w-3 inline mr-0.5" />{money(simResult.projected_cost_usd)} projected</p>
                </div>
                <div className="rounded-lg border border-violet-200/60 dark:border-violet-800/40 bg-gradient-to-br from-violet-50/80 to-violet-100/30 dark:from-violet-950/40 dark:to-violet-900/20 p-3">
                  <div className="flex items-center justify-between"><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Affected requests</p><Zap className="h-4 w-4 text-violet-600" /></div>
                  <p className="mt-1 text-xl font-bold text-slate-900 dark:text-white tabular-nums">{simResult.affected_requests.toLocaleString()}</p>
                  <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${simResult.confidence === 'high' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300' : simResult.confidence === 'medium' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>{simResult.confidence}</span>
                </div>
                <div className={`rounded-lg border p-3 ${risk?.bg}`}>
                  <div className="flex items-center justify-between"><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Quality risk</p><RiskIcon className={`h-4 w-4 ${risk?.text}`} /></div>
                  <p className={`mt-1 text-xl font-bold capitalize ${risk?.text}`}>{simResult.quality_risk}</p>
                  {simResult.latency_delta_pct && <p className="text-[10px] text-slate-500 flex items-center gap-0.5"><Clock className="h-3 w-3" />Latency: {pct(simResult.latency_delta_pct)}</p>}
                </div>
              </div>

              {(simResult.current_avg_latency_ms || simResult.projected_latency_ms) && (
                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Current avg</p>
                    <p className="text-sm font-bold text-slate-900 dark:text-white tabular-nums">{simResult.current_avg_latency_ms ? `${parseFloat(simResult.current_avg_latency_ms).toFixed(0)}ms` : 'n/a'}</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Projected avg</p>
                    <p className="text-sm font-bold text-slate-900 dark:text-white tabular-nums">{simResult.projected_latency_ms ? `${parseFloat(simResult.projected_latency_ms).toFixed(0)}ms` : 'n/a'}</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 px-3 py-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Delta</p>
                    <p className={`text-sm font-bold tabular-nums ${simResult.latency_delta_pct && parseFloat(simResult.latency_delta_pct) > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>{pct(simResult.latency_delta_pct)}</p>
                  </div>
                </div>
              )}

              {simResult.impacts.length > 0 && (
                <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 p-4">
                  <div className="flex items-center gap-2 mb-2"><BarChart3 className="h-4 w-4 text-emerald-600" /><h3 className="text-xs font-bold text-slate-800 dark:text-white">Impact Breakdown</h3></div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                          <th className="pb-1.5 pr-3 text-left">Change</th>
                          <th className="pb-1.5 pr-3 text-left">Current</th>
                          <th className="pb-1.5 pr-3 text-left">Projected</th>
                          <th className="pb-1.5 text-right">Delta</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {simResult.impacts.map((imp, i) => (
                          <tr key={i} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                            <td className="py-1.5 pr-3 font-medium text-slate-800 dark:text-slate-100">{imp.label}</td>
                            <td className="py-1.5 pr-3 text-slate-500">{imp.current_value}</td>
                            <td className="py-1.5 pr-3 font-medium text-emerald-700 dark:text-emerald-300">{imp.projected_value}</td>
                            <td className={`py-1.5 text-right font-semibold tabular-nums ${imp.delta_pct && parseFloat(imp.delta_pct) < 0 ? 'text-emerald-600' : imp.delta_pct && parseFloat(imp.delta_pct) > 0 ? 'text-rose-600' : 'text-slate-500'}`}>{pct(imp.delta_pct)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 px-4 py-3">
                <div className="flex items-start gap-2">
                  <Sparkles className="mt-0.5 h-4 w-4 text-emerald-600" />
                  <div>
                    <p className="text-xs font-bold text-slate-800 dark:text-white">Summary</p>
                    <p className="mt-0.5 text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">{simResult.description}</p>
                  </div>
                </div>
              </div>
            </>
          )}

          {!simResult && !simRunning && (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-900/60 px-6 py-14 text-center">
              <Cpu className="h-8 w-8 text-slate-400" />
              <h2 className="mt-3 text-sm font-bold text-slate-700 dark:text-slate-200">Configure a simulation</h2>
              <p className="mt-1 max-w-md text-xs text-slate-500">Choose a current model, propose a replacement (or enable caching/compression), and run the simulation to preview savings, latency impact, and quality risk.</p>
            </div>
          )}

          {simResult && simResult.affected_requests === 0 && (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-900/60 px-6 py-14 text-center">
              <ShieldCheck className="h-8 w-8 text-slate-400" />
              <h2 className="mt-3 text-sm font-bold text-slate-700 dark:text-slate-200">No matching requests</h2>
              <p className="mt-1 max-w-md text-xs text-slate-500">No requests matched the current model/intent filters in the selected time range. Try broadening filters or extending the time range.</p>
            </div>
          )}

          <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 px-4 py-3">
            <div className="flex items-start gap-2">
              <FlaskConical className="mt-0.5 h-4 w-4 text-emerald-600" />
              <div>
                <h3 className="text-xs font-bold text-slate-800 dark:text-white">How simulations work</h3>
                <p className="mt-0.5 text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">Queries real request telemetry, applies cost ratios from known pricing tiers, and estimates cache/compression impact from industry benchmarks. Quality risk is derived from model capability tiers. Projections improve with 100+ requests.</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
