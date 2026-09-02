import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getUserSpend, getBudgetDetailObservePosture, getBudgetControlObservePosture } from '@/lib/api'
import SpendOverTimeChart from '@/components/analytics/SpendOverTimeChart'
import SpendByModelChart from '@/components/analytics/SpendByModelChart'
import SpendByFeatureChart from '@/components/analytics/SpendByFeatureChart'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChevronLeft, Search, Route, DollarSign } from 'lucide-react'

function fmt$$(value: string): string {
  const n = parseFloat(value)
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

interface PageProps {
  params: { end_user_id: string }
  searchParams: { from?: string; to?: string }
}

function defaultWindow() {
  const to = new Date()
  const from = new Date(to.getTime() - 30 * 24 * 3_600_000)
  return { from: from.toISOString(), to: to.toISOString() }
}

export default async function UserSpendPage({ params, searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const userId = decodeURIComponent(params.end_user_id)
  const window = {
    from: searchParams.from ?? defaultWindow().from,
    to: searchParams.to ?? defaultWindow().to,
  }

  let detail
  try {
    detail = await getUserSpend(session.apiKey, userId, window)
  } catch {
    notFound()
  }

  const budgetPosture = await getBudgetDetailObservePosture(session.apiKey).catch(() => null)
  const budgetControlPosture = await getBudgetControlObservePosture(session.apiKey).catch(() => null)

  const spendOverTime = {
    granularity: 'daily',
    points: detail.spend_over_time,
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link
          href="/analytics/users"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
        >
          <ChevronLeft className="h-4 w-4" />
          Top Spenders
        </Link>
      </div>

      <div>
        <h1 className="text-xl font-semibold">{userId}</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Last active: {fmtDate(detail.last_active)}
        </p>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: 'Total Spend', value: fmt$$(detail.cost_usd) },
          { label: 'Runs', value: detail.run_count.toLocaleString() },
          { label: 'Calls', value: detail.call_count.toLocaleString() },
          { label: 'Avg / Run', value: fmt$$(detail.avg_cost_per_run) },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-xl border bg-card p-4 shadow-sm">
            <p className="text-xs font-medium text-muted-foreground">{label}</p>
            <p className="mt-1 text-2xl font-bold tracking-tight">{value}</p>
          </div>
        ))}
      </div>

      {budgetPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">Budget Context</p>
          </div>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Users with Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetPosture.user_budget_context.users_with_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetPosture.budget_context.active_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">30d Spend</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${budgetPosture.spend_context.total_spend_30d.toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
              <p className={`mt-1 text-lg font-semibold ${budgetPosture.budget_context.breach_count > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetPosture.budget_context.breach_count}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href={`/budgets?scope_type=end_user&scope_id=${encodeURIComponent(userId)}`} className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">This User&apos;s Budgets</Link>
            <Link href="/billing" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Billing</Link>
            <Link href="/chargeback" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Chargeback</Link>
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

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Spend Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <SpendOverTimeChart data={spendOverTime} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Models Used</CardTitle>
          </CardHeader>
          <CardContent>
            <SpendByModelChart items={detail.models_used} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Features Used</CardTitle>
          </CardHeader>
          <CardContent>
            <SpendByFeatureChart items={detail.features_used} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Per-User Drilldown</p>
          <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Turn spend into investigation context</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            This page explains how one end user accumulated spend over time and across models or features. Use the linked observability pages when you need the exact requests or routing decisions behind the chart.
          </p>
        </div>
        <Link
          href={`/request-explorer?end_user_id=${encodeURIComponent(userId)}`}
          className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/60 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-400 dark:hover:bg-slate-800"
        >
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-slate-950 dark:text-white">Open Request Explorer</h2>
            <Search className="h-5 w-5 text-blue-600" />
          </div>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Filter the request log to this end user and inspect the exact runs, prompts, route choices, tools, and outcomes.
          </p>
        </Link>
        <Link
          href={`/request-flow?scope=workspace&mode=user-intent-model&metric=cost`}
          className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/60 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-400 dark:hover:bg-slate-800"
        >
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-slate-950 dark:text-white">View User Cost Flow</h2>
            <Route className="h-5 w-5 text-blue-600" />
          </div>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Compare this user’s activity against the broader user-to-model flow to see whether cost concentration is isolated or systemic.
          </p>
        </Link>
      </div>

      <Link
        href="/outcomes"
        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-blue-400 dark:hover:bg-slate-800 dark:hover:text-blue-300"
      >
        Compare with Outcomes &amp; ROI <DollarSign className="h-4 w-4" />
      </Link>
    </div>
  )
}
