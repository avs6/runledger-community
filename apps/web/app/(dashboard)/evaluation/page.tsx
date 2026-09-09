'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import {
  FlaskConical, Database, BookText, Plus, Trash2, Play,
  CheckCircle, Clock, XCircle, Loader2, Star, Beaker,
  Network, ChevronDown, ChevronRight, Sparkles,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import {
  listEvalDatasets, createEvalDataset, listEvalExperiments, createEvalExperiment, runEvalExperiment,
  listPrompts, createPrompt, deletePrompt,
  listEvaluators, createEvaluator, deleteEvaluator, runEvaluator,
  getCostQuality, getBestValueModels,
  getBudgetDetailBuildPosture,
  getBudgetControlBuildPosture,
  getEvalReplayOrgGatewayPosture,
  getEvalReplayObservePosture,
  getBuildInternalPosture,
  getEvalStudioParentPosture,
  getReplayLabModePosture,
} from '@/lib/api'
import type {
  EvalDataset, EvalExperiment, DatasetItem, PromptResponse,
  EvaluatorResponse, CostQualityPoint, BestValueModel,
  BudgetDetailBuildPosture,
  BudgetControlBuildPosture,
  EvalReplayOrgGatewayPosture,
  EvalReplayObservePosture,
  BuildInternalPosture,
  EvalStudioParentPosture,
  ReplayLabModePosture,
} from '@/types/api'
import QualityScoresTab from '@/components/evaluation/QualityScoresTab'
import { num } from '@/lib/utils'

type Tab = 'scores' | 'experiments' | 'datasets' | 'prompts' | 'evaluators' | 'replay'

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300 animate-pulse',
  completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/60 dark:text-red-300',
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  pending: <Clock className="h-3 w-3" />,
  running: <Loader2 className="h-3 w-3 animate-spin" />,
  completed: <CheckCircle className="h-3 w-3" />,
  failed: <XCircle className="h-3 w-3" />,
}

