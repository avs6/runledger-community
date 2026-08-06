'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { getBillingSummary, exportBilling } from '@/lib/api'
import type { BillingPeriodSummary } from '@/types/api'

function money(v: number) {
  if (v >= 1) return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  if (v >= 0.001) return `$${v.toFixed(4)}`
  return `$${v.toFixed(6)}`
}

export default function BillingSummaryPage() {
  const { data: session } = useSession()
  const [periods, setPeriods] = useState<BillingPeriodSummary[]>([])
  const [months, setMonths] = useState(6)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)

  const apiKey = (session as any)?.apiKey as string | undefined

  async function load() {
    if (!apiKey) return
    setLoading(true)
    try {
      const data = await getBillingSummary(apiKey, months)
      setPeriods(data.periods)
    } catch { /* empty */ }
    setLoading(false)
  }

  useEffect(() => { load() }, [apiKey, months]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleExport(format: 'csv' | 'json') {
    if (!apiKey) return
    setExporting(true)
    try {
      const blob = await exportBilling(apiKey, format, months)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `billing-export.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch { /* empty */ }
    setExporting(false)
  }

  if (!apiKey) return null

  const totalCost = periods.reduce((s, p) => s + p.total_cost_usd, 0)
  const totalBillable = periods.reduce((s, p) => s + p.billable_cost_usd, 0)
  const totalNonBillable = periods.reduce((s, p) => s + p.non_billable_cost_usd, 0)
  const totalCalls = periods.reduce((s, p) => s + p.total_calls, 0)
  const maxCost = Math.max(...periods.map((p) => p.total_cost_usd), 0.01)

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-[-0.04em] text-slate-950 dark:text-slate-50">
            Billing Summary
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Billable vs non-billable cost breakdown with export.
          </p>
        </div>
        <div className="flex items-center gap-2">
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
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Export CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            disabled={exporting}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
          >
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
          <div>
            <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">Cost by Period</h2>
            <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
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
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                <tr>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Period</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Total Cost</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Billable</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Non-Billable</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Total Calls</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Billable %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {periods.map((p) => {
                  const pct = p.total_cost_usd > 0 ? ((p.billable_cost_usd / p.total_cost_usd) * 100).toFixed(1) : '0.0'
                  return (
                    <tr key={p.period} className="bg-white dark:bg-slate-900">
                      <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{p.period}</td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{money(p.total_cost_usd)}</td>
                      <td className="px-4 py-3 text-emerald-600 dark:text-emerald-400">{money(p.billable_cost_usd)}</td>
                      <td className="px-4 py-3 text-amber-600 dark:text-amber-400">{money(p.non_billable_cost_usd)}</td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{p.total_calls.toLocaleString()}</td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{pct}%</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
