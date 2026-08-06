'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  listPlugins,
  createPlugin,
  deletePlugin,
  listPluginExecutions,
} from '@/lib/api'
import type { PluginResponse, PluginExecutionResponse } from '@/types/api'

export default function PluginsPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey

  const [plugins, setPlugins] = useState<PluginResponse[]>([])
  const [executions, setExecutions] = useState<PluginExecutionResponse[]>([])
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [name, setName] = useState('')
  const [pluginType, setPluginType] = useState('webhook')
  const [hooks, setHooks] = useState('')
  const [priority, setPriority] = useState(100)

  async function load() {
    if (!apiKey) return
    setLoading(true)
    try {
      const res = await listPlugins(apiKey)
      setPlugins(res.items)
    } catch {
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [apiKey])

  async function loadExecutions(pluginId: string) {
    if (!apiKey) return
    setSelectedPlugin(pluginId)
    const res = await listPluginExecutions(apiKey, pluginId)
    setExecutions(res.items)
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !name) return
    await createPlugin(apiKey, {
      name,
      plugin_type: pluginType,
      hooks: hooks ? hooks.split(',').map(h => h.trim()) : [],
      priority,
    })
    setName('')
    setHooks('')
    load()
  }

  async function handleDelete(id: string) {
    if (!apiKey) return
    await deletePlugin(apiKey, id)
    if (selectedPlugin === id) setSelectedPlugin(null)
    load()
  }

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Plugins</h1>
      <p className="text-sm text-slate-500">Install and manage custom plugins that hook into RunLedger lifecycle events.</p>

      <form onSubmit={handleCreate} className="flex flex-wrap gap-3 items-end rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Name</label>
          <input value={name} onChange={e => setName(e.target.value)} required className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Type</label>
          <select value={pluginType} onChange={e => setPluginType(e.target.value)} className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white">
            <option value="webhook">Webhook</option>
            <option value="transformer">Transformer</option>
            <option value="validator">Validator</option>
            <option value="enricher">Enricher</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Hooks (comma-sep)</label>
          <input value={hooks} onChange={e => setHooks(e.target.value)} placeholder="pre_ingest, post_ingest" className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Priority</label>
          <input type="number" value={priority} onChange={e => setPriority(Number(e.target.value))} className="w-20 rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
        </div>
        <button type="submit" className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">Install Plugin</button>
      </form>

      {loading && <p className="text-sm text-slate-400">Loading...</p>}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {plugins.map(p => (
          <div key={p.id} className={`rounded-lg border p-4 transition ${selectedPlugin === p.id ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-900/10' : 'border-slate-200 bg-white dark:border-white/10 dark:bg-white/5'}`}>
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white">{p.name}</h3>
                <p className="mt-0.5 text-xs text-slate-500">{p.plugin_type} &middot; v{p.version || '0.0.1'}</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${p.is_active ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-100 text-slate-500 dark:bg-white/10'}`}>
                {p.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            {p.description && <p className="mt-2 text-sm text-slate-500">{p.description}</p>}
            <div className="mt-3 flex flex-wrap gap-1">
              {p.hooks.map(h => (
                <span key={h} className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-white/10 dark:text-slate-300">{h}</span>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
              <span>Priority: {p.priority}</span>
              <span>{p.author || 'Unknown author'}</span>
            </div>
            <div className="mt-3 flex gap-2">
              <button onClick={() => loadExecutions(p.id)} className="text-xs text-indigo-500 hover:text-indigo-700">Executions</button>
              <button onClick={() => handleDelete(p.id)} className="text-xs text-red-500 hover:text-red-700">Uninstall</button>
            </div>
          </div>
        ))}
        {plugins.length === 0 && !loading && <p className="col-span-full text-center text-slate-400 py-8">No plugins installed.</p>}
      </div>

      {selectedPlugin && (
        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            Execution Log — {plugins.find(p => p.id === selectedPlugin)?.name}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-200 text-left text-xs font-medium uppercase text-slate-500 dark:border-white/10">
                <th className="py-2 pr-4">Hook</th><th className="py-2 pr-4">Status</th><th className="py-2 pr-4">Latency</th><th className="py-2">Time</th>
              </tr></thead>
              <tbody>
                {executions.map(ex => (
                  <tr key={ex.id} className="border-b border-slate-100 dark:border-white/5">
                    <td className="py-2 pr-4 font-mono text-slate-900 dark:text-white">{ex.hook}</td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${ex.status === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                        {ex.status}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-slate-500">{ex.latency_ms != null ? `${ex.latency_ms}ms` : '—'}</td>
                    <td className="py-2 text-slate-500">{new Date(ex.created_at).toLocaleString()}</td>
                  </tr>
                ))}
                {executions.length === 0 && <tr><td colSpan={4} className="py-4 text-center text-slate-400">No executions recorded.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
