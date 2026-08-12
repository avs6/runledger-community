'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Sparkles, Plus, Trash2, Key, RefreshCw, Cpu, Tag, ExternalLink } from 'lucide-react'
import {
  listHubModels,
  addHubModel,
  deleteHubModel,
  requestHubAccess,
  syncHubProvider,
} from '@/lib/api'
import type { HubModelResponse } from '@/types/api'

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

export default function AiHubPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey

  const [models, setModels] = useState<HubModelResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [filterProvider, setFilterProvider] = useState('')
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [showSyncModal, setShowSyncModal] = useState(false)

  // Manual Add Form State
  const [name, setName] = useState('')
  const [provider, setProvider] = useState('')
  const [description, setDescription] = useState('')
  const [contextWindow, setContextWindow] = useState<number | ''>('')
  const [inputCost, setInputCost] = useState<number | ''>('')
  const [outputCost, setOutputCost] = useState<number | ''>('')
  const [tags, setTags] = useState('')
  const [isFeatured, setIsFeatured] = useState(false)

  // Sync Provider Form State
  const [syncProviderName, setSyncProviderName] = useState('huggingface')
  const [syncToken, setSyncToken] = useState('')
  const [syncing, setSyncing] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const res = await listHubModels(apiKey, {
        featured_only: featuredOnly,
        provider: filterProvider || undefined,
      })
      setModels(res.items)
    } catch {
      toast.error('Failed to load AI Hub model catalog')
    } finally {
      setLoading(false)
    }
  }, [apiKey, filterProvider, featuredOnly])

  useEffect(() => {
    load()
  }, [load])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !name || !provider) return
    try {
      await addHubModel(apiKey, {
        name,
        provider,
        description: description || undefined,
        context_window: contextWindow !== '' ? contextWindow : undefined,
        input_cost_per_1k: inputCost !== '' ? inputCost : undefined,
        output_cost_per_1k: outputCost !== '' ? outputCost : undefined,
        tags: tags ? tags.split(',').map((t) => t.trim()) : [],
        is_featured: isFeatured,
        is_public: true,
      })
      toast.success(`Model '${name}' added to AI Hub`)
      setName('')
      setProvider('')
      setDescription('')
      setContextWindow('')
      setInputCost('')
      setOutputCost('')
      setTags('')
      setIsFeatured(false)
      setShowForm(false)
      load()
    } catch (err) {
      toast.error('Failed to add model')
    }
  }

  async function handleSyncProvider(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !syncProviderName) return
    setSyncing(true)
    try {
      const res = await syncHubProvider(apiKey, { provider: syncProviderName, hf_token: syncToken.trim() || undefined })
      toast.success(
        `Auto-connected to ${res.provider}! Added ${res.models_synced} models to AI Hub catalog.`
      )
      setShowSyncModal(false)
      setSyncToken('')
      load()
    } catch (err) {
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
      load()
    } catch (err) {
      toast.error('Failed to remove model')
    }
  }

  async function handleRequestAccess(id: string) {
    if (!apiKey) return
    try {
      await requestHubAccess(apiKey, id)
      toast.success('Access request submitted')
      load()
    } catch (err) {
      toast.error('Failed to request model access')
    }
  }

  const providers = Array.from(new Set(models.map((m) => m.provider)))

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between dark:border-slate-800 dark:bg-slate-900/80">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-blue-700 dark:text-blue-400">
            Model Intelligence & Marketplace
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 dark:text-white">
            AI Hub & Model Catalog
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Discover, auto-connect Hugging Face open weights, and manage corporate model access.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setShowSyncModal(true)}
            className="flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300 dark:hover:bg-blue-900 transition"
          >
            <Sparkles className="h-4 w-4" /> Auto-Connect Provider
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition"
          >
            <Plus className="h-4 w-4" /> {showForm ? 'Cancel' : 'Add Model Manually'}
          </button>
        </div>
      </div>

      {/* Auto-Connect Provider Modal */}
      {showSyncModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <h2 className="text-lg font-bold text-slate-950 dark:text-white flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-blue-600" /> Auto-Connect Model Provider
            </h2>
            <p className="text-xs text-slate-500">
              Select an AI model provider or Hugging Face Hub repository to auto-sync pre-configured model cards into your workspace.
            </p>

            <form onSubmit={handleSyncProvider} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Target Provider *
                </label>
                <select
                  value={syncProviderName}
                  onChange={(e) => setSyncProviderName(e.target.value)}
                  className={inputCls}
                >
                  <option value="huggingface">Hugging Face Hub (Open-Weights & Llama/DeepSeek)</option>
                  <option value="openai">OpenAI (GPT-4o, o3-mini, GPT-4o-mini)</option>
                  <option value="anthropic">Anthropic (Claude 3.5 Sonnet & Haiku)</option>
                  <option value="ollama">Ollama (Local Llama & DeepSeek-R1)</option>
                </select>
              </div>

              {syncProviderName === 'huggingface' && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Hugging Face User Access Token (Optional for gated models)
                  </label>
                  <input
                    type="password"
                    value={syncToken}
                    onChange={(e) => setSyncToken(e.target.value)}
                    placeholder="hf_..."
                    className={inputCls}
                  />
                  <p className="mt-1 text-[11px] text-slate-400">
                    Provide a read token from Hugging Face Settings to auto-import trending text generation models.
                  </p>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
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
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {syncing ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Connect & Import Models'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Manual Add Form */}
      {showForm && (
        <form
          onSubmit={handleAdd}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4"
        >
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">
            Register Custom Model Card
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Name *
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="e.g., custom-fine-tune-v1"
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Provider *
              </label>
              <input
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                required
                placeholder="openai, huggingface, local"
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Context Window
              </label>
              <input
                type="number"
                value={contextWindow}
                onChange={(e) => setContextWindow(e.target.value ? Number(e.target.value) : '')}
                placeholder="128000"
                className={inputCls}
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Description
            </label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Model specs and capabilities..."
              className={inputCls}
            />
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Input $/1k tokens
              </label>
              <input
                type="number"
                step="0.0001"
                value={inputCost}
                onChange={(e) => setInputCost(e.target.value ? Number(e.target.value) : '')}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Output $/1k tokens
              </label>
              <input
                type="number"
                step="0.0001"
                value={outputCost}
                onChange={(e) => setOutputCost(e.target.value ? Number(e.target.value) : '')}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Tags (comma-separated)
              </label>
              <input
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="chat, code, vision"
                className={inputCls}
              />
            </div>
          </div>
          <div className="flex items-center gap-4 pt-2">
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={isFeatured}
                onChange={(e) => setIsFeatured(e.target.checked)}
                className="h-4 w-4 rounded text-blue-600 focus:ring-blue-500"
              />{' '}
              Mark as Featured Model
            </label>
            <button
              type="submit"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              Add to Hub
            </button>
          </div>
        </form>
      )}

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <select
          value={filterProvider}
          onChange={(e) => setFilterProvider(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
        >
          <option value="">All Providers ({providers.length})</option>
          {providers.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-xs font-medium text-slate-700 dark:text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={featuredOnly}
            onChange={(e) => setFeaturedOnly(e.target.checked)}
            className="h-3.5 w-3.5 rounded text-blue-600 focus:ring-blue-500"
          />{' '}
          Featured Models Only
        </label>
      </div>

      {loading && <p className="text-sm text-slate-400">Loading model catalog...</p>}

      {/* Model Cards Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {models.map((m) => (
          <div
            key={m.id}
            className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
          >
            <div>
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-slate-950 dark:text-white flex items-center gap-1.5">
                    <Cpu className="h-4 w-4 text-blue-600" /> {m.name}
                  </h3>
                  <p className="text-xs uppercase tracking-wider font-semibold text-slate-400 mt-0.5">
                    {m.provider}
                  </p>
                </div>
                <div className="flex gap-1">
                  {m.is_featured && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                      Featured
                    </span>
                  )}
                </div>
              </div>

              {m.description && (
                <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                  {m.description}
                </p>
              )}

              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl bg-slate-50 p-2 dark:bg-slate-950">
                  <p className="text-[10px] text-slate-400 uppercase font-semibold">Context</p>
                  <p className="text-xs font-semibold text-slate-900 dark:text-white mt-0.5">
                    {m.context_window ? `${(m.context_window / 1000).toFixed(0)}k` : '—'}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 p-2 dark:bg-slate-950">
                  <p className="text-[10px] text-slate-400 uppercase font-semibold">In $/1k</p>
                  <p className="text-xs font-semibold text-slate-900 dark:text-white mt-0.5">
                    {m.input_cost_per_1k != null ? `$${m.input_cost_per_1k}` : '—'}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 p-2 dark:bg-slate-950">
                  <p className="text-[10px] text-slate-400 uppercase font-semibold">Out $/1k</p>
                  <p className="text-xs font-semibold text-slate-900 dark:text-white mt-0.5">
                    {m.output_cost_per_1k != null ? `$${m.output_cost_per_1k}` : '—'}
                  </p>
                </div>
              </div>

              {m.tags && m.tags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {m.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                    >
                      #{t}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-800">
              <span className="text-[11px] text-slate-400">
                {m.access_request_count || 0} access requests
              </span>
              <div className="flex gap-3">
                <button
                  onClick={() => handleRequestAccess(m.id)}
                  className="text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400"
                >
                  Request Access
                </button>
                <button
                  onClick={() => handleDelete(m.id)}
                  className="text-xs font-medium text-red-500 hover:text-red-700"
                >
                  Remove
                </button>
              </div>
            </div>
          </div>
        ))}
        {models.length === 0 && !loading && (
          <div className="col-span-full py-12 text-center text-slate-400">
            No models in the AI Hub catalog yet. Click &quot;Auto-Connect Provider&quot; above to import Hugging Face or OpenAI models.
          </div>
        )}
      </div>
    </div>
  )
}
