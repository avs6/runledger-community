'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Database, Plus, Pencil, Trash2, RefreshCw, Search, X, CloudDownload, Upload, FileDown, ChevronDown, ChevronUp } from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import {
  listProviderPricing,
  createProviderPricing,
  updateProviderPricing,
  deleteProviderPricing,
  repriceProvider,
  triggerPricingSync,
  importProviderPricing,
  getPricingExampleYaml,
  getProviderProfileFinopsPosture,
  getProviderProfileObservePosture,
  getProviderProfileRuntimePosture,
} from '@/lib/api'
import type { ProviderPricingResponse, ProviderProfileFinopsPosture, ProviderProfileObservePosture, ProviderProfileRuntimePosture } from '@/types/api'
import { num } from '@/lib/utils'

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500'

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

  const [showForm, setShowForm] = useState(false)
  const [newProvider, setNewProvider] = useState('')
  const [newModel, setNewModel] = useState('')
  const [newInputCost, setNewInputCost] = useState('')
  const [newOutputCost, setNewOutputCost] = useState('')
  const [newCachedCost, setNewCachedCost] = useState('')
  const [addingPricing, setAddingPricing] = useState(false)

  const [editState, setEditState] = useState<EditState | null>(null)
  const [savingEdit, setSavingEdit] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [importing, setImporting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [pricingSearch, setPricingSearch] = useState('')
  const [pricingProviderFilter, setPricingProviderFilter] = useState('')
  const [pricingScopeFilter, setPricingScopeFilter] = useState<'all' | 'workspace' | 'global'>('all')

  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [postureData, setPostureData] = useState<Record<string, ProviderProfileFinopsPosture>>({})
  const [observeData, setObserveData] = useState<Record<string, ProviderProfileObservePosture>>({})
  const [postureLoading, setPostureLoading] = useState<string | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<ProviderProfileRuntimePosture | null>(null)

  async function loadPosture(p: ProviderPricingResponse) {
    if (!apiKey) return
    if (postureData[p.id] && observeData[p.id]) return
    setPostureLoading(p.id)
    try {
      const [finops, observe] = await Promise.all([
        getProviderProfileFinopsPosture(apiKey, p.id).catch(() => null),
        getProviderProfileObservePosture(apiKey, p.id).catch(() => null),
      ])
      if (finops) setPostureData((prev) => ({ ...prev, [p.id]: finops }))
      if (observe) setObserveData((prev) => ({ ...prev, [p.id]: observe }))
    } finally {
      setPostureLoading(null)
    }
  }

  const load = useCallback(async () => {
    if (!apiKey || !canManage) { setLoading(false); return }
    setLoading(true)
    try {
      const data = await listProviderPricing(apiKey)
      setPricing(data.items)
    } catch {
      toast.error('Failed to load provider profiles')
    } finally {
      setLoading(false)
    }
  }, [apiKey, canManage])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!apiKey) return
    getProviderProfileRuntimePosture(apiKey).then(setRuntimePosture).catch(() => {})
  }, [apiKey])

  if (!canManage) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Provider Profiles</h1>
        <p className="mt-2 text-sm text-slate-500">Provider pricing management requires org-admin access.</p>
      </div>
    )
  }

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
      setNewProvider(''); setNewModel(''); setNewInputCost(''); setNewOutputCost(''); setNewCachedCost('')
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
      const updated = await updateProviderPricing(apiKey, editState.id, {
        input_cost_per_1m: editState.input,
        output_cost_per_1m: editState.output,
        cached_input_cost_per_1m: editState.cached.trim() || null,
      })
      setPricing((prev) => prev.map((p) => (p.id === updated.id ? updated : p)))
      setEditState(null)
      toast.success('Provider profile updated')
    } catch {
      toast.error('Failed to update provider profile')
    } finally {
      setSavingEdit(false)
    }
  }

  async function handlePullPricing() {
    if (!apiKey) return
    setSyncing(true)
    try {
      const result = await triggerPricingSync(apiKey, { force: true })
      toast.success(`Pricing updated: ${result.inserted} added, ${result.updated} updated, ${result.skipped} skipped`)
      await load()
    } catch (err: unknown) {
      toast.error(`Sync failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setSyncing(false)
    }
  }

  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !apiKey) return
    setImporting(true)
    try {
      const r = await importProviderPricing(apiKey, file)
      toast.success(`Imported: ${r.inserted} added, ${r.updated} updated, ${r.unchanged} unchanged`)
      if (r.errors.length) toast.warning(`${r.errors.length} row(s) skipped`)
      await load()
    } catch (err: unknown) {
      toast.error(`Import failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setImporting(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleDownloadExample() {
    if (!apiKey) return
    try {
      const yaml = await getPricingExampleYaml(apiKey)
      const blob = new Blob([yaml], { type: 'text/yaml' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = 'pricing.example.yml'; a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Could not fetch example file')
    }
  }

  async function handleReprice(provider: string, model: string) {
    if (!apiKey) return
    if (!confirm(`Reset all ${provider}/${model} costs to NULL and re-enrich?`)) return
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

  // Group by provider
  const grouped: Record<string, ProviderPricingResponse[]> = {}
  filteredPricing.forEach((p) => { ;(grouped[p.provider] ??= []).push(p) })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <RefreshCw className="h-5 w-5 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* ── Header ───────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 shadow-lg shadow-indigo-500/25">
            <Database className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Provider Profiles</h1>
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
              AI provider pricing catalog. Used for cost calculations across all runs and gateway routes.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <input ref={fileInputRef} type="file" accept=".yml,.yaml,text/yaml" onChange={handleImportFile} className="hidden" />
          <button onClick={() => fileInputRef.current?.click()} disabled={importing} className="flex items-center gap-1 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 px-2.5 py-1 text-[10px] font-semibold text-indigo-700 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-800/40 disabled:opacity-50">
            <Upload className={`h-3 w-3 ${importing ? 'animate-pulse' : ''}`} />{importing ? 'Importing…' : 'Import YAML'}
          </button>
          <button onClick={handleDownloadExample} className="flex items-center gap-1 rounded-lg bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700">
            <FileDown className="h-3 w-3" />Example
          </button>
          <button onClick={handlePullPricing} disabled={syncing} className="flex items-center gap-1 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 px-2.5 py-1 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300 hover:bg-emerald-200 dark:hover:bg-emerald-800/40 disabled:opacity-50">
            <CloudDownload className={`h-3 w-3 ${syncing ? 'animate-pulse' : ''}`} />{syncing ? 'Syncing…' : 'Pull Internet'}
          </button>
          <button onClick={load} className="flex items-center gap-1 rounded-lg bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700">
            <RefreshCw className="h-3 w-3" />Refresh
          </button>
          {canManage && (
            <button onClick={() => setShowForm((v) => !v)} className="flex items-center gap-1 rounded-lg bg-indigo-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-indigo-700">
              <Plus className="h-3 w-3" />{showForm ? 'Cancel' : 'Add Profile'}
            </button>
          )}
        </div>
      </div>

      {/* ── KPI strip ────────────────────────────── */}
      <div className="grid grid-cols-6 gap-2">
        {[
          { label: 'Profiles', value: pricing.length },
          { label: 'Providers', value: uniqueProviders.length },
          { label: 'Workspace', value: pricing.filter((p) => p.workspace_id).length },
          { label: 'Global', value: pricing.filter((p) => !p.workspace_id).length },
          { label: 'With Budgets', value: pricing.filter((p) => p.budget_count > 0).length, accent: true },
          { label: 'Runtime Alerts', value: runtimePosture?.observe_context?.monitoring_alerts ?? '—' },
        ].map(({ label, value, accent }) => (
          <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
            <p className={`text-sm font-bold ${accent ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* ── Quick nav chips ──────────────────────── */}
      <div className="flex flex-wrap gap-1.5">
        {[
          { label: 'Gateway', href: '/gateway' },
          { label: 'Guardrails', href: '/guardrails' },
          { label: 'Budgets', href: '/budgets' },
          { label: 'Billing', href: '/billing' },
          { label: 'Analytics', href: '/analytics/model-usage' },
          { label: 'Playground', href: '/playground' },
        ].map(({ label, href }) => (
          <Link key={label} href={href} className="rounded-full bg-indigo-100 dark:bg-indigo-900/30 px-2.5 py-1 text-[10px] font-semibold text-indigo-700 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-800/40 transition-colors">{label}</Link>
        ))}
      </div>

      {/* ── Add form ─────────────────────────────── */}
      {showForm && canManage && (
        <form onSubmit={handleAddPricing} className="grid gap-2 rounded-lg border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-900/10 p-3 sm:grid-cols-3 lg:grid-cols-6">
          <input type="text" placeholder="Provider (e.g. openai)" value={newProvider} onChange={(e) => setNewProvider(e.target.value)} className={inputCls} required />
          <input type="text" placeholder="Model (e.g. gpt-4o)" value={newModel} onChange={(e) => setNewModel(e.target.value)} className={inputCls} required />
          <input type="number" step="0.0001" placeholder="Input $/1M" value={newInputCost} onChange={(e) => setNewInputCost(e.target.value)} className={inputCls} required />
          <input type="number" step="0.0001" placeholder="Output $/1M" value={newOutputCost} onChange={(e) => setNewOutputCost(e.target.value)} className={inputCls} required />
          <input type="number" step="0.0001" placeholder="Cached $/1M (opt)" value={newCachedCost} onChange={(e) => setNewCachedCost(e.target.value)} className={inputCls} />
          <button type="submit" disabled={addingPricing || !newProvider.trim() || !newModel.trim()} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
            {addingPricing ? 'Adding…' : 'Add Profile'}
          </button>
        </form>
      )}

      {/* ── Filters ──────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-40">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search provider or model…"
            value={pricingSearch}
            onChange={(e) => setPricingSearch(e.target.value)}
            className={`pl-7 ${inputCls}`}
          />
          {pricingSearch && (
            <button onClick={() => setPricingSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
        <select value={pricingProviderFilter} onChange={(e) => setPricingProviderFilter(e.target.value)} className={`w-auto ${inputCls}`}>
          <option value="">All providers</option>
          {uniqueProviders.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <div className="flex items-center gap-0.5 rounded-lg border border-slate-200 dark:border-slate-700 p-0.5">
          {(['all', 'workspace', 'global'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setPricingScopeFilter(s)}
              className={`rounded-md px-2 py-1 text-[10px] font-semibold transition-colors ${pricingScopeFilter === s ? 'bg-indigo-600 text-white' : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
            >
              {s === 'all' ? 'All' : s === 'workspace' ? 'Workspace' : 'Global'}
            </button>
          ))}
        </div>
        <span className="text-[10px] text-slate-400">{filteredPricing.length} of {pricing.length} profiles</span>
      </div>

      {/* ── Provider cards ────────────────────────── */}
      {filteredPricing.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 dark:border-slate-700 py-12 gap-2">
          <Database className="h-8 w-8 text-slate-300 dark:text-slate-600" />
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {pricing.length === 0 ? 'No pricing yet — import a YAML to load your catalog.' : 'No profiles match the current filters.'}
          </p>
          {pricing.length === 0 && canManage && (
            <button onClick={() => fileInputRef.current?.click()} className="mt-1 flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700">
              <Upload className="h-3 w-3" /> Import pricing YAML
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {Object.entries(grouped).map(([provider, models]) => (
            <div key={provider} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 overflow-hidden">
              {/* Provider header */}
              <div className="flex items-center justify-between px-3 py-2 bg-slate-50/80 dark:bg-slate-800/60 border-b border-slate-200/60 dark:border-slate-700/40">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-900 dark:text-white capitalize">{provider}</span>
                  <span className="rounded-full bg-indigo-100 dark:bg-indigo-900/30 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 dark:text-indigo-300">{models.length} models</span>
                </div>
              </div>

              {/* Model table */}
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-slate-700/40">
                    <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Model</th>
                    <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Input/1M</th>
                    <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Output/1M</th>
                    <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Cached/1M</th>
                    <th className="px-3 py-1.5 text-center text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Scope</th>
                    <th className="px-3 py-1.5 text-center text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Tags</th>
                    {canManage && <th className="px-3 py-1.5 w-24" />}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100/60 dark:divide-slate-700/30">
                  {models.map((p) => {
                    const isExpanded = expandedId === p.id
                    const finops = postureData[p.id]
                    const observe = observeData[p.id]
                    return (
                      <>
                        <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors group">
                          <td className="px-3 py-1.5">
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => {
                                  if (isExpanded) { setExpandedId(null) } else { setExpandedId(p.id); void loadPosture(p) }
                                }}
                                className="text-slate-400 hover:text-indigo-500"
                              >
                                {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                              </button>
                              <span className="font-mono font-medium text-slate-900 dark:text-slate-100">{p.display_name || p.model}</span>
                              {p.display_name && <span className="font-mono text-[10px] text-slate-400">{p.model}</span>}
                            </div>
                          </td>
                          {editState?.id === p.id ? (
                            <>
                              <td className="px-3 py-1"><input type="number" step="0.0001" value={editState.input} onChange={(e) => setEditState({ ...editState, input: e.target.value })} className={`${inputCls} w-20 text-right`} /></td>
                              <td className="px-3 py-1"><input type="number" step="0.0001" value={editState.output} onChange={(e) => setEditState({ ...editState, output: e.target.value })} className={`${inputCls} w-20 text-right`} /></td>
                              <td className="px-3 py-1"><input type="number" step="0.0001" value={editState.cached} onChange={(e) => setEditState({ ...editState, cached: e.target.value })} className={`${inputCls} w-20 text-right`} placeholder="—" /></td>
                            </>
                          ) : (
                            <>
                              <td className="px-3 py-1.5 text-right font-mono text-slate-700 dark:text-slate-300">${parseFloat(p.input_cost_per_1m).toFixed(4)}</td>
                              <td className="px-3 py-1.5 text-right font-mono text-slate-700 dark:text-slate-300">${parseFloat(p.output_cost_per_1m).toFixed(4)}</td>
                              <td className="px-3 py-1.5 text-right font-mono text-slate-400">{p.cached_input_cost_per_1m ? `$${parseFloat(p.cached_input_cost_per_1m).toFixed(4)}` : '—'}</td>
                            </>
                          )}
                          <td className="px-3 py-1.5 text-center">
                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${p.workspace_id ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                              {p.workspace_id ? 'WS' : 'Global'}
                            </span>
                          </td>
                          <td className="px-3 py-1.5 text-center">
                            <div className="flex flex-wrap justify-center gap-0.5">
                              {p.tags.map((t) => (
                                <span key={t} className="rounded-full bg-sky-100 dark:bg-sky-900/30 px-1.5 py-0.5 text-[9px] font-medium text-sky-700 dark:text-sky-300">{t}</span>
                              ))}
                            </div>
                          </td>
                          {canManage && (
                            <td className="px-3 py-1.5 text-right">
                              {editState?.id === p.id ? (
                                <div className="flex items-center justify-end gap-1">
                                  <button onClick={handleSaveEdit} disabled={savingEdit} className="rounded bg-indigo-600 px-2 py-0.5 text-[10px] font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{savingEdit ? '…' : 'Save'}</button>
                                  <button onClick={() => setEditState(null)} className="rounded border border-slate-200 dark:border-slate-700 px-2 py-0.5 text-[10px] text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700">Cancel</button>
                                </div>
                              ) : (
                                <div className="flex items-center justify-end gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                  {p.workspace_id && (
                                    <button onClick={() => startEdit(p)} className="rounded p-1 text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20" title="Edit">
                                      <Pencil className="h-3 w-3" />
                                    </button>
                                  )}
                                  <button onClick={() => handleReprice(p.provider, p.model)} className="rounded p-1 text-slate-400 hover:text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20" title="Re-enrich costs">
                                    <RefreshCw className="h-3 w-3" />
                                  </button>
                                  {p.workspace_id && (
                                    <button onClick={() => handleDeletePricing(p.id)} className="rounded p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20" title="Delete">
                                      <Trash2 className="h-3 w-3" />
                                    </button>
                                  )}
                                </div>
                              )}
                            </td>
                          )}
                        </tr>
                        {isExpanded && (
                          <tr key={`${p.id}-detail`}>
                            <td colSpan={canManage ? 7 : 6} className="px-3 py-2 bg-slate-50/50 dark:bg-slate-800/30">
                              {postureLoading === p.id ? (
                                <div className="flex items-center gap-2 text-xs text-slate-400"><RefreshCw className="h-3 w-3 animate-spin" /> Loading posture data...</div>
                              ) : (
                                <div className="grid gap-2 sm:grid-cols-2">
                                  {/* FinOps posture */}
                                  {finops && (
                                    <div className="rounded-lg border border-slate-200/60 dark:border-slate-700/40 p-2 space-y-1.5">
                                      <h4 className="text-[10px] font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider">FinOps Posture</h4>
                                      <div className="flex flex-wrap gap-1">
                                        {[
                                          `${finops.budgets.budget_count} budgets`,
                                          `${finops.budgets.active_budget_count} active`,
                                          `$${num(finops.budgets.total_limit_usd).toFixed(2)} limit`,
                                          `${finops.budgets.breach_count} breaches`,
                                          `${finops.overrides.override_count} overrides`,
                                          `${finops.billing.billing_period_count} billing periods`,
                                          `${finops.chargeback.chargeback_rule_count} chargeback rules`,
                                        ].map((chip) => (
                                          <span key={chip} className="rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-1.5 py-0.5 text-[9px] font-medium text-emerald-700 dark:text-emerald-300">{chip}</span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                  {/* Observe posture */}
                                  {observe && (
                                    <div className="rounded-lg border border-slate-200/60 dark:border-slate-700/40 p-2 space-y-1.5">
                                      <h4 className="text-[10px] font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Observe Posture</h4>
                                      <div className="flex flex-wrap gap-1">
                                        {[
                                          `${observe.runs.run_count} runs`,
                                          `${observe.runs.request_count} requests`,
                                          `${observe.runs.error_count} errors`,
                                          `$${num(observe.cost.total_cost_usd).toFixed(4)} cost`,
                                          `$${num(observe.cost.total_savings_usd).toFixed(4)} saved`,
                                          `${observe.tokens.input_tokens.toLocaleString()} in tokens`,
                                          `${observe.tokens.output_tokens.toLocaleString()} out tokens`,
                                          observe.performance.avg_latency_ms != null ? `${observe.performance.avg_latency_ms}ms avg` : null,
                                        ].filter(Boolean).map((chip) => (
                                          <span key={chip} className="rounded-full bg-sky-100 dark:bg-sky-900/30 px-1.5 py-0.5 text-[9px] font-medium text-sky-700 dark:text-sky-300">{chip}</span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                  {/* Quick links */}
                                  <div className="sm:col-span-2 flex flex-wrap gap-1.5">
                                    {[
                                      { label: 'Budgets', href: `/budgets?scope_type=provider_profile&scope_id=${encodeURIComponent(p.id)}` },
                                      { label: 'Budget Overrides', href: `/budgets?scope_type=provider_profile&scope_id=${encodeURIComponent(p.id)}&view=overrides` },
                                      { label: 'Billing', href: '/billing' },
                                      { label: 'Chargeback', href: '/chargeback' },
                                      { label: 'Gateway', href: '/gateway' },
                                      { label: 'Playground', href: '/playground' },
                                    ].map(({ label, href }) => (
                                      <Link key={label} href={href} className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[9px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700">{label}</Link>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {/* ── Runtime posture strip ─────────────────── */}
      {runtimePosture && (
        <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3 space-y-2">
          <h3 className="text-[10px] font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Runtime & Scope Posture</h3>
          <div className="flex flex-wrap gap-1.5">
            {[
              `${runtimePosture.provider_profiles} profiles`,
              `${runtimePosture.finops_context.budget_notifications} budget notifications`,
              `${runtimePosture.finops_context.ledger_snapshots} ledger snapshots`,
              `${runtimePosture.org_context.users} users`,
              `${runtimePosture.observe_context.monitoring_alerts} alerts`,
              `${runtimePosture.governance_context.mcp_servers} MCP servers`,
              `${runtimePosture.governance_context.search_tools} search tools`,
              `${runtimePosture.governance_context.capture_policies} capture policies`,
            ].map((chip) => (
              <span key={chip} className="rounded-full bg-violet-100 dark:bg-violet-900/30 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">{chip}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
