import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { Activity, ArrowRight, Clock, Cpu, DollarSign, GitBranch, Network, Route, Sparkles, Table2, Tags, Wallet } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getBestValueModels, getBudgetControlObservePosture, getCostQuality, getInvestigationGatewayRuntimePosture, getModelBudgetUtilization, getModelUsageGatewayPosture, getRunFlow } from '@/lib/api'
import DashboardScopeBar, { getDashboardWindow } from '@/components/dashboard/DashboardScopeBar'
import {
  ModelQualityCostBars,
  RoutingDistribution,
  StackedResourceTimeline,
  type ModelTimelineDetail,
  type ModelTimelinePoint,
  type QualityCostPoint,
  type RoutingSlice,
} from '@/components/dashboard/ModelRoutingCharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MODEL_FAMILY_COLORS, classifyModel as classifyModelFamily } from '@/lib/modelColors'
import type { BestValueModel, RunFlowRecord } from '@/types/api'

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
  if (Math.abs(value) >= 1) return `$${value.toFixed(2)}`
  if (Math.abs(value) >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

function percent(value: number) {
  if (!Number.isFinite(value)) return '0%'
  return `${value.toFixed(0)}%`
}

function formatLatency(ms: number | null) {
  if (ms === null || !Number.isFinite(ms)) return 'n/a'
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
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
      inputTokens: 0,
      outputTokens: 0,
      cost: 0,
      cacheSavings: 0,
      latencyMs: null,
      outcomeRate: 0,
      latencyTotal: 0,
      latencySamples: 0,
      successes: 0,
      requests: 0,
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
          inputTokens: detail.inputTokens,
          outputTokens: detail.outputTokens,
          cost: detail.cost,
          cacheSavings: detail.cacheSavings,
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
      model: key,
      provider: item.provider || 'unknown',
      requests: 0,
      inputTokens: 0,
      outputTokens: 0,
      cachedTokens: 0,
      cost: 0,
      savings: 0,
      latencyTotal: 0,
      latencySamples: 0,
      successes: 0,
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
      key,
      route,
      model,
      provider: item.provider || 'unknown',
      requests: 0,
      cost: 0,
      savings: 0,
      latencyTotal: 0,
      latencySamples: 0,
      successes: 0,
      cached: 0,
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
  if (route.cached > 0) return 'Cache lane reduced repeated model work for this route.'
  if (text.includes('local') || text.includes('llama') || text.includes('ollama')) return 'Local model lane likely optimized for privacy or lower unit cost.'
  if (text.includes('fallback')) return 'Fallback route handled traffic when the preferred provider was not used.'
  if (text.includes('budget') || text.includes('cost')) return 'Cost-aware policy selected this route under budget guardrails.'
  return 'Configured gateway routing selected this provider/model for the request profile.'
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
    getCostQuality(session.apiKey, {
      score_name: 'quality',
      from: win.from,
      to: win.to,
    }).catch(() => ({ items: [] })),
    getBestValueModels(session.apiKey, {
      score_name: 'quality',
      from: win.from,
      to: win.to,
    }).catch(() => ({ items: [] })),
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
  const qualityScoreMap = new Map(
    costQuality.items.map((item) => [item.model, parseScore(item.avg_score)])
  )
  const bestValueByModel = new Map<string, BestValueModel>(
    bestValue.items.map((item) => [item.model, item])
  )
  const qualitySamples = costQuality.items.filter((item) => item.avg_score !== null)
  const avgQualityScore =
    qualitySamples.length > 0
      ? qualitySamples.reduce((sum, item) => sum + (parseScore(item.avg_score) ?? 0), 0) / qualitySamples.length
      : null

  const cheapestModel = models
    .filter((model) => model.requests > 0)
    .sort((a, b) => a.cost / a.requests - b.cost / b.requests)[0]
  const fastestModel = models
    .filter((model) => model.latencySamples > 0)
    .sort((a, b) => a.latencyTotal / a.latencySamples - b.latencyTotal / b.latencySamples)[0]

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950">Model Usage</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Explain which models are used, why routes select them, and how cost, latency, cache, and outcomes compare.
          </p>
        </div>
        <Link
          href={`/request-flow?scope=${selectedScope}&mode=request-route-provider-outcome&metric=cost`}
          className="inline-flex items-center gap-1 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700 transition-colors hover:bg-blue-100"
        >
          Open request flow <ArrowRight className="h-3.5 w-3.5" />
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
              href={`/model-usage?scope=${scope}&range=${win.range}`}
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
        context={`${requests.toLocaleString()} requests analyzed`}
        activeRange={win.range}
        basePath={`/model-usage?scope=${selectedScope}`}
        dimensions={['Model', 'Provider', 'Route', 'Cache', 'Tokens', 'Latency', 'Outcome']}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { title: 'Requests', value: requests.toLocaleString(), sub: `${items.length.toLocaleString()} sampled`, icon: Activity },
          { title: 'Model spend', value: money(totalCost), sub: `${money(totalSavings)} saved`, icon: Cpu },
          { title: 'Avg latency', value: formatLatency(avgLatency), sub: 'Across captured samples', icon: Clock },
          {
            title: 'Avg quality',
            value: avgQualityScore !== null ? percent(avgQualityScore) : 'n/a',
            sub: avgQualityScore !== null ? `${qualitySamples.length} models with score data` : 'No explicit quality scores captured yet in this window',
            icon: Sparkles,
          },
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

      {gatewayPosture && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50/60 p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-violet-700">Gateway & Intelligence Context</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950">
                {gatewayPosture.gateway_context.active_routes} active routes across {gatewayPosture.gateway_context.distinct_models} models
                {gatewayRuntime && `. ${gatewayRuntime.guardrail_context.active_rules} guardrail rules, ${gatewayRuntime.rate_limit_context.routes_with_rpm_limits} RPM-limited routes.`}
              </h2>
            </div>
            <Network className="h-5 w-5 shrink-0 text-violet-500" />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-white/80 p-3 shadow-sm">
              <p className="text-xs font-medium text-slate-500">Routes</p>
              <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{gatewayPosture.gateway_context.active_routes}</p>
              <p className="mt-1 text-xs text-slate-500">{gatewayPosture.gateway_context.total_routes} total</p>
            </div>
            <div className="rounded-lg bg-white/80 p-3 shadow-sm">
              <p className="text-xs font-medium text-slate-500">Models</p>
              <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{gatewayPosture.gateway_context.distinct_models}</p>
              <p className="mt-1 text-xs text-slate-500">{gatewayPosture.gateway_context.routing_policies} policies</p>
            </div>
            <div className="rounded-lg bg-white/80 p-3 shadow-sm">
              <p className="text-xs font-medium text-slate-500">Runs 30d</p>
              <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{gatewayPosture.investigation_context.runs_30d}</p>
              <p className="mt-1 text-xs text-slate-500">{gatewayPosture.investigation_context.provider_calls_30d} calls</p>
            </div>
            <div className="rounded-lg bg-white/80 p-3 shadow-sm">
              <p className="text-xs font-medium text-slate-500">Tags</p>
              <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{gatewayPosture.tag_context.active_tags}</p>
              <p className="mt-1 text-xs text-slate-500">{gatewayPosture.tag_context.tags} total</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/gateway" className="rounded-full bg-violet-100 px-3 py-1 font-medium text-violet-700 hover:bg-violet-200 transition-colors">Model Gateway</Link>
            <Link href="/provider-profiles" className="rounded-full bg-violet-100 px-3 py-1 font-medium text-violet-700 hover:bg-violet-200 transition-colors">Provider Profiles</Link>
            <Link href="/guardrails" className="rounded-full bg-violet-100 px-3 py-1 font-medium text-violet-700 hover:bg-violet-200 transition-colors">Guardrails</Link>
            <Link href="/rate-limits" className="rounded-full bg-violet-100 px-3 py-1 font-medium text-violet-700 hover:bg-violet-200 transition-colors">Rate Limits</Link>
            <Link href="/runs" className="rounded-full bg-violet-100 px-3 py-1 font-medium text-violet-700 hover:bg-violet-200 transition-colors">Runs</Link>
            <Link href="/request-flow" className="rounded-full bg-violet-100 px-3 py-1 font-medium text-violet-700 hover:bg-violet-200 transition-colors">Request Flow</Link>
            <Link href="/request-explorer" className="rounded-full bg-violet-100 px-3 py-1 font-medium text-violet-700 hover:bg-violet-200 transition-colors">Request Explorer</Link>
            <Link href="/tags" className="rounded-full bg-violet-100 px-3 py-1 font-medium text-violet-700 hover:bg-violet-200 transition-colors">Tags</Link>
            <Link href="/monitoring/telemetry" className="rounded-full bg-blue-100 px-3 py-1 font-medium text-blue-700 hover:bg-blue-200 transition-colors dark:bg-blue-900/40 dark:text-blue-300 dark:hover:bg-blue-800/50">Telemetry</Link>
          </div>
        </div>
      )}

      {budgetControlPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">Budget Control — Observe Posture</p>
          </div>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetControlPosture.budget_policy.active_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
              <p className={`mt-1 text-lg font-semibold ${budgetControlPosture.budget_policy.breached_budgets > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetControlPosture.budget_policy.breached_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">At Risk</p>
              <p className={`mt-1 text-lg font-semibold ${budgetControlPosture.budget_policy.at_risk_budgets > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-900 dark:text-white'}`}>{budgetControlPosture.budget_policy.at_risk_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Avg Utilization</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">{budgetControlPosture.budget_policy.avg_utilization_pct.toFixed(1)}%</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?tab=overrides" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Overrides</Link>
            <Link href="/budgets?tab=notifications" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Notifications</Link>
            <Link href="/billing" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Billing</Link>
          </div>
        </div>
      )}

      {modelBudgets && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-emerald-700">FinOps Model Budget Utilization</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950">
                {modelBudgets.active_model_budgets} active model budgets
              </h2>
            </div>
            <Link href="/model-budgets" className="text-xs font-semibold text-emerald-700 hover:underline">Manage model budgets</Link>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Model Budgets</p>
                  <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{modelBudgets.active_model_budgets}</p>
                  <p className="mt-1 text-xs text-slate-500">{modelBudgets.total_model_budgets} total</p>
                </div>
                <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700"><Wallet className="h-5 w-5" /></div>
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Billing Periods</p>
                  <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{modelBudgets.billing_periods}</p>
                  <p className="mt-1 text-xs text-slate-500">{modelBudgets.open_billing_periods} open</p>
                </div>
                <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700"><DollarSign className="h-5 w-5" /></div>
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Chargeback Rules</p>
                  <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{modelBudgets.chargeback_rules}</p>
                  <p className="mt-1 text-xs text-slate-500">attribution rules</p>
                </div>
                <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700"><Activity className="h-5 w-5" /></div>
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Models with Budgets</p>
                  <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">
                    {modelBudgets.models.filter(m => m.budget_limit_usd !== null).length}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{modelBudgets.models.length} total tracked</p>
                </div>
                <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700"><Cpu className="h-5 w-5" /></div>
              </div>
            </div>
          </div>
          {modelBudgets.models.filter(m => m.budget_limit_usd !== null).length > 0 && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-y border-emerald-200 bg-emerald-50/80">
                    {['Model', 'Spend (30d)', 'Requests', 'Budget Limit', 'Utilization', 'Action', 'Status'].map(h => (
                      <th key={h} className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-[0.12em] text-emerald-700">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-100">
                  {modelBudgets.models.filter(m => m.budget_limit_usd !== null).map(m => {
                    const util = m.budget_limit_usd && m.budget_limit_usd > 0 ? (m.spend_30d / m.budget_limit_usd) * 100 : 0
                    return (
                      <tr key={m.model} className="hover:bg-emerald-50/40">
                        <td className="px-4 py-2 font-semibold text-slate-950">{m.model}</td>
                        <td className="px-4 py-2 font-mono text-xs font-semibold">{money(m.spend_30d)}</td>
                        <td className="px-4 py-2 font-mono text-xs">{m.request_count.toLocaleString()}</td>
                        <td className="px-4 py-2 font-mono text-xs">{m.budget_limit_usd !== null ? money(m.budget_limit_usd) : '—'}</td>
                        <td className="px-4 py-2 font-mono text-xs font-semibold">
                          <span className={util > 100 ? 'text-red-600' : util > 80 ? 'text-amber-600' : 'text-emerald-600'}>
                            {percent(util)}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-xs text-slate-500">{m.budget_action ?? '—'}</td>
                        <td className="px-4 py-2">
                          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${m.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                            {m.is_active ? 'active' : 'inactive'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/model-budgets" className="text-xs text-emerald-700 hover:underline">Model Budgets</Link>
            <Link href="/budgets" className="text-xs text-emerald-700 hover:underline">Budgets</Link>
            <Link href="/budgets?view=detail" className="text-xs text-emerald-700 hover:underline">Budget Detail</Link>
            <Link href="/billing" className="text-xs text-emerald-700 hover:underline">Billing Periods</Link>
            <Link href="/billing?view=detail" className="text-xs text-emerald-700 hover:underline">Billing Detail</Link>
            <Link href="/chargeback" className="text-xs text-emerald-700 hover:underline">Chargeback</Link>
          </div>
        </div>
      )}

      <Card className="border-slate-200 bg-white/90 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            <GitBranch className="h-4 w-4 text-blue-600" /> 100% Resource Usage Timeline
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Daily model mix by request count. Hover a segment to see tokens, cost, cache savings, latency, and outcome rate.
          </p>
        </CardHeader>
        <CardContent>
          <StackedResourceTimeline data={timeline.data} keys={timeline.keys} colors={modelColors} details={timeline.details} />
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="border-slate-200 bg-white/90 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Route className="h-4 w-4 text-blue-600" /> Routing Distribution
            </CardTitle>
            <p className="text-xs text-muted-foreground">Claude, GPT, Gemini, local, cached, failed/rejected, and other route share.</p>
          </CardHeader>
          <CardContent>
            <RoutingDistribution data={routingSlices} />
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white/90 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Table2 className="h-4 w-4 text-blue-600" /> Cost, Latency, Quality
            </CardTitle>
            <p className="text-xs text-muted-foreground">Bars show cost. Quality uses explicit evaluation scores when present, then falls back to outcome success rate.</p>
          </CardHeader>
          <CardContent>
            <ModelQualityCostBars data={qualityCost} />
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden border-slate-200 bg-white/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Model Usage Table</CardTitle>
          <p className="text-xs text-muted-foreground">Request, token, cost, latency, and explicit quality score by model, with outcome fallback where no scores exist.</p>
        </CardHeader>
        <CardContent className="p-0">
          {models.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-muted-foreground">No model usage yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-y border-slate-200 bg-slate-50/80">
                  {['Model', 'Provider', 'Requests', 'Input', 'Output', 'Cost', 'Latency', 'Quality score'].map((heading) => (
                    <th key={heading} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {models.map((model) => {
                  const latency = model.latencySamples > 0 ? model.latencyTotal / model.latencySamples : null
                  const explicitQuality = qualityScoreMap.get(model.model)
                  const fallbackQuality = model.requests > 0 ? (model.successes / model.requests) * 100 : 0
                  const quality = explicitQuality ?? fallbackQuality
                  const qualityLabel = explicitQuality !== null && explicitQuality !== undefined ? 'score' : 'proxy'
                  return (
                    <tr key={model.model} className="hover:bg-blue-50/40">
                      <td className="px-5 py-3 font-semibold text-slate-950">{model.model}</td>
                      <td className="px-5 py-3 text-slate-500">{model.provider}</td>
                      <td className="px-5 py-3 font-mono text-xs">{model.requests.toLocaleString()}</td>
                      <td className="px-5 py-3 font-mono text-xs">{shortNumber(model.inputTokens)}</td>
                      <td className="px-5 py-3 font-mono text-xs">{shortNumber(model.outputTokens)}</td>
                      <td className="px-5 py-3 font-mono text-xs font-semibold">{money(model.cost)}</td>
                      <td className="px-5 py-3 font-mono text-xs">{formatLatency(latency)}</td>
                      <td className="px-5 py-3 font-mono text-xs font-semibold">
                        {percent(quality)}
                        <span className="ml-2 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500">
                          {qualityLabel}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-slate-200 bg-white/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Routing Decision Detail</CardTitle>
          <p className="text-xs text-muted-foreground">Explains why routes selected models and what lower-cost, lower-latency, or better value alternatives exist in current telemetry.</p>
        </CardHeader>
        <CardContent className="p-0">
          {routes.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-muted-foreground">No routing decisions yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-y border-slate-200 bg-slate-50/80">
                  {['Route', 'Selected model', 'Why selected', 'Cost delta', 'Latency tradeoff', 'Outcome'].map((heading) => (
                    <th key={heading} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {routes.map((route) => {
                  const avgCost = route.requests > 0 ? route.cost / route.requests : 0
                  const avgLatency = route.latencySamples > 0 ? route.latencyTotal / route.latencySamples : null
                  const cheapestAvg = cheapestModel ? cheapestModel.cost / Math.max(cheapestModel.requests, 1) : 0
                  const fastestLatency = fastestModel && fastestModel.latencySamples > 0 ? fastestModel.latencyTotal / fastestModel.latencySamples : null
                  const costDelta = cheapestModel && cheapestModel.model !== route.model ? avgCost - cheapestAvg : 0
                  const latencyDelta = fastestLatency !== null && avgLatency !== null ? avgLatency - fastestLatency : null
                  const bestValueAlternative = bestValueByModel.get(route.model)
                  const routeQuality = qualityScoreMap.get(route.model) ?? (route.requests > 0 ? (route.successes / route.requests) * 100 : 0)
                  return (
                    <tr key={route.key} className="align-top hover:bg-blue-50/40">
                      <td className="px-5 py-3 font-semibold text-slate-950">{route.route}</td>
                      <td className="px-5 py-3">
                        <div className="font-semibold text-slate-800">{route.model}</div>
                        <div className="text-xs text-slate-500">{route.provider} / {route.requests.toLocaleString()} requests</div>
                      </td>
                      <td className="max-w-md px-5 py-3 text-slate-600">{routeReason(route)}</td>
                      <td className="px-5 py-3 text-xs text-slate-600">
                        {cheapestModel && cheapestModel.model !== route.model
                          ? `${money(Math.max(costDelta, 0))} vs ${cheapestModel.model}`
                          : 'Already lowest observed cost'}
                      </td>
                      <td className="px-5 py-3 text-xs text-slate-600">
                        {fastestModel && fastestModel.model !== route.model && latencyDelta !== null
                          ? `${formatLatency(Math.max(latencyDelta, 0))} vs ${fastestModel.model}`
                          : 'Already fastest observed lane'}
                      </td>
                      <td className="px-5 py-3 text-xs text-slate-600">
                        <div className="font-mono font-semibold">{percent(routeQuality)}</div>
                        {bestValueAlternative ? (
                          <div className="mt-1 text-[11px] text-slate-500">
                            value score {Number(bestValueAlternative.value_score).toFixed(2)}
                          </div>
                        ) : (
                          <div className="mt-1 text-[11px] text-slate-400">no quality sample yet</div>
                        )}
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
  )
}
