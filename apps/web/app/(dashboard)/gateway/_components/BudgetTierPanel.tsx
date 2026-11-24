'use client'

import { useEffect, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { listApiKeys, listBudgetTiers, createBudgetTier, updateBudgetTier, deleteBudgetTier, assignTierToKey, apiErrorMessage } from '@/lib/api'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { SectionError } from '@/components/ui/async-card'
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
  const [error, setError] = useState('')
  const { confirm, dialog } = useConfirm()
  const [keys, setKeys] = useState<ApiKeyResponse[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editId, setEditId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [assigningKeyId, setAssigningKeyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [tierData, keyData] = await Promise.all([
        listBudgetTiers(apiKey, { limit: 500 }),
        listApiKeys(apiKey),
      ])
      setTiers(tierData.items)
      setKeys(keyData.filter((item) => !item.is_session))
    } catch (err) {
      setError(apiErrorMessage(err, "Couldn't load quota tiers"))
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
      // On edit an emptied field is sent as null, which clears that limit (G-20).
      const clear = editId ? null : undefined
      const body = {
        name: form.name.trim(),
        period_type: form.period_type,
        is_default: form.is_default,
        max_spend_usd: form.max_spend_usd ? parseFloat(form.max_spend_usd) : clear,
        rpm_limit: form.rpm_limit ? parseInt(form.rpm_limit, 10) : clear,
        tpm_limit: form.tpm_limit ? parseInt(form.tpm_limit, 10) : clear,
        allowed_models: form.allowed_models.trim() ? parseCsvTags(form.allowed_models) : clear,
      }
      if (editId) {
        await updateBudgetTier(apiKey, editId, body)
        toast.success('Budget tier updated')
      } else {
        await createBudgetTier(apiKey, {
          ...body,
          max_spend_usd: body.max_spend_usd ?? undefined,
          rpm_limit: body.rpm_limit ?? undefined,
          tpm_limit: body.tpm_limit ?? undefined,
          allowed_models: body.allowed_models ?? undefined,
        })
        toast.success('Budget tier created')
      }
      setForm(emptyForm)
      setEditId(null)
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to save budget tier'))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(tier: BudgetTier) {
    const tierId = tier.id
    if (!(await confirm({
      title: `Delete tier '${tier.name}'?`,
      description: `${tier.key_count} key(s) lose this tier and fall back to the default tier, if any.`,
      destructive: true,
      confirmLabel: 'Delete',
    }))) return
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
  const limit = (v: number | string | null | undefined) => (v == null ? '—' : String(v))
  const tierColumns: DataTableColumn<BudgetTier>[] = [
    {
      key: 'name',
      header: 'Tier',
      sortable: true,
      render: (t) => (
        <span className="flex flex-wrap items-center gap-1.5">
          <span className="font-mono">{t.name}</span>
          {t.is_default && <span className="rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">default</span>}
        </span>
      ),
    },
    { key: 'rpm_limit', header: 'Req/min', sortable: true, value: (t) => t.rpm_limit ?? null, render: (t) => limit(t.rpm_limit) },
    { key: 'tpm_limit', header: 'Tokens/min', sortable: true, value: (t) => t.tpm_limit ?? null, render: (t) => limit(t.tpm_limit) },
    {
      key: 'allowed_models',
      header: 'Allowed models',
      value: (t) => t.allowed_models?.join(' ') ?? '',
      render: (t) => (t.allowed_models?.length ? t.allowed_models.join(', ') : <span className="text-slate-400">any</span>),
    },
    {
      key: 'max_spend_usd',
      header: 'Spend cap',
      sortable: true,
      value: (t) => (t.max_spend_usd != null ? Number(t.max_spend_usd) : null),
      render: (t) => (t.max_spend_usd != null ? `$${Number(t.max_spend_usd).toFixed(2)} / ${t.period_type}` : '—'),
    },
    { key: 'key_count', header: 'Keys', sortable: true, value: (t) => t.key_count ?? 0 },
    ...(canManage
      ? [{
          key: 'actions',
          header: 'Actions',
          value: () => '',
          render: (t: BudgetTier) => (
            <span className="flex gap-1.5">
              <button type="button" aria-label={`Edit tier ${t.name}`} onClick={() => startEdit(t)} className="rounded-md border border-slate-200 px-2 py-0.5 text-[11px] text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700">Edit</button>
              <button type="button" aria-label={`Delete tier ${t.name}`} onClick={() => void handleDelete(t)} className="rounded-md border border-rose-200 px-2 py-0.5 text-[11px] text-rose-600 hover:bg-rose-50 dark:border-rose-900/40 dark:text-rose-300 dark:hover:bg-rose-950/30">Delete</button>
            </span>
          ),
        } satisfies DataTableColumn<BudgetTier>]
      : []),
  ]

  return (
    <section id="gateway-quota-tiers" className="space-y-4">
      {dialog}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold dark:text-white">API Key Quota Tiers</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Reusable per-key limits. The gateway enforces requests/min, tokens/min (estimated at request time) and allowed models
            for every key on the tier; keys without a tier use the default tier. The spend cap is a FinOps limit.
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          aria-label="Refresh quota tiers"
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {canManage && (
        <form onSubmit={handleSubmit} className="grid gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <input aria-label="Tier name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputCls} placeholder="Tier name" required />
          <input value={form.max_spend_usd} onChange={(e) => setForm({ ...form, max_spend_usd: e.target.value })} className={inputCls} aria-label="Max spend in USD (empty for none)" placeholder="Max spend USD" type="number" step="0.01" />
          <select aria-label="Spend cap period" value={form.period_type} onChange={(e) => setForm({ ...form, period_type: e.target.value })} className={inputCls}>
            <option value="daily">Daily</option>
            <option value="monthly">Monthly</option>
            <option value="total">Total</option>
          </select>
          <input value={form.rpm_limit} onChange={(e) => setForm({ ...form, rpm_limit: e.target.value })} className={inputCls} aria-label="Requests per minute per key (empty for none)" placeholder="RPM limit" type="number" />
          <input value={form.tpm_limit} onChange={(e) => setForm({ ...form, tpm_limit: e.target.value })} className={inputCls} aria-label="Tokens per minute per key (empty for none)" placeholder="TPM limit" type="number" />
          <input value={form.allowed_models} onChange={(e) => setForm({ ...form, allowed_models: e.target.value })} className={`${inputCls} lg:col-span-2`} aria-label="Allowed model aliases, comma separated (empty for any)" placeholder="Allowed models (csv)" />
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

      {error && <SectionError message={error} onRetry={() => void load()} />}
      <DataTable<BudgetTier>
        label="API key quota tiers"
        urlPrefix="tier"
        rows={tiers}
        rowKey={(t) => t.id}
        pageSize={10}
        searchPlaceholder="Search tiers…"
        csvFileName="quota-tiers.csv"
        emptyTitle="No quota tiers yet"
        emptyDescription="Create a tier, then assign it to API keys below."
        columns={tierColumns}
      />

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold dark:text-white">Assign tiers to API keys</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">A key gets the limits of the tier picked here; with no tier it gets the default tier.</p>
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
                      disabled={assigningKeyId === key.id || !canManage}
                      aria-label={`Quota tier for ${key.name || key.key_prefix}`}
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
