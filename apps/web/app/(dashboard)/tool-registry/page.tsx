'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  Wrench, Plus, Trash2, RefreshCw, ShieldCheck, Search, Pencil, X, DollarSign,
  Play, FlaskConical, Shield, Layers, Radio, Building2, Link2, Zap, Activity,
  CheckCircle2, XCircle, Loader2, FileText, ArrowUpCircle, ExternalLink,
} from 'lucide-react'
import {
  createSearchTool, createToolPolicy, deleteSearchTool, deleteToolPolicy,
  deleteToolRegistry, getAccessGroups, getGovernanceInternalPosture, getSearchTools,
  getToolGovernanceGatewayPosture, getToolGovernanceOrgPosture, getToolPolicies,
  getToolPolicyAnalytics, getToolRegistryFinopsPosture, getToolRegistryRuntimePosture,
  getToolPoliciesRuntimePosture, listMcpTools, listToolRegistry, policyDryRun,
  getPolicyDryRunReport, promotePolicy, simulateToolPolicy, updateSearchTool,
  updateToolPolicy, updateToolRegistry, upsertToolRegistry,
} from '@/lib/api'
import type {
  AccessGroupResponse, GovernanceInternalPosture, McpToolListItem, SearchToolResponse,
  ToolGovernanceGatewayPosture, ToolGovernanceOrgPosture, ToolPoliciesRuntimePosture,
  ToolPolicyResponse, ToolPolicySimulationResponse, ToolRegistryResponse,
  ToolRegistryFinopsPosture, ToolRegistryRuntimePosture, ToolUsageAnalyticsResponse,
  PolicyCheckResponse, PolicyDryRunReport,
} from '@/types/api'
import { num } from '@/lib/utils'

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500'

type Tab = 'registry' | 'search' | 'policies' | 'dry-run'

function parseTab(value: string | null): Tab {
  if (value === 'search') return 'search'
  if (value === 'policies') return 'policies'
  if (value === 'dry-run') return 'dry-run'
  return 'registry'
}

const tabDefs: { id: Tab; label: string; icon: typeof Wrench }[] = [
  { id: 'registry', label: 'Registry', icon: Wrench },
  { id: 'search', label: 'Search Providers', icon: Search },
  { id: 'policies', label: 'Policies', icon: ShieldCheck },
  { id: 'dry-run', label: 'Dry Run', icon: FlaskConical },
]

const defaultPolicyForm = {
  name: '', description: '', tool_name: '', action: 'block',
  condition_type: 'all', condition_config_text: '{}',
  scope_type: 'workspace', scope_id: '', priority: 100, is_active: true,
}

const dryRunFields = [
  { key: 'end_user_id', label: 'End User ID', placeholder: 'e.g. user_abc123' },
  { key: 'feature_tag', label: 'Feature Tag', placeholder: 'e.g. chat, summarize' },
  { key: 'tool_name', label: 'Tool Name', placeholder: 'e.g. web_search' },
  { key: 'model_alias', label: 'Model Alias', placeholder: 'e.g. gpt-4o' },
] as const
type DryRunFormKeys = (typeof dryRunFields)[number]['key']

const detailLabels: { key: string; label: string; good: (v: unknown) => boolean }[] = [
  { key: 'budget_remaining_usd', label: 'Budget Remaining', good: (v) => Number(v) > 0 },
  { key: 'budget_limit_usd', label: 'Budget Limit', good: () => true },
  { key: 'budget_period', label: 'Budget Period', good: () => true },
  { key: 'tool_registered', label: 'Tool Registered', good: (v) => v === true },
  { key: 'tool_policy_setting', label: 'Tool Policy', good: (v) => v === 'allow' || v === 'audit' },
  { key: 'gateway_routes_found', label: 'Gateway Routes', good: (v) => Number(v) > 0 },
  { key: 'gateway_route_aliases', label: 'Route Aliases', good: (v) => Array.isArray(v) && v.length > 0 },
  { key: 'score_latest_value', label: 'Score Value', good: () => true },
  { key: 'score_gate_threshold', label: 'Score Threshold', good: () => true },
]

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return '-'
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  if (Array.isArray(v)) return v.length ? v.join(', ') : '-'
  return String(v)
}

const actionBadge: Record<string, string> = {
  block: 'bg-red-500/10 text-red-400 border-red-500/20',
  allow: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  audit: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  require_approval: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  reroute: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
}

