import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { Activity, ArrowRight, Clock, Cpu, GitBranch, Route, Sparkles, Table2 } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getRunFlow } from '@/lib/api'
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
import type { RunFlowRecord } from '@/types/api'

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

const modelColors: Record<string, string> = {
  'GPT-5': '#2563eb',
  Claude: '#7c3aed',
  Gemini: '#0891b2',
  'Local Llama': '#059669',
  DeepSeek: '#ea580c',
  'Cached Responses': '#16a34a',
  'Rejected Requests': '#dc2626',
  Other: '#64748b',
}

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
  const haystack = `${item.primary_model ?? ''} ${item.provider ?? ''}`.toLowerCase()
  if (!item.success || item.status === 'rejected' || item.outcome === 'rejected') return 'Rejected Requests'
  if (item.cached_input_tokens > 0) return 'Cached Responses'
  if (haystack.includes('gpt') || haystack.includes('openai')) return 'GPT-5'
  if (haystack.includes('claude') || haystack.includes('anthropic')) return 'Claude'
  if (haystack.includes('gemini') || haystack.includes('google')) return 'Gemini'
  if (haystack.includes('llama') || haystack.includes('ollama') || haystack.includes('local')) return 'Local Llama'
  if (haystack.includes('deepseek')) return 'DeepSeek'
  return 'Other'
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
    quality: model.requests > 0 ? (model.successes / model.requests) * 100 : 0,
  }))

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
          <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-[11px] font-semibold text-blue-700">
            Phase 6
          </span>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950">Model Usage</h1>
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
          { title: 'Cache hit rate', value: percent(cacheHitRate), sub: 'Cached input token usage', icon: Sparkles },
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
              <Table2 className="h-4 w-4 text-blue-600" /> Cost, Latency, Quality Proxy
            </CardTitle>
            <p className="text-xs text-muted-foreground">Bars show cost. Table below includes latency and success-rate quality proxy.</p>
          </CardHeader>
          <CardContent>
            <ModelQualityCostBars data={qualityCost} />
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden border-slate-200 bg-white/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Model Usage Table</CardTitle>
          <p className="text-xs text-muted-foreground">Request, token, cost, latency, and quality proxy by model.</p>
        </CardHeader>
        <CardContent className="p-0">
          {models.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-muted-foreground">No model usage yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-y border-slate-200 bg-slate-50/80">
                  {['Model', 'Provider', 'Requests', 'Input', 'Output', 'Cost', 'Latency', 'Quality proxy'].map((heading) => (
                    <th key={heading} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {models.map((model) => {
                  const latency = model.latencySamples > 0 ? model.latencyTotal / model.latencySamples : null
                  const quality = model.requests > 0 ? (model.successes / model.requests) * 100 : 0
                  return (
                    <tr key={model.model} className="hover:bg-blue-50/40">
                      <td className="px-5 py-3 font-semibold text-slate-950">{model.model}</td>
                      <td className="px-5 py-3 text-slate-500">{model.provider}</td>
                      <td className="px-5 py-3 font-mono text-xs">{model.requests.toLocaleString()}</td>
                      <td className="px-5 py-3 font-mono text-xs">{shortNumber(model.inputTokens)}</td>
                      <td className="px-5 py-3 font-mono text-xs">{shortNumber(model.outputTokens)}</td>
                      <td className="px-5 py-3 font-mono text-xs font-semibold">{money(model.cost)}</td>
                      <td className="px-5 py-3 font-mono text-xs">{formatLatency(latency)}</td>
                      <td className="px-5 py-3 font-mono text-xs font-semibold">{percent(quality)}</td>
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
          <p className="text-xs text-muted-foreground">Explains why routes selected models and what lower-cost or lower-latency alternatives exist in current telemetry.</p>
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
                      <td className="px-5 py-3 font-mono text-xs font-semibold">{percent(route.requests > 0 ? (route.successes / route.requests) * 100 : 0)}</td>
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
