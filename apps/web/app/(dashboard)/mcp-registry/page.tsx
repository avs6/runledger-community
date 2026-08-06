'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  listMcpServers,
  registerMcpServer,
  deleteMcpServer,
  listMcpTools,
  listMcpToolCalls,
  listMcpPermissions,
  grantMcpPermission,
  revokeMcpPermission,
} from '@/lib/api'
import type {
  McpServerResponse,
  McpToolListItem,
  McpToolCallResponse,
  McpPermissionResponse,
} from '@/types/api'

type Tab = 'servers' | 'tools' | 'calls' | 'permissions'

export default function McpRegistryPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey
  const [tab, setTab] = useState<Tab>('servers')

  const [servers, setServers] = useState<McpServerResponse[]>([])
  const [tools, setTools] = useState<McpToolListItem[]>([])
  const [calls, setCalls] = useState<McpToolCallResponse[]>([])
  const [permissions, setPermissions] = useState<McpPermissionResponse[]>([])
  const [loading, setLoading] = useState(true)

  const [name, setName] = useState('')
  const [transport, setTransport] = useState('http')
  const [url, setUrl] = useState('')

  const [permServerId, setPermServerId] = useState('')
  const [permScopeType, setPermScopeType] = useState('workspace')
  const [permScopeId, setPermScopeId] = useState('')
  const [permTools, setPermTools] = useState('')

  async function load() {
    if (!apiKey) return
    setLoading(true)
    try {
      const [s, t, c, p] = await Promise.all([
        listMcpServers(apiKey),
        listMcpTools(apiKey),
        listMcpToolCalls(apiKey),
        listMcpPermissions(apiKey),
      ])
      setServers(s.items)
      setTools(t.items)
      setCalls(c.items)
      setPermissions(p.items)
    } catch {
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [apiKey])

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !name) return
    await registerMcpServer(apiKey, { name, transport, url: url || undefined })
    setName('')
    setUrl('')
    load()
  }

  async function handleDelete(id: string) {
    if (!apiKey) return
    await deleteMcpServer(apiKey, id)
    load()
  }

  async function handleGrantPermission(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !permServerId) return
    await grantMcpPermission(apiKey, {
      mcp_server_id: permServerId,
      scope_type: permScopeType,
      scope_id: permScopeId,
      allowed_tools: permTools ? permTools.split(',').map(t => t.trim()) : [],
    })
    setPermServerId('')
    setPermScopeId('')
    setPermTools('')
    load()
  }

  async function handleRevokePermission(id: string) {
    if (!apiKey) return
    await revokeMcpPermission(apiKey, id)
    load()
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'servers', label: `Servers (${servers.length})` },
    { key: 'tools', label: `Tools (${tools.length})` },
    { key: 'calls', label: `Tool Calls (${calls.length})` },
    { key: 'permissions', label: `Permissions (${permissions.length})` },
  ]

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">MCP Server Registry</h1>
      <p className="text-sm text-slate-500">Register, discover, and manage MCP servers and their tools across your workspace.</p>

      <div className="flex gap-2 border-b border-slate-200 dark:border-white/10">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${tab === t.key ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400' : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading && <p className="text-sm text-slate-400">Loading...</p>}

      {tab === 'servers' && (
        <div className="space-y-4">
          <form onSubmit={handleRegister} className="flex flex-wrap gap-3 items-end rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Name</label>
              <input value={name} onChange={e => setName(e.target.value)} required className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Transport</label>
              <select value={transport} onChange={e => setTransport(e.target.value)} className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white">
                <option value="http">HTTP</option>
                <option value="stdio">Stdio</option>
                <option value="sse">SSE</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">URL</label>
              <input value={url} onChange={e => setUrl(e.target.value)} placeholder="http://..." className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <button type="submit" className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">Register</button>
          </form>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-200 text-left text-xs font-medium uppercase text-slate-500 dark:border-white/10">
                <th className="py-2 pr-4">Name</th><th className="py-2 pr-4">Transport</th><th className="py-2 pr-4">Health</th>
                <th className="py-2 pr-4">Tools</th><th className="py-2 pr-4">Resources</th><th className="py-2">Actions</th>
              </tr></thead>
              <tbody>
                {servers.map(s => (
                  <tr key={s.id} className="border-b border-slate-100 dark:border-white/5">
                    <td className="py-2 pr-4 font-medium text-slate-900 dark:text-white">{s.name}</td>
                    <td className="py-2 pr-4 text-slate-500">{s.transport}</td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${s.health_status === 'healthy' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'}`}>
                        {s.health_status}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-slate-500">{s.tool_count}</td>
                    <td className="py-2 pr-4 text-slate-500">{s.resource_count}</td>
                    <td className="py-2">
                      <button onClick={() => handleDelete(s.id)} className="text-xs text-red-500 hover:text-red-700">Deactivate</button>
                    </td>
                  </tr>
                ))}
                {servers.length === 0 && !loading && <tr><td colSpan={6} className="py-8 text-center text-slate-400">No MCP servers registered.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'tools' && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-slate-200 text-left text-xs font-medium uppercase text-slate-500 dark:border-white/10">
              <th className="py-2 pr-4">Tool</th><th className="py-2 pr-4">Server</th><th className="py-2">Description</th>
            </tr></thead>
            <tbody>
              {tools.map((t, i) => (
                <tr key={i} className="border-b border-slate-100 dark:border-white/5">
                  <td className="py-2 pr-4 font-mono text-sm text-slate-900 dark:text-white">{t.tool_name}</td>
                  <td className="py-2 pr-4 text-slate-500">{t.server_name}</td>
                  <td className="py-2 text-slate-500">{t.description || '—'}</td>
                </tr>
              ))}
              {tools.length === 0 && !loading && <tr><td colSpan={3} className="py-8 text-center text-slate-400">No tools discovered yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'calls' && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-slate-200 text-left text-xs font-medium uppercase text-slate-500 dark:border-white/10">
              <th className="py-2 pr-4">Tool</th><th className="py-2 pr-4">Status</th><th className="py-2 pr-4">Latency</th>
              <th className="py-2 pr-4">Cost</th><th className="py-2">Time</th>
            </tr></thead>
            <tbody>
              {calls.map(c => (
                <tr key={c.id} className="border-b border-slate-100 dark:border-white/5">
                  <td className="py-2 pr-4 font-mono text-sm text-slate-900 dark:text-white">{c.tool_name}</td>
                  <td className="py-2 pr-4">
                    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${c.status === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-slate-500">{c.latency_ms != null ? `${c.latency_ms}ms` : '—'}</td>
                  <td className="py-2 pr-4 text-slate-500">{c.cost_usd != null ? `$${c.cost_usd.toFixed(4)}` : '—'}</td>
                  <td className="py-2 text-slate-500">{new Date(c.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {calls.length === 0 && !loading && <tr><td colSpan={5} className="py-8 text-center text-slate-400">No tool calls recorded.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'permissions' && (
        <div className="space-y-4">
          <form onSubmit={handleGrantPermission} className="flex flex-wrap gap-3 items-end rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Server</label>
              <select value={permServerId} onChange={e => setPermServerId(e.target.value)} required className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white">
                <option value="">Select server</option>
                {servers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Scope Type</label>
              <select value={permScopeType} onChange={e => setPermScopeType(e.target.value)} className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white">
                <option value="workspace">Workspace</option>
                <option value="team">Team</option>
                <option value="user">User</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Scope ID</label>
              <input value={permScopeId} onChange={e => setPermScopeId(e.target.value)} placeholder="UUID" className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Allowed Tools (comma-sep)</label>
              <input value={permTools} onChange={e => setPermTools(e.target.value)} placeholder="tool1, tool2" className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <button type="submit" className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">Grant</button>
          </form>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-200 text-left text-xs font-medium uppercase text-slate-500 dark:border-white/10">
                <th className="py-2 pr-4">Server</th><th className="py-2 pr-4">Scope</th><th className="py-2 pr-4">Allowed Tools</th><th className="py-2">Actions</th>
              </tr></thead>
              <tbody>
                {permissions.map(p => (
                  <tr key={p.id} className="border-b border-slate-100 dark:border-white/5">
                    <td className="py-2 pr-4 text-slate-900 dark:text-white">{servers.find(s => s.id === p.mcp_server_id)?.name || p.mcp_server_id.slice(0, 8)}</td>
                    <td className="py-2 pr-4 text-slate-500">{p.scope_type}: {p.scope_id.slice(0, 8)}</td>
                    <td className="py-2 pr-4 text-slate-500">{p.allowed_tools.length > 0 ? p.allowed_tools.join(', ') : 'All'}</td>
                    <td className="py-2"><button onClick={() => handleRevokePermission(p.id)} className="text-xs text-red-500 hover:text-red-700">Revoke</button></td>
                  </tr>
                ))}
                {permissions.length === 0 && !loading && <tr><td colSpan={4} className="py-8 text-center text-slate-400">No permissions configured.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
