'use client'

import { useEffect, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { listApiKeys, listModelBudgets, createModelBudget, updateModelBudget, deleteModelBudget } from '@/lib/api'
import type { ApiKeyResponse, ModelBudget } from '@/types/api'
import { inputCls } from './shared'

export function ModelQuotaPanel({ apiKey, canManage }: { apiKey: string; canManage: boolean }) {
  const emptyForm = {
    model_pattern: '',
    max_spend_usd: '',
    period_type: 'monthly',
    rpm_limit: '',
    tpm_limit: '',
    action: 'block',
  }
  const [keys, setKeys] = useState<ApiKeyResponse[]>([])
  const [selectedKeyId, setSelectedKeyId] = useState('')
  const [items, setItems] = useState<ModelBudget[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editId, setEditId] = useState<string | null>(null)
  const [loadingKeys, setLoadingKeys] = useState(false)
  const [loadingItems, setLoadingItems] = useState(false)
  const [saving, setSaving] = useState(false)

  const loadKeys = useCallback(async () => {
    setLoadingKeys(true)
    try {
      const data = await listApiKeys(apiKey)
      const filtered = data.filter((item) => !item.is_session)
      setKeys(filtered)
      if (!selectedKeyId && filtered.length > 0) {
        setSelectedKeyId(filtered[0].id)
      }
    } catch {
      toast.error('Failed to load API keys for model quotas')
    } finally {
      setLoadingKeys(false)
    }
  }, [apiKey, selectedKeyId])

  const loadItems = useCallback(async () => {
    if (!selectedKeyId) {
      setItems([])
      return
    }
    setLoadingItems(true)
    try {
      const data = await listModelBudgets(apiKey, selectedKeyId)
      setItems(data.items)
    } catch {
      toast.error('Failed to load model quotas')
    } finally {
      setLoadingItems(false)
    }
  }, [apiKey, selectedKeyId])

  useEffect(() => { void loadKeys() }, [loadKeys])
  useEffect(() => { void loadItems() }, [loadItems])

  function startEdit(item: ModelBudget) {
    setEditId(item.id)
    setForm({
      model_pattern: item.model_pattern,
      max_spend_usd: item.max_spend_usd != null ? String(item.max_spend_usd) : '',
      period_type: item.period_type,
      rpm_limit: item.rpm_limit != null ? String(item.rpm_limit) : '',
      tpm_limit: item.tpm_limit != null ? String(item.tpm_limit) : '',
      action: item.action,
    })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedKeyId) return
    setSaving(true)
    try {
      const createBody: {
        model_pattern: string
        max_spend_usd?: number
        period_type?: string
        rpm_limit?: number
        tpm_limit?: number
        action?: string
      } = {
        model_pattern: form.model_pattern.trim(),
        period_type: form.period_type,
        action: form.action,
      }
      if (form.max_spend_usd) createBody.max_spend_usd = parseFloat(form.max_spend_usd)
      if (form.rpm_limit) createBody.rpm_limit = parseInt(form.rpm_limit, 10)
      if (form.tpm_limit) createBody.tpm_limit = parseInt(form.tpm_limit, 10)
      if (editId) {
        await updateModelBudget(apiKey, selectedKeyId, editId, createBody)
        toast.success('Model quota updated')
      } else {
        await createModelBudget(apiKey, selectedKeyId, createBody)
        toast.success('Model quota created')
      }
      setForm(emptyForm)
      setEditId(null)
      await loadItems()
    } catch {
      toast.error('Failed to save model quota')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(budgetId: string) {
    if (!selectedKeyId || !confirm('Delete this model quota?')) return
    try {
      await deleteModelBudget(apiKey, selectedKeyId, budgetId)
      setItems((prev) => prev.filter((item) => item.id !== budgetId))
      toast.success('Model quota deleted')
    } catch {
      toast.error('Failed to delete model quota')
    }
  }

  const selectedKey = keys.find((item) => item.id === selectedKeyId)

  return (
    <section id="gateway-model-quotas" className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold dark:text-white">Per-Model Quotas</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Manage per-model RPM, TPM, and spend limits for a selected API key directly from Gateway.
          </p>
        </div>
        <button
          onClick={() => { void loadKeys(); void loadItems() }}
          disabled={loadingKeys || loadingItems}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
        >
          {loadingKeys || loadingItems ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <label className="block">
            <span className="text-xs font-medium text-slate-600 dark:text-slate-300">API Key</span>
            <select value={selectedKeyId} onChange={(e) => setSelectedKeyId(e.target.value)} className={`${inputCls} mt-1 w-full`}>
              {keys.length === 0 && <option value="">No API keys</option>}
              {keys.map((key) => (
                <option key={key.id} value={key.id}>
                  {(key.name || key.key_prefix)} {key.workspace_name ? `• ${key.workspace_name}` : ''}
                </option>
              ))}
            </select>
          </label>
          <div className="text-xs text-slate-500 dark:text-slate-400">
            {selectedKey ? `Current tier: ${selectedKey.budget_tier_id ? 'assigned' : 'none'}` : 'Select a key to manage quotas.'}
          </div>
        </div>
      </div>

      {canManage && selectedKeyId && (
        <form onSubmit={handleSubmit} className="grid gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <input value={form.model_pattern} onChange={(e) => setForm({ ...form, model_pattern: e.target.value })} className={inputCls} placeholder="Model pattern" required />
          <input value={form.max_spend_usd} onChange={(e) => setForm({ ...form, max_spend_usd: e.target.value })} className={inputCls} placeholder="Max spend USD" type="number" step="0.01" />
          <select value={form.period_type} onChange={(e) => setForm({ ...form, period_type: e.target.value })} className={inputCls}>
            <option value="daily">Daily</option>
            <option value="monthly">Monthly</option>
            <option value="total">Total</option>
          </select>
          <input value={form.rpm_limit} onChange={(e) => setForm({ ...form, rpm_limit: e.target.value })} className={inputCls} placeholder="RPM limit" type="number" />
          <input value={form.tpm_limit} onChange={(e) => setForm({ ...form, tpm_limit: e.target.value })} className={inputCls} placeholder="TPM limit" type="number" />
          <select value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })} className={inputCls}>
            <option value="block">Block</option>
            <option value="notify">Notify</option>
            <option value="throttle">Throttle</option>
            <option value="downgrade">Downgrade</option>
            <option value="fallback">Fallback</option>
          </select>
          <div className="lg:col-span-3 flex items-center gap-2">
            <button type="submit" disabled={saving} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {saving ? 'Saving...' : editId ? 'Update model quota' : 'Create model quota'}
            </button>
            {editId && (
              <button type="button" onClick={() => { setEditId(null); setForm(emptyForm) }} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                Cancel
              </button>
            )}
          </div>
        </form>
      )}

      {selectedKeyId && (
        <div className="grid gap-3 lg:grid-cols-2">
          {items.length === 0 && !loadingItems ? (
            <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400 lg:col-span-2">
              No per-model quotas configured for this API key yet.
            </div>
          ) : items.map((item) => (
            <div key={item.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm dark:text-slate-100">{item.model_pattern}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">{item.period_type}</span>
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">{item.action}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                    <span className="rounded-full bg-sky-100 px-2 py-0.5 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">rpm: {item.rpm_limit ?? '—'}</span>
                    <span className="rounded-full bg-violet-100 px-2 py-0.5 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">tpm: {item.tpm_limit ?? '—'}</span>
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">spend: {item.max_spend_usd != null ? `$${Number(item.max_spend_usd).toFixed(2)}` : '—'}</span>
                  </div>
                </div>
                {canManage && (
                  <div className="flex gap-2">
                    <button onClick={() => startEdit(item)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                      Edit
                    </button>
                    <button onClick={() => void handleDelete(item.id)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                      Delete
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
