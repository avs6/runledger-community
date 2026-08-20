import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import {
  Activity,
  ArrowRight,
  BarChart2,
  Building2,
  Cpu,
  DollarSign,
  LayoutDashboard,
  Route,
  Sparkles,
  Users,
  Wallet,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getOrgDashboard, getRunFlow, getRuns, getScopedSummary } from '@/lib/api'
import RunStatusBadge from '@/components/runs/RunStatusBadge'
import { formatAge, formatCost, formatTokens, truncateId } from '@/lib/utils'
import type { DashboardRange } from '@/components/dashboard/DashboardScopeBar'

type Scope = 'workspace' | 'org' | 'platform'
type View = 'overview' | 'breakdown'

function getDashboardWindow(range: string | undefined): {
  range: DashboardRange
  from: string
  to: string
  label: string
} {
  const normalized: DashboardRange =
    range === '24h' || range === '30d' || range === '90d' ? range : '7d'
  const now = new Date()
  const days = normalized === '24h' ? 1 : normalized === '30d' ? 30 : normalized === '90d' ? 90 : 7
  const from = new Date(now.getTime() - days * 24 * 3_600_000)
  return {
    range: normalized,
    from: from.toISOString(),
    to: now.toISOString(),
    label: normalized === '24h' ? 'Last 24 hours' : `Last ${days} days`,
  }
}

function parseScope(value: string | undefined, canOrg: boolean, canPlatform: boolean): Scope {
  if (value === 'platform' && canPlatform) return 'platform'
  if (value === 'org' && canOrg) return 'org'
  return 'workspace'
}

function parseView(value: string | undefined): View {
  return value === 'breakdown' ? 'breakdown' : 'overview'
}

function scopeLabel(scope: Scope) {
  return scope === 'platform' ? 'Platform' : scope === 'org' ? 'Organization' : 'Workspace'
}

function hrefFor(scope: Scope, range: DashboardRange, view: View) {
  return `/analytics?scope=${scope}&range=${range}&view=${view}`
}

function money(value: string | number | null | undefined) {
  const numeric = typeof value === 'number' ? value : Number.parseFloat(value ?? '0')
  if (!Number.isFinite(numeric)) return '$0'
  if (Math.abs(numeric) >= 1) return `$${numeric.toFixed(2)}`
  if (Math.abs(numeric) >= 0.001) return `$${numeric.toFixed(4)}`
  return `$${numeric.toFixed(6)}`
}

function percent(value: string | null | undefined) {
  const numeric = Number.parseFloat(value ?? '0')
  if (!Number.isFinite(numeric)) return '0%'
  return `${numeric >= 0 ? '+' : ''}${numeric.toFixed(1)}%`
}

function ScopeTabs({
  currentScope,
  currentRange,
  currentView,
  canOrg,
  canPlatform,
}: {
  currentScope: Scope
  currentRange: DashboardRange
  currentView: View
  canOrg: boolean
  canPlatform: boolean
}) {
  const options: { scope: Scope; label: string; visible: boolean }[] = [
    { scope: 'workspace', label: 'Workspace', visible: true },
    { scope: 'org', label: 'Organization', visible: canOrg },
    { scope: 'platform', label: 'Platform', visible: canPlatform },
  ]

  return (
    <div className="flex flex-wrap gap-2">
      {options.filter(option => option.visible).map(option => {
        const active = option.scope === currentScope
        return (
          <Link
            key={option.scope}
            href={hrefFor(option.scope, currentRange, currentView)}
            className={`rounded-full px-3 py-1.5 text-sm font-semibold transition ${
              active
                ? 'bg-blue-600 text-white'
                : 'border border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'
            }`}
          >
            {option.label}
          </Link>
        )
      })}
    </div>
  )
}

