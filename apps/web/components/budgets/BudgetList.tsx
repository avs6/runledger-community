'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowRight, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import type { Budget } from '@/types/api'
import { deleteBudget } from '@/lib/api'
import { routes } from '@/lib/routes'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'

interface Props {
  items: Budget[]
  apiKey: string
  onDeleted?: (id: string) => void
  emptyMessage?: string
}

const ACTION_CLASSES: Record<string, string> = {
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
  if (item.scope_display_name) return item.scope_display_name
  if (!item.scope_id) return 'All workspace traffic'
  return item.scope_id
}

export default function BudgetList({ items, apiKey, onDeleted, emptyMessage }: Props) {
  const [deleting, setDeleting] = useState<string | null>(null)
  const router = useRouter()
  const { confirm, dialog } = useConfirm()

  async function handleDelete(item: Budget) {
    const ok = await confirm({
      title: 'Deactivate this budget?',
      description: `${item.scope_type.replace('_', ' ')} · ${formatScope(item)} stops being enforced. Its spend history is kept.`,
      confirmLabel: 'Deactivate',
      destructive: true,
    })
    if (!ok) return
    setDeleting(item.id)
    try {
      await deleteBudget(apiKey, item.id)
      onDeleted?.(item.id)
      toast.success('Budget deactivated')
      router.refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to deactivate budget')
    } finally {
      setDeleting(null)
    }
  }

  const columns: DataTableColumn<Budget>[] = [
    {
      key: 'scope',
      header: 'Scope',
      sortable: true,
      value: (item) => `${item.scope_type} ${formatScope(item)}`,
      render: (item) => (
        <div>
          <div className="font-medium capitalize text-slate-950 dark:text-slate-100">
            {item.scope_type.replace('_', ' ')}
            {item.api_key_id ? <span className="ml-1 text-[10px] normal-case text-slate-500">(one key)</span> : null}
          </div>
          <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{formatScope(item)}</div>
        </div>
      ),
    },
    { key: 'period_type', header: 'Period', sortable: true, className: 'capitalize' },
    {
      key: 'limit_usd',
      header: 'Limit',
      sortable: true,
      value: (item) => Number(item.limit_usd),
      render: (item) => <span className="tabular-nums">{formatMoney(item.limit_usd)}</span>,
    },
    {
      key: 'pct_used',
      header: 'Live spend',
      sortable: true,
      value: (item) => Number(item.pct_used),
      render: (item) => {
        const pct = Math.min(100, parseFloat(item.pct_used))
        const bar = pct >= 100 ? 'bg-red-500' : pct >= 80 ? 'bg-amber-500' : 'bg-blue-600'
        return (
          <div className="flex items-center gap-3">
            <div
              className="h-2 w-32 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
              role="progressbar"
              aria-label="Budget used"
              aria-valuenow={Math.round(pct)}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
            </div>
            <span className="tabular-nums text-slate-700 dark:text-slate-300">
              {formatMoney(item.current_spend_usd)}{' '}
              <span className="text-slate-500 dark:text-slate-400">({pct.toFixed(0)}%)</span>
            </span>
          </div>
        )
      },
    },
    {
      key: 'action',
      header: 'Action',
      sortable: true,
      render: (item) => (
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ACTION_CLASSES[item.action] ?? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}
        >
          {item.action}
        </span>
      ),
    },
    {
      key: 'controls',
      header: 'Controls',
      render: (item) => (
        <div className="flex items-center justify-end gap-2">
          <Link
            href={routes.budgetsId(item.id)}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
          >
            Open
            <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
          <button
            type="button"
            onClick={() => handleDelete(item)}
            disabled={deleting === item.id}
            aria-label={`Deactivate budget for ${formatScope(item)}`}
            title="Deactivate"
            className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40 dark:hover:bg-red-950/30 dark:hover:text-red-300"
          >
            <Trash2 className="h-4 w-4" aria-hidden />
          </button>
        </div>
      ),
    },
  ]

  return (
    <>
      <DataTable
        label="Budgets"
        rows={items}
        columns={columns}
        rowKey={(item) => item.id}
        urlPrefix="b_"
        searchPlaceholder="Search scope, period or action"
        csvFileName="budgets.csv"
        emptyTitle="No budgets"
        emptyDescription={emptyMessage ?? 'Create one to start enforcing spend limits.'}
      />
      {dialog}
    </>
  )
}
