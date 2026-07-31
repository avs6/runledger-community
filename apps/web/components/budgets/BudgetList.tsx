'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import type { Budget } from '@/types/api'
import { deleteBudget } from '@/lib/api'

interface Props {
  items: Budget[]
  apiKey: string
  onDeleted?: (id: string) => void
}

const ACTION_COLOURS: Record<string, string> = {
  block: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  notify: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  downgrade: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
}

export default function BudgetList({ items, apiKey, onDeleted }: Props) {
  const [deleting, setDeleting] = useState<string | null>(null)
  const router = useRouter()

  async function handleDelete(id: string) {
    if (!confirm('Deactivate this budget?')) return
    setDeleting(id)
    try {
      await deleteBudget(apiKey, id)
      onDeleted?.(id)
      router.refresh()
    } catch (err) {
      toast.error('Failed to delete budget')
      console.error(err)
    } finally {
      setDeleting(null)
    }
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white/70 py-12 text-center text-sm text-slate-500 shadow-sm">
        No budgets yet. Create one to start enforcing spend limits.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-300 bg-white/90 shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Scope</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Period</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-600">Limit</th>
            <th className="w-48 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Spend</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">Action</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white/80">
          {items.map((b) => {
            const pct = Math.min(100, parseFloat(b.pct_used))
            const barColour =
              pct >= 100
                ? 'bg-red-500'
                : pct >= 80
                  ? 'bg-yellow-400'
                  : 'bg-indigo-500'

            return (
              <tr key={b.id} className="hover:bg-blue-50/45">
                <td className="px-4 py-3">
                  <span className="font-medium capitalize text-slate-950">
                    {b.scope_type.replace('_', ' ')}
                  </span>
                  {b.scope_id && (
                    <span className="ml-1.5 text-slate-500">({b.scope_id})</span>
                  )}
                </td>
                <td className="px-4 py-3 capitalize text-slate-700">{b.period_type}</td>
                <td className="px-4 py-3 text-right tabular-nums text-slate-950">
                  ${parseFloat(b.limit_usd).toFixed(2)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-32 overflow-hidden rounded-full bg-slate-200">
                      <div
                        className={`h-full rounded-full ${barColour}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="tabular-nums text-slate-700">
                      ${parseFloat(b.current_spend_usd).toFixed(4)}{' '}
                      <span className="text-slate-500">({pct.toFixed(0)}%)</span>
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ACTION_COLOURS[b.action] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}`}
                  >
                    {b.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => handleDelete(b.id)}
                    disabled={deleting === b.id}
                    className="text-slate-400 hover:text-red-500 disabled:opacity-40"
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
