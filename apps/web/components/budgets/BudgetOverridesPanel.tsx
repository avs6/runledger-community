'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import { createBudgetOverride, listBudgetOverrides, revokeBudgetOverride } from '@/lib/api'
import type { Budget, BudgetOverride } from '@/types/api'

interface Props {
  budgets: Budget[]
  apiKey: string
}

function formatMoney(value: number | string | null) {
  if (value == null) return '-'
  return `$${Number(value).toFixed(2)}`
}

const statusColors: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
  pending: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
  expired: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  revoked: 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300',
}

function budgetLabel(budget: Budget) {
  const scope = budget.scope_type.replace('_', ' ')
  const target = budget.scope_display_name ?? budget.scope_id ?? 'workspace'
  return `${scope}: ${target} · ${formatMoney(budget.limit_usd)}`
}

export default function BudgetOverridesPanel({ budgets, apiKey }: Props) {
  const [selectedBudget, setSelectedBudget] = useState(budgets[0]?.id ?? '')
  const [items, setItems] = useState<BudgetOverride[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    override_limit_usd: '',
    starts_at: '',
    expires_at: '',
    reason: '',
    require_approval: false,
  })

  const activeBudget = useMemo(
    () => budgets.find((budget) => budget.id === selectedBudget) ?? null,
    [budgets, selectedBudget]
  )

  async function loadOverrides(budgetId: string) {
    if (!budgetId) {
      setItems([])
      return
    }
    setLoading(true)
    try {
      const result = await listBudgetOverrides(apiKey, budgetId)
      setItems(result.items)
    } catch (err) {
      toast.error('Failed to load overrides')
      console.error(err)
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (budgets.length === 0) return
    if (!selectedBudget) {
      setSelectedBudget(budgets[0].id)
      return
    }
    void loadOverrides(selectedBudget)
  }, [budgets, selectedBudget])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedBudget) return
    setSaving(true)
    try {
      await createBudgetOverride(apiKey, selectedBudget, {
        override_limit_usd: parseFloat(form.override_limit_usd),
        starts_at: new Date(form.starts_at).toISOString(),
        expires_at: new Date(form.expires_at).toISOString(),
        reason: form.reason || undefined,
        require_approval: form.require_approval,
      })
      toast.success(form.require_approval ? 'Override sent for approval' : 'Override created')
      setShowForm(false)
      setForm({
        override_limit_usd: '',
        starts_at: '',
        expires_at: '',
        reason: '',
        require_approval: false,
      })
      await loadOverrides(selectedBudget)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create override')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  async function handleRevoke(overrideId: string) {
    if (!selectedBudget) return
    try {
      await revokeBudgetOverride(apiKey, selectedBudget, overrideId)
      toast.success('Override revoked')
      await loadOverrides(selectedBudget)
    } catch (err) {
      toast.error('Failed to revoke override')
      console.error(err)
    }
  }

  const activeCount = items.filter((item) => item.status === 'active').length

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-wide text-slate-500">Budget Overrides</p>
          <h3 className="text-lg font-semibold text-slate-950 dark:text-slate-100">
            Temporary exceptions inside the main budget workflow
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Use overrides for short-lived increases instead of creating shadow policies.
          </p>
        </div>
        <button
          onClick={() => setShowForm((value) => !value)}
          disabled={budgets.length === 0}
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {showForm ? 'Hide form' : 'New Override'}
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Budget</label>
            <select
              value={selectedBudget}
              onChange={(e) => setSelectedBudget(e.target.value)}
              className="min-w-[280px] rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            >
              {budgets.map((budget) => (
                <option key={budget.id} value={budget.id}>
                  {budgetLabel(budget)}
                </option>
              ))}
            </select>
          </div>

          {showForm && selectedBudget && (
            <form onSubmit={handleCreate} className="mt-5 grid gap-4 rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Override limit (USD)</span>
                  <input
                    required
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={form.override_limit_usd}
                    onChange={(e) => setForm({ ...form, override_limit_usd: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Reason</span>
                  <input
                    value={form.reason}
                    onChange={(e) => setForm({ ...form, reason: e.target.value })}
                    placeholder="Launch traffic or temporary exception"
                    className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Starts at</span>
                  <input
                    required
                    type="datetime-local"
                    value={form.starts_at}
                    onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Expires at</span>
                  <input
                    required
                    type="datetime-local"
                    value={form.expires_at}
                    onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </label>
              </div>
              <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 dark:border-slate-800 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={form.require_approval}
                  onChange={(e) => setForm({ ...form, require_approval: e.target.checked })}
                  className="h-4 w-4"
                />
                Require governance approval before activating this override
              </label>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Create Override'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="mt-5">
            {loading ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">Loading overrides...</p>
            ) : items.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-400">
                No overrides for this budget yet.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-900/70">
                    <tr>
                      <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Status</th>
                      <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Original</th>
                      <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Override</th>
                      <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Window</th>
                      <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Reason</th>
                      <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {items.map((item) => (
                      <tr key={item.id} className="bg-white dark:bg-slate-950">
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusColors[item.status] ?? statusColors.expired}`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                          {formatMoney(item.original_limit_usd)}
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-950 dark:text-slate-100">
                          {formatMoney(item.override_limit_usd)}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
                          {new Date(item.starts_at).toLocaleString()} to{' '}
                          {new Date(item.expires_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                          {item.reason || '-'}
                        </td>
                        <td className="px-4 py-3">
                          {item.approval_id && (
                            <Link
                              href="/approvals"
                              className="mr-2 text-xs text-blue-600 hover:underline dark:text-blue-300"
                            >
                              Review approval
                            </Link>
                          )}
                          {item.status === 'active' && (
                            <button
                              onClick={() => handleRevoke(item.id)}
                              className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950/30"
                            >
                              Revoke
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs uppercase tracking-wide text-slate-500">Selected Budget</p>
            <h4 className="mt-2 text-lg font-semibold text-slate-950 dark:text-slate-100">
              {activeBudget ? budgetLabel(activeBudget) : 'No budget selected'}
            </h4>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Active overrides: {activeCount}
            </p>
            {activeBudget?.scope_display_name && (
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                Related scope: {activeBudget.scope_display_name}
              </p>
            )}
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs uppercase tracking-wide text-slate-500">Governance Note</p>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              Overrides are temporary exceptions. Keep them visible in the main budget workflow so
              operators can explain spend spikes without creating duplicate policy paths.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
