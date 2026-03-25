'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { listEvalDatasets, createEvalDataset, deleteEvalDataset } from '@/lib/api'
import type { EvalDataset, DatasetItem } from '@/types/api'
import { toast } from 'sonner'
import { Plus, Trash2, X, TableProperties } from 'lucide-react'

const inputCls =
  'w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

export default function DatasetsPage() {
  const { data: session } = useSession()
  const [datasets, setDatasets] = useState<EvalDataset[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<EvalDataset | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  // Form
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [itemsText, setItemsText] = useState('')
  const [creating, setCreating] = useState(false)
  const [inputMode, setInputMode] = useState<'paste' | 'upload' | 'url'>('paste')
  const [urlInput, setUrlInput] = useState('')
  const [fetching, setFetching] = useState(false)

  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  async function load() {
    if (!apiKey) return
    setLoading(true)
    try {
      const res = await listEvalDatasets(apiKey)
      setDatasets(res.items)
    } catch {
      toast.error('Failed to load datasets')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (apiKey) load() }, [apiKey])

  function parseItems(text: string): DatasetItem[] {
    // Support CSV (input,expected_output) or JSON array
    const trimmed = text.trim()
    if (trimmed.startsWith('[')) {
      try {
        return JSON.parse(trimmed) as DatasetItem[]
      } catch {
        throw new Error('Invalid JSON array')
      }
    }
    // CSV: first row = headers or data
    const lines = trimmed.split('\n').filter(Boolean)
    return lines.map(line => {
      const parts = line.split(',')
      return {
        input: parts[0]?.trim() ?? '',
        expected_output: parts[1]?.trim() || null,
        metadata: {},
      }
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

  async function handleCreate() {
    if (!name.trim()) { toast.error('Name is required'); return }
    setCreating(true)
    try {
      const items = itemsText.trim() ? parseItems(itemsText) : []
      const ds = await createEvalDataset(apiKey, {
        name: name.trim(),
        description: description.trim() || undefined,
        items,
      })
      setDatasets(prev => [ds, ...prev])
      setShowCreate(false)
      setName(''); setDescription(''); setItemsText(''); setUrlInput(''); setInputMode('paste')
      toast.success('Dataset created')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Create failed')
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this dataset?')) return
    try {
      await deleteEvalDataset(apiKey, id)
      setDatasets(prev => prev.filter(d => d.id !== id))
      if (selected?.id === id) setSelected(null)
      toast.success('Deleted')
    } catch {
      toast.error('Delete failed')
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <TableProperties className="h-6 w-6 text-indigo-500" />
            Datasets
          </h1>
          <p className="mt-1 text-sm text-gray-500">Manage test case collections for evaluation experiments.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" /> New Dataset
        </button>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-xl bg-white dark:bg-gray-900 p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">New Dataset</h2>
              <button onClick={() => setShowCreate(false)}><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Name *</label>
                <input className={inputCls} value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Customer Q&A" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Description</label>
                <input className={inputCls} value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional" />
              </div>
              <div>
                <div className="flex gap-1 mb-2">
                  {(['paste', 'upload', 'url'] as const).map(mode => (
                    <button key={mode} type="button" onClick={() => setInputMode(mode)}
                      className={`rounded px-3 py-1 text-xs font-medium capitalize ${inputMode === mode ? 'bg-indigo-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}`}>
                      {mode === 'paste' ? 'Paste' : mode === 'upload' ? 'Upload File' : 'From URL'}
                    </button>
                  ))}
                </div>
                {inputMode === 'paste' && (
                  <>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Items (CSV: input,expected_output — or JSON array)
                    </label>
                    <textarea
                      className={`${inputCls} h-32 resize-none font-mono`}
                      value={itemsText}
                      onChange={e => setItemsText(e.target.value)}
                      placeholder={'What is 2+2?,4\nCapital of France?,Paris'}
                    />
                  </>
                )}
                {inputMode === 'upload' && (
                  <>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Upload CSV or JSON file</label>
                    <input type="file" accept=".csv,.json,.txt" onChange={handleFileUpload}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:rounded file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-indigo-700 hover:file:bg-indigo-100 dark:file:bg-indigo-900/30 dark:file:text-indigo-400" />
                    {itemsText && <p className="mt-1 text-xs text-green-600 dark:text-green-400">✓ File loaded — switch to Paste to review</p>}
                  </>
                )}
                {inputMode === 'url' && (
                  <>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">File URL (HTTP/HTTPS or GitHub raw URL)</label>
                    <div className="flex gap-2">
                      <input value={urlInput} onChange={e => setUrlInput(e.target.value)}
                        className={inputCls} placeholder="https://raw.githubusercontent.com/..." />
                      <button type="button" onClick={handleFetchUrl} disabled={fetching}
                        className="shrink-0 rounded border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50">
                        {fetching ? 'Fetching…' : 'Fetch'}
                      </button>
                    </div>
                    {itemsText && <p className="mt-1 text-xs text-green-600 dark:text-green-400">✓ Content loaded — switch to Paste to review</p>}
                  </>
                )}
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => setShowCreate(false)} className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 py-2 text-sm text-gray-600 dark:text-gray-300">Cancel</button>
              <button onClick={handleCreate} disabled={creating} className="flex-1 rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {creating ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* List */}
        <div className="lg:col-span-1 space-y-2">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />
            ))
          ) : datasets.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-600 p-8 text-center">
              <TableProperties className="mx-auto h-8 w-8 text-gray-300 dark:text-gray-600" />
              <p className="mt-2 text-sm text-gray-500">No datasets yet</p>
            </div>
          ) : (
            datasets.map(ds => (
              <div
                key={ds.id}
                onClick={() => setSelected(ds)}
                className={`cursor-pointer rounded-xl border p-4 hover:border-indigo-500 transition-colors ${
                  selected?.id === ds.id
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/30'
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900'
                }`}
              >
                <div className="flex items-center justify-between">
                  <p className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">{ds.name}</p>
                  <button
                    onClick={e => { e.stopPropagation(); handleDelete(ds.id) }}
                    className="text-red-400 hover:text-red-600 ml-2"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                {ds.description && <p className="text-xs text-gray-500 mt-0.5 truncate">{ds.description}</p>}
                <p className="text-xs text-indigo-500 mt-1">{ds.item_count} items</p>
              </div>
            ))
          )}
        </div>

        {/* Detail */}
        <div className="lg:col-span-2">
          {selected ? (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{selected.name}</h2>
                {selected.description && <p className="text-sm text-gray-500 mt-0.5">{selected.description}</p>}
                <div className="mt-2 flex gap-4 text-xs text-gray-400">
                  <span>{selected.item_count} items</span>
                  <span>Source: {selected.source}</span>
                  <span>Created {new Date(selected.created_at).toLocaleDateString()}</span>
                </div>
              </div>

              {selected.items.length > 0 && (
                <div className="overflow-auto max-h-96">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-white dark:bg-gray-900">
                      <tr className="border-b border-gray-200 dark:border-gray-700 text-xs text-gray-400">
                        <th className="text-left py-2 pr-4">#</th>
                        <th className="text-left py-2 pr-4">Input</th>
                        <th className="text-left py-2">Expected Output</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.items.map((item, i) => (
                        <tr key={i} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                          <td className="py-2 pr-4 text-gray-400">{i + 1}</td>
                          <td className="py-2 pr-4 text-gray-900 dark:text-gray-100">{item.input}</td>
                          <td className="py-2 text-gray-500">{item.expected_output ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-600 p-12 flex flex-col items-center justify-center text-center">
              <TableProperties className="h-10 w-10 text-gray-200 dark:text-gray-700" />
              <p className="mt-3 text-sm text-gray-400">Select a dataset to view items</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
