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
import {
  getRunFlow, simulateOptimization,
  getOptimizationOrgGatewayPosture, getOptimizationObservePosture,
  getOptimizationFinOpsPosture, getBuildInternalPosture,
  getOptOppsRationalePosture, getOptSimDecisionPosture,
} from '@/lib/api'
import type {
  RunFlowRecord, SimulationResult,
  OptimizationOrgGatewayPosture, OptimizationObservePosture,
  OptimizationFinOpsPosture, BuildInternalPosture,
  OptOppsRationalePosture, OptSimDecisionPosture,
} from '@/types/api'
import { num } from '@/lib/utils'

type ViewTab = 'opportunities' | 'simulator'
type Risk = 'Low' | 'Medium' | 'High'
type Recommendation = {
  id: string; title: string; problem: string; evidence: string[]
  action: string; projectedSavings: number; projectedSavingsPct: number
  realizedSavings: number; risk: Risk; confidence: 'High' | 'Medium' | 'Directional'
  href: string; cta: string; category: string
}

function parseMoney(v: string | null | undefined) { const n = Number.parseFloat(v ?? '0'); return Number.isFinite(n) ? n : 0 }
function money(v: string | number) { const n = typeof v === 'string' ? parseFloat(v) : v; if (!Number.isFinite(n)) return '$0'; if (Math.abs(num(n)) >= 1) return `$${num(n).toFixed(2)}`; if (Math.abs(num(n)) >= 0.001) return `$${num(n).toFixed(4)}`; return `$${num(n).toFixed(6)}` }
function pct(v: string | number | null) { if (v === null) return 'n/a'; const n = typeof v === 'string' ? parseFloat(v) : v; if (!Number.isFinite(n)) return 'n/a'; return `${num(n) >= 0 ? '+' : ''}${num(n).toFixed(1)}%` }
function percent(v: number) { return Number.isFinite(v) ? `${num(v).toFixed(0)}%` : '0%' }

function modelClass(item: RunFlowRecord) {
  const t = `${item.primary_model ?? ''} ${item.provider ?? ''}`.toLowerCase()
  if (t.includes('gpt') || t.includes('openai')) return 'GPT'
  if (t.includes('claude') || t.includes('anthropic')) return 'Claude'
  if (t.includes('gemini') || t.includes('google')) return 'Gemini'
  if (t.includes('llama') || t.includes('local') || t.includes('ollama')) return 'Local'
  if (t.includes('deepseek')) return 'DeepSeek'
  return 'Other'
}

function taskIntent(item: RunFlowRecord) {
  const f = `${item.prompt} ${item.skill} ${item.agent} ${item.feature_tag ?? ''} ${item.route}`.toLowerCase()
  if (f.includes('doc') || f.includes('summar')) return 'Documentation / summarization'
  if (f.includes('code') || f.includes('repo') || f.includes('pull request')) return 'Coding'
  if (f.includes('search') || f.includes('research')) return 'Research'
  if (f.includes('support') || f.includes('ticket')) return 'Support'
  if (f.includes('reason') || f.includes('plan')) return 'Reasoning'
  return item.feature_tag || item.skill || item.agent || 'General'
}

function totalSpend(items: RunFlowRecord[]) { return items.reduce((s, i) => s + parseMoney(i.total_cost_usd), 0) }
function totalSavings(items: RunFlowRecord[], cats?: string[]) {
  const allowed = cats ? new Set(cats) : null
  return items.reduce((s, i) => { const c = i.savings_category; if (allowed && (!c || !allowed.has(c))) return s; return s + parseMoney(i.savings_usd) }, 0)
}

