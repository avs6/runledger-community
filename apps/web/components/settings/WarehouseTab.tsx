'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Plus, Trash2, Play, TestTube, ToggleLeft, ToggleRight, CheckCircle,
  XCircle, AlertTriangle, Database, ChevronDown, ChevronRight,
} from 'lucide-react'
import { toast } from 'sonner'
import {
  listWarehouseDestinations,
  createWarehouseDestination,
  updateWarehouseDestination,
  deleteWarehouseDestination,
  testWarehouseDestination,
  listExportJobs,
  triggerExportJob,
} from '@/lib/api'
import type {
  WarehouseDestination,
  ExportJob,
  WarehouseProvider,
  WarehouseFormat,
  ExportJobStatus,
} from '@/types/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500 dark:focus:ring-violet-400'

const PROVIDERS: { value: WarehouseProvider; label: string; note: string }[] = [
  { value: 's3', label: 'AWS S3', note: 'Standard AWS S3' },
  { value: 'gcs', label: 'Google Cloud Storage', note: 'S3-compatible interop endpoint' },
  { value: 'r2', label: 'Cloudflare R2', note: 'endpoint_url required' },
]

const FORMATS: { value: WarehouseFormat; label: string }[] = [
  { value: 'jsonl', label: 'JSON Lines (JSONL)' },
  { value: 'parquet', label: 'Parquet (Snappy)' },
]

const ALL_RESOURCES = ['runs', 'spans', 'provider_calls']

const STATUS_BADGE: Record<ExportJobStatus, string> = {
  pending: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400',
  running: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
  completed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
  failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
}

function yesterday(): string {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toISOString().slice(0, 10)
}

