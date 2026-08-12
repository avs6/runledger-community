'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  Server,
  Wrench,
  Activity,
  ShieldCheck,
  Plus,
  Trash2,
  Play,
  RefreshCw,
  Sparkles,
  CheckCircle2,
  XCircle,
  Clock,
  Terminal,
} from 'lucide-react'
import {
  listMcpServers,
  registerMcpServer,
  deleteMcpServer,
  seedDefaultMcpServers,
  listMcpTools,
  callMcpTool,
  listMcpToolCalls,
  listMcpPermissions,
  grantMcpPermission,
  revokeMcpPermission,
  listProjects,
} from '@/lib/api'
import type {
  McpServerResponse,
  McpToolListItem,
  McpToolCallResponse,
  McpPermissionResponse,
  ProjectResponse,
} from '@/types/api'

type Tab = 'servers' | 'tools' | 'calls' | 'permissions'

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

export default function McpRegistryPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey
  const [tab, setTab] = useState<Tab>('servers')

  const [servers, setServers] = useState<McpServerResponse[]>([])
  const [tools, setTools] = useState<McpToolListItem[]>([])
  const [calls, setCalls] = useState<McpToolCallResponse[]>([])
  const [permissions, setPermissions] = useState<McpPermissionResponse[]>([])
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [loading, setLoading] = useState(true)

  // Server Registration State
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [transport, setTransport] = useState<'stdio' | 'http' | 'sse'>('stdio')
  const [command, setCommand] = useState('')
  const [argsStr, setArgsStr] = useState('')
  const [url, setUrl] = useState('')

  // Tool Testing Modal State
  const [testingTool, setTestingTool] = useState<McpToolListItem | null>(null)
  const [toolArgsJson, setToolArgsJson] = useState('{}')
  const [executingTool, setExecutingTool] = useState(false)
  const [toolResult, setToolResult] = useState<any>(null)

  // Permission Grant Form State
  const [permServerId, setPermServerId] = useState('')
  const [permScopeType, setPermScopeType] = useState('workspace')
  const [permScopeId, setPermScopeId] = useState('')
  const [permTools, setPermTools] = useState('')

  const loadData = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      let s = await listMcpServers(apiKey).catch(() => ({ items: [], total: 0 }))
      if ((s.items || []).length === 0) {
        await seedDefaultMcpServers(apiKey).catch(() => null)
        s = await listMcpServers(apiKey).catch(() => ({ items: [], total: 0 }))
      }
      const [t, c, p, projRes] = await Promise.all([
        listMcpTools(apiKey).catch(() => ({ items: [], total: 0 })),
        listMcpToolCalls(apiKey).catch(() => ({ items: [], total: 0 })),
        listMcpPermissions(apiKey).catch(() => ({ items: [], total: 0 })),
        listProjects(apiKey).catch(() => ({ items: [] })),
      ])
      setServers(s.items || [])
      setTools(t.items || [])
      setCalls(c.items || [])
      setPermissions(p.items || [])
      setProjects(projRes.items || [])
    } catch (err) {
      console.error(err)
      toast.error('Failed to load MCP registry data')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !name.trim()) return
    try {
      await registerMcpServer(apiKey, {
        name: name.trim(),
        description: description.trim() || undefined,
        transport,
        url: transport !== 'stdio' ? url.trim() : undefined,
        command: transport === 'stdio' ? command.trim() : undefined,
        args: argsStr ? argsStr.split(' ').map((a) => a.trim()) : [],
      })
      toast.success(`MCP Server '${name}' registered`)
      setName('')
      setDescription('')
      setCommand('')
      setArgsStr('')
      setUrl('')
      loadData()
    } catch (err) {
      toast.error('Failed to register MCP server')
    }
  }

  async function handleSeedDefaults() {
    if (!apiKey) return
    try {
      const res = await seedDefaultMcpServers(apiKey)
      toast.success(`Populated ${res.servers_added} default popular MCP servers!`)
      loadData()
    } catch (err) {
      toast.error('Failed to seed default MCP servers')
    }
  }

  async function handleDelete(id: string) {
    if (!apiKey) return
    try {
      await deleteMcpServer(apiKey, id)
      toast.success('MCP server deactivated')
      loadData()
    } catch (err) {
      toast.error('Failed to deactivate server')
    }
  }

  async function handleExecuteToolCall(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !testingTool) return
    setExecutingTool(true)
    setToolResult(null)
    try {
      let parsedArgs = {}
      if (toolArgsJson.trim()) {
        parsedArgs = JSON.parse(toolArgsJson)
      }
      const res = await callMcpTool(apiKey, {
        server_id: testingTool.server_id,
        tool_name: testingTool.tool_name,
        arguments: parsedArgs,
      })
      setToolResult(res)
      toast.success(`Tool '${testingTool.tool_name}' executed successfully`)
      loadData()
    } catch (err) {
      toast.error('Failed to execute tool call')
    } finally {
      setExecutingTool(false)
    }
  }

  async function handleGrantPermission(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !permServerId) return
    try {
      await grantMcpPermission(apiKey, {
        mcp_server_id: permServerId,
        scope_type: permScopeType,
        scope_id: permScopeId.trim() || undefined,
        allowed_tools: permTools ? permTools.split(',').map((t) => t.trim()) : [],
      })
      toast.success('Permission policy created')
      setPermServerId('')
      setPermScopeId('')
      setPermTools('')
      loadData()
    } catch (err) {
      toast.error('Failed to grant permission')
    }
  }

  async function handleRevokePermission(id: string) {
    if (!apiKey) return
    try {
      await revokeMcpPermission(apiKey, id)
      toast.success('Permission policy revoked')
      loadData()
    } catch (err) {
      toast.error('Failed to revoke permission')
    }
  }

  const tabs: { key: Tab; label: string; icon: any; count: number }[] = [
    { key: 'servers', label: 'MCP Servers', icon: Server, count: servers.length },
    { key: 'tools', label: 'Discovered Tools', icon: Wrench, count: tools.length },
    { key: 'calls', label: 'Tool Calls Log', icon: Activity, count: calls.length },
    { key: 'permissions', label: 'Permissions & Policies', icon: ShieldCheck, count: permissions.length },
  ]

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between dark:border-slate-800 dark:bg-slate-900/80">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-blue-700 dark:text-blue-400">
            Agent Control Plane & Tool Registry
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 dark:text-white">
            MCP Server Registry & Governance
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Register Model Context Protocol servers, manage tool capabilities, inspect execution logs, and grant granular policies.
          </p>
        </div>

        <button
          onClick={handleSeedDefaults}
          className="flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300 dark:hover:bg-blue-900 transition"
        >
          <Sparkles className="h-4 w-4" /> Populate Popular MCP Servers
        </button>
      </div>

      {/* Tabs Header */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800">
        {tabs.map((t) => {
          const Icon = t.icon
          const active = tab === t.key
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 -mb-px transition ${
                active
                  ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <Icon className="h-4 w-4" />
              {t.label} ({t.count})
            </button>
          )
        })}
      </div>

      {/* TAB 1: SERVERS */}
      {tab === 'servers' && (
        <div className="space-y-6">
          <form
            onSubmit={handleRegister}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4"
          >
            <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Plus className="h-4 w-4 text-blue-600" /> Register Custom MCP Server
            </h2>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Server Name *
                </label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  placeholder="e.g., GitHub MCP Server"
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Transport Type
                </label>
                <select
                  value={transport}
                  onChange={(e) => setTransport(e.target.value as any)}
                  className={inputCls}
                >
                  <option value="stdio">stdio (Local Subprocess / npx)</option>
                  <option value="http">HTTP / REST MCP Server</option>
                  <option value="sse">SSE (Server-Sent Events)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Description
                </label>
                <input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Server capabilities..."
                  className={inputCls}
                />
              </div>
            </div>

            {transport === 'stdio' ? (
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Command (e.g. npx, python, node)
                  </label>
                  <input
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    placeholder="npx"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Command Arguments (space-separated)
                  </label>
                  <input
                    value={argsStr}
                    onChange={(e) => setArgsStr(e.target.value)}
                    placeholder="-y @modelcontextprotocol/server-github"
                    className={inputCls}
                  />
                </div>
              </div>
            ) : (
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Endpoint URL *
                </label>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://mcp.internal.company.com/sse"
                  className={inputCls}
                />
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition"
              >
                Register MCP Server
              </button>
            </div>
          </form>

          {/* Servers Grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {servers.map((s) => (
              <div
                key={s.id}
                className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-bold text-slate-950 dark:text-white flex items-center gap-2">
                        <Server className="h-4 w-4 text-blue-600" /> {s.name}
                      </h3>
                      <p className="text-xs font-mono text-slate-400 mt-0.5">{s.transport.toUpperCase()}</p>
                    </div>
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        s.is_active
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                          : 'bg-slate-100 text-slate-500 dark:bg-slate-800'
                      }`}
                    >
                      {s.is_active ? 'Healthy' : 'Inactive'}
                    </span>
                  </div>

                  {s.description && (
                    <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                      {s.description}
                    </p>
                  )}

                  {s.command && (
                    <div className="mt-3 rounded-lg bg-slate-950 p-2 font-mono text-[11px] text-slate-200 flex items-center gap-1.5 overflow-x-auto">
                      <Terminal className="h-3 w-3 text-blue-400 shrink-0" />
                      <span>
                        {s.command} {(s.args || []).join(' ')}
                      </span>
                    </div>
                  )}

                  {s.url && (
                    <div className="mt-3 font-mono text-xs text-blue-600 truncate">{s.url}</div>
                  )}

                  <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
                    <Wrench className="h-3.5 w-3.5 text-slate-400" />
                    <span>{(s.discovered_tools || []).length} Discovered Tools</span>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-800">
                  <span className="text-[11px] text-slate-400">ID: {s.id.slice(0, 8)}...</span>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="text-xs font-medium text-red-500 hover:text-red-700"
                  >
                    Deactivate
                  </button>
                </div>
              </div>
            ))}
            {servers.length === 0 && !loading && (
              <div className="col-span-full py-12 text-center text-slate-400">
                No MCP servers registered yet. Click &quot;Populate Popular MCP Servers&quot; above to seed default tools.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: DISCOVERED TOOLS */}
      {tab === 'tools' && (
        <div className="space-y-4">
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <table className="w-full text-sm">
              <thead className="bg-slate-50/80 dark:bg-slate-950/50 text-xs uppercase tracking-wider text-slate-500 font-semibold border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4 text-left">Tool Name</th>
                  <th className="py-3 px-4 text-left">Server ID / Source</th>
                  <th className="py-3 px-4 text-left">Description</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {tools.map((t) => (
                  <tr key={`${t.server_id}-${t.tool_name}`} className="hover:bg-slate-50 dark:hover:bg-slate-950/40">
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                      <Wrench className="h-4 w-4 text-blue-600" /> {t.tool_name}
                    </td>
                    <td className="py-3 px-4 text-xs font-mono text-slate-500">
                      {t.server_name || t.server_id.slice(0, 8)}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-600 dark:text-slate-300">
                      {t.description || 'No description provided'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => {
                          setTestingTool(t)
                          setToolArgsJson('{}')
                          setToolResult(null)
                        }}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400"
                      >
                        <Play className="h-3 w-3" /> Test Call
                      </button>
                    </td>
                  </tr>
                ))}
                {tools.length === 0 && !loading && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-400">
                      No MCP tools discovered yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Test Tool Call Modal */}
          {testingTool && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm">
              <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Play className="h-4 w-4 text-blue-600" /> Test Execute Tool: {testingTool.tool_name}
                </h3>
                <p className="text-xs text-slate-500">
                  Execute this tool through RunLedger MCP Gateway with governance monitoring and cost telemetry.
                </p>

                <form onSubmit={handleExecuteToolCall} className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Arguments (JSON format)
                    </label>
                    <textarea
                      value={toolArgsJson}
                      onChange={(e) => setToolArgsJson(e.target.value)}
                      rows={4}
                      className="font-mono text-xs w-full rounded-xl border border-slate-300 bg-slate-950 p-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => setTestingTool(null)}
                      className="rounded-lg px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                    >
                      Close
                    </button>
                    <button
                      type="submit"
                      disabled={executingTool}
                      className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
                    >
                      {executingTool ? 'Executing...' : 'Run Tool'}
                    </button>
                  </div>
                </form>

                {toolResult && (
                  <div className="rounded-xl border border-slate-200 bg-slate-950 p-4 font-mono text-xs text-slate-200 space-y-2 max-h-48 overflow-y-auto">
                    <div className="text-emerald-400 font-semibold flex items-center gap-1.5">
                      <CheckCircle2 className="h-4 w-4" /> Execution Success ({toolResult.status})
                    </div>
                    <pre>{JSON.stringify(toolResult, null, 2)}</pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: TOOL CALLS LOG */}
      {tab === 'calls' && (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <table className="w-full text-sm">
            <thead className="bg-slate-50/80 dark:bg-slate-950/50 text-xs uppercase tracking-wider text-slate-500 font-semibold border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-3 px-4 text-left">Tool Name</th>
                <th className="py-3 px-4 text-left">Arguments</th>
                <th className="py-3 px-4 text-left">Latency</th>
                <th className="py-3 px-4 text-left">Status</th>
                <th className="py-3 px-4 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {calls.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50 dark:hover:bg-slate-950/40">
                  <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                    <Wrench className="h-4 w-4 text-blue-600" /> {c.tool_name}
                  </td>
                  <td className="py-3 px-4 font-mono text-xs text-slate-500 max-w-xs truncate">
                    {JSON.stringify(c.arguments || {})}
                  </td>
                  <td className="py-3 px-4 font-mono text-xs text-slate-600 dark:text-slate-300">
                    {c.latency_ms ? `${c.latency_ms}ms` : '—'}
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-block rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                      {c.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-xs text-slate-400 font-mono">
                    {new Date(c.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
              {calls.length === 0 && !loading && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400">
                    No MCP tool call logs recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 4: PERMISSIONS & POLICIES */}
      {tab === 'permissions' && (
        <div className="space-y-6">
          <form
            onSubmit={handleGrantPermission}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4"
          >
            <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-blue-600" /> Grant Tool Permission Policy
            </h2>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Target MCP Server *
                </label>
                <select
                  value={permServerId}
                  onChange={(e) => setPermServerId(e.target.value)}
                  required
                  className={inputCls}
                >
                  <option value="">-- Select MCP Server --</option>
                  {servers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Scope Type
                </label>
                <select
                  value={permScopeType}
                  onChange={(e) => setPermScopeType(e.target.value)}
                  className={inputCls}
                >
                  <option value="workspace">Workspace (All Keys)</option>
                  <option value="project">Project Workload</option>
                  <option value="api_key">Specific API Key</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Target Project / Key ID (Optional)
                </label>
                {permScopeType === 'project' && projects.length > 0 ? (
                  <select
                    value={permScopeId}
                    onChange={(e) => setPermScopeId(e.target.value)}
                    className={inputCls}
                  >
                    <option value="">-- Select Project --</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    value={permScopeId}
                    onChange={(e) => setPermScopeId(e.target.value)}
                    placeholder="Project / Key UUID..."
                    className={inputCls}
                  />
                )}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Allowed Tools (comma-separated, leave blank for all)
              </label>
              <input
                value={permTools}
                onChange={(e) => setPermTools(e.target.value)}
                placeholder="query, list_tables, brave_web_search"
                className={inputCls}
              />
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={!permServerId}
                className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 transition"
              >
                Grant Permission Policy
              </button>
            </div>
          </form>

          {/* Permissions Table */}
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <table className="w-full text-sm">
              <thead className="bg-slate-50/80 dark:bg-slate-950/50 text-xs uppercase tracking-wider text-slate-500 font-semibold border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4 text-left">Server ID</th>
                  <th className="py-3 px-4 text-left">Scope</th>
                  <th className="py-3 px-4 text-left">Allowed Tools</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {permissions.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-950/40">
                    <td className="py-3 px-4 font-mono text-xs text-slate-900 dark:text-white">
                      {p.mcp_server_id.slice(0, 8)}...
                    </td>
                    <td className="py-3 px-4 text-xs font-semibold text-slate-700 dark:text-slate-300">
                      {p.scope_type} {p.scope_id ? `(${p.scope_id.slice(0, 8)})` : ''}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-600 dark:text-slate-400">
                      {(p.allowed_tools || []).length === 0
                        ? 'All Tools (Unrestricted)'
                        : p.allowed_tools.join(', ')}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleRevokePermission(p.id)}
                        className="text-xs text-red-500 hover:text-red-700 font-medium"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
                {permissions.length === 0 && !loading && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-400">
                      No permission policies configured yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
