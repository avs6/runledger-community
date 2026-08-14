'use client'

import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
  createSharedCostPolicy,
  deleteSharedCostPolicy,
  listSharedCostPolicies,
  previewSharedCostAllocation,
  updateSharedCostPolicy,
} from '@/lib/api'
import type { SharedCostPolicy, SharedCostAllocationResult } from '@/types/api'

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

  async function loadPolicies() {
    setLoading(true)
    try {
      const result = await listSharedCostPolicies(apiKey)
      setItems(result.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load shared-cost policies')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadPolicies()
  }, [apiKey])

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
      toast.error(err instanceof Error ? err.message : 'Failed to save shared-cost policy')
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
    if (!window.confirm('Delete this shared-cost policy?')) return
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
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Preview Pool</p>
              <input
                value={poolUsd}
                onChange={(e) => setPoolUsd(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              />
            </div>
            <p className="max-w-md text-sm text-slate-500">
              Preview how a reconciliation pool would allocate before the period is exported into chargeback or ledger closure.
            </p>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-700">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Policy</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Formula</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Allocations</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Status</th>
                <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr className="bg-white dark:bg-slate-900">
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-500">Loading policies...</td>
                </tr>
              ) : items.length === 0 ? (
                <tr className="bg-white dark:bg-slate-900">
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-500">No shared-cost policies yet.</td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="bg-white dark:bg-slate-900">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900 dark:text-white">{item.name}</div>
                      <div className="text-xs text-slate-500">{item.description || 'No description'}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{item.formula_type}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{item.allocations.length}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${item.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300'}`}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button onClick={() => handlePreview(item.id)} className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
                          Preview
                        </button>
                        <button onClick={() => startEdit(item)} className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
                          Edit
                        </button>
                        <button onClick={() => handleDelete(item.id)} className="rounded-lg border border-rose-200 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-900/40 dark:text-rose-300 dark:hover:bg-rose-950/30">
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
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
  )
}
