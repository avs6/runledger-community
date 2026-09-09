import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import {
  ArrowRight,
  Banknote,
  DollarSign,
  Flame,
  LineChart,
  Network,
  PiggyBank,
  Target,
  TrendingDown,
  Wallet,
  Zap,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getBudgetRollup, getEconomicsFinopsPosture, getEconomicsGatewayPosture, getRunFlow } from '@/lib/api'
import DashboardScopeBar from '@/components/dashboard/DashboardScopeBar'
import { getDashboardWindow } from '@/lib/dashboard-window'
import {
  CostBreakdownBars,
  CostHeatmap,
  SavingsAttributionCards,
  type CostBreakdownPoint,
  type HeatmapRow,
  type SavingsCategoryPoint,
} from '@/components/dashboard/FinOpsCharts'
import type { BudgetRollupResponse, BudgetRollupWorkspace, EconomicsFinopsPosture, RunFlowRecord } from '@/types/api'
import { num } from '@/lib/utils'

type FlowScope = 'workspace' | 'org' | 'platform'

type RoiRow = {
  name: string
  spend: number
  saved: number
  requests: number
  successes: number
}

const heatmapColumns = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const savingsMeta: Record<string, { name: string; color: string; note: string }> = {
  prompt_compression: {
    name: 'Prompt compression',
    color: '#f59e0b',
    note: 'Savings from reducing prompt token volume before the provider call.',
  },
  cache_hits: {
    name: 'Cache hits',
    color: '#2563eb',
    note: 'Savings from reused cached input tokens or gateway cache hits.',
  },
  smart_routing: {
    name: 'Smart routing',
    color: '#7c3aed',
    note: 'Savings from choosing a cheaper eligible model or route.',
  },
  local_models: {
    name: 'Local models',
    color: '#059669',
    note: 'Savings attributed to local or self-hosted model lanes.',
  },
  duplicate_detection: {
    name: 'Duplicate detection',
    color: '#0f766e',
    note: 'Savings from avoiding repeated work.',
  },
  tool_optimization: {
    name: 'Tool optimization',
    color: '#0891b2',
    note: 'Savings from fewer or cheaper tool hops.',
  },
}

function parseMoney(value: string | null | undefined) {
  const parsed = Number.parseFloat(value ?? '0')
  return Number.isFinite(parsed) ? parsed : 0
}

function money(value: number) {
  if (!Number.isFinite(value)) return '$0'
  if (Math.abs(num(value)) >= 1) return `$${num(value).toFixed(2)}`
  if (Math.abs(num(value)) >= 0.001) return `$${num(value).toFixed(4)}`
  return `$${num(value).toFixed(6)}`
}

function percent(value: number) {
  if (!Number.isFinite(value)) return '0%'
  return `${num(value).toFixed(0)}%`
}

function allowedScope(raw: string | undefined, isPlatformAdmin: boolean, isOrgAdmin: boolean): FlowScope {
  const requested = raw === 'platform' || raw === 'org' || raw === 'workspace' ? raw : undefined
  const fallback: FlowScope = isPlatformAdmin ? 'platform' : isOrgAdmin ? 'org' : 'workspace'
  if (!requested) return fallback
  if (requested === 'platform' && !isPlatformAdmin) return fallback
  if (requested === 'org' && !isOrgAdmin && !isPlatformAdmin) return fallback
  return requested
}

function scopeLabel(scope: FlowScope): 'Platform' | 'Organization' | 'Workspace' {
  if (scope === 'platform') return 'Platform'
  if (scope === 'org') return 'Organization'
  return 'Workspace'
}

function modelName(item: RunFlowRecord) {
  return item.primary_model || item.provider || 'Unknown model'
}

function dimensionValue(item: RunFlowRecord, dimension: string) {
  if (dimension === 'Workspace') return item.workspace_name || item.application || 'Unassigned'
  if (dimension === 'Workflow') return item.feature_tag || item.application || 'Unassigned'
  if (dimension === 'Application') return item.application || 'Unassigned'
  if (dimension === 'User') return item.end_user_id || 'Anonymous'
  if (dimension === 'Agent') return item.agent || 'Direct request'
  if (dimension === 'Model') return modelName(item)
  if (dimension === 'Tool') return item.tool || 'No tool'
  if (dimension === 'Time') {
    const date = new Date(item.started_at)
    return Number.isNaN(date.getTime()) ? 'Unknown time' : date.toLocaleDateString([], { month: 'short', day: 'numeric' })
  }
  return 'Unassigned'
}

