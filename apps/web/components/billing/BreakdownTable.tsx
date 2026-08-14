'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { PeriodBreakdown } from '@/types/api'
import { ChevronDown, ChevronRight } from 'lucide-react'

interface Props {
  breakdown: PeriodBreakdown
}

function money(value: string) {
  return `$${Number.parseFloat(value).toFixed(4)}`
}

export default function BreakdownTable({ breakdown }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

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

        {breakdown.by_application.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500 dark:text-slate-400">No usage data for this period.</p>
        ) : (
          <table className="min-w-full divide-y divide-gray-100 text-sm dark:divide-slate-800">
            <thead className="bg-gray-50 dark:bg-slate-800">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-gray-600 dark:text-slate-300">Application / User</th>
                <th className="px-4 py-2 text-right font-medium text-gray-600 dark:text-slate-300">Cost (USD)</th>
                <th className="px-4 py-2 text-right font-medium text-gray-600 dark:text-slate-300">Runs</th>
                <th className="w-20 px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white dark:divide-slate-800 dark:bg-slate-900">
              {breakdown.by_application.map((app, index) => {
                const appKey = app.application_id ?? `app-${index}`
                const isExpanded = expanded.has(appKey)
                const runCount = app.users.reduce((sum, user) => sum + user.run_count, 0)

                return [
                  <tr
                    key={appKey}
                    className="cursor-pointer bg-gray-50 hover:bg-gray-100 dark:bg-slate-800/60 dark:hover:bg-slate-800"
                    onClick={() => toggle(appKey)}
                  >
                    <td className="flex items-center gap-1 px-4 py-2.5 font-medium text-gray-800 dark:text-slate-100">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-gray-500" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-gray-500" />
                      )}
                      {app.application_id ?? 'No application'}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-700 dark:text-slate-300">
                      {money(app.cost_usd)}
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-600 dark:text-slate-400">{runCount}</td>
                    <td />
                  </tr>,
                  ...(isExpanded
                    ? app.users.map((user, userIndex) => (
                        <tr key={`${appKey}-${userIndex}`} className="hover:bg-gray-50 dark:hover:bg-slate-800/70">
                          <td className="py-2 pl-10 pr-4 text-gray-600 dark:text-slate-300">
                            {user.end_user_id ? (
                              <Link
                                href={`/runs?end_user_id=${encodeURIComponent(user.end_user_id)}`}
                                className="text-indigo-600 hover:underline dark:text-indigo-400"
                              >
                                {user.end_user_id}
                              </Link>
                            ) : (
                              <span className="italic text-gray-400">anonymous</span>
                            )}
                          </td>
                          <td className="py-2 pr-4 text-right font-mono text-gray-700 dark:text-slate-300">
                            {money(user.cost_usd)}
                          </td>
                          <td className="py-2 pr-4 text-right text-gray-600 dark:text-slate-400">{user.run_count}</td>
                          <td />
                        </tr>
                      ))
                    : []),
                ]
              })}
            </tbody>
          </table>
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
