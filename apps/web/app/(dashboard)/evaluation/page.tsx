'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import {
  FlaskConical, Database, BookText, Plus, Trash2, Play,
  CheckCircle, Clock, XCircle, Loader2,
} from 'lucide-react'
import {
  createDataset, listDatasets, createExperiment, listExperiments, runExperiment,
  listPrompts, createPrompt, deletePrompt, listVersions,
  listGatewayRoutes, listProviderPricing,
} from '@/lib/api'
import type { DatasetResponse, ExperimentResponse, PromptResponse, GatewayRoute, ProviderPricingResponse, PromptVersion } from '@/types/api'

// ── Helpers ───────────────────────────────────────────────────────────────────

type Tab = 'experiments' | 'datasets' | 'prompts'

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

// ── Model selector — pulls from gateway route aliases + provider pricing ──────

function ModelSelect({
  value, onChange, placeholder, routes, pricing,
}: {
  value: string
  onChange: (v: string) => void
  placeholder: string
  routes: GatewayRoute[]
  pricing: ProviderPricingResponse[]
}) {
  const aliases = Array.from(new Set(routes.map((r) => r.alias)))
  const models = Array.from(new Set(pricing.map((p) => `${p.provider}/${p.model}`)))

  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className={inputCls}>
      <option value="">{placeholder}</option>
      {aliases.length > 0 && (
        <optgroup label="Gateway Aliases">
          {aliases.map((a) => (
            <option key={`alias:${a}`} value={a}>{a} (alias)</option>
          ))}
        </optgroup>
      )}
      {models.length > 0 && (
        <optgroup label="Provider Models">
          {models.map((m) => (
            <option key={`model:${m}`} value={m.split('/')[1]}>{m}</option>
          ))}
        </optgroup>
      )}
    </select>
  )
}

// ── Prompt version selector ────────────────────────────────────────────────────

