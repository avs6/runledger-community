import { getServerSession } from 'next-auth'
import { Suspense } from 'react'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import {
  getAnalyticsSummary, getSpendOverTime,
  getSpendByModel, getSpendByFeature, getRuns,
} from '@/lib/api'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import DashboardAreaChart from '@/components/dashboard/DashboardAreaChart'
import ModelDonutChart from '@/components/dashboard/ModelDonutChart'
import FeatureBarsChart from '@/components/dashboard/FeatureBarsChart'
import RunStatusBadge from '@/components/runs/RunStatusBadge'
import {
  DollarSign, Zap, TrendingUp, TrendingDown,
  Hash, Cpu, ArrowRight, Clock,
} from 'lucide-react'
import { formatCost, formatTokens, truncateId, formatAge } from '@/lib/utils'
import type { AnalyticsSummary } from '@/types/api'

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
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
            {title}
          </p>
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
        <div className="shrink-0 rounded-xl bg-white/20 p-2.5 dark:bg-white/10">
          {icon}
        </div>
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt$$(v: string) {
  const n = parseFloat(v)
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

function deriveKpis(summary: AnalyticsSummary) {
  const tokens = summary.total_input_tokens + summary.total_output_tokens
  const avg = summary.run_count > 0
    ? fmt$$(String(parseFloat(summary.total_cost_usd) / summary.run_count))
    : '$0'
  const inputPct = tokens > 0
    ? ((summary.total_input_tokens / tokens) * 100).toFixed(0)
    : null
  return { tokens, avg, inputPct }
}

// ── Main content (async) ──────────────────────────────────────────────────────

async function DashboardContent() {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const now = new Date()
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 3_600_000)
  const win = { from: sevenDaysAgo.toISOString(), to: now.toISOString() }

  const [summary, spendTime, spendModel, spendFeature, recentRuns] = await Promise.all([
    getAnalyticsSummary(session.apiKey, win),
    getSpendOverTime(session.apiKey, 'daily', win),
    getSpendByModel(session.apiKey, win),
    getSpendByFeature(session.apiKey, win),
    getRuns(session.apiKey, { limit: 8 }),
  ])

  const { tokens, avg, inputPct } = deriveKpis(summary)

  return (
    <div className="space-y-6">
      {/* ── KPI cards ── */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          title="Total Spend"
          value={fmt$$(summary.total_cost_usd)}
          delta={summary.cost_delta_pct}
          icon={<DollarSign className="h-5 w-5 text-teal-600 dark:text-teal-300" />}
          cardFrom="from-teal-50 to-teal-100/40 dark:from-teal-950/60 dark:to-teal-900/20"
          cardTo="bg-teal-300/30 dark:bg-teal-500/20"
          border="border-teal-200/70 dark:border-teal-800/50"
        />
        <KpiCard
          title="Agent Runs"
          value={summary.run_count.toLocaleString()}
          sub="last 7 days"
          icon={<Zap className="h-5 w-5 text-violet-600 dark:text-violet-300" />}
          cardFrom="from-violet-50 to-violet-100/40 dark:from-violet-950/60 dark:to-violet-900/20"
          cardTo="bg-violet-300/30 dark:bg-violet-500/20"
          border="border-violet-200/70 dark:border-violet-800/50"
        />
        <KpiCard
          title="Avg Cost / Run"
          value={avg}
          icon={<Hash className="h-5 w-5 text-indigo-600 dark:text-indigo-300" />}
          cardFrom="from-indigo-50 to-indigo-100/40 dark:from-indigo-950/60 dark:to-indigo-900/20"
          cardTo="bg-indigo-300/30 dark:bg-indigo-500/20"
          border="border-indigo-200/70 dark:border-indigo-800/50"
        />
        <KpiCard
          title="Total Tokens"
          value={formatTokens(tokens)}
          sub={inputPct ? `${inputPct}% input` : undefined}
          icon={<Cpu className="h-5 w-5 text-cyan-600 dark:text-cyan-300" />}
          cardFrom="from-cyan-50 to-cyan-100/40 dark:from-cyan-950/60 dark:to-cyan-900/20"
          cardTo="bg-cyan-300/30 dark:bg-cyan-500/20"
          border="border-cyan-200/70 dark:border-cyan-800/50"
        />
      </div>

      {/* ── Spend over time ── */}
      <Card className="overflow-hidden border-slate-200/60 dark:border-slate-700/60">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-base font-semibold">Spend Over Time</CardTitle>
            <p className="mt-0.5 text-xs text-muted-foreground">Daily — last 7 days · dashed line = average</p>
          </div>
          <Link
            href="/analytics"
            className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-teal-600 transition-colors hover:bg-teal-50 dark:text-teal-400 dark:hover:bg-teal-950/40"
          >
            Full analytics <ArrowRight className="h-3 w-3" />
          </Link>
        </CardHeader>
        <CardContent className="pb-4 pt-0">
          <DashboardAreaChart data={spendTime} />
        </CardContent>
      </Card>

      {/* ── Model + Feature row ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="border-slate-200/60 dark:border-slate-700/60">
          <CardHeader className="pb-1">
            <CardTitle className="text-base font-semibold">Spend by Model</CardTitle>
            <p className="text-xs text-muted-foreground">Distribution across AI providers</p>
          </CardHeader>
          <CardContent>
            <ModelDonutChart items={spendModel.items} />
          </CardContent>
        </Card>

        <Card className="border-slate-200/60 dark:border-slate-700/60">
          <CardHeader className="pb-1">
            <CardTitle className="text-base font-semibold">Spend by Feature</CardTitle>
            <p className="text-xs text-muted-foreground">Top feature tags by cost</p>
          </CardHeader>
          <CardContent>
            <FeatureBarsChart items={spendFeature.items} />
          </CardContent>
        </Card>
      </div>

      {/* ── Recent runs ── */}
      <Card className="overflow-hidden border-slate-200/60 dark:border-slate-700/60">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-base font-semibold">Recent Runs</CardTitle>
            <p className="mt-0.5 text-xs text-muted-foreground">Latest agent runs</p>
          </div>
          <Link
            href="/runs"
            className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-teal-600 transition-colors hover:bg-teal-50 dark:text-teal-400 dark:hover:bg-teal-950/40"
          >
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          {recentRuns.items.length === 0 ? (
            <p className="px-5 py-10 text-center text-sm text-muted-foreground">No runs yet</p>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {recentRuns.items.map(run => (
                <Link
                  key={run.id}
                  href={`/runs/${run.id}`}
                  className="group flex items-center gap-4 px-5 py-3 transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                >
                  <code className="w-28 shrink-0 font-mono text-xs text-indigo-600 group-hover:underline dark:text-indigo-400">
                    {truncateId(run.id, 12)}
                  </code>
                  <RunStatusBadge status={run.status} />
                  <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
                    {run.feature_tag ?? '—'}
                  </span>
                  <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
                    {run.primary_model ?? '—'}
                  </span>
                  <span className="w-20 text-right font-mono text-xs font-medium">
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

// ── Page ──────────────────────────────────────────────────────────────────────

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-32 rounded-2xl" />)}
      </div>
      <Skeleton className="h-80 rounded-2xl" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
      <Skeleton className="h-72 rounded-2xl" />
    </div>
  )
}

export default async function DashboardPage() {
  const session = await getServerSession(authOptions)
  const s = session as Record<string, unknown> | null
  const tenantRole = s?.tenantRole as string | undefined
  const isPlatformAdmin = s?.isPlatformAdmin as boolean | undefined
  const workspaceName = s?.workspaceName as string | undefined
  const isOrgAdmin = isPlatformAdmin || tenantRole === 'org_admin'

  const dateStr = new Date().toLocaleDateString([], {
    weekday: 'long', month: 'long', day: 'numeric',
  })

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          {workspaceName && (
            <div className="flex items-center gap-2 mb-1">
              <span className="rounded-full bg-teal-100 px-2.5 py-0.5 text-[11px] font-semibold text-teal-700 dark:bg-teal-900/40 dark:text-teal-300">
                {workspaceName}
              </span>
            </div>
          )}
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">{dateStr} · Last 7 days</p>
        </div>
        <div className="hidden sm:flex items-center gap-4">
          {isOrgAdmin && (
            <Link
              href="/organization/dashboard"
              className="flex items-center gap-1 rounded-lg border border-violet-200 bg-violet-50 px-3 py-1.5 text-sm font-medium text-violet-700 transition-colors hover:bg-violet-100 dark:border-violet-800 dark:bg-violet-900/20 dark:text-violet-300 dark:hover:bg-violet-900/40"
            >
              Global Dashboard →
            </Link>
          )}
        </div>
      </div>
      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardContent />
      </Suspense>
    </div>
  )
}
