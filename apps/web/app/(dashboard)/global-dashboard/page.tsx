import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import type { ReactNode } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  Download,
  Landmark,
  LayoutGrid,
  PiggyBank,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  Users,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getRunFlow, listPlatformOrganizations } from '@/lib/api'
import DashboardScopeBar, { getDashboardWindow } from '@/components/dashboard/DashboardScopeBar'
import {
  ExecutiveSavingsBars,
  ExecutiveTrendChart,
  ExecutiveWaterfallChart,
  type ExecutiveSavingsPoint,
  type ExecutiveTrendPoint,
  type ExecutiveWaterfallPoint,
} from '@/components/dashboard/ExecutiveCharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { RunFlowRecord, TenantResponse } from '@/types/api'

type Driver = {
  name: string
  spend: number
  saved: number
  requests: number
  optimization: number
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

function parseMoney(value: string | null | undefined) {
  const parsed = Number.parseFloat(value ?? '0')
  return Number.isFinite(parsed) ? parsed : 0
}

function statusClass(status: string) {
  if (status === 'active') return 'bg-emerald-100 text-emerald-700'
  if (status === 'suspended') return 'bg-amber-100 text-amber-700'
  return 'bg-slate-100 text-slate-600'
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

function StatCard({
  title,
  value,
  sub,
  icon,
  tone = 'blue',
  titleHelp,
}: {
  title: string
  value: string
  sub: string
  icon: ReactNode
  tone?: 'blue' | 'emerald' | 'amber' | 'slate' | 'violet'
  titleHelp: string
}) {
  const tones = {
    blue: 'border-blue-200 bg-blue-50/75 text-blue-700',
    emerald: 'border-emerald-200 bg-emerald-50/75 text-emerald-700',
    amber: 'border-amber-200 bg-amber-50/75 text-amber-700',
    slate: 'border-slate-200 bg-slate-50/85 text-slate-700',
    violet: 'border-violet-200 bg-violet-50/75 text-violet-700',
  }

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${tones[tone]}`} title={titleHelp}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-75">{title}</p>
          <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] tabular-nums text-slate-950">
            {value}
          </p>
          <p className="mt-1 text-xs text-slate-600">{sub}</p>
        </div>
        <div className="rounded-xl bg-white/75 p-2.5 shadow-sm">{icon}</div>
      </div>
    </div>
  )
}

function bucketDrivers(items: RunFlowRecord[], key: 'workspace_name' | 'team' | 'application'): Driver[] {
  const map = new Map<string, Driver>()
  for (const item of items) {
    const label = item[key] || 'Unassigned'
    const existing = map.get(label) ?? { name: label, spend: 0, saved: 0, requests: 0, optimization: 0 }
    existing.spend += parseMoney(item.total_cost_usd)
    existing.saved += parseMoney(item.savings_usd)
    existing.requests += 1
    map.set(label, existing)
  }
  return Array.from(map.values())
    .map((driver) => ({
      ...driver,
      optimization: driver.spend + driver.saved > 0 ? (driver.saved / (driver.spend + driver.saved)) * 100 : 0,
    }))
    .sort((a, b) => b.spend - a.spend)
    .slice(0, 8)
}

function buildTrend(items: RunFlowRecord[]): ExecutiveTrendPoint[] {
  const buckets = new Map<string, { actual: number; savings: number }>()
  for (const item of items) {
    const date = new Date(item.started_at)
    if (Number.isNaN(date.getTime())) continue
    const key = date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    const bucket = buckets.get(key) ?? { actual: 0, savings: 0 }
    bucket.actual += parseMoney(item.total_cost_usd)
    bucket.savings += parseMoney(item.savings_usd)
    buckets.set(key, bucket)
  }
  return Array.from(buckets.entries()).map(([period, bucket]) => ({
    period,
    projected: bucket.actual + bucket.savings,
    actual: bucket.actual,
    optimized: Math.max(bucket.actual - bucket.savings, 0),
  }))
}

function estimateSavings(items: RunFlowRecord[]) {
  const cache = items.reduce((sum, item) => sum + (item.cached_input_tokens > 0 ? parseMoney(item.savings_usd) : 0), 0)
  const local = items.reduce((sum, item) => {
    const model = (item.primary_model ?? '').toLowerCase()
    if (model.includes('llama') || model.includes('local') || model.includes('ollama')) {
      return sum + parseMoney(item.savings_usd)
    }
    return sum
  }, 0)
  const total = items.reduce((sum, item) => sum + parseMoney(item.savings_usd), 0)
  const remaining = Math.max(total - cache - local, 0)
  return {
    cache,
    local,
    routing: remaining * 0.55,
    promptCompression: remaining * 0.30,
    toolOptimization: remaining * 0.15,
    total,
  }
}

function csvHref(drivers: Driver[]) {
  const rows = [
    ['Workspace/Team', 'Spend', 'Saved', 'Requests', 'Optimization %'],
    ...drivers.map((driver) => [
      driver.name,
      driver.spend.toFixed(6),
      driver.saved.toFixed(6),
      String(driver.requests),
      driver.optimization.toFixed(2),
    ]),
  ]
  const csv = rows.map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(',')).join('\n')
  return `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`
}

export default async function GlobalDashboardPage({
  searchParams,
}: {
  searchParams?: { range?: string }
}) {
  const session = await getServerSession(authOptions)
  const s = session as Record<string, unknown> | null
  if (!s?.isPlatformAdmin) redirect('/dashboard')

  const win = getDashboardWindow(searchParams?.range ?? '30d')
  const [orgs, flow] = await Promise.all([
    listPlatformOrganizations(session!.apiKey),
    getRunFlow(session!.apiKey, {
      scope: 'platform',
      mode: 'team-app-agent-model-cost',
      metric: 'cost',
      limit: 1000,
      from: win.from,
      to: win.to,
    }),
  ])

  const items = flow.items
  const spend = items.reduce((sum, item) => sum + parseMoney(item.total_cost_usd), 0)
  const requests = flow.total_runs || items.length
  const savings = estimateSavings(items)
  const originalSpend = spend + savings.total
  const roi = spend > 0 ? savings.total / spend : 0
  const latencySamples = items.map((item) => item.latency_ms).filter((value): value is number => value !== null)
  const avgLatency = latencySamples.length > 0
    ? latencySamples.reduce((sum, value) => sum + value, 0) / latencySamples.length
    : null
  const cacheHits = items.filter((item) => item.cached_input_tokens > 0).length
  const cacheHitRate = items.length > 0 ? (cacheHits / items.length) * 100 : 0
  const totalInput = items.reduce((sum, item) => sum + item.total_input_tokens, 0)
  const cachedInput = items.reduce((sum, item) => sum + item.cached_input_tokens, 0)
  const tokenReduction = totalInput + cachedInput > 0 ? (cachedInput / (totalInput + cachedInput)) * 100 : 0
  const activeOrgs = orgs.filter((org) => org.status === 'active')
  const suspendedOrgs = orgs.filter((org) => org.status === 'suspended')
  const archivedOrgs = orgs.filter((org) => org.status === 'archived')
  const workspaceCount = orgs.reduce((sum, org) => sum + org.workspace_count, 0)
  const memberCount = orgs.reduce((sum, org) => sum + org.member_count, 0)
  const atRiskCount = suspendedOrgs.length + archivedOrgs.length
  const drivers = bucketDrivers(items, 'workspace_name')
  const trend = buildTrend(items)
  const waterfall: ExecutiveWaterfallPoint[] = [
    { name: 'Original', value: originalSpend, kind: 'start' },
    { name: 'Cache', value: -savings.cache, kind: 'saving' },
    { name: 'Routing', value: -savings.routing, kind: 'saving' },
    { name: 'Prompt', value: -savings.promptCompression, kind: 'saving' },
    { name: 'Local', value: -savings.local, kind: 'saving' },
    { name: 'Final', value: spend, kind: 'end' },
  ]
  const savingsBars: ExecutiveSavingsPoint[] = [
    { name: 'Cache hits', value: savings.cache, color: '#2563eb' },
    { name: 'Smart model routing', value: savings.routing, color: '#7c3aed' },
    { name: 'Prompt compression', value: savings.promptCompression, color: '#f59e0b' },
    { name: 'Local models', value: savings.local, color: '#059669' },
    { name: 'Tool optimization', value: savings.toolOptimization, color: '#0f766e' },
  ]
  const dateStr = new Date().toLocaleDateString([], {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-[11px] font-semibold text-blue-700">
            Executive view
          </span>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-[-0.05em]">Global Dashboard</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {dateStr} - {win.label} - Platform AI spend, savings, usage, and health
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={csvHref(drivers)}
            download={`runledger-executive-${win.range}.csv`}
            className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50"
          >
            <Download className="h-3.5 w-3.5" /> Export CSV
          </a>
          <Link
            href="/ledger"
            className="inline-flex items-center gap-1 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700 transition-colors hover:bg-blue-100"
          >
            Snapshot ledger <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      <DashboardScopeBar
        scope="Platform"
        context="All organizations"
        activeRange={win.range}
        basePath="/global-dashboard"
        dimensions={['Platform', 'Time range', 'Organization', 'Workspace', 'Team', 'Application', 'Model', 'Outcome']}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="AI Spend"
          value={money(spend)}
          sub={`${win.label.toLowerCase()} actual spend`}
          icon={<DollarSign className="h-5 w-5" />}
          titleHelp="Sum of total_cost_usd across platform flow records in the selected window."
        />
        <StatCard
          title="Savings"
          value={money(savings.total)}
          sub="Captured plus estimated optimization savings"
          icon={<PiggyBank className="h-5 w-5" />}
          tone="emerald"
          titleHelp="Sum of savings_usd from flow records. Attribution categories are estimated until Phase 7 finance-grade savings attribution lands."
        />
        <StatCard
          title="ROI"
          value={`${roi.toFixed(1)}x`}
          sub="Savings divided by current spend"
          icon={<TrendingDown className="h-5 w-5" />}
          tone="violet"
          titleHelp="Calculated as savings_usd divided by total_cost_usd for the selected window."
        />
        <StatCard
          title="Requests"
          value={requests.toLocaleString()}
          sub={`${items.length.toLocaleString()} sampled for drivers`}
          icon={<Activity className="h-5 w-5" />}
          tone="slate"
          titleHelp="Total run count from the platform flow API. Driver charts use the sampled records returned by the API."
        />
        <StatCard
          title="Avg Latency"
          value={formatLatency(avgLatency)}
          sub={`${latencySamples.length.toLocaleString()} latency samples`}
          icon={<Clock className="h-5 w-5" />}
          tone="blue"
          titleHelp="Average of latency_ms across sampled flow records that captured latency."
        />
        <StatCard
          title="Cache Hit Rate"
          value={percent(cacheHitRate)}
          sub={`${cacheHits.toLocaleString()} cached requests`}
          icon={<Cpu className="h-5 w-5" />}
          tone="emerald"
          titleHelp="Percentage of sampled requests with cached_input_tokens greater than zero."
        />
        <StatCard
          title="Token Reduction"
          value={percent(tokenReduction)}
          sub={`${cachedInput.toLocaleString()} cached input tokens`}
          icon={<Sparkles className="h-5 w-5" />}
          tone="amber"
          titleHelp="Cached input tokens divided by input plus cached input tokens for sampled records."
        />
        <StatCard
          title="Org Health"
          value={`${activeOrgs.length}/${orgs.length}`}
          sub={`${atRiskCount} suspended or archived`}
          icon={<ShieldCheck className="h-5 w-5" />}
          tone={atRiskCount > 0 ? 'amber' : 'emerald'}
          titleHelp="Active organizations divided by total organizations from the platform lifecycle API."
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.35fr_0.85fr]">
        <Card className="border-slate-200/80 bg-white/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Spend Trend</CardTitle>
            <p className="text-xs text-muted-foreground">Projected original spend, actual spend, and optimized spend from sampled platform traffic.</p>
          </CardHeader>
          <CardContent>
            <ExecutiveTrendChart data={trend} />
          </CardContent>
        </Card>

        <Card className="border-slate-200/80 bg-white/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Savings Attribution</CardTitle>
            <p className="text-xs text-muted-foreground">Attribution is directional until Phase 7 adds finance-grade realized savings categories.</p>
          </CardHeader>
          <CardContent>
            <ExecutiveSavingsBars data={savingsBars} />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="border-slate-200/80 bg-white/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Cost Waterfall</CardTitle>
            <p className="text-xs text-muted-foreground">From original spend to optimized final spend.</p>
          </CardHeader>
          <CardContent>
            <ExecutiveWaterfallChart data={waterfall} />
          </CardContent>
        </Card>

        <Card className="overflow-hidden border-slate-200/80 bg-white/90 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-semibold">Top Workspaces By Spend</CardTitle>
              <p className="mt-0.5 text-xs text-muted-foreground">Spend, savings, requests, and optimization rate.</p>
            </div>
            <Link href="/request-flow?scope=platform&mode=team-app-agent-model-cost&metric=cost" className="text-xs font-semibold text-blue-700 hover:underline">
              Flow detail →
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {drivers.length === 0 ? (
              <div className="px-5 py-12 text-center text-sm text-muted-foreground">No workspace spend yet.</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-y border-slate-200 bg-slate-50/80">
                    <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Workspace</th>
                    <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Spend</th>
                    <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Saved</th>
                    <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Requests</th>
                    <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Optimization</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {drivers.map((driver) => (
                    <tr key={driver.name} className="transition-colors hover:bg-blue-50/40">
                      <td className="px-5 py-3 font-semibold text-slate-950">{driver.name}</td>
                      <td className="px-5 py-3 text-right font-mono text-xs font-semibold">{money(driver.spend)}</td>
                      <td className="px-5 py-3 text-right font-mono text-xs font-semibold text-emerald-700">{money(driver.saved)}</td>
                      <td className="px-5 py-3 text-right font-mono text-xs">{driver.requests.toLocaleString()}</td>
                      <td className="px-5 py-3 text-right font-mono text-xs font-semibold">{percent(driver.optimization)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden border-slate-200/80 bg-white/90 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base font-semibold">Platform Lifecycle Context</CardTitle>
            <p className="mt-0.5 text-xs text-muted-foreground">Organization, workspace, and member footprint behind the executive metrics.</p>
          </div>
          <Link href="/organizations" className="text-xs font-semibold text-blue-700 hover:underline">Manage organizations →</Link>
        </CardHeader>
        <CardContent className="p-0">
          <div className="grid gap-3 p-5 md:grid-cols-4">
            {[
              { label: 'Organizations', value: orgs.length.toLocaleString(), icon: Landmark },
              { label: 'Workspaces', value: workspaceCount.toLocaleString(), icon: LayoutGrid },
              { label: 'Members', value: memberCount.toLocaleString(), icon: Users },
              { label: 'Lifecycle Risk', value: atRiskCount.toLocaleString(), icon: AlertTriangle },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.16em]">{label}</span>
                  <Icon className="h-4 w-4" />
                </div>
                <p className="mt-3 font-display text-2xl font-semibold tracking-[-0.04em] text-slate-950">{value}</p>
              </div>
            ))}
          </div>
          {orgs.length > 0 && (
            <table className="w-full border-t border-slate-200 text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80">
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Organization</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Status</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Workspaces</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Members</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {orgs.slice(0, 8).map((org: TenantResponse) => (
                  <tr key={org.id} className="transition-colors hover:bg-blue-50/40">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-100 text-blue-700">
                          <Building2 className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="font-semibold text-slate-950">{org.name}</div>
                          <div className="text-xs text-muted-foreground">{org.plan}{org.is_default ? ' - default org' : ''}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusClass(org.status)}`}>
                        {org.status === 'active' && <CheckCircle2 className="h-3 w-3" />}
                        {org.status.charAt(0).toUpperCase() + org.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-xs font-semibold">{org.workspace_count}</td>
                    <td className="px-5 py-3 text-right font-mono text-xs font-semibold">{org.member_count}</td>
                    <td className="px-5 py-3 text-right text-xs text-muted-foreground">{formatDate(org.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