function PromptVersionSelect({
  apiKey, prompts, promptName, onPromptChange,
  versionId, onVersionChange,
}: {
  apiKey: string
  prompts: PromptResponse[]
  promptName: string
  onPromptChange: (name: string) => void
  versionId: string
  onVersionChange: (v: string) => void
}) {
  const [versions, setVersions] = useState<PromptVersion[]>([])

  useEffect(() => {
    if (!promptName || !apiKey) { setVersions([]); onVersionChange(''); return }
    listVersions(apiKey, promptName)
      .then((r) => setVersions(r.items))
      .catch(() => setVersions([]))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [promptName, apiKey])

  return (
    <div className="flex gap-2">
      <select value={promptName} onChange={(e) => { onPromptChange(e.target.value); onVersionChange('') }} className={inputCls}>
        <option value="">No prompt (use all runs)</option>
        {prompts.map((p) => (
          <option key={p.id} value={p.name}>{p.name}</option>
        ))}
      </select>
      {promptName && (
        <select value={versionId} onChange={(e) => onVersionChange(e.target.value)} className={`${inputCls} w-36 shrink-0`}>
          <option value="">Latest</option>
          {versions.map((v) => (
            <option key={v.id} value={String(v.version)}>v{v.version}{v.commit_message ? ` — ${v.commit_message.slice(0, 20)}` : ''}</option>
          ))}
        </select>
      )}
    </div>
  )
}

// ── Experiments tab ───────────────────────────────────────────────────────────

function ExperimentsTab({
  experiments, datasets, prompts, routes, pricing, loading,
  onCreate, onRun,
}: {
  experiments: ExperimentResponse[]
  datasets: DatasetResponse[]
  prompts: PromptResponse[]
  routes: GatewayRoute[]
  pricing: ProviderPricingResponse[]
  loading: boolean
  onCreate: (data: { name: string; dataset_id: string; configs: Array<{ model: string; prompt_name?: string; prompt_version?: number }> }) => Promise<void>
  onRun: (id: string) => Promise<void>
}) {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const [name, setName] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [modelA, setModelA] = useState('')
  const [modelB, setModelB] = useState('')
  const [promptA, setPromptA] = useState('')
  const [promptVersionA, setPromptVersionA] = useState('')
  const [promptB, setPromptB] = useState('')
  const [promptVersionB, setPromptVersionB] = useState('')
  const [creating, setCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)

  function buildConfigs() {
    const cfgA: { model: string; prompt_name?: string; prompt_version?: number } = { model: modelA }
    if (promptA) { cfgA.prompt_name = promptA; if (promptVersionA) cfgA.prompt_version = parseInt(promptVersionA) }
    const configs = [cfgA]
    if (modelB) {
      const cfgB: { model: string; prompt_name?: string; prompt_version?: number } = { model: modelB }
      if (promptB) { cfgB.prompt_name = promptB; if (promptVersionB) cfgB.prompt_version = parseInt(promptVersionB) }
      configs.push(cfgB)
    }
    return configs
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setCreating(true)
    await onCreate({ name, dataset_id: datasetId, configs: buildConfigs() })
    setName(''); setDatasetId(''); setModelA(''); setModelB('')
    setPromptA(''); setPromptVersionA(''); setPromptB(''); setPromptVersionB('')
    setShowForm(false)
    setCreating(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Run A/B experiments to compare model cost, latency, and quality across your datasets. Optionally scope each config to a specific prompt version.
          </p>
        </div>
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
                <label className={labelCls}>Experiment Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="gpt-4o vs mistral" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Dataset</label>
                <select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} required className={inputCls}>
                  <option value="">Select dataset…</option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>{d.name} ({d.run_count} runs)</option>
                  ))}
                </select>
              </div>
            </div>
            {/* Config A */}
            <div className="rounded-lg border border-slate-100 dark:border-slate-800 p-3 space-y-3">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Config A — Baseline</p>
              <div>
                <label className={labelCls}>Model</label>
                <ModelSelect value={modelA} onChange={setModelA} placeholder="Select model A…" routes={routes} pricing={pricing} />
              </div>
              <div>
                <label className={labelCls}>Prompt (optional — scope tokens to runs using this prompt version)</label>
                <PromptVersionSelect apiKey={apiKey} prompts={prompts} promptName={promptA} onPromptChange={setPromptA} versionId={promptVersionA} onVersionChange={setPromptVersionA} />
              </div>
            </div>
            {/* Config B */}
            <div className="rounded-lg border border-slate-100 dark:border-slate-800 p-3 space-y-3">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Config B — Challenger (optional)</p>
              <div>
                <label className={labelCls}>Model</label>
                <ModelSelect value={modelB} onChange={setModelB} placeholder="Select model B…" routes={routes} pricing={pricing} />
              </div>
              {modelB && (
                <div>
                  <label className={labelCls}>Prompt (optional)</label>
                  <PromptVersionSelect apiKey={apiKey} prompts={prompts} promptName={promptB} onPromptChange={setPromptB} versionId={promptVersionB} onVersionChange={setPromptVersionB} />
                </div>
              )}
            </div>
            <div className="flex gap-2 pt-1">
              <button type="submit" disabled={creating || !name || !datasetId || !modelA}
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
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Models</th>
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
                  <p className="text-sm text-slate-500 dark:text-slate-400">No experiments yet. Create one to start comparing models.</p>
                </td>
              </tr>
            ) : experiments.map((exp) => (
              <tr key={exp.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">{exp.name}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {exp.configs.map((c, i) => (
                      <span key={i} className="flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-mono text-slate-600 dark:text-slate-300">
                        {c.model}
                        {c.prompt_name && (
                          <span className="ml-1 rounded-full bg-teal-100 dark:bg-teal-900/50 px-1.5 py-0 text-[10px] text-teal-700 dark:text-teal-300">
                            {c.prompt_name}{c.prompt_version != null ? `@v${c.prompt_version}` : ''}
                          </span>
                        )}
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
                  <div className="flex gap-2">
                    {exp.status === 'pending' && (
                      <button onClick={() => onRun(exp.id)}
                        className="flex items-center gap-1 rounded-lg bg-teal-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-teal-700">
                        <Play className="h-3 w-3" /> Run
                      </button>
                    )}
                    {exp.status === 'completed' && (
                      <Link href={`/replay/${exp.id}`}
                        className="flex items-center gap-1 rounded-lg bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-700">
                        <CheckCircle className="h-3 w-3" /> Results
                      </Link>
                    )}
                  </div>
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
  datasets: DatasetResponse[]
  loading: boolean
  onCreate: (data: { name: string; run_ids: string[]; source: string }) => Promise<void>
}) {
  const [name, setName] = useState('')
  const [runIds, setRunIds] = useState('')
  const [source, setSource] = useState('live_runs')
  const [creating, setCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setCreating(true)
    const ids = runIds.split('\n').map((s) => s.trim()).filter(Boolean)
    await onCreate({ name, run_ids: ids, source })
    setName(''); setRunIds(''); setSource('live_runs')
    setShowForm(false)
    setCreating(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Capture sets of production runs to use as ground truth for experiments.
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
                <label className={labelCls}>Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="customer-support-q4" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Source type</label>
                <select value={source} onChange={(e) => setSource(e.target.value)} className={inputCls}>
                  <option value="live_runs">live_runs</option>
                  <option value="manual">manual</option>
                </select>
              </div>
            </div>
            <div>
              <label className={labelCls}>Run IDs (one per line)</label>
              <textarea value={runIds} onChange={(e) => setRunIds(e.target.value)} rows={4}
                className={`${inputCls} font-mono`} placeholder="paste run UUIDs here…" />
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
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Source</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Runs</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={4} /> :
             datasets.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center">
                  <Database className="mx-auto mb-2 h-8 w-8 text-slate-300 dark:text-slate-600" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">No datasets yet. Capture production runs to build one.</p>
                </td>
              </tr>
            ) : datasets.map((d) => (
              <tr key={d.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">{d.name}</td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs text-slate-600 dark:text-slate-300">{d.source}</span>
                </td>
                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{d.run_count}</td>
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

// ── Main page ─────────────────────────────────────────────────────────────────

export default function EvaluationPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const [tab, setTab] = useState<Tab>('experiments')
  const [loading, setLoading] = useState(true)

  const [experiments, setExperiments] = useState<ExperimentResponse[]>([])
  const [datasets, setDatasets] = useState<DatasetResponse[]>([])
  const [prompts, setPrompts] = useState<PromptResponse[]>([])
  const [routes, setRoutes] = useState<GatewayRoute[]>([])
  const [pricing, setPricing] = useState<ProviderPricingResponse[]>([])

  const refresh = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [exp, ds, pr, rt, prc] = await Promise.all([
        listExperiments(apiKey),
        listDatasets(apiKey),
        listPrompts(apiKey),
        listGatewayRoutes(apiKey, true),
        listProviderPricing(apiKey),
      ])
      setExperiments(exp.items)
      setDatasets(ds.items)
      setPrompts(pr.items)
      setRoutes(rt.items)
      setPricing(prc.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load evaluation data')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { refresh() }, [refresh])

  async function handleCreateExperiment({ name, dataset_id, configs }: { name: string; dataset_id: string; configs: Array<{ model: string; prompt_name?: string; prompt_version?: number }> }) {
    try {
      await createExperiment(apiKey, { name, dataset_id, configs })
      toast.success('Experiment created')
      await refresh()
    } catch { toast.error('Failed to create experiment') }
  }

  async function handleRunExperiment(id: string) {
    try {
      await runExperiment(apiKey, id)
      setExperiments((prev) => prev.map((e) => (e.id === id ? { ...e, status: 'running' } : e)))
      toast.success('Experiment queued')
    } catch { toast.error('Failed to run experiment') }
  }

  async function handleCreateDataset(data: { name: string; run_ids: string[]; source: string }) {
    try {
      await createDataset(apiKey, data)
      toast.success('Dataset created')
      await refresh()
    } catch { toast.error('Failed to create dataset') }
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: 'experiments', label: 'Experiments', icon: <FlaskConical className="h-4 w-4" />, count: experiments.length },
    { id: 'datasets', label: 'Datasets', icon: <Database className="h-4 w-4" />, count: datasets.length },
    { id: 'prompts', label: 'Prompts', icon: <BookText className="h-4 w-4" />, count: prompts.length },
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
          routes={routes}
          pricing={pricing}
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
    </div>
  )
}
