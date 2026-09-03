'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  FlaskConical,
  Gauge,
  Layers,
  PiggyBank,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  Zap,
} from 'lucide-react'
import Link from 'next/link'
import { simulateOptimization, getOptimizationOrgGatewayPosture, getOptimizationObservePosture, getOptimizationFinOpsPosture, getBuildInternalPosture, getOptSimDecisionPosture } from '@/lib/api'
import type { SimulationResult, OptimizationOrgGatewayPosture, OptimizationObservePosture, OptimizationFinOpsPosture, BuildInternalPosture, OptSimDecisionPosture } from '@/types/api'

const MODELS = [
  { value: '', label: 'No change' },
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'gpt-4.1', label: 'GPT-4.1' },
  { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
  { value: 'gpt-4.1-nano', label: 'GPT-4.1 Nano' },
  { value: 'gpt-5', label: 'GPT-5' },
  { value: 'o3', label: 'o3' },
  { value: 'o4-mini', label: 'o4-mini' },
  { value: 'claude-sonnet-4', label: 'Claude Sonnet 4' },
  { value: 'claude-opus-4', label: 'Claude Opus 4' },
  { value: 'claude-haiku-3.5', label: 'Claude Haiku 3.5' },
  { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  { value: 'deepseek-v3', label: 'DeepSeek V3' },
  { value: 'deepseek-r1', label: 'DeepSeek R1' },
  { value: 'llama-3.3-70b', label: 'Llama 3.3 70B' },
  { value: 'llama-4-scout', label: 'Llama 4 Scout' },
  { value: 'llama-4-maverick', label: 'Llama 4 Maverick' },
  { value: 'qwen-3-235b', label: 'Qwen 3 235B' },
  { value: 'local/ollama', label: 'Local / Ollama' },
]

const INTENTS = [
  '', 'reasoning', 'code_generation', 'search', 'translation',
  'email', 'summarization', 'chat', 'planning', 'research',
  'classification', 'vision', 'workflow',
]

const RANGES = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
]

function rangeWindow(range: string) {
  const now = new Date()
  const from = new Date(now)
  if (range === '7d') from.setDate(from.getDate() - 7)
  else if (range === '30d') from.setDate(from.getDate() - 30)
  else from.setDate(from.getDate() - 90)
  return { from: from.toISOString(), to: now.toISOString() }
}

