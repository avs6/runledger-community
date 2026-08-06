'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  getBudgets,
  createBudgetOverride,
  listBudgetOverrides,
  revokeBudgetOverride,
} from '@/lib/api'
import type { BudgetOverride } from '@/types/api'

function money(v: number | null) {
  if (v == null) return '—'
  return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const statusColors: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  pending: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  expired: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  revoked: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
}

interface BudgetOption {
  id: string
  label: string
  limit_usd: number
}

export default function BudgetOverridesPage() {
  const { data: session } = useSession()
  const [budgets, setBudgets] = useState<BudgetOption[]>([])
  const [selectedBudget, setSelectedBudget] = useState('')
  const [overrides, setOverrides] = useState<BudgetOverride[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    override_limit_usd: '',
    starts_at: '',
    expires_at: '',
    reason: '',
  })

  const apiKey = (session as any)?.apiKey as string | undefined

  async function loadBudgets() {
    if (!apiKey) return
    try {
      const data = await getBudgets(apiKey)
      const opts = data.items.map((b: any) => ({
        id: b.id,
        label: `${b.scope}/${b.feature_tag || b.end_user || b.app || 'workspace'} — ${money(b.limit_usd)}`,
        limit_usd: b.limit_usd,
      }))
      setBudgets(opts)
      if (opts.length > 0 && !selectedBudget) setSelectedBudget(opts[0].id)
    } catch { /* empty */ }
    setLoading(false)
  }

  async function loadOverrides(budgetId: string) {
    if (!apiKey || !budgetId) return
    try {
      const data = await listBudgetOverrides(apiKey, budgetId)
      setOverrides(data.items)
    } catch {
      setOverrides([])
    }
  }

  useEffect(() => { loadBudgets() }, [apiKey]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (selectedBudget) loadOverrides(selectedBudget) }, [selectedBudget, apiKey]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !selectedBudget) return
    setSaving(true)
    try {
      await createBudgetOverride(apiKey, selectedBudget, {
        override_limit_usd: parseFloat(form.override_limit_usd),
        starts_at: new Date(form.starts_at).toISOString(),
        expires_at: new Date(form.expires_at).toISOString(),
        reason: form.reason || undefined,
      })
      setShowForm(false)
      setForm({ override_limit_usd: '', starts_at: '', expires_at: '', reason: '' })
      await loadOverrides(selectedBudget)
    } catch { /* empty */ }
    setSaving(false)
  }

  async function handleRevoke(overrideId: string) {
    if (!apiKey || !selectedBudget) return
    await revokeBudgetOverride(apiKey, selectedBudget, overrideId)
    await loadOverrides(selectedBudget)
  }

  if (!apiKey) return null

  const activeCount = overrides.filter((o) => o.status === 'active').length

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-[-0.04em] text-slate-950 dark:text-slate-50">
            Budget Overrides
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Create time-boxed budget increases with automatic expiry. {activeCount > 0 && `${activeCount} active override${activeCount !== 1 ? 's' : ''}.`}
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          disabled={budgets.length === 0}
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
        >
          New Override
        </button>
      </div>

      <div className="flex items-center gap-4">
        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Budget</label>
        <select
          value={selectedBudget}
          onChange={(e) => setSelectedBudget(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
        >
          {budgets.map((b) => (
            <option key={b.id} value={b.id}>{b.label}</option>
          ))}
        </select>
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900"
        >
          <h2 className="mb-4 text-sm font-semibold text-slate-900 dark:text-white">
            Create Temporary Increase
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Override Limit (USD)</span>
              <input
                required
                type="number"
                step="0.01"
                value={form.override_limit_usd}
                onChange={(e) => setForm({ ...form, override_limit_usd: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Reason</span>
              <input
                value={form.reason}
                onChange={(e) => setForm({ ...form, reason: e.target.value })}
                placeholder="e.g., Product launch traffic spike"
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Starts At</span>
              <input
                required
                type="datetime-local"
                value={form.starts_at}
                onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Expires At</span>
              <input
                required
                type="datetime-local"
                value={form.expires_at}
                onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </label>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Creating...' : 'Create Override'}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : overrides.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center dark:border-slate-700 dark:bg-slate-900/50">
          <p className="text-sm text-slate-500">
            No overrides for this budget. Create a temporary increase to allow short-term overspend.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Status</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Original</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Override</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Starts</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Expires</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Reason</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {overrides.map((o) => (
                <tr key={o.id} className="bg-white dark:bg-slate-900">
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusColors[o.status] || statusColors.expired}`}>
                      {o.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{money(o.original_limit_usd)}</td>
                  <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{money(o.override_limit_usd)}</td>
                  <td className="px-4 py-3 text-xs text-slate-500">{new Date(o.starts_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-xs text-slate-500">{new Date(o.expires_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">{o.reason || '—'}</td>
                  <td className="px-4 py-3">
                    {o.status === 'active' && (
                      <button
                        onClick={() => handleRevoke(o.id)}
                        className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30"
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
  )
}
