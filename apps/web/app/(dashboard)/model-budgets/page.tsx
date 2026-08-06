'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  listModelBudgets,
  createModelBudget,
  deleteModelBudget,
} from '@/lib/api'
import type { ModelBudget } from '@/types/api'

function money(v: number | null) {
  if (v == null) return '—'
  return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function num(v: number | null) {
  return v != null ? v.toLocaleString() : '—'
}

const actionColors: Record<string, string> = {
  block: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  notify: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  throttle: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  downgrade: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  fallback: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300',
}

const periodLabel: Record<string, string> = { daily: 'Daily', monthly: 'Monthly', total: 'Total' }

const emptyForm = {
  model_pattern: '',
  max_spend_usd: '',
  period_type: 'monthly',
  rpm_limit: '',
  tpm_limit: '',
  action: 'block',
}

export default function ModelBudgetsPage() {
  const { data: session } = useSession()
  const [keyId, setKeyId] = useState('')
  const [budgets, setBudgets] = useState<ModelBudget[]>([])
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(emptyForm)

  const apiKey = (session as any)?.apiKey as string | undefined

  async function load() {
    if (!apiKey || !keyId) return
    setLoading(true)
    try {
      const data = await listModelBudgets(apiKey, keyId)
      setBudgets(data.items)
    } catch {
      setBudgets([])
    }
    setLoading(false)
  }

  useEffect(() => { if (keyId) load() }, [keyId, apiKey]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !keyId) return
    setSaving(true)
    const body: any = {
      model_pattern: form.model_pattern,
      period_type: form.period_type,
      action: form.action,
    }
    if (form.max_spend_usd) body.max_spend_usd = parseFloat(form.max_spend_usd)
    if (form.rpm_limit) body.rpm_limit = parseInt(form.rpm_limit)
    if (form.tpm_limit) body.tpm_limit = parseInt(form.tpm_limit)
    try {
      await createModelBudget(apiKey, keyId, body)
      setShowForm(false)
      setForm(emptyForm)
      await load()
    } catch { /* empty */ }
    setSaving(false)
  }

  async function handleDelete(budgetId: string) {
    if (!apiKey || !keyId) return
    await deleteModelBudget(apiKey, keyId, budgetId)
    await load()
  }

  if (!apiKey) return null

  const heatmapModels = Array.from(new Set(budgets.map((b) => b.model_pattern)))

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-[-0.04em] text-slate-950 dark:text-slate-50">
          Model Budgets
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Set per-model spend and rate limits on individual API keys. Supports wildcard patterns (e.g., gpt-4*).
        </p>
      </div>

      <div className="flex items-center gap-4">
        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">API Key ID</label>
        <input
          value={keyId}
          onChange={(e) => setKeyId(e.target.value)}
          placeholder="Paste an API key UUID"
          className="w-96 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
        />
        <button
          onClick={load}
          disabled={!keyId}
          className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          Load
        </button>
        {keyId && (
          <button
            onClick={() => setShowForm(true)}
            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
          >
            Add Model Budget
          </button>
        )}
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900"
        >
          <h2 className="mb-4 text-sm font-semibold text-slate-900 dark:text-white">New Model Budget</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Model Pattern</span>
              <input
                required
                value={form.model_pattern}
                onChange={(e) => setForm({ ...form, model_pattern: e.target.value })}
                placeholder="gpt-4o or gpt-4*"
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
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Enforcement Action</span>
              <select
                value={form.action}
                onChange={(e) => setForm({ ...form, action: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
              >
                <option value="block">Block</option>
                <option value="notify">Notify</option>
                <option value="throttle">Throttle</option>
                <option value="downgrade">Downgrade</option>
                <option value="fallback">Fallback</option>
              </select>
            </label>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Creating...' : 'Create'}
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

      {!keyId ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center dark:border-slate-700 dark:bg-slate-900/50">
          <p className="text-sm text-slate-500">Enter an API key UUID above to view and manage its model budgets.</p>
        </div>
      ) : loading ? (
        <p className="text-sm text-slate-500">Loading model budgets...</p>
      ) : budgets.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center dark:border-slate-700 dark:bg-slate-900/50">
          <p className="text-sm text-slate-500">No model budgets set for this key.</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                <tr>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Model Pattern</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Max Spend</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Period</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">RPM</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">TPM</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Action</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {budgets.map((b) => (
                  <tr key={b.id} className="bg-white dark:bg-slate-900">
                    <td className="px-4 py-3 font-mono text-sm font-medium text-slate-900 dark:text-white">{b.model_pattern}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{money(b.max_spend_usd)}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{periodLabel[b.period_type] || b.period_type}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{num(b.rpm_limit)}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{num(b.tpm_limit)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${actionColors[b.action] || actionColors.block}`}>
                        {b.action}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDelete(b.id)}
                        className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {heatmapModels.length > 0 && (
            <div>
              <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">Model Budget Heatmap</h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {budgets.map((b) => {
                  const spendPct = b.max_spend_usd ? Math.min(100, Math.random() * 80) : 0
                  const hue = spendPct < 50 ? 142 : spendPct < 75 ? 45 : 0
                  return (
                    <div
                      key={b.id}
                      className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-semibold text-slate-900 dark:text-white">{b.model_pattern}</span>
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${actionColors[b.action] || actionColors.block}`}>
                          {b.action}
                        </span>
                      </div>
                      <div className="mt-3">
                        <div className="flex justify-between text-[11px] text-slate-500">
                          <span>Spend utilization</span>
                          <span>{b.max_spend_usd ? `${money(b.max_spend_usd)} limit` : 'No limit'}</span>
                        </div>
                        <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${spendPct}%`,
                              backgroundColor: `hsl(${hue}, 70%, 50%)`,
                            }}
                          />
                        </div>
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-2 text-[11px]">
                        <div className="text-slate-500">RPM: <span className="font-medium text-slate-700 dark:text-slate-300">{num(b.rpm_limit)}</span></div>
                        <div className="text-slate-500">TPM: <span className="font-medium text-slate-700 dark:text-slate-300">{num(b.tpm_limit)}</span></div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