function SkeletonRows({ cols, rows = 3 }: { cols: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-3 py-1.5">
              <div className="h-3 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500'

const labelCls = 'block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5'

const PAGE_SIZE = 20

function Pagination({ page, totalPages, total, onPageChange }: { page: number; totalPages: number; total: number; onPageChange: (p: number) => void }) {
  if (totalPages <= 1) return null
  const from = page * PAGE_SIZE + 1
  const to = Math.min((page + 1) * PAGE_SIZE, total)
  return (
    <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 pt-2 mt-2">
      <span className="text-[10px] text-slate-400">{from}–{to} of {total}</span>
      <div className="flex gap-1">
        <button onClick={() => onPageChange(page - 1)} disabled={page === 0} className="rounded px-2 py-0.5 text-[10px] font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30">Prev</button>
        <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages - 1} className="rounded px-2 py-0.5 text-[10px] font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30">Next</button>
      </div>
    </div>
  )
}

// ── Experiments tab ───────────────────────────────────────────────────────────

function ExperimentsTab({
  experiments, datasets, prompts, loading,
  onCreate, onRun, canWrite,
}: {
  experiments: EvalExperiment[]
  datasets: EvalDataset[]
  prompts: PromptResponse[]
  loading: boolean
  onCreate: (data: { name: string; description?: string; dataset_id?: string; prompt_name?: string; prompt_version?: number; models: Array<{ model: string; provider: string; label: null }> }) => Promise<void>
  onRun: (id: string) => Promise<void>
  canWrite: boolean
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [promptName, setPromptName] = useState('')
  const [promptVersion, setPromptVersion] = useState('')
  const [modelStr, setModelStr] = useState('gpt-4o')
  const [provider, setProvider] = useState('openai')
  const [creating, setCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [page, setPage] = useState(0)

  const totalPages = Math.ceil(experiments.length / PAGE_SIZE)
  const paged = experiments.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setCreating(true)
    await onCreate({
      name: name.trim(),
      description: description.trim() || undefined,
      dataset_id: datasetId || undefined,
      prompt_name: promptName || undefined,
      prompt_version: promptVersion ? parseInt(promptVersion) : undefined,
      models: modelStr ? [{ model: modelStr, provider, label: null }] : [],
    })
    setName(''); setDescription(''); setDatasetId(''); setPromptName(''); setPromptVersion(''); setModelStr('gpt-4o')
    setShowForm(false)
    setCreating(false)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500 dark:text-slate-400">Run prompts against datasets and evaluate model performance.</p>
        {canWrite && (
          <button onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-1 rounded-lg bg-violet-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-violet-700">
            <Plus className="h-3.5 w-3.5" /> New Experiment
          </button>
        )}
      </div>

      {showForm && canWrite && (
        <div className="rounded-xl border border-violet-300 dark:border-violet-800/40 bg-violet-50 dark:bg-violet-950/20 p-4">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <div><label className={labelCls}>Name *</label><input value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. GPT-4o vs Claude" className={inputCls} /></div>
              <div><label className={labelCls}>Description</label><input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" className={inputCls} /></div>
              <div>
                <label className={labelCls}>Dataset</label>
                <select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className={inputCls}>
                  <option value="">— None —</option>
                  {datasets.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.item_count})</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Prompt</label>
                <select value={promptName} onChange={(e) => { setPromptName(e.target.value); setPromptVersion('') }} className={inputCls}>
                  <option value="">— None —</option>
                  {prompts.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
                </select>
              </div>
              {promptName && (
                <div><label className={labelCls}>Version (blank = latest)</label><input value={promptVersion} onChange={(e) => setPromptVersion(e.target.value)} type="number" min="1" placeholder="e.g. 3" className={inputCls} /></div>
              )}
              <div><label className={labelCls}>Model</label><input value={modelStr} onChange={(e) => setModelStr(e.target.value)} placeholder="gpt-4o" className={inputCls} /></div>
              <div>
                <label className={labelCls}>Provider</label>
                <select value={provider} onChange={(e) => setProvider(e.target.value)} className={inputCls}>
                  <option value="openai">OpenAI</option><option value="anthropic">Anthropic</option><option value="google">Google</option><option value="mistral">Mistral</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={creating || !name} className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50">{creating ? 'Creating…' : 'Create'}</button>
              <button type="button" onClick={() => setShowForm(false)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-800/60">
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Prompt / Models</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Status</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={4} /> :
             paged.length === 0 ? (
              <tr><td colSpan={4} className="px-3 py-8 text-center text-xs text-slate-400">No experiments yet.</td></tr>
            ) : paged.map((exp) => (
              <tr key={exp.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                <td className="px-3 py-1.5 font-medium text-slate-800 dark:text-slate-200">{exp.name}</td>
                <td className="px-3 py-1.5">
                  <div className="flex flex-wrap gap-1">
                    {exp.prompt_name && <span className="rounded-full bg-violet-100 dark:bg-violet-900/50 px-1.5 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{exp.prompt_name}{exp.prompt_version ? ` v${exp.prompt_version}` : ''}</span>}
                    {exp.models.map((m, i) => <span key={i} className="rounded-full bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-600 dark:text-slate-300">{m.model}</span>)}
                  </div>
                </td>
                <td className="px-3 py-1.5">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[exp.status] ?? STATUS_STYLES.pending}`}>{STATUS_ICON[exp.status]}{exp.status}</span>
                </td>
                {canWrite && (
                  <td className="px-3 py-1.5">
                    <button onClick={() => onRun(exp.id)} disabled={exp.status === 'running'}
                      className="flex items-center gap-1 rounded bg-violet-600 px-2 py-0.5 text-[10px] font-medium text-white hover:bg-violet-700 disabled:opacity-40">
                      <Play className="h-3 w-3" /> Run
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={page} totalPages={totalPages} total={experiments.length} onPageChange={setPage} />
      </div>
    </div>
  )
}

// ── Datasets tab ──────────────────────────────────────────────────────────────

function DatasetsTab({
  datasets, loading, onCreate, canWrite,
}: {
  datasets: EvalDataset[]
  loading: boolean
  onCreate: (data: { name: string; description?: string; items: DatasetItem[] }) => Promise<void>
  canWrite: boolean
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [itemsText, setItemsText] = useState('')
  const [inputMode, setInputMode] = useState<'paste' | 'upload' | 'url'>('paste')
  const [urlInput, setUrlInput] = useState('')
  const [creating, setCreating] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [page, setPage] = useState(0)

  const totalPages = Math.ceil(datasets.length / PAGE_SIZE)
  const paged = datasets.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  function parseItems(text: string): DatasetItem[] {
    const trimmed = text.trim()
    if (trimmed.startsWith('[')) return JSON.parse(trimmed) as DatasetItem[]
    return trimmed.split('\n').filter(Boolean).map(line => {
      const parts = line.split(',')
      return { input: parts[0]?.trim() ?? '', expected_output: parts[1]?.trim() || null, metadata: {} }
    })
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setItemsText(await file.text())
    setInputMode('paste')
  }

  async function handleFetchUrl() {
    if (!urlInput.trim()) return
    setFetching(true)
    try {
      const res = await fetch(urlInput.trim())
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setItemsText(await res.text())
      setInputMode('paste')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Fetch failed')
    } finally { setFetching(false) }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setCreating(true)
    try {
      const items = itemsText.trim() ? parseItems(itemsText) : []
      await onCreate({ name: name.trim(), description: description.trim() || undefined, items })
      setName(''); setDescription(''); setItemsText(''); setUrlInput('')
      setShowForm(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Parse failed — check CSV/JSON format')
    } finally { setCreating(false) }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500 dark:text-slate-400">Test case collections (input / expected output pairs) shared with Experiments.</p>
        {canWrite && (
          <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1 rounded-lg bg-violet-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-violet-700">
            <Plus className="h-3.5 w-3.5" /> New Dataset
          </button>
        )}
      </div>

      {showForm && canWrite && (
        <div className="rounded-xl border border-violet-300 dark:border-violet-800/40 bg-violet-50 dark:bg-violet-950/20 p-4">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><label className={labelCls}>Name *</label><input value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. Customer Q&A" className={inputCls} /></div>
              <div><label className={labelCls}>Description</label><input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" className={inputCls} /></div>
            </div>
            <div>
              <div className="flex gap-1 mb-2">
                {(['paste', 'upload', 'url'] as const).map(mode => (
                  <button key={mode} type="button" onClick={() => setInputMode(mode)}
                    className={`rounded px-2 py-0.5 text-[10px] font-medium capitalize ${inputMode === mode ? 'bg-violet-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'}`}>
                    {mode === 'paste' ? 'Paste' : mode === 'upload' ? 'Upload' : 'URL'}
                  </button>
                ))}
              </div>
              {inputMode === 'paste' && (
                <div><label className={labelCls}>Items (CSV or JSON array)</label><textarea value={itemsText} onChange={(e) => setItemsText(e.target.value)} rows={4} className={`${inputCls} font-mono`} placeholder={'What is 2+2?,4\nCapital of France?,Paris'} /></div>
              )}
              {inputMode === 'upload' && (
                <div>
                  <label className={labelCls}>Upload CSV or JSON</label>
                  <input type="file" accept=".csv,.json,.txt" onChange={handleFileUpload} className="block w-full text-xs text-slate-500 file:mr-3 file:rounded file:border-0 file:bg-violet-50 file:px-2.5 file:py-1 file:text-[10px] file:font-medium file:text-violet-700 dark:file:bg-violet-900/30 dark:file:text-violet-400" />
                </div>
              )}
              {inputMode === 'url' && (
                <div className="flex gap-2">
                  <input value={urlInput} onChange={(e) => setUrlInput(e.target.value)} className={inputCls} placeholder="https://raw.githubusercontent.com/..." />
                  <button type="button" onClick={handleFetchUrl} disabled={fetching} className="shrink-0 rounded-lg bg-slate-100 dark:bg-slate-800 px-2.5 py-1.5 text-[10px] font-medium text-slate-700 dark:text-slate-300 disabled:opacity-50">{fetching ? 'Fetching…' : 'Fetch'}</button>
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={creating || !name} className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50">{creating ? 'Creating…' : 'Create'}</button>
              <button type="button" onClick={() => setShowForm(false)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-800/60">
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Description</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Items</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={4} /> :
             paged.length === 0 ? (
              <tr><td colSpan={4} className="px-3 py-8 text-center text-xs text-slate-400">No datasets yet.</td></tr>
            ) : paged.map((d) => (
              <tr key={d.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                <td className="px-3 py-1.5 font-medium text-slate-800 dark:text-slate-200">{d.name}</td>
                <td className="px-3 py-1.5 max-w-xs truncate text-slate-500 dark:text-slate-400">{d.description ?? '—'}</td>
                <td className="px-3 py-1.5 tabular-nums text-slate-600 dark:text-slate-300">{d.item_count}</td>
                <td className="px-3 py-1.5 text-slate-500 dark:text-slate-400">{new Date(d.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={page} totalPages={totalPages} total={datasets.length} onPageChange={setPage} />
      </div>
    </div>
  )
}

// ── Prompts tab ───────────────────────────────────────────────────────────────

function PromptsTab({
  prompts, loading, onRefresh, canWrite,
}: {
  prompts: PromptResponse[]
  loading: boolean
  onRefresh: () => void
  canWrite: boolean
}) {
  const router = useRouter()
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [defaultEnv, setDefaultEnv] = useState('production')
  const [creating, setCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [page, setPage] = useState(0)

  const totalPages = Math.ceil(prompts.length / PAGE_SIZE)
  const paged = prompts.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreating(true)
    try {
      await createPrompt(apiKey, { name: name.trim(), description: description.trim() || null, default_environment: defaultEnv })
      toast.success(`Prompt "${name}" created`)
      setName(''); setDescription(''); setDefaultEnv('production'); setShowForm(false)
      onRefresh()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      toast.error(msg.includes('409') ? 'A prompt with that name already exists' : `Error: ${msg}`)
    } finally { setCreating(false) }
  }

  async function handleDelete(promptName: string) {
    if (!confirm(`Delete prompt "${promptName}" and all its versions?`)) return
    try {
      await deletePrompt(apiKey, promptName)
      toast.success('Prompt deleted')
      onRefresh()
    } catch { toast.error('Failed to delete prompt') }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500 dark:text-slate-400">Version-controlled prompt templates with variable substitution.</p>
        {canWrite && (
          <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1 rounded-lg bg-violet-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-violet-700">
            <Plus className="h-3.5 w-3.5" /> New Prompt
          </button>
        )}
      </div>

      {showForm && canWrite && (
        <div className="rounded-xl border border-violet-300 dark:border-violet-800/40 bg-violet-50 dark:bg-violet-950/20 p-4">
          <form onSubmit={handleCreate} className="grid grid-cols-3 gap-3">
            <div><label className={labelCls}>Name *</label><input value={name} onChange={(e) => setName(e.target.value)} required placeholder="support-agent" className={inputCls} /></div>
            <div><label className={labelCls}>Description</label><input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" className={inputCls} /></div>
            <div>
              <label className={labelCls}>Default Env</label>
              <select value={defaultEnv} onChange={(e) => setDefaultEnv(e.target.value)} className={inputCls}>
                <option value="production">production</option><option value="staging">staging</option><option value="dev">dev</option>
              </select>
            </div>
            <div className="col-span-3 flex gap-2">
              <button type="submit" disabled={creating} className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50">{creating ? 'Creating…' : 'Create'}</button>
              <button type="button" onClick={() => setShowForm(false)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-800/60">
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Description</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Env</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Created</th>
              <th className="px-3 py-1.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={5} /> :
             paged.length === 0 ? (
              <tr><td colSpan={5} className="px-3 py-8 text-center text-xs text-slate-400">No prompts yet.</td></tr>
            ) : paged.map((p) => (
              <tr key={p.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 cursor-pointer"
                onClick={() => router.push(`/prompts/${encodeURIComponent(p.name)}`)}>
                <td className="px-3 py-1.5 font-mono font-medium text-violet-700 dark:text-violet-400">{p.name}</td>
                <td className="px-3 py-1.5 max-w-xs truncate text-slate-500 dark:text-slate-400">{p.description ?? '—'}</td>
                <td className="px-3 py-1.5"><span className="rounded-full bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-600 dark:text-slate-300">{p.default_environment}</span></td>
                <td className="px-3 py-1.5 text-slate-500 dark:text-slate-400">{new Date(p.created_at).toLocaleDateString()}</td>
                {canWrite && (
                  <td className="px-3 py-1.5 text-right">
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(p.name) }} className="rounded p-0.5 text-slate-400 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={page} totalPages={totalPages} total={prompts.length} onPageChange={setPage} />
      </div>
    </div>
  )
}

// ── Evaluators tab ────────────────────────────────────────────────────────────

function EvaluatorsTab({
  evaluators, costQuality, bestValue, loading,
  onCreate, onDelete, onRun, canWrite,
}: {
  evaluators: EvaluatorResponse[]
  costQuality: CostQualityPoint[]
  bestValue: BestValueModel[]
  loading: boolean
  onCreate: (data: { name: string; description: string; type: string; config: Record<string, unknown> }) => Promise<void>
  onDelete: (id: string) => Promise<void>
  onRun: (id: string) => Promise<void>
  canWrite: boolean
}) {
  const [showForm, setShowForm] = useState(false)
  const [creating, setCreating] = useState(false)
  const [running, setRunning] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [type, setType] = useState<'rule' | 'llm_judge'>('rule')
  const [configText, setConfigText] = useState('{\n  "rules": []\n}')
  const [configError, setConfigError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    let config: Record<string, unknown> = {}
    try { config = JSON.parse(configText) } catch { setConfigError('Invalid JSON'); return }
    setConfigError('')
    setCreating(true)
    try {
      await onCreate({ name, description, type, config })
      setName(''); setDescription(''); setConfigText('{\n  "rules": []\n}'); setShowForm(false)
    } finally { setCreating(false) }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500 dark:text-slate-400">Rule-based and LLM-judge evaluator pipelines.</p>
        {canWrite && (
          <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1 rounded-lg bg-violet-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-violet-700">
            {showForm ? 'Cancel' : <><Plus className="h-3.5 w-3.5" /> New Evaluator</>}
          </button>
        )}
      </div>

      {showForm && canWrite && (
        <div className="rounded-xl border border-violet-300 dark:border-violet-800/40 bg-violet-50 dark:bg-violet-950/20 p-4">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><label className={labelCls}>Name</label><input value={name} onChange={(e) => setName(e.target.value)} required className={inputCls} placeholder="e.g. Quality Judge" /></div>
              <div>
                <label className={labelCls}>Type</label>
                <select value={type} onChange={(e) => { setType(e.target.value as 'rule' | 'llm_judge'); setConfigText(e.target.value === 'llm_judge' ? '{\n  "model": "gpt-4o-mini",\n  "criteria": "Rate quality 0-1."\n}' : '{\n  "rules": []\n}') }} className={inputCls}>
                  <option value="rule">Rule-based</option><option value="llm_judge">LLM Judge</option>
                </select>
              </div>
            </div>
            <div><label className={labelCls}>Description</label><input value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} placeholder="What does this evaluator check?" /></div>
            <div>
              <label className={labelCls}>Config (JSON)</label>
              <textarea value={configText} onChange={(e) => { setConfigText(e.target.value); setConfigError('') }} rows={4} className={`${inputCls} font-mono`} />
              {configError && <p className="text-[10px] text-red-500">{configError}</p>}
            </div>
            <button type="submit" disabled={creating || !name} className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50">{creating ? 'Creating…' : 'Create'}</button>
          </form>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-800/60">
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Type</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Status</th>
              <th className="px-3 py-1.5 text-right text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Runs</th>
              <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Last Run</th>
              <th className="px-3 py-1.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={6} /> :
             evaluators.length === 0 ? (
              <tr><td colSpan={6} className="px-3 py-8 text-center text-xs text-slate-400">No evaluators yet.</td></tr>
            ) : evaluators.map((ev) => (
              <tr key={ev.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                <td className="px-3 py-1.5 font-medium text-slate-800 dark:text-slate-100">{ev.name}</td>
                <td className="px-3 py-1.5">
                  <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${ev.type === 'llm_judge' ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/50 dark:text-violet-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'}`}>
                    {ev.type === 'llm_judge' ? 'LLM Judge' : 'Rule'}
                  </span>
                </td>
                <td className="px-3 py-1.5">
                  <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${ev.status === 'active' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>{ev.status}</span>
                </td>
                <td className="px-3 py-1.5 text-right tabular-nums text-slate-600 dark:text-slate-300">{ev.last_run_count.toLocaleString()}</td>
                <td className="px-3 py-1.5 text-slate-500 dark:text-slate-400">{ev.last_run_at ? new Date(ev.last_run_at).toLocaleDateString() : '—'}</td>
                <td className="px-3 py-1.5">
                  <div className="flex items-center justify-end gap-1.5">
                    {canWrite && (
                      <button onClick={async () => { setRunning(ev.id); try { await onRun(ev.id) } finally { setRunning(null) } }} disabled={running === ev.id}
                        className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-900/30 disabled:opacity-50">
                        {running === ev.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}Run
                      </button>
                    )}
                    {canWrite && <button onClick={() => onDelete(ev.id)} className="rounded p-0.5 text-slate-400 hover:text-red-500"><Trash2 className="h-3 w-3" /></button>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {costQuality.length > 0 && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 p-4">
          <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 mb-2">Cost vs Quality by Model</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] text-slate-500 dark:text-slate-400">
                  <th className="pb-1.5 text-left font-medium">Model</th>
                  <th className="pb-1.5 text-right font-medium">Avg Cost</th>
                  <th className="pb-1.5 text-right font-medium">Avg Score</th>
                  <th className="pb-1.5 text-right font-medium">Runs</th>
                </tr>
              </thead>
              <tbody>
                {costQuality.map((pt) => (
                  <tr key={pt.model} className="border-b border-slate-50 dark:border-slate-800/50">
                    <td className="py-1.5 font-mono text-slate-700 dark:text-slate-200">{pt.model}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-600 dark:text-slate-300">${Number(pt.avg_cost_usd).toFixed(6)}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-600 dark:text-slate-300">{pt.avg_score != null ? Number(pt.avg_score).toFixed(3) : '—'}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-600 dark:text-slate-300">{pt.run_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {bestValue.length > 0 && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 p-4">
          <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 mb-0.5">Best Value Models</h3>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 mb-2">Ranked by quality / cost (higher = better)</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] text-slate-500 dark:text-slate-400">
                  <th className="pb-1.5 text-left font-medium">#</th>
                  <th className="pb-1.5 text-left font-medium">Model</th>
                  <th className="pb-1.5 text-right font-medium">Score</th>
                  <th className="pb-1.5 text-right font-medium">Cost</th>
                  <th className="pb-1.5 text-right font-medium">Value</th>
                  <th className="pb-1.5 text-right font-medium">Runs</th>
                </tr>
              </thead>
              <tbody>
                {bestValue.map((bv, i) => (
                  <tr key={bv.model} className="border-b border-slate-50 dark:border-slate-800/50">
                    <td className="py-1.5 text-slate-400">#{i + 1}</td>
                    <td className="py-1.5 font-mono text-slate-700 dark:text-slate-200">{bv.model}</td>
                    <td className="py-1.5 text-right tabular-nums text-emerald-600 dark:text-emerald-400 font-medium">{Number(bv.avg_score).toFixed(3)}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-600 dark:text-slate-300">${Number(bv.avg_cost_usd).toFixed(6)}</td>
                    <td className="py-1.5 text-right tabular-nums text-violet-600 dark:text-violet-400 font-semibold">{Number(bv.value_score).toFixed(2)}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-600 dark:text-slate-300">{bv.run_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Replay tab ────────────────────────────────────────────────────────────────

function ReplayTab({
  datasets, experiments, loading, canWrite,
  onCreateDataset, onCreateExperiment, onRunExperiment,
  modePosture,
}: {
  datasets: EvalDataset[]
  experiments: EvalExperiment[]
  loading: boolean
  canWrite: boolean
  onCreateDataset: (data: { name: string; description?: string; items: DatasetItem[] }) => Promise<void>
  onCreateExperiment: (data: { name: string; description?: string; dataset_id?: string; prompt_name?: string; prompt_version?: number; models: Array<{ model: string; provider: string; label: null }> }) => Promise<void>
  onRunExperiment: (id: string) => Promise<void>
  modePosture: ReplayLabModePosture | null
}) {
  const [subTab, setSubTab] = useState<'datasets' | 'experiments'>('datasets')
  const [showNewDs, setShowNewDs] = useState(false)
  const [newDsName, setNewDsName] = useState('')
  const [creatingDs, setCreatingDs] = useState(false)
  const [showNewExp, setShowNewExp] = useState(false)
  const [newExpName, setNewExpName] = useState('')
  const [newExpDatasetId, setNewExpDatasetId] = useState('')
  const [newExpModel, setNewExpModel] = useState('')
  const [newExpProvider, setNewExpProvider] = useState('')
  const [creatingExp, setCreatingExp] = useState(false)
  const [expandedExp, setExpandedExp] = useState<string | null>(null)
  const [page, setPage] = useState(0)

  const items = subTab === 'datasets' ? datasets : experiments
  const totalPages = Math.ceil(items.length / PAGE_SIZE)
  const pagedDs = datasets.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const pagedExp = experiments.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const datasetMap = Object.fromEntries(datasets.map((d) => [d.id, d.name]))

  async function handleCreateDs() {
    if (!newDsName.trim()) return
    setCreatingDs(true)
    try {
      await onCreateDataset({ name: newDsName.trim(), items: [] })
      setNewDsName(''); setShowNewDs(false)
    } finally { setCreatingDs(false) }
  }

  async function handleCreateExp() {
    if (!newExpName.trim() || !newExpDatasetId || !newExpModel.trim() || !newExpProvider.trim()) return
    setCreatingExp(true)
    try {
      await onCreateExperiment({
        name: newExpName.trim(),
        dataset_id: newExpDatasetId,
        models: [{ model: newExpModel.trim(), provider: newExpProvider.trim(), label: null }],
      })
      setNewExpName(''); setNewExpDatasetId(''); setNewExpModel(''); setNewExpProvider(''); setShowNewExp(false)
    } finally { setCreatingExp(false) }
  }

  return (
    <div className="space-y-3">
      {modePosture && (
        <div className="grid grid-cols-4 gap-2">
          <div className="rounded-lg border border-amber-300 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-950/20 px-3 py-2">
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Chargeback Rules</p>
            <p className="text-sm font-bold text-slate-900 dark:text-white">{modePosture.chargeback_context.chargeback_rules}</p>
          </div>
          <div className="rounded-lg border border-amber-300 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-950/20 px-3 py-2">
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Cost 30d</p>
            <p className="text-sm font-bold text-amber-600 dark:text-amber-400">${num(modePosture.chargeback_context.cost_30d).toFixed(2)}</p>
          </div>
          <div className="rounded-lg border border-amber-300 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-950/20 px-3 py-2">
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Replay Experiments</p>
            <p className="text-sm font-bold text-slate-900 dark:text-white">{modePosture.replay_context.replay_experiments}</p>
          </div>
          <div className="rounded-lg border border-amber-300 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-950/20 px-3 py-2">
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Replay Datasets</p>
            <p className="text-sm font-bold text-slate-900 dark:text-white">{modePosture.replay_context.replay_datasets}</p>
          </div>
        </div>
      )}

      <div className="flex items-center gap-3 rounded-lg border border-violet-300 dark:border-violet-800/40 bg-violet-50 dark:bg-violet-950/20 px-3 py-2">
        <Network className="h-4 w-4 text-violet-600 dark:text-violet-400" />
        <p className="text-xs text-violet-800 dark:text-violet-200">Experiments replay traffic through gateway routes and model configs.</p>
        <div className="ml-auto flex gap-1.5">
          {[{ label: 'Gateway', href: '/gateway' }, { label: 'Providers', href: '/provider-profiles' }, { label: 'Routes', href: '/routes' }].map(({ label, href }) => (
            <Link key={label} href={href} className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] font-semibold text-violet-700 dark:text-violet-300 hover:bg-violet-200 dark:hover:bg-violet-800/50">{label}</Link>
          ))}
        </div>
      </div>

      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {(['datasets', 'experiments'] as const).map((t) => (
          <button key={t} onClick={() => { setSubTab(t); setPage(0) }}
            className={`px-3 py-1.5 text-xs font-medium capitalize ${subTab === t ? 'border-b-2 border-violet-500 text-violet-600 dark:text-violet-400' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}>
            {t}
          </button>
        ))}
      </div>

      {subTab === 'datasets' && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500 dark:text-slate-400">Replay datasets for model comparison.</p>
            {canWrite && <button onClick={() => setShowNewDs(!showNewDs)} className="flex items-center gap-1 rounded-lg bg-violet-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-violet-700"><Plus className="h-3.5 w-3.5" /> New Dataset</button>}
          </div>
          {showNewDs && (
            <div className="flex items-center gap-2">
              <input value={newDsName} onChange={(e) => setNewDsName(e.target.value)} placeholder="Dataset name" className={inputCls} />
              <button onClick={handleCreateDs} disabled={creatingDs} className="rounded-lg bg-violet-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50">{creatingDs ? 'Creating…' : 'Create'}</button>
            </div>
          )}
          <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-800/60">
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Source</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Items</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loading ? <SkeletonRows cols={4} /> :
                 pagedDs.length === 0 ? (
                  <tr><td colSpan={4} className="px-3 py-6 text-center text-xs text-slate-400">No datasets yet.</td></tr>
                ) : pagedDs.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                    <td className="px-3 py-1.5 font-medium text-slate-800 dark:text-slate-200">{d.name}</td>
                    <td className="px-3 py-1.5 text-slate-500">{d.source ?? '—'}</td>
                    <td className="px-3 py-1.5 tabular-nums">{d.item_count}</td>
                    <td className="px-3 py-1.5 text-slate-500">{new Date(d.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} totalPages={Math.ceil(datasets.length / PAGE_SIZE)} total={datasets.length} onPageChange={setPage} />
          </div>
        </div>
      )}

      {subTab === 'experiments' && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500 dark:text-slate-400">Re-run datasets with different model configs to compare costs.</p>
            {canWrite && <button onClick={() => setShowNewExp(!showNewExp)} className="flex items-center gap-1 rounded-lg bg-violet-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-violet-700"><Plus className="h-3.5 w-3.5" /> New Experiment</button>}
          </div>
          {showNewExp && (
            <div className="flex flex-wrap items-center gap-2">
              <input value={newExpName} onChange={(e) => setNewExpName(e.target.value)} placeholder="Experiment name" className={inputCls} />
              <select value={newExpDatasetId} onChange={(e) => setNewExpDatasetId(e.target.value)} className={inputCls}>
                <option value="">Select dataset</option>
                {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
              <input value={newExpModel} onChange={(e) => setNewExpModel(e.target.value)} placeholder="Model" className={inputCls} />
              <input value={newExpProvider} onChange={(e) => setNewExpProvider(e.target.value)} placeholder="Provider" className={inputCls} />
              <button onClick={handleCreateExp} disabled={creatingExp} className="rounded-lg bg-violet-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50">{creatingExp ? 'Creating…' : 'Create'}</button>
            </div>
          )}
          <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-800/60">
                  <th className="px-3 py-1.5 w-6" />
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Status</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Dataset</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Models</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Scores</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Created</th>
                  <th className="px-3 py-1.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loading ? <SkeletonRows cols={8} /> :
                 pagedExp.length === 0 ? (
                  <tr><td colSpan={8} className="px-3 py-6 text-center text-xs text-slate-400">No experiments yet.</td></tr>
                ) : pagedExp.map((e) => (
                  <>
                    <tr key={e.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                      <td className="px-3 py-1.5">
                        {e.status === 'completed' && e.results && (
                          <button onClick={() => setExpandedExp(expandedExp === e.id ? null : e.id)}>
                            {expandedExp === e.id ? <ChevronDown className="h-3.5 w-3.5 text-slate-400" /> : <ChevronRight className="h-3.5 w-3.5 text-slate-400" />}
                          </button>
                        )}
                      </td>
                      <td className="px-3 py-1.5 font-medium text-slate-800 dark:text-slate-200">{e.name}</td>
                      <td className="px-3 py-1.5">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[e.status] ?? ''}`}>{STATUS_ICON[e.status]}{e.status}</span>
                      </td>
                      <td className="px-3 py-1.5 text-slate-500">{e.dataset_id ? datasetMap[e.dataset_id] ?? e.dataset_id.slice(0, 8) : '—'}</td>
                      <td className="px-3 py-1.5 text-slate-500 font-mono">{e.models.map((m) => `${m.provider}/${m.model}`).join(', ') || '—'}</td>
                      <td className="px-3 py-1.5 tabular-nums">{e.scores_created}</td>
                      <td className="px-3 py-1.5 text-slate-500">{new Date(e.created_at).toLocaleDateString()}</td>
                      <td className="px-3 py-1.5">
                        {e.status === 'pending' && canWrite && (
                          <button onClick={() => onRunExperiment(e.id)} className="flex items-center gap-1 rounded bg-emerald-600 px-2 py-0.5 text-[10px] font-medium text-white hover:bg-emerald-700">
                            <Play className="h-3 w-3" /> Run
                          </button>
                        )}
                      </td>
                    </tr>
                    {expandedExp === e.id && e.results && (
                      <tr key={`${e.id}-r`} className="border-b border-slate-100 dark:border-slate-800">
                        <td colSpan={8} className="px-4 py-2">
                          <pre className="max-h-48 overflow-auto rounded-lg bg-slate-50 dark:bg-slate-800 p-2 text-[10px] font-mono">{JSON.stringify(e.results, null, 2)}</pre>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
            <Pagination page={page} totalPages={Math.ceil(experiments.length / PAGE_SIZE)} total={experiments.length} onPageChange={setPage} />
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function EvaluationPage() {
  const { data: session } = useSession()
  const { canWrite } = useRole()
  const router = useRouter()
  const searchParams = useSearchParams()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const parseTab = useCallback((value: string | null): Tab => {
    if (value === 'scores' || value === 'experiments' || value === 'datasets' || value === 'prompts' || value === 'evaluators' || value === 'replay') return value
    return 'experiments'
  }, [])

  const [tab, setTab] = useState<Tab>(parseTab(searchParams.get('tab')))
  const [loading, setLoading] = useState(true)

  const [experiments, setExperiments] = useState<EvalExperiment[]>([])
  const [datasets, setDatasets] = useState<EvalDataset[]>([])
  const [prompts, setPrompts] = useState<PromptResponse[]>([])
  const [evaluators, setEvaluators] = useState<EvaluatorResponse[]>([])
  const [costQuality, setCostQuality] = useState<CostQualityPoint[]>([])
  const [bestValue, setBestValue] = useState<BestValueModel[]>([])
  const [budgetBuildPosture, setBudgetBuildPosture] = useState<BudgetDetailBuildPosture | null>(null)
  const [budgetControlBuildPosture, setBudgetControlBuildPosture] = useState<BudgetControlBuildPosture | null>(null)
  const [orgGatewayPosture, setOrgGatewayPosture] = useState<EvalReplayOrgGatewayPosture | null>(null)
  const [observePosture, setObservePosture] = useState<EvalReplayObservePosture | null>(null)
  const [buildPosture, setBuildPosture] = useState<BuildInternalPosture | null>(null)
  const [parentPosture, setParentPosture] = useState<EvalStudioParentPosture | null>(null)
  const [modePosture, setModePosture] = useState<ReplayLabModePosture | null>(null)

  const refresh = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [exp, ds, pr, evs, cq, bv] = await Promise.all([
        listEvalExperiments(apiKey),
        listEvalDatasets(apiKey),
        listPrompts(apiKey),
        listEvaluators(apiKey),
        getCostQuality(apiKey).catch(() => ({ items: [] })),
        getBestValueModels(apiKey).catch(() => ({ items: [] })),
      ])
      setExperiments(exp.items)
      setDatasets(ds.items)
      setPrompts(pr.items)
      setEvaluators(evs.items)
      setCostQuality(cq.items)
      setBestValue(bv.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load evaluation data')
    } finally { setLoading(false) }
  }, [apiKey])

  useEffect(() => {
    refresh()
    if (apiKey) {
      getBudgetDetailBuildPosture(apiKey).then(setBudgetBuildPosture).catch(() => {})
      getBudgetControlBuildPosture(apiKey).then(setBudgetControlBuildPosture).catch(() => {})
      getEvalReplayOrgGatewayPosture(apiKey).then(setOrgGatewayPosture).catch(() => {})
      getEvalReplayObservePosture(apiKey).then(setObservePosture).catch(() => {})
      getBuildInternalPosture(apiKey).then(setBuildPosture).catch(() => {})
      getEvalStudioParentPosture(apiKey).then(setParentPosture).catch(() => {})
      getReplayLabModePosture(apiKey).then(setModePosture).catch(() => {})
    }
  }, [refresh])

  useEffect(() => {
    const next = parseTab(searchParams.get('tab'))
    setTab((current) => (current === next ? current : next))
  }, [parseTab, searchParams])

  function handleTabChange(next: Tab) {
    setTab(next)
    router.replace(`/evaluation?tab=${next}`)
  }

  async function handleCreateExperiment(data: { name: string; description?: string; dataset_id?: string; prompt_name?: string; prompt_version?: number; models: Array<{ model: string; provider: string; label: null }> }) {
    try { await createEvalExperiment(apiKey, data); toast.success('Experiment created'); await refresh() } catch { toast.error('Failed to create experiment') }
  }

  async function handleRunExperiment(id: string) {
    try { const updated = await runEvalExperiment(apiKey, id); setExperiments((prev) => prev.map((e) => (e.id === id ? updated : e))); toast.success('Experiment completed') } catch { toast.error('Failed to run experiment') }
  }

  async function handleCreateDataset(data: { name: string; description?: string; items: DatasetItem[] }) {
    try { await createEvalDataset(apiKey, data); toast.success('Dataset created'); await refresh() } catch { toast.error('Failed to create dataset') }
  }

  async function handleCreateEvaluator(data: { name: string; description: string; type: string; config: Record<string, unknown> }) {
    try { await createEvaluator(apiKey, data); toast.success('Evaluator created'); await refresh() } catch { toast.error('Failed to create evaluator') }
  }

  async function handleDeleteEvaluator(id: string) {
    try { await deleteEvaluator(apiKey, id); toast.success('Evaluator deleted'); setEvaluators((prev) => prev.filter((e) => e.id !== id)) } catch { toast.error('Failed to delete evaluator') }
  }

  async function handleRunEvaluator(id: string) {
    try { await runEvaluator(apiKey, id); toast.success('Evaluation queued'); await refresh() } catch { toast.error('Failed to queue evaluation') }
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: 'scores', label: 'Scores', icon: <Star className="h-3.5 w-3.5" /> },
    { id: 'experiments', label: 'Experiments', icon: <FlaskConical className="h-3.5 w-3.5" />, count: experiments.length },
    { id: 'datasets', label: 'Datasets', icon: <Database className="h-3.5 w-3.5" />, count: datasets.length },
    { id: 'prompts', label: 'Prompts', icon: <BookText className="h-3.5 w-3.5" />, count: prompts.length },
    { id: 'evaluators', label: 'Evaluators', icon: <CheckCircle className="h-3.5 w-3.5" />, count: evaluators.length },
    { id: 'replay', label: 'Replay Lab', icon: <Beaker className="h-3.5 w-3.5" /> },
  ]

  return (
    <div className="space-y-3">
      {/* ── Gradient header ────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">Evaluation Studio</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Compare models, manage datasets & prompts, run evaluator pipelines.</p>
          </div>
        </div>
        <div className="flex gap-1.5">
          {[
            { label: 'Playground', href: '/playground' },
            { label: 'Agents', href: '/agents' },
            { label: 'Workflows', href: '/workflows' },
            { label: 'Scorecards', href: '/model-scorecards' },
          ].map(({ label, href }) => (
            <Link key={label} href={href} className="rounded-full bg-violet-100 dark:bg-violet-900/30 px-2.5 py-1 text-[10px] font-semibold text-violet-700 dark:text-violet-300 hover:bg-violet-200 dark:hover:bg-violet-800/40 transition-colors">{label}</Link>
          ))}
        </div>
      </div>

      {/* ── KPI strip ──────────────────────────────────────── */}
      <div className="grid grid-cols-8 gap-2">
        {[
          { label: 'Experiments', value: experiments.length },
          { label: 'Datasets', value: datasets.length },
          { label: 'Prompts', value: prompts.length },
          { label: 'Evaluators', value: evaluators.length },
          { label: 'Scores', value: bestValue.length > 0 ? bestValue.reduce((a, b) => a + b.run_count, 0) : '—' },
          { label: 'Active Budgets', value: budgetBuildPosture?.budget_context.active_budgets ?? '—' },
          { label: '30d Spend', value: budgetBuildPosture ? `$${num(budgetBuildPosture.spend_context.total_spend_30d).toFixed(2)}` : '—', accent: true },
          { label: 'Hub Models', value: orgGatewayPosture?.ai_hub_context.hub_models ?? '—' },
        ].map(({ label, value, accent }) => (
          <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
            <p className={`text-sm font-bold ${accent ? 'text-violet-600 dark:text-violet-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* ── Posture chips ──────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-2">
        {budgetControlBuildPosture && (
          <div className="rounded-lg border border-emerald-300 dark:border-emerald-800/40 bg-emerald-50 dark:bg-emerald-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-1">FinOps</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-300">{budgetControlBuildPosture.budget_policy.active_budgets} budgets</span>
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-300">{num(budgetControlBuildPosture.budget_policy.avg_utilization_pct).toFixed(1)}% util</span>
              {budgetControlBuildPosture.budget_policy.breached_budgets > 0 && <span className="rounded-full bg-red-100 dark:bg-red-900/40 px-2 py-0.5 text-[10px] text-red-700 dark:text-red-300">{budgetControlBuildPosture.budget_policy.breached_budgets} breached</span>}
              <Link href="/budgets" className="text-[10px] text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            </div>
          </div>
        )}
        {orgGatewayPosture && (
          <div className="rounded-lg border border-blue-300 dark:border-blue-800/40 bg-blue-50 dark:bg-blue-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-1">Org & Providers</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-[10px] text-blue-700 dark:text-blue-300">{orgGatewayPosture.provider_context.distinct_providers} providers</span>
              <span className="rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-[10px] text-blue-700 dark:text-blue-300">{orgGatewayPosture.provider_context.active_routes} routes</span>
              <span className="rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-[10px] text-blue-700 dark:text-blue-300">{orgGatewayPosture.guardrail_context.guardrail_rules} guardrails</span>
              <Link href="/gateway" className="text-[10px] text-blue-600 hover:underline dark:text-blue-400">Gateway</Link>
            </div>
          </div>
        )}
        {buildPosture && (
          <div className="rounded-lg border border-rose-300 dark:border-rose-800/40 bg-rose-50 dark:bg-rose-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-1">Build & Improve</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-[10px] text-rose-700 dark:text-rose-300">{buildPosture.playground_context.sessions_30d} playground</span>
              <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-[10px] text-rose-700 dark:text-rose-300">{buildPosture.workflows_context.definitions} workflows</span>
              <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-[10px] text-rose-700 dark:text-rose-300">{buildPosture.scorecards_context.score_events_30d} scores</span>
              <Link href="/workflows" className="text-[10px] text-rose-600 hover:underline dark:text-rose-400">Workflows</Link>
            </div>
          </div>
        )}
      </div>

      {/* ── Tab bar ────────────────────────────────────────── */}
      <div className="flex gap-0.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-0.5">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => handleTabChange(t.id)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
              tab === t.id
                ? 'bg-white dark:bg-slate-900 text-violet-700 dark:text-violet-300 shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white'
            }`}
          >
            {t.icon}
            {t.label}
            {t.count !== undefined && t.count > 0 && (
              <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${
                tab === t.id ? 'bg-violet-100 dark:bg-violet-900/60 text-violet-700 dark:text-violet-300' : 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
              }`}>{t.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Tab content ────────────────────────────────────── */}
      {tab === 'scores' && <QualityScoresTab apiKey={apiKey} />}
      {tab === 'experiments' && (
        <ExperimentsTab experiments={experiments} datasets={datasets} prompts={prompts} loading={loading} onCreate={handleCreateExperiment} onRun={handleRunExperiment} canWrite={canWrite} />
      )}
      {tab === 'datasets' && (
        <DatasetsTab datasets={datasets} loading={loading} onCreate={handleCreateDataset} canWrite={canWrite} />
      )}
      {tab === 'prompts' && (
        <PromptsTab prompts={prompts} loading={loading} onRefresh={refresh} canWrite={canWrite} />
      )}
      {tab === 'evaluators' && (
        <EvaluatorsTab evaluators={evaluators} costQuality={costQuality} bestValue={bestValue} loading={loading} onCreate={handleCreateEvaluator} onDelete={handleDeleteEvaluator} onRun={handleRunEvaluator} canWrite={canWrite} />
      )}
      {tab === 'replay' && (
        <ReplayTab datasets={datasets} experiments={experiments} loading={loading} canWrite={canWrite}
          onCreateDataset={handleCreateDataset} onCreateExperiment={handleCreateExperiment} onRunExperiment={handleRunExperiment}
          modePosture={modePosture} />
      )}
    </div>
  )
}
