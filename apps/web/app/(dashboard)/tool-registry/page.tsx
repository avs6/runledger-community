'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Wrench, Plus, Trash2, RefreshCw, ShieldCheck, Search, Pencil, X, DollarSign, Building2, Radio, Link2, Layers } from 'lucide-react'
import {
  createSearchTool,
  deleteSearchTool,
  deleteToolRegistry,
  getGovernanceInternalPosture,
  getSearchTools,
  getToolGovernanceGatewayPosture,
  getToolGovernanceOrgPosture,
  getToolRegistryFinopsPosture,
  getToolRegistryRuntimePosture,
  listToolRegistry,
  updateSearchTool,
  updateToolRegistry,
  upsertToolRegistry,
} from '@/lib/api'
import type { SearchToolResponse, ToolRegistryResponse, ToolRegistryFinopsPosture, ToolGovernanceOrgPosture, ToolGovernanceGatewayPosture, GovernanceInternalPosture, ToolRegistryRuntimePosture } from '@/types/api'

const inputCls =
  'rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500'

type Tab = 'registry' | 'search'

function parseTab(value: string | null): Tab {
  return value === 'search' ? 'search' : 'registry'
}

export default function ToolRegistryPage() {
  const { data: session } = useSession()
  const searchParams = useSearchParams()
  const router = useRouter()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const [tab, setTab] = useState<Tab>(parseTab(searchParams.get('tab')))

  const [tools, setTools] = useState<ToolRegistryResponse[]>([])
  const [searchTools, setSearchTools] = useState<SearchToolResponse[]>([])
  const [finopsPosture, setFinopsPosture] = useState<ToolRegistryFinopsPosture | null>(null)
  const [orgPosture, setOrgPosture] = useState<ToolGovernanceOrgPosture | null>(null)
  const [gatewayPosture, setGatewayPosture] = useState<ToolGovernanceGatewayPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<ToolRegistryRuntimePosture | null>(null)
  const [loading, setLoading] = useState(true)

  const [showRegistryForm, setShowRegistryForm] = useState(false)
  const [showSearchForm, setShowSearchForm] = useState(false)
  const [editingToolName, setEditingToolName] = useState<string | null>(null)
  const [editingSearchId, setEditingSearchId] = useState<string | null>(null)

  const [registryForm, setRegistryForm] = useState({
    tool_name: '',
    policy: 'audit',
    runtime_enforcement: false,
    description: '',
  })
  const [searchForm, setSearchForm] = useState({
    name: '',
    description: '',
    tool_type: 'web_search',
    endpoint_url: '',
    auth_type: '',
    rate_limit_rpm: '',
    cost_per_query: '0',
    is_active: true,
  })
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [registry, providers, posture, orgP, gwP, govI, rtP] = await Promise.all([
        listToolRegistry(apiKey),
        getSearchTools(apiKey, { include_inactive: true }),
        getToolRegistryFinopsPosture(apiKey).catch(() => null),
        getToolGovernanceOrgPosture(apiKey).catch(() => null),
        getToolGovernanceGatewayPosture(apiKey).catch(() => null),
        getGovernanceInternalPosture(apiKey).catch(() => null),
        getToolRegistryRuntimePosture(apiKey).catch(() => null),
      ])
      setTools(registry.items)
      setSearchTools(providers.items)
      setFinopsPosture(posture)
      setOrgPosture(orgP)
      setGatewayPosture(gwP)
      setGovInternal(govI)
      setRuntimePosture(rtP)
    } catch {
      toast.error('Failed to load tool governance data')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { void load() }, [load])
  useEffect(() => { setTab(parseTab(searchParams.get('tab'))) }, [searchParams])

  function startEditRegistry(tool: ToolRegistryResponse) {
    setEditingToolName(tool.tool_name)
    setRegistryForm({
      tool_name: tool.tool_name,
      policy: tool.policy,
      runtime_enforcement: tool.runtime_enforcement,
      description: tool.description ?? '',
    })
    setShowRegistryForm(true)
    setTab('registry')
  }

  function startEditSearch(tool: SearchToolResponse) {
    setEditingSearchId(tool.id)
    setSearchForm({
      name: tool.name,
      description: tool.description ?? '',
      tool_type: tool.tool_type,
      endpoint_url: tool.endpoint_url ?? '',
      auth_type: tool.auth_type ?? '',
      rate_limit_rpm: tool.rate_limit_rpm != null ? String(tool.rate_limit_rpm) : '',
      cost_per_query: String(tool.cost_per_query ?? 0),
      is_active: tool.is_active,
    })
    setShowSearchForm(true)
    setTab('search')
  }

  function resetRegistryForm() {
    setEditingToolName(null)
    setRegistryForm({ tool_name: '', policy: 'audit', runtime_enforcement: false, description: '' })
    setShowRegistryForm(false)
  }

  function resetSearchForm() {
    setEditingSearchId(null)
    setSearchForm({
      name: '',
      description: '',
      tool_type: 'web_search',
      endpoint_url: '',
      auth_type: '',
      rate_limit_rpm: '',
      cost_per_query: '0',
      is_active: true,
    })
    setShowSearchForm(false)
  }

  async function handleSaveRegistry(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !registryForm.tool_name.trim()) return
    setSaving(true)
    try {
      if (editingToolName) {
        await updateToolRegistry(apiKey, editingToolName, {
          policy: registryForm.policy,
          runtime_enforcement: registryForm.runtime_enforcement,
          description: registryForm.description.trim() || null,
        })
        toast.success('Tool registry entry updated')
      } else {
        await upsertToolRegistry(apiKey, {
          tool_name: registryForm.tool_name.trim(),
          policy: registryForm.policy,
          runtime_enforcement: registryForm.runtime_enforcement,
          description: registryForm.description.trim() || null,
        })
        toast.success('Tool registered')
      }
      resetRegistryForm()
      await load()
    } catch {
      toast.error('Failed to save tool registry entry')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteRegistry(toolName: string) {
    if (!apiKey || !confirm(`Remove "${toolName}" from the registry?`)) return
    try {
      await deleteToolRegistry(apiKey, toolName)
      toast.success('Tool removed')
      await load()
    } catch {
      toast.error('Failed to remove tool')
    }
  }

  async function handleSaveSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !searchForm.name.trim()) return
    setSaving(true)
    try {
      const payload = {
        name: searchForm.name.trim(),
        description: searchForm.description.trim() || null,
        tool_type: searchForm.tool_type.trim(),
        endpoint_url: searchForm.endpoint_url.trim() || null,
        auth_type: searchForm.auth_type.trim() || null,
        auth_config: {},
        rate_limit_rpm: searchForm.rate_limit_rpm ? Number(searchForm.rate_limit_rpm) : null,
        cost_per_query: Number(searchForm.cost_per_query || '0'),
        is_active: searchForm.is_active,
      }
      if (editingSearchId) {
        await updateSearchTool(apiKey, editingSearchId, payload)
        toast.success('Search provider updated')
      } else {
        await createSearchTool(apiKey, payload)
        toast.success('Search provider created')
      }
      resetSearchForm()
      await load()
    } catch {
      toast.error('Failed to save search provider')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteSearch(toolId: string) {
    if (!apiKey || !confirm('Deactivate this search provider?')) return
    try {
      await deleteSearchTool(apiKey, toolId)
      toast.success('Search provider deactivated')
      await load()
    } catch {
      toast.error('Failed to deactivate search provider')
    }
  }

  const activeRegistry = tools.filter((tool) => tool.runtime_enforcement).length
  const activeSearch = searchTools.filter((tool) => tool.is_active).length

  return (
    <div className="space-y-8 max-w-6xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <Wrench className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            <h1 className="text-2xl font-bold tracking-tight dark:text-white">Tool Registry</h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Manage runtime tool registrations and search providers from one governance surface. Policy simulation and dry-run testing live in{' '}
            <Link href="/tool-policies" className="font-medium text-violet-600 hover:text-violet-700 dark:text-violet-400">
              Tool Policies
            </Link>.
          </p>
        </div>
        <button
          onClick={() => void load()}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Registered Tools</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{tools.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Runtime Enforced</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{activeRegistry}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Search Providers</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{searchTools.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Active Search Providers</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{activeSearch}</p>
        </div>
      </div>

      {finopsPosture && (
        <div className="rounded-2xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/60 dark:bg-emerald-950/40 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-emerald-700 dark:text-emerald-400">FinOps Budget Impact</p>
              <p className="text-lg font-semibold text-slate-900 dark:text-slate-50">Tool Cost Attribution</p>
            </div>
            <Link href="/budgets" className="text-xs font-medium text-emerald-700 hover:text-emerald-800 dark:text-emerald-400 dark:hover:text-emerald-300">
              Manage budgets &rarr;
            </Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border border-emerald-100 dark:border-emerald-900 bg-white dark:bg-slate-900 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Tool Spend (30d)</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">${finopsPosture.spend_context.tool_spend_30d.toFixed(2)}</p>
              <p className="text-xs text-slate-500">{finopsPosture.spend_context.tool_call_count_30d.toLocaleString()} tool calls</p>
            </div>
            <div className="rounded-xl border border-emerald-100 dark:border-emerald-900 bg-white dark:bg-slate-900 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Total Spend (30d)</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">${finopsPosture.spend_context.total_spend_30d.toFixed(2)}</p>
              <p className="text-xs text-slate-500">{finopsPosture.spend_context.total_spend_30d > 0 ? ((finopsPosture.spend_context.tool_spend_30d / finopsPosture.spend_context.total_spend_30d) * 100).toFixed(1) : '0.0'}% from tools</p>
            </div>
            <div className="rounded-xl border border-emerald-100 dark:border-emerald-900 bg-white dark:bg-slate-900 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Active Budgets</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">{finopsPosture.budget_context.total_budgets}</p>
              <p className="text-xs text-slate-500">{finopsPosture.budget_context.tool_scoped_budgets} tool-scoped</p>
            </div>
            <div className="rounded-xl border border-emerald-100 dark:border-emerald-900 bg-white dark:bg-slate-900 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Chargeback Rules</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">{finopsPosture.chargeback_context.chargeback_rules}</p>
              <p className="text-xs text-slate-500">{finopsPosture.chargeback_context.tool_dimension_rules} tool-dimension</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link href="/budgets" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?view=detail" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Budget Detail</Link>
            <Link href="/chargeback?dimension=feature_tag" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Chargeback by Tool</Link>
            <Link href="/ledger" className="text-xs text-emerald-700 hover:underline dark:text-emerald-400">Ledger</Link>
          </div>
        </div>
      )}

      {orgPosture && (
        <div className="rounded-2xl border border-blue-200 dark:border-blue-800 bg-blue-50/60 dark:bg-blue-950/40 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-100">Org &amp; Access Scope</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Workspace Users</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.user_context.total_users}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Access Groups</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.access_group_context.total_groups}</p>
              <p className="text-xs text-slate-500">{orgPosture.access_group_context.tool_policy_groups} with tool policies</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Active API Keys</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.api_key_context.total_keys}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">MCP Servers</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.mcp_context.active_servers}</p>
              <p className="text-xs text-slate-500">{orgPosture.mcp_context.total_servers} total</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/organization" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Organization</Link>
            <Link href="/users" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Users</Link>
            <Link href="/workspaces" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Workspaces</Link>
            <Link href="/access-groups" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Access Groups</Link>
            <Link href="/api-keys" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">API Keys</Link>
            <Link href="/mcp-registry" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">MCP Registry</Link>
          </div>
        </div>
      )}

      {gatewayPosture && (
        <div className="rounded-2xl border border-violet-200 dark:border-violet-800 bg-violet-50/60 dark:bg-violet-950/40 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Radio className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            <h2 className="text-lg font-semibold text-violet-900 dark:text-violet-100">Gateway &amp; Observe Runtime</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Gateway Routes</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.provider_context.total_routes}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.provider_context.total_providers} providers</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Guardrails</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.guardrail_context.total_guardrails}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.guardrail_context.guardrail_events_30d} events (30d)</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Tool Calls (30d)</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.run_context.tool_runs_30d.toLocaleString()}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.run_context.total_runs_30d.toLocaleString()} total runs</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Alert Firings (30d)</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.monitoring_context.alert_firings_30d}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.monitoring_context.total_alert_rules} active rules</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/gateway" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Gateway</Link>
            <Link href="/guardrails" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Guardrails</Link>
            <Link href="/runs" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Runs</Link>
            <Link href="/request-explorer" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Request Explorer</Link>
            <Link href="/monitoring" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Monitoring</Link>
          </div>
        </div>
      )}

      {govInternal && (
        <div className="rounded-2xl border border-rose-200 dark:border-rose-800 bg-rose-50/60 dark:bg-rose-950/30 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-rose-600 dark:text-rose-400" />
            <h2 className="text-lg font-semibold text-rose-900 dark:text-rose-100">Governance Cohesion</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Pending Approvals</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.approvals_context.pending_approvals}</p>
              <p className="text-xs text-slate-500">{govInternal.approvals_context.total_approvals_30d} total (30d)</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Security Events (30d)</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.security_context.security_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Audit Events (30d)</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.audit_context.audit_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Active Tags</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.tags_context.active_tags}</p>
              <p className="text-xs text-slate-500">{govInternal.tags_context.total_tags} total</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/tool-policies" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Policies</Link>
            <Link href="/approvals" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Approvals</Link>
            <Link href="/data-capture" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Data Capture</Link>
            <Link href="/security" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Security</Link>
            <Link href="/alert-rules" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Alert Rules</Link>
            <Link href="/audit" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Audit Log</Link>
            <Link href="/governance-pack" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Governance Pack</Link>
            <Link href="/tags" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tags</Link>
          </div>
        </div>
      )}

      {runtimePosture && (
        <div className="rounded-2xl border border-cyan-200 dark:border-cyan-800 bg-cyan-50/60 dark:bg-cyan-950/30 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
            <h2 className="text-lg font-semibold text-cyan-900 dark:text-cyan-100">Runtime Scope &amp; Evidence</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">API Keys w/ Tool Calls</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.api_key_scope.keys_with_tool_calls_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.api_key_scope.active_keys} active keys</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Model Routes</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.gateway_runtime.model_routes}</p>
              <p className="text-xs text-slate-500">{runtimePosture.gateway_runtime.rate_limited_routes} rate-limited</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Tool Requests (30d)</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.observe_evidence.tool_requests_30d.toLocaleString()}</p>
              <p className="text-xs text-slate-500">{runtimePosture.observe_evidence.tool_runs_30d.toLocaleString()} tagged runs</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Budget Notifications (30d)</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.budget_linkage.budget_notifications_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.budget_linkage.tool_scoped_budgets} tool-scoped budgets</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/workspaces" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Workspaces</Link>
            <Link href="/api-keys" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">API Keys</Link>
            <Link href="/mcp-registry" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">MCP Registry</Link>
            <Link href="/gateway" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Model Gateway</Link>
            <Link href="/gateway?tab=cache" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Response Cache</Link>
            <Link href="/gateway?tab=rate-limits" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Rate Limits</Link>
            <Link href="/runs" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Run Detail</Link>
            <Link href="/request-explorer" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Request Flow</Link>
            <Link href="/budgets" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Budgets</Link>
            <Link href="/budgets?view=detail" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Budget Detail</Link>
          </div>
        </div>
      )}

      <div className="flex gap-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-1">
        {([
          { id: 'registry' as Tab, label: 'Runtime Registry', icon: Wrench },
          { id: 'search' as Tab, label: 'Search Providers', icon: Search },
        ]).map((item) => (
          <button
            key={item.id}
            onClick={() => {
              setTab(item.id)
              router.replace(`/tool-registry?tab=${item.id}`)
            }}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              tab === item.id
                ? 'bg-white dark:bg-slate-900 text-violet-700 dark:text-violet-300 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'registry' && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button
              onClick={() => {
                if (showRegistryForm && !editingToolName) resetRegistryForm()
                else setShowRegistryForm(true)
              }}
              className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
            >
              {showRegistryForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              {showRegistryForm && !editingToolName ? 'Cancel' : editingToolName ? 'Editing Tool' : 'Register Tool'}
            </button>
          </div>

          {showRegistryForm && (
            <form onSubmit={handleSaveRegistry} className="rounded-xl border border-violet-200 dark:border-violet-800 bg-violet-50/50 dark:bg-violet-900/10 p-5 space-y-4">
              <h3 className="text-sm font-semibold text-violet-800 dark:text-violet-300">
                {editingToolName ? `Edit ${editingToolName}` : 'Register a runtime tool'}
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-500">Tool name *</label>
                  <input
                    value={registryForm.tool_name}
                    onChange={(e) => setRegistryForm((prev) => ({ ...prev, tool_name: e.target.value }))}
                    className={inputCls}
                    disabled={Boolean(editingToolName)}
                    required
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-500">Policy</label>
                  <select
                    value={registryForm.policy}
                    onChange={(e) => setRegistryForm((prev) => ({ ...prev, policy: e.target.value }))}
                    className={inputCls}
                  >
                    <option value="audit">audit</option>
                    <option value="allow">allow</option>
                    <option value="block">block</option>
                  </select>
                </div>
                <div className="md:col-span-2 flex flex-col gap-1">
                  <label className="text-xs text-slate-500">Description</label>
                  <input
                    value={registryForm.description}
                    onChange={(e) => setRegistryForm((prev) => ({ ...prev, description: e.target.value }))}
                    className={inputCls}
                    placeholder="What this tool does and why it is governed"
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={registryForm.runtime_enforcement}
                  onChange={(e) => setRegistryForm((prev) => ({ ...prev, runtime_enforcement: e.target.checked }))}
                />
                Enable live runtime enforcement
              </label>
              <div className="flex gap-2">
                <button type="submit" disabled={saving} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50">
                  {saving ? 'Saving...' : editingToolName ? 'Save Changes' : 'Register Tool'}
                </button>
                <button type="button" onClick={resetRegistryForm} className="rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm text-slate-600 dark:text-slate-300">
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-20"><RefreshCw className="h-5 w-5 animate-spin text-slate-400" /></div>
            ) : tools.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <Wrench className="h-8 w-8 text-slate-300 dark:text-slate-600" />
                <div className="text-center">
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">No tools registered yet</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Register tools to enable runtime governance and audit logging.</p>
                </div>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Tool</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Policy</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Enforced</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Description</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Cost</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                  {tools.map((tool) => (
                    <tr key={tool.tool_name} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="px-4 py-3 font-mono text-sm font-semibold dark:text-slate-200">{tool.tool_name}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{tool.policy}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${tool.runtime_enforcement ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300'}`}>
                          {tool.runtime_enforcement ? 'live' : 'off'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 max-w-[280px] truncate">
                        {tool.description || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <Link href={`/chargeback?dimension=feature_tag`} className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-700 dark:text-emerald-400">
                          <DollarSign className="h-3 w-3" /> View
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <button onClick={() => startEditRegistry(tool)} className="rounded-lg p-1.5 text-slate-400 hover:text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-900/20" title="Edit tool">
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => void handleDeleteRegistry(tool.tool_name)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20" title="Remove tool">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {tab === 'search' && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button
              onClick={() => {
                if (showSearchForm && !editingSearchId) resetSearchForm()
                else setShowSearchForm(true)
              }}
              className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
            >
              {showSearchForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              {showSearchForm && !editingSearchId ? 'Cancel' : editingSearchId ? 'Editing Provider' : 'Add Search Provider'}
            </button>
          </div>

          {showSearchForm && (
            <form onSubmit={handleSaveSearch} className="rounded-xl border border-violet-200 dark:border-violet-800 bg-violet-50/50 dark:bg-violet-900/10 p-5 space-y-4">
              <h3 className="text-sm font-semibold text-violet-800 dark:text-violet-300">
                {editingSearchId ? 'Edit search provider' : 'Create search provider'}
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                <input value={searchForm.name} onChange={(e) => setSearchForm((prev) => ({ ...prev, name: e.target.value }))} className={inputCls} placeholder="Provider name" required />
                <input value={searchForm.tool_type} onChange={(e) => setSearchForm((prev) => ({ ...prev, tool_type: e.target.value }))} className={inputCls} placeholder="Tool type" required />
                <input value={searchForm.endpoint_url} onChange={(e) => setSearchForm((prev) => ({ ...prev, endpoint_url: e.target.value }))} className={inputCls} placeholder="Endpoint URL" />
                <input value={searchForm.auth_type} onChange={(e) => setSearchForm((prev) => ({ ...prev, auth_type: e.target.value }))} className={inputCls} placeholder="Auth type" />
                <input value={searchForm.rate_limit_rpm} onChange={(e) => setSearchForm((prev) => ({ ...prev, rate_limit_rpm: e.target.value }))} className={inputCls} placeholder="Rate limit RPM" />
                <input value={searchForm.cost_per_query} onChange={(e) => setSearchForm((prev) => ({ ...prev, cost_per_query: e.target.value }))} className={inputCls} placeholder="Cost per query" />
                <div className="md:col-span-2">
                  <input value={searchForm.description} onChange={(e) => setSearchForm((prev) => ({ ...prev, description: e.target.value }))} className={inputCls} placeholder="Description" />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={searchForm.is_active} onChange={(e) => setSearchForm((prev) => ({ ...prev, is_active: e.target.checked }))} />
                Provider active
              </label>
              <div className="flex gap-2">
                <button type="submit" disabled={saving} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50">
                  {saving ? 'Saving...' : editingSearchId ? 'Save Changes' : 'Create Provider'}
                </button>
                <button type="button" onClick={resetSearchForm} className="rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm text-slate-600 dark:text-slate-300">
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-20"><RefreshCw className="h-5 w-5 animate-spin text-slate-400" /></div>
            ) : searchTools.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <Search className="h-8 w-8 text-slate-300 dark:text-slate-600" />
                <div className="text-center">
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">No search providers yet</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Add providers here instead of maintaining a separate Search Tools page.</p>
                </div>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Provider</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Type</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Queries</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Policies</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                  {searchTools.map((tool) => (
                    <tr key={tool.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{tool.name}</div>
                        <div className="text-xs text-slate-500">{tool.endpoint_url || 'managed internally'}</div>
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{tool.tool_type}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{tool.total_queries}</td>
                      <td className="px-4 py-3">
                        <Link href={`/tool-policies?tool=${encodeURIComponent(tool.name)}`} className="text-violet-600 hover:text-violet-700 dark:text-violet-400 text-xs font-medium">
                          {tool.policy_count} policies
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <button onClick={() => startEditSearch(tool)} className="rounded-lg p-1.5 text-slate-400 hover:text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-900/20" title="Edit provider">
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => void handleDeleteSearch(tool.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20" title="Deactivate provider">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4">
            <div className="flex items-start gap-2">
              <ShieldCheck className="h-4 w-4 text-violet-600 dark:text-violet-400 mt-0.5 shrink-0" />
              <div className="text-sm text-slate-600 dark:text-slate-300">
                <p className="font-medium mb-1">Collapse note</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Search providers are now managed here instead of a separate Search Tools landing page. Their attached governance rules remain visible and editable from Tool Policies.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
