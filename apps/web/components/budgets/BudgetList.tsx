'use client'

import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import type { Budget } from '@/types/api'
import { deleteBudget } from '@/lib/api'

interface Props {
  items: Budget[]
  apiKey: string
  onDeleted: (id: string) => void
}

const ACTION_COLOURS: Record<string, string> = {
  block: 'bg-red-100 text-red-700',
  notify: 'bg-yellow-100 text-yellow-700',
  downgrade: 'bg-blue-100 text-blue-700',
}

export default function BudgetList({ items, apiKey, onDeleted }: Props) {
  const [deleting, setDeleting] = useState<string | null>(null)

  async function handleDelete(id: string) {
    if (!confirm('Deactivate this budget?')) return
    setDeleting(id)
    try {
      await deleteBudget(apiKey, id)
      onDeleted(id)
    } catch (err) {
      alert('Failed to delete budget')
      console.error(err)
    } finally {
      setDeleting(null)
    }
  }

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500">
        No budgets yet. Create one to start enforcing spend limits.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Scope</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Period</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600">Limit</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 w-48">Spend</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Action</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {items.map((b) => {
            const pct = Math.min(100, parseFloat(b.pct_used))
            const barColour =
              pct >= 100
                ? 'bg-red-500'
                : pct >= 80
                  ? 'bg-yellow-400'
                  : 'bg-indigo-500'

            return (
              <tr key={b.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <span className="font-medium capitalize">
                    {b.scope_type.replace('_', ' ')}
                  </span>
                  {b.scope_id && (
                    <span className="ml-1.5 text-gray-400">({b.scope_id})</span>
                  )}
                </td>
                <td className="px-4 py-3 capitalize text-gray-600">{b.period_type}</td>
                <td className="px-4 py-3 text-right tabular-nums">
                  ${parseFloat(b.limit_usd).toFixed(2)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-32 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className={`h-full rounded-full ${barColour}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="tabular-nums text-gray-600">
                      ${parseFloat(b.current_spend_usd).toFixed(4)}{' '}
                      <span className="text-gray-400">({pct.toFixed(0)}%)</span>
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ACTION_COLOURS[b.action] ?? 'bg-gray-100 text-gray-600'}`}
                  >
                    {b.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => handleDelete(b.id)}
                    disabled={deleting === b.id}
                    className="text-gray-400 hover:text-red-500 disabled:opacity-40"
                    title="Deactivate"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
