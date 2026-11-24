'use client'

import Link from 'next/link'
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
  discoverMcpServer,
  getToolPolicies,
  listMcpServers,
  listMcpToolCalls,
  listMcpTools,
  registerMcpServer,
  resumeMcpToolCall,
  seedDefaultMcpServers,
  updateMcpServer,
} from '@/lib/api'
import type {
  McpServerResponse,
  McpToolCallResponse,
  McpToolListItem,
  ToolPolicyResponse,
} from '@/types/api'
import McpSetupPanel from '@/components/mcp/McpSetupPanel'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'

type Tab = 'setup' | 'servers' | 'tools' | 'calls' | 'policies'

const CALL_STATUSES = ['success', 'error', 'blocked', 'pending_approval', 'denied', 'not_executed'] as const

function callStatusClass(status: string): string {
  if (status === 'success') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
  if (status === 'blocked' || status === 'error' || status === 'denied') return 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300'
  return 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
}

/** A ToolPolicy that targets one MCP server (scope or condition). */
function policyServerId(p: ToolPolicyResponse): string | null {
  if (p.scope_type === 'mcp_server' && p.scope_id) return p.scope_id
  const cfg = (p.condition_config ?? {}) as Record<string, unknown>
  if (p.condition_type === 'mcp_server' && typeof cfg.server_id === 'string') return cfg.server_id
  return null
}

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
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [tab, setTab] = useState<Tab>('setup')
  const [servers, setServers] = useState<McpServerResponse[]>([])
  const [tools, setTools] = useState<McpToolListItem[]>([])
  const [calls, setCalls] = useState<McpToolCallResponse[]>([])
  const [serverPolicies, setServerPolicies] = useState<ToolPolicyResponse[]>([])
  const { confirm, dialog } = useConfirm()
  const statusFilter = searchParams.get('status') ?? ''
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

  useEffect(() => {
    const requested = searchParams.get('tab')
    const nextTab: Tab =
      requested === 'setup' ||
      requested === 'servers' ||
      requested === 'tools' ||
      requested === 'calls' ||
      requested === 'policies'
        ? requested
        : 'setup'
    setTab(nextTab)
  }, [searchParams])

  const loadData = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      // No auto-seeding: "Populate Default Servers" is an explicit, confirmed action.
      const [serverList, toolList, callList, policyList] = await Promise.all([
        listMcpServers(apiKey, includeInactive),
        listMcpTools(apiKey),
        listMcpToolCalls(apiKey, { limit: 200, status: statusFilter || undefined }),
        getToolPolicies(apiKey),
      ])
      setServers(serverList.items || [])
      setTools(toolList.items || [])
      setCalls(callList.items || [])
      setServerPolicies((policyList.items || []).filter(p => policyServerId(p) !== null))
      if (!activeServerId && (serverList.items || []).length > 0) {
        setActiveServerId(serverList.items[0].id)
      }
    } catch (err) {
      console.error(err)
      toast.error('Failed to load MCP registry data')
    } finally {
      setLoading(false)
    }
  }, [activeServerId, apiKey, includeInactive, statusFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  const activeServer = useMemo(
    () => servers.find(server => server.id === activeServerId) ?? servers[0] ?? null,
    [activeServerId, servers]
  )

  function selectTab(nextTab: Tab) {
    setParam('tab', nextTab)
  }

  function setParam(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString())
    if (value) params.set(key, value)
    else params.delete(key)
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
      if (!isActive) {
        const ok = await confirm({
          title: `Deactivate ${server.name}?`,
          description: 'Governed calls to this server will be refused until it is re-activated.',
          confirmLabel: 'Deactivate',
          destructive: true,
        })
        if (!ok) return
      }
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
    const ok = await confirm({
      title: 'Add the default MCP server catalog?',
      description: 'Adds GitHub, Postgres, Brave Search, Puppeteer and FileSystem stdio definitions that are not registered yet. They run on the agent machine; use Discover on HTTP servers to check real health.',
      confirmLabel: 'Add servers',
    })
    if (!ok) return
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
      // Report the real outcome, never a blanket "Executed" (review S-26).
      if (res.status === 'success') toast.success(`${testingTool.tool_name} ran in ${res.latency_ms ?? 0} ms`)
      else if (res.status === 'pending_approval') toast.info(`Held for approval ${res.approval_id ?? ''}`.trim())
      else toast.error(`${testingTool.tool_name}: ${res.status}${res.error ? ` — ${res.error}` : ''}`)
      await loadData()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to call tool'
      toast.error(message.includes('403') ? `Blocked by tool policy: ${message.replace(/^API 403: /, '')}` : message)
    } finally {
      setExecutingTool(false)
    }
  }

  async function handleDiscover(server: McpServerResponse) {
    if (!apiKey) return
    try {
      const res = await discoverMcpServer(apiKey, server.id)
      if (res.health_status === 'healthy') toast.success(`${server.name}: ${res.tool_count} tools discovered`)
      else toast.warning(`${server.name}: ${res.health_status}${res.error ? ` — ${res.error}` : ''}`)
      await loadData()
    } catch {
      toast.error('Discovery failed')
    }
  }

  async function handleResume(call: McpToolCallResponse) {
    if (!apiKey) return
    try {
      const res = await resumeMcpToolCall(apiKey, call.id)
      if (res.status === 'success') toast.success(`${call.tool_name} ran after approval`)
      else toast.warning(`${call.tool_name}: ${res.status}${res.error ? ` — ${res.error}` : ''}`)
      await loadData()
    } catch (err) {
      toast.error(err instanceof Error && err.message.includes('409') ? 'The approval is still pending' : 'Resume failed')
    }
  }

  const callColumns: DataTableColumn<McpToolCallResponse>[] = [
    { key: 'tool_name', header: 'Tool', sortable: true, render: c => <span className="font-semibold text-slate-900 dark:text-white">{c.tool_name}</span> },
    {
      key: 'mcp_server_id',
      header: 'Server',
      value: c => servers.find(s => s.id === c.mcp_server_id)?.name ?? c.mcp_server_id,
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: c => <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${callStatusClass(c.status)}`}>{c.status}</span>,
    },
    { key: 'policy_name', header: 'Policy', value: c => c.policy_name ?? '—' },
    { key: 'latency_ms', header: 'Latency (ms)', sortable: true, value: c => c.latency_ms ?? null },
    { key: 'created_at', header: 'Created', sortable: true, value: c => c.created_at, render: c => new Date(c.created_at).toLocaleString() },
    { key: 'error', header: 'Error', defaultHidden: true, value: c => c.error ?? '' },
    {
      key: 'actions',
      header: '',
      render: c =>
        c.status === 'pending_approval' ? (
          <div className="flex items-center gap-2">
            <Link href={`/approvals?status=pending`} className="text-xs text-blue-600 hover:underline">Approval</Link>
            <button type="button" onClick={() => void handleResume(c)} aria-label={`Resume held call to ${c.tool_name}`}
              className="rounded-md border border-blue-200 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-50 dark:border-blue-900 dark:text-blue-300">
              Resume
            </button>
          </div>
        ) : null,
    },
  ]

  const tabs: { key: Tab; label: string; icon: typeof Server; count: number }[] = [
    { key: 'setup', label: 'Setup & Connect', icon: PlugZap, count: 0 },
    { key: 'servers', label: 'MCP Servers', icon: Server, count: servers.length },
    { key: 'tools', label: 'Discovered Tools', icon: Wrench, count: tools.length },
    { key: 'calls', label: 'Tool Calls Log', icon: Activity, count: calls.length },
    { key: 'policies', label: 'Tool Policies', icon: ShieldCheck, count: serverPolicies.length },
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
          <div className="flex flex-wrap gap-2 mt-2">
            <Link href="/gateway" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Gateway</Link>
            <Link href="/provider-profiles" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Provider Profiles</Link>
            <Link href="/guardrails" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Guardrails</Link>
            <Link href="/runs" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Runs</Link>
            <Link href="/analytics" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Analytics</Link>
            <Link href="/request-flow" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Flow</Link>
            <Link href="/request-explorer" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Explorer</Link>
            <Link href="/approvals" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Approvals</Link>
            <Link href="/audit" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Audit Log</Link>
            <Link href="/governance-pack" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Governance Pack</Link>
            <Link href="/chargeback" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Chargeback</Link>
            <Link href="/agents" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Agents</Link>
            <Link href="/workflows" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Workflows</Link>
            <Link href="/evaluation" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Evaluation Studio</Link>
          </div>
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
                      onClick={() => void handleDiscover(activeServer)}
                      disabled={!activeServer.is_active}
                      aria-label={`Discover tools and check health of ${activeServer.name}`}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                    >
                      <Activity className="h-4 w-4" /> Discover
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
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="mcp-call-status" className="text-xs font-medium text-slate-600 dark:text-slate-300">Status</label>
            <select id="mcp-call-status" aria-label="Filter tool calls by status" value={statusFilter}
              onChange={e => setParam('status', e.target.value)} className={`${inputCls} w-48`}>
              <option value="">All</option>
              {CALL_STATUSES.map(st => <option key={st} value={st}>{st}</option>)}
            </select>
          </div>
          <DataTable
            label="MCP tool calls"
            urlPrefix="calls"
            rows={calls}
            columns={callColumns}
            rowKey={c => c.id}
            csvFileName="mcp-tool-calls.csv"
            emptyTitle="No MCP tool calls yet"
            emptyDescription="Governed calls made through POST /mcp-registry/tools/call appear here with their policy decision."
          />
        </div>
      )}

      {tab === 'policies' && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
            Per-server permissions are tool policies scoped to an MCP server. The same evaluator enforces them on
            governed MCP calls, <code>/tools/check</code>, <code>/policies/check</code> and the gateway. To allow-list a
            server, add <em>allow</em> rules for its tools and a lower-priority <em>block *</em> scoped to the server.
            <div className="mt-3">
              <Link href={`/tool-registry?tab=policies`} className="font-medium text-blue-600 hover:underline">Manage tool policies</Link>
            </div>
          </div>
          {servers.map(server => {
            const rows = serverPolicies.filter(p => policyServerId(p) === server.id)
            if (rows.length === 0) return null
            return (
              <div key={server.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">{server.name}</h2>
                <ul className="mt-3 divide-y divide-slate-100 dark:divide-slate-800">
                  {rows.map(p => (
                    <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                      <span className="font-medium text-slate-800 dark:text-slate-100">{p.name}</span>
                      <span className="text-xs text-slate-500">{p.tool_name} · {p.action} · priority {p.priority} · {p.scope_type}{p.scope_id ? `:${p.scope_id.slice(0, 8)}` : ''}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
          {serverPolicies.length === 0 && !loading && (
            <p className="text-sm text-slate-500">No tool policies target an MCP server yet.</p>
          )}
        </div>
      )}

      {dialog}
      {loading && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <CheckCircle2 className="h-4 w-4 animate-pulse text-blue-600" /> Loading MCP registry data…
        </div>
      )}
    </div>
  )
}