function buildBreakdown(items: RunFlowRecord[], dimension: string): CostBreakdownPoint[] {
  const map = new Map<string, CostBreakdownPoint>()
  for (const item of items) {
    const name = dimensionValue(item, dimension)
    const existing = map.get(name) ?? { name, spend: 0, saved: 0, requests: 0 }
    existing.spend += parseMoney(item.total_cost_usd)
    existing.saved += parseMoney(item.savings_usd)
    existing.requests += 1
    map.set(name, existing)
  }
  return Array.from(map.values()).sort((a, b) => b.spend + b.saved - (a.spend + a.saved)).slice(0, 10)
}

function buildRoiRows(items: RunFlowRecord[]): RoiRow[] {
  const map = new Map<string, RoiRow>()
  for (const item of items) {
    const name = item.workspace_name || item.application || item.feature_tag || 'Unassigned'
    const existing = map.get(name) ?? { name, spend: 0, saved: 0, requests: 0, successes: 0 }
    existing.spend += parseMoney(item.total_cost_usd)
    existing.saved += parseMoney(item.savings_usd)
    existing.requests += 1
    if (item.success) existing.successes += 1
    map.set(name, existing)
  }
  return Array.from(map.values()).sort((a, b) => b.spend - a.spend).slice(0, 12)
}

function buildSavings(items: RunFlowRecord[]): SavingsCategoryPoint[] {
  const buckets = new Map<string, number>()
  for (const item of items) {
    const amount = parseMoney(item.savings_usd)
    if (amount <= 0) continue
    let category = item.savings_category
    if (!category) {
      const text = `${item.primary_model ?? ''} ${item.provider ?? ''}`.toLowerCase()
      if (item.cached_input_tokens > 0) category = 'cache_hits'
      else if (text.includes('llama') || text.includes('local') || text.includes('ollama')) category = 'local_models'
      else category = 'smart_routing'
    }
    buckets.set(category, (buckets.get(category) ?? 0) + amount)
  }

  const total = items.reduce((sum, item) => sum + parseMoney(item.savings_usd), 0)
  const categorized = Array.from(buckets.values()).reduce((sum, value) => sum + value, 0)
  const uncategorized = Math.max(total - categorized, 0)
  if (uncategorized > 0) {
    buckets.set('smart_routing', (buckets.get('smart_routing') ?? 0) + uncategorized)
  }

  return Object.entries(savingsMeta).map(([key, meta]) => ({
    name: meta.name,
    value: buckets.get(key) ?? 0,
    color: meta.color,
    note: meta.note,
  }))
}

function buildHeatmap(items: RunFlowRecord[]): HeatmapRow[] {
  const map = new Map<string, HeatmapRow>()
  for (const item of items) {
    const date = new Date(item.started_at)
    if (Number.isNaN(date.getTime())) continue
    const day = date.toLocaleDateString('en-US', { weekday: 'short' })
    const name = item.workspace_name || item.application || item.feature_tag || 'Unassigned'
    const existing = map.get(name) ?? { name, values: {} }
    existing.values[day] = (existing.values[day] ?? 0) + parseMoney(item.total_cost_usd)
    map.set(name, existing)
  }
  return Array.from(map.values())
    .sort((a, b) => heatmapColumns.reduce((sum, day) => sum + (b.values[day] ?? 0) - (a.values[day] ?? 0), 0))
    .slice(0, 8)
}

