'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  listEvalDatasets,
  createEvalDataset,
  listEvalExperiments,
  createEvalExperiment,
  runEvalExperiment,
} from '@/lib/api'
import type { EvalDataset, EvalExperiment } from '@/types/api'
import Link from 'next/link'
import { Beaker, Network, Plus, Play, ChevronDown, ChevronRight } from 'lucide-react'
import { toast } from 'sonner'

export default function ReplayLabPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''

  const [tab, setTab] = useState<'datasets' | 'experiments'>('datasets')
  const [datasets, setDatasets] = useState<EvalDataset[]>([])
  const [experiments, setExperiments] = useState<EvalExperiment[]>([])
  const [loading, setLoading] = useState(true)

  const [showNewDataset, setShowNewDataset] = useState(false)
  const [newDsName, setNewDsName] = useState('')
  const [creatingDs, setCreatingDs] = useState(false)

  const [showNewExperiment, setShowNewExperiment] = useState(false)
  const [newExpName, setNewExpName] = useState('')
  const [newExpDatasetId, setNewExpDatasetId] = useState('')
  const [newExpModel, setNewExpModel] = useState('')
  const [newExpProvider, setNewExpProvider] = useState('')
  const [creatingExp, setCreatingExp] = useState(false)

  const [expandedExp, setExpandedExp] = useState<string | null>(null)

  useEffect(() => {
    if (!apiKey) return
    setLoading(true)
    Promise.all([listEvalDatasets(apiKey), listEvalExperiments(apiKey)])
      .then(([ds, ex]) => {
        setDatasets(ds.items)
        setExperiments(ex.items)
      })
      .catch(() => toast.error('Failed to load data'))
      .finally(() => setLoading(false))
  }, [apiKey])

  async function handleCreateDataset() {
    if (!newDsName.trim()) return
    setCreatingDs(true)
    try {
      const ds = await createEvalDataset(apiKey, { name: newDsName.trim() })
      setDatasets((prev) => [ds, ...prev])
      setNewDsName('')
      setShowNewDataset(false)
      toast.success('Dataset created')
    } catch {
      toast.error('Failed to create dataset')
    } finally {
      setCreatingDs(false)
    }
  }

  async function handleCreateExperiment() {
    if (!newExpName.trim() || !newExpDatasetId || !newExpModel.trim() || !newExpProvider.trim()) return
    setCreatingExp(true)
    try {
      const exp = await createEvalExperiment(apiKey, {
        name: newExpName.trim(),
        dataset_id: newExpDatasetId,
        models: [{ model: newExpModel.trim(), provider: newExpProvider.trim(), label: null }],
      })
      setExperiments((prev) => [exp, ...prev])
      setNewExpName('')
      setNewExpDatasetId('')
      setNewExpModel('')
      setNewExpProvider('')
      setShowNewExperiment(false)
      toast.success('Experiment created')
    } catch {
      toast.error('Failed to create experiment')
    } finally {
      setCreatingExp(false)
    }
  }

  async function handleRun(id: string) {
    try {
      const updated = await runEvalExperiment(apiKey, id)
      setExperiments((prev) => prev.map((e) => (e.id === id ? updated : e)))
      toast.success('Experiment started')
    } catch {
      toast.error('Failed to run experiment')
    }
  }

  const statusColor: Record<string, string> = {
    pending: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 animate-pulse',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  }

  const datasetMap = Object.fromEntries(datasets.map((d) => [d.id, d.name]))

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Beaker className="h-7 w-7 text-indigo-500" />
        <div>
          <h1 className="text-2xl font-bold">Replay Lab</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Re-run datasets with different model configs to compare costs
          </p>
        </div>
      </div>

      {/* Gateway context bar */}
      <div className="flex items-center gap-3 rounded-xl border border-violet-200 bg-violet-50/60 px-4 py-2.5 dark:border-violet-800 dark:bg-violet-950/30">
        <Network className="h-4 w-4 text-violet-600 dark:text-violet-400" />
        <p className="text-sm text-violet-800 dark:text-violet-200">
          Experiments replay traffic through gateway routes and model configs.
        </p>
        <div className="ml-auto flex gap-2">
          {[
            { label: 'Model Gateway', href: '/gateway' },
            { label: 'Provider Profiles', href: '/provider-profiles' },
            { label: 'Routes', href: '/routes' },
          ].map(({ label, href }) => (
            <Link key={label} href={href} className="rounded-full bg-violet-100 px-3 py-1 text-xs font-semibold text-violet-700 hover:bg-violet-200 dark:bg-violet-900/40 dark:text-violet-300 dark:hover:bg-violet-800/50 transition-colors">
              {label}
            </Link>
          ))}
        </div>
      </div>

      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-700">
        {(['datasets', 'experiments'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? 'border-b-2 border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'datasets' && (
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Datasets</h2>
            <button
              onClick={() => setShowNewDataset(!showNewDataset)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4" /> New Dataset
            </button>
          </div>

          {showNewDataset && (
            <div className="mb-4 flex items-center gap-2">
              <input
                value={newDsName}
                onChange={(e) => setNewDsName(e.target.value)}
                placeholder="Dataset name"
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
              />
              <button
                onClick={handleCreateDataset}
                disabled={creatingDs}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {creatingDs ? 'Creating...' : 'Create'}
              </button>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  <th className="pb-2 pr-4 font-medium">Name</th>
                  <th className="pb-2 pr-4 font-medium">Source</th>
                  <th className="pb-2 pr-4 font-medium">Items</th>
                  <th className="pb-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 3 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 4 }).map((_, j) => (
                        <td key={j} className="py-2 pr-4">
                          <div className="h-4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : datasets.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-400">
                      No datasets yet
                    </td>
                  </tr>
                ) : (
                  datasets.map((d) => (
                    <tr key={d.id} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-2 pr-4 font-medium">{d.name}</td>
                      <td className="py-2 pr-4 text-slate-500">{d.source ?? '—'}</td>
                      <td className="py-2 pr-4">{d.item_count}</td>
                      <td className="py-2 text-slate-500">{new Date(d.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'experiments' && (
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Experiments</h2>
            <button
              onClick={() => setShowNewExperiment(!showNewExperiment)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4" /> New Experiment
            </button>
          </div>

          {showNewExperiment && (
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <input
                value={newExpName}
                onChange={(e) => setNewExpName(e.target.value)}
                placeholder="Experiment name"
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
              />
              <select
                value={newExpDatasetId}
                onChange={(e) => setNewExpDatasetId(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
              >
                <option value="">Select dataset</option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
              <input
                value={newExpModel}
                onChange={(e) => setNewExpModel(e.target.value)}
                placeholder="Model"
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
              />
              <input
                value={newExpProvider}
                onChange={(e) => setNewExpProvider(e.target.value)}
                placeholder="Provider"
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
              />
              <button
                onClick={handleCreateExperiment}
                disabled={creatingExp}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {creatingExp ? 'Creating...' : 'Create'}
              </button>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  <th className="pb-2 pr-4 font-medium" />
                  <th className="pb-2 pr-4 font-medium">Name</th>
                  <th className="pb-2 pr-4 font-medium">Status</th>
                  <th className="pb-2 pr-4 font-medium">Dataset</th>
                  <th className="pb-2 pr-4 font-medium">Models</th>
                  <th className="pb-2 pr-4 font-medium">Scores</th>
                  <th className="pb-2 pr-4 font-medium">Created</th>
                  <th className="pb-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 3 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 8 }).map((_, j) => (
                        <td key={j} className="py-2 pr-4">
                          <div className="h-4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : experiments.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-400">
                      No experiments yet
                    </td>
                  </tr>
                ) : (
                  experiments.map((e) => (
                    <>
                      <tr key={e.id} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-2 pr-2">
                          {e.status === 'completed' && e.results && (
                            <button onClick={() => setExpandedExp(expandedExp === e.id ? null : e.id)}>
                              {expandedExp === e.id ? (
                                <ChevronDown className="h-4 w-4 text-slate-400" />
                              ) : (
                                <ChevronRight className="h-4 w-4 text-slate-400" />
                              )}
                            </button>
                          )}
                        </td>
                        <td className="py-2 pr-4 font-medium">{e.name}</td>
                        <td className="py-2 pr-4">
                          <span
                            className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${statusColor[e.status] ?? ''}`}
                          >
                            {e.status}
                          </span>
                        </td>
                        <td className="py-2 pr-4 text-slate-500">
                          {e.dataset_id ? datasetMap[e.dataset_id] ?? e.dataset_id : '—'}
                        </td>
                        <td className="py-2 pr-4 text-slate-500">
                          {e.models.map((m) => `${m.provider}/${m.model}`).join(', ') || '—'}
                        </td>
                        <td className="py-2 pr-4">{e.scores_created}</td>
                        <td className="py-2 pr-4 text-slate-500">
                          {new Date(e.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-2">
                          {e.status === 'pending' && (
                            <button
                              onClick={() => handleRun(e.id)}
                              className="inline-flex items-center gap-1 rounded-lg bg-green-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-700"
                            >
                              <Play className="h-3 w-3" /> Run
                            </button>
                          )}
                        </td>
                      </tr>
                      {expandedExp === e.id && e.results && (
                        <tr key={`${e.id}-results`} className="border-b border-slate-100 dark:border-slate-800">
                          <td colSpan={8} className="px-4 py-3">
                            <pre className="max-h-64 overflow-auto rounded-lg bg-slate-50 p-3 text-xs dark:bg-slate-800">
                              {JSON.stringify(e.results, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
