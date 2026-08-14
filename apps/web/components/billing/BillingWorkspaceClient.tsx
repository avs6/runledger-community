'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Plus, Receipt, Settings2 } from 'lucide-react'
import type { BillingPeriod, BillingSummaryResponse } from '@/types/api'
import BillingPeriodTable from '@/components/billing/BillingPeriodTable'
import BillingSummaryPanel from '@/components/billing/BillingSummaryPanel'
import CreatePeriodModal from '@/components/billing/CreatePeriodModal'
import SharedCostPoliciesPanel from '@/components/billing/SharedCostPoliciesPanel'

interface Props {
  apiKey: string
  initialPeriods: BillingPeriod[]
  summary: BillingSummaryResponse
  initialTab: 'summary' | 'periods' | 'shared-costs'
  initialMonths: number
}

function money(value: number) {
  if (value >= 1) return `$${value.toFixed(2)}`
  if (value >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

export default function BillingWorkspaceClient({
  apiKey,
  initialPeriods,
  summary,
  initialTab,
  initialMonths,
}: Props) {
  const [periods, setPeriods] = useState(initialPeriods)
  const [showCreate, setShowCreate] = useState(false)

  const totalCost = summary.periods.reduce((sum, period) => sum + period.total_cost_usd, 0)
  const totalCalls = summary.periods.reduce((sum, period) => sum + period.total_calls, 0)
  const billableShare = totalCost > 0
    ? (summary.periods.reduce((sum, period) => sum + period.billable_cost_usd, 0) / totalCost) * 100
    : 0

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Recent Cost</p>
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
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Operator Flow</p>
          <p className="mt-2 text-lg font-semibold text-slate-900 dark:text-white">Periods + reconciliation + shared costs</p>
          <p className="mt-2 text-sm text-slate-500">Billing now owns period operations instead of only summary/export views.</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <Link
            href="/billing"
            className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
              initialTab === 'periods' ? 'bg-blue-600 text-white shadow-sm' : 'border border-slate-200 bg-white text-slate-600 hover:bg-blue-50'
            }`}
          >
            Billing Periods
          </Link>
          <Link
            href={`/billing?tab=summary&months=${initialMonths}`}
            className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
              initialTab === 'summary' ? 'bg-blue-600 text-white shadow-sm' : 'border border-slate-200 bg-white text-slate-600 hover:bg-blue-50'
            }`}
          >
            Summary
          </Link>
          <Link
            href="/billing?tab=shared-costs"
            className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
              initialTab === 'shared-costs' ? 'bg-blue-600 text-white shadow-sm' : 'border border-slate-200 bg-white text-slate-600 hover:bg-blue-50'
            }`}
          >
            Shared Costs
          </Link>
        </div>
        {initialTab === 'periods' ? (
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            <Plus className="h-4 w-4" />
            New period
          </button>
        ) : null}
      </div>

      {initialTab === 'summary' ? (
        <BillingSummaryPanel apiKey={apiKey} initialMonths={initialMonths} />
      ) : null}

      {initialTab === 'periods' ? (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="flex items-center gap-2 text-slate-900 dark:text-white">
                <Receipt className="h-4 w-4 text-blue-600" />
                <h2 className="text-sm font-semibold">Period operations</h2>
              </div>
              <p className="mt-2 text-sm text-slate-500">
                Open a period, close it when finance is ready, then drill into reconciliation, breakdown, adjustments, and exports from the detail view.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="flex items-center gap-2 text-slate-900 dark:text-white">
                <Settings2 className="h-4 w-4 text-emerald-600" />
                <h2 className="text-sm font-semibold">Downstream handoff</h2>
              </div>
              <p className="mt-2 text-sm text-slate-500">
                Use shared-cost policies to prepare for chargeback, and use the period detail page to verify period quality before close.
              </p>
            </div>
          </div>
          <BillingPeriodTable
            items={periods}
            apiKey={apiKey}
          />
        </div>
      ) : null}

      {initialTab === 'shared-costs' ? <SharedCostPoliciesPanel apiKey={apiKey} defaultPoolUsd={String(totalCost.toFixed(2))} /> : null}

      {showCreate ? (
        <CreatePeriodModal
          apiKey={apiKey}
          onCreated={(period) => setPeriods((current) => [period, ...current])}
          onClose={() => setShowCreate(false)}
        />
      ) : null}
    </div>
  )
}
