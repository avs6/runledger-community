'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowRight, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import type { Budget } from '@/types/api'
import { deleteBudget } from '@/lib/api'

interface Props {
  items: Budget[]
  apiKey: string
  onDeleted?: (id: string) => void
  emptyMessage?: string
}

const ACTION_COLOURS: Record<string, string> = {
  block: 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300',
  notify: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
  downgrade: 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300',
  throttle: 'bg-violet-100 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300',
  fallback: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
}

function formatMoney(value: string) {
  return `$${parseFloat(value).toFixed(2)}`
}

function formatScope(item: Budget) {
  if (item.scope_display_name) {
    return item.scope_display_name
  }
  if (!item.scope_id) {
    return 'All workspace traffic'
  }
  return item.scope_id
}

export default function BudgetList({ items, apiKey, onDeleted, emptyMessage }: Props) {
  const [deleting, setDeleting] = useState<string | null>(null)
  const router = useRouter()

  async function handleDelete(id: string) {
    if (!confirm('Deactivate this budget?')) return
    setDeleting(id)
    try {
      await deleteBudget(apiKey, id)
      onDeleted?.(id)
      toast.success('Budget deactivated')
      router.refresh()
    } catch (err) {
      toast.error('Failed to deactivate budget')
      console.error(err)
    } finally {
      setDeleting(null)
    }
  }

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white/70 py-12 text-center text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400">
        {emptyMessage ?? 'No budgets yet. Create one to start enforcing spend limits.'}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
        <thead className="bg-slate-50 dark:bg-slate-900">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
              Scope
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
              Period
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
              Limit
            </th>
            <th className="w-56 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
              Live Spend
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
              Action
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
              Controls
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white/90 dark:divide-slate-800 dark:bg-slate-950">
          {items.map((item) => {
            const pct = Math.min(100, parseFloat(item.pct_used))
            const barColour =
              pct >= 100 ? 'bg-red-500' : pct >= 80 ? 'bg-amber-500' : 'bg-blue-600'

            return (
              <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-900/70">
                <td className="px-4 py-3">
                  <div className="font-medium capitalize text-slate-950 dark:text-slate-100">
                    {item.scope_type.replace('_', ' ')}
                  </div>
                  <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {formatScope(item)}
                  </div>
                </td>
                <td className="px-4 py-3 capitalize text-slate-700 dark:text-slate-300">
                  {item.period_type}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-slate-950 dark:text-slate-100">
                  {formatMoney(item.limit_usd)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="h-2 w-32 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                      <div
                        className={`h-full rounded-full ${barColour}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="tabular-nums text-slate-700 dark:text-slate-300">
                      {formatMoney(item.current_spend_usd)}{' '}
                      <span className="text-slate-500 dark:text-slate-400">
                        ({pct.toFixed(0)}%)
                      </span>
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ACTION_COLOURS[item.action] ?? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}
                  >
                    {item.action}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-2">
                    <Link
                      href={`/budgets/${item.id}`}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
                    >
                      Open
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                    <button
                      onClick={() => handleDelete(item.id)}
                      disabled={deleting === item.id}
                      className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40 dark:hover:bg-red-950/30 dark:hover:text-red-300"
                      title="Deactivate"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
