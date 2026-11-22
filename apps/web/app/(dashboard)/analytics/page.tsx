import { getServerSession } from 'next-auth'
import Link from 'next/link'
import {
  Activity,
  Cpu,
  DollarSign,
  LayoutDashboard,
  Network,
  Route,
  Shield,
  Sparkles,
  Users,
  Wallet,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getOrgDashboard, getRunFlow, getRuns, getScopedSummary } from '@/lib/api'
import RunStatusBadge from '@/components/runs/RunStatusBadge'
import { formatAge, formatCost, formatTokens, truncateId, num } from '@/lib/utils'
import AnalyticsBreakdownClient from '@/components/dashboard/AnalyticsBreakdownClient'
import type { DashboardRange } from '@/components/dashboard/DashboardScopeBar'
import { RelatedPanel } from '@/components/context/RelatedPanel'

type Scope = 'workspace' | 'org' | 'platform'

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

function scopeLabel(scope: Scope) {
  return scope === 'platform' ? 'Platform' : scope === 'org' ? 'Organization' : 'Workspace'
}

function hrefFor(scope: Scope, range: DashboardRange) {
  return `/analytics?scope=${scope}&range=${range}`
}

function money(value: string | number | null | undefined) {
  const numeric = typeof value === 'number' ? value : Number.parseFloat(value ?? '0')
  if (!Number.isFinite(numeric)) return '$0'
  if (Math.abs(num(numeric)) >= 1) return `$${num(numeric).toFixed(2)}`
  if (Math.abs(num(numeric)) >= 0.001) return `$${num(numeric).toFixed(4)}`
  return `$${num(numeric).toFixed(6)}`
}

function percent(value: string | null | undefined) {
  const numeric = Number.parseFloat(value ?? '0')
  if (!Number.isFinite(numeric)) return '0%'
  return `${num(numeric) >= 0 ? '+' : ''}${num(numeric).toFixed(1)}%`
}

function ScopeTabs({
  currentScope,
  currentRange,
  canOrg,
  canPlatform,
}: {
  currentScope: Scope
  currentRange: DashboardRange
  canOrg: boolean
  canPlatform: boolean
}) {
  const options: { scope: Scope; label: string; visible: boolean }[] = [
    { scope: 'workspace', label: 'Workspace', visible: true },
    { scope: 'org', label: 'Organization', visible: canOrg },
    { scope: 'platform', label: 'Platform', visible: canPlatform },
  ]

  return (
    <div className="flex flex-wrap gap-1.5">
      {options.filter(o => o.visible).map(o => {
        const active = o.scope === currentScope
        return (
          <Link
            key={o.scope}
            href={hrefFor(o.scope, currentRange)}
            className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
              active
                ? 'bg-blue-600 text-white dark:bg-blue-500'
                : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
            }`}
          >
            {o.label}
          </Link>
        )
      })}
    </div>
  )
}

function RangeTabs({ currentScope, currentRange }: { currentScope: Scope; currentRange: DashboardRange }) {
  const ranges: DashboardRange[] = ['24h', '7d', '30d', '90d']
  return (
    <div className="flex rounded-lg border border-slate-200 bg-slate-100 p-0.5 dark:border-slate-700 dark:bg-slate-800">
      {ranges.map(range => (
        <Link
          key={range}
          href={hrefFor(currentScope, range)}
          className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${
            currentRange === range
              ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
              : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
          }`}
        >
          {range}
        </Link>
      ))}
    </div>
  )
}

function HeroStat({
  label,
  value,
  sub,
  icon: Icon,
}: {
  label: string
  value: string
  sub: string
  icon: React.ElementType
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-700 dark:bg-slate-800/60">
      <div className="flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
        <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">{label}</span>
      </div>
      <p className="mt-1 text-xl font-bold tracking-tight text-slate-900 dark:text-white">{value}</p>
      <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">{sub}</p>
    </div>
  )
}