function budgetRollupStatus(row: Pick<BudgetRollupWorkspace, 'active_budget_count' | 'pct_used' | 'exceeded_count' | 'at_risk_count'>) {
  const pct = parseMoney(row.pct_used)
  if (row.active_budget_count === 0) return { label: 'Missing', cls: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' }
  if (row.exceeded_count > 0) return { label: 'Exceeded', cls: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300' }
  if (row.at_risk_count > 0) return { label: 'At risk', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' }
  if (pct >= 100) return { label: 'Exceeded', cls: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300' }
  if (pct >= 80) return { label: 'At risk', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' }
  return { label: 'Healthy', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' }
}

function nextOptimization(rows: RoiRow[]) {
  const candidate = rows
    .map((row) => {
      const optimization = row.spend + row.saved > 0 ? (row.saved / (row.spend + row.saved)) * 100 : 0
      const costPerRequest = row.requests > 0 ? row.spend / row.requests : 0
      return { ...row, optimization, costPerRequest }
    })
    .sort((a, b) => b.spend * (1 - b.optimization / 100) - a.spend * (1 - a.optimization / 100))[0]
  if (!candidate) return null
  return {
    title: `${candidate.name} is the next best optimization target`,
    body: `${candidate.name} has ${money(candidate.spend)} in spend, ${percent(candidate.optimization)} optimization, and ${money(candidate.costPerRequest)} cost per request. Review cache, routing, and prompt compression rules here first.`,
  }
}

const TABS = [
  { id: 'breakdown', label: 'Cost Breakdown' },
  { id: 'roi', label: 'ROI Table' },
  { id: 'savings', label: 'Savings' },
  { id: 'heatmap', label: 'Heatmap' },
  { id: 'budget', label: 'Budget Overlay' },
] as const
type TabId = (typeof TABS)[number]['id']

export default async function CostSavingsPage({
  searchParams,
}: {
  searchParams?: Promise<{ range?: string; scope?: string; dimension?: string; tab?: string }>
}) {
  const session = await getServerSession(authOptions)
  if (!session?.apiKey) redirect('/login')
  const s = session as unknown as Record<string, unknown>
  const isPlatformAdmin = Boolean(s.isPlatformAdmin)
  const tenantRole = String(s.tenantRole ?? '')
  const isOrgAdmin = isPlatformAdmin || tenantRole === 'org_admin'
  const sp = (await searchParams) ?? {}
  const selectedScope = allowedScope(sp.scope, isPlatformAdmin, isOrgAdmin)
  const dimension = ['Workspace', 'Workflow', 'Application', 'User', 'Agent', 'Model', 'Tool', 'Time'].includes(sp.dimension ?? '')
    ? String(sp.dimension)
    : 'Workspace'
  const activeTab: TabId = TABS.some((t) => t.id === sp.tab) ? (sp.tab as TabId) : 'breakdown'
  const win = getDashboardWindow(sp.range ?? '30d')
  const [flow, budgetRollup, finopsPosture, gatewayPosture] = await Promise.all([
    getRunFlow(session.apiKey, {
      scope: selectedScope,
      mode: 'workspace-app-agent-model-cost',
      metric: 'cost',
      limit: 1000,
      from: win.from,
      to: win.to,
    }),
    getBudgetRollup(session.apiKey, selectedScope).catch(() => null as BudgetRollupResponse | null),
    getEconomicsFinopsPosture(session.apiKey).catch(() => null as EconomicsFinopsPosture | null),
    getEconomicsGatewayPosture(session.apiKey).catch(() => null),
  ])

  const items = flow.items
  const requests = flow.total_runs || items.length
  const spend = items.reduce((sum, item) => sum + parseMoney(item.total_cost_usd), 0)
  const saved = items.reduce((sum, item) => sum + parseMoney(item.savings_usd), 0)
  const optimization = spend + saved > 0 ? (saved / (spend + saved)) * 100 : 0
  const costPerRequest = requests > 0 ? spend / requests : 0
  const breakdown = buildBreakdown(items, dimension)
  const roiRows = buildRoiRows(items)
  const savings = buildSavings(items)
  const heatmapRows = buildHeatmap(items)
  const recommendation = nextOptimization(roiRows)
  const budgetRows = budgetRollup?.workspaces ?? []

  const postureChips: string[] = []
  if (finopsPosture) {
    postureChips.push(`${finopsPosture.billing_context.open_billing_periods} open periods`)
    postureChips.push(`${finopsPosture.billing_context.chargeback_rules} CB rules`)
    postureChips.push(`${finopsPosture.budget_context.active_overrides} overrides`)
    postureChips.push(`${finopsPosture.notification_context.active_notifications} notifications`)
    postureChips.push(`${finopsPosture.ledger_context.ledger_snapshots} snapshots`)
  }
  if (gatewayPosture) {
    postureChips.push(`${gatewayPosture.provider_context.distinct_providers} providers`)
    postureChips.push(`${gatewayPosture.gateway_context.active_routes} routes`)
    postureChips.push(`${gatewayPosture.gateway_context.distinct_models} models`)
    postureChips.push(`${gatewayPosture.investigation_context.runs_30d} runs 30d`)
  }

  return (
    <div className="space-y-5">
      {/* ── Hero ── */}
      <section className="rounded-2xl border border-slate-200 bg-white/90 px-6 py-8 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <DollarSign className="h-6 w-6 text-cyan-600 dark:text-cyan-400" />
              <h1 className="text-2xl font-bold tracking-tight text-slate-950 dark:text-white">Cost & Savings</h1>
            </div>
            <p className="mt-1.5 max-w-xl text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
              Trace spend by business dimension, explain savings, identify the next optimization target, and overlay budget guardrails — all in one command center.
            </p>
            {postureChips.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {postureChips.map((c) => (
                  <span key={c} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    {c}
                  </span>
                ))}
              </div>
            )}
          </div>
          <Link
            href="/budgets"
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-md transition hover:brightness-110"
          >
            Manage Budgets <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {/* KPI strip */}
        <div className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
          {[
            { label: 'AI Spend', value: money(spend) },
            { label: 'Saved', value: money(saved) },
            { label: 'Optimization', value: percent(optimization) },
            { label: 'Requests', value: requests.toLocaleString() },
            { label: 'Cost/Req', value: money(costPerRequest) },
            { label: 'Dimension', value: dimension },
            { label: 'Scope', value: scopeLabel(selectedScope) },
            { label: 'Range', value: win.label },
          ].map((kpi) => (
            <div key={kpi.label} className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">{kpi.label}</p>
              <p className="mt-0.5 truncate text-sm font-bold text-slate-900 dark:text-white">{kpi.value}</p>
            </div>
          ))}
        </div>

        {/* Scope selector */}
        <div className="mt-4 flex flex-wrap gap-2">
          {(['workspace', 'org', 'platform'] as FlowScope[]).map((scope) => {
            const disabled = (scope === 'platform' && !isPlatformAdmin) || (scope === 'org' && !isOrgAdmin && !isPlatformAdmin)
            if (disabled) return null
            const active = selectedScope === scope
            return (
              <Link
                key={scope}
                href={`/cost-savings?scope=${scope}&range=${win.range}&dimension=${dimension}&tab=${activeTab}`}
                className={`rounded-full px-3 py-1 text-[11px] font-semibold transition ${
                  active ? 'bg-cyan-100 text-cyan-700 ring-1 ring-cyan-300 dark:bg-cyan-500/30 dark:text-cyan-200 dark:ring-cyan-400/40' : 'bg-slate-100 text-slate-500 ring-1 ring-slate-200 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:ring-slate-700 dark:hover:bg-slate-700'
                }`}
              >
                {scopeLabel(scope)}
              </Link>
            )
          })}
        </div>
      </section>

      {/* Recommendation */}
      {recommendation && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4 shadow-sm dark:border-amber-800/50 dark:bg-amber-950/30">
          <div className="flex gap-3">
            <Flame className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
            <div>
              <p className="text-xs font-bold text-amber-900 dark:text-amber-200">{recommendation.title}</p>
              <p className="mt-1 text-[11px] leading-relaxed text-amber-800/80 dark:text-amber-300/70">{recommendation.body}</p>
            </div>
          </div>
        </div>
      )}

      <DashboardScopeBar
        scope={scopeLabel(selectedScope)}
        context={`${requests.toLocaleString()} requests in ${win.label.toLowerCase()}`}
        activeRange={win.range}
        basePath={`/cost-savings?scope=${selectedScope}&dimension=${dimension}&tab=${activeTab}`}
        dimensions={['Workspace', 'Workflow', 'Application', 'User', 'Agent', 'Model', 'Tool', 'Time', 'Budget']}
      />

      {/* Tab bar */}
      <div className="rounded-lg bg-slate-100 p-1 dark:bg-slate-800/80">
        <nav className="flex flex-wrap gap-1">
          {TABS.map((tab) => (
            <Link
              key={tab.id}
              href={`/cost-savings?scope=${selectedScope}&range=${win.range}&dimension=${dimension}&tab=${tab.id}`}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                activeTab === tab.id
                  ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Dimension chips (only for breakdown tab) */}
      {activeTab === 'breakdown' && (
        <div className="flex flex-wrap gap-1.5">
          {['Workspace', 'Workflow', 'Application', 'User', 'Agent', 'Model', 'Tool', 'Time'].map((d) => (
            <Link
              key={d}
              href={`/cost-savings?scope=${selectedScope}&range=${win.range}&dimension=${d}&tab=breakdown`}
              className={`rounded-full px-3 py-1 text-[11px] font-semibold transition ${
                dimension === d
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'border border-slate-200 bg-white text-slate-600 hover:bg-cyan-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
              }`}
            >
              {d}
            </Link>
          ))}
        </div>
      )}

      {/* ── Tab content ── */}

      {activeTab === 'breakdown' && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">Cost Breakdown — {dimension}</h2>
              <p className="text-[11px] text-slate-500">Top 10 by spend + saved. Click a dimension chip above to pivot.</p>
            </div>
            <Banknote className="h-5 w-5 text-cyan-500" />
          </div>
          <CostBreakdownBars data={breakdown} />
        </div>
      )}

      {activeTab === 'roi' && (
        <div className="overflow-hidden rounded-xl border border-slate-200 shadow-sm dark:border-slate-700">
          <div className="border-b border-slate-200 bg-white px-5 py-3 dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">ROI Table</h2>
                <p className="text-[11px] text-slate-500">Spend, saved, optimization %, requests, cost/request, and outcome rate.</p>
              </div>
              <Target className="h-5 w-5 text-cyan-500" />
            </div>
          </div>
          {roiRows.length === 0 ? (
            <div className="bg-white px-5 py-12 text-center text-xs text-slate-400 dark:bg-slate-900">No ROI rows yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                    {['Workspace / Workload', 'Spend', 'Saved', 'Optimization', 'Requests', 'Cost/Req', 'Outcome'].map((h) => (
                      <th key={h} className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {roiRows.map((row) => {
                    const rowOpt = row.spend + row.saved > 0 ? (row.saved / (row.spend + row.saved)) * 100 : 0
                    const rowCPR = row.requests > 0 ? row.spend / row.requests : 0
                    const outcome = row.requests > 0 ? (row.successes / row.requests) * 100 : 0
                    return (
                      <tr key={row.name} className="bg-white hover:bg-cyan-50/30 dark:bg-slate-900 dark:hover:bg-slate-800/50">
                        <td className="px-4 py-2.5 font-semibold text-slate-900 dark:text-white">{row.name}</td>
                        <td className="px-4 py-2.5 font-mono font-semibold text-slate-900 dark:text-white">{money(row.spend)}</td>
                        <td className="px-4 py-2.5 font-mono font-semibold text-emerald-600 dark:text-emerald-400">{money(row.saved)}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-700 dark:text-slate-300">{percent(rowOpt)}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-700 dark:text-slate-300">{row.requests.toLocaleString()}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-700 dark:text-slate-300">{money(rowCPR)}</td>
                        <td className="px-4 py-2.5 font-mono font-semibold text-slate-900 dark:text-white">{percent(outcome)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'savings' && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
                <TrendingDown className="h-4 w-4 text-emerald-500" /> Savings Attribution
              </h2>
              <p className="text-[11px] text-slate-500">
                Uses realized savings category/reason codes when present, with telemetry fallback for older cached or local-model traffic.
              </p>
            </div>
          </div>
          <SavingsAttributionCards data={savings} />
        </div>
      )}

      {activeTab === 'heatmap' && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">Cost Heatmap</h2>
              <p className="text-[11px] text-slate-500">Rows are workspaces/workflows/applications. Columns are day of week. Darker cells burn more spend.</p>
            </div>
            <Zap className="h-5 w-5 text-cyan-500" />
          </div>
          <CostHeatmap rows={heatmapRows} columns={heatmapColumns} />
        </div>
      )}

      {activeTab === 'budget' && (
        <div className="overflow-hidden rounded-xl border border-slate-200 shadow-sm dark:border-slate-700">
          <div className="border-b border-slate-200 bg-white px-5 py-3 dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
                  <Wallet className="h-4 w-4 text-blue-500" /> Budget Overlay
                </h2>
                <p className="text-[11px] text-slate-500">
                  {budgetRollup
                    ? `${scopeLabel(selectedScope)} guardrails across ${budgetRollup.workspace_count.toLocaleString()} workspace${budgetRollup.workspace_count === 1 ? '' : 's'}: ${money(parseMoney(budgetRollup.current_spend_usd))} used of ${money(parseMoney(budgetRollup.limit_usd))}.`
                    : 'Budget rollup is unavailable for this scope.'}
                </p>
              </div>
            </div>
          </div>
          {budgetRows.length === 0 ? (
            <div className="bg-white px-5 py-12 text-center text-xs text-slate-400 dark:bg-slate-900">No budget rollup rows for this scope.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                    {['Workspace', 'Budgets', 'Limit', 'Used', 'Remaining', 'Alert'].map((h) => (
                      <th key={h} className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {budgetRows.map((row) => {
                    const used = parseMoney(row.current_spend_usd)
                    const limit = parseMoney(row.limit_usd)
                    const remaining = parseMoney(row.remaining_usd)
                    const status = budgetRollupStatus(row)
                    return (
                      <tr key={row.workspace_id} className="bg-white hover:bg-cyan-50/30 dark:bg-slate-900 dark:hover:bg-slate-800/50">
                        <td className="px-4 py-2.5 font-semibold text-slate-900 dark:text-white">{row.workspace_name}</td>
                        <td className="px-4 py-2.5 font-mono">{row.active_budget_count}/{row.budget_count}</td>
                        <td className="px-4 py-2.5 font-mono">{money(limit)}</td>
                        <td className="px-4 py-2.5 font-mono">{money(used)}</td>
                        <td className="px-4 py-2.5 font-mono">{money(remaining)}</td>
                        <td className="px-4 py-2.5">
                          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${status.cls}`}>{status.label}</span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Context panels ── */}
      {finopsPosture && (
        <div className="rounded-xl border border-cyan-300 bg-gradient-to-r from-cyan-50 to-blue-50 p-4 dark:border-cyan-800/30 dark:from-cyan-950/30 dark:to-blue-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Wallet className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
            <h2 className="text-xs font-bold text-cyan-900 dark:text-cyan-200">FinOps Detail Context</h2>
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {[
              { label: 'Billing Periods', value: `${finopsPosture.billing_context.open_billing_periods}/${finopsPosture.billing_context.billing_periods}` },
              { label: 'Overrides', value: `${finopsPosture.budget_context.active_overrides}/${finopsPosture.budget_context.overrides}` },
              { label: 'Notifications', value: `${finopsPosture.notification_context.active_notifications}/${finopsPosture.notification_context.notifications}` },
              { label: 'Ledger Snapshots', value: String(finopsPosture.ledger_context.ledger_snapshots) },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg bg-white/80 p-2.5 dark:bg-slate-800/60">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-600 dark:text-cyan-400">{label}</p>
                <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-white">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {gatewayPosture && (
        <div className="rounded-xl border border-violet-300 bg-gradient-to-r from-violet-50 to-purple-50 p-4 dark:border-violet-800/30 dark:from-violet-950/30 dark:to-purple-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Network className="h-4 w-4 text-violet-600 dark:text-violet-400" />
            <h2 className="text-xs font-bold text-violet-900 dark:text-violet-200">Gateway & Provider Context</h2>
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {[
              { label: 'Providers', value: String(gatewayPosture.provider_context.distinct_providers) },
              { label: 'Routes', value: String(gatewayPosture.gateway_context.active_routes) },
              { label: 'Runs (30d)', value: String(gatewayPosture.investigation_context.runs_30d) },
              { label: 'Alerts (30d)', value: String(gatewayPosture.investigation_context.monitoring_alerts_30d) },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg bg-white/80 p-2.5 dark:bg-slate-800/60">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-400">{label}</p>
                <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-white">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Quick-nav footer ── */}
      <div className="flex flex-wrap gap-2 pt-2">
        {[
          { label: 'Budgets', href: '/budgets' },
          { label: 'Budget Overrides', href: '/budgets?tab=overrides' },
          { label: 'Notifications', href: '/budgets?tab=notifications' },
          { label: 'Billing Periods', href: '/billing' },
          { label: 'Chargeback', href: '/chargeback' },
          { label: 'Gateway', href: '/gateway' },
          { label: 'Provider Profiles', href: '/provider-profiles' },
          { label: 'Request Flow', href: '/request-flow' },
          { label: 'Monitoring', href: '/monitoring' },
        ].map(({ label, href }) => (
          <Link
            key={label}
            href={href}
            className="rounded-full border border-cyan-200 bg-cyan-50/80 px-3 py-1 text-[11px] font-semibold text-cyan-700 transition hover:bg-cyan-100 dark:border-cyan-800/50 dark:bg-cyan-950/30 dark:text-cyan-300 dark:hover:bg-cyan-900/40"
          >
            {label}
          </Link>
        ))}
      </div>
    </div>
  )
}
