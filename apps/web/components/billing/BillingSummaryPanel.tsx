'use client'

import { useEffect, useState } from 'react'
import { BarChart3, Download, ReceiptText } from 'lucide-react'
import { getBillingSummary, exportBilling } from '@/lib/api'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import type { BillingPeriodSummary } from '@/types/api'

function money(v: number | string) {
  const n = Number(v) || 0
  if (n >= 1) return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

export default function BillingSummaryPanel({
  apiKey,
  initialMonths = 6,
}: {
  apiKey: string
  initialMonths?: number
}) {
  const [periods, setPeriods] = useState<BillingPeriodSummary[]>([])
  const [months, setMonths] = useState(initialMonths)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    let active = true
    async function load() {
      setLoading(true)
      try {
        const data = await getBillingSummary(apiKey, months)
        if (active) setPeriods(data.periods)
      } catch {
        if (active) setPeriods([])
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [apiKey, months])

  async function handleExport(format: 'csv' | 'json') {
    setExporting(true)
    try {
      const blob = await exportBilling(apiKey, format, months)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `billing-summary.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setExporting(false)
    }
  }

  const totalCost = periods.reduce((s, p) => s + p.total_cost_usd, 0)
  const totalBillable = periods.reduce((s, p) => s + p.billable_cost_usd, 0)
  const totalNonBillable = periods.reduce((s, p) => s + p.non_billable_cost_usd, 0)
  const totalCalls = periods.reduce((s, p) => s + p.total_calls, 0)
  const maxCost = Math.max(...periods.map((p) => p.total_cost_usd), 0.01)

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Summary View</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-slate-50">Billing Summary</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Period rollups for billable versus non-billable usage, plus export for reconciliation and downstream finance workflows.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={months}
            onChange={(e) => setMonths(Number(e.target.value))}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          >
            <option value={3}>Last 3 months</option>
            <option value={6}>Last 6 months</option>
            <option value={12}>Last 12 months</option>
          </select>
          <button
            onClick={() => handleExport('csv')}
            disabled={exporting}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            disabled={exporting}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <ReceiptText className="h-4 w-4" />
            Export JSON
          </button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs font-medium text-slate-500">Total Cost</p>
          <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">{money(totalCost)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs font-medium text-slate-500">Billable</p>
          <p className="mt-1 text-2xl font-bold text-emerald-600 dark:text-emerald-400">{money(totalBillable)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs font-medium text-slate-500">Non-Billable</p>
          <p className="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{money(totalNonBillable)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs font-medium text-slate-500">Total Calls</p>
          <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">{totalCalls.toLocaleString()}</p>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">Loading billing data...</p>
      ) : periods.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center dark:border-slate-700 dark:bg-slate-900/50">
          <p className="text-sm text-slate-500">No billing data available yet. Cost data appears after runs are ingested and metered.</p>
        </div>
      ) : (
        <>
          <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-3 flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-blue-600" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Cost by Period</h3>
            </div>
            <div className="flex items-end gap-2" style={{ height: 200 }}>
              {periods.map((p) => {
                const billableH = (p.billable_cost_usd / maxCost) * 180
                const nonBillableH = (p.non_billable_cost_usd / maxCost) * 180
                return (
                  <div key={p.period} className="flex flex-1 flex-col items-center gap-1">
                    <div className="flex w-full flex-col items-center" style={{ height: 180 }}>
                      <div className="mt-auto flex w-full max-w-[40px] flex-col">
                        <div
                          className="w-full rounded-t bg-amber-400 dark:bg-amber-500"
                          style={{ height: Math.max(nonBillableH, 1) }}
                          title={`Non-billable: ${money(p.non_billable_cost_usd)}`}
                        />
                        <div
                          className="w-full rounded-b bg-emerald-500 dark:bg-emerald-400"
                          style={{ height: Math.max(billableH, 1) }}
                          title={`Billable: ${money(p.billable_cost_usd)}`}
                        />
                      </div>
                    </div>
                    <span className="text-[10px] text-slate-500">{p.period}</span>
                  </div>
                )
              })}
            </div>
            <div className="mt-4 flex items-center justify-center gap-6 text-xs text-slate-500">
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-sm bg-emerald-500" />
                Billable
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-sm bg-amber-400" />
                Non-Billable
              </div>
            </div>
          </div>

          <DataTable
            label="Billing summary by month"
            rows={periods}
            rowKey={(p) => p.period}
            urlPrefix="bs_"
            searchable={false}
            csvFileName="billing-summary.csv"
            columns={[
              { key: 'period', header: 'Period', sortable: true },
              { key: 'total_cost_usd', header: 'Total Cost', sortable: true, value: (p) => Number(p.total_cost_usd), render: (p) => money(p.total_cost_usd) },
              { key: 'billable_cost_usd', header: 'Billable', sortable: true, value: (p) => Number(p.billable_cost_usd), render: (p) => <span className="text-emerald-600 dark:text-emerald-400">{money(p.billable_cost_usd)}</span> },
              { key: 'non_billable_cost_usd', header: 'Non-Billable', sortable: true, value: (p) => Number(p.non_billable_cost_usd), render: (p) => <span className="text-amber-600 dark:text-amber-400">{money(p.non_billable_cost_usd)}</span> },
              { key: 'total_calls', header: 'Total Calls', sortable: true, render: (p) => p.total_calls.toLocaleString() },
              {
                key: 'billable_pct',
                header: 'Billable %',
                sortable: true,
                value: (p) => (Number(p.total_cost_usd) > 0 ? (Number(p.billable_cost_usd) / Number(p.total_cost_usd)) * 100 : 0),
                render: (p) => `${(Number(p.total_cost_usd) > 0 ? (Number(p.billable_cost_usd) / Number(p.total_cost_usd)) * 100 : 0).toFixed(1)}%`,
              },
            ] satisfies DataTableColumn<BillingPeriodSummary>[]}
          />
        </>
      )}
    </div>
  )
}
