'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  ShieldCheck,
  Plus,
  Trash2,
  Play,
  Wrench,
  Pencil,
  X,
  RefreshCw,
  FlaskConical,
  Building2,
  Radio,
  Link2,
  Layers,
} from 'lucide-react'
import {
  createToolPolicy,
  deleteToolPolicy,
  getAccessGroups,
  getSearchTools,
  getToolGovernanceGatewayPosture,
  getGovernanceInternalPosture,
  getToolPoliciesRuntimePosture,
  getToolGovernanceOrgPosture,
  getToolPolicies,
  getToolPolicyAnalytics,
  listMcpTools,
  simulateToolPolicy,
  updateToolPolicy,
} from '@/lib/api'
import type {
  AccessGroupResponse,
  GovernanceInternalPosture,
  McpToolListItem,
  SearchToolResponse,
  ToolGovernanceGatewayPosture,
  ToolGovernanceOrgPosture,
  ToolPoliciesRuntimePosture,
  ToolPolicyResponse,
  ToolPolicySimulationResponse,
  ToolUsageAnalyticsResponse,
} from '@/types/api'
import PolicyDryRunPanel from '@/components/governance/PolicyDryRunPanel'

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

type Tab = 'policies' | 'dry-run'

function parseTab(value: string | null): Tab {
  return value === 'dry-run' ? 'dry-run' : 'policies'
}

const defaultPolicyForm = {
  name: '',
  description: '',
  tool_name: '',
  action: 'block',
  condition_type: 'all',
  condition_config_text: '{}',
  scope_type: 'workspace',
  scope_id: '',
  priority: 100,
  is_active: true,
}