function generateRecommendations(items: RunFlowRecord[]): Recommendation[] {
  const recs: Recommendation[] = []
  const total = totalSpend(items)
  const requests = items.length
  const cached = items.filter((i) => i.cached_input_tokens > 0).length
  const cacheRate = requests > 0 ? (cached / requests) * 100 : 0
  const failures = items.filter((i) => !i.success)
  const failureSpend = totalSpend(failures)
  const localEligible = items.filter((i) => { const intent = taskIntent(i).toLowerCase(); return modelClass(i) !== 'Local' && (intent.includes('summar') || intent.includes('documentation') || intent.includes('support')) })
  const localEligibleSpend = totalSpend(localEligible)
  const gptDocs = items.filter((i) => modelClass(i) === 'GPT' && taskIntent(i).toLowerCase().includes('documentation'))
  const gptDocsSpend = totalSpend(gptDocs)
  const reasoningLike = items.filter((i) => { const t = `${i.primary_model ?? ''} ${i.route} ${i.prompt}`.toLowerCase(); return t.includes('reason') || t.includes('o3') || t.includes('o4') || t.includes('gpt-5') })
  const reasoningSpend = totalSpend(reasoningLike)
  const toolHeavy = items.filter((i) => i.tool && i.tool !== 'No tool')
  const toolSpend = totalSpend(toolHeavy)
  const slow = items.filter((i) => (i.latency_ms ?? 0) > 8000)
  const slowSpend = totalSpend(slow)

  if (cacheRate < 25 && requests >= 5) { const p = total * 0.18; recs.push({ id: 'cache-hit-rate', title: 'Raise cache hit rate on repeat traffic', problem: `Cache hit rate is ${percent(cacheRate)}, below the expected 35-45% for enterprise workflows.`, evidence: [`${cached.toLocaleString()} cached / ${requests.toLocaleString()} total`, `${money(total)} in scope`, 'Repeated prompts are strong cache candidates'], action: 'Enable exact/semantic cache on high-repeat routes.', projectedSavings: p, projectedSavingsPct: total > 0 ? (p / total) * 100 : 0, realizedSavings: totalSavings(items.filter((i) => i.cached_input_tokens > 0), ['cache_hits']), risk: 'Low', confidence: 'Medium', href: '/gateway', cta: 'Tune cache policy', category: 'Cache policy' }) }
  if (gptDocsSpend > 0) { const p = gptDocsSpend * 0.45; recs.push({ id: 'docs-model-mismatch', title: 'Route documentation to a cheaper model', problem: 'Documentation requests use GPT-class routes where a smaller model suffices.', evidence: [`${gptDocs.length.toLocaleString()} doc requests on GPT`, `${money(gptDocsSpend)} spend`, 'Expected 35-45% unit-cost reduction'], action: 'Create a gateway experiment comparing GPT, Claude Sonnet, and local models.', projectedSavings: p, projectedSavingsPct: 45, realizedSavings: totalSavings(gptDocs, ['smart_routing', 'local_models']), risk: 'Medium', confidence: 'Directional', href: '/evaluation?tab=experiments', cta: 'Launch experiment', category: 'Model routing' }) }
  if (localEligibleSpend > 0) { const p = localEligibleSpend * 0.35; recs.push({ id: 'local-model-lane', title: 'Move safe traffic to local models', problem: 'Repeatable low-risk traffic appears eligible for local model routing.', evidence: [`${localEligible.length.toLocaleString()} eligible requests`, `${money(localEligibleSpend)} spend`, 'Summarization/support is often low-risk'], action: 'Add a local-model route in approval mode, compare outcomes.', projectedSavings: p, projectedSavingsPct: 35, realizedSavings: totalSavings(localEligible, ['local_models']), risk: 'Medium', confidence: 'Directional', href: '/gateway', cta: 'Create local route', category: 'Local models' }) }
  if (reasoningLike.length > Math.max(3, requests * 0.15)) { const p = reasoningSpend * 0.28; recs.push({ id: 'reasoning-overuse', title: 'Reduce unnecessary reasoning-model usage', problem: `${percent(requests > 0 ? (reasoningLike.length / requests) * 100 : 0)} of requests look reasoning-heavy.`, evidence: [`${reasoningLike.length.toLocaleString()} reasoning requests`, `${money(reasoningSpend)} spend`, 'Many workflows only need reasoning for planning'], action: 'Add a classifier route for planning/reasoning intents.', projectedSavings: p, projectedSavingsPct: 28, realizedSavings: totalSavings(reasoningLike, ['smart_routing', 'prompt_compression']), risk: 'Medium', confidence: 'Medium', href: '/gateway', cta: 'Review routes', category: 'Reasoning control' }) }
  if (toolHeavy.length > Math.max(3, requests * 0.2)) { const p = toolSpend * 0.16; recs.push({ id: 'tool-overuse', title: 'Trim tool calls with MCP filtering', problem: 'High tool usage warrants filtering or skill routing.', evidence: [`${toolHeavy.length.toLocaleString()} tool requests`, `${money(toolSpend)} spend`, 'Tool filtering reduces latency and context'], action: 'Use MCP tool filtering per task class, measure cost deltas.', projectedSavings: p, projectedSavingsPct: 16, realizedSavings: totalSavings(toolHeavy, ['tool_optimization', 'prompt_compression', 'smart_routing']), risk: 'Low', confidence: 'Medium', href: '/mcp', cta: 'Open MCP tools', category: 'Tool optimization' }) }
  if (slow.length > 0) { const p = slowSpend * 0.12; recs.push({ id: 'latency-outliers', title: 'Investigate latency outliers', problem: `${slow.length.toLocaleString()} requests crossed 8s latency.`, evidence: [`${money(slowSpend)} on slow requests`, 'High latency correlates with retries', 'Route-level fallback protects UX'], action: 'Compare slow routes against faster alternatives.', projectedSavings: p, projectedSavingsPct: 12, realizedSavings: totalSavings(slow, ['smart_routing', 'local_models']), risk: 'Low', confidence: 'Medium', href: '/model-usage', cta: 'Compare models', category: 'Latency' }) }
  if (failures.length > 0) { const p = failureSpend * 0.5; recs.push({ id: 'failed-spend', title: 'Recover wasted spend from failures', problem: 'Failed requests still consume tokens and cost.', evidence: [`${failures.length.toLocaleString()} failed`, `${money(failureSpend)} wasted`, 'Failures should trigger fallback routing'], action: 'Add failure-aware fallback routing and alert on error spikes.', projectedSavings: p, projectedSavingsPct: 50, realizedSavings: totalSavings(failures), risk: 'Low', confidence: 'High', href: '/alert-rules', cta: 'Create alert', category: 'Reliability' }) }
  return recs.sort((a, b) => b.projectedSavings - a.projectedSavings).slice(0, 8)
}

