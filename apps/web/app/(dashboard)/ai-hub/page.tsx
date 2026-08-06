'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  listHubModels,
  addHubModel,
  deleteHubModel,
  requestHubAccess,
} from '@/lib/api'
import type { HubModelResponse } from '@/types/api'

export default function AiHubPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey

  const [models, setModels] = useState<HubModelResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [filterProvider, setFilterProvider] = useState('')
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [showForm, setShowForm] = useState(false)

  const [name, setName] = useState('')
  const [provider, setProvider] = useState('')
  const [description, setDescription] = useState('')
  const [contextWindow, setContextWindow] = useState<number | ''>('')
  const [inputCost, setInputCost] = useState<number | ''>('')
  const [outputCost, setOutputCost] = useState<number | ''>('')
  const [tags, setTags] = useState('')
  const [isFeatured, setIsFeatured] = useState(false)

  async function load() {
    if (!apiKey) return
    setLoading(true)
    try {
      const res = await listHubModels(apiKey, {
        featured_only: featuredOnly,
        provider: filterProvider || undefined,
      })
      setModels(res.items)
    } catch {
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [apiKey, filterProvider, featuredOnly])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !name || !provider) return
    await addHubModel(apiKey, {
      name,
      provider,
      description: description || undefined,
      context_window: contextWindow !== '' ? contextWindow : undefined,
      input_cost_per_1k: inputCost !== '' ? inputCost : undefined,
      output_cost_per_1k: outputCost !== '' ? outputCost : undefined,
      tags: tags ? tags.split(',').map(t => t.trim()) : [],
      is_featured: isFeatured,
      is_public: true,
    })
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
  }

  async function handleDelete(id: string) {
    if (!apiKey) return
    await deleteHubModel(apiKey, id)
    load()
  }

  async function handleRequestAccess(id: string) {
    if (!apiKey) return
    await requestHubAccess(apiKey, id)
    load()
  }

  const providers = Array.from(new Set(models.map(m => m.provider)))

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">AI Hub</h1>
          <p className="text-sm text-slate-500">Browse and manage the model catalog for your workspace.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
          {showForm ? 'Cancel' : 'Add Model'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5 space-y-3">
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Name *</label>
              <input value={name} onChange={e => setName(e.target.value)} required className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Provider *</label>
              <input value={provider} onChange={e => setProvider(e.target.value)} required placeholder="openai, anthropic, ..." className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Context Window</label>
              <input type="number" value={contextWindow} onChange={e => setContextWindow(e.target.value ? Number(e.target.value) : '')} className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Description</label>
            <input value={description} onChange={e => setDescription(e.target.value)} className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Input $/1k tokens</label>
              <input type="number" step="0.0001" value={inputCost} onChange={e => setInputCost(e.target.value ? Number(e.target.value) : '')} className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Output $/1k tokens</label>
              <input type="number" step="0.0001" value={outputCost} onChange={e => setOutputCost(e.target.value ? Number(e.target.value) : '')} className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Tags (comma-sep)</label>
              <input value={tags} onChange={e => setTags(e.target.value)} placeholder="chat, code, vision" className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <input type="checkbox" checked={isFeatured} onChange={e => setIsFeatured(e.target.checked)} /> Featured
            </label>
            <button type="submit" className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">Add to Hub</button>
          </div>
        </form>
      )}

      <div className="flex gap-3 items-center">
        <select value={filterProvider} onChange={e => setFilterProvider(e.target.value)} className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white">
          <option value="">All Providers</option>
          {providers.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input type="checkbox" checked={featuredOnly} onChange={e => setFeaturedOnly(e.target.checked)} /> Featured only
        </label>
      </div>

      {loading && <p className="text-sm text-slate-400">Loading...</p>}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {models.map(m => (
          <div key={m.id} className="rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white">{m.name}</h3>
                <p className="text-xs text-slate-500">{m.provider}</p>
              </div>
              <div className="flex gap-1">
                {m.is_featured && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">Featured</span>}
                {m.is_deprecated && <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">Deprecated</span>}
              </div>
            </div>
            {m.description && <p className="mt-2 text-sm text-slate-500">{m.description}</p>}
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded bg-slate-50 p-2 dark:bg-white/5">
                <p className="text-xs text-slate-400">Context</p>
                <p className="text-sm font-medium text-slate-900 dark:text-white">{m.context_window ? `${(m.context_window / 1000).toFixed(0)}k` : '—'}</p>
              </div>
              <div className="rounded bg-slate-50 p-2 dark:bg-white/5">
                <p className="text-xs text-slate-400">In $/1k</p>
                <p className="text-sm font-medium text-slate-900 dark:text-white">{m.input_cost_per_1k != null ? `$${m.input_cost_per_1k}` : '—'}</p>
              </div>
              <div className="rounded bg-slate-50 p-2 dark:bg-white/5">
                <p className="text-xs text-slate-400">Out $/1k</p>
                <p className="text-sm font-medium text-slate-900 dark:text-white">{m.output_cost_per_1k != null ? `$${m.output_cost_per_1k}` : '—'}</p>
              </div>
            </div>
            {m.capabilities.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {m.capabilities.map(c => (
                  <span key={c} className="rounded bg-indigo-50 px-2 py-0.5 text-xs text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400">{c}</span>
                ))}
              </div>
            )}
            {m.tags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {m.tags.map(t => (
                  <span key={t} className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-white/10 dark:text-slate-400">{t}</span>
                ))}
              </div>
            )}
            <div className="mt-3 flex items-center justify-between">
              <span className="text-xs text-slate-400">{m.access_request_count} access requests</span>
              <div className="flex gap-2">
                <button onClick={() => handleRequestAccess(m.id)} className="text-xs text-indigo-500 hover:text-indigo-700">Request Access</button>
                <button onClick={() => handleDelete(m.id)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
              </div>
            </div>
          </div>
        ))}
        {models.length === 0 && !loading && <p className="col-span-full text-center text-slate-400 py-8">No models in the hub.</p>}
      </div>
    </div>
  )
}
