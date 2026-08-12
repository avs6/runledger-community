import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getBillingPeriods, getBillingSummary } from '@/lib/api'
import BillingPeriodTable from '@/components/billing/BillingPeriodTable'

function money(value: number) {
  if (value >= 1) return `$${value.toFixed(2)}`
  if (value >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

export default async function BillingPage() {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  const [periods, summary] = await Promise.all([
    getBillingPeriods(session.apiKey),
    getBillingSummary(session.apiKey, 6).catch(() => ({ workspace_id: '', periods: [] })),
  ])
  const totalCost = summary.periods.reduce((sum, period) => sum + period.total_cost_usd, 0)
  const totalCalls = summary.periods.reduce((sum, period) => sum + period.total_calls, 0)
  const billableShare = totalCost > 0
    ? (summary.periods.reduce((sum, period) => sum + period.billable_cost_usd, 0) / totalCost) * 100
    : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Billing</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          View billing periods, export-ready summaries, and billable vs non-billable usage in one place.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">6-Month Cost</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{money(totalCost)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Total Calls</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{totalCalls.toLocaleString()}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Billable Share</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{billableShare.toFixed(1)}%</p>
        </div>
        <Link href="/billing-summary" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/40 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Summary View</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">Open</p>
          <p className="mt-2 text-sm text-slate-500">Dive into period rollups, charts, and export controls.</p>
        </Link>
      </div>

      <BillingPeriodTable items={periods.items} apiKey={session.apiKey} />
    </div>
  )
}
