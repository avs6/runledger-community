import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ChevronLeft, FileSpreadsheet, Shield } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getBillingPeriod, getPeriodBreakdown, getReconciliation, listBillingAdjustments } from '@/lib/api'
import BillingPeriodDetailClient from '@/components/billing/BillingPeriodDetailClient'
import type { BillingAdjustmentList, PeriodBreakdown, ReconciliationResult } from '@/types/api'
import { num } from '@/lib/utils'

export default async function BillingPeriodDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ period_id: string }>
  searchParams?: Promise<{ access_group_id?: string; api_key_id?: string }>
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const { period_id } = await params
  const sp = (await searchParams) ?? {}
  const accessGroupId = sp.access_group_id
  const apiKeyId = sp.api_key_id

  let period
  try {
    period = await getBillingPeriod(session.apiKey, period_id)
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
    getReconciliation(session.apiKey, period_id, {
      access_group_id: accessGroupId,
      api_key_id: apiKeyId,
    }).then((result) => {
      reconciliation = result
    }),
    getPeriodBreakdown(session.apiKey, period_id, {
      access_group_id: accessGroupId,
      api_key_id: apiKeyId,
    }).then((result) => {
      breakdown = result
    }),
    listBillingAdjustments(session.apiKey, period_id).then((result) => {
      adjustments = result
    }),
  ])


  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <Link
          href={
            accessGroupId
              ? `/billing?access_group_id=${encodeURIComponent(accessGroupId)}`
              : apiKeyId
                ? `/api-keys/${encodeURIComponent(apiKeyId)}`
                : '/billing'
          }
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Billing
        </Link>
      </div>

      {/* ── Hero ── */}
      <section className="relative isolate overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-emerald-950 to-teal-950 px-6 py-7 text-white shadow-lg">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(16,185,129,0.15),transparent_60%)]" />
        <div className="relative">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight">{period.period_start} — {period.period_end}</h1>
          </div>
          <p className="mt-1 font-mono text-[10px] text-slate-400">{period_id}</p>
        </div>
      </section>

      {/* ── Context panels ── */}



      <BillingPeriodDetailClient
        apiKey={session.apiKey}
        period={period}
        reconciliation={reconciliation}
        breakdown={breakdown}
        adjustments={adjustments}
        accessGroupId={accessGroupId}
        apiKeyId={apiKeyId}
      />
    </div>
  )
}