function RangeTabs({ currentScope, currentRange, currentView }: { currentScope: Scope; currentRange: DashboardRange; currentView: View }) {
  const ranges: DashboardRange[] = ['24h', '7d', '30d', '90d']
  return (
    <div className="flex flex-wrap rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
      {ranges.map(range => (
        <Link
          key={range}
          href={hrefFor(currentScope, range, currentView)}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
            currentRange === range
              ? 'bg-white text-blue-700 shadow-sm dark:bg-slate-950 dark:text-blue-300'
              : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'
          }`}
        >
          {range}
        </Link>
      ))}
    </div>
  )
}

function ViewTabs({ currentScope, currentRange }: { currentScope: Scope; currentRange: DashboardRange }) {
  return (
    <div className="flex flex-wrap gap-2">
      <span className="rounded-full bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white dark:bg-slate-100 dark:text-slate-950">Overview</span>
      <Link
        href={currentScope === 'workspace' ? '/analytics/breakdown' : hrefFor('workspace', currentRange, 'breakdown')}
        className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-600 transition hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
      >
        Breakdown
      </Link>
    </div>
  )
}

function StatCard({
  title,
  value,
  sub,
  icon: Icon,
}: {
  title: string
  value: string
  sub: string
  icon: React.ElementType
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm ring-1 ring-white/60 dark:border-slate-700 dark:bg-slate-900/85">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">{title}</p>
          <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-slate-50">{value}</p>
          <p className="mt-1 text-xs text-slate-500">{sub}</p>
        </div>
        <div className="rounded-xl bg-blue-50 p-2 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300">
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  )
}

export default async function AnalyticsOverviewPage({
  searchParams,
}: {
  searchParams?: { scope?: string; range?: string; view?: string; access_group_id?: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const raw = session as unknown as Record<string, unknown>
  const tenantRole = raw.tenantRole as string | undefined
  const isPlatformAdmin = raw.isPlatformAdmin as boolean | undefined
  const canOrg = Boolean(isPlatformAdmin || tenantRole === 'org_admin')
  const canPlatform = Boolean(isPlatformAdmin)

  const view = parseView(searchParams?.view)
  const win = getDashboardWindow(searchParams?.range)
  const accessGroupId = searchParams?.access_group_id
  const scope = accessGroupId ? 'workspace' : parseScope(searchParams?.scope, canOrg, canPlatform)
  const accessGroupDashboard = accessGroupId
    ? await getAccessGroupDashboard(session.apiKey, accessGroupId).catch(() => null)
    : null
  const accessGroup = accessGroupDashboard?.groups[0] ?? null

  if (view === 'breakdown') {
    if (scope !== 'workspace') {
      redirect(hrefFor('workspace', win.range, 'breakdown'))
    }
    redirect('/analytics/breakdown')
  }

  const [summary, flow, workspaceRuns, orgDashboard] = await Promise.all([
    getScopedSummary(session.apiKey, scope, { from: win.from, to: win.to, access_group_id: accessGroupId }),
    getRunFlow(session.apiKey, {
      scope,
      mode: 'request-route-provider-outcome',
      metric: 'requests',
      limit: 300,
      from: win.from,
      to: win.to,
      access_group_id: accessGroupId,
    }).catch(() => null),
    scope === 'workspace'
      ? getRuns(session.apiKey, { limit: 8, from: win.from, to: win.to, access_group_id: accessGroupId }).then(result => result.items)
      : Promise.resolve([]),
    scope === 'org'
      ? getOrgDashboard(session.apiKey, { from: win.from, to: win.to }).catch(() => null)
      : Promise.resolve(null),
  ])

  const flowItems = flow?.items ?? []
  const successCount = flowItems.filter(item => item.success).length
  const successRate = flowItems.length > 0 ? `${Math.round((successCount / flowItems.length) * 100)}%` : '—'
  const routeCounts = new Map<string, number>()
  for (const item of flowItems) {
    const label = item.route || item.provider || item.primary_model || 'Unassigned'
    routeCounts.set(label, (routeCounts.get(label) ?? 0) + 1)
  }
  const topRoute = Array.from(routeCounts.entries()).sort((a, b) => b[1] - a[1])[0] ?? null
  const recentRuns = scope === 'workspace' ? workspaceRuns : orgDashboard?.recent_runs ?? []
  const totalTokens = summary.total_input_tokens + summary.total_output_tokens
  const savingsRate = Number.parseFloat(summary.total_cost_usd) + Number.parseFloat(summary.total_savings_usd) > 0
    ? percent(String((Number.parseFloat(summary.total_savings_usd) / (Number.parseFloat(summary.total_cost_usd) + Number.parseFloat(summary.total_savings_usd))) * 100))
    : '—'

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <LayoutDashboard className="h-5 w-5 text-blue-700 dark:text-blue-300" />
            <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
              {scopeLabel(scope)} Observe
            </span>
          </div>
          <h1 className="font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950 dark:text-slate-50">
            Observability Overview
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            One scoped entry point for dashboards, analytics, request analysis, and workflow telemetry.
            Detailed charts stay available under Breakdown, while deep investigation continues in Runs, Sessions, Request Flow, and Request Explorer.
          </p>
          {accessGroup && (
            <p className="mt-2 text-sm text-blue-700 dark:text-blue-300">
              Filtered to access group: <span className="font-semibold">{accessGroup.name}</span>
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link href={`/request-flow?scope=${scope}&mode=request-route-provider-outcome&metric=requests${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
            Request Flow
          </Link>
          <Link href={accessGroupId ? `/request-explorer?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-explorer'} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
            Request Explorer
          </Link>
          <Link href={scope === 'workspace' ? '/analytics/breakdown' : hrefFor('workspace', win.range, 'breakdown')} className="rounded-xl bg-blue-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-blue-700">
            Open Breakdown
          </Link>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white/85 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900/90">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="space-y-3">
            <ScopeTabs currentScope={scope} currentRange={win.range} currentView="overview" canOrg={canOrg} canPlatform={canPlatform} />
            <ViewTabs currentScope={scope} currentRange={win.range} />
          </div>
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Window</div>
            <RangeTabs currentScope={scope} currentRange={win.range} currentView="overview" />
          </div>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Total Spend" value={money(summary.total_cost_usd)} sub={`${win.label} • ${percent(summary.cost_delta_pct)} vs prior`} icon={DollarSign} />
        <StatCard title="Runs" value={summary.run_count.toLocaleString()} sub={`${summary.call_count.toLocaleString()} provider calls`} icon={Activity} />
        <StatCard title="Savings" value={money(summary.total_savings_usd)} sub={summary.avg_cost_per_run ? `avg ${money(summary.avg_cost_per_run)} per run` : 'avg cost unavailable'} icon={Sparkles} />
        <StatCard title="Coverage" value={formatTokens(totalTokens)} sub={`${summary.active_users.toLocaleString()} active users • ${summary.workspace_count.toLocaleString()} workspaces`} icon={Cpu} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/85">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Top Intents</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">Workflow demand in this scope</h2>
            </div>
            <Link href={accessGroupId ? `/runs?access_group_id=${encodeURIComponent(accessGroupId)}` : '/runs'} className="text-xs font-semibold text-blue-700 hover:underline dark:text-blue-300">Open runs</Link>
          </div>
          <div className="mt-4 space-y-3">
            {summary.top_intents.length === 0 ? (
              <p className="rounded-xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-slate-700">No intent-tagged runs in this window yet.</p>
            ) : (
              summary.top_intents.map(intent => (
                <div key={intent.intent} className="rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/50">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-slate-900 dark:text-slate-100">{intent.intent}</p>
                      <p className="mt-1 text-xs text-slate-500">{intent.count.toLocaleString()} runs • {money(intent.cost_usd)}</p>
                    </div>
                    <Link href={`/request-flow?scope=${scope}&mode=request-intent-model-result&metric=requests${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`} className="text-xs font-semibold text-blue-700 hover:underline dark:text-blue-300">
                      Trace
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/85">
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Request Analysis</p>
          <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">Live pipeline health</h2>
          <div className="mt-4 grid gap-3">
            <StatCard title="Success rate" value={successRate} sub={`${flowItems.length.toLocaleString()} flow samples`} icon={Route} />
            <StatCard title="Most active route" value={topRoute?.[0] ?? 'No route data'} sub={topRoute ? `${topRoute[1].toLocaleString()} requests` : 'Send traffic through the gateway to populate routing analysis.'} icon={BarChart2} />
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm ring-1 ring-white/60 dark:border-slate-700 dark:bg-slate-900/85">
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Next actions</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link href={`/request-flow?scope=${scope}&mode=request-route-provider-outcome&metric=requests${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`} className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:text-blue-700 dark:bg-slate-800 dark:text-slate-200">
                  Request flow
                </Link>
                <Link href={accessGroupId ? `/request-explorer?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-explorer'} className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:text-blue-700 dark:bg-slate-800 dark:text-slate-200">
                  Explorer
                </Link>
                <Link href="/cost-savings" className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:text-blue-700 dark:bg-slate-800 dark:text-slate-200">
                  Cost & savings
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/85">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Top Models</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">Model mix for this scope</h2>
            </div>
            <Link href="/model-usage" className="text-xs font-semibold text-blue-700 hover:underline dark:text-blue-300">Open model usage</Link>
          </div>
          <div className="mt-4 space-y-3">
            {summary.top_models.length === 0 ? (
              <p className="rounded-xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-slate-700">No successful provider calls in this window yet.</p>
            ) : (
              summary.top_models.map(model => (
                <div key={`${model.provider}:${model.model}`} className="rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/50">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-mono text-sm font-medium text-slate-900 dark:text-slate-100">{model.model}</p>
                      <p className="mt-1 text-xs text-slate-500">{model.provider} • {model.call_count.toLocaleString()} calls • {formatTokens(model.input_tokens + model.output_tokens)}</p>
                    </div>
                    <span className="shrink-0 text-sm font-semibold text-slate-900 dark:text-slate-100">{money(model.cost_usd)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/85">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Recent Activity</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">
                {scope === 'platform' ? 'Scope summary for platform operators' : 'Latest runs in scope'}
              </h2>
            </div>
            {scope !== 'platform' && <Link href="/runs" className="text-xs font-semibold text-blue-700 hover:underline dark:text-blue-300">Open runs</Link>}
          </div>
          <div className="mt-4">
            {scope === 'platform' ? (
              <div className="grid gap-3 md:grid-cols-3">
                <StatCard title="Scope" value={scopeLabel(scope)} sub={`${summary.workspace_count.toLocaleString()} workspaces represented`} icon={Building2} />
                <StatCard title="Users" value={summary.active_users.toLocaleString()} sub="active in selected window" icon={Users} />
                <StatCard title="Savings rate" value={savingsRate} sub="estimated across successful calls" icon={Wallet} />
              </div>
            ) : recentRuns.length === 0 ? (
              <p className="rounded-xl border border-dashed border-slate-300 px-4 py-8 text-sm text-slate-500 dark:border-slate-700">No runs were captured in this window.</p>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {recentRuns.map(run => (
                  <Link
                    key={run.id}
                    href={`/runs/${run.id}`}
                    className="flex items-center gap-4 px-1 py-3 transition hover:bg-slate-50/80 dark:hover:bg-slate-950/40"
                  >
                    <code className="w-24 shrink-0 font-mono text-xs text-blue-700 dark:text-blue-300">{truncateId(run.id, 10)}</code>
                    <RunStatusBadge status={run.status as 'running' | 'succeeded' | 'failed' | 'cancelled'} />
                    <span className="min-w-0 flex-1 truncate text-xs text-slate-500">
                      {run.feature_tag ?? ('workspace_name' in run ? run.workspace_name : null) ?? 'General / Untagged'}
                    </span>
                    <span className="w-20 text-right text-xs font-medium text-slate-900 dark:text-slate-100">{formatCost(run.total_cost_usd)}</span>
                    <span className="w-16 text-right text-xs text-slate-500">{run.started_at ? formatAge(run.started_at) : '—'}</span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-300">
        <p className="font-semibold text-slate-950 dark:text-slate-50">Observe flow</p>
        <p className="mt-1">
          Start in Overview to understand scope-level health, jump to Breakdown for workspace charts, move into Runs or Sessions for concrete executions, then use Request Flow and Request Explorer when you need routing and pipeline causality.
        </p>
      </div>
    </div>
  )
}
