'use client'

import { useMemo, useState } from 'react'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { toast } from 'sonner'
import {
  createBillingAdjustment,
  deleteBillingAdjustment,
  updateBillingAdjustment,
} from '@/lib/api'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import type { BillingAdjustmentList, BillingAdjustment } from '@/types/api'

interface Props {
  apiKey: string
  periodId: string
  initialData: BillingAdjustmentList
  canEdit: boolean
}

type AdjustmentType = BillingAdjustment['adjustment_type']

const EMPTY_FORM = {
  adjustment_type: 'credit' as AdjustmentType,
  amount_usd: '',
  description: '',
  reference_id: '',
}

function money(value: string) {
  return `$${Number.parseFloat(value).toFixed(4)}`
}

export default function BillingAdjustmentsPanel({
  apiKey,
  periodId,
  initialData,
  canEdit,
}: Props) {
  const { confirm, dialog } = useConfirm()
  const [items, setItems] = useState(initialData.items)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const totals = useMemo(() => {
    const credits = items
      .filter((item) => item.adjustment_type !== 'surcharge')
      .reduce((sum, item) => sum + Number.parseFloat(item.amount_usd), 0)
    const surcharges = items
      .filter((item) => item.adjustment_type === 'surcharge')
      .reduce((sum, item) => sum + Number.parseFloat(item.amount_usd), 0)
    return {
      credits: credits.toFixed(4),
      surcharges: surcharges.toFixed(4),
      net: (surcharges - credits).toFixed(4),
    }
  }, [items])

  function reset() {
    setEditingId(null)
    setForm(EMPTY_FORM)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (editingId) {
        const updated = await updateBillingAdjustment(apiKey, periodId, editingId, form)
        setItems((current) => current.map((item) => (item.id === editingId ? updated : item)))
        toast.success('Adjustment updated')
      } else {
        const created = await createBillingAdjustment(apiKey, periodId, form)
        setItems((current) => [...current, created])
        toast.success('Adjustment created')
      }
      reset()
    } catch (err) {
      console.error(err)
      toast.error(err instanceof Error ? err.message : 'Failed to save adjustment')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(adjustmentId: string) {
    if (!(await confirm({ title: 'Delete this adjustment?', confirmLabel: 'Delete', destructive: true }))) return
    try {
      await deleteBillingAdjustment(apiKey, periodId, adjustmentId)
      setItems((current) => current.filter((item) => item.id !== adjustmentId))
      if (editingId === adjustmentId) reset()
      toast.success('Adjustment deleted')
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete adjustment')
    }
  }

  function startEdit(item: BillingAdjustment) {
    setEditingId(item.id)
    setForm({
      adjustment_type: item.adjustment_type,
      amount_usd: item.amount_usd,
      description: item.description ?? '',
      reference_id: item.reference_id ?? '',
    })
  }

  return (
    <>
    <div className="grid gap-6 xl:grid-cols-[0.95fr_1.35fr]">
      <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Adjustments</p>
          <h3 className="mt-1 text-xl font-semibold text-slate-950 dark:text-white">
            {editingId ? 'Edit adjustment' : 'Add adjustment'}
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Use credits, refunds, prepaid deductions, or surcharges to reconcile a period before close.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
            <p className="text-xs text-slate-500">Credits</p>
            <p className="mt-1 font-mono text-slate-900 dark:text-white">${totals.credits}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
            <p className="text-xs text-slate-500">Surcharges</p>
            <p className="mt-1 font-mono text-slate-900 dark:text-white">${totals.surcharges}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
            <p className="text-xs text-slate-500">Net adjustment</p>
            <p className="mt-1 font-mono text-slate-900 dark:text-white">${totals.net}</p>
          </div>
        </div>

        {canEdit ? (
          <form onSubmit={handleSubmit} className="space-y-3">
            <label className="block text-sm">
              <span className="font-medium text-slate-700 dark:text-slate-300">Type</span>
              <select
                value={form.adjustment_type}
                onChange={(e) => setForm((current) => ({ ...current, adjustment_type: e.target.value as AdjustmentType }))}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              >
                <option value="credit">Credit</option>
                <option value="refund">Refund</option>
                <option value="prepaid_deduction">Prepaid deduction</option>
                <option value="surcharge">Surcharge</option>
              </select>
            </label>

            <label className="block text-sm">
              <span className="font-medium text-slate-700 dark:text-slate-300">Amount (USD)</span>
              <input
                value={form.amount_usd}
                onChange={(e) => setForm((current) => ({ ...current, amount_usd: e.target.value }))}
                required
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              />
            </label>

            <label className="block text-sm">
              <span className="font-medium text-slate-700 dark:text-slate-300">Description</span>
              <textarea
                value={form.description}
                onChange={(e) => setForm((current) => ({ ...current, description: e.target.value }))}
                rows={3}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              />
            </label>

            <label className="block text-sm">
              <span className="font-medium text-slate-700 dark:text-slate-300">Reference</span>
              <input
                value={form.reference_id}
                onChange={(e) => setForm((current) => ({ ...current, reference_id: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              />
            </label>

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={saving}
                className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
              >
                {saving ? 'Saving...' : editingId ? 'Save adjustment' : 'Add adjustment'}
              </button>
              {editingId ? (
                <button
                  type="button"
                  onClick={reset}
                  className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
              ) : null}
            </div>
          </form>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500 dark:border-slate-700">
            Adjustments can no longer be edited after a billing period is closed.
          </div>
        )}
      </div>

      <DataTable
        label="Billing adjustments"
        rows={items}
        rowKey={(item) => item.id}
        urlPrefix="adj_"
        csvFileName="billing-adjustments.csv"
        searchPlaceholder="Search adjustments"
        emptyTitle="No adjustments yet"
        columns={[
          { key: 'adjustment_type', header: 'Type', sortable: true },
          {
            key: 'amount_usd',
            header: 'Amount',
            sortable: true,
            value: (item) => Number(item.amount_usd),
            render: (item) => <span className="font-mono">{money(item.amount_usd)}</span>,
          },
          { key: 'reference_id', header: 'Reference', render: (item) => item.reference_id || '--' },
          { key: 'description', header: 'Description', render: (item) => item.description || '--' },
          {
            key: 'actions',
            header: 'Actions',
            render: (item) =>
              canEdit ? (
                <div className="flex justify-end gap-2">
                  <button type="button" onClick={() => startEdit(item)} aria-label={`Edit ${item.adjustment_type} adjustment`} className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
                    Edit
                  </button>
                  <button type="button" onClick={() => handleDelete(item.id)} aria-label={`Delete ${item.adjustment_type} adjustment`} className="rounded-lg border border-rose-200 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-900/40 dark:text-rose-300 dark:hover:bg-rose-950/30">
                    Delete
                  </button>
                </div>
              ) : (
                <div className="text-right text-xs text-slate-500">Locked</div>
              ),
          },
        ] satisfies DataTableColumn<BillingAdjustment>[]}
      />
    </div>
      {dialog}
    </>
  )
}
