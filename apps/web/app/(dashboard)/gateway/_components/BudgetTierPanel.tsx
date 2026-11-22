'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import { toast } from 'sonner'
import { listApiKeys, listBudgetTiers, createBudgetTier, updateBudgetTier, deleteBudgetTier, assignTierToKey } from '@/lib/api'
import type { ApiKeyResponse, BudgetTier } from '@/types/api'
import { inputCls, parseCsvTags } from './shared'

export function BudgetTierPanel({ apiKey, canManage }: { apiKey: string; canManage: boolean }) {
  const emptyForm = {
    name: '',
    max_spend_usd: '',
    period_type: 'monthly',
    rpm_limit: '',
    tpm_limit: '',
    allowed_models: '',
    is_default: false,
  }
  const [tiers, setTiers] = useState<BudgetTier[]>([])
  const [tierQuery, setTierQuery] = useState('')
  const [tierSort, setTierSort] = useState<'name' | 'spend' | 'keys'>('name')
  const visibleTiers = useMemo(() => {
    const q = tierQuery.trim().toLowerCase()
    const list = q ? tiers.filter((t) => t.name.toLowerCase().includes(q)) : [...tiers]
    if (tierSort === 'spend') list.sort((a, b) => Number(b.max_spend_usd ?? -1) - Number(a.max_spend_usd ?? -1))
    else if (tierSort === 'keys') list.sort((a, b) => (b.key_count ?? 0) - (a.key_count ?? 0))
    else list.sort((a, b) => a.name.localeCompare(b.name))
    return list
  }, [tiers, tierQuery, tierSort])
  const [keys, setKeys] = useState<ApiKeyResponse[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editId, setEditId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [assigningKeyId, setAssigningKeyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [tierData, keyData] = await Promise.all([
        listBudgetTiers(apiKey, { limit: 500 }),
        listApiKeys(apiKey),
      ])
      setTiers(tierData.items)
      setKeys(keyData.filter((item) => !item.is_session))
    } catch {
      toast.error('Failed to load quota tiers')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { void load() }, [load])

  function startEdit(tier: BudgetTier) {
    setEditId(tier.id)
    setForm({
      name: tier.name,
      max_spend_usd: tier.max_spend_usd != null ? String(tier.max_spend_usd) : '',
      period_type: tier.period_type,
      rpm_limit: tier.rpm_limit != null ? String(tier.rpm_limit) : '',
      tpm_limit: tier.tpm_limit != null ? String(tier.tpm_limit) : '',
      allowed_models: tier.allowed_models?.join(', ') ?? '',
      is_default: tier.is_default,
    })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const body: {
        name: string
        max_spend_usd?: number
        period_type?: string
        rpm_limit?: number
        tpm_limit?: number
        allowed_models?: string[]
        is_default?: boolean
      } = {
        name: form.name.trim(),
        period_type: form.period_type,
        is_default: form.is_default,
      }
      if (form.max_spend_usd) body.max_spend_usd = parseFloat(form.max_spend_usd)
      if (form.rpm_limit) body.rpm_limit = parseInt(form.rpm_limit, 10)
      if (form.tpm_limit) body.tpm_limit = parseInt(form.tpm_limit, 10)
      if (form.allowed_models.trim()) body.allowed_models = parseCsvTags(form.allowed_models)
      if (editId) {
        await updateBudgetTier(apiKey, editId, body)
        toast.success('Budget tier updated')
      } else {
        await createBudgetTier(apiKey, body)
        toast.success('Budget tier created')
      }
      setForm(emptyForm)
      setEditId(null)
      await load()
    } catch {
      toast.error('Failed to save budget tier')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(tierId: string) {
    if (!confirm('Delete this budget tier?')) return
    try {
      await deleteBudgetTier(apiKey, tierId)
      setTiers((prev) => prev.filter((item) => item.id !== tierId))
      toast.success('Budget tier deleted')
      await load()
    } catch {
      toast.error('Failed to delete budget tier')
    }
  }

  async function handleAssign(keyId: string, tierId: string) {
    setAssigningKeyId(keyId)
    try {
      const assignedTierId = tierId || null
      await assignTierToKey(apiKey, keyId, assignedTierId)
      setKeys((prev) => prev.map((item) => (item.id === keyId ? { ...item, budget_tier_id: assignedTierId } : item)))
      toast.success('API key quota tier updated')
    } catch {
      toast.error('Failed to assign tier')
    } finally {
      setAssigningKeyId(null)
    }
  }

  const tierNameById = Object.fromEntries(tiers.map((tier) => [tier.id, tier.name]))

  return (
    <section id="gateway-quota-tiers" className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold dark:text-white">API Key Quota Tiers</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Manage reusable RPM and TPM quota profiles here inside Gateway, then assign them directly to API keys.
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {canManage && (
        <form onSubmit={handleSubmit} className="grid gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputCls} placeholder="Tier name" required />
          <input value={form.max_spend_usd} onChange={(e) => setForm({ ...form, max_spend_usd: e.target.value })} className={inputCls} placeholder="Max spend USD" type="number" step="0.01" />
          <select value={form.period_type} onChange={(e) => setForm({ ...form, period_type: e.target.value })} className={inputCls}>
            <option value="daily">Daily</option>
            <option value="monthly">Monthly</option>
            <option value="total">Total</option>
          </select>
          <input value={form.rpm_limit} onChange={(e) => setForm({ ...form, rpm_limit: e.target.value })} className={inputCls} placeholder="RPM limit" type="number" />
          <input value={form.tpm_limit} onChange={(e) => setForm({ ...form, tpm_limit: e.target.value })} className={inputCls} placeholder="TPM limit" type="number" />
          <input value={form.allowed_models} onChange={(e) => setForm({ ...form, allowed_models: e.target.value })} className={`${inputCls} lg:col-span-2`} placeholder="Allowed models (csv)" />
          <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
            <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
            Default tier
          </label>
          <div className="lg:col-span-3 flex items-center gap-2">
            <button type="submit" disabled={saving} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {saving ? 'Saving...' : editId ? 'Update tier' : 'Create tier'}
            </button>
            {editId && (
              <button type="button" onClick={() => { setEditId(null); setForm(emptyForm) }} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                Cancel
              </button>
            )}
          </div>
        </form>
      )}

      {tiers.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={tierQuery}
            onChange={(e) => setTierQuery(e.target.value)}
            placeholder="Search tiers…"
            className="min-w-[200px] flex-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
          <select
            value={tierSort}
            onChange={(e) => setTierSort(e.target.value as typeof tierSort)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            <option value="name">Sort: name</option>
            <option value="spend">Sort: spend cap</option>
            <option value="keys">Sort: keys assigned</option>
          </select>
          <span className="text-xs text-slate-500 dark:text-slate-400">{visibleTiers.length} of {tiers.length}</span>
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        {tiers.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400 lg:col-span-2">
            No quota tiers configured yet.
          </div>
        ) : visibleTiers.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-6 text-center text-sm text-slate-400 lg:col-span-2">
            No tiers match &ldquo;{tierQuery}&rdquo;.
          </div>
        ) : visibleTiers.map((tier) => (
          <div key={tier.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm dark:text-slate-100">{tier.name}</span>
                  {tier.is_default && <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">default</span>}
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${tier.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                    {tier.is_active ? 'active' : 'inactive'}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                  <span className="rounded-full bg-sky-100 px-2 py-0.5 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">rpm: {tier.rpm_limit ?? '—'}</span>
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">tpm: {tier.tpm_limit ?? '—'}</span>
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">keys: {tier.key_count}</span>
                  <span className="rounded-full bg-violet-100 px-2 py-0.5 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">spend: {tier.max_spend_usd != null ? `$${Number(tier.max_spend_usd).toFixed(2)}` : '—'}</span>
                </div>
                {tier.allowed_models?.length ? (
                  <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">{tier.allowed_models.join(', ')}</p>
                ) : null}
              </div>
              {canManage && (
                <div className="flex gap-2">
                  <button onClick={() => startEdit(tier)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                    Edit
                  </button>
                  <button onClick={() => void handleDelete(tier.id)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                    Delete
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold dark:text-white">Assign tiers to API keys</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">API keys inherit RPM and TPM quotas from the selected tier.</p>
          </div>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="border-b border-slate-200 dark:border-slate-700 text-slate-500">
              <tr>
                <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide">API Key</th>
                <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide">Workspace</th>
                <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide">Current Tier</th>
                <th className="px-3 py-2 text-left font-semibold uppercase tracking-wide">Assign</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
              {keys.map((key) => (
                <tr key={key.id}>
                  <td className="px-3 py-2">
                    <div className="font-mono text-slate-700 dark:text-slate-100">{key.name || key.key_prefix}</div>
                    <div className="text-slate-400">{key.key_prefix}</div>
                  </td>
                  <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{key.workspace_name || '—'}</td>
                  <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{key.budget_tier_id ? (tierNameById[key.budget_tier_id] || 'Assigned') : 'Unassigned'}</td>
                  <td className="px-3 py-2">
                    <select
                      value={key.budget_tier_id ?? ''}
                      onChange={(e) => void handleAssign(key.id, e.target.value)}
                      disabled={assigningKeyId === key.id}
                      className={`${inputCls} min-w-[220px]`}
                    >
                      <option value="">No tier</option>
                      {tiers.map((tier) => (
                        <option key={tier.id} value={tier.id}>{tier.name}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
