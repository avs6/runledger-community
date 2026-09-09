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
  accessGroupId?: string
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
  accessGroupId,
}: Props) {
  const [periods, setPeriods] = useState(initialPeriods)
  const [showCreate, setShowCreate] = useState(false)

  const totalCost = summary.periods.reduce((sum, period) => sum + period.total_cost_usd, 0)
  const totalCalls = summary.periods.reduce((sum, period) => sum + period.total_calls, 0)
  const billableShare = totalCost > 0
    ? (summary.periods.reduce((sum, period) => sum + period.billable_cost_usd, 0) / totalCost) * 100
    : 0

  const accessGroupQuery = accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''

  return (
    <div className="space-y-5">
      {/* KPI cards */}
      <div className="grid gap-3 md:grid-cols-4">
        {[
          { label: 'Recent Cost', value: money(totalCost), sub: null },
          { label: 'Total Calls', value: totalCalls.toLocaleString(), sub: null },
          { label: 'Billable Share', value: `${billableShare.toFixed(1)}%`, sub: null },
          { label: 'Operator Flow', value: 'Periods + Reconciliation', sub: 'Billing owns period operations.' },
        ].map(({ label, value, sub }) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
            <p className="mt-1.5 text-xl font-bold text-slate-900 dark:text-white">{value}</p>
            {sub && <p className="mt-1 text-[11px] text-slate-500">{sub}</p>}
          </div>
        ))}
      </div>

      {accessGroupId && (
        <div className="rounded-lg border border-blue-200 bg-blue-50/70 px-3 py-2 text-[11px] text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100">
          Billing periods are filtered to activity attributable to the selected access group.
        </div>
      )}

      {/* Tab bar + action */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="rounded-lg bg-slate-100 p-1 dark:bg-slate-800/80">
          <nav className="flex gap-1">
            <Link
              href={accessGroupId ? `/billing?access_group_id=${encodeURIComponent(accessGroupId)}` : '/billing'}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                initialTab === 'periods'
                  ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              Billing Periods
            </Link>
            <Link
              href={`/billing?tab=summary&months=${initialMonths}${accessGroupQuery}`}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                initialTab === 'summary'
                  ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              Summary
            </Link>
            <Link
              href={`/billing?tab=shared-costs${accessGroupQuery}`}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                initialTab === 'shared-costs'
                  ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              Shared Costs
            </Link>
          </nav>
        </div>
        {initialTab === 'periods' && (
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:brightness-110"
          >
            <Plus className="h-3.5 w-3.5" /> New Period
          </button>
        )}
      </div>

      {initialTab === 'summary' && (
        <BillingSummaryPanel apiKey={apiKey} initialMonths={initialMonths} />
      )}

      {initialTab === 'periods' && (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="flex items-center gap-2">
                <Receipt className="h-4 w-4 text-emerald-500" />
                <h2 className="text-xs font-bold text-slate-900 dark:text-white">Period Operations</h2>
              </div>
              <p className="mt-2 text-[11px] text-slate-500">
                Open a period, close it when finance is ready, then drill into reconciliation, breakdown, adjustments, and exports.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="flex items-center gap-2">
                <Settings2 className="h-4 w-4 text-teal-500" />
                <h2 className="text-xs font-bold text-slate-900 dark:text-white">Downstream Handoff</h2>
              </div>
              <p className="mt-2 text-[11px] text-slate-500">
                Use shared-cost policies for chargeback prep, and the period detail page to verify quality before close.
              </p>
            </div>
          </div>
          <BillingPeriodTable
            items={periods}
            apiKey={apiKey}
            accessGroupId={accessGroupId}
          />
        </div>
      )}

      {initialTab === 'shared-costs' && <SharedCostPoliciesPanel apiKey={apiKey} defaultPoolUsd={String(totalCost.toFixed(2))} />}

      {showCreate && (
        <CreatePeriodModal
          apiKey={apiKey}
          onCreated={(period) => setPeriods((current) => [period, ...current])}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  )
}
