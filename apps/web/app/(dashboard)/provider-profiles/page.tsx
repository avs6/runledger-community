'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Database, Plus, Pencil, Trash2, RefreshCw, Search, SlidersHorizontal, X } from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import {
  listProviderPricing,
  createProviderPricing,
  updateProviderPricing,
  deleteProviderPricing,
  repriceProvider,
} from '@/lib/api'
import type { ProviderPricingResponse } from '@/types/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

interface EditState {
  id: string
  isGlobal: boolean
  input: string
  output: string
  cached: string
}

export default function ProviderProfilesPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { isOrgAdmin, isPlatformAdmin } = useRole()
  const canManage = isOrgAdmin || isPlatformAdmin

  const [pricing, setPricing] = useState<ProviderPricingResponse[]>([])
  const [loading, setLoading] = useState(true)

  // Add form
  const [showForm, setShowForm] = useState(false)
  const [newProvider, setNewProvider] = useState('')
  const [newModel, setNewModel] = useState('')
  const [newInputCost, setNewInputCost] = useState('')
  const [newOutputCost, setNewOutputCost] = useState('')
  const [newCachedCost, setNewCachedCost] = useState('')
  const [addingPricing, setAddingPricing] = useState(false)

  // Edit
  const [editState, setEditState] = useState<EditState | null>(null)
  const [savingEdit, setSavingEdit] = useState(false)

  // Filters
  const [pricingSearch, setPricingSearch] = useState('')
  const [pricingProviderFilter, setPricingProviderFilter] = useState('')
  const [pricingScopeFilter, setPricingScopeFilter] = useState<'all' | 'workspace' | 'global'>('all')

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const data = await listProviderPricing(apiKey)
      setPricing(data.items)
    } catch {
      toast.error('Failed to load provider profiles')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { load() }, [load])

  async function handleAddPricing(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !newProvider.trim() || !newModel.trim()) return
    setAddingPricing(true)
    try {
      const created = await createProviderPricing(apiKey, {
        provider: newProvider.trim(),
        model: newModel.trim(),
        input_cost_per_1m: newInputCost,
        output_cost_per_1m: newOutputCost,
        cached_input_cost_per_1m: newCachedCost.trim() || null,
      })
      setPricing((prev) => [created, ...prev])
      setNewProvider('')
      setNewModel('')
      setNewInputCost('')
      setNewOutputCost('')
      setNewCachedCost('')
      setShowForm(false)
      toast.success('Provider profile added')
    } catch {
      toast.error('Failed to add provider profile')
    } finally {
      setAddingPricing(false)
    }
  }

  function startEdit(p: ProviderPricingResponse) {
    setEditState({
      id: p.id,
      isGlobal: !p.workspace_id,
      input: parseFloat(p.input_cost_per_1m).toString(),
      output: parseFloat(p.output_cost_per_1m).toString(),
      cached: p.cached_input_cost_per_1m ? parseFloat(p.cached_input_cost_per_1m).toString() : '',
    })
  }

  async function handleSaveEdit() {
    if (!editState || !apiKey) return
    setSavingEdit(true)
    try {
      const body = {
        input_cost_per_1m: editState.input,
        output_cost_per_1m: editState.output,
        cached_input_cost_per_1m: editState.cached.trim() || null,
      }
      const updated = await updateProviderPricing(apiKey, editState.id, body)
      setPricing((prev) => prev.map((p) => (p.id === updated.id ? updated : p)))
      setEditState(null)
      toast.success('Provider profile updated')
    } catch {
      toast.error('Failed to update provider profile')
    } finally {
      setSavingEdit(false)
    }
  }

  async function handleReprice(provider: string, model: string) {
    if (!apiKey) return
    if (!confirm(`Reset all ${provider}/${model} costs to NULL and re-enrich? This may take a minute.`)) return
    try {
      const result = await repriceProvider(apiKey, { provider, model })
      toast.success(`Reprice queued — ${result.reset} calls reset`)
    } catch {
      toast.error('Failed to queue reprice')
    }
  }

  async function handleDeletePricing(pricingId: string) {
    if (!confirm('Delete this pricing profile?')) return
    try {
      await deleteProviderPricing(apiKey!, pricingId)
      setPricing((prev) => prev.filter((p) => p.id !== pricingId))
      toast.success('Provider profile deleted')
    } catch {
      toast.error('Failed to delete provider profile')
    }
  }

  // Derived filter
  const uniqueProviders = Array.from(new Set(pricing.map((p) => p.provider))).sort()
  const filteredPricing = pricing.filter((p) => {
    if (pricingScopeFilter === 'workspace' && !p.workspace_id) return false
    if (pricingScopeFilter === 'global' && p.workspace_id) return false
    if (pricingProviderFilter && p.provider !== pricingProviderFilter) return false
    if (pricingSearch) {
      const q = pricingSearch.toLowerCase()
      if (!p.provider.toLowerCase().includes(q) && !p.model.toLowerCase().includes(q)) return false
    }
    return true
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <RefreshCw className="h-5 w-5 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Database className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            <h1 className="text-2xl font-bold tracking-tight dark:text-white">Provider Profiles</h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Workspace-scoped pricing overrides for AI providers. These rates are used for cost calculations across all runs.
            {!canManage && (
              <span className="ml-1 text-amber-600 dark:text-amber-400">Read-only — Org Admin access required to add or edit profiles.</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="shrink-0 flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
          {canManage && (
            <button
              onClick={() => setShowForm((v) => !v)}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              {showForm ? 'Cancel' : 'Add Profile'}
            </button>
          )}
        </div>
      </div>

      {/* Add form */}
      {showForm && canManage && (
        <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-900/10 p-5">
          <h3 className="text-sm font-semibold text-indigo-800 dark:text-indigo-300 mb-3">New provider profile (workspace-scoped)</h3>
          <form onSubmit={handleAddPricing} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Provider *</label>
              <input type="text" placeholder="e.g. openai" value={newProvider} onChange={(e) => setNewProvider(e.target.value)} className={inputCls} required />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Model *</label>
              <input type="text" placeholder="e.g. gpt-4o" value={newModel} onChange={(e) => setNewModel(e.target.value)} className={inputCls} required />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Input cost / 1M tokens *</label>
              <input type="number" step="0.0001" placeholder="e.g. 5.00" value={newInputCost} onChange={(e) => setNewInputCost(e.target.value)} className={inputCls} required />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Output cost / 1M tokens *</label>
              <input type="number" step="0.0001" placeholder="e.g. 15.00" value={newOutputCost} onChange={(e) => setNewOutputCost(e.target.value)} className={inputCls} required />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Cached input cost / 1M (optional)</label>
              <input type="number" step="0.0001" placeholder="e.g. 1.25" value={newCachedCost} onChange={(e) => setNewCachedCost(e.target.value)} className={inputCls} />
            </div>
            <div className="flex items-end">
              <button type="submit" disabled={addingPricing || !newProvider.trim() || !newModel.trim()} className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
                {addingPricing ? 'Adding…' : 'Add Profile'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-40">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search provider or model…"
            value={pricingSearch}
            onChange={(e) => setPricingSearch(e.target.value)}
            className={`pl-8 ${inputCls}`}
          />
          {pricingSearch && (
            <button onClick={() => setPricingSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <select value={pricingProviderFilter} onChange={(e) => setPricingProviderFilter(e.target.value)} className={inputCls}>
          <option value="">All providers</option>
          {uniqueProviders.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <div className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 p-0.5">
          {(['all', 'workspace', 'global'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setPricingScopeFilter(s)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                pricingScopeFilter === s
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {s === 'all' ? 'All' : s === 'workspace' ? 'Workspace' : 'Global'}
            </button>
          ))}
        </div>
        {(pricingSearch || pricingProviderFilter || pricingScopeFilter !== 'all') && (
          <button
            onClick={() => { setPricingSearch(''); setPricingProviderFilter(''); setPricingScopeFilter('all') }}
            className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
          >
            <SlidersHorizontal className="h-3 w-3" /> Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        {filteredPricing.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-2">
            <Database className="h-8 w-8 text-slate-300 dark:text-slate-600" />
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {pricing.length === 0 ? 'No provider profiles yet.' : 'No profiles match the current filters.'}
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Provider / Model</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Input / 1M</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Output / 1M</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Cached / 1M</th>
                <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Scope</th>
                {canManage && <th className="px-4 py-2.5" />}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
              {filteredPricing.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="px-4 py-2.5">
                    <div className="flex flex-col">
                      <span className="font-medium capitalize dark:text-slate-200">{p.provider}</span>
                      <span className="font-mono text-xs text-slate-500 dark:text-slate-400">{p.model}</span>
                    </div>
                  </td>
                  {editState?.id === p.id ? (
                    <>
                      <td className="px-4 py-2">
                        <input type="number" step="0.0001" value={editState.input} onChange={(e) => setEditState({ ...editState, input: e.target.value })} className={`${inputCls} w-24 text-right`} />
                      </td>
                      <td className="px-4 py-2">
                        <input type="number" step="0.0001" value={editState.output} onChange={(e) => setEditState({ ...editState, output: e.target.value })} className={`${inputCls} w-24 text-right`} />
                      </td>
                      <td className="px-4 py-2">
                        <input type="number" step="0.0001" value={editState.cached} onChange={(e) => setEditState({ ...editState, cached: e.target.value })} className={`${inputCls} w-24 text-right`} placeholder="—" />
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-4 py-2.5 text-right font-mono text-xs dark:text-slate-300">${parseFloat(p.input_cost_per_1m).toFixed(4)}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs dark:text-slate-300">${parseFloat(p.output_cost_per_1m).toFixed(4)}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-400">{p.cached_input_cost_per_1m ? `$${parseFloat(p.cached_input_cost_per_1m).toFixed(4)}` : '—'}</td>
                    </>
                  )}
                  <td className="px-4 py-2.5 text-center">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${p.workspace_id ? 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                      {p.workspace_id ? 'Workspace' : 'Global'}
                    </span>
                  </td>
                  {canManage && (
                    <td className="px-4 py-2.5 text-right">
                      {editState?.id === p.id ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <button onClick={handleSaveEdit} disabled={savingEdit} className="rounded-lg bg-indigo-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
                            {savingEdit ? 'Saving…' : 'Save'}
                          </button>
                          <button onClick={() => setEditState(null)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-1 text-xs font-medium text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-0.5">
                          {p.workspace_id && (
                            <button onClick={() => startEdit(p)} className="rounded-lg p-1.5 text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors" title="Edit">
                              <Pencil className="h-3.5 w-3.5" />
                            </button>
                          )}
                          <button onClick={() => handleReprice(p.provider, p.model)} className="rounded-lg p-1.5 text-slate-400 hover:text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors" title="Re-enrich costs">
                            <RefreshCw className="h-3.5 w-3.5" />
                          </button>
                          {p.workspace_id && (
                            <button onClick={() => handleDeletePricing(p.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors" title="Delete">
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Info box */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4 text-sm text-slate-600 dark:text-slate-300">
        <p className="font-medium mb-1">About provider profiles</p>
        <ul className="space-y-1 text-xs text-slate-500 dark:text-slate-400 list-disc list-inside">
          <li>Workspace profiles override global defaults for cost calculations.</li>
          <li>Global profiles are set by platform admins and apply org-wide.</li>
          <li>The &ldquo;Re-enrich&rdquo; button (<RefreshCw className="inline h-3 w-3" />) resets past costs for that model and re-runs enrichment with the new rate.</li>
          <li>Costs are in USD per 1 million tokens.</li>
        </ul>
      </div>
    </div>
  )
}
