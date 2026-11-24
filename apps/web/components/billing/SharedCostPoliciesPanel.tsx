'use client'

import { useEffect, useState } from 'react'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { toast } from 'sonner'
import {
  apiErrorMessage,
  applySharedCostPolicy,
  createSharedCostPolicy,
  deleteCostAllocation,
  deleteSharedCostPolicy,
  listCostAllocations,
  listCostCenters,
  listSharedCostPolicies,
  previewSharedCostAllocation,
  updateSharedCostPolicy,
} from '@/lib/api'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import type { CostAllocation, CostCenter, SharedCostPolicy, SharedCostAllocationResult } from '@/types/api'

function currentMonth(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

interface Props {
  apiKey: string
  defaultPoolUsd: string
}

const EMPTY_ALLOCATIONS = JSON.stringify(
  [{ label: 'Engineering', weight: '0.5' }, { label: 'Product', weight: '0.5' }],
  null,
  2
)

export default function SharedCostPoliciesPanel({ apiKey, defaultPoolUsd }: Props) {
  const { confirm, dialog } = useConfirm()
  const [items, setItems] = useState<SharedCostPolicy[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [formulaType, setFormulaType] = useState<'equal_split' | 'proportional' | 'fixed_weight'>('equal_split')
  const [allocationsText, setAllocationsText] = useState(EMPTY_ALLOCATIONS)
  const [isActive, setIsActive] = useState(true)
  const [poolUsd, setPoolUsd] = useState(defaultPoolUsd)
  const [preview, setPreview] = useState<SharedCostAllocationResult | null>(null)
  const [month, setMonth] = useState(currentMonth())
  const [applied, setApplied] = useState<CostAllocation[]>([])
  const [centers, setCenters] = useState<CostCenter[]>([])

  async function loadPolicies() {
    setLoading(true)
    try {
      const [result, cc] = await Promise.all([listSharedCostPolicies(apiKey), listCostCenters(apiKey)])
      setItems(result.items)
      setCenters(cc.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load shared-cost policies')
    } finally {
      setLoading(false)
    }
  }

  async function loadApplied() {
    try {
      setApplied((await listCostAllocations(apiKey, { period: month })).items)
    } catch {
      setApplied([])
    }
  }

  useEffect(() => {
    void loadPolicies()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey])

  useEffect(() => {
    void loadApplied()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, month])

  async function handleApply(policy: SharedCostPolicy) {
    const ok = await confirm({
      title: `Apply ${policy.name} to ${month}?`,
      description: `Pool of USD ${poolUsd}. This replaces any earlier split of this policy for ${month}.`,
      confirmLabel: 'Apply',
    })
    if (!ok) return
    try {
      const res = await applySharedCostPolicy(apiKey, policy.id, { period: month, pool_usd: poolUsd })
      toast.success(`Applied: USD ${res.total_usd} split across ${res.items.length} cost centers`)
      await loadApplied()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to apply the policy'))
    }
  }

  async function handleRemoveApplied(id: string) {
    try {
      await deleteCostAllocation(apiKey, id)
      await loadApplied()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to remove the allocation'))
    }
  }

  const centerName = (id: string | null) =>
    centers.find((c) => c.id === id)?.name ?? (id ? '(deleted)' : 'Unassigned')

  function resetForm() {
    setEditingId(null)
    setName('')
    setDescription('')
    setFormulaType('equal_split')
    setAllocationsText(EMPTY_ALLOCATIONS)
    setIsActive(true)
    setPreview(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const allocations = JSON.parse(allocationsText) as Array<Record<string, unknown>>
      const payload = {
        name,
        description: description || null,
        formula_type: formulaType,
        allocations: allocations.map((item) => ({
          label: String(item.label ?? ''),
          cost_center_id: item.cost_center_id ? String(item.cost_center_id) : null,
          weight: item.weight != null ? String(item.weight) : null,
          denominator_value: item.denominator_value != null ? String(item.denominator_value) : null,
        })),
        is_active: isActive,
      }

      if (editingId) {
        await updateSharedCostPolicy(apiKey, editingId, payload)
        toast.success('Shared-cost policy updated')
      } else {
        await createSharedCostPolicy(apiKey, payload)
        toast.success('Shared-cost policy created')
      }

      resetForm()
      await loadPolicies()
    } catch (err) {
      console.error(err)
      toast.error(apiErrorMessage(err, 'Failed to save shared-cost policy'))
    } finally {
      setSaving(false)
    }
  }

  async function handlePreview(policyId: string) {
    try {
      const result = await previewSharedCostAllocation(apiKey, policyId, poolUsd || '0')
      setPreview(result)
    } catch (err) {
      console.error(err)
      toast.error('Failed to preview allocation')
    }
  }

  async function handleDelete(policyId: string) {
    if (!(await confirm({ title: 'Delete this shared-cost policy?', confirmLabel: 'Delete', destructive: true }))) return
    try {
      await deleteSharedCostPolicy(apiKey, policyId)
      toast.success('Shared-cost policy deleted')
      if (editingId === policyId) resetForm()
      await loadPolicies()
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete shared-cost policy')
    }
  }

  function startEdit(item: SharedCostPolicy) {
    setEditingId(item.id)
    setName(item.name)
    setDescription(item.description ?? '')
    setFormulaType(item.formula_type)
    setAllocationsText(JSON.stringify(item.allocations, null, 2))
    setIsActive(item.is_active)
    setPreview(null)
  }

  return (
    <>
    <div className="grid gap-6 xl:grid-cols-[1.05fr_1.35fr]">
      <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Shared Cost Policy</p>
          <h2 className="mt-1 text-xl font-semibold text-slate-950 dark:text-white">
            {editingId ? 'Edit policy' : 'Create policy'}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Define how shared overhead should be distributed before chargeback and ledger close.
          </p>
        </div>

        <label className="block text-sm">
          <span className="font-medium text-slate-700 dark:text-slate-300">Name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
          />
        </label>

        <label className="block text-sm">
          <span className="font-medium text-slate-700 dark:text-slate-300">Formula</span>
          <select
            value={formulaType}
            onChange={(e) => setFormulaType(e.target.value as typeof formulaType)}
            className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
          >
            <option value="equal_split">Equal split</option>
            <option value="fixed_weight">Fixed weight</option>
            <option value="proportional">Proportional</option>
          </select>
        </label>

        <label className="block text-sm">
          <span className="font-medium text-slate-700 dark:text-slate-300">Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
          />
        </label>

        <label className="block text-sm">
          <span className="font-medium text-slate-700 dark:text-slate-300">Allocations JSON</span>
          <textarea
            value={allocationsText}
            onChange={(e) => setAllocationsText(e.target.value)}
            rows={10}
            className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 font-mono text-xs dark:border-slate-700 dark:bg-slate-950 dark:text-white"
          />
        </label>

        <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            {saving ? 'Saving...' : editingId ? 'Save changes' : 'Create policy'}
          </button>
          {editingId ? (
            <button
              type="button"
              onClick={resetForm}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
          ) : null}
        </div>
      </form>

      <div className="space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Pool (USD)</p>
              <input
                value={poolUsd}
                onChange={(e) => setPoolUsd(e.target.value)}
                aria-label="Pool in USD"
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Month</p>
              <input
                type="month"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
                aria-label="Month to apply to"
                className="mt-1 rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              />
            </div>
            <p className="max-w-md text-sm text-slate-500">
              Preview a split, or apply it to a month: applied amounts are charged to the cost centers in the Chargeback cost-center report.
            </p>
          </div>
        </div>

        {loading ? (
          <p className="rounded-2xl border border-slate-200 px-4 py-6 text-center text-sm text-slate-500 dark:border-slate-700">Loading policies...</p>
        ) : (
          <DataTable
            label="Shared-cost policies"
            rows={items}
            rowKey={(item) => item.id}
            urlPrefix="scp_"
            csvFileName="shared-cost-policies.csv"
            searchPlaceholder="Search policies"
            emptyTitle="No shared-cost policies yet"
            columns={[
              {
                key: 'name',
                header: 'Policy',
                sortable: true,
                render: (item) => (
                  <div>
                    <div className="font-medium text-slate-900 dark:text-white">{item.name}</div>
                    <div className="text-xs text-slate-500">{item.description || 'No description'}</div>
                  </div>
                ),
              },
              { key: 'formula_type', header: 'Formula', sortable: true },
              { key: 'allocations', header: 'Allocations', value: (item) => item.allocations.length },
              {
                key: 'is_active',
                header: 'Status',
                value: (item) => (item.is_active ? 'Active' : 'Inactive'),
                render: (item) => (
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${item.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300'}`}>
                    {item.is_active ? 'Active' : 'Inactive'}
                  </span>
                ),
              },
              {
                key: 'actions',
                header: 'Actions',
                render: (item) => (
                  <div className="flex justify-end gap-2">
                    <button type="button" onClick={() => handlePreview(item.id)} aria-label={`Preview ${item.name}`} className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
                      Preview
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApply(item)}
                      disabled={!item.is_active}
                      aria-label={`Apply ${item.name} to ${month}`}
                      className="rounded-lg border border-emerald-300 px-2 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-40 dark:border-emerald-800 dark:text-emerald-300"
                    >
                      Apply to {month}
                    </button>
                    <button type="button" onClick={() => startEdit(item)} aria-label={`Edit ${item.name}`} className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
                      Edit
                    </button>
                    <button type="button" onClick={() => handleDelete(item.id)} aria-label={`Delete ${item.name}`} className="rounded-lg border border-rose-200 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-900/40 dark:text-rose-300 dark:hover:bg-rose-950/30">
                      Delete
                    </button>
                  </div>
                ),
              },
            ] satisfies DataTableColumn<SharedCostPolicy>[]}
          />
        )}

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Applied to {month}</h3>
          {applied.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">No shared costs applied to this month.</p>
          ) : (
            <div className="mt-3 space-y-2">
              {applied.map((a) => (
                <div key={a.id} className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
                  <span className="text-slate-700 dark:text-slate-300">
                    {a.label} → {centerName(a.cost_center_id)}
                    <span className="ml-2 text-xs text-slate-400">{items.find((p) => p.id === a.policy_id)?.name ?? ''}</span>
                  </span>
                  <span className="flex items-center gap-3">
                    <span className="font-mono text-slate-900 dark:text-white">USD {a.amount_usd}</span>
                    <button onClick={() => handleRemoveApplied(a.id)} className="text-xs text-rose-600 hover:underline">Remove</button>
                  </span>
                </div>
              ))}
            </div>
          )}
          {centers.length > 0 && (
            <p className="mt-3 text-xs text-slate-500">
              Cost center ids for allocations: {centers.map((c) => `${c.name} = ${c.id}`).join(' · ')}
            </p>
          )}
        </div>

        {preview ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Preview: {preview.policy_name}
            </h3>
            <p className="mt-1 text-sm text-slate-500">Pool: ${preview.pool_usd}</p>
            <div className="mt-4 space-y-2">
              {preview.allocations.map((item) => (
                <div key={`${preview.policy_id}-${item.label}`} className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
                  <span className="text-slate-700 dark:text-slate-300">{item.label}</span>
                  <span className="font-mono text-slate-900 dark:text-white">${item.allocated_usd}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
      {dialog}
    </>
  )
}
