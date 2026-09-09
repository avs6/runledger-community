'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { toast } from 'sonner'
import {
  AlertTriangle, BookOpen, ChevronDown, ChevronRight, Clock, Copy,
  Database, ExternalLink, FileText, HardDrive, Layers, Plus, RefreshCw,
  Search, Server, Sparkles, Trash2, X, Zap,
} from 'lucide-react'
import {
  getVectorCollections, getVectorStoresLifecyclePosture,
  createVectorCollection, deleteVectorCollection,
} from '@/lib/api'
import type { VectorCollectionResponse, VectorStoresLifecyclePosture } from '@/types/api'
import { num } from '@/lib/utils'

function bytes(n: number) {
  if (n < 1024) return `${n} B`
  if (num(n) < 1024 * 1024) return `${(num(n) / 1024).toFixed(1)} KB`
  return `${(num(n) / (1024 * 1024)).toFixed(1)} MB`
}

function money(v: number | null | undefined) {
  if (!v) return '$0.00'
  if (num(v) >= 1) return `$${num(v).toFixed(2)}`
  if (num(v) >= 0.001) return `$${num(v).toFixed(4)}`
  return `$${num(v).toFixed(6)}`
}

function timeAgo(dt: string | null) {
  if (!dt) return 'Never'
  const diff = Date.now() - new Date(dt).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'Just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

function statusCls(s: string) {
  if (s === 'active') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300'
  if (s === 'inactive') return 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300'
  return 'bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-300'
}

const DISTANCE_METRICS = [
  { value: 'cosine', label: 'Cosine', desc: 'Best for normalized embeddings' },
  { value: 'euclidean', label: 'Euclidean', desc: 'Best for spatial distance' },
  { value: 'dot', label: 'Dot Product', desc: 'Best for magnitude-aware search' },
]

const EMBEDDING_PRESETS = [
  { model: 'bge-small-en-v1.5', dims: 384, label: 'BGE Small EN v1.5' },
  { model: 'bge-base-en-v1.5', dims: 768, label: 'BGE Base EN v1.5' },
  { model: 'bge-large-en-v1.5', dims: 1024, label: 'BGE Large EN v1.5' },
  { model: 'text-embedding-3-small', dims: 1536, label: 'OpenAI Small' },
  { model: 'text-embedding-3-large', dims: 3072, label: 'OpenAI Large' },
  { model: 'voyage-3', dims: 1024, label: 'Voyage 3' },
  { model: 'nomic-embed-text-v1.5', dims: 768, label: 'Nomic Embed v1.5' },
  { model: '', dims: 0, label: 'Custom' },
]

const inputCls = 'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-cyan-500'

type ViewTab = 'stores' | 'register' | 'guide'

export default function VectorStoresPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''

  const [tab, setTab] = useState<ViewTab>('stores')
  const [loading, setLoading] = useState(true)
  const [collections, setCollections] = useState<VectorCollectionResponse[]>([])
  const [total, setTotal] = useState(0)
  const [lifecyclePosture, setLifecyclePosture] = useState<VectorStoresLifecyclePosture | null>(null)
  const [expandedGuide, setExpandedGuide] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  // Register form
  const [formName, setFormName] = useState('')
  const [formQdrant, setFormQdrant] = useState('')
  const [formDesc, setFormDesc] = useState('')
  const [formPreset, setFormPreset] = useState(0)
  const [formModel, setFormModel] = useState('bge-small-en-v1.5')
  const [formDims, setFormDims] = useState(384)
  const [formMetric, setFormMetric] = useState('cosine')
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [data, posture] = await Promise.all([
        getVectorCollections(apiKey),
        getVectorStoresLifecyclePosture(apiKey).catch(() => null),
      ])
      setCollections(data.collections)
      setTotal(data.total)
      setLifecyclePosture(posture)
    } catch { toast.error('Failed to load vector stores') }
    finally { setLoading(false) }
  }, [apiKey])

  useEffect(() => { load() }, [load])

  function applyPreset(idx: number) {
    setFormPreset(idx)
    const p = EMBEDDING_PRESETS[idx]
    if (p.model) { setFormModel(p.model); setFormDims(p.dims) }
  }

  async function handleCreate() {
    if (!formName.trim() || !formQdrant.trim()) { toast.error('Name and Qdrant collection are required'); return }
    setCreating(true)
    try {
      await createVectorCollection(apiKey, {
        name: formName.trim(),
        qdrant_collection: formQdrant.trim(),
        description: formDesc.trim() || undefined,
        embedding_model: formModel || undefined,
        dimensions: formDims || undefined,
        distance_metric: formMetric,
      })
      toast.success(`Vector store "${formName}" registered`)
      setFormName(''); setFormQdrant(''); setFormDesc('')
      setTab('stores')
      load()
    } catch { toast.error('Failed to register vector store') }
    finally { setCreating(false) }
  }

  async function handleDelete(id: string, name: string) {
    setDeleting(id)
    try {
      await deleteVectorCollection(apiKey, id)
      toast.success(`Deleted "${name}"`)
      load()
    } catch { toast.error('Failed to delete collection') }
    finally { setDeleting(null) }
  }

  function copySnippet(text: string) {
    navigator.clipboard.writeText(text).then(() => toast.success('Copied to clipboard'))
  }

  const totalDocs = collections.reduce((s, c) => s + c.document_count, 0)
  const totalQueries = collections.reduce((s, c) => s + c.total_queries, 0)
  const totalSize = collections.reduce((s, c) => s + c.size_bytes, 0)
  const totalCost = collections.reduce((s, c) => s + (c.total_query_cost || 0) + (c.total_embed_cost || 0), 0)
  const activeCount = collections.filter(c => c.status === 'active').length

  return (
    <div className="space-y-3">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/25">
            <Database className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">Vector Stores</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Register, monitor, and manage Qdrant-backed knowledge bases for RAG and semantic search.</p>
          </div>
        </div>
        <div className="flex gap-1.5">
          {[
            { label: 'Agents', href: '/agents' },
            { label: 'Workflows', href: '/workflows' },
            { label: 'Eval Studio', href: '/evaluation' },
            { label: 'MCP Servers', href: '/mcp' },
          ].map(({ label, href }) => (
            <Link key={label} href={href} className="rounded-full bg-cyan-100 dark:bg-cyan-900/30 px-2.5 py-1 text-[10px] font-semibold text-cyan-700 dark:text-cyan-300 hover:bg-cyan-200 dark:hover:bg-cyan-800/40 transition-colors">{label}</Link>
          ))}
        </div>
      </div>

      {/* ── KPI strip ──────────────────────────────────── */}
      <div className="grid grid-cols-8 gap-2">
        {[
          { label: 'Collections', value: total },
          { label: 'Active', value: activeCount, accent: true },
          { label: 'Documents', value: totalDocs.toLocaleString() },
          { label: 'Total Size', value: bytes(totalSize) },
          { label: 'Queries', value: totalQueries.toLocaleString() },
          { label: 'Total Cost', value: money(totalCost), accent: true },
          { label: 'Calls 30d', value: lifecyclePosture?.observe_context.provider_calls_30d ?? '—' },
          { label: 'Workflows', value: lifecyclePosture?.build_context.workflows ?? '—' },
        ].map(({ label, value, accent }) => (
          <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
            <p className={`text-sm font-bold ${accent ? 'text-cyan-600 dark:text-cyan-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* ── Posture chips ──────────────────────────────── */}
      {lifecyclePosture && (
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-lg border border-cyan-200/60 dark:border-cyan-800/40 bg-cyan-50/30 dark:bg-cyan-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 mb-1">Workspace</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-cyan-100 dark:bg-cyan-900/40 px-2 py-0.5 text-[10px] text-cyan-700 dark:text-cyan-300">{lifecyclePosture.workspace_context.workspace_name}</span>
              <span className="rounded-full bg-cyan-100 dark:bg-cyan-900/40 px-2 py-0.5 text-[10px] text-cyan-700 dark:text-cyan-300">${Number(lifecyclePosture.cost_context.cost_30d).toFixed(2)} 30d</span>
              <Link href="/workspace" className="text-[10px] text-cyan-600 hover:underline dark:text-cyan-400">Workspaces</Link>
            </div>
          </div>
          <div className="rounded-lg border border-blue-200/60 dark:border-blue-800/40 bg-blue-50/30 dark:bg-blue-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-1">Observe</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-[10px] text-blue-700 dark:text-blue-300">{lifecyclePosture.observe_context.provider_calls_30d} calls</span>
              <span className="rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-[10px] text-blue-700 dark:text-blue-300">{lifecyclePosture.observe_context.distinct_models_30d} models</span>
              <Link href="/request-explorer" className="text-[10px] text-blue-600 hover:underline dark:text-blue-400">Explorer</Link>
            </div>
          </div>
          <div className="rounded-lg border border-violet-200/60 dark:border-violet-800/40 bg-violet-50/30 dark:bg-violet-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-400 mb-1">Build</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{lifecyclePosture.build_context.workflows} workflows</span>
              <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{lifecyclePosture.build_context.eval_experiments} experiments</span>
              <Link href="/evaluation" className="text-[10px] text-violet-600 hover:underline dark:text-violet-400">Eval Studio</Link>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab bar ─────────────────────────────────────── */}
      <div className="flex gap-0.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-0.5">
        {([
          { id: 'stores' as ViewTab, label: 'Collections', icon: <Database className="h-3.5 w-3.5" />, count: total },
          { id: 'register' as ViewTab, label: 'Register Store', icon: <Plus className="h-3.5 w-3.5" /> },
          { id: 'guide' as ViewTab, label: 'Setup Guide', icon: <BookOpen className="h-3.5 w-3.5" /> },
        ]).map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
              tab === t.id ? 'bg-white dark:bg-slate-900 text-cyan-700 dark:text-cyan-300 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white'
            }`}>
            {t.icon}{t.label}
            {t.count !== undefined && t.count > 0 && (
              <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${tab === t.id ? 'bg-cyan-100 dark:bg-cyan-900/60 text-cyan-700 dark:text-cyan-300' : 'bg-slate-200 dark:bg-slate-700 text-slate-500'}`}>{t.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Collections tab ─────────────────────────────── */}
      {tab === 'stores' && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <button onClick={() => load()} disabled={loading} className="rounded-lg bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center gap-1">
              <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />Refresh
            </button>
            <button onClick={() => setTab('register')} className="rounded-lg bg-cyan-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-cyan-700 flex items-center gap-1">
              <Plus className="h-3 w-3" />Register Store
            </button>
          </div>

          {collections.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-900/60 px-6 py-14 text-center">
              <Database className="h-8 w-8 text-slate-400" />
              <h2 className="mt-3 text-sm font-bold text-slate-700 dark:text-slate-200">No vector stores registered</h2>
              <p className="mt-1 max-w-md text-xs text-slate-500">Register a Qdrant-backed collection to start tracking embeddings, queries, and cost. Use the Register tab or the API.</p>
              <div className="flex gap-2 mt-4">
                <button onClick={() => setTab('register')} className="rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-700 flex items-center gap-1">
                  <Plus className="h-3.5 w-3.5" />Register Store
                </button>
                <button onClick={() => setTab('guide')} className="rounded-lg bg-slate-100 dark:bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center gap-1">
                  <BookOpen className="h-3.5 w-3.5" />Setup Guide
                </button>
              </div>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {collections.map((c) => {
                const totalCost = (c.total_query_cost || 0) + (c.total_embed_cost || 0)
                return (
                  <div key={c.id} className="group rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between gap-2">
                      <Link href={`/vector-stores/${c.id}`} className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 dark:from-cyan-500/10 dark:to-blue-500/10">
                            <Database className="h-3.5 w-3.5 text-cyan-600 dark:text-cyan-400" />
                          </div>
                          <h3 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-cyan-600 dark:group-hover:text-cyan-400 truncate">{c.name}</h3>
                        </div>
                      </Link>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase ${statusCls(c.status)}`}>{c.status}</span>
                        <button onClick={() => handleDelete(c.id, c.name)} disabled={deleting === c.id}
                          className="rounded-lg p-1 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/30 opacity-0 group-hover:opacity-100 transition-all">
                          {deleting === c.id ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                        </button>
                      </div>
                    </div>
                    {c.description && <p className="mt-1.5 text-[10px] text-slate-500 dark:text-slate-400 line-clamp-2 pl-9">{c.description}</p>}
                    <div className="flex flex-wrap gap-1 mt-2 pl-9">
                      <span className="rounded-full bg-cyan-100 dark:bg-cyan-900/40 px-2 py-0.5 text-[9px] font-semibold text-cyan-700 dark:text-cyan-300">{c.distance_metric}</span>
                      {c.embedding_model && <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[9px] text-slate-600 dark:text-slate-300">{c.embedding_model}</span>}
                      {c.dimensions && <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[9px] text-slate-600 dark:text-slate-300">{c.dimensions}d</span>}
                    </div>
                    <div className="mt-3 grid grid-cols-4 gap-2">
                      {[
                        { label: 'Docs', value: c.document_count.toLocaleString() },
                        { label: 'Size', value: bytes(c.size_bytes) },
                        { label: 'Queries', value: c.total_queries.toLocaleString() },
                        { label: 'Cost', value: money(totalCost) },
                      ].map(({ label, value }) => (
                        <div key={label} className="rounded-lg bg-slate-50 dark:bg-slate-800/60 px-2 py-1.5 text-center">
                          <p className="text-xs font-bold text-slate-900 dark:text-white tabular-nums">{value}</p>
                          <p className="text-[9px] text-slate-500">{label}</p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400 pl-9">
                      <span className="flex items-center gap-1"><Clock className="h-3 w-3" />Last queried: {timeAgo(c.last_queried_at)}</span>
                      <Link href={`/vector-stores/${c.id}`} className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-0.5">Details<ChevronRight className="h-3 w-3" /></Link>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Register tab ───────────────────────────────── */}
      {tab === 'register' && (
        <div className="max-w-2xl space-y-3">
          <div className="rounded-xl border border-cyan-200/60 dark:border-cyan-800/40 bg-cyan-50/30 dark:bg-cyan-950/20 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Plus className="h-4 w-4 text-cyan-600" />
              <h2 className="text-xs font-bold text-slate-800 dark:text-white">Register a Vector Store</h2>
              <span className="text-[10px] text-slate-400 ml-auto">* Required</span>
            </div>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Collection name *</label>
                  <input value={formName} onChange={e => setFormName(e.target.value)} placeholder="my-knowledge-base" className={inputCls} />
                </div>
                <div>
                  <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Qdrant collection name *</label>
                  <input value={formQdrant} onChange={e => setFormQdrant(e.target.value)} placeholder="kb_v1" className={inputCls} />
                </div>
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Description</label>
                <input value={formDesc} onChange={e => setFormDesc(e.target.value)} placeholder="Knowledge base for customer support docs" className={inputCls} />
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-1">Embedding model preset</label>
                <div className="flex flex-wrap gap-1.5">
                  {EMBEDDING_PRESETS.map((p, i) => (
                    <button key={i} onClick={() => applyPreset(i)}
                      className={`rounded-lg px-2.5 py-1 text-[10px] font-medium transition ${formPreset === i ? 'bg-cyan-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'}`}>
                      {p.label}{p.dims ? ` (${p.dims}d)` : ''}
                    </button>
                  ))}
                </div>
              </div>
              {EMBEDDING_PRESETS[formPreset].label === 'Custom' && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Model name</label>
                    <input value={formModel} onChange={e => setFormModel(e.target.value)} placeholder="my-embedding-model" className={inputCls} />
                  </div>
                  <div>
                    <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Dimensions</label>
                    <input type="number" value={formDims || ''} onChange={e => setFormDims(parseInt(e.target.value) || 0)} placeholder="384" className={inputCls} />
                  </div>
                </div>
              )}
              <div>
                <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-1">Distance metric</label>
                <div className="flex gap-2">
                  {DISTANCE_METRICS.map(m => (
                    <button key={m.value} onClick={() => setFormMetric(m.value)}
                      className={`flex-1 rounded-lg border px-3 py-2 text-center transition ${formMetric === m.value
                        ? 'border-cyan-500 bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300'
                        : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:border-cyan-300 dark:hover:border-cyan-700'}`}>
                      <p className="text-xs font-semibold">{m.label}</p>
                      <p className="text-[9px] text-slate-400 mt-0.5">{m.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
                <p className="text-[10px] text-slate-400">Will register <span className="font-semibold text-slate-600 dark:text-slate-300">{formModel || 'unknown model'}</span> with <span className="font-semibold text-slate-600 dark:text-slate-300">{formDims || '?'}d</span> vectors using <span className="font-semibold text-slate-600 dark:text-slate-300">{formMetric}</span></p>
                <button onClick={() => void handleCreate()} disabled={creating || !formName.trim() || !formQdrant.trim()}
                  className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-cyan-700 disabled:opacity-40 transition">
                  {creating ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                  {creating ? 'Registering…' : 'Register Store'}
                </button>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 px-4 py-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-500" />
              <div>
                <p className="text-xs font-bold text-slate-800 dark:text-white">Prerequisites</p>
                <p className="mt-0.5 text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">A Qdrant instance must be running and accessible from the RunLedger API. The Qdrant collection should already exist before registering — RunLedger tracks it but does not create the underlying Qdrant collection.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Guide tab ──────────────────────────────────── */}
      {tab === 'guide' && (
        <div className="max-w-3xl space-y-3">
          {[
            {
              id: 'what',
              title: 'What are Vector Stores?',
              icon: <Layers className="h-4 w-4 text-cyan-600" />,
              content: (
                <div className="text-[10px] text-slate-600 dark:text-slate-300 leading-relaxed space-y-2">
                  <p>Vector Stores in RunLedger represent <strong>registered Qdrant collections</strong> used for Retrieval-Augmented Generation (RAG) and semantic search. RunLedger does not host the vector database — it connects to your existing Qdrant instance and tracks:</p>
                  <ul className="list-disc pl-4 space-y-1">
                    <li>Document count, index size, and embedding model metadata</li>
                    <li>Every query: text, results, latency, cost, and relevance scores</li>
                    <li>Embedding cost (for re-indexing) and query cost (per-request pricing)</li>
                    <li>Status lifecycle: active → inactive → deleted</li>
                  </ul>
                </div>
              ),
            },
            {
              id: 'prereqs',
              title: 'Prerequisites',
              icon: <Server className="h-4 w-4 text-blue-600" />,
              content: (
                <div className="text-[10px] text-slate-600 dark:text-slate-300 leading-relaxed space-y-2">
                  <p><strong>1. Qdrant instance</strong> — Running and accessible from the RunLedger API container. The default Docker Compose stack includes Qdrant on port 6333.</p>
                  <p><strong>2. Qdrant collection</strong> — Create the collection in Qdrant before registering in RunLedger. RunLedger tracks metadata but doesn't create collections in Qdrant.</p>
                  <p><strong>3. Embedding model</strong> — Decide on your model and dimensions before creating the collection (e.g., BGE Small = 384d, OpenAI Small = 1536d).</p>
                  <div className="rounded-lg bg-slate-100 dark:bg-slate-800 p-3 mt-2">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">Create Qdrant collection (Python)</p>
                      <button onClick={() => copySnippet(`from qdrant_client import QdrantClient, models\n\nclient = QdrantClient("http://localhost:6333")\n\nclient.create_collection(\n    collection_name="my_kb",\n    vectors_config=models.VectorParams(\n        size=384,\n        distance=models.Distance.COSINE,\n    ),\n)`)} className="text-[9px] text-cyan-600 hover:underline flex items-center gap-0.5"><Copy className="h-2.5 w-2.5" />Copy</button>
                    </div>
                    <pre className="text-[10px] text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{`from qdrant_client import QdrantClient, models

client = QdrantClient("http://localhost:6333")

client.create_collection(
    collection_name="my_kb",
    vectors_config=models.VectorParams(
        size=384,
        distance=models.Distance.COSINE,
    ),
)`}</pre>
                  </div>
                </div>
              ),
            },
            {
              id: 'register-api',
              title: 'Register via API',
              icon: <Zap className="h-4 w-4 text-emerald-600" />,
              content: (
                <div className="text-[10px] text-slate-600 dark:text-slate-300 leading-relaxed space-y-2">
                  <p>Register a vector store by POSTing to the RunLedger API. You can also use the <strong>Register Store</strong> tab above for a UI-based approach.</p>
                  <div className="rounded-lg bg-slate-100 dark:bg-slate-800 p-3">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">cURL</p>
                      <button onClick={() => copySnippet(`curl -X POST http://localhost:8201/vector-stores \\\n  -H "Authorization: Bearer YOUR_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d '{\n    "name": "my-knowledge-base",\n    "qdrant_collection": "my_kb",\n    "embedding_model": "bge-small-en-v1.5",\n    "dimensions": 384,\n    "distance_metric": "cosine",\n    "description": "Knowledge base for customer support"\n  }'`)} className="text-[9px] text-cyan-600 hover:underline flex items-center gap-0.5"><Copy className="h-2.5 w-2.5" />Copy</button>
                    </div>
                    <pre className="text-[10px] text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{`curl -X POST http://localhost:8201/vector-stores \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "my-knowledge-base",
    "qdrant_collection": "my_kb",
    "embedding_model": "bge-small-en-v1.5",
    "dimensions": 384,
    "distance_metric": "cosine",
    "description": "Knowledge base for customer support"
  }'`}</pre>
                  </div>
                  <div className="overflow-x-auto mt-2">
                    <table className="w-full text-[10px]">
                      <thead>
                        <tr className="border-b border-slate-200 dark:border-slate-700 text-[9px] font-semibold uppercase tracking-wider text-slate-500">
                          <th className="pb-1 pr-3 text-left">Field</th>
                          <th className="pb-1 pr-3 text-left">Required</th>
                          <th className="pb-1 text-left">Description</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {[
                          ['name', 'Yes', 'Display name for the collection (max 200 chars)'],
                          ['qdrant_collection', 'Yes', 'Name of the existing Qdrant collection to track'],
                          ['description', 'No', 'Human-readable description (max 2000 chars)'],
                          ['embedding_model', 'No', 'Model used for embeddings (e.g. bge-small-en-v1.5)'],
                          ['dimensions', 'No', 'Vector dimension count (1–10000)'],
                          ['distance_metric', 'No', 'cosine (default), euclidean, or dot'],
                          ['config', 'No', 'Arbitrary JSON config object'],
                        ].map(([f, r, d]) => (
                          <tr key={f}>
                            <td className="py-1 pr-3 font-mono font-semibold text-cyan-700 dark:text-cyan-300">{f}</td>
                            <td className="py-1 pr-3">{r}</td>
                            <td className="py-1 text-slate-500">{d}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ),
            },
            {
              id: 'query',
              title: 'Querying & Testing',
              icon: <Search className="h-4 w-4 text-violet-600" />,
              content: (
                <div className="text-[10px] text-slate-600 dark:text-slate-300 leading-relaxed space-y-2">
                  <p>Once registered, you can test semantic search from the collection detail page or via the API:</p>
                  <div className="rounded-lg bg-slate-100 dark:bg-slate-800 p-3">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">Search test</p>
                      <button onClick={() => copySnippet(`curl -X POST http://localhost:8201/vector-stores/{collection_id}/search-test \\\n  -H "Authorization: Bearer YOUR_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d '{"query": "How do I reset my password?", "top_k": 5}'`)} className="text-[9px] text-cyan-600 hover:underline flex items-center gap-0.5"><Copy className="h-2.5 w-2.5" />Copy</button>
                    </div>
                    <pre className="text-[10px] text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{`curl -X POST http://localhost:8201/vector-stores/{collection_id}/search-test \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "How do I reset my password?", "top_k": 5}'`}</pre>
                  </div>
                  <p>RunLedger logs every query: text, results, latency, cost, and relevance scores — visible in the collection detail view and queryable via the API.</p>
                </div>
              ),
            },
            {
              id: 'lifecycle',
              title: 'Lifecycle Management',
              icon: <FileText className="h-4 w-4 text-amber-600" />,
              content: (
                <div className="text-[10px] text-slate-600 dark:text-slate-300 leading-relaxed space-y-2">
                  <p>Collections follow a lifecycle: <span className="font-semibold text-emerald-600">active</span> → <span className="font-semibold text-amber-600">inactive</span> → <span className="font-semibold text-rose-600">deleted</span>.</p>
                  <ul className="list-disc pl-4 space-y-1">
                    <li><strong>Active:</strong> Queries are routed and tracked. Default state after registration.</li>
                    <li><strong>Inactive:</strong> Queries are paused. Use this during re-indexing or maintenance.</li>
                    <li><strong>Deleted:</strong> Soft-deleted. The Qdrant collection is not affected — only RunLedger tracking stops.</li>
                  </ul>
                  <p>Update status via PUT <code className="rounded bg-slate-200 dark:bg-slate-700 px-1">{'PUT /vector-stores/{id}'}</code> with <code className="rounded bg-slate-200 dark:bg-slate-700 px-1">{`{"status": "inactive"}`}</code>.</p>
                </div>
              ),
            },
          ].map(section => (
            <div key={section.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 overflow-hidden">
              <button onClick={() => setExpandedGuide(expandedGuide === section.id ? null : section.id)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                {section.icon}
                <span className="text-xs font-bold text-slate-800 dark:text-white flex-1">{section.title}</span>
                <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform ${expandedGuide === section.id ? '' : '-rotate-90'}`} />
              </button>
              {expandedGuide === section.id && (
                <div className="px-4 pb-4 pt-0 pl-11">{section.content}</div>
              )}
            </div>
          ))}

          <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 px-4 py-3">
            <div className="flex items-start gap-2">
              <Sparkles className="mt-0.5 h-4 w-4 text-cyan-600" />
              <div>
                <p className="text-xs font-bold text-slate-800 dark:text-white">Architecture note</p>
                <p className="mt-0.5 text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">RunLedger is an observability and governance layer — it does not host vector data. Your Qdrant (or compatible) instance owns the vectors; RunLedger registers collections, proxies search-test requests for tracking, and aggregates cost/latency/quality metrics.</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
