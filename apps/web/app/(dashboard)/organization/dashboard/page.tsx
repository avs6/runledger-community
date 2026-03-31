import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { Suspense } from 'react'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getOrgDashboard } from '@/lib/api'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import RunStatusBadge from '@/components/runs/RunStatusBadge'
import OrgSpendChart from '@/components/dashboard/OrgSpendChart'
import {
  DollarSign, Zap, TrendingUp, TrendingDown,
  Hash, Users, LayoutGrid, ArrowRight, Clock, Cpu,
} from 'lucide-react'
import { formatCost, formatTokens, truncateId, formatAge } from '@/lib/utils'
import type { OrgDashboard } from '@/types/api'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt$$(v: string | number) {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (isNaN(n)) return '$0'
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

// ── KPI card ─────────────────────────────────────────────────────────────────

function KpiCard({
  title, value, sub, delta, icon, cardFrom, cardTo, border,
}: {
  title: string
  value: string
  sub?: string
  delta?: string | null
  icon: React.ReactNode
  cardFrom: string
  cardTo: string
  border: string
}) {
  const d = delta !== undefined && delta !== null ? parseFloat(delta) : null
  return (
    <div className={`relative overflow-hidden rounded-2xl border ${border} bg-gradient-to-br ${cardFrom} p-5 shadow-sm`}>
      <div className={`pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full ${cardTo} blur-2xl opacity-50`} />
      <div className="relative flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{title}</p>
          <p className="mt-2 truncate text-3xl font-bold tracking-tight">{value}</p>
          {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
          {d !== null && (
            <div className={`mt-1.5 flex items-center gap-1 text-xs font-semibold ${d >= 0 ? 'text-rose-500 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
              {d >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {d >= 0 ? '+' : ''}{d.toFixed(1)}%
              <span className="font-normal text-muted-foreground">vs prior 7d</span>
            </div>
          )}
        </div>
        <div className="shrink-0 rounded-xl bg-white/20 p-2.5 dark:bg-white/10">{icon}</div>
      </div>
    </div>
  )
}

// ── Status badge colours ──────────────────────────────────────────────────────

const WS_STATUS: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  suspended: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  archived: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
}

// ── Main content (async server component) ─────────────────────────────────────

async function OrgDashboardContent() {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const data: OrgDashboard = await getOrgDashboard(session.apiKey)
  const totalTokens = data.total_tokens ?? 0

  return (
    <div className="space-y-6">
      {/* ── KPI row ── */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          title="Total Org Spend"
          value={fmt$$(data.total_cost_usd)}
          delta={data.cost_delta_pct}
          icon={<DollarSign className="h-5 w-5 text-violet-600 dark:text-violet-300" />}
          cardFrom="from-violet-50 to-violet-100/40 dark:from-violet-950/60 dark:to-violet-900/20"
          cardTo="bg-violet-300/30 dark:bg-violet-500/20"
          border="border-violet-200/70 dark:border-violet-800/50"
        />
        <KpiCard
          title="Agent Runs"
          value={data.run_count.toLocaleString()}
          sub="last 7 days"
          icon={<Zap className="h-5 w-5 text-violet-600 dark:text-violet-300" />}
          cardFrom="from-violet-50 to-violet-100/40 dark:from-violet-950/60 dark:to-violet-900/20"
          cardTo="bg-violet-300/30 dark:bg-violet-500/20"
          border="border-violet-200/70 dark:border-violet-800/50"
        />
        <KpiCard
          title="Workspaces"
          value={data.workspace_count.toLocaleString()}
          sub={`${data.member_count} members`}
          icon={<LayoutGrid className="h-5 w-5 text-indigo-600 dark:text-indigo-300" />}
          cardFrom="from-indigo-50 to-indigo-100/40 dark:from-indigo-950/60 dark:to-indigo-900/20"
          cardTo="bg-indigo-300/30 dark:bg-indigo-500/20"
          border="border-indigo-200/70 dark:border-indigo-800/50"
        />
        <KpiCard
          title="Total Tokens"
          value={formatTokens(totalTokens)}
          sub="across all workspaces"
          icon={<Cpu className="h-5 w-5 text-cyan-600 dark:text-cyan-300" />}
          cardFrom="from-cyan-50 to-cyan-100/40 dark:from-cyan-950/60 dark:to-cyan-900/20"
          cardTo="bg-cyan-300/30 dark:bg-cyan-500/20"
          border="border-cyan-200/70 dark:border-cyan-800/50"
        />
      </div>

      {/* ── Workspace spend chart + table ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Workspace breakdown bar chart */}
        <Card className="overflow-hidden border-slate-200/60 dark:border-slate-700/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Spend by Workspace</CardTitle>
            <p className="text-xs text-muted-foreground">Last 7 days · sorted by cost</p>
          </CardHeader>
          <CardContent className="pb-4 pt-0">
            <OrgSpendChart workspaces={data.workspaces} />
          </CardContent>
        </Card>

        {/* Top models */}
        <Card className="border-slate-200/60 dark:border-slate-700/60">
          <CardHeader className="pb-1">
            <CardTitle className="text-base font-semibold">Top Models</CardTitle>
            <p className="text-xs text-muted-foreground">Across all workspaces — last 7 days</p>
          </CardHeader>
          <CardContent className="p-0">
            {data.top_models.length === 0 ? (
              <p className="px-5 py-8 text-center text-sm text-muted-foreground">No model usage yet</p>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {data.top_models.map((m) => (
                  <div key={m.model} className="flex items-center gap-3 px-5 py-2.5">
                    <span className="flex-1 truncate font-mono text-xs text-slate-700 dark:text-slate-200">{m.model}</span>
                    <span className="text-xs text-slate-400">{m.call_count.toLocaleString()} calls</span>
                    <span className="w-20 text-right font-mono text-xs font-semibold">{fmt$$(m.cost_usd)}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Workspace table ── */}
      <Card className="overflow-hidden border-slate-200/60 dark:border-slate-700/60">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-base font-semibold">All Workspaces</CardTitle>
            <p className="mt-0.5 text-xs text-muted-foreground">Cost and run breakdown — last 7 days</p>
          </div>
          <Link
            href="/organization"
            className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-violet-600 transition-colors hover:bg-violet-50 dark:text-violet-400 dark:hover:bg-violet-950/40"
          >
            Manage org <ArrowRight className="h-3 w-3" />
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          {data.workspaces.length === 0 ? (
            <p className="px-5 py-10 text-center text-sm text-muted-foreground">No workspaces yet</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40">
                  <th className="px-5 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Workspace</th>
                  <th className="px-5 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="px-5 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Runs</th>
                  <th className="px-5 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Members</th>
                  <th className="px-5 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Spend (7d)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {data.workspaces.map((ws) => (
                  <tr key={ws.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400 text-xs font-bold shrink-0">
                          {ws.name.charAt(0).toUpperCase()}
                        </div>
                        <span className="font-medium text-slate-900 dark:text-white">{ws.name}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${WS_STATUS[ws.status] ?? WS_STATUS.active}`}>
                        {ws.status.charAt(0).toUpperCase() + ws.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right text-xs text-slate-500 dark:text-slate-400">
                      {ws.run_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <div className="flex items-center justify-end gap-1 text-xs text-slate-500 dark:text-slate-400">
                        <Users className="h-3 w-3" />
                        {ws.member_count}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-xs font-semibold">
                      {fmt$$(ws.cost_usd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* ── Recent runs across workspaces ── */}
      <Card className="overflow-hidden border-slate-200/60 dark:border-slate-700/60">
        <CardHeader className="pb-2">
          <div>
            <CardTitle className="text-base font-semibold">Recent Runs</CardTitle>
            <p className="mt-0.5 text-xs text-muted-foreground">Latest runs across all workspaces</p>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {data.recent_runs.length === 0 ? (
            <p className="px-5 py-10 text-center text-sm text-muted-foreground">No runs yet</p>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {data.recent_runs.map((run) => (
                <Link
                  key={run.id}
                  href={`/runs/${run.id}`}
                  className="group flex items-center gap-4 px-5 py-3 transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                >
                  <code className="w-24 shrink-0 font-mono text-xs text-indigo-600 group-hover:underline dark:text-indigo-400">
                    {truncateId(run.id, 10)}
                  </code>
                  <RunStatusBadge status={run.status as 'running' | 'succeeded' | 'failed' | 'cancelled'} />
                  <span className="flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-500 dark:text-slate-400 shrink-0">
                    <LayoutGrid className="h-3 w-3" />
                    {run.workspace_name}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
                    {run.feature_tag ?? '—'}
                  </span>
                  <span className="w-20 text-right font-mono text-xs font-semibold">
                    {formatCost(run.total_cost_usd)}
                  </span>
                  <span className="flex w-16 items-center justify-end gap-1 text-right text-xs text-muted-foreground">
                    <Clock className="h-3 w-3 shrink-0" />
                    {run.started_at ? formatAge(run.started_at) : '—'}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function OrgDashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-32 rounded-2xl" />)}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
      <Skeleton className="h-72 rounded-2xl" />
      <Skeleton className="h-64 rounded-2xl" />
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default async function OrgDashboardPage() {
  const session = await getServerSession(authOptions)
  const s = session as Record<string, unknown> | null
  const tenantRole = s?.tenantRole as string | undefined
  const isPlatformAdmin = s?.isPlatformAdmin as boolean | undefined

  const isOrgAdmin = isPlatformAdmin || tenantRole === 'org_admin'
  if (!isOrgAdmin) redirect('/dashboard')

  const orgName = (s?.tenantName ?? s?.orgName) as string | undefined
  const dateStr = new Date().toLocaleDateString([], {
    weekday: 'long', month: 'long', day: 'numeric',
  })

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="rounded-full bg-violet-100 px-2.5 py-0.5 text-[11px] font-semibold text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
              Global View
            </span>
            {orgName && (
              <span className="text-sm text-muted-foreground font-medium">{orgName}</span>
            )}
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Organization Dashboard</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">{dateStr} · Last 7 days · All workspaces</p>
        </div>
        <Link
          href="/dashboard"
          className="hidden text-sm text-violet-600 hover:underline dark:text-violet-400 sm:block"
        >
          ← Workspace dashboard
        </Link>
      </div>
      <Suspense fallback={<OrgDashboardSkeleton />}>
        <OrgDashboardContent />
      </Suspense>
    </div>
  )
}
