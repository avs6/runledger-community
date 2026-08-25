import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import {
  Activity,
  ArrowRight,
  BarChart2,
  BookOpen,
  Building2,
  Cpu,
  Database,
  DollarSign,
  Key,
  LayoutDashboard,
  Lock,
  Network,
  Route,
  Shield,
  Sparkles,
  Users,
  Wallet,
  Wrench,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getInvestigationAccessGroupPosture, getOrgDashboard, getOverviewFinopsBudgetPosture, getOverviewGatewayPosture, getOverviewGovernancePosture, getOverviewOrgPosture, getOverviewScopePosture, getRunFlow, getRuns, getScopedSummary } from '@/lib/api'
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

  const [investigationPosture, budgetPosture, gatewayPosture, governancePosture, orgPosture, scopePosture] = await Promise.all([
    getInvestigationAccessGroupPosture(session.apiKey).catch(() => null),
    getOverviewFinopsBudgetPosture(session.apiKey).catch(() => null),
    getOverviewGatewayPosture(session.apiKey).catch(() => null),
    getOverviewGovernancePosture(session.apiKey).catch(() => null),
    getOverviewOrgPosture(session.apiKey).catch(() => null),
    getOverviewScopePosture(session.apiKey).catch(() => null),
  ])

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
          <Link href="/monitoring" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
            Monitoring
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
                <Link href="/monitoring" className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:text-blue-700 dark:bg-slate-800 dark:text-slate-200">
                  Monitoring
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

      {investigationPosture && (
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/85">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Investigation Scope</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">Access-Group Scoped Investigation</h2>
            </div>
            <Link href="/access-groups" className="text-xs font-semibold text-blue-700 hover:underline dark:text-blue-300">Manage groups</Link>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Access Groups" value={investigationPosture.access_group_context.access_groups.toLocaleString()} sub="active groups" icon={Shield} />
            <StatCard title="Group Members" value={investigationPosture.access_group_context.total_members.toLocaleString()} sub="across all groups" icon={Users} />
            <StatCard title="Runs (30d)" value={investigationPosture.investigation_context.runs_30d.toLocaleString()} sub={`${investigationPosture.investigation_context.requests_30d.toLocaleString()} requests`} icon={Activity} />
            <StatCard title="Active Users" value={investigationPosture.investigation_context.active_users.toLocaleString()} sub={`${investigationPosture.investigation_context.active_routes.toLocaleString()} active routes`} icon={Cpu} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/access-groups" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Access Groups</Link>
            <Link href={`/runs${accessGroupId ? `?access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`} className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Runs</Link>
            <Link href={`/request-flow${accessGroupId ? `?access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`} className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Flow</Link>
            <Link href={`/request-explorer${accessGroupId ? `?access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`} className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Explorer</Link>
            <Link href="/users" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Users</Link>
            <Link href="/workspaces" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Workspaces</Link>
            <Link href="/analytics/users" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Analytics Users</Link>
            <Link href="/model-usage" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Model Usage</Link>
            <Link href="/monitoring" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Monitoring</Link>
          </div>
        </div>
      )}

      {budgetPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 shadow-sm dark:border-emerald-800 dark:bg-emerald-950/40">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-emerald-700 dark:text-emerald-400">FinOps Budget Posture</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">Budget & Billing Overview</h2>
            </div>
            <Link href="/budgets" className="text-xs font-semibold text-emerald-700 hover:underline dark:text-emerald-400">Manage budgets</Link>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Active Budgets" value={`${budgetPosture.budget_context.active_budgets}`} sub={`${budgetPosture.budget_context.budgets} total • ${budgetPosture.budget_context.breach_count} breached`} icon={Wallet} />
            <StatCard title="Budget Limit" value={`$${budgetPosture.budget_context.total_limit_usd.toFixed(2)}`} sub={`${budgetPosture.budget_context.overrides} overrides (${budgetPosture.budget_context.active_overrides} active)`} icon={DollarSign} />
            <StatCard title="Spend (30d)" value={`$${budgetPosture.spend_context.total_spend_30d.toFixed(2)}`} sub={`${budgetPosture.spend_context.total_runs_30d.toLocaleString()} runs`} icon={Activity} />
            <StatCard title="Notifications" value={`${budgetPosture.notification_context.active_notifications}`} sub={`${budgetPosture.notification_context.notifications} total configured`} icon={Shield} />
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-emerald-200 bg-white/80 px-4 py-3 dark:border-emerald-800 dark:bg-slate-900/60">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-emerald-600 dark:text-emerald-400">Billing</p>
              <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-50">{budgetPosture.billing_context.billing_periods}</p>
              <p className="text-xs text-slate-500">{budgetPosture.billing_context.open_billing_periods} open</p>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-white/80 px-4 py-3 dark:border-emerald-800 dark:bg-slate-900/60">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-emerald-600 dark:text-emerald-400">Chargeback</p>
              <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-50">{budgetPosture.billing_context.chargeback_rules}</p>
              <p className="text-xs text-slate-500">attribution rules</p>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-white/80 px-4 py-3 dark:border-emerald-800 dark:bg-slate-900/60">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-emerald-600 dark:text-emerald-400">Budget Health</p>
              <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-50">
                {budgetPosture.budget_context.active_budgets > 0
                  ? `${Math.round(((budgetPosture.budget_context.active_budgets - budgetPosture.budget_context.breach_count) / budgetPosture.budget_context.active_budgets) * 100)}%`
                  : 'n/a'}
              </p>
              <p className="text-xs text-slate-500">within limit</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/budgets" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?view=detail" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Budget Detail</Link>
            <Link href="/budgets?view=overrides" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Budget Overrides</Link>
            <Link href="/budgets?view=notifications" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Notifications</Link>
            <Link href="/billing" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Billing Periods</Link>
            <Link href="/billing?view=detail" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Billing Detail</Link>
            <Link href="/chargeback" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Chargeback</Link>
            <Link href="/ledger" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Ledger</Link>
            <Link href="/model-budgets" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Model Budgets</Link>
          </div>
        </div>
      )}

      {gatewayPosture && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50/60 p-5 shadow-sm dark:border-violet-800 dark:bg-violet-950/40">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-violet-700 dark:text-violet-400">Gateway Posture</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">Routing & Guardrails</h2>
            </div>
            <Link href="/gateway" className="text-xs font-semibold text-violet-700 hover:underline dark:text-violet-400">Gateway</Link>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <StatCard title="Providers" value={`${gatewayPosture.provider_context.distinct_providers}`} sub={`${gatewayPosture.provider_context.active_routes} active routes`} icon={Network} />
            <StatCard title="Routes" value={`${gatewayPosture.provider_context.active_routes}/${gatewayPosture.provider_context.total_routes}`} sub={`${gatewayPosture.provider_context.routing_policies} policies`} icon={Route} />
            <StatCard title="Guardrails" value={`${gatewayPosture.guardrail_context.active_rules}`} sub={`${gatewayPosture.guardrail_context.events_30d} events (30d) • ${gatewayPosture.guardrail_context.blocks_30d} blocks`} icon={Shield} />
          </div>
          {scopePosture && (
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-violet-200 bg-white/80 px-4 py-3 dark:border-violet-800 dark:bg-slate-900/60">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-violet-600 dark:text-violet-400">Response Cache</p>
                <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-50">{scopePosture.cache_context.enabled_configs}/{scopePosture.cache_context.cache_configs}</p>
                <p className="text-xs text-slate-500">{scopePosture.cache_context.total_hits.toLocaleString()} hits • ${scopePosture.cache_context.total_savings_usd.toFixed(2)} saved</p>
              </div>
              <div className="rounded-xl border border-violet-200 bg-white/80 px-4 py-3 dark:border-violet-800 dark:bg-slate-900/60">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-violet-600 dark:text-violet-400">Rate Limits</p>
                <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-50">{scopePosture.rate_limit_context.routes_with_limits}</p>
                <p className="text-xs text-slate-500">rate-limited routes • {scopePosture.rate_limit_context.routes_without_limits} unlimited</p>
              </div>
              <div className="rounded-xl border border-violet-200 bg-white/80 px-4 py-3 dark:border-violet-800 dark:bg-slate-900/60">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-violet-600 dark:text-violet-400">Passthrough</p>
                <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-50">{gatewayPosture.route_context.passthrough_endpoints}</p>
                <p className="text-xs text-slate-500">passthrough endpoints</p>
              </div>
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/provider-profiles" className="text-xs text-violet-700 hover:underline dark:text-violet-400">Provider Profiles</Link>
            <Link href="/gateway" className="text-xs text-violet-700 hover:underline dark:text-violet-400">Model Gateway</Link>
            <Link href="/guardrails" className="text-xs text-violet-700 hover:underline dark:text-violet-400">Guardrails</Link>
            <Link href="/gateway/routes" className="text-xs text-violet-700 hover:underline dark:text-violet-400">Gateway Routes</Link>
            <Link href="/response-cache" className="text-xs text-violet-700 hover:underline dark:text-violet-400">Response Cache</Link>
            <Link href="/rate-limits" className="text-xs text-violet-700 hover:underline dark:text-violet-400">Rate Limits</Link>
          </div>
        </div>
      )}

      {governancePosture && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-5 shadow-sm dark:border-amber-800 dark:bg-amber-950/40">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-amber-700 dark:text-amber-400">Governance Posture</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">Security, Alerts & Audit</h2>
            </div>
            <Link href="/security" className="text-xs font-semibold text-amber-700 hover:underline dark:text-amber-400">Security</Link>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Security Events" value={`${governancePosture.security_context.security_events_30d}`} sub={`${governancePosture.security_context.security_events} total`} icon={Shield} />
            <StatCard title="Alert Rules" value={`${governancePosture.alert_context.active_alert_rules}/${governancePosture.alert_context.alert_rules}`} sub={`${governancePosture.alert_context.active_firings} active firings`} icon={Activity} />
            <StatCard title="Audit (30d)" value={`${governancePosture.audit_context.audit_events_30d}`} sub="audit events" icon={BookOpen} />
            <StatCard title="Tags" value={`${governancePosture.governance_context.active_tags}/${governancePosture.governance_context.tags}`} sub={`${governancePosture.governance_context.approvals} approvals`} icon={Sparkles} />
          </div>
          {scopePosture && (
            <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-xl border border-amber-200 bg-white/80 px-4 py-3 dark:border-amber-800 dark:bg-slate-900/60">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-amber-600 dark:text-amber-400">Tool Registry</p>
                <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-50">{scopePosture.tool_context.tool_registry_entries}</p>
                <p className="text-xs text-slate-500">registered tools</p>
              </div>
              <div className="rounded-xl border border-amber-200 bg-white/80 px-4 py-3 dark:border-amber-800 dark:bg-slate-900/60">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-amber-600 dark:text-amber-400">Tool Policies</p>
                <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-50">{scopePosture.tool_context.active_tool_policies}/{scopePosture.tool_context.tool_policies}</p>
                <p className="text-xs text-slate-500">active / total</p>
              </div>
              <div className="rounded-xl border border-amber-200 bg-white/80 px-4 py-3 dark:border-amber-800 dark:bg-slate-900/60">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-amber-600 dark:text-amber-400">Approvals</p>
                <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-50">{scopePosture.tool_context.pending_approvals}</p>
                <p className="text-xs text-slate-500">pending approvals</p>
              </div>
              <div className="rounded-xl border border-amber-200 bg-white/80 px-4 py-3 dark:border-amber-800 dark:bg-slate-900/60">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-amber-600 dark:text-amber-400">Data Capture</p>
                <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-50">{scopePosture.tool_context.capture_policies}</p>
                <p className="text-xs text-slate-500">capture policies</p>
              </div>
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/security" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Security</Link>
            <Link href="/alert-rules" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Alert Rules</Link>
            <Link href="/audit" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Audit Log</Link>
            <Link href="/governance" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Governance Pack</Link>
            <Link href="/tags" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Tags</Link>
            <Link href="/tool-registry" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Tool Registry</Link>
            <Link href="/tool-policies" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Tool Policies</Link>
            <Link href="/approvals" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Approvals</Link>
            <Link href="/data-capture" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Data Capture</Link>
          </div>
        </div>
      )}

      {orgPosture && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/60 p-5 shadow-sm dark:border-blue-800 dark:bg-blue-950/40">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-blue-700 dark:text-blue-400">Org Identity</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">Users, Keys & Telemetry</h2>
            </div>
            <Link href="/organization" className="text-xs font-semibold text-blue-700 hover:underline dark:text-blue-400">Organization</Link>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <StatCard title="Users" value={`${orgPosture.user_context.workspace_users}`} sub="workspace members" icon={Users} />
            <StatCard title="API Keys" value={`${orgPosture.api_key_context.active_api_keys}/${orgPosture.api_key_context.api_keys}`} sub="active / total" icon={Key} />
            <StatCard title="Telemetry (30d)" value={`${orgPosture.telemetry_context.telemetry_batches_30d}`} sub={`${orgPosture.telemetry_context.telemetry_batches} total batches`} icon={Activity} />
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <StatCard title="MCP Servers" value={`${orgPosture.mcp_context.active_mcp_servers}/${orgPosture.mcp_context.mcp_servers}`} sub="active / total" icon={Cpu} />
            <StatCard title="AI Hub Models" value={`${orgPosture.hub_context.active_hub_models}/${orgPosture.hub_context.hub_models}`} sub="active / total" icon={Sparkles} />
            {scopePosture && (
              <StatCard title="Access Groups" value={`${scopePosture.access_group_context.active_access_groups}/${scopePosture.access_group_context.access_groups}`} sub={`${scopePosture.access_group_context.total_members} members`} icon={Shield} />
            )}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/onboarding" className="text-xs text-blue-700 hover:underline dark:text-blue-400">Onboarding</Link>
            <Link href="/users" className="text-xs text-blue-700 hover:underline dark:text-blue-400">Users</Link>
            <Link href="/api-keys" className="text-xs text-blue-700 hover:underline dark:text-blue-400">API Keys</Link>
            <Link href="/access-groups" className="text-xs text-blue-700 hover:underline dark:text-blue-400">Access Groups</Link>
            <Link href="/monitoring/telemetry" className="text-xs text-blue-700 hover:underline dark:text-blue-400">Telemetry</Link>
            <Link href="/mcp-registry" className="text-xs text-blue-700 hover:underline dark:text-blue-400">MCP Registry</Link>
            <Link href="/ai-hub" className="text-xs text-blue-700 hover:underline dark:text-blue-400">AI Hub</Link>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-300">
        <p className="font-semibold text-slate-950 dark:text-slate-50">Observe flow</p>
        <p className="mt-1">
          Start in Overview to understand scope-level health, jump to Breakdown for workspace charts, move into Runs or Sessions for concrete executions, then use Request Flow and Request Explorer when you need routing and pipeline causality.
        </p>
      </div>
    </div>
  )
}
