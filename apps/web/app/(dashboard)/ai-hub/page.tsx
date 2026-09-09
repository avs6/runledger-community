'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  ArrowRight,
  Box,
  ChevronDown,
  ChevronUp,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Star,
  Trash2,
  X,
  Zap,
} from 'lucide-react'
import {
  addHubModel,
  deleteHubModel,
  getHubModelCostPosture,
  getHubModelGovernance,
  listHubModels,
  requestHubAccess,
  syncHubProvider,
  updateHubModel,
} from '@/lib/api'
import type { HubModelCostPosture, HubModelGovernanceStatus } from '@/types/api'
import type { HubModelResponse } from '@/types/api'

const inputCls =
  'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100'

type ModelFormState = {
  name: string
  provider: string
  description: string
  capabilities: string
  contextWindow: string
  inputCost: string
  outputCost: string
  tags: string
  isFeatured: boolean
  isPublic: boolean
  isDeprecated: boolean
  deprecationNotice: string
}

const emptyForm: ModelFormState = {
  name: '',
  provider: '',
  description: '',
  capabilities: '',
  contextWindow: '',
  inputCost: '',
  outputCost: '',
  tags: '',
  isFeatured: false,
  isPublic: true,
  isDeprecated: false,
  deprecationNotice: '',
}