export default async function AnalyticsOverviewPage({
  searchParams,
}: {
  searchParams?: { scope?: string; range?: string; access_group_id?: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const raw = session as unknown as Record<string, unknown>
  const tenantRole = raw.tenantRole as string | undefined
  const isPlatformAdmin = raw.isPlatformAdmin as boolean | undefined
  const canOrg = Boolean(isPlatformAdmin || tenantRole === 'org_admin')
  const canPlatform = Boolean(isPlatformAdmin)

  const win = getDashboardWindow(searchParams?.range)
  const accessGroupId = searchParams?.access_group_id
  const scope = accessGroupId ? 'workspace' : parseScope(searchParams?.scope, canOrg, canPlatform)
  const accessGroupDashboard = accessGroupId
    ? await getAccessGroupDashboard(session.apiKey, accessGroupId).catch(() => null)
    : null
  const accessGroup = accessGroupDashboard?.groups[0] ?? null


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
      ? getRuns(session.apiKey, { limit: 6, from: win.from, to: win.to, access_group_id: accessGroupId }).then(result => result.items)
      : Promise.resolve([]),
    scope === 'org'
      ? getOrgDashboard(session.apiKey, { from: win.from, to: win.to }).catch(() => null)
      : Promise.resolve(null),
  ])

  const flowItems = flow?.items ?? []
  const successCount = flowItems.filter(item => item.success).length
  const successRate = flowItems.length > 0 ? `${Math.round((successCount / flowItems.length) * 100)}%` : '--'
  const totalTokens = summary.total_input_tokens + summary.total_output_tokens
  const recentRuns = scope === 'workspace' ? workspaceRuns : orgDashboard?.recent_runs ?? []

  return (
    <div className="space-y-4">
      {/* Hero header */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="mb-1.5 flex items-center gap-2">
                <LayoutDashboard className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-blue-700 dark:bg-blue-500/20 dark:text-blue-300">
                  {scopeLabel(scope)} Overview
                </span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-950 dark:text-white">
                Observability Command Center
              </h1>
                <div className="mt-2"><RelatedPanel entity="workspace" label="Workspace context" /></div>
              <p className="mt-1 max-w-2xl text-xs text-slate-500 dark:text-slate-400">
                Unified analytics, cost attribution, and platform health.
              </p>
              {accessGroup && (
                <p className="mt-1 text-xs text-blue-600 dark:text-blue-300">
                  Filtered: <span className="font-semibold">{accessGroup.name}</span>
                </p>
              )}
            </div>
            <div className="flex flex-col items-end gap-2">
              <ScopeTabs currentScope={scope} currentRange={win.range} canOrg={canOrg} canPlatform={canPlatform} />
              <RangeTabs currentScope={scope} currentRange={win.range} />
            </div>
          </div>

          {/* KPI strip */}
          <div className="mt-4 grid grid-cols-2 gap-2 lg:grid-cols-5">
            <HeroStat label="Total Spend" value={money(summary.total_cost_usd)} sub={`${percent(summary.cost_delta_pct)} vs prior`} icon={DollarSign} />
            <HeroStat label="Runs" value={summary.run_count.toLocaleString()} sub={`${summary.call_count.toLocaleString()} calls`} icon={Activity} />
            <HeroStat label="Savings" value={money(summary.total_savings_usd)} sub={summary.avg_cost_per_run ? `${money(summary.avg_cost_per_run)}/run` : '--'} icon={Sparkles} />
            <HeroStat label="Tokens" value={formatTokens(totalTokens)} sub={`${summary.active_users.toLocaleString()} users`} icon={Cpu} />
            <HeroStat label="Success" value={successRate} sub={`${flowItems.length.toLocaleString()} samples`} icon={Route} />
          </div>

          {/* Quick nav */}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {[
              { href: `/request-flow?scope=${scope}&mode=request-route-provider-outcome&metric=requests${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`, label: 'Request Flow' },
              { href: accessGroupId ? `/request-explorer?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-explorer', label: 'Explorer' },
              { href: '/monitoring', label: 'Monitoring' },
              { href: '/cost-savings', label: 'Cost & Savings' },
              { href: '/model-usage', label: 'Models' },
            ].map(nav => (
              <Link key={nav.label} href={nav.href} className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-600 transition hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-white">
                {nav.label}
              </Link>
            ))}
          </div>
      </div>

      {/* Analytics Breakdown — charts as hero */}
      <AnalyticsBreakdownClient embedded initialPreset={win.range} apiKey={session.apiKey} />

      {/* Grid: Recent activity + Top intents + Top models */}
      <div className="grid gap-3 xl:grid-cols-3">
        {/* Recent Activity */}
        <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900/85">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Recent Runs</p>
            <Link href="/runs" className="text-[10px] font-semibold text-blue-600 hover:underline dark:text-blue-400">All runs</Link>
          </div>
          <div className="mt-2">
            {recentRuns.length === 0 ? (
              <p className="py-6 text-center text-xs text-slate-400 dark:text-slate-500">No runs captured</p>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {recentRuns.map(run => (
                  <Link key={run.id} href={`/runs/${run.id}`} className="flex items-center gap-2 py-1.5 transition hover:bg-slate-50/80 dark:hover:bg-slate-950/40">
                    <code className="w-16 shrink-0 font-mono text-[10px] text-blue-600 dark:text-blue-400">{truncateId(run.id, 8)}</code>
                    <RunStatusBadge status={run.status as 'running' | 'succeeded' | 'failed' | 'cancelled'} />
                    <span className="min-w-0 flex-1 truncate text-[11px] text-slate-500">{run.feature_tag ?? ('workspace_name' in run ? run.workspace_name : null) ?? 'Untagged'}</span>
                    <span className="text-[10px] font-medium text-slate-700 dark:text-slate-300">{formatCost(run.total_cost_usd)}</span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Top Intents */}
        <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900/85">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Top Intents</p>
            <Link href={`/request-flow?scope=${scope}&mode=request-intent-model-result&metric=requests`} className="text-[10px] font-semibold text-blue-600 hover:underline dark:text-blue-400">Trace</Link>
          </div>
          <div className="mt-2 space-y-1.5">
            {summary.top_intents.length === 0 ? (
              <p className="py-6 text-center text-xs text-slate-400 dark:text-slate-500">No intent-tagged runs</p>
            ) : (
              summary.top_intents.map(intent => (
                <div key={intent.intent} className="rounded-lg border border-slate-100 bg-slate-50/60 px-2.5 py-2 dark:border-slate-800 dark:bg-slate-950/40">
                  <p className="truncate text-xs font-medium text-slate-800 dark:text-slate-200">{intent.intent}</p>
                  <p className="mt-0.5 text-[10px] text-slate-400">{intent.count.toLocaleString()} runs &middot; {money(intent.cost_usd)}</p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Top Models */}
        <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900/85">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Top Models</p>
            <Link href="/model-usage" className="text-[10px] font-semibold text-blue-600 hover:underline dark:text-blue-400">All models</Link>
          </div>
          <div className="mt-2 space-y-1.5">
            {summary.top_models.length === 0 ? (
              <p className="py-6 text-center text-xs text-slate-400 dark:text-slate-500">No model data</p>
            ) : (
              summary.top_models.map(model => (
                <div key={`${model.provider}:${model.model}`} className="rounded-lg border border-slate-100 bg-slate-50/60 px-2.5 py-2 dark:border-slate-800 dark:bg-slate-950/40">
                  <div className="flex items-center justify-between gap-2">
                    <p className="min-w-0 truncate font-mono text-[11px] font-medium text-slate-800 dark:text-slate-200">{model.model}</p>
                    <span className="shrink-0 text-xs font-semibold text-slate-700 dark:text-slate-200">{money(model.cost_usd)}</span>
                  </div>
                  <p className="mt-0.5 text-[10px] text-slate-400">{model.provider} &middot; {model.call_count.toLocaleString()} calls &middot; {formatTokens(model.input_tokens + model.output_tokens)}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-2 lg:grid-cols-2">




      </div>
    </div>
  )
}