function riskCls(risk: Risk) {
  if (risk === 'Low') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300'
  if (risk === 'Medium') return 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300'
  return 'bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-300'
}

const MODELS = [
  { value: '', label: 'Any (all models)' },
  { value: 'gpt-4o', label: 'GPT-4o' }, { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'gpt-4.1', label: 'GPT-4.1' }, { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' }, { value: 'gpt-4.1-nano', label: 'GPT-4.1 Nano' },
  { value: 'gpt-5', label: 'GPT-5' }, { value: 'o3', label: 'o3' }, { value: 'o4-mini', label: 'o4-mini' },
  { value: 'claude-sonnet-4', label: 'Claude Sonnet 4' }, { value: 'claude-opus-4', label: 'Claude Opus 4' }, { value: 'claude-haiku-3.5', label: 'Claude Haiku 3.5' },
  { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' }, { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  { value: 'deepseek-v3', label: 'DeepSeek V3' }, { value: 'deepseek-r1', label: 'DeepSeek R1' },
  { value: 'llama-3.3-70b', label: 'Llama 3.3 70B' }, { value: 'llama-4-scout', label: 'Llama 4 Scout' }, { value: 'llama-4-maverick', label: 'Llama 4 Maverick' },
  { value: 'qwen-3-235b', label: 'Qwen 3 235B' }, { value: 'local/ollama', label: 'Local / Ollama' },
]
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
  const [orgGatewayPosture, setOrgGatewayPosture] = useState<OptimizationOrgGatewayPosture | null>(null)
  const [observePosture, setObservePosture] = useState<OptimizationObservePosture | null>(null)
  const [finOpsPosture, setFinOpsPosture] = useState<OptimizationFinOpsPosture | null>(null)
  const [buildPosture, setBuildPosture] = useState<BuildInternalPosture | null>(null)
  const [rationalePosture, setRationalePosture] = useState<OptOppsRationalePosture | null>(null)
  const [decisionPosture, setDecisionPosture] = useState<OptSimDecisionPosture | null>(null)

  // Opportunities state
  const [items, setItems] = useState<RunFlowRecord[]>([])
  const [oppsLoading, setOppsLoading] = useState(true)
  const [range, setRange] = useState('30d')

  // Simulator state
  const [currentModel, setCurrentModel] = useState('')
  const [proposedModel, setProposedModel] = useState('')
  const [intent, setIntent] = useState('')
  const [enableCache, setEnableCache] = useState(false)
  const [enableCompression, setEnableCompression] = useState(false)
  const [simRange, setSimRange] = useState('30d')
  const [simRunning, setSimRunning] = useState(false)
  const [simResult, setSimResult] = useState<SimulationResult | null>(null)

  useEffect(() => {
    if (!apiKey) return
    getOptimizationOrgGatewayPosture(apiKey).then(setOrgGatewayPosture).catch(() => {})
    getOptimizationObservePosture(apiKey).then(setObservePosture).catch(() => {})
    getOptimizationFinOpsPosture(apiKey).then(setFinOpsPosture).catch(() => {})
    getBuildInternalPosture(apiKey).then(setBuildPosture).catch(() => {})
    getOptOppsRationalePosture(apiKey).then(setRationalePosture).catch(() => {})
    getOptSimDecisionPosture(apiKey).then(setDecisionPosture).catch(() => {})
  }, [apiKey])

  const loadOpps = useCallback(async () => {
    if (!apiKey) return
    setOppsLoading(true)
    const win = rangeWindow(range)
    try {
      const flow = await getRunFlow(apiKey, { scope: 'workspace', mode: 'workspace-app-agent-model-cost', metric: 'cost', limit: 1000, from: win.from, to: win.to })
      setItems(flow.items)
    } catch { toast.error('Failed to load optimization data') }
    finally { setOppsLoading(false) }
  }, [apiKey, range])

  useEffect(() => { loadOpps() }, [loadOpps])

  function handleTabChange(next: ViewTab) {
    setTab(next)
    router.replace(`/optimization-opportunities?tab=${next}`)
  }

  const recommendations = generateRecommendations(items)
  const totalProjected = recommendations.reduce((s, r) => s + r.projectedSavings, 0)
  const measuredSavings = totalSavings(items)
  const total = totalSpend(items)

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
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/25">
            <Lightbulb className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">Optimization</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Rule-based recommendations and what-if simulations for cost, latency, and quality.</p>
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
          { label: 'Opportunities', value: recommendations.length },
          { label: 'Projected', value: money(totalProjected), accent: true },
          { label: 'Measured', value: money(measuredSavings), accent: true },
          { label: 'Scope Spend', value: money(total) },
          { label: 'Requests', value: items.length.toLocaleString() },
          { label: 'Budgets', value: finOpsPosture?.budget_context.active_budgets ?? '—' },
          { label: 'Spend 30d', value: finOpsPosture ? `$${num(finOpsPosture.budget_context.spend_30d).toFixed(2)}` : '—' },
          { label: 'Models', value: observePosture?.model_usage_context.distinct_models_30d ?? '—' },
        ].map(({ label, value, accent }) => (
          <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
            <p className={`text-sm font-bold ${accent ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
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
        {finOpsPosture && (
          <div className="rounded-lg border border-emerald-200/60 dark:border-emerald-800/40 bg-emerald-50/30 dark:bg-emerald-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-1">FinOps</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-300">{finOpsPosture.budget_context.active_budgets} budgets</span>
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-300">${num(finOpsPosture.budget_context.spend_30d).toFixed(2)} spent</span>
              <Link href="/budgets" className="text-[10px] text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            </div>
          </div>
        )}
        {buildPosture && (
          <div className="rounded-lg border border-rose-200/60 dark:border-rose-800/40 bg-rose-50/30 dark:bg-rose-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-1">Build & Improve</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-[10px] text-rose-700 dark:text-rose-300">{buildPosture.evaluation_context.experiments} experiments</span>
              <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-[10px] text-rose-700 dark:text-rose-300">{buildPosture.scorecards_context.score_events_30d} scores</span>
              <Link href="/evaluation" className="text-[10px] text-rose-600 hover:underline dark:text-rose-400">Eval Studio</Link>
            </div>
          </div>
        )}
      </div>

      {/* ── Tab bar ─────────────────────────────────────── */}
      <div className="flex gap-0.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-0.5">
        {([
          { id: 'opportunities' as ViewTab, label: 'Opportunities', icon: <Lightbulb className="h-3.5 w-3.5" />, count: recommendations.length },
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
            <span className="text-[10px] text-slate-500 dark:text-slate-400">Range:</span>
            {RANGES.map((r) => (
              <button key={r.value} onClick={() => setRange(r.value)}
                className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition ${range === r.value ? 'bg-emerald-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'}`}>
                {r.label}
              </button>
            ))}
            {oppsLoading && <RefreshCw className="h-3.5 w-3.5 animate-spin text-slate-400" />}
          </div>

          {recommendations.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-900/60 p-10 text-center">
              <Sparkles className="mx-auto h-7 w-7 text-emerald-500" />
              <h2 className="mt-3 text-sm font-bold text-slate-800 dark:text-white">No strong recommendations yet</h2>
              <p className="mx-auto mt-1 max-w-lg text-xs text-slate-500">Send richer model, route, tool, cache, and outcome telemetry. Recommendations appear as usage patterns emerge.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recommendations.map((rec) => (
                <div key={rec.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                        <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">{rec.category}</span>
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${riskCls(rec.risk)}`}>{rec.risk} risk</span>
                        <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:text-slate-300">{rec.confidence}</span>
                      </div>
                      <h3 className="text-xs font-bold text-slate-900 dark:text-white">{rec.title}</h3>
                      <p className="mt-1 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">{rec.problem}</p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {rec.evidence.map((e) => (
                          <span key={e} className="rounded-lg bg-slate-50 dark:bg-slate-800/60 px-2 py-1 text-[10px] text-slate-600 dark:text-slate-300">{e}</span>
                        ))}
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        {rec.risk === 'High' ? <AlertTriangle className="h-3 w-3 text-rose-500" /> : <ShieldCheck className="h-3 w-3 text-emerald-500" />}
                        <span className="text-[10px] text-slate-600 dark:text-slate-300">{rec.action}</span>
                      </div>
                    </div>
                    <div className="shrink-0 text-right space-y-1.5">
                      <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-3 py-2">
                        <p className="text-[9px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Projected</p>
                        <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300 tabular-nums">{money(rec.projectedSavings)}</p>
                        <p className="text-[10px] text-emerald-600 dark:text-emerald-400">{percent(rec.projectedSavingsPct)} lift</p>
                      </div>
                      <div className="rounded-lg border border-blue-200/60 dark:border-blue-800/40 bg-blue-50/40 dark:bg-blue-950/20 px-3 py-1.5">
                        <p className="text-[9px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">Measured</p>
                        <p className="text-sm font-bold text-blue-700 dark:text-blue-300 tabular-nums">{money(rec.realizedSavings)}</p>
                      </div>
                      <div className="flex gap-1">
                        <Link href={rec.href} className="rounded-lg bg-slate-100 dark:bg-slate-800 px-2 py-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700">{rec.cta}</Link>
                        <Link href={`/evaluation?tab=experiments&recommendation=${rec.id}`} className="rounded-lg bg-emerald-600 px-2 py-1 text-[10px] font-semibold text-white hover:bg-emerald-700">
                          <Beaker className="h-3 w-3 inline mr-0.5" />Experiment
                        </Link>
                      </div>
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
                <p className="mt-0.5 text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">Deterministic rules over request-flow telemetry: model mismatch, cache hit rate, reasoning-heavy routes, tool overuse, latency outliers, failed spend, and local-model eligibility.</p>
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
                  {MODELS.map(m => <option key={`c-${m.value}`} value={m.value}>{m.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Proposed model *</label>
                <select value={proposedModel} onChange={e => setProposedModel(e.target.value)} className={inputCls}>
                  <option value="">No change</option>
                  {MODELS.filter(m => m.value).map(m => <option key={`p-${m.value}`} value={m.value}>{m.label}</option>)}
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
