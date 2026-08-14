import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import {
  getBillingPeriod,
  getPeriodBreakdown,
  getReconciliation,
  listBillingAdjustments,
} from '@/lib/api'
import BillingPeriodDetailClient from '@/components/billing/BillingPeriodDetailClient'
import type { BillingAdjustmentList, PeriodBreakdown, ReconciliationResult } from '@/types/api'

export default async function BillingPeriodDetailPage({
  params,
}: {
  params: { period_id: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let period
  try {
    period = await getBillingPeriod(session.apiKey, params.period_id)
  } catch {
    notFound()
  }

  let reconciliation: ReconciliationResult | null = null
  let breakdown: PeriodBreakdown | null = null
  let adjustments: BillingAdjustmentList = {
    items: [],
    total_credits_usd: '0',
    total_surcharges_usd: '0',
    net_adjustment_usd: '0',
  }

  await Promise.allSettled([
    getReconciliation(session.apiKey, params.period_id).then((result) => {
      reconciliation = result
    }),
    getPeriodBreakdown(session.apiKey, params.period_id).then((result) => {
      breakdown = result
    }),
    listBillingAdjustments(session.apiKey, params.period_id).then((result) => {
      adjustments = result
    }),
  ])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link
          href="/billing"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
        >
          <ChevronLeft className="h-4 w-4" />
          Billing
        </Link>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            {period.period_start} - {period.period_end}
          </h1>
          <p className="mt-0.5 font-mono text-xs text-gray-400">{params.period_id}</p>
        </div>
      </div>

      <BillingPeriodDetailClient
        apiKey={session.apiKey}
        period={period}
        reconciliation={reconciliation}
        breakdown={breakdown}
        adjustments={adjustments}
      />
    </div>
  )
}
