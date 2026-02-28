'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { createDataset, listDatasets, createExperiment, listExperiments, runExperiment } from '@/lib/api'
import type { DatasetResponse, ExperimentResponse } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FlaskConical } from 'lucide-react'
import Link from 'next/link'

const STATUS_BADGE: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600',
  running: 'bg-blue-100 text-blue-700 animate-pulse',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

export default function ReplayPage() {
  const { data: session } = useSession()
  const [datasets, setDatasets] = useState<DatasetResponse[]>([])
  const [experiments, setExperiments] = useState<ExperimentResponse[]>([])
  const [loading, setLoading] = useState(true)

  // New dataset form
  const [dsName, setDsName] = useState('')
  const [dsRunIds, setDsRunIds] = useState('')
  const [dsSource, setDsSource] = useState('live_runs')
  const [dsCreating, setDsCreating] = useState(false)

  // New experiment form
  const [expName, setExpName] = useState('')
  const [expDatasetId, setExpDatasetId] = useState('')
  const [expModelA, setExpModelA] = useState('')
  const [expModelB, setExpModelB] = useState('')
  const [expCreating, setExpCreating] = useState(false)

  function refresh(key: string) {
    Promise.all([listDatasets(key), listExperiments(key)]).then(([ds, ex]) => {
      setDatasets(ds.items)
      setExperiments(ex.items)
      setLoading(false)
    })
  }

  useEffect(() => {
    if (!session?.apiKey) return
    refresh(session.apiKey as string)
  }, [session?.apiKey])

  async function handleCreateDataset(e: React.FormEvent) {
    e.preventDefault()
    if (!session?.apiKey) return
    setDsCreating(true)
    const runIds = dsRunIds.split('\n').map((s) => s.trim()).filter(Boolean)
    await createDataset(session.apiKey as string, { name: dsName, run_ids: runIds, source: dsSource })
    setDsName('')
    setDsRunIds('')
    setDsCreating(false)
    refresh(session.apiKey as string)
  }

  async function handleCreateExperiment(e: React.FormEvent) {
    e.preventDefault()
    if (!session?.apiKey) return
    setExpCreating(true)
    const configs = [
      { model: expModelA },
      { model: expModelB },
    ].filter((c) => c.model)
    await createExperiment(session.apiKey as string, { dataset_id: expDatasetId, name: expName, configs })
    setExpName('')
    setExpModelA('')
    setExpModelB('')
    setExpCreating(false)
    refresh(session.apiKey as string)
  }

  async function handleRun(id: string) {
    if (!session?.apiKey) return
    await runExperiment(session.apiKey as string, id)
    setExperiments((prev) =>
      prev.map((e) => (e.id === id ? { ...e, status: 'running' } : e))
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <FlaskConical className="h-5 w-5 text-gray-500" />
        <h1 className="text-xl font-semibold">Replay</h1>
        <span className="text-sm text-gray-400">— cost-projection experiments</span>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ── Datasets panel ── */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Datasets</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-sm text-gray-400">Loading…</p>
              ) : datasets.length === 0 ? (
                <p className="text-sm text-gray-400">No datasets yet.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-xs font-medium text-gray-500">
                      <th className="pb-2 pr-3">Name</th>
                      <th className="pb-2 pr-3">Source</th>
                      <th className="pb-2 pr-3">Runs</th>
                      <th className="pb-2">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datasets.map((d) => (
                      <tr key={d.id} className="border-b last:border-0">
                        <td className="py-1.5 pr-3 font-medium">{d.name}</td>
                        <td className="py-1.5 pr-3 text-gray-500">{d.source}</td>
                        <td className="py-1.5 pr-3">{d.run_count}</td>
                        <td className="py-1.5 text-gray-400 text-xs">
                          {new Date(d.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-gray-700">New Dataset</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateDataset} className="space-y-3">
                <div>
                  <label className="text-xs text-gray-500">Name</label>
                  <input
                    value={dsName}
                    onChange={(e) => setDsName(e.target.value)}
                    required
                    className="mt-1 w-full rounded border px-2 py-1 text-sm"
                    placeholder="my-dataset"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Run IDs (one per line)</label>
                  <textarea
                    value={dsRunIds}
                    onChange={(e) => setDsRunIds(e.target.value)}
                    rows={4}
                    className="mt-1 w-full rounded border px-2 py-1 font-mono text-xs"
                    placeholder="uuid&#10;uuid&#10;…"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Source</label>
                  <select
                    value={dsSource}
                    onChange={(e) => setDsSource(e.target.value)}
                    className="mt-1 w-full rounded border px-2 py-1 text-sm"
                  >
                    <option value="live_runs">live_runs</option>
                    <option value="manual">manual</option>
                  </select>
                </div>
                <button
                  type="submit"
                  disabled={dsCreating}
                  className="rounded bg-gray-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
                >
                  {dsCreating ? 'Creating…' : 'Create Dataset'}
                </button>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* ── Experiments panel ── */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Experiments</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-sm text-gray-400">Loading…</p>
              ) : experiments.length === 0 ? (
                <p className="text-sm text-gray-400">No experiments yet.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-xs font-medium text-gray-500">
                      <th className="pb-2 pr-3">Name</th>
                      <th className="pb-2 pr-3">Configs</th>
                      <th className="pb-2 pr-3">Status</th>
                      <th className="pb-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {experiments.map((e) => (
                      <tr key={e.id} className="border-b last:border-0">
                        <td className="py-1.5 pr-3 font-medium">{e.name}</td>
                        <td className="py-1.5 pr-3 text-xs text-gray-500">
                          {e.configs.map((c) => c.model).join(', ')}
                        </td>
                        <td className="py-1.5 pr-3">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[e.status] ?? STATUS_BADGE.pending}`}
                          >
                            {e.status}
                          </span>
                        </td>
                        <td className="py-1.5 flex gap-2">
                          {e.status === 'pending' && (
                            <button
                              onClick={() => handleRun(e.id)}
                              className="rounded bg-blue-600 px-2 py-0.5 text-xs text-white hover:bg-blue-700"
                            >
                              Run
                            </button>
                          )}
                          {e.status === 'completed' && (
                            <Link
                              href={`/replay/${e.id}`}
                              className="rounded bg-green-600 px-2 py-0.5 text-xs text-white hover:bg-green-700"
                            >
                              Results
                            </Link>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-gray-700">New Experiment</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateExperiment} className="space-y-3">
                <div>
                  <label className="text-xs text-gray-500">Dataset</label>
                  <select
                    value={expDatasetId}
                    onChange={(e) => setExpDatasetId(e.target.value)}
                    required
                    className="mt-1 w-full rounded border px-2 py-1 text-sm"
                  >
                    <option value="">Select a dataset…</option>
                    {datasets.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.run_count} runs)
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Name</label>
                  <input
                    value={expName}
                    onChange={(e) => setExpName(e.target.value)}
                    required
                    className="mt-1 w-full rounded border px-2 py-1 text-sm"
                    placeholder="gpt-4o vs gpt-4o-mini"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-gray-500">Model A</label>
                    <input
                      value={expModelA}
                      onChange={(e) => setExpModelA(e.target.value)}
                      required
                      className="mt-1 w-full rounded border px-2 py-1 text-sm"
                      placeholder="gpt-4o"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">Model B</label>
                    <input
                      value={expModelB}
                      onChange={(e) => setExpModelB(e.target.value)}
                      className="mt-1 w-full rounded border px-2 py-1 text-sm"
                      placeholder="gpt-4o-mini"
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={expCreating}
                  className="rounded bg-gray-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
                >
                  {expCreating ? 'Creating…' : 'Create Experiment'}
                </button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
