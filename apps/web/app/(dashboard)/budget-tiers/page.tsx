'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  listBudgetTiers,
  createBudgetTier,
  updateBudgetTier,
  deleteBudgetTier,
} from '@/lib/api'
import type { BudgetTier } from '@/types/api'

function money(v: number | null) {
  if (v == null) return '—'
  return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function num(v: number | null) {
  return v != null ? v.toLocaleString() : '—'
}

const periodLabel: Record<string, string> = {
  daily: 'Daily',
  monthly: 'Monthly',
  total: 'Total',
}

const emptyForm = {
  name: '',
  max_spend_usd: '',
  period_type: 'monthly',
  rpm_limit: '',
  tpm_limit: '',
  allowed_models: '',
  is_default: false,
}

export default function BudgetTiersPage() {
  const { data: session } = useSession()
  const [tiers, setTiers] = useState<BudgetTier[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)

  const apiKey = (session as any)?.apiKey as string | undefined

  async function load() {
    if (!apiKey) return
    try {
      const data = await listBudgetTiers(apiKey)
      setTiers(data.items)
    } catch { /* empty */ }
    setLoading(false)
  }

  useEffect(() => { load() }, [apiKey]) // eslint-disable-line react-hooks/exhaustive-deps

  function startEdit(t: BudgetTier) {
    setEditId(t.id)
    setForm({
      name: t.name,
      max_spend_usd: t.max_spend_usd != null ? String(t.max_spend_usd) : '',
      period_type: t.period_type,
      rpm_limit: t.rpm_limit != null ? String(t.rpm_limit) : '',
      tpm_limit: t.tpm_limit != null ? String(t.tpm_limit) : '',
      allowed_models: t.allowed_models?.join(', ') || '',
      is_default: t.is_default,
    })
    setShowForm(true)
  }

  function startCreate() {
    setEditId(null)
    setForm(emptyForm)
    setShowForm(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setSaving(true)
    const body: any = {
      name: form.name,
      period_type: form.period_type,
      is_default: form.is_default,
    }
    if (form.max_spend_usd) body.max_spend_usd = parseFloat(form.max_spend_usd)
    if (form.rpm_limit) body.rpm_limit = parseInt(form.rpm_limit)
    if (form.tpm_limit) body.tpm_limit = parseInt(form.tpm_limit)
    if (form.allowed_models.trim()) body.allowed_models = form.allowed_models.split(',').map((s: string) => s.trim()).filter(Boolean)
    try {
      if (editId) {
        await updateBudgetTier(apiKey, editId, body)
      } else {
        await createBudgetTier(apiKey, body)
      }
      setShowForm(false)
      setEditId(null)
      setForm(emptyForm)
      await load()
    } catch { /* empty */ }
    setSaving(false)
  }

  async function handleDelete(id: string) {
    if (!apiKey) return
    await deleteBudgetTier(apiKey, id)
    await load()
  }

  if (!apiKey) return null

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-[-0.04em] text-slate-950 dark:text-slate-50">
            Budget Tiers
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Define standardized spend and rate profiles, then assign them to API keys.
          </p>
        </div>
        <button
          onClick={startCreate}
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
        >
          Create Tier
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900"
        >
          <h2 className="mb-4 text-sm font-semibold text-slate-900 dark:text-white">
            {editId ? 'Edit Tier' : 'New Tier'}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Name</span>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Max Spend (USD)</span>
              <input
                type="number"
                step="0.01"
                value={form.max_spend_usd}
                onChange={(e) => setForm({ ...form, max_spend_usd: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Period</span>
              <select
                value={form.period_type}
                onChange={(e) => setForm({ ...form, period_type: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              >
                <option value="daily">Daily</option>
                <option value="monthly">Monthly</option>
                <option value="total">Total</option>
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">RPM Limit</span>
              <input
                type="number"
                value={form.rpm_limit}
                onChange={(e) => setForm({ ...form, rpm_limit: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">TPM Limit</span>
              <input
                type="number"
                value={form.tpm_limit}
                onChange={(e) => setForm({ ...form, tpm_limit: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Allowed Models (comma-separated)</span>
              <input
                value={form.allowed_models}
                onChange={(e) => setForm({ ...form, allowed_models: e.target.value })}
                placeholder="gpt-4o, gpt-4o-mini, claude-3.5-sonnet"
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              />
            </label>
          </div>
          <label className="mt-4 flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={form.is_default}
              onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
              className="rounded border-slate-300"
            />
            Default tier for new keys
          </label>
          <div className="mt-4 flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : editId ? 'Update' : 'Create'}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setEditId(null) }}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading tiers...</p>
      ) : tiers.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center dark:border-slate-700 dark:bg-slate-900/50">
          <p className="text-sm text-slate-500">
            No budget tiers defined yet. Create tiers to standardize spend profiles across API keys.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Tier</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Max Spend</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Period</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">RPM</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">TPM</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Models</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Keys</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {tiers.map((t) => (
                <tr key={t.id} className="bg-white dark:bg-slate-900">
                  <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                    {t.name}
                    {t.is_default && (
                      <span className="ml-2 inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                        DEFAULT
                      </span>
                    )}
                    {!t.is_active && (
                      <span className="ml-2 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                        INACTIVE
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{money(t.max_spend_usd)}</td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{periodLabel[t.period_type] || t.period_type}</td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{num(t.rpm_limit)}</td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{num(t.tpm_limit)}</td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                    {t.allowed_models?.length ? (
                      <div className="flex flex-wrap gap-1">
                        {t.allowed_models.slice(0, 3).map((m) => (
                          <span key={m} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] dark:bg-slate-800">
                            {m}
                          </span>
                        ))}
                        {t.allowed_models.length > 3 && (
                          <span className="text-[10px] text-slate-400">+{t.allowed_models.length - 3}</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-slate-400">All</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{t.key_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <button
                        onClick={() => startEdit(t)}
                        className="rounded-lg px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/30"
                      >
                        Edit
                      </button>
                      {t.is_active && (
                        <button
                          onClick={() => handleDelete(t.id)}
                          className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30"
                        >
                          Retire
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tiers.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">Tier Comparison</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {tiers.filter((t) => t.is_active).map((t) => (
              <div
                key={t.id}
                className={`rounded-2xl border p-5 shadow-sm ${
                  t.is_default
                    ? 'border-blue-300 bg-blue-50/50 dark:border-blue-600 dark:bg-blue-950/30'
                    : 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900'
                }`}
              >
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">{t.name}</h3>
                <div className="mt-3 space-y-2 text-xs text-slate-600 dark:text-slate-400">
                  <div className="flex justify-between">
                    <span>Spend Limit</span>
                    <span className="font-medium text-slate-900 dark:text-white">{money(t.max_spend_usd)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Requests/min</span>
                    <span className="font-medium text-slate-900 dark:text-white">{num(t.rpm_limit)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Tokens/min</span>
                    <span className="font-medium text-slate-900 dark:text-white">{num(t.tpm_limit)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Period</span>
                    <span className="font-medium text-slate-900 dark:text-white">{periodLabel[t.period_type]}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Keys assigned</span>
                    <span className="font-medium text-slate-900 dark:text-white">{t.key_count}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
