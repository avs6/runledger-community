'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { PeriodBreakdown } from '@/types/api'
import { ChevronDown, ChevronRight } from 'lucide-react'

interface Props {
  breakdown: PeriodBreakdown
}

export default function BreakdownTable({ breakdown }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-800">Cost Breakdown</h3>
        <span className="font-mono text-sm font-medium text-gray-700">
          Total: ${parseFloat(breakdown.total_cost_usd).toFixed(4)}
        </span>
      </div>

      {breakdown.by_application.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-500">No usage data for this period.</p>
      ) : (
        <table className="min-w-full divide-y divide-gray-100 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-gray-600">Application / User</th>
              <th className="px-4 py-2 text-right font-medium text-gray-600">Cost (USD)</th>
              <th className="px-4 py-2 text-right font-medium text-gray-600">Runs</th>
              <th className="w-20 px-4 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {breakdown.by_application.map((app, ai) => {
              const appKey = app.application_id ?? `__none_${ai}`
              const isExpanded = expanded.has(appKey)
              return [
                <tr
                  key={appKey}
                  className="cursor-pointer bg-gray-50 hover:bg-gray-100"
                  onClick={() => toggle(appKey)}
                >
                  <td className="flex items-center gap-1 px-4 py-2.5 font-medium text-gray-800">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-gray-500" />
                    )}
                    {app.application_id ?? 'No application'}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-gray-700">
                    ${parseFloat(app.cost_usd).toFixed(4)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-gray-600">
                    {app.users.reduce((s, u) => s + u.run_count, 0)}
                  </td>
                  <td />
                </tr>,
                ...(isExpanded
                  ? app.users.map((user, ui) => (
                      <tr key={`${appKey}-${ui}`} className="hover:bg-gray-50">
                        <td className="py-2 pl-10 pr-4 text-gray-600">
                          {user.end_user_id ? (
                            <Link
                              href={`/runs?end_user_id=${encodeURIComponent(user.end_user_id)}`}
                              className="text-indigo-600 hover:underline"
                            >
                              {user.end_user_id}
                            </Link>
                          ) : (
                            <span className="italic text-gray-400">anonymous</span>
                          )}
                        </td>
                        <td className="py-2 pr-4 text-right font-mono text-gray-700">
                          ${parseFloat(user.cost_usd).toFixed(4)}
                        </td>
                        <td className="py-2 pr-4 text-right text-gray-600">{user.run_count}</td>
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
  )
}