export default function WarehouseTab({ apiKey }: { apiKey: string }) {
  const [destinations, setDestinations] = useState<WarehouseDestination[]>([])
  const [jobs, setJobs] = useState<ExportJob[]>([])
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [expandedDest, setExpandedDest] = useState<string | null>(null)

  // Create form state
  const [creating, setCreating] = useState(false)
  const [fName, setFName] = useState('')
  const [fProvider, setFProvider] = useState<WarehouseProvider>('s3')
  const [fBucket, setFBucket] = useState('')
  const [fPrefix, setFPrefix] = useState('')
  const [fRegion, setFRegion] = useState('')
  const [fEndpoint, setFEndpoint] = useState('')
  const [fKeyId, setFKeyId] = useState('')
  const [fSecret, setFSecret] = useState('')
  const [fFormat, setFFormat] = useState<WarehouseFormat>('jsonl')
  const [fResources, setFResources] = useState<string[]>(ALL_RESOURCES)

  // Testing state
  const [testingId, setTestingId] = useState<string | null>(null)
  const [triggeringId, setTriggeringId] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [destRes, jobRes] = await Promise.all([
        listWarehouseDestinations(apiKey, true),
        listExportJobs(apiKey),
      ])
      setDestinations(destRes.items)
      setJobs(jobRes.items)
    } catch {
      toast.error('Failed to load warehouse data')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { loadData() }, [loadData])

  function resetForm() {
    setFName(''); setFProvider('s3'); setFBucket(''); setFPrefix('')
    setFRegion(''); setFEndpoint(''); setFKeyId(''); setFSecret('')
    setFFormat('jsonl'); setFResources(ALL_RESOURCES)
  }

  async function handleCreate() {
    if (!fName || !fBucket || !fKeyId || !fSecret) {
      toast.error('Name, bucket, access key ID, and secret are required')
      return
    }
    setCreating(true)
    try {
      await createWarehouseDestination(apiKey, {
        name: fName,
        provider: fProvider,
        bucket: fBucket,
        prefix: fPrefix || '',
        region: fRegion || null,
        endpoint_url: fEndpoint || null,
        access_key_id: fKeyId,
        secret_access_key: fSecret,
        format: fFormat,
        resources: fResources,
      })
      toast.success('Destination created')
      setShowForm(false)
      resetForm()
      await loadData()
    } catch (e: unknown) {
      toast.error((e as Error)?.message ?? 'Failed to create destination')
    } finally {
      setCreating(false)
    }
  }

  async function handleToggle(dest: WarehouseDestination) {
    try {
      await updateWarehouseDestination(apiKey, dest.id, { is_active: !dest.is_active })
      toast.success(`Destination ${dest.is_active ? 'disabled' : 'enabled'}`)
      await loadData()
    } catch {
      toast.error('Failed to update destination')
    }
  }

  async function handleDelete(dest: WarehouseDestination) {
    if (!confirm(`Delete destination "${dest.name}"? All associated job history will be removed.`)) return
    try {
      await deleteWarehouseDestination(apiKey, dest.id)
      toast.success('Destination deleted')
      await loadData()
    } catch {
      toast.error('Failed to delete destination')
    }
  }

  async function handleTest(dest: WarehouseDestination) {
    setTestingId(dest.id)
    try {
      const result = await testWarehouseDestination(apiKey, dest.id)
      if (result.ok) {
        toast.success(`Connection OK — bucket "${dest.bucket}" is reachable`)
      } else {
        toast.error(`Connection failed: ${result.error}`)
      }
    } catch {
      toast.error('Connection test failed')
    } finally {
      setTestingId(null)
    }
  }

  async function handleTrigger(dest: WarehouseDestination) {
    setTriggeringId(dest.id)
    try {
      const job = await triggerExportJob(apiKey, {
        destination_id: dest.id,
        export_date: yesterday(),
      })
      toast.success(`Export job queued (${job.export_date})`)
      await loadData()
    } catch (e: unknown) {
      toast.error((e as Error)?.message ?? 'Failed to trigger export')
    } finally {
      setTriggeringId(null)
    }
  }

  function toggleResource(r: string) {
    setFResources(prev =>
      prev.includes(r) ? prev.filter(x => x !== r) : [...prev, r]
    )
  }

  const destJobs = (destId: string) => jobs.filter(j => j.destination_id === destId)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Warehouse Exports</h3>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
            Export agent runs, spans, and provider calls to S3-compatible storage in JSONL or Parquet format.
          </p>
        </div>
        <button
          onClick={() => setShowForm(v => !v)}
          className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700"
        >
          <Plus className="h-3.5 w-3.5" />
          New Destination
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4 space-y-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">Create Destination</h4>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Name</label>
              <input
                type="text"
                placeholder="Production S3"
                value={fName}
                onChange={e => setFName(e.target.value)}
                className={inputCls + ' w-full'}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Provider</label>
              <select
                value={fProvider}
                onChange={e => setFProvider(e.target.value as WarehouseProvider)}
                className={inputCls + ' w-full'}
              >
                {PROVIDERS.map(p => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                {PROVIDERS.find(p => p.value === fProvider)?.note}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Bucket</label>
              <input
                type="text"
                placeholder="my-export-bucket"
                value={fBucket}
                onChange={e => setFBucket(e.target.value)}
                className={inputCls + ' w-full'}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Prefix</label>
              <input
                type="text"
                placeholder="runledger/"
                value={fPrefix}
                onChange={e => setFPrefix(e.target.value)}
                className={inputCls + ' w-full'}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Region</label>
              <input
                type="text"
                placeholder="us-east-1 (leave blank for GCS/R2)"
                value={fRegion}
                onChange={e => setFRegion(e.target.value)}
                className={inputCls + ' w-full'}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Endpoint URL</label>
              <input
                type="text"
                placeholder="https://... (R2 or MinIO only)"
                value={fEndpoint}
                onChange={e => setFEndpoint(e.target.value)}
                className={inputCls + ' w-full'}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Access Key ID</label>
              <input
                type="text"
                placeholder="AKIA..."
                value={fKeyId}
                onChange={e => setFKeyId(e.target.value)}
                className={inputCls + ' w-full'}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Secret Access Key</label>
              <input
                type="password"
                placeholder="••••••••"
                value={fSecret}
                onChange={e => setFSecret(e.target.value)}
                className={inputCls + ' w-full'}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Format</label>
              <select
                value={fFormat}
                onChange={e => setFFormat(e.target.value as WarehouseFormat)}
                className={inputCls + ' w-full'}
              >
                {FORMATS.map(f => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Resources</label>
              <div className="flex gap-3 mt-1.5">
                {ALL_RESOURCES.map(r => (
                  <label key={r} className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={fResources.includes(r)}
                      onChange={() => toggleResource(r)}
                      className="rounded"
                    />
                    {r}
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 px-3 py-2">
            <AlertTriangle className="h-3.5 w-3.5 text-blue-500 shrink-0" />
            <p className="text-xs text-blue-700 dark:text-blue-400">
              Files are written as <code className="font-mono">{`{prefix}/{resource}/date={YYYY-MM-DD}/data.${fFormat}`}</code> — Hive-style partitioning for Snowflake external stages.
            </p>
          </div>

          <div className="flex gap-2 justify-end">
            <button
              onClick={() => { setShowForm(false); resetForm() }}
              className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={creating}
              className="rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
            >
              {creating ? 'Creating…' : 'Create Destination'}
            </button>
          </div>
        </div>
      )}

      {/* Destinations list */}
      {loading && destinations.length === 0 ? (
        <div className="space-y-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-16 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" />
          ))}
        </div>
      ) : destinations.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 dark:border-gray-700 py-10 text-center">
          <Database className="mx-auto h-8 w-8 text-gray-300 dark:text-gray-600 mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">No destinations configured</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            Add an S3, GCS, or R2 destination to start exporting daily snapshots
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {destinations.map(dest => {
            const djobs = destJobs(dest.id)
            const isOpen = expandedDest === dest.id
            return (
              <div
                key={dest.id}
                className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
              >
                {/* Destination header row */}
                <div className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-900">
                  <button
                    onClick={() => setExpandedDest(isOpen ? null : dest.id)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    {isOpen
                      ? <ChevronDown className="h-4 w-4" />
                      : <ChevronRight className="h-4 w-4" />}
                  </button>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{dest.name}</span>
                      <span className="text-xs font-mono text-gray-400 dark:text-gray-500 uppercase">{dest.provider}</span>
                      <span className="text-xs font-mono text-gray-400 dark:text-gray-500">{dest.format}</span>
                    </div>
                    <div className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 truncate">
                      {dest.bucket}/{dest.prefix || ''}
                      {dest.last_export_at && (
                        <span className="ml-2">
                          Last export: {new Date(dest.last_export_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Status toggle */}
                  <button
                    onClick={() => handleToggle(dest)}
                    className="flex items-center gap-1 text-xs"
                    title={dest.is_active ? 'Click to disable' : 'Click to enable'}
                  >
                    {dest.is_active ? (
                      <><ToggleRight className="h-4 w-4 text-violet-600" /><span className="text-violet-700 dark:text-violet-400">Active</span></>
                    ) : (
                      <><ToggleLeft className="h-4 w-4 text-gray-400" /><span className="text-gray-500">Inactive</span></>
                    )}
                  </button>

                  {/* Action buttons */}
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleTest(dest)}
                      disabled={testingId === dest.id}
                      title="Test connection"
                      className="rounded p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:opacity-40"
                    >
                      <TestTube className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => handleTrigger(dest)}
                      disabled={triggeringId === dest.id || !dest.is_active}
                      title="Trigger export (yesterday)"
                      className="rounded p-1.5 text-gray-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 disabled:opacity-40"
                    >
                      <Play className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(dest)}
                      title="Delete destination"
                      className="rounded p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                {/* Job history (expanded) */}
                {isOpen && (
                  <div className="border-t border-gray-100 dark:border-gray-800">
                    {djobs.length === 0 ? (
                      <p className="px-4 py-3 text-xs text-gray-400 dark:text-gray-500">No export jobs yet — click ▶ to trigger one.</p>
                    ) : (
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="bg-gray-50/60 dark:bg-gray-800/40 border-b border-gray-100 dark:border-gray-800">
                            <th className="px-4 py-2 text-left font-medium text-gray-500 dark:text-gray-400">Date</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-500 dark:text-gray-400">Status</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-500 dark:text-gray-400">Rows</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-500 dark:text-gray-400">Duration</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-500 dark:text-gray-400">Files</th>
                          </tr>
                        </thead>
                        <tbody>
                          {djobs.slice(0, 10).map(job => {
                            const totalRows = job.row_counts
                              ? Object.values(job.row_counts).reduce((a, b) => a + b, 0)
                              : null
                            const durationMs =
                              job.started_at && job.completed_at
                                ? new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()
                                : null
                            return (
                              <tr key={job.id} className="border-b border-gray-50 dark:border-gray-800/50 last:border-0">
                                <td className="px-4 py-2 font-mono text-gray-700 dark:text-gray-300">{job.export_date}</td>
                                <td className="px-4 py-2">
                                  <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[job.status as ExportJobStatus] || STATUS_BADGE.pending}`}>
                                    {job.status === 'completed' && <CheckCircle className="h-3 w-3" />}
                                    {job.status === 'failed' && <XCircle className="h-3 w-3" />}
                                    {job.status}
                                  </span>
                                </td>
                                <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                                  {totalRows !== null ? totalRows.toLocaleString() : '—'}
                                </td>
                                <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                                  {durationMs !== null ? `${(durationMs / 1000).toFixed(1)}s` : '—'}
                                </td>
                                <td className="px-4 py-2 text-gray-500 dark:text-gray-400 max-w-xs">
                                  {job.file_keys ? (
                                    <div className="space-y-0.5">
                                      {Object.entries(job.file_keys).map(([r, uri]) => (
                                        <div key={r} className="truncate font-mono text-xs" title={uri}>
                                          {r}: …{uri.split('/').slice(-3).join('/')}
                                        </div>
                                      ))}
                                    </div>
                                  ) : job.error ? (
                                    <span className="text-red-500 dark:text-red-400 truncate" title={job.error}>
                                      {job.error.slice(0, 60)}
                                    </span>
                                  ) : '—'}
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Info footer */}
      <div className="rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/40 px-4 py-3">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          <strong className="text-gray-700 dark:text-gray-300">Snowflake external stage:</strong>{' '}
          Point your stage at <code className="font-mono text-xs bg-white dark:bg-gray-900 px-1 rounded">{'{prefix}/{resource}/date={YYYY-MM-DD}/'}</code>.
          Exports run nightly at 02:00 UTC or can be triggered manually.
        </p>
      </div>
    </div>
  )
}