function parseCsv(value: string): string[] {
  return value
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

function modelToForm(model: HubModelResponse): ModelFormState {
  return {
    name: model.name,
    provider: model.provider,
    description: model.description ?? '',
    capabilities: (model.capabilities ?? []).join(', '),
    contextWindow: model.context_window != null ? String(model.context_window) : '',
    inputCost: model.input_cost_per_1k != null ? String(model.input_cost_per_1k) : '',
    outputCost: model.output_cost_per_1k != null ? String(model.output_cost_per_1k) : '',
    tags: (model.tags ?? []).join(', '),
    isFeatured: model.is_featured,
    isPublic: model.is_public,
    isDeprecated: model.is_deprecated,
    deprecationNotice: model.deprecation_notice ?? '',
  }
}

function badgeCls(tone: 'blue' | 'amber' | 'emerald' | 'slate') {
  const map = {
    blue: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300',
    amber: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
    slate: 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300',
  }
  return `inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${map[tone]}`
}

export default function AiHubPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey

  const [models, setModels] = useState<HubModelResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [search, setSearch] = useState('')
  const [filterProvider, setFilterProvider] = useState('')
  const [filterTag, setFilterTag] = useState('')
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [showSyncModal, setShowSyncModal] = useState(false)
  const [syncProviderName, setSyncProviderName] = useState('huggingface')
  const [syncToken, setSyncToken] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [form, setForm] = useState<ModelFormState>(emptyForm)
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null)
  const [costPosture, setCostPosture] = useState<HubModelCostPosture | null>(null)
  const [govStatus, setGovStatus] = useState<HubModelGovernanceStatus | null>(null)
  const [loadingPosture, setLoadingPosture] = useState(false)
  const [expandedCardId, setExpandedCardId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid')

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const res = await listHubModels(apiKey, {
        featured_only: featuredOnly,
        provider: filterProvider || undefined,
        tag: filterTag || undefined,
      })
      setModels(res.items)
    } catch {
      toast.error('Failed to load the model catalog')
    } finally {
      setLoading(false)
    }
  }, [apiKey, featuredOnly, filterProvider, filterTag])

  useEffect(() => {
    load()
  }, [load])

  const filteredModels = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return models
    return models.filter(model => {
      const haystack = [
        model.name,
        model.provider,
        model.description ?? '',
        ...(model.tags ?? []),
        ...(model.capabilities ?? []),
      ]
        .join(' ')
        .toLowerCase()
      return haystack.includes(needle)
    })
  }, [models, search])

  const providers = useMemo(() => Array.from(new Set(models.map(model => model.provider))).sort(), [models])
  const tags = useMemo(() => Array.from(new Set(models.flatMap(model => model.tags ?? []))).sort(), [models])

  const summary = useMemo(() => {
    const total = models.length
    const featured = models.filter(model => model.is_featured).length
    const deprecated = models.filter(model => model.is_deprecated).length
    const accessRequests = models.reduce((sum, model) => sum + (model.access_request_count ?? 0), 0)
    const providerCount = new Set(models.map(m => m.provider)).size
    return { total, featured, deprecated, accessRequests, providerCount }
  }, [models])

  function resetForm() {
    setForm(emptyForm)
    setEditingId(null)
    setShowForm(false)
  }

  function openCreateForm() {
    setEditingId(null)
    setForm(emptyForm)
    setShowForm(true)
  }

  function openEditForm(model: HubModelResponse) {
    setEditingId(model.id)
    setForm(modelToForm(model))
    setShowForm(true)
  }

  function updateForm<K extends keyof ModelFormState>(key: K, value: ModelFormState[K]) {
    setForm(current => ({ ...current, [key]: value }))
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !form.name.trim() || !form.provider.trim()) return
    setSaving(true)
    const payload = {
      name: form.name.trim(),
      provider: form.provider.trim(),
      description: form.description.trim() || undefined,
      capabilities: parseCsv(form.capabilities),
      context_window: form.contextWindow ? Number(form.contextWindow) : undefined,
      input_cost_per_1k: form.inputCost ? Number(form.inputCost) : undefined,
      output_cost_per_1k: form.outputCost ? Number(form.outputCost) : undefined,
      tags: parseCsv(form.tags),
      is_featured: form.isFeatured,
      is_public: form.isPublic,
      is_deprecated: form.isDeprecated,
      deprecation_notice: form.isDeprecated ? form.deprecationNotice.trim() || undefined : undefined,
    }

    try {
      if (editingId) {
        await updateHubModel(apiKey, editingId, payload)
        toast.success(`Updated ${form.name}`)
      } else {
        await addHubModel(apiKey, payload)
        toast.success(`Added ${form.name} to the catalog`)
      }
      resetForm()
      await load()
    } catch {
      toast.error(editingId ? 'Failed to update model card' : 'Failed to add model card')
    } finally {
      setSaving(false)
    }
  }

  async function handleSyncProvider(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !syncProviderName) return
    setSyncing(true)
    try {
      const res = await syncHubProvider(apiKey, {
        provider: syncProviderName,
        token: syncToken.trim() || undefined,
      })
      toast.success(`Synced ${res.models_added} model cards from ${res.provider}.`)
      setShowSyncModal(false)
      setSyncToken('')
      await load()
    } catch {
      toast.error('Failed to sync provider models')
    } finally {
      setSyncing(false)
    }
  }

  async function handleDelete(id: string) {
    if (!apiKey || !confirm('Remove this model from the catalog?')) return
    try {
      await deleteHubModel(apiKey, id)
      toast.success('Model removed from catalog')
      if (editingId === id) resetForm()
      await load()
    } catch {
      toast.error('Failed to remove model')
    }
  }

  async function openModelPosture(model: HubModelResponse) {
    if (!apiKey) return
    setSelectedModelId(model.id)
    setLoadingPosture(true)
    setCostPosture(null)
    setGovStatus(null)
    try {
      const [cost, gov] = await Promise.all([
        getHubModelCostPosture(apiKey, model.id),
        getHubModelGovernance(apiKey, model.id),
      ])
      setCostPosture(cost)
      setGovStatus(gov)
    } catch {
      toast.error('Failed to load model posture')
    } finally {
      setLoadingPosture(false)
    }
  }

  async function handleRequestAccess(id: string) {
    if (!apiKey) return
    try {
      await requestHubAccess(apiKey, id)
      toast.success('Access request recorded')
      await load()
    } catch {
      toast.error('Failed to record access request')
    }
  }

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="space-y-5">
      {/* ── Hero ── */}
      <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="rounded-xl bg-blue-100 p-2 ring-1 ring-blue-200 dark:bg-blue-500/20 dark:ring-blue-500/30">
              <Sparkles className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">AI Hub</h1>
              <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
                Curate the model catalog your workspace exposes to workflows, sync provider baselines, and manage governance.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setShowSyncModal(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300 dark:hover:bg-blue-900"
            >
              <Sparkles className="h-3.5 w-3.5" /> Sync Provider
            </button>
            <button
              onClick={openCreateForm}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              <Plus className="h-3.5 w-3.5" /> Add Model
            </button>
          </div>
        </div>

        {/* KPI strip */}
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          {[
            { label: 'Models', value: summary.total },
            { label: 'Providers', value: summary.providerCount },
            { label: 'Featured', value: summary.featured },
            { label: 'Deprecated', value: summary.deprecated },
            { label: 'Access Requests', value: summary.accessRequests },
          ].map(kpi => (
            <div key={kpi.label} className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">{kpi.label}</p>
              <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-white">{kpi.value}</p>
            </div>
          ))}
        </div>

        {/* Search & filters */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search models, providers, tags..."
              className={`${inputCls} pl-8`}
            />
          </div>
          <select value={filterProvider} onChange={e => setFilterProvider(e.target.value)} className={`${inputCls} w-auto min-w-[140px]`}>
            <option value="">All providers</option>
            {providers.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <select value={filterTag} onChange={e => setFilterTag(e.target.value)} className={`${inputCls} w-auto min-w-[120px]`}>
            <option value="">All tags</option>
            {tags.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <label className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <input
              type="checkbox"
              checked={featuredOnly}
              onChange={e => setFeaturedOnly(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            Featured only
          </label>
        </div>
      </section>

      {/* ── Model Cards Grid ── */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {loading ? 'Loading...' : `${filteredModels.length} model${filteredModels.length !== 1 ? 's' : ''}`}
          </p>
          <button onClick={() => load()} className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700">
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        {!loading && filteredModels.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-700 dark:bg-slate-900">
            <Box className="mx-auto mb-3 h-10 w-10 text-slate-300 dark:text-slate-600" />
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
              {search || filterProvider || filterTag ? 'No models match the current filters.' : 'No models in the catalog yet.'}
            </p>
            <div className="mt-4 flex justify-center gap-3">
              <button onClick={openCreateForm} className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline dark:text-blue-400">
                <Plus className="h-4 w-4" /> Add a model card
              </button>
              <button onClick={() => setShowSyncModal(true)} className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline dark:text-blue-400">
                <Sparkles className="h-4 w-4" /> Sync from a provider
              </button>
            </div>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredModels.map(model => {
            const isExpanded = expandedCardId === model.id
            return (
              <div
                key={model.id}
                className="group flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600"
              >
                <div>
                  {/* Header row */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <h3 className="text-base font-semibold text-slate-900 dark:text-white truncate">{model.name}</h3>
                        {model.is_featured && (
                          <span className={badgeCls('blue')}><Star className="h-3 w-3" /> Featured</span>
                        )}
                        {model.is_deprecated && (
                          <span className={badgeCls('amber')}>Deprecated</span>
                        )}
                        {!model.is_public && (
                          <span className={badgeCls('slate')}>Private</span>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{model.provider}</p>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <button onClick={() => openEditForm(model)} title="Edit" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200">
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={() => handleDelete(model.id)} title="Delete" className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40 dark:hover:text-rose-400">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Description */}
                  {model.description && (
                    <p className="mt-2 text-sm text-slate-600 dark:text-slate-300 line-clamp-2">{model.description}</p>
                  )}

                  {/* Stats row */}
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    <div className="rounded-lg bg-slate-50 px-2 py-1.5 dark:bg-slate-800/60">
                      <p className="text-[10px] text-slate-400">Context</p>
                      <p className="text-xs font-medium text-slate-700 dark:text-slate-200">{model.context_window ? `${(model.context_window / 1000).toFixed(0)}K` : '—'}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 px-2 py-1.5 dark:bg-slate-800/60">
                      <p className="text-[10px] text-slate-400">In / 1K</p>
                      <p className="text-xs font-medium text-slate-700 dark:text-slate-200">{model.input_cost_per_1k != null ? `$${model.input_cost_per_1k}` : '—'}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 px-2 py-1.5 dark:bg-slate-800/60">
                      <p className="text-[10px] text-slate-400">Out / 1K</p>
                      <p className="text-xs font-medium text-slate-700 dark:text-slate-200">{model.output_cost_per_1k != null ? `$${model.output_cost_per_1k}` : '—'}</p>
                    </div>
                  </div>

                  {/* Tags & capabilities */}
                  {(model.capabilities?.length > 0 || model.tags?.length > 0) && (
                    <div className="mt-2.5 flex flex-wrap gap-1">
                      {(model.capabilities ?? []).map(c => (
                        <span key={c} className={badgeCls('slate')}><Zap className="h-2.5 w-2.5" /> {c}</span>
                      ))}
                      {(model.tags ?? []).map(t => (
                        <span key={t} className={badgeCls('blue')}>{t}</span>
                      ))}
                    </div>
                  )}

                  {/* Deprecation notice */}
                  {model.is_deprecated && model.deprecation_notice && (
                    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-200">
                      {model.deprecation_notice}
                    </div>
                  )}

                  {/* Expandable details */}
                  {isExpanded && (
                    <div className="mt-3 space-y-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        <span className="font-medium text-slate-700 dark:text-slate-200">Access requests:</span> {model.access_request_count ?? 0}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        <span className="font-medium text-slate-700 dark:text-slate-200">Visibility:</span> {model.is_public ? 'Public' : 'Private'}
                      </div>
                    </div>
                  )}
                </div>

                {/* Card footer */}
                <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openModelPosture(model)}
                      className="rounded-lg border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      Posture
                    </button>
                    <button
                      onClick={() => handleRequestAccess(model.id)}
                      className="rounded-lg border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      <KeyRound className="mr-1 inline h-3 w-3" />Access
                    </button>
                  </div>
                  <button
                    onClick={() => setExpandedCardId(isExpanded ? null : model.id)}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                  >
                    {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {/* ── Create / Edit Model Modal ── */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm" onClick={resetForm}>
          <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-700 dark:bg-slate-900" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {editingId ? 'Edit Model Card' : 'Add Model Card'}
              </h2>
              <button onClick={resetForm} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Name *</label>
                  <input value={form.name} onChange={e => updateForm('name', e.target.value)} className={inputCls} required placeholder="gpt-4o" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Provider *</label>
                  <input value={form.provider} onChange={e => updateForm('provider', e.target.value)} className={inputCls} required placeholder="openai" />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Description</label>
                <textarea value={form.description} onChange={e => updateForm('description', e.target.value)} rows={2} className={inputCls} placeholder="Short description or governance note" />
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Context window</label>
                  <input value={form.contextWindow} onChange={e => updateForm('contextWindow', e.target.value)} className={inputCls} inputMode="numeric" placeholder="128000" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Input cost / 1K</label>
                  <input value={form.inputCost} onChange={e => updateForm('inputCost', e.target.value)} className={inputCls} inputMode="decimal" placeholder="0.0025" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Output cost / 1K</label>
                  <input value={form.outputCost} onChange={e => updateForm('outputCost', e.target.value)} className={inputCls} inputMode="decimal" placeholder="0.01" />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Capabilities</label>
                  <input value={form.capabilities} onChange={e => updateForm('capabilities', e.target.value)} className={inputCls} placeholder="chat, reasoning, code, tools" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Tags</label>
                  <input value={form.tags} onChange={e => updateForm('tags', e.target.value)} className={inputCls} placeholder="featured, open-weights, fast" />
                </div>
              </div>

              <div className="flex flex-wrap gap-4">
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input type="checkbox" checked={form.isFeatured} onChange={e => updateForm('isFeatured', e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
                  Featured
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input type="checkbox" checked={form.isPublic} onChange={e => updateForm('isPublic', e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
                  Public
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input type="checkbox" checked={form.isDeprecated} onChange={e => updateForm('isDeprecated', e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
                  Deprecated
                </label>
              </div>

              {form.isDeprecated && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Deprecation notice</label>
                  <textarea value={form.deprecationNotice} onChange={e => updateForm('deprecationNotice', e.target.value)} rows={2} className={inputCls} placeholder="Migration guidance or replacement model" />
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
                <button type="button" onClick={resetForm} className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
                  Cancel
                </button>
                <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
                  {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : editingId ? 'Save Changes' : 'Create Model'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Sync Provider Modal ── */}
      {showSyncModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm" onClick={() => setShowSyncModal(false)}>
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-700 dark:bg-slate-900" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
                <Sparkles className="h-5 w-5 text-blue-600 dark:text-blue-400" /> Sync Provider Catalog
              </h2>
              <button onClick={() => setShowSyncModal(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
              Seed your workspace catalog from a provider baseline, then customize the resulting cards.
            </p>
            <form onSubmit={handleSyncProvider} className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Provider</label>
                <select value={syncProviderName} onChange={e => setSyncProviderName(e.target.value)} className={inputCls}>
                  <option value="huggingface">Hugging Face</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="ollama">Ollama</option>
                </select>
              </div>
              {syncProviderName === 'huggingface' && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Token (optional)</label>
                  <input type="password" value={syncToken} onChange={e => setSyncToken(e.target.value)} placeholder="hf_..." className={inputCls} />
                  <p className="mt-1 text-[11px] text-slate-400">For gated models that require authentication.</p>
                </div>
              )}
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowSyncModal(false)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
                  Cancel
                </button>
                <button type="submit" disabled={syncing} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
                  {syncing ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Sync Models'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Model Posture Modal ── */}
      {selectedModelId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm" onClick={() => setSelectedModelId(null)}>
          <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-700 dark:bg-slate-900" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Model Posture {costPosture ? `— ${costPosture.model_name}` : ''}
              </h2>
              <button onClick={() => setSelectedModelId(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                <X className="h-5 w-5" />
              </button>
            </div>

            {loadingPosture && <p className="text-sm text-slate-500 animate-pulse">Loading posture data...</p>}

            {costPosture && (
              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Cost Posture</h3>
                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    { label: 'Active Budgets', value: costPosture.active_budget_count },
                    { label: 'Budget Limit', value: `$${Number(costPosture.total_budget_limit_usd).toFixed(2)}` },
                    { label: 'Current Spend', value: `$${Number(costPosture.current_spend_usd).toFixed(2)}` },
                  ].map(s => (
                    <div key={s.label} className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">{s.label}</p>
                      <p className="mt-0.5 text-lg font-semibold text-slate-900 dark:text-white">{s.value}</p>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link href={`/budgets?scope_type=model&scope_id=${encodeURIComponent(costPosture.model_name)}`} className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
                    Budget detail
                  </Link>
                  <Link href={`/billing?model=${encodeURIComponent(costPosture.model_name)}`} className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
                    Billing
                  </Link>
                </div>
              </section>
            )}

            {govStatus && (
              <section className="mt-5 space-y-3 border-t border-slate-100 pt-5 dark:border-slate-800">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Governance</h3>
                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    { label: 'Approvals', value: govStatus.approval_count },
                    { label: 'Audit Events', value: govStatus.audit_event_count },
                    { label: 'Tool Policies', value: govStatus.tool_policy_count },
                  ].map(s => (
                    <div key={s.label} className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">{s.label}</p>
                      <p className="mt-0.5 text-lg font-semibold text-slate-900 dark:text-white">{s.value}</p>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link href={`/approvals?request_type=model_access&target_id=${encodeURIComponent(selectedModelId)}`} className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
                    Approvals
                  </Link>
                  <Link href={`/audit?target_type=hub_model&target_id=${encodeURIComponent(selectedModelId)}`} className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
                    Audit log
                  </Link>
                </div>
                {govStatus.is_deprecated && govStatus.deprecation_notice && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-200">
                    Deprecated: {govStatus.deprecation_notice}
                  </div>
                )}
              </section>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