function money(v: string | number) {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (!Number.isFinite(n)) return '$0'
  if (Math.abs(n) >= 1) return `$${n.toFixed(2)}`
  if (Math.abs(n) >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

function pct(v: string | number | null) {
  if (v === null) return 'n/a'
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (!Number.isFinite(n)) return 'n/a'
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

const inputCls =
  'rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm transition focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:border-slate-300 dark:bg-white dark:text-slate-900'

const riskColors: Record<string, { bg: string; text: string; icon: typeof CheckCircle2 }> = {
  low: { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700', icon: CheckCircle2 },
  medium: { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-700', icon: AlertTriangle },
  high: { bg: 'bg-rose-50 border-rose-200', text: 'text-rose-700', icon: AlertTriangle },
  unknown: { bg: 'bg-slate-100 border-slate-200', text: 'text-slate-600', icon: Gauge },
}

export default function OptimizationSimulatorPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey

  const [currentModel, setCurrentModel] = useState('')
  const [proposedModel, setProposedModel] = useState('')
  const [intent, setIntent] = useState('')
  const [enableCache, setEnableCache] = useState(false)
  const [enableCompression, setEnableCompression] = useState(false)
  const [range, setRange] = useState('30d')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [orgGatewayPosture, setOrgGatewayPosture] = useState<OptimizationOrgGatewayPosture | null>(null)
  const [observePosture, setObservePosture] = useState<OptimizationObservePosture | null>(null)
  const [finOpsPosture, setFinOpsPosture] = useState<OptimizationFinOpsPosture | null>(null)
  const [buildPosture, setBuildPosture] = useState<BuildInternalPosture | null>(null)
  const [decisionPosture, setDecisionPosture] = useState<OptSimDecisionPosture | null>(null)

  useEffect(() => { if (apiKey) { getOptimizationOrgGatewayPosture(apiKey).then(setOrgGatewayPosture).catch(() => {}); getOptimizationObservePosture(apiKey).then(setObservePosture).catch(() => {}); getOptimizationFinOpsPosture(apiKey).then(setFinOpsPosture).catch(() => {}); getBuildInternalPosture(apiKey).then(setBuildPosture).catch(() => {}); getOptSimDecisionPosture(apiKey).then(setDecisionPosture).catch(() => {}) } }, [apiKey])

  const canRun = Boolean(apiKey) && (proposedModel || enableCache || enableCompression)

  const handleRun = useCallback(async () => {
    if (!apiKey || !canRun) return
    setRunning(true)
    setResult(null)
    const win = rangeWindow(range)
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
      setResult(res)
      if (res.affected_requests === 0) {
        toast.info('No matching requests found for those filters')
      }
    } catch {
      toast.error('Simulation failed')
    } finally {
      setRunning(false)
    }
  }, [apiKey, canRun, currentModel, proposedModel, intent, enableCache, enableCompression, range])

  const risk = result ? riskColors[result.quality_risk] ?? riskColors.unknown : null
  const RiskIcon = risk?.icon ?? Gauge

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FlaskConical className="h-5 w-5 text-violet-600" />
            <h1 className="font-display text-2xl font-semibold tracking-[-0.045em] text-slate-950">
              Optimization Simulator
            </h1>
          </div>
          <p className="max-w-2xl text-sm text-slate-500">
            Preview savings before changing routes or policies. Select a current configuration, propose changes, and see projected cost, latency, and quality impact.
          </p>
        </div>
      </div>

      {orgGatewayPosture && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Organization &amp; Access Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Workspace</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{orgGatewayPosture.workspace_context.workspace_name}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">API Keys</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{orgGatewayPosture.api_key_context.api_keys}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Hub Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{orgGatewayPosture.ai_hub_context.hub_models}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Active Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{orgGatewayPosture.ai_hub_context.hub_active_models}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-blue-200">
            <Link href="/organization" className="text-xs text-blue-600 hover:underline">Organization</Link>
            <Link href="/api-keys" className="text-xs text-blue-600 hover:underline">API Keys</Link>
            <Link href="/ai-hub" className="text-xs text-blue-600 hover:underline">AI Hub</Link>
          </div>
        </div>
      )}

      {orgGatewayPosture && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50/50 p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-600">Gateway &amp; Routing Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Providers</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{orgGatewayPosture.provider_context.distinct_providers}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Active Routes</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{orgGatewayPosture.provider_context.active_routes}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Guardrails</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{orgGatewayPosture.guardrail_context.guardrail_rules}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Cache Configs</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{orgGatewayPosture.cache_context.cache_configs}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-violet-200">
            <Link href="/gateway" className="text-xs text-violet-600 hover:underline">Model Gateway</Link>
            <Link href="/routes" className="text-xs text-violet-600 hover:underline">Routes</Link>
            <Link href="/guardrails" className="text-xs text-violet-600 hover:underline">Guardrails</Link>
            <Link href="/response-cache" className="text-xs text-violet-600 hover:underline">Response Cache</Link>
            <Link href="/rate-limits" className="text-xs text-violet-600 hover:underline">Rate Limits</Link>
          </div>
        </div>
      )}

      {observePosture && (
        <div className="rounded-2xl border border-cyan-200 bg-cyan-50/50 p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-600">Observe &amp; Runtime Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Runs 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{observePosture.runs_context.runs_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Provider Calls 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{observePosture.request_flow_context.provider_calls_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Distinct Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{observePosture.model_usage_context.distinct_models_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Total Cost 30d</p>
              <p className="mt-1 text-lg font-semibold text-cyan-600">${observePosture.cost_savings_context.total_cost_30d.toFixed(2)}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-cyan-200">
            <Link href="/analytics" className="text-xs text-cyan-600 hover:underline">Analytics Overview</Link>
            <Link href="/runs" className="text-xs text-cyan-600 hover:underline">Runs</Link>
            <Link href="/analytics?tab=requests" className="text-xs text-cyan-600 hover:underline">Request Flow</Link>
            <Link href="/request-explorer" className="text-xs text-cyan-600 hover:underline">Request Explorer</Link>
            <Link href="/analytics?tab=models" className="text-xs text-cyan-600 hover:underline">Model Usage</Link>
          </div>
        </div>
      )}

      {finOpsPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 shadow-sm">
          <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">FinOps &amp; Budget Context</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3">
            <div>
              <p className="text-[11px] text-emerald-600">Active budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{finOpsPosture.budget_context.active_budgets}</p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600">Total limit</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">${finOpsPosture.budget_context.total_limit.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600">Spend 30d</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600">${finOpsPosture.budget_context.spend_30d.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600">Billing periods</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{finOpsPosture.billing_context.active_billing_periods} / {finOpsPosture.billing_context.total_billing_periods}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline">Budgets</Link>
            <Link href="/billing" className="text-xs text-emerald-600 hover:underline">Billing Periods</Link>
            <Link href="/chargeback" className="text-xs text-emerald-600 hover:underline">Chargeback</Link>
            <Link href="/cost-savings" className="text-xs text-emerald-600 hover:underline">Cost &amp; Savings</Link>
          </div>
        </div>
      )}

      {buildPosture && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-rose-600">Build &amp; Improve Loop</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Playground 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{buildPosture.playground_context.sessions_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Workflows</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{buildPosture.workflows_context.definitions}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Eval Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{buildPosture.evaluation_context.experiments}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Score Events 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{buildPosture.scorecards_context.score_events_30d}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-rose-200">
            <Link href="/playground" className="text-xs text-rose-600 hover:underline">Playground</Link>
            <Link href="/workflows" className="text-xs text-rose-600 hover:underline">Workflows</Link>
            <Link href="/evaluation?tab=scores" className="text-xs text-rose-600 hover:underline">Evaluation Studio</Link>
            <Link href="/model-scorecards" className="text-xs text-rose-600 hover:underline">Model Scorecards</Link>
          </div>
        </div>
      )}

      {decisionPosture && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-600">Cost, Evaluation &amp; Optimization Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Cost 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">${Number(decisionPosture.cost_context.cost_30d).toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Eval Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{decisionPosture.optimization_context.eval_experiments}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Replay Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{decisionPosture.optimization_context.replay_experiments}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <p className="text-xs text-slate-500">Score Events 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{decisionPosture.optimization_context.score_events_30d}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-amber-200">
            <Link href="/cost-savings" className="text-xs text-amber-600 hover:underline">Cost &amp; Savings</Link>
            <Link href="/optimization-opportunities" className="text-xs text-amber-600 hover:underline">Optimization Opportunities</Link>
            <Link href="/evaluation?tab=scores" className="text-xs text-amber-600 hover:underline">Evaluation Studio</Link>
            <Link href="/model-scorecards" className="text-xs text-amber-600 hover:underline">Model Scorecards</Link>
          </div>
        </div>
      )}

      {/* ── Configuration panel ── */}
      <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-5">
          <Layers className="h-4 w-4 text-blue-700" />
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">Simulation Parameters</h2>
        </div>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          <label className="space-y-1.5">
            <span className="text-xs font-semibold text-slate-600">Current model</span>
            <select value={currentModel} onChange={e => setCurrentModel(e.target.value)} className={`w-full ${inputCls}`}>
              {MODELS.map(m => <option key={`cur-${m.value}`} value={m.value}>{m.label || 'Any (all models)'}</option>)}
            </select>
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold text-slate-600">Proposed model</span>
            <select value={proposedModel} onChange={e => setProposedModel(e.target.value)} className={`w-full ${inputCls}`}>
              {MODELS.map(m => <option key={`prop-${m.value}`} value={m.value}>{m.label || 'No change'}</option>)}
            </select>
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold text-slate-600">Intent filter</span>
            <select value={intent} onChange={e => setIntent(e.target.value)} className={`w-full ${inputCls}`}>
              {INTENTS.map(i => <option key={i} value={i}>{i || 'All intents'}</option>)}
            </select>
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold text-slate-600">Time range</span>
            <select value={range} onChange={e => setRange(e.target.value)} className={`w-full ${inputCls}`}>
              {RANGES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </label>

          <div className="space-y-3 pt-1">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={enableCache}
                onChange={e => setEnableCache(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-slate-700">Enable caching</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={enableCompression}
                onChange={e => setEnableCompression(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-slate-700">Enable prompt compression</span>
            </label>
          </div>

          <div className="flex items-end">
            <button
              type="button"
              onClick={() => void handleRun()}
              disabled={!canRun || running}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-50"
            >
              {running ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {running ? 'Simulating...' : 'Run Simulation'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Results ── */}
      {result && result.affected_requests > 0 && (
        <>
          {/* KPI cards */}
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-emerald-100/40 p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Projected savings</p>
                <PiggyBank className="h-5 w-5 text-emerald-600" />
              </div>
              <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950 tabular-nums">
                {money(result.projected_savings_usd)}
              </p>
              <p className="mt-1 flex items-center gap-1 text-xs font-semibold text-emerald-600">
                <TrendingDown className="h-3 w-3" />
                {parseFloat(result.savings_pct).toFixed(1)}% cost reduction
              </p>
            </div>

            <div className="rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50 to-blue-100/40 p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Current cost</p>
                <DollarSign className="h-5 w-5 text-blue-600" />
              </div>
              <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950 tabular-nums">
                {money(result.current_cost_usd)}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                <ArrowRight className="mr-1 inline h-3 w-3" />
                {money(result.projected_cost_usd)} projected
              </p>
            </div>

            <div className="rounded-2xl border border-violet-200 bg-gradient-to-br from-violet-50 to-violet-100/40 p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Affected requests</p>
                <Zap className="h-5 w-5 text-violet-600" />
              </div>
              <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950 tabular-nums">
                {result.affected_requests.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${result.confidence === 'high' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : result.confidence === 'medium' ? 'border-amber-200 bg-amber-50 text-amber-700' : 'border-slate-200 bg-slate-100 text-slate-600'}`}>
                  {result.confidence} confidence
                </span>
              </p>
            </div>

            <div className={`rounded-2xl border p-5 shadow-sm ${risk?.bg}`}>
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Quality risk</p>
                <RiskIcon className={`h-5 w-5 ${risk?.text}`} />
              </div>
              <p className={`mt-2 font-display text-3xl font-semibold capitalize tracking-[-0.045em] ${risk?.text}`}>
                {result.quality_risk}
              </p>
              {result.latency_delta_pct && (
                <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                  <Clock className="h-3 w-3" />
                  Latency: {pct(result.latency_delta_pct)}
                </p>
              )}
            </div>
          </div>

          {/* Latency comparison */}
          {(result.current_avg_latency_ms || result.projected_latency_ms) && (
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="h-4 w-4 text-blue-700" />
                <h3 className="text-sm font-semibold text-slate-950">Latency Impact</h3>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Current avg</p>
                  <p className="mt-1 text-2xl font-semibold text-slate-900 tabular-nums">
                    {result.current_avg_latency_ms ? `${parseFloat(result.current_avg_latency_ms).toFixed(0)}ms` : 'n/a'}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Projected avg</p>
                  <p className="mt-1 text-2xl font-semibold text-slate-900 tabular-nums">
                    {result.projected_latency_ms ? `${parseFloat(result.projected_latency_ms).toFixed(0)}ms` : 'n/a'}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Delta</p>
                  <p className={`mt-1 text-2xl font-semibold tabular-nums ${result.latency_delta_pct && parseFloat(result.latency_delta_pct) > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {pct(result.latency_delta_pct)}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Impact breakdown */}
          {result.impacts.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="h-4 w-4 text-blue-700" />
                <h3 className="text-sm font-semibold text-slate-950">Impact Breakdown</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      <th className="pb-3 pr-4">Change</th>
                      <th className="pb-3 pr-4">Current</th>
                      <th className="pb-3 pr-4">Projected</th>
                      <th className="pb-3 text-right">Cost delta</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {result.impacts.map((impact, i) => (
                      <tr key={i} className="hover:bg-slate-50/80">
                        <td className="py-3 pr-4 font-medium text-slate-900">{impact.label}</td>
                        <td className="py-3 pr-4 text-slate-600">{impact.current_value}</td>
                        <td className="py-3 pr-4 font-medium text-blue-700">{impact.projected_value}</td>
                        <td className={`py-3 text-right font-semibold tabular-nums ${impact.delta_pct && parseFloat(impact.delta_pct) < 0 ? 'text-emerald-600' : impact.delta_pct && parseFloat(impact.delta_pct) > 0 ? 'text-rose-600' : 'text-slate-500'}`}>
                          {pct(impact.delta_pct)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Description summary */}
          <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 text-sm text-slate-600">
            <div className="flex items-start gap-3">
              <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
              <div>
                <p className="font-semibold text-slate-900">Simulation summary</p>
                <p className="mt-1 leading-6">{result.description}</p>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Empty state when no result yet */}
      {!result && !running && (
        <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white/60 px-6 py-20 text-center">
          <Cpu className="h-10 w-10 text-slate-400" />
          <h2 className="mt-4 text-lg font-semibold text-slate-700">Configure a simulation</h2>
          <p className="mt-1.5 max-w-md text-sm text-slate-500">
            Choose a current route, propose changes (model swap, caching, compression), and run the simulation to preview projected savings, latency impact, and quality risk.
          </p>
        </div>
      )}

      {/* No results empty state */}
      {result && result.affected_requests === 0 && (
        <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white/60 px-6 py-20 text-center">
          <ShieldCheck className="h-10 w-10 text-slate-400" />
          <h2 className="mt-4 text-lg font-semibold text-slate-700">No matching requests</h2>
          <p className="mt-1.5 max-w-md text-sm text-slate-500">
            No requests matched the current model/intent filters in the selected time range. Try broadening the filters or extending the time range.
          </p>
        </div>
      )}

      {/* Methodology note */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <FlaskConical className="mt-0.5 h-5 w-5 text-blue-700" />
          <div>
            <h2 className="font-semibold text-slate-950">How simulations work</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              The simulator queries your real request telemetry, applies cost ratios from known model pricing tiers, and estimates cache/compression impact from industry benchmarks. Quality risk is derived from model capability tiers. Projections improve with more telemetry — simulations on 100+ requests have high confidence.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