export default function ToolPoliciesPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const router = useRouter()
  const searchParams = useSearchParams()

  const [tab, setTab] = useState<Tab>(parseTab(searchParams.get('tab')))
  const [policies, setPolicies] = useState<ToolPolicyResponse[]>([])
  const [analytics, setAnalytics] = useState<ToolUsageAnalyticsResponse | null>(null)
  const [accessGroups, setAccessGroups] = useState<AccessGroupResponse[]>([])
  const [searchTools, setSearchTools] = useState<SearchToolResponse[]>([])
  const [discoveredTools, setDiscoveredTools] = useState<McpToolListItem[]>([])
  const [orgPosture, setOrgPosture] = useState<ToolGovernanceOrgPosture | null>(null)
  const [gatewayPosture, setGatewayPosture] = useState<ToolGovernanceGatewayPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<ToolPoliciesRuntimePosture | null>(null)
  const [loading, setLoading] = useState(true)

  const [showForm, setShowForm] = useState(false)
  const [editingPolicyId, setEditingPolicyId] = useState<string | null>(null)
  const [form, setForm] = useState(defaultPolicyForm)
  const [saving, setSaving] = useState(false)

  const [simToolName, setSimToolName] = useState('query')
  const [simRiskScore, setSimRiskScore] = useState(25)
  const [simResult, setSimResult] = useState<ToolPolicySimulationResponse | null>(null)
  const [simulating, setSimulating] = useState(false)

  const filterTool = searchParams.get('tool')

  const loadData = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [polRes, anaRes, agRes, toolsRes, searchRes, orgP, gwP, govInt, rtP] = await Promise.all([
        getToolPolicies(apiKey, { tool_name: filterTool ?? undefined, include_inactive: true }).catch(() => ({ items: [], total: 0 })),
        getToolPolicyAnalytics(apiKey, 250).catch(() => null),
        getAccessGroups(apiKey).catch(() => ({ items: [], total: 0 })),
        listMcpTools(apiKey).catch(() => ({ items: [], total: 0 })),
        getSearchTools(apiKey, { include_inactive: true }).catch(() => ({ items: [], total: 0 })),
        getToolGovernanceOrgPosture(apiKey).catch(() => null),
        getToolGovernanceGatewayPosture(apiKey).catch(() => null),
        getGovernanceInternalPosture(apiKey).catch(() => null),
        getToolPoliciesRuntimePosture(apiKey).catch(() => null),
      ])
      setPolicies(polRes.items || [])
      setAnalytics(anaRes)
      setAccessGroups(agRes.items || [])
      setDiscoveredTools(toolsRes.items || [])
      setSearchTools(searchRes.items || [])
      setOrgPosture(orgP)
      setGatewayPosture(gwP)
      setGovInternal(govInt)
      setRuntimePosture(rtP)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load tool governance data')
    } finally {
      setLoading(false)
    }
  }, [apiKey, filterTool])

  useEffect(() => { void loadData() }, [loadData])
  useEffect(() => { setTab(parseTab(searchParams.get('tab'))) }, [searchParams])

  const toolOptions = useMemo(() => {
    const names = new Set<string>()
    for (const tool of discoveredTools) names.add(tool.tool_name)
    for (const tool of searchTools) names.add(tool.name)
    for (const policy of policies) names.add(policy.tool_name)
    return Array.from(names).sort()
  }, [discoveredTools, searchTools, policies])

  function resetForm() {
    setEditingPolicyId(null)
    setForm(defaultPolicyForm)
    setShowForm(false)
  }

  function startCreate() {
    setEditingPolicyId(null)
    setForm(defaultPolicyForm)
    setShowForm(true)
  }

  function startEdit(policy: ToolPolicyResponse) {
    setEditingPolicyId(policy.id)
    setForm({
      name: policy.name,
      description: policy.description ?? '',
      tool_name: policy.tool_name,
      action: policy.action,
      condition_type: policy.condition_type ?? 'all',
      condition_config_text: JSON.stringify(policy.condition_config ?? {}, null, 2),
      scope_type: policy.scope_type || 'workspace',
      scope_id: policy.scope_id ?? '',
      priority: policy.priority,
      is_active: policy.is_active,
    })
    setShowForm(true)
    setTab('policies')
  }

  async function handleSavePolicy(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !form.name.trim() || !form.tool_name.trim()) return
    let conditionConfig: Record<string, unknown> = {}
    try {
      conditionConfig = JSON.parse(form.condition_config_text || '{}')
    } catch {
      toast.error('Condition config must be valid JSON')
      return
    }

    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      tool_name: form.tool_name.trim(),
      action: form.action,
      condition_type: form.condition_type || undefined,
      condition_config: conditionConfig,
      scope_type: form.scope_type,
      scope_id: form.scope_id || undefined,
      priority: Number(form.priority),
      is_active: form.is_active,
    }

    setSaving(true)
    try {
      if (editingPolicyId) {
        await updateToolPolicy(apiKey, editingPolicyId, payload)
        toast.success('Tool policy updated')
      } else {
        await createToolPolicy(apiKey, payload)
        toast.success('Tool policy created')
      }
      resetForm()
      await loadData()
    } catch {
      toast.error('Failed to save tool policy')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeletePolicy(id: string) {
    if (!apiKey || !confirm('Deactivate this tool policy?')) return
    try {
      await deleteToolPolicy(apiKey, id)
      toast.success('Tool policy deactivated')
      await loadData()
    } catch {
      toast.error('Failed to delete tool policy')
    }
  }

  async function handleSimulate(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !simToolName.trim()) return
    setSimulating(true)
    try {
      const res = await simulateToolPolicy(apiKey, {
        tool_name: simToolName.trim(),
        risk_score: simRiskScore,
        context: { environment: 'production' },
      })
      setSimResult(res)
    } catch {
      toast.error('Failed to run policy simulation')
    } finally {
      setSimulating(false)
    }
  }

  function setTabAndRoute(next: Tab) {
    setTab(next)
    router.replace(`/tool-policies?tab=${next}${filterTool ? `&tool=${encodeURIComponent(filterTool)}` : ''}`)
  }

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between dark:border-slate-800 dark:bg-slate-900/80">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-blue-700 dark:text-blue-400">
            Tool Governance
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 dark:text-white">
            Tool Policies
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Define runtime allow, audit, block, and approval rules for tools. Registry and search-provider setup live in{' '}
            <Link href="/tool-registry" className="font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">
              Tool Registry
            </Link>.
          </p>
          {filterTool && (
            <p className="mt-2 text-xs text-slate-500">
              Filtered to tool: <span className="font-mono text-slate-700 dark:text-slate-300">{filterTool}</span>
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => void loadData()}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={showForm ? resetForm : startCreate}
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition"
          >
            {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showForm ? 'Cancel' : 'Create Tool Policy'}
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-400 font-semibold">Active Policies</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">{policies.filter((p) => p.is_active).length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-400 font-semibold">Unique Tools Tracked</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">{analytics?.unique_tools || toolOptions.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-400 font-semibold">Tool Calls Analyzed</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">{analytics?.total_calls || 0}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-400 font-semibold">Access Groups in Scope</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">{accessGroups.length}</p>
        </div>
      </div>

      {orgPosture && (
        <div className="rounded-2xl border border-blue-200 dark:border-blue-800 bg-blue-50/60 dark:bg-blue-950/40 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-100">Org &amp; Access Scope</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Policy Scope Resolution</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.policy_context.active_policies}</p>
              <p className="text-xs text-slate-500">{orgPosture.policy_context.org_scope} org · {orgPosture.policy_context.workspace_scope} ws · {orgPosture.policy_context.access_group_scope} group</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Access Groups</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.access_group_context.total_groups}</p>
              <p className="text-xs text-slate-500">{orgPosture.access_group_context.tool_policy_groups} with tool policies</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Workspace Users</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.user_context.total_users}</p>
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
              <p className="text-xs text-slate-500">{govInternal.approvals_context.total_approvals_30d} total 30d</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Security Events 30d</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.security_context.security_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Audit Events 30d</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.audit_context.audit_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Active Tags</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.tags_context.active_tags}</p>
              <p className="text-xs text-slate-500">{govInternal.tags_context.total_tags} total</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/tool-registry" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Registry</Link>
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
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Guardrail Events 30d</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.gateway_enforcement.guardrail_events_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.gateway_enforcement.guardrail_rules} rules active</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Policy Violations 30d</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.observe_evidence.policy_violations_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.observe_evidence.request_flows_30d} request flows</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Total Budgets</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.budget_context.total_budgets}</p>
              <p className="text-xs text-slate-500">{runtimePosture.budget_context.budget_notifications_30d} notifications 30d</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Ledger Snapshots</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.ledger_context.ledger_snapshots}</p>
              <p className="text-xs text-slate-500">{runtimePosture.ledger_context.ledger_entries_30d} entries 30d</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/workspaces" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Workspaces</Link>
            <Link href="/api-keys" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">API Keys</Link>
            <Link href="/model-gateway" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Model Gateway</Link>
            <Link href="/guardrails" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Guardrails</Link>
            <Link href="/request-flow" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Request Flow</Link>
            <Link href="/alert-rules" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Alert Rules</Link>
            <Link href="/budgets" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Budgets</Link>
            <Link href="/ledger" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Ledger</Link>
          </div>
        </div>
      )}

      <div className="flex gap-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-1">
        {([
          { id: 'policies' as Tab, label: 'Policies & Simulator', icon: ShieldCheck },
          { id: 'dry-run' as Tab, label: 'Policy Dry Run', icon: FlaskConical },
        ]).map((item) => (
          <button
            key={item.id}
            onClick={() => setTabAndRoute(item.id)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              tab === item.id
                ? 'bg-white dark:bg-slate-900 text-blue-700 dark:text-blue-300 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'policies' && (
        <>
          {showForm && (
            <form onSubmit={handleSavePolicy} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
              <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-blue-600" /> {editingPolicyId ? 'Edit Tool Policy' : 'New Tool Policy'}
              </h2>

              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Policy Name *</label>
                  <input value={form.name} onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))} required className={inputCls} />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Target Tool *</label>
                  {toolOptions.length > 0 ? (
                    <select value={form.tool_name} onChange={(e) => setForm((prev) => ({ ...prev, tool_name: e.target.value }))} className={inputCls} required>
                      <option value="">-- Pick Tool --</option>
                      <option value="*">* (All Tools)</option>
                      {toolOptions.map((tool) => (
                        <option key={tool} value={tool}>{tool}</option>
                      ))}
                    </select>
                  ) : (
                    <input value={form.tool_name} onChange={(e) => setForm((prev) => ({ ...prev, tool_name: e.target.value }))} required className={inputCls} />
                  )}
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Action *</label>
                  <select value={form.action} onChange={(e) => setForm((prev) => ({ ...prev, action: e.target.value }))} className={inputCls}>
                    <option value="block">block</option>
                    <option value="require_approval">require_approval</option>
                    <option value="audit">audit</option>
                    <option value="allow">allow</option>
                  </select>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Scope Type</label>
                  <select value={form.scope_type} onChange={(e) => setForm((prev) => ({ ...prev, scope_type: e.target.value, scope_id: '' }))} className={inputCls}>
                    <option value="workspace">workspace</option>
                    <option value="access_group">access_group</option>
                    <option value="search_tool">search_tool</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Scope Target</label>
                  {form.scope_type === 'access_group' ? (
                    <select value={form.scope_id} onChange={(e) => setForm((prev) => ({ ...prev, scope_id: e.target.value }))} className={inputCls}>
                      <option value="">-- All Access Groups --</option>
                      {accessGroups.map((group) => (
                        <option key={group.id} value={group.id}>{group.name}</option>
                      ))}
                    </select>
                  ) : form.scope_type === 'search_tool' ? (
                    <select value={form.scope_id} onChange={(e) => setForm((prev) => ({ ...prev, scope_id: e.target.value }))} className={inputCls}>
                      <option value="">-- Any Search Provider --</option>
                      {searchTools.map((tool) => (
                        <option key={tool.id} value={tool.id}>{tool.name}</option>
                      ))}
                    </select>
                  ) : (
                    <input value={form.scope_id} onChange={(e) => setForm((prev) => ({ ...prev, scope_id: e.target.value }))} className={inputCls} placeholder="Optional scope id" />
                  )}
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Priority</label>
                  <input type="number" value={form.priority} onChange={(e) => setForm((prev) => ({ ...prev, priority: Number(e.target.value) }))} className={inputCls} />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Condition Type</label>
                  <select value={form.condition_type} onChange={(e) => setForm((prev) => ({ ...prev, condition_type: e.target.value }))} className={inputCls}>
                    <option value="all">all</option>
                    <option value="risk_score_gte">risk_score_gte</option>
                    <option value="tool_type">tool_type</option>
                    <option value="end_user">end_user</option>
                    <option value="feature_tag">feature_tag</option>
                    <option value="context_equals">context_equals</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Description</label>
                  <input value={form.description} onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))} className={inputCls} placeholder="Why this rule exists" />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Condition Config (JSON)</label>
                <textarea value={form.condition_config_text} onChange={(e) => setForm((prev) => ({ ...prev, condition_config_text: e.target.value }))} className={`${inputCls} min-h-28 font-mono`} />
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((prev) => ({ ...prev, is_active: e.target.checked }))} />
                Policy active
              </label>

              <div className="flex gap-2">
                <button type="submit" disabled={saving} className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 transition">
                  {saving ? 'Saving...' : editingPolicyId ? 'Save Changes' : 'Save Policy Rule'}
                </button>
                <button type="button" onClick={resetForm} className="rounded-xl border border-slate-200 dark:border-slate-700 px-5 py-2.5 text-sm font-semibold text-slate-600 dark:text-slate-300">
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
              <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <Play className="h-4 w-4 text-blue-600" /> Interactive Policy Simulator
              </h2>
              <p className="text-xs text-slate-500">
                Test arbitrary tool execution payloads against the registered rules and inspect rule matching.
              </p>

              <form onSubmit={handleSimulate} className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Test Tool Name</label>
                  <input value={simToolName} onChange={(e) => setSimToolName(e.target.value)} className={inputCls} />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">Risk Score (0-100)</label>
                  <input type="number" min={0} max={100} value={simRiskScore} onChange={(e) => setSimRiskScore(Number(e.target.value))} className={inputCls} />
                </div>
                <button type="submit" disabled={simulating} className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50">
                  {simulating ? 'Simulating...' : 'Run Simulation'}
                </button>
              </form>

              {simResult && (
                <div className="mt-4 rounded-xl border border-slate-200 bg-slate-950 p-4 font-mono text-xs text-slate-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Final Action:</span>
                    <span className={`font-bold uppercase ${
                      simResult.final_action === 'block'
                        ? 'text-red-400'
                        : simResult.final_action === 'require_approval'
                        ? 'text-amber-400'
                        : simResult.final_action === 'audit'
                        ? 'text-blue-400'
                        : 'text-emerald-400'
                    }`}>
                      {simResult.final_action}
                    </span>
                  </div>
                  <div>
                    <p className="text-slate-400 font-semibold mb-1">Matched Rules:</p>
                    {simResult.matched_policy_names.length === 0 ? (
                      <p className="text-slate-500">No policy rules matched. Default ALLOW.</p>
                    ) : (
                      simResult.matched_policy_names.map((name, i) => (
                        <div key={`${name}-${i}`} className="text-slate-300">
                          • {name} — <span className="text-slate-400">{simResult.reasons[i]}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
              <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-blue-600" /> Active Policy Rules ({policies.length})
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50/80 dark:bg-slate-950/50 text-xs uppercase tracking-wider text-slate-500 font-semibold border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3 text-left">Policy</th>
                      <th className="py-2.5 px-3 text-left">Tool</th>
                      <th className="py-2.5 px-3 text-left">Action</th>
                      <th className="py-2.5 px-3 text-left">Scope</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {policies.map((policy) => (
                      <tr key={policy.id} className="hover:bg-slate-50 dark:hover:bg-slate-950/40">
                        <td className="py-2.5 px-3">
                          <div className="font-semibold text-slate-900 dark:text-white">{policy.name}</div>
                          <div className="text-xs text-slate-500">{policy.condition_type || 'all'} • priority {policy.priority}</div>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-xs text-blue-600 dark:text-blue-400">{policy.tool_name}</td>
                        <td className="py-2.5 px-3">
                          <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                            policy.action === 'block'
                              ? 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
                              : policy.action === 'require_approval'
                              ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                              : policy.action === 'audit'
                              ? 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                              : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                          }`}>
                            {policy.action}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-xs text-slate-500">{policy.scope_type || 'workspace'}</td>
                        <td className="py-2.5 px-3">
                          <div className="flex justify-end gap-2">
                            <button onClick={() => startEdit(policy)} className="rounded-lg p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20" title="Edit policy">
                              <Pencil className="h-3.5 w-3.5" />
                            </button>
                            <button onClick={() => void handleDeletePolicy(policy.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20" title="Deactivate policy">
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {policies.length === 0 && !loading && (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-slate-400 text-xs">
                          No tool policy rules created yet. Create one above to add runtime safety rules.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          {analytics && (
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="p-4 border-b border-slate-200 dark:border-slate-800 font-semibold text-slate-900 dark:text-white text-sm">
                Tool Telemetry & Execution Analytics
              </div>
              <table className="w-full text-sm">
                <thead className="bg-slate-50/80 dark:bg-slate-950/50 text-xs uppercase tracking-wider text-slate-500 font-semibold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3 text-left">Tool Name</th>
                    <th className="px-4 py-3 text-left">Total Calls</th>
                    <th className="px-4 py-3 text-left">Allowed</th>
                    <th className="px-4 py-3 text-left">Denied / Blocked</th>
                    <th className="px-4 py-3 text-right">Avg Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {analytics.items.map((item) => (
                    <tr key={item.tool_name} className="hover:bg-slate-50 dark:hover:bg-slate-950/40">
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        <Wrench className="h-4 w-4 text-blue-600" /> {item.tool_name}
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300 font-mono text-xs">{item.total_calls}</td>
                      <td className="px-4 py-3 text-emerald-600 font-mono text-xs">{item.allowed_calls}</td>
                      <td className="px-4 py-3 text-red-500 font-mono text-xs">{item.denied_calls}</td>
                      <td className="px-4 py-3 text-right text-xs text-slate-400 font-mono">
                        {item.avg_duration_ms != null ? `${item.avg_duration_ms.toFixed(1)} ms` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </>
      )}

      {tab === 'dry-run' && <PolicyDryRunPanel apiKey={apiKey} />}
    </div>
  )
}
