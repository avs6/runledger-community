'use client'

import { useMemo } from 'react'
import Link from 'next/link'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import type { PeriodBreakdown } from '@/types/api'

interface Props {
  breakdown: PeriodBreakdown
}

function money(value: string) {
  return `$${Number.parseFloat(value).toFixed(4)}`
}

interface BreakdownRow {
  key: string
  application: string
  end_user_id: string | null
  cost_usd: string
  run_count: number
}

export default function BreakdownTable({ breakdown }: Props) {
  // One row per application and end user: sortable, searchable and exportable.
  const rows: BreakdownRow[] = useMemo(
    () =>
      breakdown.by_application.flatMap((app, i) =>
        app.users.map((user, j) => ({
          key: `${app.application_id ?? `app-${i}`}-${j}`,
          application: app.application_id ?? 'No application',
          end_user_id: user.end_user_id,
          cost_usd: user.cost_usd,
          run_count: user.run_count,
        }))
      ),
    [breakdown]
  )

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Gross</p>
          <p className="mt-2 font-mono text-xl text-slate-900 dark:text-white">{money(breakdown.gross_cost_usd)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Adjustments</p>
          <p className="mt-2 font-mono text-xl text-slate-900 dark:text-white">{money(breakdown.total_adjustments_usd)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Net</p>
          <p className="mt-2 font-mono text-xl text-slate-900 dark:text-white">{money(breakdown.net_cost_usd)}</p>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-slate-800">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-slate-100">Cost Breakdown</h3>
          <span className="font-mono text-sm font-medium text-gray-700 dark:text-slate-300">
            Total: {money(breakdown.gross_cost_usd)}
          </span>
        </div>

        {rows.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500 dark:text-slate-400">No usage data for this period.</p>
        ) : (
          <div className="p-3">
            <DataTable
              label="Cost breakdown by application and user"
              rows={rows}
              rowKey={(row) => row.key}
              urlPrefix="bd_"
              csvFileName="period-breakdown.csv"
              searchPlaceholder="Search application or user"
              columns={[
                { key: 'application', header: 'Application', sortable: true },
                {
                  key: 'end_user_id',
                  header: 'End user',
                  sortable: true,
                  value: (row) => row.end_user_id ?? '',
                  render: (row) =>
                    row.end_user_id ? (
                      <Link
                        href={`/runs?end_user_id=${encodeURIComponent(row.end_user_id)}`}
                        className="text-indigo-600 hover:underline dark:text-indigo-400"
                      >
                        {row.end_user_id}
                      </Link>
                    ) : (
                      <span className="italic text-gray-400">anonymous</span>
                    ),
                },
                {
                  key: 'cost_usd',
                  header: 'Cost (USD)',
                  sortable: true,
                  value: (row) => Number(row.cost_usd),
                  render: (row) => <span className="font-mono">{money(row.cost_usd)}</span>,
                },
                { key: 'run_count', header: 'Runs', sortable: true },
              ] satisfies DataTableColumn<BreakdownRow>[]}
            />
          </div>
        )}
      </div>

      {breakdown.adjustments.length ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Adjustments included in net cost</h3>
          <div className="mt-3 grid gap-2">
            {breakdown.adjustments.map((item) => (
              <div key={item.id} className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
                <div>
                  <div className="font-medium text-slate-900 dark:text-white">{item.adjustment_type}</div>
                  <div className="text-xs text-slate-500">{item.description || item.reference_id || 'No description'}</div>
                </div>
                <div className="font-mono text-slate-900 dark:text-white">{money(item.amount_usd)}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
