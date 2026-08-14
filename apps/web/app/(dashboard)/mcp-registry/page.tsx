'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import {
  Activity,
  CheckCircle2,
  Pencil,
  Play,
  Plus,
  Server,
  ShieldCheck,
  Sparkles,
  Terminal,
  Wrench,
  PlugZap,
} from 'lucide-react'
import {
  callMcpTool,
  deleteMcpServer,
  grantMcpPermission,
  listMcpPermissions,
  listMcpServers,
  listMcpToolCalls,
  listMcpTools,
  registerMcpServer,
  revokeMcpPermission,
  seedDefaultMcpServers,
  updateMcpServer,
} from '@/lib/api'
import type {
  McpPermissionResponse,
  McpServerResponse,
  McpToolCallResponse,
  McpToolListItem,
} from '@/types/api'
import McpSetupPanel from '@/components/mcp/McpSetupPanel'

type Tab = 'setup' | 'servers' | 'tools' | 'calls' | 'permissions'

type ServerFormState = {
  name: string
  description: string
  transport: 'stdio' | 'http' | 'sse'
  command: string
  argsStr: string
  url: string
  envJson: string
  authType: string
  authConfigJson: string
}

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

const emptyServerForm: ServerFormState = {
  name: '',
  description: '',
  transport: 'stdio',
  command: '',
  argsStr: '',
  url: '',
  envJson: '{}',
  authType: '',
  authConfigJson: '{}',
}

function formatJson(value: Record<string, unknown> | undefined): string {
  return JSON.stringify(value ?? {}, null, 2)
}

function parseArgs(value: string): string[] {
  return value
    .split(' ')
    .map(item => item.trim())
    .filter(Boolean)
}

function serverToForm(server: McpServerResponse): ServerFormState {
  return {
    name: server.name,
    description: server.description ?? '',
    transport: (server.transport as 'stdio' | 'http' | 'sse') ?? 'stdio',
    command: server.command ?? '',
    argsStr: (server.args ?? []).join(' '),
    url: server.url ?? '',
    envJson: formatJson(server.env as Record<string, unknown>),
    authType: server.auth_type ?? '',
    authConfigJson: '{}',
  }
}

