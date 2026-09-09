import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import {
  Activity,
  ArrowRight,
  Clock,
  Cpu,
  DollarSign,
  GitBranch,
  Network,
  Route,
  Search,
  Sparkles,
  Table2,
  Tags,
  Wallet,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import {
  getBestValueModels,
  getBudgetControlObservePosture,
  getCostQuality,
  getInvestigationGatewayRuntimePosture,
  getModelBudgetUtilization,
  getModelUsageGatewayPosture,
  getRunFlow,
} from '@/lib/api'
import DashboardScopeBar from '@/components/dashboard/DashboardScopeBar'
import { getDashboardWindow } from '@/lib/dashboard-window'
import {
  ModelQualityCostBars,
  RoutingDistribution,
  StackedResourceTimeline,
  type ModelTimelineDetail,
  type ModelTimelinePoint,
  type QualityCostPoint,
  type RoutingSlice,
} from '@/components/dashboard/ModelRoutingCharts'
import { MODEL_FAMILY_COLORS, classifyModel as classifyModelFamily } from '@/lib/modelColors'
import type { BestValueModel, RunFlowRecord } from '@/types/api'
import { num } from '@/lib/utils'

type FlowScope = 'workspace' | 'org' | 'platform'

type ModelRollup = {
  model: string
  provider: string
  requests: number
  inputTokens: number
  outputTokens: number
  cachedTokens: number
  cost: number
  savings: number
  latencyTotal: number
  latencySamples: number
  successes: number
}

type RouteRollup = {
  key: string
  route: string
  model: string
  provider: string
  requests: number
  cost: number
  savings: number
  latencyTotal: number
  latencySamples: number
  successes: number
  cached: number
}

const modelColors = MODEL_FAMILY_COLORS

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

function formatLatency(ms: number | null) {
  if (ms === null || !Number.isFinite(ms)) return 'n/a'
  if (num(ms) >= 1000) return `${(num(ms) / 1000).toFixed(1)}s`
  return `${Math.round(ms)}ms`
}

function shortNumber(value: number) {
  return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

function parseScore(value: string | null | undefined) {
  if (value == null) return null
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) ? parsed : null
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

function classifyModel(item: RunFlowRecord) {
  return classifyModelFamily(item.primary_model, {
    provider: item.provider,
    status: item.status,
    cachedTokens: item.cached_input_tokens,
    success: item.success,
  })
}

function buildTimeline(items: RunFlowRecord[]) {
  const buckets = new Map<string, { total: number; counts: Record<string, number>; details: Record<string, ModelTimelineDetail & { latencyTotal: number; latencySamples: number; successes: number; requests: number }> }>()
  for (const item of items) {
    const date = new Date(item.started_at)
    if (Number.isNaN(date.getTime())) continue
    const period = date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    const model = classifyModel(item)
    const bucket = buckets.get(period) ?? { total: 0, counts: {}, details: {} }
    bucket.total += 1
    bucket.counts[model] = (bucket.counts[model] ?? 0) + 1
    const detail = bucket.details[model] ?? {
      inputTokens: 0, outputTokens: 0, cost: 0, cacheSavings: 0,
      latencyMs: null, outcomeRate: 0, latencyTotal: 0, latencySamples: 0, successes: 0, requests: 0,
    }
    detail.inputTokens += item.total_input_tokens
    detail.outputTokens += item.total_output_tokens
    detail.cost += parseMoney(item.total_cost_usd)
    detail.cacheSavings += item.cached_input_tokens > 0 ? parseMoney(item.savings_usd) : 0
    detail.requests += 1
    if (item.success) detail.successes += 1
    if (item.latency_ms !== null) {
      detail.latencyTotal += item.latency_ms
      detail.latencySamples += 1
    }
    bucket.details[model] = detail
    buckets.set(period, bucket)
  }

  const data: ModelTimelinePoint[] = []
  const details: Record<string, Record<string, ModelTimelineDetail>> = {}
  const keys = Object.keys(modelColors).filter((key) => items.some((item) => classifyModel(item) === key))
  for (const [period, bucket] of Array.from(buckets.entries())) {
    const point: ModelTimelinePoint = { period }
    details[period] = {}
    for (const key of keys) {
      point[key] = bucket.total > 0 ? ((bucket.counts[key] ?? 0) / bucket.total) * 100 : 0
      const detail = bucket.details[key]
      if (detail) {
        details[period][key] = {
          inputTokens: detail.inputTokens, outputTokens: detail.outputTokens,
          cost: detail.cost, cacheSavings: detail.cacheSavings,
          latencyMs: detail.latencySamples > 0 ? detail.latencyTotal / detail.latencySamples : null,
          outcomeRate: detail.requests > 0 ? (detail.successes / detail.requests) * 100 : 0,
        }
      }
    }
    data.push(point)
  }
  return { data, details, keys }
}

function rollupModels(items: RunFlowRecord[]) {
  const map = new Map<string, ModelRollup>()
  for (const item of items) {
    const key = modelName(item)
    const existing = map.get(key) ?? {
      model: key, provider: item.provider || 'unknown',
      requests: 0, inputTokens: 0, outputTokens: 0, cachedTokens: 0,
      cost: 0, savings: 0, latencyTotal: 0, latencySamples: 0, successes: 0,
    }
    existing.requests += 1
    existing.inputTokens += item.total_input_tokens
    existing.outputTokens += item.total_output_tokens
    existing.cachedTokens += item.cached_input_tokens
    existing.cost += parseMoney(item.total_cost_usd)
    existing.savings += parseMoney(item.savings_usd)
    if (item.latency_ms !== null) {
      existing.latencyTotal += item.latency_ms
      existing.latencySamples += 1
    }
    if (item.success) existing.successes += 1
    map.set(key, existing)
  }
  return Array.from(map.values()).sort((a, b) => b.cost - a.cost)
}

function rollupRoutes(items: RunFlowRecord[]) {
  const map = new Map<string, RouteRollup>()
  for (const item of items) {
    const route = item.route || 'default'
    const model = modelName(item)
    const key = `${route}|${model}|${item.provider ?? 'unknown'}`
    const existing = map.get(key) ?? {
      key, route, model, provider: item.provider || 'unknown',
      requests: 0, cost: 0, savings: 0, latencyTotal: 0, latencySamples: 0, successes: 0, cached: 0,
    }
    existing.requests += 1
    existing.cost += parseMoney(item.total_cost_usd)
    existing.savings += parseMoney(item.savings_usd)
    if (item.latency_ms !== null) {
      existing.latencyTotal += item.latency_ms
      existing.latencySamples += 1
    }
    if (item.success) existing.successes += 1
    if (item.cached_input_tokens > 0) existing.cached += 1
    map.set(key, existing)
  }
  return Array.from(map.values()).sort((a, b) => b.cost - a.cost).slice(0, 8)
}

function routeReason(route: RouteRollup) {
  const text = `${route.route} ${route.model} ${route.provider}`.toLowerCase()
  if (route.cached > 0) return 'Cache lane reduced repeated model work.'
  if (text.includes('local') || text.includes('llama') || text.includes('ollama')) return 'Local model for privacy/lower cost.'
  if (text.includes('fallback')) return 'Fallback when preferred provider unavailable.'
  if (text.includes('budget') || text.includes('cost')) return 'Cost-aware policy under budget guardrails.'
  return 'Gateway routing selected this provider/model.'
}

export default async function ModelUsagePage({
  searchParams,
}: {
  searchParams?: { range?: string; scope?: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session?.apiKey) redirect('/login')
  const s = session as unknown as Record<string, unknown>
  const isPlatformAdmin = Boolean(s.isPlatformAdmin)
  const tenantRole = String(s.tenantRole ?? '')
  const isOrgAdmin = isPlatformAdmin || tenantRole === 'org_admin'
  const selectedScope = allowedScope(searchParams?.scope, isPlatformAdmin, isOrgAdmin)
  const win = getDashboardWindow(searchParams?.range ?? '30d')
  const flow = await getRunFlow(session.apiKey, {
    scope: selectedScope,
    mode: 'request-route-provider-outcome',
    metric: 'requests',
    limit: 1000,
    from: win.from,
    to: win.to,
  })
  const budgetControlPosture = await getBudgetControlObservePosture(session.apiKey).catch(() => null)
  const [costQuality, bestValue, modelBudgets, gatewayPosture, gatewayRuntime] = await Promise.all([
    getCostQuality(session.apiKey, { score_name: 'quality', from: win.from, to: win.to }).catch(() => ({ items: [] })),
    getBestValueModels(session.apiKey, { score_name: 'quality', from: win.from, to: win.to }).catch(() => ({ items: [] })),
    getModelBudgetUtilization(session.apiKey).catch(() => null),
    getModelUsageGatewayPosture(session.apiKey).catch(() => null),
    getInvestigationGatewayRuntimePosture(session.apiKey).catch(() => null),
  ])

  const items = flow.items
  const timeline = buildTimeline(items)
  const models = rollupModels(items)
  const routes = rollupRoutes(items)
  const requests = flow.total_runs || items.length
  const totalCost = items.reduce((sum, item) => sum + parseMoney(item.total_cost_usd), 0)
  const totalSavings = items.reduce((sum, item) => sum + parseMoney(item.savings_usd), 0)
  const avgLatency = (() => {
    const samples = items.map((item) => item.latency_ms).filter((value): value is number => value !== null)
    return samples.length > 0 ? samples.reduce((sum, value) => sum + value, 0) / samples.length : null
  })()
  const cacheHitRate = items.length > 0 ? (items.filter((item) => item.cached_input_tokens > 0).length / items.length) * 100 : 0

  const routingSlices: RoutingSlice[] = Object.entries(
    items.reduce<Record<string, number>>((acc, item) => {
      const key = classifyModel(item)
      acc[key] = (acc[key] ?? 0) + 1
      return acc
    }, {})
  ).map(([name, value]) => ({ name, value, color: modelColors[name] ?? modelColors.Other }))

  const qualityCost: QualityCostPoint[] = models.slice(0, 8).map((model) => ({
    model: model.model,
    cost: model.cost,
    latency: model.latencySamples > 0 ? model.latencyTotal / model.latencySamples : 0,
    quality:
      parseScore(costQuality.items.find((item) => item.model === model.model)?.avg_score) ??
      (model.requests > 0 ? (model.successes / model.requests) * 100 : 0),
  }))
  const qualityScoreMap = new Map(costQuality.items.map((item) => [item.model, parseScore(item.avg_score)]))
  const bestValueByModel = new Map<string, BestValueModel>(bestValue.items.map((item) => [item.model, item]))
  const qualitySamples = costQuality.items.filter((item) => item.avg_score !== null)
  const avgQualityScore =
    qualitySamples.length > 0
      ? qualitySamples.reduce((sum, item) => sum + (parseScore(item.avg_score) ?? 0), 0) / qualitySamples.length
      : null

  const cheapestModel = models.filter((m) => m.requests > 0).sort((a, b) => a.cost / a.requests - b.cost / b.requests)[0]
  const fastestModel = models.filter((m) => m.latencySamples > 0).sort((a, b) => a.latencyTotal / a.latencySamples - b.latencyTotal / b.latencySamples)[0]

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">Model Usage</h1>
          <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">Models, routes, cost, latency, cache, and outcomes.</p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {(['workspace', 'org', 'platform'] as FlowScope[]).map((scope) => {
            const disabled = (scope === 'platform' && !isPlatformAdmin) || (scope === 'org' && !isOrgAdmin && !isPlatformAdmin)
            if (disabled) return null
            const active = selectedScope === scope
            return (
              <Link
                key={scope}
                href={`/model-usage?scope=${scope}&range=${win.range}`}
                className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition ${active ? 'bg-blue-600 text-white shadow-sm' : 'border border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'}`}
              >
                {scopeLabel(scope)}
              </Link>
            )
          })}
          <Link
            href={`/request-flow?scope=${selectedScope}&mode=request-route-provider-outcome&metric=cost`}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            Flow <ArrowRight className="h-3 w-3" />
          </Link>
          <Link href="/request-explorer" className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
            Explorer <Search className="h-3 w-3" />
          </Link>
        </div>
      </div>

      <DashboardScopeBar
        scope={scopeLabel(selectedScope)}
        context={`${requests.toLocaleString()} requests`}
        activeRange={win.range}
        basePath={`/model-usage?scope=${selectedScope}`}
        dimensions={['Model', 'Provider', 'Route', 'Cache', 'Tokens', 'Latency', 'Outcome']}
      />

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-6">
        {[
          { title: 'Requests', value: requests.toLocaleString(), sub: `${items.length.toLocaleString()} sampled`, icon: Activity, color: 'text-blue-600 dark:text-blue-400' },
          { title: 'Model Spend', value: money(totalCost), sub: `${money(totalSavings)} saved`, icon: Cpu, color: 'text-emerald-600 dark:text-emerald-400' },
          { title: 'Avg Latency', value: formatLatency(avgLatency), icon: Clock, color: 'text-blue-600 dark:text-blue-400' },
          { title: 'Cache Rate', value: percent(cacheHitRate), icon: Sparkles, color: 'text-purple-600 dark:text-purple-400' },
          { title: 'Quality', value: avgQualityScore !== null ? percent(avgQualityScore) : 'n/a', sub: avgQualityScore !== null ? `${qualitySamples.length} scored` : 'No scores yet', icon: Sparkles, color: 'text-amber-600 dark:text-amber-400' },
          { title: 'Models', value: `${models.length}`, sub: `${routes.length} routes`, icon: Cpu, color: 'text-blue-600 dark:text-blue-400' },
        ].map(kpi => (
          <div key={kpi.title} className="rounded-xl border border-slate-200 bg-white/90 p-2.5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-1">
              <kpi.icon className={`h-3 w-3 ${kpi.color}`} />
              <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">{kpi.title}</span>
            </div>
            <p className="mt-1 text-base font-bold text-slate-950 dark:text-white">{kpi.value}</p>
            {kpi.sub && <p className="text-[10px] text-slate-400">{kpi.sub}</p>}
          </div>
        ))}
      </div>

      {/* Charts: Timeline hero + Routing + Quality side by side */}
      <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-2 flex items-center gap-1.5">
          <GitBranch className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Resource Usage Timeline</p>
          <span className="text-[10px] text-slate-400">Daily model mix by request count</span>
        </div>
        <StackedResourceTimeline data={timeline.data} keys={timeline.keys} colors={modelColors} details={timeline.details} />
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-2 flex items-center gap-1.5">
            <Route className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
            <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Routing Distribution</p>
          </div>
          <RoutingDistribution data={routingSlices} />
        </div>
        <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-2 flex items-center gap-1.5">
            <Table2 className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
            <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Cost / Latency / Quality</p>
          </div>
          <ModelQualityCostBars data={qualityCost} />
        </div>
      </div>

      {/* Gateway posture — compact chips */}
      {gatewayPosture && (
        <div className="rounded-xl border border-violet-300 bg-violet-50 p-3 dark:border-violet-800/40 dark:bg-violet-950/20">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <Network className="h-3.5 w-3.5 text-violet-600 dark:text-violet-400" />
              <span className="text-xs font-semibold text-violet-700 dark:text-violet-300">Gateway & Intelligence</span>
              {gatewayRuntime && (
                <span className="text-[10px] text-violet-500 dark:text-violet-400">
                  {gatewayRuntime.guardrail_context.active_rules} guardrails, {gatewayRuntime.rate_limit_context.routes_with_rpm_limits} RPM limits
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-1">
              {[
                { href: '/gateway', label: 'Gateway' },
                { href: '/provider-profiles', label: 'Providers' },
                { href: '/guardrails', label: 'Guardrails' },
                { href: '/tags', label: 'Tags' },
              ].map(l => (
                <Link key={l.label} href={l.href} className="text-[10px] font-semibold text-violet-600 hover:underline dark:text-violet-400">{l.label}</Link>
              ))}
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {[
              { l: 'Routes', v: `${gatewayPosture.gateway_context.active_routes}/${gatewayPosture.gateway_context.total_routes}` },
              { l: 'Models', v: `${gatewayPosture.gateway_context.distinct_models}` },
              { l: 'Policies', v: `${gatewayPosture.gateway_context.routing_policies}` },
              { l: 'Runs 30d', v: `${gatewayPosture.investigation_context.runs_30d}` },
              { l: 'Calls 30d', v: `${gatewayPosture.investigation_context.provider_calls_30d}` },
              { l: 'Tags', v: `${gatewayPosture.tag_context.active_tags}/${gatewayPosture.tag_context.tags}` },
            ].map(c => (
              <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-violet-200 bg-violet-50 px-2 py-0.5 text-[11px] dark:border-violet-800 dark:bg-violet-950/40">
                <span className="font-medium text-violet-500 dark:text-violet-400">{c.l}</span>
                <span className="font-bold text-violet-700 dark:text-violet-300">{c.v}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Budget control — compact chips */}
      {budgetControlPosture && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-3 dark:border-emerald-800/40 dark:bg-emerald-950/20">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <DollarSign className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">Budget Control</span>
            </div>
            <div className="flex gap-1.5">
              {[{ href: '/budgets', l: 'Budgets' }, { href: '/billing', l: 'Billing' }].map(x => (
                <Link key={x.l} href={x.href} className="text-[10px] font-semibold text-emerald-600 hover:underline dark:text-emerald-400">{x.l}</Link>
              ))}
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {[
              { l: 'Active', v: `${budgetControlPosture.budget_policy.active_budgets}` },
              { l: 'Breached', v: `${budgetControlPosture.budget_policy.breached_budgets}` },
              { l: 'At Risk', v: `${budgetControlPosture.budget_policy.at_risk_budgets}` },
              { l: 'Utilization', v: `${num(budgetControlPosture.budget_policy.avg_utilization_pct).toFixed(1)}%` },
            ].map(c => (
              <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] dark:border-emerald-800 dark:bg-emerald-950/40">
                <span className="font-medium text-emerald-500 dark:text-emerald-400">{c.l}</span>
                <span className="font-bold text-emerald-700 dark:text-emerald-300">{c.v}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Model Budget Utilization — compact */}
      {modelBudgets && modelBudgets.models.filter(m => m.budget_limit_usd !== null).length > 0 && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-3 dark:border-emerald-800/40 dark:bg-emerald-950/20">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <Wallet className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">Model Budgets</span>
              <div className="flex gap-1.5">
                {[
                  { l: 'Active', v: modelBudgets.active_model_budgets },
                  { l: 'Periods', v: modelBudgets.billing_periods },
                  { l: 'Chargeback', v: modelBudgets.chargeback_rules },
                ].map(c => (
                  <span key={c.l} className="inline-flex items-center gap-1 text-[10px]">
                    <span className="text-emerald-500 dark:text-emerald-400">{c.l}</span>
                    <span className="font-bold text-emerald-700 dark:text-emerald-300">{c.v}</span>
                  </span>
                ))}
              </div>
            </div>
            <Link href="/model-budgets" className="text-[10px] font-semibold text-emerald-600 hover:underline dark:text-emerald-400">Manage</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-y border-emerald-300 bg-emerald-50 dark:border-emerald-800/40 dark:bg-emerald-950/30">
                  {['Model', 'Spend', 'Reqs', 'Limit', 'Util', 'Action', ''].map(h => (
                    <th key={h} className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-emerald-600 dark:text-emerald-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-emerald-100 dark:divide-emerald-800/40">
                {modelBudgets.models.filter(m => m.budget_limit_usd !== null).map(m => {
                  const util = m.budget_limit_usd && m.budget_limit_usd > 0 ? (m.spend_30d / m.budget_limit_usd) * 100 : 0
                  return (
                    <tr key={m.model} className="hover:bg-emerald-50/40 dark:hover:bg-emerald-900/20">
                      <td className="px-3 py-1.5 font-semibold text-slate-800 dark:text-white">{m.model}</td>
                      <td className="px-3 py-1.5 font-mono">{money(m.spend_30d)}</td>
                      <td className="px-3 py-1.5 font-mono">{m.request_count.toLocaleString()}</td>
                      <td className="px-3 py-1.5 font-mono">{m.budget_limit_usd !== null ? money(m.budget_limit_usd) : '—'}</td>
                      <td className="px-3 py-1.5 font-mono font-semibold">
                        <span className={util > 100 ? 'text-red-600 dark:text-red-400' : util > 80 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}>
                          {percent(util)}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-slate-500">{m.budget_action ?? '—'}</td>
                      <td className="px-3 py-1.5">
                        <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${m.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                          {m.is_active ? 'active' : 'off'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Model Usage Table — compact */}
      <div className="rounded-xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-1.5 px-3 pt-3">
          <Cpu className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Model Usage</p>
        </div>
        {models.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-400">No model usage yet.</div>
        ) : (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-y border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                  {['Model', 'Provider', 'Reqs', 'Input', 'Output', 'Cost', 'Latency', 'Quality'].map(h => (
                    <th key={h} className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {models.map((model) => {
                  const latency = model.latencySamples > 0 ? model.latencyTotal / model.latencySamples : null
                  const explicitQuality = qualityScoreMap.get(model.model)
                  const fallbackQuality = model.requests > 0 ? (model.successes / model.requests) * 100 : 0
                  const quality = explicitQuality ?? fallbackQuality
                  const qualityLabel = explicitQuality !== null && explicitQuality !== undefined ? 'score' : 'proxy'
                  return (
                    <tr key={model.model} className="hover:bg-blue-50/40 dark:hover:bg-slate-800/40">
                      <td className="px-3 py-1.5 font-semibold text-slate-800 dark:text-white">{model.model}</td>
                      <td className="px-3 py-1.5 text-slate-500">{model.provider}</td>
                      <td className="px-3 py-1.5 font-mono">{model.requests.toLocaleString()}</td>
                      <td className="px-3 py-1.5 font-mono">{shortNumber(model.inputTokens)}</td>
                      <td className="px-3 py-1.5 font-mono">{shortNumber(model.outputTokens)}</td>
                      <td className="px-3 py-1.5 font-mono font-semibold">{money(model.cost)}</td>
                      <td className="px-3 py-1.5 font-mono">{formatLatency(latency)}</td>
                      <td className="px-3 py-1.5 font-mono font-semibold">
                        {percent(quality)}
                        <span className="ml-1 rounded-full bg-slate-100 px-1 py-px text-[9px] font-medium text-slate-400 dark:bg-slate-700">{qualityLabel}</span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Routing Decision Detail — compact */}
      <div className="rounded-xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-1.5 px-3 pt-3">
          <Route className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Routing Decisions</p>
        </div>
        {routes.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-400">No routing decisions yet.</div>
        ) : (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-y border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                  {['Route', 'Model', 'Why', 'Cost delta', 'Latency', 'Outcome'].map(h => (
                    <th key={h} className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {routes.map((route) => {
                  const avgCost = route.requests > 0 ? route.cost / route.requests : 0
                  const routeAvgLatency = route.latencySamples > 0 ? route.latencyTotal / route.latencySamples : null
                  const cheapestAvg = cheapestModel ? cheapestModel.cost / Math.max(cheapestModel.requests, 1) : 0
                  const fastestLatency = fastestModel && fastestModel.latencySamples > 0 ? fastestModel.latencyTotal / fastestModel.latencySamples : null
                  const costDelta = cheapestModel && cheapestModel.model !== route.model ? avgCost - cheapestAvg : 0
                  const latencyDelta = fastestLatency !== null && routeAvgLatency !== null ? routeAvgLatency - fastestLatency : null
                  const bestValueAlternative = bestValueByModel.get(route.model)
                  const routeQuality = qualityScoreMap.get(route.model) ?? (route.requests > 0 ? (route.successes / route.requests) * 100 : 0)
                  return (
                    <tr key={route.key} className="align-top hover:bg-blue-50/40 dark:hover:bg-slate-800/40">
                      <td className="px-3 py-1.5 font-semibold text-slate-800 dark:text-white">{route.route}</td>
                      <td className="px-3 py-1.5">
                        <span className="font-semibold text-slate-700 dark:text-slate-200">{route.model}</span>
                        <span className="ml-1 text-slate-400">{route.provider} / {route.requests}</span>
                      </td>
                      <td className="max-w-[200px] px-3 py-1.5 text-slate-500">{routeReason(route)}</td>
                      <td className="px-3 py-1.5 text-slate-500">
                        {cheapestModel && cheapestModel.model !== route.model
                          ? `${money(Math.max(costDelta, 0))} vs ${cheapestModel.model}`
                          : 'Lowest'}
                      </td>
                      <td className="px-3 py-1.5 text-slate-500">
                        {fastestModel && fastestModel.model !== route.model && latencyDelta !== null
                          ? `${formatLatency(Math.max(latencyDelta, 0))} vs ${fastestModel.model}`
                          : 'Fastest'}
                      </td>
                      <td className="px-3 py-1.5">
                        <span className="font-mono font-semibold text-slate-700 dark:text-slate-200">{percent(routeQuality)}</span>
                        {bestValueAlternative && (
                          <span className="ml-1 text-[10px] text-slate-400">val {Number(bestValueAlternative.value_score).toFixed(2)}</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