export default function ToolGovernancePage() {
  const { data: session } = useSession()
  const searchParams = useSearchParams()
  const router = useRouter()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const [tab, setTab] = useState<Tab>(parseTab(searchParams.get('tab')))

  const [tools, setTools] = useState<ToolRegistryResponse[]>([])
  const [searchToolsList, setSearchToolsList] = useState<SearchToolResponse[]>([])
  const [policies, setPolicies] = useState<ToolPolicyResponse[]>([])
  const [analytics, setAnalytics] = useState<ToolUsageAnalyticsResponse | null>(null)
  const [accessGroups, setAccessGroups] = useState<AccessGroupResponse[]>([])
  const [discoveredTools, setDiscoveredTools] = useState<McpToolListItem[]>([])
  const [finopsPosture, setFinopsPosture] = useState<ToolRegistryFinopsPosture | null>(null)
  const [orgPosture, setOrgPosture] = useState<ToolGovernanceOrgPosture | null>(null)
  const [gatewayPosture, setGatewayPosture] = useState<ToolGovernanceGatewayPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<ToolRegistryRuntimePosture | null>(null)
  const [policiesRuntimePosture, setPoliciesRuntimePosture] = useState<ToolPoliciesRuntimePosture | null>(null)
  const [loading, setLoading] = useState(true)

  const [showRegistryForm, setShowRegistryForm] = useState(false)
  const [showSearchForm, setShowSearchForm] = useState(false)
  const [showPolicyForm, setShowPolicyForm] = useState(false)
  const [editingToolName, setEditingToolName] = useState<string | null>(null)
  const [editingSearchId, setEditingSearchId] = useState<string | null>(null)
  const [editingPolicyId, setEditingPolicyId] = useState<string | null>(null)

  const [registryForm, setRegistryForm] = useState({
    tool_name: '', policy: 'audit', runtime_enforcement: false, description: '',
  })
  const [searchForm, setSearchForm] = useState({
    name: '', description: '', tool_type: 'web_search', endpoint_url: '',
    auth_type: '', rate_limit_rpm: '', cost_per_query: '0', is_active: true,
  })
  const [policyForm, setPolicyForm] = useState(defaultPolicyForm)
  const [saving, setSaving] = useState(false)

  const [simToolName, setSimToolName] = useState('query')
  const [simRiskScore, setSimRiskScore] = useState(25)
  const [simResult, setSimResult] = useState<ToolPolicySimulationResponse | null>(null)
  const [simulating, setSimulating] = useState(false)

  const [dryRunForm, setDryRunForm] = useState<Record<DryRunFormKeys, string>>({
    end_user_id: '', feature_tag: '', tool_name: '', model_alias: '',
  })
  const [dryRunLoading, setDryRunLoading] = useState(false)
  const [dryRunResult, setDryRunResult] = useState<PolicyCheckResponse | null>(null)
  const [promoting, setPromoting] = useState(false)
  const [report, setReport] = useState<PolicyDryRunReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportPromoting, setReportPromoting] = useState(false)
  const [dryRunSub, setDryRunSub] = useState<'single' | 'report'>('single')

  const filterTool = searchParams.get('tool')

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [registry, providers, polRes, anaRes, agRes, mcpTools, posture, orgP, gwP, govI, rtP, prtP] = await Promise.all([
        listToolRegistry(apiKey),
        getSearchTools(apiKey, { include_inactive: true }),
        getToolPolicies(apiKey, { tool_name: filterTool ?? undefined, include_inactive: true }).catch(() => ({ items: [], total: 0 })),
        getToolPolicyAnalytics(apiKey, 250).catch(() => null),
        getAccessGroups(apiKey).catch(() => ({ items: [], total: 0 })),
        listMcpTools(apiKey).catch(() => ({ items: [], total: 0 })),
        getToolRegistryFinopsPosture(apiKey).catch(() => null),
        getToolGovernanceOrgPosture(apiKey).catch(() => null),
        getToolGovernanceGatewayPosture(apiKey).catch(() => null),
        getGovernanceInternalPosture(apiKey).catch(() => null),
        getToolRegistryRuntimePosture(apiKey).catch(() => null),
        getToolPoliciesRuntimePosture(apiKey).catch(() => null),
      ])
      setTools(registry.items)
      setSearchToolsList(providers.items)
      setPolicies(polRes.items || [])
      setAnalytics(anaRes)
      setAccessGroups(agRes.items || [])
      setDiscoveredTools(mcpTools.items || [])
      setFinopsPosture(posture)
      setOrgPosture(orgP)
      setGatewayPosture(gwP)
      setGovInternal(govI)
      setRuntimePosture(rtP)
      setPoliciesRuntimePosture(prtP)
    } catch {
      toast.error('Failed to load tool governance data')
    } finally {
      setLoading(false)
    }
  }, [apiKey, filterTool])

  useEffect(() => { void load() }, [load])
  useEffect(() => { setTab(parseTab(searchParams.get('tab'))) }, [searchParams])

  const toolOptions = useMemo(() => {
    const names = new Set<string>()
    for (const t of discoveredTools) names.add(t.tool_name)
    for (const t of searchToolsList) names.add(t.name)
    for (const p of policies) names.add(p.tool_name)
    return Array.from(names).sort()
  }, [discoveredTools, searchToolsList, policies])

  function changeTab(next: Tab) {
    setTab(next)
    router.replace(`/tool-registry?tab=${next}${filterTool ? `&tool=${encodeURIComponent(filterTool)}` : ''}`)
  }

  // --- Registry CRUD ---
  function resetRegistryForm() {
    setEditingToolName(null)
    setRegistryForm({ tool_name: '', policy: 'audit', runtime_enforcement: false, description: '' })
    setShowRegistryForm(false)
  }
  function startEditRegistry(tool: ToolRegistryResponse) {
    setEditingToolName(tool.tool_name)
    setRegistryForm({ tool_name: tool.tool_name, policy: tool.policy, runtime_enforcement: tool.runtime_enforcement, description: tool.description ?? '' })
    setShowRegistryForm(true)
  }
  async function handleSaveRegistry(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !registryForm.tool_name.trim()) return
    setSaving(true)
    try {
      if (editingToolName) {
        await updateToolRegistry(apiKey, editingToolName, { policy: registryForm.policy, runtime_enforcement: registryForm.runtime_enforcement, description: registryForm.description.trim() || null })
        toast.success('Tool updated')
      } else {
        await upsertToolRegistry(apiKey, { tool_name: registryForm.tool_name.trim(), policy: registryForm.policy, runtime_enforcement: registryForm.runtime_enforcement, description: registryForm.description.trim() || null })
        toast.success('Tool registered')
      }
      resetRegistryForm()
      await load()
    } catch { toast.error('Failed to save') } finally { setSaving(false) }
  }
  async function handleDeleteRegistry(toolName: string) {
    if (!apiKey || !confirm(`Remove "${toolName}"?`)) return
    try { await deleteToolRegistry(apiKey, toolName); toast.success('Removed'); await load() } catch { toast.error('Failed') }
  }

  // --- Search CRUD ---
  function resetSearchForm() {
    setEditingSearchId(null)
    setSearchForm({ name: '', description: '', tool_type: 'web_search', endpoint_url: '', auth_type: '', rate_limit_rpm: '', cost_per_query: '0', is_active: true })
    setShowSearchForm(false)
  }
  function startEditSearch(tool: SearchToolResponse) {
    setEditingSearchId(tool.id)
    setSearchForm({ name: tool.name, description: tool.description ?? '', tool_type: tool.tool_type, endpoint_url: tool.endpoint_url ?? '', auth_type: tool.auth_type ?? '', rate_limit_rpm: tool.rate_limit_rpm != null ? String(tool.rate_limit_rpm) : '', cost_per_query: String(tool.cost_per_query ?? 0), is_active: tool.is_active })
    setShowSearchForm(true)
  }
  async function handleSaveSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !searchForm.name.trim()) return
    setSaving(true)
    try {
      const payload = { name: searchForm.name.trim(), description: searchForm.description.trim() || null, tool_type: searchForm.tool_type.trim(), endpoint_url: searchForm.endpoint_url.trim() || null, auth_type: searchForm.auth_type.trim() || null, auth_config: {}, rate_limit_rpm: searchForm.rate_limit_rpm ? Number(searchForm.rate_limit_rpm) : null, cost_per_query: Number(searchForm.cost_per_query || '0'), is_active: searchForm.is_active }
      if (editingSearchId) { await updateSearchTool(apiKey, editingSearchId, payload); toast.success('Updated') } else { await createSearchTool(apiKey, payload); toast.success('Created') }
      resetSearchForm()
      await load()
    } catch { toast.error('Failed to save') } finally { setSaving(false) }
  }
  async function handleDeleteSearch(toolId: string) {
    if (!apiKey || !confirm('Deactivate this provider?')) return
    try { await deleteSearchTool(apiKey, toolId); toast.success('Deactivated'); await load() } catch { toast.error('Failed') }
  }

  // --- Policy CRUD ---
  function resetPolicyForm() { setEditingPolicyId(null); setPolicyForm(defaultPolicyForm); setShowPolicyForm(false) }
  function startEditPolicy(p: ToolPolicyResponse) {
    setEditingPolicyId(p.id)
    setPolicyForm({ name: p.name, description: p.description ?? '', tool_name: p.tool_name, action: p.action, condition_type: p.condition_type ?? 'all', condition_config_text: JSON.stringify(p.condition_config ?? {}, null, 2), scope_type: p.scope_type || 'workspace', scope_id: p.scope_id ?? '', priority: p.priority, is_active: p.is_active })
    setShowPolicyForm(true)
  }
  async function handleSavePolicy(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !policyForm.name.trim() || !policyForm.tool_name.trim()) return
    let condCfg: Record<string, unknown> = {}
    try { condCfg = JSON.parse(policyForm.condition_config_text || '{}') } catch { toast.error('Invalid JSON'); return }
    const payload = { name: policyForm.name.trim(), description: policyForm.description.trim() || undefined, tool_name: policyForm.tool_name.trim(), action: policyForm.action, condition_type: policyForm.condition_type || undefined, condition_config: condCfg, scope_type: policyForm.scope_type, scope_id: policyForm.scope_id || undefined, priority: Number(policyForm.priority), is_active: policyForm.is_active }
    setSaving(true)
    try {
      if (editingPolicyId) { await updateToolPolicy(apiKey, editingPolicyId, payload); toast.success('Policy updated') } else { await createToolPolicy(apiKey, payload); toast.success('Policy created') }
      resetPolicyForm()
      await load()
    } catch { toast.error('Failed to save policy') } finally { setSaving(false) }
  }
  async function handleDeletePolicy(id: string) {
    if (!apiKey || !confirm('Deactivate this policy?')) return
    try { await deleteToolPolicy(apiKey, id); toast.success('Deactivated'); await load() } catch { toast.error('Failed') }
  }

  // --- Simulator ---
  async function handleSimulate(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !simToolName.trim()) return
    setSimulating(true)
    try { const res = await simulateToolPolicy(apiKey, { tool_name: simToolName.trim(), risk_score: simRiskScore, context: { environment: 'production' } }); setSimResult(res) } catch { toast.error('Simulation failed') } finally { setSimulating(false) }
  }

  // --- Dry Run ---
  async function handleDryRun(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setDryRunLoading(true); setDryRunResult(null)
    try {
      const body: Record<string, unknown> = { dry_run: true as const }
      for (const f of dryRunFields) { if (dryRunForm[f.key].trim()) body[f.key] = dryRunForm[f.key].trim() }
      const res = await policyDryRun(apiKey, body as Parameters<typeof policyDryRun>[1])
      setDryRunResult(res)
    } catch { toast.error('Check failed') } finally { setDryRunLoading(false) }
  }
  async function handlePromote(policyType: string) {
    setPromoting(true)
    try { const res = await promotePolicy(apiKey!, { policy_type: policyType, enforce: true }); toast.success(res.message || 'Promoted') } catch { toast.error('Failed') } finally { setPromoting(false) }
  }
  async function loadReport() {
    setReportLoading(true)
    try { const data = await getPolicyDryRunReport(apiKey!, { limit: 100 }); setReport(data) } catch { toast.error('Failed to load report') } finally { setReportLoading(false) }
  }
  async function handleReportPromote(policyType: string) {
    setReportPromoting(true)
    try { const res = await promotePolicy(apiKey!, { policy_type: policyType, enforce: true }); toast.success(res.message || 'Promoted') } catch { toast.error('Failed') } finally { setReportPromoting(false) }
  }

  const activeRegistry = tools.filter((t) => t.runtime_enforcement).length
  const activeSearch = searchToolsList.filter((t) => t.is_active).length
  const activePolicies = policies.filter((p) => p.is_active).length

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-6xl space-y-3">
      {/* ── Hero Header ── */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 px-5 py-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 border border-cyan-200 dark:bg-cyan-500/20 dark:border-cyan-500/30">
                <Shield className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
              </div>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-600 dark:text-cyan-400">Safety &amp; Governance</p>
            </div>
            <h1 className="text-lg font-bold text-slate-950 dark:text-white">Tool Governance</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 max-w-xl">
              Unified control surface for runtime tool registrations, search providers, governance policies, and dry-run testing.
            </p>
            {filterTool && (
              <p className="text-[10px] text-cyan-600 dark:text-cyan-400 mt-1">Filtered: <span className="font-mono text-cyan-700 dark:text-cyan-300">{filterTool}</span></p>
            )}
          </div>
          <button onClick={() => void load()} className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 transition-colors dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300 dark:hover:bg-slate-700/60">
            <RefreshCw className="h-3 w-3" /> Refresh
          </button>
        </div>
      </div>

      {/* ── KPI Strip ── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
        {[
          { label: 'Registered', value: tools.length, color: 'cyan' },
          { label: 'Enforced', value: activeRegistry, color: 'emerald' },
          { label: 'Search Providers', value: searchToolsList.length, color: 'violet' },
          { label: 'Active Providers', value: activeSearch, color: 'blue' },
          { label: 'Active Policies', value: activePolicies, color: 'amber' },
          { label: 'Tools Tracked', value: analytics?.unique_tools || toolOptions.length, color: 'rose' },
        ].map((k) => {
          const colorMap: Record<string, { border: string; bg: string; text: string }> = {
            cyan: { border: 'border-cyan-500/20', bg: 'bg-cyan-500/5 dark:bg-cyan-950/30', text: 'text-cyan-600 dark:text-cyan-400' },
            emerald: { border: 'border-emerald-500/20', bg: 'bg-emerald-500/5 dark:bg-emerald-950/30', text: 'text-emerald-600 dark:text-emerald-400' },
            violet: { border: 'border-violet-500/20', bg: 'bg-violet-500/5 dark:bg-violet-950/30', text: 'text-violet-600 dark:text-violet-400' },
            blue: { border: 'border-blue-500/20', bg: 'bg-blue-500/5 dark:bg-blue-950/30', text: 'text-blue-600 dark:text-blue-400' },
            amber: { border: 'border-amber-500/20', bg: 'bg-amber-500/5 dark:bg-amber-950/30', text: 'text-amber-600 dark:text-amber-400' },
            rose: { border: 'border-rose-500/20', bg: 'bg-rose-500/5 dark:bg-rose-950/30', text: 'text-rose-600 dark:text-rose-400' },
          }
          const c = colorMap[k.color] || colorMap.cyan
          return (
            <div key={k.label} className={`rounded-xl border ${c.border} ${c.bg} px-3 py-2`}>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{k.label}</p>
              <p className={`text-xl font-bold ${c.text}`}>{k.value}</p>
            </div>
          )
        })}
      </div>

      {/* ── Posture Sections (compact chips) ── */}
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {finopsPosture && (
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 dark:bg-emerald-950/20 px-3 py-2.5 space-y-1.5">
            <div className="flex items-center gap-1.5">
              <DollarSign className="h-3.5 w-3.5 text-emerald-500" />
              <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 dark:text-emerald-400">FinOps</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">Spend 30d: ${num(finopsPosture.spend_context.tool_spend_30d).toFixed(2)}</span>
              <span className="rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">{finopsPosture.spend_context.tool_call_count_30d.toLocaleString()} calls</span>
              <span className="rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">{finopsPosture.budget_context.total_budgets} budgets</span>
              <span className="rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">{finopsPosture.chargeback_context.chargeback_rules} chargeback</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              <Link href="/budgets" className="text-[10px] text-emerald-600 hover:text-emerald-500 dark:text-emerald-400">Budgets</Link>
              <Link href="/chargeback?dimension=feature_tag" className="text-[10px] text-emerald-600 hover:text-emerald-500 dark:text-emerald-400">Chargeback</Link>
              <Link href="/ledger" className="text-[10px] text-emerald-600 hover:text-emerald-500 dark:text-emerald-400">Ledger</Link>
            </div>
          </div>
        )}

        {orgPosture && (
          <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 dark:bg-blue-950/20 px-3 py-2.5 space-y-1.5">
            <div className="flex items-center gap-1.5">
              <Building2 className="h-3.5 w-3.5 text-blue-500" />
              <p className="text-[10px] font-bold uppercase tracking-widest text-blue-600 dark:text-blue-400">Org Scope</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-md bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:text-blue-300">{orgPosture.user_context.total_users} users</span>
              <span className="rounded-md bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:text-blue-300">{orgPosture.access_group_context.total_groups} groups</span>
              <span className="rounded-md bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:text-blue-300">{orgPosture.api_key_context.total_keys} API keys</span>
              <span className="rounded-md bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:text-blue-300">{orgPosture.mcp_context.active_servers} MCP servers</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              <Link href="/organization" className="text-[10px] text-blue-600 hover:text-blue-500 dark:text-blue-400">Org</Link>
              <Link href="/users" className="text-[10px] text-blue-600 hover:text-blue-500 dark:text-blue-400">Users</Link>
              <Link href="/access-groups" className="text-[10px] text-blue-600 hover:text-blue-500 dark:text-blue-400">Groups</Link>
              <Link href="/mcp-registry" className="text-[10px] text-blue-600 hover:text-blue-500 dark:text-blue-400">MCP</Link>
            </div>
          </div>
        )}

        {gatewayPosture && (
          <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 dark:bg-violet-950/20 px-3 py-2.5 space-y-1.5">
            <div className="flex items-center gap-1.5">
              <Radio className="h-3.5 w-3.5 text-violet-500" />
              <p className="text-[10px] font-bold uppercase tracking-widest text-violet-600 dark:text-violet-400">Gateway</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-md bg-violet-500/10 border border-violet-500/20 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">{gatewayPosture.provider_context.total_routes} routes</span>
              <span className="rounded-md bg-violet-500/10 border border-violet-500/20 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">{gatewayPosture.guardrail_context.total_guardrails} guardrails</span>
              <span className="rounded-md bg-violet-500/10 border border-violet-500/20 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">{gatewayPosture.run_context.tool_runs_30d.toLocaleString()} tool calls</span>
              <span className="rounded-md bg-violet-500/10 border border-violet-500/20 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">{gatewayPosture.monitoring_context.alert_firings_30d} alerts</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              <Link href="/gateway" className="text-[10px] text-violet-600 hover:text-violet-500 dark:text-violet-400">Gateway</Link>
              <Link href="/guardrails" className="text-[10px] text-violet-600 hover:text-violet-500 dark:text-violet-400">Guardrails</Link>
              <Link href="/runs" className="text-[10px] text-violet-600 hover:text-violet-500 dark:text-violet-400">Runs</Link>
              <Link href="/monitoring" className="text-[10px] text-violet-600 hover:text-violet-500 dark:text-violet-400">Monitoring</Link>
            </div>
          </div>
        )}

        {govInternal && (
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 dark:bg-rose-950/20 px-3 py-2.5 space-y-1.5">
            <div className="flex items-center gap-1.5">
              <Link2 className="h-3.5 w-3.5 text-rose-500" />
              <p className="text-[10px] font-bold uppercase tracking-widest text-rose-600 dark:text-rose-400">Governance</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-md bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:text-rose-300">{govInternal.approvals_context.pending_approvals} pending</span>
              <span className="rounded-md bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:text-rose-300">{govInternal.security_context.security_events_30d} security</span>
              <span className="rounded-md bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:text-rose-300">{govInternal.audit_context.audit_events_30d} audit</span>
              <span className="rounded-md bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:text-rose-300">{govInternal.tags_context.active_tags} tags</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              <Link href="/approvals" className="text-[10px] text-rose-600 hover:text-rose-500 dark:text-rose-400">Approvals</Link>
              <Link href="/security" className="text-[10px] text-rose-600 hover:text-rose-500 dark:text-rose-400">Security</Link>
              <Link href="/audit" className="text-[10px] text-rose-600 hover:text-rose-500 dark:text-rose-400">Audit</Link>
              <Link href="/tags" className="text-[10px] text-rose-600 hover:text-rose-500 dark:text-rose-400">Tags</Link>
            </div>
          </div>
        )}

        {runtimePosture && (
          <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 dark:bg-cyan-950/20 px-3 py-2.5 space-y-1.5">
            <div className="flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-cyan-500" />
              <p className="text-[10px] font-bold uppercase tracking-widest text-cyan-600 dark:text-cyan-400">Runtime</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-md bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 text-[10px] font-medium text-cyan-700 dark:text-cyan-300">{runtimePosture.api_key_scope.keys_with_tool_calls_30d} keys w/ tools</span>
              <span className="rounded-md bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 text-[10px] font-medium text-cyan-700 dark:text-cyan-300">{runtimePosture.gateway_runtime.model_routes} model routes</span>
              <span className="rounded-md bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 text-[10px] font-medium text-cyan-700 dark:text-cyan-300">{runtimePosture.observe_evidence.tool_requests_30d.toLocaleString()} requests</span>
              <span className="rounded-md bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 text-[10px] font-medium text-cyan-700 dark:text-cyan-300">{runtimePosture.budget_linkage.budget_notifications_30d} budget alerts</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              <Link href="/api-keys" className="text-[10px] text-cyan-600 hover:text-cyan-500 dark:text-cyan-400">Keys</Link>
              <Link href="/gateway" className="text-[10px] text-cyan-600 hover:text-cyan-500 dark:text-cyan-400">Gateway</Link>
              <Link href="/request-explorer" className="text-[10px] text-cyan-600 hover:text-cyan-500 dark:text-cyan-400">Requests</Link>
              <Link href="/budgets" className="text-[10px] text-cyan-600 hover:text-cyan-500 dark:text-cyan-400">Budgets</Link>
            </div>
          </div>
        )}

        {policiesRuntimePosture && (
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 dark:bg-amber-950/20 px-3 py-2.5 space-y-1.5">
            <div className="flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-amber-500" />
              <p className="text-[10px] font-bold uppercase tracking-widest text-amber-600 dark:text-amber-400">Enforcement</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-md bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-300">{policiesRuntimePosture.gateway_enforcement.guardrail_events_30d} guardrail events</span>
              <span className="rounded-md bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-300">{policiesRuntimePosture.observe_evidence.policy_violations_30d} violations</span>
              <span className="rounded-md bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-300">{policiesRuntimePosture.budget_context.total_budgets} budgets</span>
              <span className="rounded-md bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-300">{policiesRuntimePosture.ledger_context.ledger_snapshots} snapshots</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              <Link href="/guardrails" className="text-[10px] text-amber-600 hover:text-amber-500 dark:text-amber-400">Guardrails</Link>
              <Link href="/alert-rules" className="text-[10px] text-amber-600 hover:text-amber-500 dark:text-amber-400">Alert Rules</Link>
              <Link href="/ledger" className="text-[10px] text-amber-600 hover:text-amber-500 dark:text-amber-400">Ledger</Link>
            </div>
          </div>
        )}
      </div>

      {/* ── Tab Bar ── */}
      <div className="flex gap-0.5 rounded-xl border border-slate-200/60 dark:border-slate-700/60 bg-slate-100/80 dark:bg-slate-800/50 p-0.5">
        {tabDefs.map((t) => (
          <button
            key={t.id}
            onClick={() => changeTab(t.id)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
              tab === t.id
                ? 'bg-white dark:bg-slate-900 text-cyan-700 dark:text-cyan-300 shadow-sm border border-cyan-500/20'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white'
            }`}
          >
            <t.icon className="h-3.5 w-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {/* ══════════ REGISTRY TAB ══════════ */}
      {tab === 'registry' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button
              onClick={() => { if (showRegistryForm && !editingToolName) resetRegistryForm(); else { resetRegistryForm(); setShowRegistryForm(true) } }}
              className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:from-cyan-500 hover:to-blue-500 transition-all shadow-sm shadow-cyan-500/20"
            >
              {showRegistryForm ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
              {showRegistryForm && !editingToolName ? 'Cancel' : editingToolName ? 'Editing' : 'Register Tool'}
            </button>
          </div>

          {showRegistryForm && (
            <form onSubmit={handleSaveRegistry} className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 dark:bg-cyan-950/20 p-3 space-y-2.5">
              <h3 className="text-xs font-bold text-cyan-700 dark:text-cyan-300">{editingToolName ? `Edit ${editingToolName}` : 'Register a runtime tool'}</h3>
              <div className="grid gap-2 md:grid-cols-2">
                <div className="flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Tool name *</label>
                  <input value={registryForm.tool_name} onChange={(e) => setRegistryForm((p) => ({ ...p, tool_name: e.target.value }))} className={inputCls} disabled={Boolean(editingToolName)} required />
                </div>
                <div className="flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Policy</label>
                  <select value={registryForm.policy} onChange={(e) => setRegistryForm((p) => ({ ...p, policy: e.target.value }))} className={inputCls}>
                    <option value="audit">audit</option><option value="allow">allow</option><option value="block">block</option>
                  </select>
                </div>
                <div className="md:col-span-2 flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Description</label>
                  <input value={registryForm.description} onChange={(e) => setRegistryForm((p) => ({ ...p, description: e.target.value }))} className={inputCls} placeholder="What this tool does" />
                </div>
              </div>
              <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={registryForm.runtime_enforcement} onChange={(e) => setRegistryForm((p) => ({ ...p, runtime_enforcement: e.target.checked }))} />
                Enable runtime enforcement
              </label>
              <div className="flex gap-2">
                <button type="submit" disabled={saving} className="rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50">{saving ? 'Saving...' : editingToolName ? 'Save' : 'Register'}</button>
                <button type="button" onClick={resetRegistryForm} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300">Cancel</button>
              </div>
            </form>
          )}

          <div className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-12"><RefreshCw className="h-4 w-4 animate-spin text-slate-400" /></div>
            ) : tools.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 gap-2">
                <Wrench className="h-6 w-6 text-slate-400 dark:text-slate-600" />
                <p className="text-xs text-slate-500">No tools registered yet</p>
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead className="bg-slate-50/80 dark:bg-slate-800/60 border-b border-slate-200/60 dark:border-slate-700/60">
                  <tr>
                    <th className="px-3 py-1.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-500">Tool</th>
                    <th className="px-3 py-1.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-500">Policy</th>
                    <th className="px-3 py-1.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-500">Status</th>
                    <th className="px-3 py-1.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-500">Description</th>
                    <th className="px-3 py-1.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-500">Cost</th>
                    <th className="px-3 py-1.5 text-right text-[10px] font-bold uppercase tracking-wider text-slate-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100/80 dark:divide-slate-700/40">
                  {tools.map((tool) => (
                    <tr key={tool.tool_name} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                      <td className="px-3 py-1.5 font-mono font-semibold text-slate-900 dark:text-slate-200">{tool.tool_name}</td>
                      <td className="px-3 py-1.5 text-slate-600 dark:text-slate-300">{tool.policy}</td>
                      <td className="px-3 py-1.5">
                        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold ${tool.runtime_enforcement ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'border-slate-300/40 bg-slate-100/60 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                          <Zap className="h-2.5 w-2.5" />{tool.runtime_enforcement ? 'LIVE' : 'OFF'}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-slate-500 dark:text-slate-400 max-w-[200px] truncate">{tool.description || '-'}</td>
                      <td className="px-3 py-1.5"><Link href="/chargeback?dimension=feature_tag" className="inline-flex items-center gap-0.5 text-emerald-600 hover:text-emerald-500 dark:text-emerald-400"><DollarSign className="h-2.5 w-2.5" />View</Link></td>
                      <td className="px-3 py-1.5">
                        <div className="flex justify-end gap-1">
                          <button onClick={() => startEditRegistry(tool)} className="rounded p-1 text-slate-400 hover:text-cyan-500 hover:bg-cyan-500/10"><Pencil className="h-3 w-3" /></button>
                          <button onClick={() => void handleDeleteRegistry(tool.tool_name)} className="rounded p-1 text-slate-400 hover:text-red-500 hover:bg-red-500/10"><Trash2 className="h-3 w-3" /></button>
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

      {/* ══════════ SEARCH TAB ══════════ */}
      {tab === 'search' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button
              onClick={() => { if (showSearchForm && !editingSearchId) resetSearchForm(); else { resetSearchForm(); setShowSearchForm(true) } }}
              className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 px-3 py-1.5 text-xs font-semibold text-white hover:from-violet-500 hover:to-purple-500 transition-all shadow-sm shadow-violet-500/20"
            >
              {showSearchForm ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
              {showSearchForm && !editingSearchId ? 'Cancel' : editingSearchId ? 'Editing' : 'Add Provider'}
            </button>
          </div>

          {showSearchForm && (
            <form onSubmit={handleSaveSearch} className="rounded-xl border border-violet-500/20 bg-violet-500/5 dark:bg-violet-950/20 p-3 space-y-2.5">
              <h3 className="text-xs font-bold text-violet-700 dark:text-violet-300">{editingSearchId ? 'Edit provider' : 'Create search provider'}</h3>
              <div className="grid gap-2 md:grid-cols-2">
                <input value={searchForm.name} onChange={(e) => setSearchForm((p) => ({ ...p, name: e.target.value }))} className={inputCls} placeholder="Provider name *" required />
                <input value={searchForm.tool_type} onChange={(e) => setSearchForm((p) => ({ ...p, tool_type: e.target.value }))} className={inputCls} placeholder="Tool type *" required />
                <input value={searchForm.endpoint_url} onChange={(e) => setSearchForm((p) => ({ ...p, endpoint_url: e.target.value }))} className={inputCls} placeholder="Endpoint URL" />
                <input value={searchForm.auth_type} onChange={(e) => setSearchForm((p) => ({ ...p, auth_type: e.target.value }))} className={inputCls} placeholder="Auth type" />
                <input value={searchForm.rate_limit_rpm} onChange={(e) => setSearchForm((p) => ({ ...p, rate_limit_rpm: e.target.value }))} className={inputCls} placeholder="Rate limit RPM" />
                <input value={searchForm.cost_per_query} onChange={(e) => setSearchForm((p) => ({ ...p, cost_per_query: e.target.value }))} className={inputCls} placeholder="Cost per query" />
                <div className="md:col-span-2"><input value={searchForm.description} onChange={(e) => setSearchForm((p) => ({ ...p, description: e.target.value }))} className={inputCls} placeholder="Description" /></div>
              </div>
              <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={searchForm.is_active} onChange={(e) => setSearchForm((p) => ({ ...p, is_active: e.target.checked }))} /> Active
              </label>
              <div className="flex gap-2">
                <button type="submit" disabled={saving} className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 disabled:opacity-50">{saving ? 'Saving...' : editingSearchId ? 'Save' : 'Create'}</button>
                <button type="button" onClick={resetSearchForm} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300">Cancel</button>
              </div>
            </form>
          )}

          <div className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-12"><RefreshCw className="h-4 w-4 animate-spin text-slate-400" /></div>
            ) : searchToolsList.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 gap-2">
                <Search className="h-6 w-6 text-slate-400 dark:text-slate-600" />
                <p className="text-xs text-slate-500">No search providers yet</p>
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead className="bg-slate-50/80 dark:bg-slate-800/60 border-b border-slate-200/60 dark:border-slate-700/60">
                  <tr>
                    <th className="px-3 py-1.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-500">Provider</th>
                    <th className="px-3 py-1.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-500">Type</th>
                    <th className="px-3 py-1.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-500">Queries</th>
                    <th className="px-3 py-1.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-500">Policies</th>
                    <th className="px-3 py-1.5 text-right text-[10px] font-bold uppercase tracking-wider text-slate-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100/80 dark:divide-slate-700/40">
                  {searchToolsList.map((tool) => (
                    <tr key={tool.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                      <td className="px-3 py-1.5">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{tool.name}</div>
                        <div className="text-[10px] text-slate-500">{tool.endpoint_url || 'managed'}</div>
                      </td>
                      <td className="px-3 py-1.5 text-slate-600 dark:text-slate-300">{tool.tool_type}</td>
                      <td className="px-3 py-1.5 font-mono text-slate-600 dark:text-slate-300">{tool.total_queries}</td>
                      <td className="px-3 py-1.5">
                        <button onClick={() => changeTab('policies')} className="text-violet-600 hover:text-violet-500 dark:text-violet-400 font-medium">{tool.policy_count} policies</button>
                      </td>
                      <td className="px-3 py-1.5">
                        <div className="flex justify-end gap-1">
                          <button onClick={() => startEditSearch(tool)} className="rounded p-1 text-slate-400 hover:text-violet-500 hover:bg-violet-500/10"><Pencil className="h-3 w-3" /></button>
                          <button onClick={() => void handleDeleteSearch(tool.id)} className="rounded p-1 text-slate-400 hover:text-red-500 hover:bg-red-500/10"><Trash2 className="h-3 w-3" /></button>
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

      {/* ══════════ POLICIES TAB ══════════ */}
      {tab === 'policies' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button
              onClick={showPolicyForm ? resetPolicyForm : () => { resetPolicyForm(); setShowPolicyForm(true) }}
              className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-amber-600 to-orange-600 px-3 py-1.5 text-xs font-semibold text-white hover:from-amber-500 hover:to-orange-500 transition-all shadow-sm shadow-amber-500/20"
            >
              {showPolicyForm ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
              {showPolicyForm ? 'Cancel' : 'Create Policy'}
            </button>
          </div>

          {showPolicyForm && (
            <form onSubmit={handleSavePolicy} className="rounded-xl border border-amber-500/20 bg-amber-500/5 dark:bg-amber-950/20 p-3 space-y-2.5">
              <h3 className="text-xs font-bold text-amber-700 dark:text-amber-300 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5" /> {editingPolicyId ? 'Edit Policy' : 'New Policy'}
              </h3>
              <div className="grid gap-2 md:grid-cols-3">
                <div className="flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Name *</label>
                  <input value={policyForm.name} onChange={(e) => setPolicyForm((p) => ({ ...p, name: e.target.value }))} required className={inputCls} />
                </div>
                <div className="flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Target Tool *</label>
                  {toolOptions.length > 0 ? (
                    <select value={policyForm.tool_name} onChange={(e) => setPolicyForm((p) => ({ ...p, tool_name: e.target.value }))} className={inputCls} required>
                      <option value="">-- Pick --</option><option value="*">* (All)</option>
                      {toolOptions.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  ) : <input value={policyForm.tool_name} onChange={(e) => setPolicyForm((p) => ({ ...p, tool_name: e.target.value }))} required className={inputCls} />}
                </div>
                <div className="flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Action *</label>
                  <select value={policyForm.action} onChange={(e) => setPolicyForm((p) => ({ ...p, action: e.target.value }))} className={inputCls}>
                    <option value="block">block</option><option value="require_approval">require_approval</option><option value="audit">audit</option><option value="allow">allow</option>
                  </select>
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-3">
                <div className="flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Scope Type</label>
                  <select value={policyForm.scope_type} onChange={(e) => setPolicyForm((p) => ({ ...p, scope_type: e.target.value, scope_id: '' }))} className={inputCls}>
                    <option value="workspace">workspace</option><option value="access_group">access_group</option><option value="search_tool">search_tool</option>
                  </select>
                </div>
                <div className="flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Scope Target</label>
                  {policyForm.scope_type === 'access_group' ? (
                    <select value={policyForm.scope_id} onChange={(e) => setPolicyForm((p) => ({ ...p, scope_id: e.target.value }))} className={inputCls}><option value="">-- All --</option>{accessGroups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select>
                  ) : policyForm.scope_type === 'search_tool' ? (
                    <select value={policyForm.scope_id} onChange={(e) => setPolicyForm((p) => ({ ...p, scope_id: e.target.value }))} className={inputCls}><option value="">-- Any --</option>{searchToolsList.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
                  ) : <input value={policyForm.scope_id} onChange={(e) => setPolicyForm((p) => ({ ...p, scope_id: e.target.value }))} className={inputCls} placeholder="Optional" />}
                </div>
                <div className="flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Priority</label>
                  <input type="number" value={policyForm.priority} onChange={(e) => setPolicyForm((p) => ({ ...p, priority: Number(e.target.value) }))} className={inputCls} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                <div className="flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Condition Type</label>
                  <select value={policyForm.condition_type} onChange={(e) => setPolicyForm((p) => ({ ...p, condition_type: e.target.value }))} className={inputCls}>
                    <option value="all">all</option><option value="risk_score_gte">risk_score_gte</option><option value="tool_type">tool_type</option><option value="end_user">end_user</option><option value="feature_tag">feature_tag</option><option value="context_equals">context_equals</option>
                  </select>
                </div>
                <div className="flex flex-col gap-0.5">
                  <label className="text-[10px] font-medium text-slate-500">Description</label>
                  <input value={policyForm.description} onChange={(e) => setPolicyForm((p) => ({ ...p, description: e.target.value }))} className={inputCls} placeholder="Why this rule exists" />
                </div>
              </div>
              <div className="flex flex-col gap-0.5">
                <label className="text-[10px] font-medium text-slate-500">Condition Config (JSON)</label>
                <textarea value={policyForm.condition_config_text} onChange={(e) => setPolicyForm((p) => ({ ...p, condition_config_text: e.target.value }))} className={`${inputCls} min-h-16 font-mono`} />
              </div>
              <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={policyForm.is_active} onChange={(e) => setPolicyForm((p) => ({ ...p, is_active: e.target.checked }))} /> Active
              </label>
              <div className="flex gap-2">
                <button type="submit" disabled={saving} className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-500 disabled:opacity-50">{saving ? 'Saving...' : editingPolicyId ? 'Save' : 'Create'}</button>
                <button type="button" onClick={resetPolicyForm} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300">Cancel</button>
              </div>
            </form>
          )}

          <div className="grid gap-3 lg:grid-cols-2">
            {/* Simulator */}
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 bg-white/50 dark:bg-slate-900/50 p-3 space-y-2.5">
              <h3 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                <Play className="h-3.5 w-3.5 text-cyan-500" /> Policy Simulator
              </h3>
              <form onSubmit={handleSimulate} className="space-y-2">
                <div className="grid gap-2 grid-cols-2">
                  <div className="flex flex-col gap-0.5">
                    <label className="text-[10px] font-medium text-slate-500">Tool Name</label>
                    <input value={simToolName} onChange={(e) => setSimToolName(e.target.value)} className={inputCls} />
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <label className="text-[10px] font-medium text-slate-500">Risk Score (0-100)</label>
                    <input type="number" min={0} max={100} value={simRiskScore} onChange={(e) => setSimRiskScore(Number(e.target.value))} className={inputCls} />
                  </div>
                </div>
                <button type="submit" disabled={simulating} className="rounded-lg bg-cyan-600 px-3 py-1.5 text-[10px] font-bold text-white hover:bg-cyan-500 disabled:opacity-50">
                  {simulating ? 'Running...' : 'Simulate'}
                </button>
              </form>
              {simResult && (
                <div className="rounded-lg border border-slate-700/60 bg-slate-950 p-2.5 font-mono text-[10px] text-slate-300 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Action:</span>
                    <span className={`font-bold uppercase ${simResult.final_action === 'block' ? 'text-red-400' : simResult.final_action === 'require_approval' ? 'text-amber-400' : simResult.final_action === 'audit' ? 'text-cyan-400' : 'text-emerald-400'}`}>{simResult.final_action}</span>
                  </div>
                  {simResult.matched_policy_names.length === 0 ? <p className="text-slate-500">No rules matched — default ALLOW.</p> : simResult.matched_policy_names.map((name, i) => (
                    <div key={`${name}-${i}`}>• {name} — <span className="text-slate-500">{simResult.reasons[i]}</span></div>
                  ))}
                </div>
              )}
            </div>

            {/* Policy Rules */}
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 bg-white/50 dark:bg-slate-900/50 p-3 space-y-2.5">
              <h3 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-amber-500" /> Active Rules ({policies.length})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50/60 dark:bg-slate-800/40 text-[10px] uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200/60 dark:border-slate-700/60">
                    <tr>
                      <th className="py-1.5 px-2 text-left">Policy</th>
                      <th className="py-1.5 px-2 text-left">Tool</th>
                      <th className="py-1.5 px-2 text-left">Action</th>
                      <th className="py-1.5 px-2 text-right">Ops</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100/60 dark:divide-slate-800/40">
                    {policies.map((p) => (
                      <tr key={p.id} className="hover:bg-slate-50/40 dark:hover:bg-slate-800/20">
                        <td className="py-1.5 px-2">
                          <div className="font-semibold text-slate-900 dark:text-white">{p.name}</div>
                          <div className="text-[10px] text-slate-500">{p.condition_type || 'all'} · pri {p.priority}</div>
                        </td>
                        <td className="py-1.5 px-2 font-mono text-cyan-600 dark:text-cyan-400">{p.tool_name}</td>
                        <td className="py-1.5 px-2">
                          <span className={`inline-block rounded-full border px-1.5 py-0.5 text-[10px] font-bold uppercase ${actionBadge[p.action] || 'bg-slate-100 text-slate-600'}`}>{p.action}</span>
                        </td>
                        <td className="py-1.5 px-2">
                          <div className="flex justify-end gap-1">
                            <button onClick={() => startEditPolicy(p)} className="rounded p-1 text-slate-400 hover:text-amber-500 hover:bg-amber-500/10"><Pencil className="h-3 w-3" /></button>
                            <button onClick={() => void handleDeletePolicy(p.id)} className="rounded p-1 text-slate-400 hover:text-red-500 hover:bg-red-500/10"><Trash2 className="h-3 w-3" /></button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {policies.length === 0 && !loading && (
                      <tr><td colSpan={4} className="py-6 text-center text-slate-400 text-[10px]">No policies yet.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Analytics */}
          {analytics && (
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 overflow-hidden">
              <div className="px-3 py-2 border-b border-slate-200/60 dark:border-slate-700/60 bg-slate-50/60 dark:bg-slate-800/40">
                <p className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5"><Activity className="h-3.5 w-3.5 text-cyan-500" /> Tool Telemetry</p>
              </div>
              <table className="w-full text-xs">
                <thead className="bg-slate-50/60 dark:bg-slate-800/40 text-[10px] uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200/60 dark:border-slate-700/60">
                  <tr>
                    <th className="px-3 py-1.5 text-left">Tool</th>
                    <th className="px-3 py-1.5 text-left">Total</th>
                    <th className="px-3 py-1.5 text-left">Allowed</th>
                    <th className="px-3 py-1.5 text-left">Denied</th>
                    <th className="px-3 py-1.5 text-right">Avg Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100/60 dark:divide-slate-800/40">
                  {analytics.items.map((item) => (
                    <tr key={item.tool_name} className="hover:bg-slate-50/40 dark:hover:bg-slate-800/20">
                      <td className="px-3 py-1.5 font-semibold text-slate-900 dark:text-white flex items-center gap-1"><Wrench className="h-3 w-3 text-cyan-500" />{item.tool_name}</td>
                      <td className="px-3 py-1.5 font-mono text-slate-600 dark:text-slate-300">{item.total_calls}</td>
                      <td className="px-3 py-1.5 font-mono text-emerald-600 dark:text-emerald-400">{item.allowed_calls}</td>
                      <td className="px-3 py-1.5 font-mono text-red-500 dark:text-red-400">{item.denied_calls}</td>
                      <td className="px-3 py-1.5 text-right font-mono text-slate-400">{item.avg_duration_ms != null ? `${num(item.avg_duration_ms).toFixed(1)}ms` : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ══════════ DRY RUN TAB ══════════ */}
      {tab === 'dry-run' && (
        <div className="space-y-3">
          <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 dark:bg-indigo-950/20 p-3">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/20 border border-indigo-500/30">
                <Shield className="h-3.5 w-3.5 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-xs font-bold text-slate-900 dark:text-white">Policy Dry Run</h2>
                <p className="text-[10px] text-slate-500">Test policy checks without active enforcement.</p>
              </div>
            </div>
          </div>

          <div className="flex gap-0.5 rounded-lg bg-slate-100/80 dark:bg-slate-800/50 p-0.5">
            {([
              { id: 'single' as const, label: 'Single Check', icon: Shield },
              { id: 'report' as const, label: 'Report', icon: FileText },
            ]).map((t) => (
              <button
                key={t.id}
                onClick={() => { setDryRunSub(t.id); if (t.id === 'report' && !report) void loadReport() }}
                className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                  dryRunSub === t.id ? 'bg-white dark:bg-slate-900 text-indigo-700 dark:text-indigo-300 shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-white'
                }`}
              >
                <t.icon className="h-3.5 w-3.5" />{t.label}
              </button>
            ))}
          </div>

          {dryRunSub === 'single' && (
            <>
              <form onSubmit={handleDryRun} className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 bg-white/50 dark:bg-slate-900/50 p-3 space-y-2.5">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Check Parameters</p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {dryRunFields.map((f) => (
                    <label key={f.key} className="block">
                      <span className="mb-0.5 block text-[10px] font-medium text-slate-500">{f.label}</span>
                      <input type="text" className={inputCls} placeholder={f.placeholder} value={dryRunForm[f.key]} onChange={(e) => setDryRunForm((p) => ({ ...p, [f.key]: e.target.value }))} />
                    </label>
                  ))}
                </div>
                <button type="submit" disabled={dryRunLoading} className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
                  {dryRunLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Shield className="h-3.5 w-3.5" />} Run Check
                </button>
              </form>

              {dryRunResult && (
                <div className="space-y-2">
                  <div className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 bg-white/50 dark:bg-slate-900/50 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        {dryRunResult.allowed ? <CheckCircle2 className="h-6 w-6 text-emerald-500" /> : <XCircle className="h-6 w-6 text-red-500" />}
                        <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-bold ${dryRunResult.allowed ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400'}`}>
                          {dryRunResult.allowed ? 'ALLOWED' : 'BLOCKED'}
                        </span>
                      </div>
                      <button onClick={() => { const pt = dryRunForm.feature_tag.trim() || dryRunForm.tool_name.trim() || 'default'; void handlePromote(pt) }} disabled={promoting} className="inline-flex items-center gap-1 rounded-lg bg-amber-600 px-2.5 py-1 text-[10px] font-bold text-white hover:bg-amber-500 disabled:opacity-50">
                        {promoting ? <Loader2 className="h-3 w-3 animate-spin" /> : <ArrowUpCircle className="h-3 w-3" />} Promote
                      </button>
                    </div>
                    {dryRunResult.reasons.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {dryRunResult.reasons.map((r, i) => (
                          <span key={`${r}-${i}`} className="rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-0.5 text-[10px] font-medium text-slate-700 dark:text-slate-300">{r}</span>
                        ))}
                      </div>
                    )}
                  </div>

                  {dryRunResult.detail && (
                    <div className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 bg-white/50 dark:bg-slate-900/50 p-3 space-y-2">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Detail Breakdown</p>
                      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                        {detailLabels.map(({ key, label, good }) => {
                          const raw = (dryRunResult.detail as unknown as Record<string, unknown>)?.[key]
                          const display = formatValue(raw)
                          const isNull = raw === null || raw === undefined
                          const clr = isNull ? 'text-slate-400' : good(raw) ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                          return (
                            <div key={key} className="flex items-baseline justify-between rounded-lg bg-slate-50/60 dark:bg-slate-800/40 px-2.5 py-1.5">
                              <span className="text-[10px] text-slate-500">{label}</span>
                              <span className={`text-xs font-semibold ${clr}`}>{display}</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  <div className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 bg-white/50 dark:bg-slate-900/50 p-3 flex items-center justify-between">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Audit Trail</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">View dry-run decisions in the audit log.</p>
                    </div>
                    <Link href="/audit?action=policy.dry_run" className="inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-1 text-[10px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
                      <ExternalLink className="h-3 w-3" /> Audit Log
                    </Link>
                  </div>
                </div>
              )}
            </>
          )}

          {dryRunSub === 'report' && (
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-700/60 bg-white/50 dark:bg-slate-900/50 p-3 space-y-2.5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Dry-Run Report</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Recent shadow-evaluation decisions.</p>
                </div>
                <button onClick={() => void loadReport()} disabled={reportLoading} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-1 text-[10px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50">
                  {reportLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileText className="h-3 w-3" />} Refresh
                </button>
              </div>

              {!report ? (
                <p className="text-xs text-slate-500">Loading report...</p>
              ) : (
                <>
                  <div className="grid gap-2 grid-cols-4">
                    {[
                      { label: 'Checked', value: report.total_checked, cls: 'text-slate-900 dark:text-white' },
                      { label: 'Would Block', value: report.would_block, cls: 'text-red-600 dark:text-red-400' },
                      { label: 'Would Allow', value: report.would_allow, cls: 'text-emerald-600 dark:text-emerald-400' },
                      { label: 'Would Reroute', value: report.would_reroute, cls: 'text-amber-600 dark:text-amber-400' },
                    ].map((s) => (
                      <div key={s.label} className="rounded-lg border border-slate-200/60 dark:border-slate-700/60 px-2.5 py-1.5">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{s.label}</p>
                        <p className={`text-lg font-bold ${s.cls}`}>{s.value}</p>
                      </div>
                    ))}
                  </div>

                  <div className="rounded-lg border border-slate-200/60 dark:border-slate-700/60 overflow-hidden">
                    <table className="w-full text-xs">
                      <thead className="bg-slate-50/60 dark:bg-slate-800/40 text-[10px] uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200/60 dark:border-slate-700/60">
                        <tr>
                          <th className="px-2.5 py-1.5 text-left">Request</th>
                          <th className="px-2.5 py-1.5 text-left">Action</th>
                          <th className="px-2.5 py-1.5 text-left">Model</th>
                          <th className="px-2.5 py-1.5 text-left">Reason</th>
                          <th className="px-2.5 py-1.5 text-right">Promote</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100/60 dark:divide-slate-800/40">
                        {report.items.map((item) => (
                          <tr key={item.request_id} className="hover:bg-slate-50/40 dark:hover:bg-slate-800/20">
                            <td className="px-2.5 py-1.5 font-mono text-[10px] text-slate-500">{item.request_id}</td>
                            <td className="px-2.5 py-1.5"><span className={`rounded-full border px-1.5 py-0.5 text-[10px] font-bold ${actionBadge[item.action] ?? 'bg-slate-100 text-slate-600'}`}>{item.action}</span></td>
                            <td className="px-2.5 py-1.5 text-slate-600 dark:text-slate-300">{item.model ?? '-'}</td>
                            <td className="px-2.5 py-1.5 text-slate-600 dark:text-slate-300">{item.reasons.join(', ') || '-'}</td>
                            <td className="px-2.5 py-1.5 text-right">
                              <button onClick={() => void handleReportPromote(item.action)} disabled={reportPromoting} className="rounded-lg bg-amber-600 px-2 py-0.5 text-[10px] font-bold text-white hover:bg-amber-500 disabled:opacity-50">Promote</button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Quick Nav Footer ── */}
      <div className="flex flex-wrap gap-1.5 pt-1">
        {[
          { label: 'Gateway', href: '/gateway' },
          { label: 'Guardrails', href: '/guardrails' },
          { label: 'Runs', href: '/runs' },
          { label: 'Approvals', href: '/approvals' },
          { label: 'Security', href: '/security' },
          { label: 'Audit Log', href: '/audit' },
          { label: 'Data Capture', href: '/data-capture' },
          { label: 'MCP Servers', href: '/mcp' },
          { label: 'Budgets', href: '/budgets' },
          { label: 'Governance Pack', href: '/governance-pack' },
        ].map((link) => (
          <Link key={link.href} href={link.href} className="rounded-md border border-cyan-500/20 bg-cyan-500/5 dark:bg-cyan-950/20 px-2 py-0.5 text-[10px] font-medium text-cyan-700 dark:text-cyan-400 hover:bg-cyan-500/10 transition-colors">
            {link.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
