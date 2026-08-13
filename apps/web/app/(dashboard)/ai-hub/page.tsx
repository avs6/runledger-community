'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { ArrowRight, KeyRound, Pencil, Plus, RefreshCw, Sparkles, Trash2 } from 'lucide-react'
import {
  addHubModel,
  deleteHubModel,
  listHubModels,
  requestHubAccess,
  syncHubProvider,
  updateHubModel,
} from '@/lib/api'
import type { HubModelResponse } from '@/types/api'

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

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

function badgeCls(tone: 'blue' | 'amber' | 'slate') {
  if (tone === 'blue') {
    return 'rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300'
  }
  if (tone === 'amber') {
    return 'rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-700 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300'
  }
  return 'rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'
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
    return { total, featured, deprecated, accessRequests }
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
    if (!apiKey) return
    try {
      await deleteHubModel(apiKey, id)
      toast.success('Model removed from catalog')
      if (editingId === id) resetForm()
      await load()
    } catch {
      toast.error('Failed to remove model')
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
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      <div className="rounded-3xl border border-slate-200 bg-white/95 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/85">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-blue-700 dark:text-blue-400">
              Model Catalog
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950 dark:text-white">
              AI Hub
            </h1>
            <p className="max-w-3xl text-sm text-slate-500">
              Curate the models your workspace exposes to workflows, connect seeded provider catalogs, and mark
              model cards for promotion, deprecation, or governance review.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/provider-profiles"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Provider Profiles <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/model-usage"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Model Usage <ArrowRight className="h-4 w-4" />
            </Link>
            <button
              onClick={() => setShowSyncModal(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300 dark:hover:bg-blue-900"
            >
              <Sparkles className="h-4 w-4" /> Sync Provider Catalog
            </button>
            <button
              onClick={openCreateForm}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" /> Add Model Card
            </button>
          </div>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/70">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Catalog Models</p>
            <p className="mt-2 text-2xl font-semibold text-slate-950 dark:text-white">{summary.total}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/70">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Featured</p>
            <p className="mt-2 text-2xl font-semibold text-slate-950 dark:text-white">{summary.featured}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/70">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Deprecated</p>
            <p className="mt-2 text-2xl font-semibold text-slate-950 dark:text-white">{summary.deprecated}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/70">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Access Requests</p>
            <p className="mt-2 text-2xl font-semibold text-slate-950 dark:text-white">{summary.accessRequests}</p>
          </div>
        </div>
      </div>

      {showSyncModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-950 dark:text-white">
              <Sparkles className="h-5 w-5 text-blue-600" /> Sync Provider Catalog
            </h2>
            <p className="text-sm text-slate-500">
              Seed your workspace catalog from a provider baseline, then edit the resulting cards for local pricing,
              tags, visibility, and governance notes.
            </p>
            <form onSubmit={handleSyncProvider} className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Provider
                </label>
                <select
                  value={syncProviderName}
                  onChange={e => setSyncProviderName(e.target.value)}
                  className={inputCls}
                >
                  <option value="huggingface">Hugging Face</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="ollama">Ollama</option>
                </select>
              </div>
              {syncProviderName === 'huggingface' && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Hugging Face token
                  </label>
                  <input
                    type="password"
                    value={syncToken}
                    onChange={e => setSyncToken(e.target.value)}
                    placeholder="hf_..."
                    className={inputCls}
                  />
                  <p className="mt-1 text-[11px] text-slate-400">
                    Optional. Use a token for live catalog imports that include gated models.
                  </p>
                </div>
              )}
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowSyncModal(false)}
                  className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={syncing}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {syncing ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Sync Models'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.2fr_2fr]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-950 dark:text-white">
                  Catalog Controls
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Filter the active catalog, then update a card to match workspace policy and routing intent.
                </p>
              </div>
              {showForm && (
                <button
                  onClick={resetForm}
                  className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                >
                  Close
                </button>
              )}
            </div>

            <div className="mt-4 space-y-3">
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search models, providers, tags, or capabilities"
                className={inputCls}
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <select value={filterProvider} onChange={e => setFilterProvider(e.target.value)} className={inputCls}>
                  <option value="">All providers</option>
                  {providers.map(provider => (
                    <option key={provider} value={provider}>
                      {provider}
                    </option>
                  ))}
                </select>
                <select value={filterTag} onChange={e => setFilterTag(e.target.value)} className={inputCls}>
                  <option value="">All tags</option>
                  {tags.map(tag => (
                    <option key={tag} value={tag}>
                      {tag}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={featuredOnly}
                  onChange={e => setFeaturedOnly(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                Show featured models only
              </label>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="mb-4">
              <h2 className="text-base font-semibold text-slate-950 dark:text-white">
                {editingId ? 'Edit Model Card' : 'Create Model Card'}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Keep model metadata close to the workflow surface so routing, cost review, and access review stay
                cohesive.
              </p>
            </div>
            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Name</label>
                  <input
                    value={form.name}
                    onChange={e => updateForm('name', e.target.value)}
                    className={inputCls}
                    required
                    placeholder="gpt-4o"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Provider</label>
                  <input
                    value={form.provider}
                    onChange={e => updateForm('provider', e.target.value)}
                    className={inputCls}
                    required
                    placeholder="openai"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Description</label>
                <textarea
                  value={form.description}
                  onChange={e => updateForm('description', e.target.value)}
                  rows={3}
                  className={inputCls}
                  placeholder="Short description, governance note, or usage guidance"
                />
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Context window</label>
                  <input
                    value={form.contextWindow}
                    onChange={e => updateForm('contextWindow', e.target.value)}
                    className={inputCls}
                    inputMode="numeric"
                    placeholder="128000"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Input cost / 1K</label>
                  <input
                    value={form.inputCost}
                    onChange={e => updateForm('inputCost', e.target.value)}
                    className={inputCls}
                    inputMode="decimal"
                    placeholder="0.0025"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Output cost / 1K</label>
                  <input
                    value={form.outputCost}
                    onChange={e => updateForm('outputCost', e.target.value)}
                    className={inputCls}
                    inputMode="decimal"
                    placeholder="0.01"
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Capabilities</label>
                  <input
                    value={form.capabilities}
                    onChange={e => updateForm('capabilities', e.target.value)}
                    className={inputCls}
                    placeholder="chat, reasoning, code, tools"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Tags</label>
                  <input
                    value={form.tags}
                    onChange={e => updateForm('tags', e.target.value)}
                    className={inputCls}
                    placeholder="featured, open-weights, fast"
                  />
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={form.isFeatured}
                    onChange={e => updateForm('isFeatured', e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  Featured
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={form.isPublic}
                    onChange={e => updateForm('isPublic', e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  Public in workspace
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={form.isDeprecated}
                    onChange={e => updateForm('isDeprecated', e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  Mark deprecated
                </label>
              </div>

              {form.isDeprecated && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Deprecation notice
                  </label>
                  <textarea
                    value={form.deprecationNotice}
                    onChange={e => updateForm('deprecationNotice', e.target.value)}
                    rows={2}
                    className={inputCls}
                    placeholder="Explain the replacement model or migration timing"
                  />
                </div>
              )}

              <div className="flex flex-wrap justify-end gap-3">
                {editingId && (
                  <button
                    type="button"
                    onClick={openCreateForm}
                    className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                  >
                    New card
                  </button>
                )}
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : editingId ? 'Save changes' : 'Create model card'}
                </button>
              </div>
            </form>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-950 dark:text-white">Catalog Inventory</h2>
              <p className="mt-1 text-sm text-slate-500">
                {loading ? 'Loading model cards…' : `${filteredModels.length} model cards in the current view.`}
              </p>
            </div>
          </div>

          <div className="mt-4 space-y-4">
            {!loading && filteredModels.length === 0 && (
              <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">
                No model cards matched the current filters.
              </div>
            )}

            {filteredModels.map(model => (
              <div
                key={model.id}
                className="rounded-2xl border border-slate-200 p-5 dark:border-slate-800"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-lg font-semibold text-slate-950 dark:text-white">{model.name}</h3>
                        {model.is_featured && <span className={badgeCls('blue')}>Featured</span>}
                        {model.is_deprecated && <span className={badgeCls('amber')}>Deprecated</span>}
                        {!model.is_public && <span className={badgeCls('slate')}>Private</span>}
                      </div>
                      <p className="mt-1 text-sm text-slate-500">
                        Provider: <span className="font-medium text-slate-700 dark:text-slate-200">{model.provider}</span>
                      </p>
                    </div>

                    {model.description && <p className="text-sm text-slate-600 dark:text-slate-300">{model.description}</p>}

                    <div className="grid gap-2 text-sm text-slate-500 sm:grid-cols-2 xl:grid-cols-4">
                      <div>
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Context</p>
                        <p className="mt-1 text-slate-700 dark:text-slate-200">{model.context_window ?? '—'}</p>
                      </div>
                      <div>
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Input / 1K</p>
                        <p className="mt-1 text-slate-700 dark:text-slate-200">{model.input_cost_per_1k ?? '—'}</p>
                      </div>
                      <div>
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Output / 1K</p>
                        <p className="mt-1 text-slate-700 dark:text-slate-200">{model.output_cost_per_1k ?? '—'}</p>
                      </div>
                      <div>
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Access requests</p>
                        <p className="mt-1 text-slate-700 dark:text-slate-200">{model.access_request_count}</p>
                      </div>
                    </div>

                    {(model.capabilities?.length > 0 || model.tags?.length > 0) && (
                      <div className="space-y-2">
                        {model.capabilities?.length > 0 && (
                          <div className="flex flex-wrap gap-2">
                            {model.capabilities.map(capability => (
                              <span key={capability} className={badgeCls('slate')}>
                                {capability}
                              </span>
                            ))}
                          </div>
                        )}
                        {model.tags?.length > 0 && (
                          <div className="flex flex-wrap gap-2">
                            {model.tags.map(tag => (
                              <span key={tag} className={badgeCls('blue')}>
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {model.is_deprecated && model.deprecation_notice && (
                      <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
                        {model.deprecation_notice}
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-2 lg:justify-end">
                    <button
                      onClick={() => openEditForm(model)}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                    >
                      <Pencil className="h-4 w-4" /> Edit
                    </button>
                    <button
                      onClick={() => handleRequestAccess(model.id)}
                      className="inline-flex items-center gap-2 rounded-lg border border-blue-200 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50 dark:border-blue-900 dark:text-blue-300 dark:hover:bg-blue-950"
                    >
                      <KeyRound className="h-4 w-4" /> Request Access
                    </button>
                    <button
                      onClick={() => handleDelete(model.id)}
                      className="inline-flex items-center gap-2 rounded-lg border border-rose-200 px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-900 dark:text-rose-300 dark:hover:bg-rose-950"
                    >
                      <Trash2 className="h-4 w-4" /> Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