export default function McpRegistryPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string; workspaceId?: string } | null)?.apiKey
  const workspaceId = (session as { workspaceId?: string } | null)?.workspaceId ?? ''
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [tab, setTab] = useState<Tab>('setup')
  const [servers, setServers] = useState<McpServerResponse[]>([])
  const [tools, setTools] = useState<McpToolListItem[]>([])
  const [calls, setCalls] = useState<McpToolCallResponse[]>([])
  const [permissions, setPermissions] = useState<McpPermissionResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [includeInactive, setIncludeInactive] = useState(false)

  const [showServerForm, setShowServerForm] = useState(false)
  const [editingServerId, setEditingServerId] = useState<string | null>(null)
  const [serverForm, setServerForm] = useState<ServerFormState>(emptyServerForm)
  const [savingServer, setSavingServer] = useState(false)
  const [activeServerId, setActiveServerId] = useState<string | null>(null)

  const [testingTool, setTestingTool] = useState<McpToolListItem | null>(null)
  const [toolArgsJson, setToolArgsJson] = useState('{}')
  const [executingTool, setExecutingTool] = useState(false)
  const [toolResult, setToolResult] = useState<unknown>(null)

  const [permServerId, setPermServerId] = useState('')
  const [permScopeType, setPermScopeType] = useState('workspace')
  const [permScopeId, setPermScopeId] = useState('')
  const [permTools, setPermTools] = useState('')

  useEffect(() => {
    if (!permScopeId && workspaceId) {
      setPermScopeId(workspaceId)
    }
  }, [permScopeId, workspaceId])

  useEffect(() => {
    const requested = searchParams.get('tab')
    const nextTab: Tab =
      requested === 'setup' ||
      requested === 'servers' ||
      requested === 'tools' ||
      requested === 'calls' ||
      requested === 'permissions'
        ? requested
        : 'setup'
    setTab(nextTab)
  }, [searchParams])

  const loadData = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      let serverList = await listMcpServers(apiKey, includeInactive).catch(() => ({ items: [] }))
      if ((serverList.items || []).length === 0 && !includeInactive) {
        await seedDefaultMcpServers(apiKey).catch(() => null)
        serverList = await listMcpServers(apiKey, includeInactive).catch(() => ({ items: [] }))
      }
      const [toolList, callList, permissionList] = await Promise.all([
        listMcpTools(apiKey).catch(() => ({ items: [] })),
        listMcpToolCalls(apiKey).catch(() => ({ items: [] })),
        listMcpPermissions(apiKey).catch(() => ({ items: [] })),
      ])
      setServers(serverList.items || [])
      setTools(toolList.items || [])
      setCalls(callList.items || [])
      setPermissions(permissionList.items || [])
      if (!activeServerId && (serverList.items || []).length > 0) {
        setActiveServerId(serverList.items[0].id)
      }
    } catch (err) {
      console.error(err)
      toast.error('Failed to load MCP registry data')
    } finally {
      setLoading(false)
    }
  }, [activeServerId, apiKey, includeInactive])

  useEffect(() => {
    loadData()
  }, [loadData])

  const activeServer = useMemo(
    () => servers.find(server => server.id === activeServerId) ?? servers[0] ?? null,
    [activeServerId, servers]
  )

  function selectTab(nextTab: Tab) {
    const params = new URLSearchParams(searchParams.toString())
    params.set('tab', nextTab)
    router.replace(`${pathname}?${params.toString()}`)
  }

  function updateServerForm<K extends keyof ServerFormState>(key: K, value: ServerFormState[K]) {
    setServerForm(current => ({ ...current, [key]: value }))
  }

  function resetServerForm() {
    setServerForm(emptyServerForm)
    setEditingServerId(null)
    setShowServerForm(false)
  }

  function openCreateServerForm() {
    setEditingServerId(null)
    setServerForm(emptyServerForm)
    setShowServerForm(true)
  }

  function openEditServerForm(server: McpServerResponse) {
    setEditingServerId(server.id)
    setServerForm(serverToForm(server))
    setActiveServerId(server.id)
    setShowServerForm(true)
  }

  async function handleSaveServer(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !serverForm.name.trim()) return
    setSavingServer(true)
    try {
      const env = JSON.parse(serverForm.envJson || '{}') as Record<string, string>
      const authConfig = JSON.parse(serverForm.authConfigJson || '{}') as Record<string, unknown>
      const payload = {
        name: serverForm.name.trim(),
        description: serverForm.description.trim() || undefined,
        transport: serverForm.transport,
        command: serverForm.transport === 'stdio' ? serverForm.command.trim() || undefined : undefined,
        args: serverForm.transport === 'stdio' ? parseArgs(serverForm.argsStr) : [],
        url: serverForm.transport !== 'stdio' ? serverForm.url.trim() || undefined : undefined,
        env: Object.keys(env).length > 0 ? env : undefined,
        auth_type: serverForm.authType.trim() || undefined,
        auth_config: Object.keys(authConfig).length > 0 ? authConfig : undefined,
      }

      if (editingServerId) {
        await updateMcpServer(apiKey, editingServerId, payload)
        toast.success(`Updated ${serverForm.name}`)
      } else {
        await registerMcpServer(apiKey, payload)
        toast.success(`Registered ${serverForm.name}`)
      }
      resetServerForm()
      await loadData()
    } catch {
      toast.error(editingServerId ? 'Failed to update MCP server' : 'Failed to register MCP server')
    } finally {
      setSavingServer(false)
    }
  }

  async function handleToggleActive(server: McpServerResponse, isActive: boolean) {
    if (!apiKey) return
    try {
      if (isActive) {
        await updateMcpServer(apiKey, server.id, { is_active: true })
        toast.success(`Re-activated ${server.name}`)
      } else {
        await deleteMcpServer(apiKey, server.id)
        toast.success(`Deactivated ${server.name}`)
      }
      await loadData()
    } catch {
      toast.error(isActive ? 'Failed to re-activate server' : 'Failed to deactivate server')
    }
  }

  async function handleSeedDefaults() {
    if (!apiKey) return
    try {
      const res = await seedDefaultMcpServers(apiKey)
      toast.success(`Populated ${res.servers_added} default MCP servers`)
      await loadData()
    } catch {
      toast.error('Failed to seed default MCP servers')
    }
  }

  async function handleExecuteToolCall(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !testingTool) return
    setExecutingTool(true)
    setToolResult(null)
    try {
      const parsedArgs = toolArgsJson.trim() ? JSON.parse(toolArgsJson) : {}
      const res = await callMcpTool(apiKey, {
        server_id: testingTool.server_id,
        tool_name: testingTool.tool_name,
        arguments: parsedArgs,
      })
      setToolResult(res)
      toast.success(`Executed ${testingTool.tool_name}`)
      await loadData()
    } catch {
      toast.error('Failed to execute tool call')
    } finally {
      setExecutingTool(false)
    }
  }

  async function handleGrantPermission(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !permServerId || !permScopeId.trim()) return
    try {
      await grantMcpPermission(apiKey, {
        mcp_server_id: permServerId,
        scope_type: permScopeType,
        scope_id: permScopeId.trim(),
        allowed_tools: permTools ? permTools.split(',').map(item => item.trim()).filter(Boolean) : [],
      })
      toast.success('Permission policy created')
      setPermServerId('')
      setPermScopeId(workspaceId)
      setPermTools('')
      await loadData()
    } catch {
      toast.error('Failed to grant permission')
    }
  }

  async function handleRevokePermission(id: string) {
    if (!apiKey) return
    try {
      await revokeMcpPermission(apiKey, id)
      toast.success('Permission policy revoked')
      await loadData()
    } catch {
      toast.error('Failed to revoke permission')
    }
  }

  const tabs: { key: Tab; label: string; icon: typeof Server; count: number }[] = [
    { key: 'setup', label: 'Setup & Connect', icon: PlugZap, count: 0 },
    { key: 'servers', label: 'MCP Servers', icon: Server, count: servers.length },
    { key: 'tools', label: 'Discovered Tools', icon: Wrench, count: tools.length },
    { key: 'calls', label: 'Tool Calls Log', icon: Activity, count: calls.length },
    { key: 'permissions', label: 'Permissions & Policies', icon: ShieldCheck, count: permissions.length },
  ]

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between dark:border-slate-800 dark:bg-slate-900/80">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-blue-700 dark:text-blue-400">
            Agent Control Plane & Tool Registry
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 dark:text-white">
            MCP Registry
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Consolidated setup, server lifecycle management, tool testing, permission policies, and MCP call review.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleSeedDefaults}
            className="flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm font-semibold text-blue-700 transition hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300 dark:hover:bg-blue-900"
          >
            <Sparkles className="h-4 w-4" /> Populate Default Servers
          </button>
          <button
            onClick={openCreateServerForm}
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" /> Register Server
          </button>
        </div>
      </div>

      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800">
        {tabs.map(item => {
          const Icon = item.icon
          const active = tab === item.key
          return (
            <button
              key={item.key}
              onClick={() => selectTab(item.key)}
              className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition ${
                active
                  ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.key === 'setup' ? item.label : `${item.label} (${item.count})`}
            </button>
          )
        })}
      </div>

      {tab === 'setup' && <McpSetupPanel />}

      {tab === 'servers' && (
        <div className="grid gap-6 xl:grid-cols-[1.15fr_1.85fr]">
          <div className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-slate-950 dark:text-white">
                    {editingServerId ? 'Edit Server' : 'Register Server'}
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Manage the canonical server definition behind the workspace MCP surface.
                  </p>
                </div>
                {showServerForm && (
                  <button
                    onClick={resetServerForm}
                    className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                  >
                    Close
                  </button>
                )}
              </div>

              {showServerForm ? (
                <form onSubmit={handleSaveServer} className="mt-4 space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Server name</label>
                      <input
                        value={serverForm.name}
                        onChange={e => updateServerForm('name', e.target.value)}
                        required
                        className={inputCls}
                        placeholder="GitHub MCP Server"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Transport</label>
                      <select
                        value={serverForm.transport}
                        onChange={e => updateServerForm('transport', e.target.value as ServerFormState['transport'])}
                        className={inputCls}
                      >
                        <option value="stdio">stdio</option>
                        <option value="http">http</option>
                        <option value="sse">sse</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Description</label>
                    <textarea
                      value={serverForm.description}
                      onChange={e => updateServerForm('description', e.target.value)}
                      rows={3}
                      className={inputCls}
                      placeholder="Describe the server, its trust boundary, and typical use."
                    />
                  </div>

                  {serverForm.transport === 'stdio' ? (
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Command</label>
                        <input
                          value={serverForm.command}
                          onChange={e => updateServerForm('command', e.target.value)}
                          className={inputCls}
                          placeholder="npx"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Args</label>
                        <input
                          value={serverForm.argsStr}
                          onChange={e => updateServerForm('argsStr', e.target.value)}
                          className={inputCls}
                          placeholder="-y @modelcontextprotocol/server-github"
                        />
                      </div>
                    </div>
                  ) : (
                    <div>
                      <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Endpoint URL</label>
                      <input
                        value={serverForm.url}
                        onChange={e => updateServerForm('url', e.target.value)}
                        className={inputCls}
                        placeholder="https://mcp.internal.company.com/http"
                      />
                    </div>
                  )}

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Env JSON</label>
                      <textarea
                        value={serverForm.envJson}
                        onChange={e => updateServerForm('envJson', e.target.value)}
                        rows={5}
                        className={`${inputCls} font-mono text-xs`}
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Auth config JSON</label>
                      <textarea
                        value={serverForm.authConfigJson}
                        onChange={e => updateServerForm('authConfigJson', e.target.value)}
                        rows={5}
                        className={`${inputCls} font-mono text-xs`}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Auth type</label>
                    <input
                      value={serverForm.authType}
                      onChange={e => updateServerForm('authType', e.target.value)}
                      className={inputCls}
                      placeholder="bearer, basic, oauth"
                    />
                  </div>

                  <div className="flex justify-end gap-3">
                    {editingServerId && (
                      <button
                        type="button"
                        onClick={openCreateServerForm}
                        className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                      >
                        New server
                      </button>
                    )}
                    <button
                      type="submit"
                      disabled={savingServer}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      {savingServer ? 'Saving…' : editingServerId ? 'Save changes' : 'Register server'}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="mt-4 rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500 dark:border-slate-700">
                  Use <span className="font-semibold text-slate-700 dark:text-slate-200">Register Server</span> to add a new MCP
                  endpoint, or pick an existing server and choose <span className="font-semibold text-slate-700 dark:text-slate-200">Edit</span>.
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-slate-950 dark:text-white">Server Inventory</h2>
                  <p className="mt-1 text-sm text-slate-500">Review active and inactive MCP servers for this workspace.</p>
                </div>
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={includeInactive}
                    onChange={e => setIncludeInactive(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  Show inactive
                </label>
              </div>

              <div className="mt-4 space-y-3">
                {servers.map(server => (
                  <button
                    key={server.id}
                    onClick={() => setActiveServerId(server.id)}
                    className={`w-full rounded-2xl border p-4 text-left transition ${
                      activeServerId === server.id
                        ? 'border-blue-300 bg-blue-50 ring-2 ring-blue-100 dark:border-blue-700 dark:bg-blue-950/40'
                        : 'border-slate-200 bg-slate-50/70 hover:border-blue-200 hover:bg-white dark:border-slate-800 dark:bg-slate-950/40 dark:hover:bg-slate-950'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-950 dark:text-white">{server.name}</p>
                        <p className="mt-1 text-xs text-slate-500">
                          {server.transport.toUpperCase()} · tools {server.tool_count} · resources {server.resource_count} · prompts {server.prompt_count}
                        </p>
                      </div>
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          server.is_active
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                            : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300'
                        }`}
                      >
                        {server.is_active ? server.health_status || 'active' : 'inactive'}
                      </span>
                    </div>
                  </button>
                ))}

                {servers.length === 0 && !loading && (
                  <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700">
                    No MCP servers registered yet.
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {activeServer ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-950 dark:text-white">
                      <Server className="h-5 w-5 text-blue-600" /> {activeServer.name}
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">{activeServer.description || 'No description recorded yet.'}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => openEditServerForm(activeServer)}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                    >
                      <Pencil className="h-4 w-4" /> Edit
                    </button>
                    <button
                      onClick={() => handleToggleActive(activeServer, !activeServer.is_active)}
                      className="inline-flex items-center gap-2 rounded-lg border border-blue-200 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50 dark:border-blue-900 dark:text-blue-300 dark:hover:bg-blue-950"
                    >
                      {activeServer.is_active ? 'Deactivate' : 'Re-activate'}
                    </button>
                  </div>
                </div>

                <div className="mt-5 grid gap-4 md:grid-cols-3">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/70">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Transport</p>
                    <p className="mt-2 font-semibold text-slate-950 dark:text-white">{activeServer.transport.toUpperCase()}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/70">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Health</p>
                    <p className="mt-2 font-semibold text-slate-950 dark:text-white">{activeServer.health_status || 'unknown'}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/70">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Auth</p>
                    <p className="mt-2 font-semibold text-slate-950 dark:text-white">{activeServer.auth_type || 'none'}</p>
                  </div>
                </div>

                {activeServer.command && (
                  <div className="mt-5">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Command</p>
                    <div className="rounded-xl bg-slate-950 p-3 font-mono text-xs text-slate-200">
                      {activeServer.command} {(activeServer.args || []).join(' ')}
                    </div>
                  </div>
                )}

                {activeServer.url && (
                  <div className="mt-5">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Endpoint</p>
                    <div className="rounded-xl bg-slate-50 p-3 font-mono text-xs text-blue-700 dark:bg-slate-950 dark:text-blue-300">
                      {activeServer.url}
                    </div>
                  </div>
                )}

                <div className="mt-5 grid gap-4 lg:grid-cols-3">
                  <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
                    <p className="mb-2 text-sm font-semibold text-slate-950 dark:text-white">Discovered tools</p>
                    <div className="space-y-2">
                      {(activeServer.discovered_tools || []).length > 0 ? (
                        activeServer.discovered_tools.map(tool => (
                          <div key={String(tool.name)} className="rounded-xl bg-slate-50 p-3 text-xs dark:bg-slate-950">
                            <p className="font-semibold text-slate-900 dark:text-white">{String(tool.name || 'tool')}</p>
                            <p className="mt-1 text-slate-500">{String(tool.description || 'No description')}</p>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-slate-500">No discovered tools recorded.</p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
                    <p className="mb-2 text-sm font-semibold text-slate-950 dark:text-white">Resources</p>
                    <div className="space-y-2">
                      {(activeServer.discovered_resources || []).length > 0 ? (
                        activeServer.discovered_resources.map((resource, index) => (
                          <div key={`${activeServer.id}-resource-${index}`} className="rounded-xl bg-slate-50 p-3 text-xs dark:bg-slate-950">
                            <p className="font-semibold text-slate-900 dark:text-white">{String(resource.name || resource.uri || 'resource')}</p>
                            <p className="mt-1 text-slate-500">{String(resource.description || resource.uri || 'No description')}</p>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-slate-500">No discovered resources recorded.</p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
                    <p className="mb-2 text-sm font-semibold text-slate-950 dark:text-white">Prompts</p>
                    <div className="space-y-2">
                      {(activeServer.discovered_prompts || []).length > 0 ? (
                        activeServer.discovered_prompts.map((prompt, index) => (
                          <div key={`${activeServer.id}-prompt-${index}`} className="rounded-xl bg-slate-50 p-3 text-xs dark:bg-slate-950">
                            <p className="font-semibold text-slate-900 dark:text-white">{String(prompt.name || 'prompt')}</p>
                            <p className="mt-1 text-slate-500">{String(prompt.description || 'No description')}</p>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-slate-500">No discovered prompts recorded.</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">
                Select a server to inspect its lifecycle details.
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'tools' && (
        <div className="space-y-4">
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/80 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-950/50">
                <tr>
                  <th className="px-4 py-3 text-left">Tool name</th>
                  <th className="px-4 py-3 text-left">Server</th>
                  <th className="px-4 py-3 text-left">Description</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {tools.map(tool => (
                  <tr key={`${tool.server_id}-${tool.tool_name}`} className="hover:bg-slate-50 dark:hover:bg-slate-950/40">
                    <td className="flex items-center gap-2 px-4 py-3 font-semibold text-slate-900 dark:text-white">
                      <Wrench className="h-4 w-4 text-blue-600" /> {tool.tool_name}
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-slate-500">{tool.server_name || tool.server_id.slice(0, 8)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-300">{tool.description || 'No description provided'}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => {
                          setTestingTool(tool)
                          setToolArgsJson('{}')
                          setToolResult(null)
                        }}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400"
                      >
                        <Play className="h-3 w-3" /> Test call
                      </button>
                    </td>
                  </tr>
                ))}
                {tools.length === 0 && !loading && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-400">No MCP tools discovered yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {testingTool && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm">
              <div className="w-full max-w-xl space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
                <h3 className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
                  <Play className="h-4 w-4 text-blue-600" /> Test tool: {testingTool.tool_name}
                </h3>
                <p className="text-xs text-slate-500">
                  Execute this tool through the RunLedger MCP control plane and record the resulting governance trail.
                </p>
                <form onSubmit={handleExecuteToolCall} className="space-y-4">
                  <textarea
                    value={toolArgsJson}
                    onChange={e => setToolArgsJson(e.target.value)}
                    rows={8}
                    className={`${inputCls} font-mono text-xs`}
                  />
                  <div className="flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => setTestingTool(null)}
                      className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                    >
                      Close
                    </button>
                    <button
                      type="submit"
                      disabled={executingTool}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      {executingTool ? 'Executing…' : 'Execute'}
                    </button>
                  </div>
                </form>
                {toolResult != null && (
                  <pre className="max-h-80 overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">
                    {JSON.stringify(toolResult, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'calls' && (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50/80 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-950/50">
              <tr>
                <th className="px-4 py-3 text-left">Tool</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Latency</th>
                <th className="px-4 py-3 text-left">Created</th>
                <th className="px-4 py-3 text-left">Arguments</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {calls.map(call => (
                <tr key={call.id} className="hover:bg-slate-50 dark:hover:bg-slate-950/40">
                  <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">{call.tool_name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        call.status === 'success'
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                          : 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                      }`}
                    >
                      {call.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{call.latency_ms ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500">{new Date(call.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <pre className="max-w-xl overflow-auto rounded-lg bg-slate-950 p-2 text-xs text-slate-100">
                      {JSON.stringify(call.arguments, null, 2)}
                    </pre>
                  </td>
                </tr>
              ))}
              {calls.length === 0 && !loading && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400">No MCP tool calls recorded yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'permissions' && (
        <div className="grid gap-6 xl:grid-cols-[1fr_1.4fr]">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900 dark:text-white">
              <ShieldCheck className="h-4 w-4 text-blue-600" /> Grant policy
            </h2>
            <form onSubmit={handleGrantPermission} className="mt-4 space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Server</label>
                <select value={permServerId} onChange={e => setPermServerId(e.target.value)} className={inputCls}>
                  <option value="">Select server</option>
                  {servers.filter(server => server.is_active).map(server => (
                    <option key={server.id} value={server.id}>
                      {server.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Scope type</label>
                <select value={permScopeType} onChange={e => setPermScopeType(e.target.value)} className={inputCls}>
                  <option value="workspace">workspace</option>
                  <option value="access_group">access_group</option>
                  <option value="user">user</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Scope id</label>
                <input
                  value={permScopeId}
                  onChange={e => setPermScopeId(e.target.value)}
                  className={inputCls}
                  placeholder="Workspace, access group, or user id"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Allowed tools</label>
                <input
                  value={permTools}
                  onChange={e => setPermTools(e.target.value)}
                  className={inputCls}
                  placeholder="tool_a, tool_b, tool_c"
                />
              </div>
              <button
                type="submit"
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
              >
                Create policy
              </button>
            </form>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Existing policies</h2>
            <div className="mt-4 space-y-3">
              {permissions.map(permission => (
                <div key={permission.id} className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="font-semibold text-slate-950 dark:text-white">
                        {servers.find(server => server.id === permission.mcp_server_id)?.name || permission.mcp_server_id}
                      </p>
                      <p className="text-xs text-slate-500">
                        {permission.scope_type} · {permission.scope_id}
                      </p>
                      <p className="text-xs text-slate-600 dark:text-slate-300">
                        {(permission.allowed_tools || []).length > 0
                          ? permission.allowed_tools.join(', ')
                          : 'All tools allowed'}
                      </p>
                    </div>
                    <button
                      onClick={() => handleRevokePermission(permission.id)}
                      className="text-xs font-medium text-red-500 hover:text-red-700"
                    >
                      Revoke
                    </button>
                  </div>
                </div>
              ))}
              {permissions.length === 0 && !loading && <p className="text-sm text-slate-500">No permission policies yet.</p>}
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <CheckCircle2 className="h-4 w-4 animate-pulse text-blue-600" /> Loading MCP registry data…
        </div>
      )}
    </div>
  )
}
