'use client'

import { useEffect, useState } from 'react'
import { apiErrorMessage, getCostCenterReport } from '@/lib/api'
import type { CostCenterReport } from '@/types/api'

function money(value: string | number) {
  return `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/**
 * Cost per cost center for one month: chargeback rules applied to billable cost
 * (direct), shared-cost pools applied to the month (shared), and the billable cost
 * no rule covers (unassigned).
 */
export default function CostCenterReportPanel({ apiKey, period }: { apiKey: string; period: string }) {
  const [report, setReport] = useState<CostCenterReport | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setReport(null)
    getCostCenterReport(apiKey, period)
      .then((r) => !cancelled && setReport(r))
      .catch((err) => !cancelled && setError(apiErrorMessage(err, 'Failed to load the cost-center report')))
    return () => {
      cancelled = true
    }
  }, [apiKey, period])

  if (error) return <p className="text-xs text-rose-600">{error}</p>
  if (!report) return <p className="text-xs text-slate-500">Loading cost-center report…</p>

  const assignedPct = Number(report.total_billable_usd) > 0
    ? (Number(report.assigned_usd) / Number(report.total_billable_usd)) * 100
    : 0

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ['Billable cost', money(report.total_billable_usd)],
          ['Assigned by rules', `${money(report.assigned_usd)} · ${assignedPct.toFixed(0)} %`],
          ['Unassigned', money(report.unassigned_usd)],
          ['Shared costs applied', money(report.shared_usd)],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900">
            <p className="text-[10px] uppercase tracking-widest text-slate-400">{label}</p>
            <p className="text-sm font-semibold text-slate-900 dark:text-white">{value}</p>
          </div>
        ))}
      </div>
      {report.rows.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 py-6 text-center text-xs text-slate-500 dark:border-slate-700">
          Nothing is charged to a cost center for {report.period}. Add rules on the Rules tab or apply a shared-cost policy on Billing.
        </p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                {['Cost center', 'Code', 'From rules', 'Shared', 'Total'].map((h) => (
                  <th key={h} className={`px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500 ${['From rules', 'Shared', 'Total'].includes(h) ? 'text-right' : 'text-left'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {report.rows.map((row) => (
                <tr key={row.cost_center_id} className="bg-white dark:bg-slate-900">
                  <td className="px-4 py-2.5 font-semibold text-slate-900 dark:text-white">{row.name}</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">{row.code ?? '—'}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{money(row.direct_usd)}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{money(row.shared_usd)}</td>
                  <td className="px-4 py-2.5 text-right font-mono font-semibold">{money(row.total_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {report.rule_dimension && (
        <p className="text-[10px] text-slate-500">Rules map by {report.rule_dimension.replace('_', ' ')}. Totals use billable cost: priced calls marked billable, whatever their status.</p>
      )}
    </div>
  )
}
