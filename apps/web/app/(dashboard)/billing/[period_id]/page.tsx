import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ChevronLeft, AlertCircle } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getBillingPeriod, getReconciliation, getPeriodBreakdown } from '@/lib/api'
import BreakdownTable from '@/components/billing/BreakdownTable'
import type { ReconciliationResult, PeriodBreakdown, BillingPeriod } from '@/types/api'

function StatusBadge({ status }: { status: BillingPeriod['status'] }) {
  const cls =
    status === 'open'
      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
      : status === 'closing'
      ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300'
      : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300'
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>
      {status}
    </span>
  )
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800/50 dark:bg-amber-950/30 dark:text-amber-300">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      {message}
    </div>
  )
}

export default async function BillingPeriodDetailPage({
  params,
}: {
  params: { period_id: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  // Fetch the period first — only call notFound() if the period itself is missing.
  let period: BillingPeriod
  try {
    period = await getBillingPeriod(session.apiKey, params.period_id)
  } catch {
    notFound()
  }

  // Reconciliation and breakdown are best-effort — a failure (e.g. no data yet
  // on a freshly-created open period) shows a degraded message, not a 404.
  let reconciliation: ReconciliationResult | null = null
  let breakdown: PeriodBreakdown | null = null
  let reconciliationError: string | null = null
  let breakdownError: string | null = null

  await Promise.allSettled([
    getReconciliation(session.apiKey, params.period_id).then(
      (r) => { reconciliation = r },
      (e: unknown) => { reconciliationError = e instanceof Error ? e.message : 'Failed to load reconciliation' }
    ),
    getPeriodBreakdown(session.apiKey, params.period_id).then(
      (b) => { breakdown = b },
      (e: unknown) => { breakdownError = e instanceof Error ? e.message : 'Failed to load breakdown' }
    ),
  ])

  return (
    <div className="space-y-6">
      {/* Back nav */}
      <div className="flex items-center gap-2">
        <Link
          href="/billing"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
        >
          <ChevronLeft className="h-4 w-4" />
          Billing
        </Link>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            {period!.period_start} — {period!.period_end}
          </h1>
          <p className="mt-0.5 font-mono text-xs text-gray-400">{params.period_id}</p>
        </div>
        <div className="flex items-center gap-3 pt-0.5">
          <StatusBadge status={period!.status} />
          {period!.total_cost_usd != null && (
            <span className="font-mono text-sm font-semibold text-gray-700 dark:text-gray-300">
              ${parseFloat(period!.total_cost_usd).toFixed(4)}
            </span>
          )}
        </div>
      </div>

      {/* Open period hint */}
      {period!.status === 'open' && (
        <div className="rounded-xl border border-blue-200/70 bg-blue-50/60 px-4 py-3 text-sm text-blue-700 dark:border-blue-800/50 dark:bg-blue-950/30 dark:text-blue-300">
          This period is still <strong>open</strong>. Reconciliation and breakdown reflect costs
          accumulated so far. Close the period to lock the totals and generate a signed snapshot.
        </div>
      )}

      {/* Reconciliation */}
      {reconciliationError ? (
        <ErrorCard message={`Reconciliation unavailable: ${reconciliationError}`} />
      ) : reconciliation ? (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Reconciliation</h3>
          <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-x-auto">
            {JSON.stringify(reconciliation, null, 2)}
          </pre>
        </div>
      ) : null}

      {/* Breakdown */}
      {breakdownError ? (
        <ErrorCard message={`Breakdown unavailable: ${breakdownError}`} />
      ) : breakdown ? (
        <BreakdownTable breakdown={breakdown} />
      ) : null}
    </div>
  )
}
