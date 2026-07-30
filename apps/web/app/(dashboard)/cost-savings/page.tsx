import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { ArrowRight, Banknote, Flame, LineChart, PiggyBank, Target, TrendingDown, Wallet } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getBudgets, getRunFlow } from '@/lib/api'
import DashboardScopeBar, { getDashboardWindow } from '@/components/dashboard/DashboardScopeBar'
import {
  CostBreakdownBars,
  CostHeatmap,
  SavingsAttributionCards,
  type CostBreakdownPoint,
  type HeatmapRow,
  type SavingsCategoryPoint,
} from '@/components/dashboard/FinOpsCharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Budget, RunFlowRecord } from '@/types/api'

type FlowScope = 'workspace' | 'org' | 'platform'

type RoiRow = {
  name: string
  spend: number
  saved: number
  requests: number
  successes: number
}

const heatmapColumns = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function parseMoney(value: string | null | undefined) {
  const parsed = Number.parseFloat(value ?? '0')
  return Number.isFinite(parsed) ? parsed : 0
}

function money(value: number) {
  if (!Number.isFinite(value)) return '$0'
  if (Math.abs(value) >= 1) return `$${value.toFixed(2)}`
  if (Math.abs(value) >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

function percent(value: number) {
  if (!Number.isFinite(value)) return '0%'
  return `${value.toFixed(0)}%`
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
  if (dimension === 'Team') return item.team || item.workspace_name || 'Unassigned'
  if (dimension === 'Project') return item.feature_tag || item.application || 'Unassigned'
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
    const name = item.team || item.workspace_name || item.application || 'Unassigned'
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
  const cache = items.reduce((sum, item) => sum + (item.cached_input_tokens > 0 ? parseMoney(item.savings_usd) : 0), 0)
  const local = items.reduce((sum, item) => {
    const text = `${item.primary_model ?? ''} ${item.provider ?? ''}`.toLowerCase()
    return text.includes('llama') || text.includes('local') || text.includes('ollama') ? sum + parseMoney(item.savings_usd) : sum
  }, 0)
  const total = items.reduce((sum, item) => sum + parseMoney(item.savings_usd), 0)
  const remaining = Math.max(total - cache - local, 0)
  return [
    { name: 'Cache hits', value: cache, color: '#2563eb', note: 'Savings from reused cached input tokens.' },
    { name: 'Smart routing', value: remaining * 0.36, color: '#7c3aed', note: 'Directional savings from cheaper eligible model routes.' },
    { name: 'Prompt compression', value: remaining * 0.24, color: '#f59e0b', note: 'Directional savings from reduced prompt token volume.' },
    { name: 'Local models', value: local, color: '#059669', note: 'Savings attributed to local or self-hosted model lanes.' },
    { name: 'Duplicate detection', value: remaining * 0.18, color: '#0f766e', note: 'Directional savings from avoiding repeated work.' },
    { name: 'Tool optimization', value: remaining * 0.22, color: '#0891b2', note: 'Directional savings from fewer or cheaper tool hops.' },
  ]
}

function buildHeatmap(items: RunFlowRecord[]): HeatmapRow[] {
  const map = new Map<string, HeatmapRow>()
  for (const item of items) {
    const date = new Date(item.started_at)
    if (Number.isNaN(date.getTime())) continue
    const day = date.toLocaleDateString('en-US', { weekday: 'short' })
    const name = item.team || item.workspace_name || item.application || 'Unassigned'
    const existing = map.get(name) ?? { name, values: {} }
    existing.values[day] = (existing.values[day] ?? 0) + parseMoney(item.total_cost_usd)
    map.set(name, existing)
  }
  return Array.from(map.values())
    .sort((a, b) => heatmapColumns.reduce((sum, day) => sum + (b.values[day] ?? 0) - (a.values[day] ?? 0), 0))
    .slice(0, 8)
}

function budgetStatus(budget: Budget) {
  const pct = parseMoney(budget.pct_used)
  if (!budget.is_active) return { label: 'Paused', className: 'bg-slate-100 text-slate-600' }
  if (pct >= 100) return { label: 'Exceeded', className: 'bg-rose-100 text-rose-700' }
  if (pct >= 80) return { label: 'At risk', className: 'bg-amber-100 text-amber-700' }
  return { label: 'Healthy', className: 'bg-emerald-100 text-emerald-700' }
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

export default async function CostSavingsPage({
  searchParams,
}: {
  searchParams?: { range?: string; scope?: string; dimension?: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session?.apiKey) redirect('/login')
  const s = session as unknown as Record<string, unknown>
  const isPlatformAdmin = Boolean(s.isPlatformAdmin)
  const tenantRole = String(s.tenantRole ?? '')
  const isOrgAdmin = isPlatformAdmin || tenantRole === 'org_admin'
  const selectedScope = allowedScope(searchParams?.scope, isPlatformAdmin, isOrgAdmin)
  const dimension = ['Team', 'Project', 'Application', 'User', 'Agent', 'Model', 'Tool', 'Time'].includes(searchParams?.dimension ?? '')
    ? String(searchParams?.dimension)
    : 'Team'
  const win = getDashboardWindow(searchParams?.range ?? '30d')
  const [flow, budgetsResult] = await Promise.all([
    getRunFlow(session.apiKey, {
      scope: selectedScope,
      mode: 'team-app-agent-model-cost',
      metric: 'cost',
      limit: 1000,
      from: win.from,
      to: win.to,
    }),
    getBudgets(session.apiKey).catch(() => ({ items: [] })),
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
  const budgets = budgetsResult.items

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-[11px] font-semibold text-blue-700">
            Phase 7
          </span>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950">Cost & Savings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Trace spend by business dimension, explain savings, and identify the next optimization target.
          </p>
        </div>
        <Link
          href="/budgets"
          className="inline-flex items-center gap-1 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700 transition-colors hover:bg-blue-100"
        >
          Manage budgets <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        {(['workspace', 'org', 'platform'] as FlowScope[]).map((scope) => {
          const disabled = (scope === 'platform' && !isPlatformAdmin) || (scope === 'org' && !isOrgAdmin && !isPlatformAdmin)
          if (disabled) return null
          const active = selectedScope === scope
          return (
            <Link
              key={scope}
              href={`/cost-savings?scope=${scope}&range=${win.range}&dimension=${dimension}`}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                active ? 'bg-blue-600 text-white shadow-sm' : 'border border-slate-200 bg-white text-slate-600 hover:bg-blue-50'
              }`}
            >
              {scopeLabel(scope)}
            </Link>
          )
        })}
      </div>

      <DashboardScopeBar
        scope={scopeLabel(selectedScope)}
        context={`${requests.toLocaleString()} requests in ${win.label.toLowerCase()}`}
        activeRange={win.range}
        basePath={`/cost-savings?scope=${selectedScope}&dimension=${dimension}`}
        dimensions={['Team', 'Project', 'Application', 'User', 'Agent', 'Model', 'Tool', 'Time', 'Budget']}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { title: 'AI spend', value: money(spend), sub: 'Actual observed spend', icon: Banknote },
          { title: 'Saved', value: money(saved), sub: `${percent(optimization)} optimization`, icon: PiggyBank },
          { title: 'Requests', value: requests.toLocaleString(), sub: `${money(costPerRequest)} per request`, icon: LineChart },
          { title: 'Next target', value: recommendation ? recommendation.title.split(' ')[0] : 'n/a', sub: recommendation ? 'Highest-value optimization' : 'Needs more data', icon: Target },
        ].map(({ title, value, sub, icon: Icon }) => (
          <div key={title} className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</p>
                <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{value}</p>
                <p className="mt-1 text-xs text-slate-500">{sub}</p>
              </div>
              <div className="rounded-xl bg-blue-50 p-2.5 text-blue-700">
                <Icon className="h-5 w-5" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {recommendation && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 text-amber-950 shadow-sm">
          <div className="flex gap-3">
            <Flame className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
            <div>
              <p className="font-semibold">{recommendation.title}</p>
              <p className="mt-1 text-sm text-amber-900/80">{recommendation.body}</p>
            </div>
          </div>
        </div>
      )}

      <Card className="border-slate-200 bg-white/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Cost Breakdown</CardTitle>
          <p className="text-xs text-muted-foreground">Drill into spend by team, project, application, user, agent, model, tool, or time.</p>
          <div className="flex flex-wrap gap-2 pt-2">
            {['Team', 'Project', 'Application', 'User', 'Agent', 'Model', 'Tool', 'Time'].map((item) => (
              <Link
                key={item}
                href={`/cost-savings?scope=${selectedScope}&range=${win.range}&dimension=${item}`}
                className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                  dimension === item ? 'bg-blue-600 text-white shadow-sm' : 'border border-slate-200 bg-white text-slate-600 hover:bg-blue-50'
                }`}
              >
                {item}
              </Link>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <CostBreakdownBars data={breakdown} />
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-slate-200 bg-white/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">ROI Table</CardTitle>
          <p className="text-xs text-muted-foreground">Spend, saved, optimization percentage, requests, cost/request, and outcome rate by team or workspace.</p>
        </CardHeader>
        <CardContent className="p-0">
          {roiRows.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-muted-foreground">No ROI rows yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-y border-slate-200 bg-slate-50/80">
                  {['Team / workspace', 'Spend', 'Saved', 'Optimization', 'Requests', 'Cost/request', 'Outcome rate'].map((heading) => (
                    <th key={heading} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {roiRows.map((row) => {
                  const rowOptimization = row.spend + row.saved > 0 ? (row.saved / (row.spend + row.saved)) * 100 : 0
                  const rowCostPerRequest = row.requests > 0 ? row.spend / row.requests : 0
                  const outcomeRate = row.requests > 0 ? (row.successes / row.requests) * 100 : 0
                  return (
                    <tr key={row.name} className="hover:bg-blue-50/40">
                      <td className="px-5 py-3 font-semibold text-slate-950">{row.name}</td>
                      <td className="px-5 py-3 font-mono text-xs font-semibold">{money(row.spend)}</td>
                      <td className="px-5 py-3 font-mono text-xs font-semibold text-emerald-700">{money(row.saved)}</td>
                      <td className="px-5 py-3 font-mono text-xs">{percent(rowOptimization)}</td>
                      <td className="px-5 py-3 font-mono text-xs">{row.requests.toLocaleString()}</td>
                      <td className="px-5 py-3 font-mono text-xs">{money(rowCostPerRequest)}</td>
                      <td className="px-5 py-3 font-mono text-xs font-semibold">{percent(outcomeRate)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Card className="border-slate-200 bg-white/90 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            <TrendingDown className="h-4 w-4 text-emerald-600" /> Savings Attribution
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Cache and local model savings are telemetry-backed. Routing, prompt compression, duplicate detection, and tool optimization are directional until realized savings categories are stored per request.
          </p>
        </CardHeader>
        <CardContent>
          <SavingsAttributionCards data={savings} />
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="border-slate-200 bg-white/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Cost Heatmap</CardTitle>
            <p className="text-xs text-muted-foreground">Rows are teams/workspaces/applications. Columns are day of week. Darker cells burn more spend.</p>
          </CardHeader>
          <CardContent>
            <CostHeatmap rows={heatmapRows} columns={heatmapColumns} />
          </CardContent>
        </Card>

        <Card className="overflow-hidden border-slate-200 bg-white/90 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Wallet className="h-4 w-4 text-blue-600" /> Budget Overlay
            </CardTitle>
            <p className="text-xs text-muted-foreground">Current workspace budget guardrails. Org/platform budget rollups can layer in once budgets are scoped beyond workspace API keys.</p>
          </CardHeader>
          <CardContent className="p-0">
            {budgets.length === 0 ? (
              <div className="px-5 py-12 text-center text-sm text-muted-foreground">No budgets configured for this workspace.</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-y border-slate-200 bg-slate-50/80">
                    {['Scope', 'Limit', 'Used', 'Remaining', 'Alert'].map((heading) => (
                      <th key={heading} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {budgets.map((budget) => {
                    const used = parseMoney(budget.current_spend_usd)
                    const limit = parseMoney(budget.limit_usd)
                    const remaining = Math.max(limit - used, 0)
                    const status = budgetStatus(budget)
                    return (
                      <tr key={budget.id} className="hover:bg-blue-50/40">
                        <td className="px-4 py-3 font-semibold text-slate-950">{budget.scope_type}</td>
                        <td className="px-4 py-3 font-mono text-xs">{money(limit)}</td>
                        <td className="px-4 py-3 font-mono text-xs">{money(used)}</td>
                        <td className="px-4 py-3 font-mono text-xs">{money(remaining)}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${status.className}`}>{status.label}</span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
