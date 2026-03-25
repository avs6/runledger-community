'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import {
  FlaskConical, Database, BookText, Plus, Trash2, Play,
  CheckCircle, Clock, XCircle, Loader2,
} from 'lucide-react'
import {
  listEvalDatasets, createEvalDataset, listEvalExperiments, createEvalExperiment, runEvalExperiment,
  listPrompts, createPrompt, deletePrompt,
  listEvaluators, createEvaluator, deleteEvaluator, runEvaluator,
  getCostQuality, getBestValueModels,
} from '@/lib/api'
import type {
  EvalDataset, EvalExperiment, DatasetItem, PromptResponse,
  EvaluatorResponse, CostQualityPoint, BestValueModel,
} from '@/types/api'

// ── Helpers ───────────────────────────────────────────────────────────────────

type Tab = 'experiments' | 'datasets' | 'prompts' | 'evaluators'

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
            <td key={j} className="px-4 py-3">
              <div className="h-4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500'

const labelCls = 'block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1'

// ── Experiments tab ───────────────────────────────────────────────────────────

function ExperimentsTab({
  experiments, datasets, prompts, loading,
  onCreate, onRun,
}: {
  experiments: EvalExperiment[]
  datasets: EvalDataset[]
  prompts: PromptResponse[]
  loading: boolean
  onCreate: (data: { name: string; description?: string; dataset_id?: string; prompt_name?: string; prompt_version?: number; models: Array<{ model: string; provider: string; label: null }> }) => Promise<void>
  onRun: (id: string) => Promise<void>
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Run prompts against datasets and evaluate model performance. Uses the datasets and prompts you have already created.
        </p>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-2 text-sm font-medium text-white hover:bg-teal-700"
        >
          <Plus className="h-4 w-4" />
          New Experiment
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-800 dark:text-white">Create Experiment</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className={labelCls}>Experiment Name *</label>
                <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. GPT-4o vs Claude" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Description</label>
                <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Dataset</label>
                <select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className={inputCls}>
                  <option value="">— None —</option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>{d.name} ({d.item_count} items)</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelCls}>Prompt</label>
                <select value={promptName} onChange={(e) => { setPromptName(e.target.value); setPromptVersion('') }} className={inputCls}>
                  <option value="">— None —</option>
                  {prompts.map((p) => (
                    <option key={p.id} value={p.name}>{p.name}</option>
                  ))}
                </select>
              </div>
              {promptName && (
                <div>
                  <label className={labelCls}>Prompt Version (blank = latest)</label>
                  <input value={promptVersion} onChange={(e) => setPromptVersion(e.target.value)} type="number" min="1" placeholder="e.g. 3" className={inputCls} />
                </div>
              )}
              <div>
                <label className={labelCls}>Model</label>
                <input value={modelStr} onChange={(e) => setModelStr(e.target.value)} placeholder="gpt-4o" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Provider</label>
                <select value={provider} onChange={(e) => setProvider(e.target.value)} className={inputCls}>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="google">Google</option>
                  <option value="mistral">Mistral</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <button type="submit" disabled={creating || !name}
                className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50">
                {creating ? 'Creating…' : 'Create Experiment'}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Prompt / Models</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={4} /> :
             experiments.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center">
                  <FlaskConical className="mx-auto mb-2 h-8 w-8 text-slate-300 dark:text-slate-600" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">No experiments yet. Create one above.</p>
                </td>
              </tr>
            ) : experiments.map((exp) => (
              <tr key={exp.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">{exp.name}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {exp.prompt_name && (
                      <span className="rounded-full bg-teal-100 dark:bg-teal-900/50 px-2 py-0.5 text-xs text-teal-700 dark:text-teal-300">
                        {exp.prompt_name}{exp.prompt_version ? ` v${exp.prompt_version}` : ''}
                      </span>
                    )}
                    {exp.models.map((m, i) => (
                      <span key={i} className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-mono text-slate-600 dark:text-slate-300">
                        {m.model}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[exp.status] ?? STATUS_STYLES.pending}`}>
                    {STATUS_ICON[exp.status]}
                    {exp.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => onRun(exp.id)}
                    disabled={exp.status === 'running'}
                    className="flex items-center gap-1 rounded-lg bg-teal-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-teal-700 disabled:opacity-40">
                    <Play className="h-3 w-3" /> Run
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Datasets tab ──────────────────────────────────────────────────────────────

function DatasetsTab({
  datasets, loading, onCreate,
}: {
  datasets: EvalDataset[]
  loading: boolean
  onCreate: (data: { name: string; description?: string; items: DatasetItem[] }) => Promise<void>
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [itemsText, setItemsText] = useState('')
  const [inputMode, setInputMode] = useState<'paste' | 'upload' | 'url'>('paste')
  const [urlInput, setUrlInput] = useState('')
  const [creating, setCreating] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [showForm, setShowForm] = useState(false)

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
    const text = await file.text()
    setItemsText(text)
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Test case collections (input / expected output pairs) shared with Experiments.
        </p>
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-2 text-sm font-medium text-white hover:bg-teal-700">
          <Plus className="h-4 w-4" /> New Dataset
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-800 dark:text-white">Create Dataset</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className={labelCls}>Name *</label>
                <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. Customer Q&A" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Description</label>
                <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" className={inputCls} />
              </div>
            </div>
            <div>
              <div className="flex gap-1 mb-3">
                {(['paste', 'upload', 'url'] as const).map(mode => (
                  <button key={mode} type="button" onClick={() => setInputMode(mode)}
                    className={`rounded px-3 py-1 text-xs font-medium capitalize ${inputMode === mode ? 'bg-teal-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'}`}>
                    {mode === 'paste' ? 'Paste' : mode === 'upload' ? 'Upload File' : 'From URL'}
                  </button>
                ))}
              </div>
              {inputMode === 'paste' && (
                <div>
                  <label className={labelCls}>Items (CSV: input,expected_output — or JSON array)</label>
                  <textarea value={itemsText} onChange={(e) => setItemsText(e.target.value)}
                    rows={5} className={`${inputCls} font-mono`} placeholder={'What is 2+2?,4\nCapital of France?,Paris'} />
                </div>
              )}
              {inputMode === 'upload' && (
                <div>
                  <label className={labelCls}>Upload CSV or JSON file</label>
                  <input type="file" accept=".csv,.json,.txt" onChange={handleFileUpload}
                    className="block w-full text-sm text-slate-500 file:mr-4 file:rounded file:border-0 file:bg-teal-50 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-teal-700 hover:file:bg-teal-100 dark:file:bg-teal-900/30 dark:file:text-teal-400" />
                  {itemsText && <p className="mt-1 text-xs text-green-600">✓ File loaded — switch to Paste to review</p>}
                </div>
              )}
              {inputMode === 'url' && (
                <div>
                  <label className={labelCls}>File URL (HTTP/HTTPS or GitHub raw)</label>
                  <div className="flex gap-2">
                    <input value={urlInput} onChange={(e) => setUrlInput(e.target.value)}
                      className={inputCls} placeholder="https://raw.githubusercontent.com/..." />
                    <button type="button" onClick={handleFetchUrl} disabled={fetching}
                      className="shrink-0 rounded-lg bg-slate-100 dark:bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 disabled:opacity-50">
                      {fetching ? 'Fetching…' : 'Fetch'}
                    </button>
                  </div>
                  {itemsText && <p className="mt-1 text-xs text-green-600">✓ Content loaded — switch to Paste to review</p>}
                </div>
              )}
            </div>
            <div className="flex gap-2 pt-1">
              <button type="submit" disabled={creating || !name}
                className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50">
                {creating ? 'Creating…' : 'Create Dataset'}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Description</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Items</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={4} /> :
             datasets.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center">
                  <Database className="mx-auto mb-2 h-8 w-8 text-slate-300 dark:text-slate-600" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">No datasets yet. Create one above or visit the Datasets page.</p>
                </td>
              </tr>
            ) : datasets.map((d) => (
              <tr key={d.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">{d.name}</td>
                <td className="px-4 py-3 max-w-xs truncate text-slate-500 dark:text-slate-400">{d.description ?? '—'}</td>
                <td className="px-4 py-3 tabular-nums text-slate-600 dark:text-slate-300">{d.item_count}</td>
                <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">{new Date(d.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Prompts tab ───────────────────────────────────────────────────────────────

function PromptsTab({
  prompts, loading, onRefresh,
}: {
  prompts: PromptResponse[]
  loading: boolean
  onRefresh: () => void
}) {
  const router = useRouter()
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [defaultEnv, setDefaultEnv] = useState('production')
  const [creating, setCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)

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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Version-controlled prompt templates with variable substitution and environment promotion.
        </p>
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-2 text-sm font-medium text-white hover:bg-teal-700">
          <Plus className="h-4 w-4" /> New Prompt
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-800 dark:text-white">Create Prompt</h3>
          <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className={labelCls}>Name *</label>
              <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="support-agent" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Description</label>
              <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Default Environment</label>
              <select value={defaultEnv} onChange={(e) => setDefaultEnv(e.target.value)} className={inputCls}>
                <option value="production">production</option>
                <option value="staging">staging</option>
                <option value="dev">dev</option>
              </select>
            </div>
            <div className="sm:col-span-3 flex gap-2">
              <button type="submit" disabled={creating}
                className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50">
                {creating ? 'Creating…' : 'Create'}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Description</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Env</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Created</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={5} /> :
             prompts.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center">
                  <BookText className="mx-auto mb-2 h-8 w-8 text-slate-300 dark:text-slate-600" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">No prompts yet. Create your first prompt template above.</p>
                </td>
              </tr>
            ) : prompts.map((p) => (
              <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer"
                onClick={() => router.push(`/prompts/${encodeURIComponent(p.name)}`)}>
                <td className="px-4 py-3 font-mono font-medium text-teal-700 dark:text-teal-400">{p.name}</td>
                <td className="px-4 py-3 max-w-xs truncate text-slate-600 dark:text-slate-300">{p.description ?? <span className="text-slate-400">—</span>}</td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs text-slate-600 dark:text-slate-300">{p.default_environment}</span>
                </td>
                <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">{new Date(p.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={(e) => { e.stopPropagation(); handleDelete(p.name) }}
                    className="rounded p-1 text-slate-400 hover:text-red-500 dark:hover:text-red-400">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Evaluators tab ────────────────────────────────────────────────────────────

function EvaluatorsTab({
  evaluators, costQuality, bestValue, loading,
  onCreate, onDelete, onRun,
}: {
  evaluators: EvaluatorResponse[]
  costQuality: CostQualityPoint[]
  bestValue: BestValueModel[]
  loading: boolean
  onCreate: (data: { name: string; description: string; type: string; config: Record<string, unknown> }) => Promise<void>
  onDelete: (id: string) => Promise<void>
  onRun: (id: string) => Promise<void>
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
    <div className="space-y-6">
      {/* Create evaluator */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Evaluators</h2>
          {showForm ? (
            <button
              onClick={() => setShowForm(false)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              Cancel
            </button>
          ) : (
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-700 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />New Evaluator
            </button>
          )}
        </div>

        {showForm && (
          <form onSubmit={handleSubmit} className="space-y-3 border-t border-slate-100 dark:border-slate-800 pt-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} required className={inputCls} placeholder="e.g. Quality Judge" />
              </div>
              <div>
                <label className={labelCls}>Type</label>
                <select value={type} onChange={(e) => { setType(e.target.value as 'rule' | 'llm_judge'); setConfigText(e.target.value === 'llm_judge' ? '{\n  "model": "gpt-4o-mini",\n  "criteria": "Rate the quality of the response from 0 to 1."\n}' : '{\n  "rules": []\n}') }} className={inputCls}>
                  <option value="rule">Rule-based</option>
                  <option value="llm_judge">LLM Judge</option>
                </select>
              </div>
            </div>
            <div>
              <label className={labelCls}>Description (optional)</label>
              <input value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} placeholder="What does this evaluator check?" />
            </div>
            <div>
              <label className={labelCls}>Config (JSON)</label>
              <textarea
                value={configText}
                onChange={(e) => { setConfigText(e.target.value); setConfigError('') }}
                rows={6}
                className={`${inputCls} font-mono text-xs`}
              />
              {configError && <p className="mt-1 text-xs text-red-500">{configError}</p>}
              {type === 'rule' && (
                <p className="mt-1 text-xs text-slate-400">
                  Rules: <code className="font-mono">{'[{"field":"status","op":"eq","value":"succeeded","score_if_pass":1,"score_if_fail":0}]'}</code>
                </p>
              )}
            </div>
            <button type="submit" disabled={creating || !name} className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 transition-colors">
              {creating && <Loader2 className="h-4 w-4 animate-spin" />}Create
            </button>
          </form>
        )}

        {/* Evaluators table */}
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
                <th className="pb-2 text-left font-medium px-1">Name</th>
                <th className="pb-2 text-left font-medium px-1">Type</th>
                <th className="pb-2 text-left font-medium px-1">Status</th>
                <th className="pb-2 text-right font-medium px-1">Runs</th>
                <th className="pb-2 text-left font-medium px-1">Last Run</th>
                <th className="pb-2 px-1"></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <SkeletonRows cols={6} />
              ) : evaluators.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-sm text-slate-400 dark:text-slate-500">
                    No evaluators yet — create one above.
                  </td>
                </tr>
              ) : (
                evaluators.map((ev) => (
                  <tr key={ev.id} className="border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30">
                    <td className="py-2.5 px-1 font-medium text-slate-800 dark:text-slate-100">{ev.name}</td>
                    <td className="py-2.5 px-1">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ev.type === 'llm_judge' ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/50 dark:text-violet-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'}`}>
                        {ev.type === 'llm_judge' ? 'LLM Judge' : 'Rule'}
                      </span>
                    </td>
                    <td className="py-2.5 px-1">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ev.status === 'active' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                        {ev.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-1 text-right tabular-nums text-slate-600 dark:text-slate-300">{ev.last_run_count.toLocaleString()}</td>
                    <td className="py-2.5 px-1 text-slate-500 dark:text-slate-400 text-xs">
                      {ev.last_run_at ? new Date(ev.last_run_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="py-2.5 px-1">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={async () => { setRunning(ev.id); try { await onRun(ev.id) } finally { setRunning(null) } }}
                          disabled={running === ev.id}
                          className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/30 transition-colors disabled:opacity-50"
                        >
                          {running === ev.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}Run
                        </button>
                        <button onClick={() => onDelete(ev.id)} className="rounded p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors">
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cost-quality chart */}
      {costQuality.length > 0 && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-4">Cost vs Quality by Model</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
                  <th className="pb-2 text-left font-medium px-1">Model</th>
                  <th className="pb-2 text-right font-medium px-1">Avg Cost</th>
                  <th className="pb-2 text-right font-medium px-1">Avg Score</th>
                  <th className="pb-2 text-right font-medium px-1">Runs</th>
                </tr>
              </thead>
              <tbody>
                {costQuality.map((pt) => (
                  <tr key={pt.model} className="border-b border-slate-50 dark:border-slate-800/50">
                    <td className="py-2 px-1 font-mono text-xs text-slate-700 dark:text-slate-200">{pt.model}</td>
                    <td className="py-2 px-1 text-right tabular-nums text-slate-600 dark:text-slate-300">${Number(pt.avg_cost_usd).toFixed(6)}</td>
                    <td className="py-2 px-1 text-right tabular-nums text-slate-600 dark:text-slate-300">
                      {pt.avg_score != null ? Number(pt.avg_score).toFixed(3) : '—'}
                    </td>
                    <td className="py-2 px-1 text-right tabular-nums text-slate-600 dark:text-slate-300">{pt.run_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Best value models */}
      {bestValue.length > 0 && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-1">Best Value Models</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">Ranked by quality ÷ cost ratio (higher = better value)</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
                  <th className="pb-2 text-left font-medium px-1">Rank</th>
                  <th className="pb-2 text-left font-medium px-1">Model</th>
                  <th className="pb-2 text-right font-medium px-1">Avg Score</th>
                  <th className="pb-2 text-right font-medium px-1">Avg Cost</th>
                  <th className="pb-2 text-right font-medium px-1">Value Score</th>
                  <th className="pb-2 text-right font-medium px-1">Runs</th>
                </tr>
              </thead>
              <tbody>
                {bestValue.map((bv, i) => (
                  <tr key={bv.model} className="border-b border-slate-50 dark:border-slate-800/50">
                    <td className="py-2 px-1 text-slate-500 dark:text-slate-400 text-xs font-medium">#{i + 1}</td>
                    <td className="py-2 px-1 font-mono text-xs text-slate-700 dark:text-slate-200">{bv.model}</td>
                    <td className="py-2 px-1 text-right tabular-nums text-emerald-600 dark:text-emerald-400 font-medium">{Number(bv.avg_score).toFixed(3)}</td>
                    <td className="py-2 px-1 text-right tabular-nums text-slate-600 dark:text-slate-300">${Number(bv.avg_cost_usd).toFixed(6)}</td>
                    <td className="py-2 px-1 text-right tabular-nums text-teal-600 dark:text-teal-400 font-semibold">{Number(bv.value_score).toFixed(2)}</td>
                    <td className="py-2 px-1 text-right tabular-nums text-slate-600 dark:text-slate-300">{bv.run_count}</td>
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

// ── Main page ─────────────────────────────────────────────────────────────────

export default function EvaluationPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const [tab, setTab] = useState<Tab>('experiments')
  const [loading, setLoading] = useState(true)

  const [experiments, setExperiments] = useState<EvalExperiment[]>([])
  const [datasets, setDatasets] = useState<EvalDataset[]>([])
  const [prompts, setPrompts] = useState<PromptResponse[]>([])
  const [evaluators, setEvaluators] = useState<EvaluatorResponse[]>([])
  const [costQuality, setCostQuality] = useState<CostQualityPoint[]>([])
  const [bestValue, setBestValue] = useState<BestValueModel[]>([])

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
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { refresh() }, [refresh])

  async function handleCreateExperiment(data: { name: string; description?: string; dataset_id?: string; prompt_name?: string; prompt_version?: number; models: Array<{ model: string; provider: string; label: null }> }) {
    try {
      await createEvalExperiment(apiKey, data)
      toast.success('Experiment created')
      await refresh()
    } catch { toast.error('Failed to create experiment') }
  }

  async function handleRunExperiment(id: string) {
    try {
      const updated = await runEvalExperiment(apiKey, id)
      setExperiments((prev) => prev.map((e) => (e.id === id ? updated : e)))
      toast.success('Experiment completed')
    } catch { toast.error('Failed to run experiment') }
  }

  async function handleCreateDataset(data: { name: string; description?: string; items: DatasetItem[] }) {
    try {
      await createEvalDataset(apiKey, data)
      toast.success('Dataset created')
      await refresh()
    } catch { toast.error('Failed to create dataset') }
  }

  async function handleCreateEvaluator(data: { name: string; description: string; type: string; config: Record<string, unknown> }) {
    try {
      await createEvaluator(apiKey, data)
      toast.success('Evaluator created')
      await refresh()
    } catch { toast.error('Failed to create evaluator') }
  }

  async function handleDeleteEvaluator(id: string) {
    try {
      await deleteEvaluator(apiKey, id)
      toast.success('Evaluator deleted')
      setEvaluators((prev) => prev.filter((e) => e.id !== id))
    } catch { toast.error('Failed to delete evaluator') }
  }

  async function handleRunEvaluator(id: string) {
    try {
      await runEvaluator(apiKey, id)
      toast.success('Evaluation queued — scores will appear shortly')
      await refresh()
    } catch { toast.error('Failed to queue evaluation') }
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: 'experiments', label: 'Experiments', icon: <FlaskConical className="h-4 w-4" />, count: experiments.length },
    { id: 'datasets', label: 'Datasets', icon: <Database className="h-4 w-4" />, count: datasets.length },
    { id: 'prompts', label: 'Prompts', icon: <BookText className="h-4 w-4" />, count: prompts.length },
    { id: 'evaluators', label: 'Evaluators', icon: <CheckCircle className="h-4 w-4" />, count: evaluators.length },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Evaluation</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Compare models with A/B experiments, manage evaluation datasets, and version prompt templates.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              tab === t.id
                ? 'bg-white dark:bg-slate-900 text-teal-700 dark:text-teal-300 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            {t.icon}
            {t.label}
            {t.count !== undefined && t.count > 0 && (
              <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
                tab === t.id ? 'bg-teal-100 dark:bg-teal-900/60 text-teal-700 dark:text-teal-300' : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
              }`}>
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === 'experiments' && (
        <ExperimentsTab
          experiments={experiments}
          datasets={datasets}
          prompts={prompts}
          loading={loading}
          onCreate={handleCreateExperiment}
          onRun={handleRunExperiment}
        />
      )}
      {tab === 'datasets' && (
        <DatasetsTab
          datasets={datasets}
          loading={loading}
          onCreate={handleCreateDataset}
        />
      )}
      {tab === 'prompts' && (
        <PromptsTab
          prompts={prompts}
          loading={loading}
          onRefresh={refresh}
        />
      )}
      {tab === 'evaluators' && (
        <EvaluatorsTab
          evaluators={evaluators}
          costQuality={costQuality}
          bestValue={bestValue}
          loading={loading}
          onCreate={handleCreateEvaluator}
          onDelete={handleDeleteEvaluator}
          onRun={handleRunEvaluator}
        />
      )}
    </div>
  )
}
