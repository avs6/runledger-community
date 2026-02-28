import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getReconciliation, getPeriodBreakdown } from '@/lib/api'
import ReconciliationPanel from '@/components/billing/ReconciliationPanel'
import BreakdownTable from '@/components/billing/BreakdownTable'

export default async function BillingPeriodDetailPage({
  params,
}: {
  params: { period_id: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let reconciliation, breakdown
  try {
    ;[reconciliation, breakdown] = await Promise.all([
      getReconciliation(session.apiKey, params.period_id),
      getPeriodBreakdown(session.apiKey, params.period_id),
    ])
  } catch {
    notFound()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link
          href="/billing"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
        >
          <ChevronLeft className="h-4 w-4" />
          Billing
        </Link>
      </div>

      <div>
        <h1 className="text-xl font-semibold text-gray-900">Billing Period Detail</h1>
        <p className="mt-0.5 font-mono text-xs text-gray-400">{params.period_id}</p>
      </div>

      <ReconciliationPanel result={reconciliation} />
      <BreakdownTable breakdown={breakdown} />
    </div>
  )
}
