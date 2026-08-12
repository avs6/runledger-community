'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  ShieldCheck,
  Plus,
  Trash2,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Layers,
  FolderKanban,
  Wrench,
  SlidersHorizontal,
} from 'lucide-react'
import {
  getToolPolicies,
  createToolPolicy,
  deleteToolPolicy,
  simulateToolPolicy,
  getToolPolicyAnalytics,
  getAccessGroups,
  listProjects,
  listMcpTools,
} from '@/lib/api'
import type {
  ToolPolicyResponse,
  ToolPolicySimulationResponse,
  ToolUsageAnalyticsResponse,
  AccessGroupResponse,
  ProjectResponse,
  McpToolListItem,
} from '@/types/api'

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

export default function ToolPoliciesPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey

  const [policies, setPolicies] = useState<ToolPolicyResponse[]>([])
  const [analytics, setAnalytics] = useState<ToolUsageAnalyticsResponse | null>(null)
  const [accessGroups, setAccessGroups] = useState<AccessGroupResponse[]>([])
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [discoveredTools, setDiscoveredTools] = useState<McpToolListItem[]>([])
  const [loading, setLoading] = useState(true)

  // Creation State
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [policyName, setPolicyName] = useState('')
  const [description, setDescription] = useState('')
  const [toolName, setToolName] = useState('')
  const [action, setAction] = useState('block')
  const [scopeType, setScopeType] = useState('access_group')
  const [scopeId, setScopeId] = useState('')
  const [priority, setPriority] = useState<number>(100)
  const [creating, setCreating] = useState(false)

  // Simulation State
  const [simToolName, setSimToolName] = useState('query')
  const [simRiskScore, setSimRiskScore] = useState(25)
  const [simResult, setSimResult] = useState<ToolPolicySimulationResponse | null>(null)
  const [simulating, setSimulating] = useState(false)

  const loadData = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [polRes, anaRes, agRes, projRes, toolsRes] = await Promise.all([
        getToolPolicies(apiKey).catch(() => ({ items: [], total: 0 })),
        getToolPolicyAnalytics(apiKey, 250).catch(() => null),
        getAccessGroups(apiKey).catch(() => ({ items: [], total: 0 })),
        listProjects(apiKey).catch(() => ({ items: [] })),
        listMcpTools(apiKey).catch(() => ({ items: [], total: 0 })),
      ])
      setPolicies(polRes.items || [])
      setAnalytics(anaRes)
      setAccessGroups(agRes.items || [])
      setProjects(projRes.items || [])
      setDiscoveredTools(toolsRes.items || [])
    } catch (err) {
      console.error(err)
      toast.error('Failed to load tool policies data')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleCreatePolicy(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !policyName.trim() || !toolName.trim()) return
    setCreating(true)
    try {
      await createToolPolicy(apiKey, {
        name: policyName.trim(),
        description: description.trim() || undefined,
        tool_name: toolName.trim(),
        action,
        scope_type: scopeType,
        scope_id: scopeId.trim() || undefined,
        priority,
      })
      toast.success(`Tool Policy '${policyName}' created successfully`)
      setPolicyName('')
      setDescription('')
      setToolName('')
      setAction('block')
      setScopeId('')
      setShowCreateForm(false)
      loadData()
    } catch (err) {
      toast.error('Failed to create tool policy')
    } finally {
      setCreating(false)
    }
  }

  async function handleDeletePolicy(id: string) {
    if (!apiKey) return
    try {
      await deleteToolPolicy(apiKey, id)
      toast.success('Policy deleted')
      loadData()
    } catch (err) {
      toast.error('Failed to delete policy')
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
    } catch (err) {
      toast.error('Failed to run policy simulation')
    } finally {
      setSimulating(false)
    }
  }

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between dark:border-slate-800 dark:bg-slate-900/80">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-blue-700 dark:text-blue-400">
            Runtime Tool Governance & Safety Engine
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 dark:text-white">
            Tool Policies & Execution Rules
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Define allow/deny/approval rules for MCP tools scoped by Access Groups, Projects, and Workspaces.
          </p>
        </div>

        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition"
        >
          <Plus className="h-4 w-4" /> {showCreateForm ? 'Cancel' : 'Create Tool Policy'}
        </button>
      </div>

      {/* Policy Creation Form */}
      {showCreateForm && (
        <form
          onSubmit={handleCreatePolicy}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4"
        >
          <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-blue-600" /> New Tool Policy Rule
          </h2>

          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Policy Name *
              </label>
              <input
                value={policyName}
                onChange={(e) => setPolicyName(e.target.value)}
                required
                placeholder="e.g. Block SQL Mutations for Support"
                className={inputCls}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Target Tool Name *
              </label>
              {discoveredTools.length > 0 ? (
                <select
                  value={toolName}
                  onChange={(e) => setToolName(e.target.value)}
                  required
                  className={inputCls}
                >
                  <option value="">-- Pick Discovered Tool --</option>
                  <option value="*">* (All Discovered Tools)</option>
                  {discoveredTools.map((t) => (
                    <option key={`${t.server_id}-${t.tool_name}`} value={t.tool_name}>
                      {t.tool_name} ({t.server_name || 'MCP'})
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={toolName}
                  onChange={(e) => setToolName(e.target.value)}
                  required
                  placeholder="query, delete_record, create_issue, or *"
                  className={inputCls}
                />
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Policy Action *
              </label>
              <select
                value={action}
                onChange={(e) => setAction(e.target.value)}
                className={inputCls}
              >
                <option value="block">BLOCK (Deny Tool Execution)</option>
                <option value="allow">ALLOW (Explicitly Permit Tool)</option>
                <option value="require_approval">REQUIRE APPROVAL (Manager Review)</option>
              </select>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Enforcement Scope Type
              </label>
              <select
                value={scopeType}
                onChange={(e) => setScopeType(e.target.value)}
                className={inputCls}
              >
                <option value="access_group">Access Group Policy</option>
                <option value="project">Project Workload Policy</option>
                <option value="workspace">Workspace Wide Policy</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Target Scope Boundary
              </label>
              {scopeType === 'access_group' && accessGroups.length > 0 ? (
                <select
                  value={scopeId}
                  onChange={(e) => setScopeId(e.target.value)}
                  className={inputCls}
                >
                  <option value="">-- All Access Groups --</option>
                  {accessGroups.map((ag) => (
                    <option key={ag.id} value={ag.id}>
                      Access Group: {ag.name}
                    </option>
                  ))}
                </select>
              ) : scopeType === 'project' && projects.length > 0 ? (
                <select
                  value={scopeId}
                  onChange={(e) => setScopeId(e.target.value)}
                  className={inputCls}
                >
                  <option value="">-- All Projects --</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      Project: {p.name}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={scopeId}
                  onChange={(e) => setScopeId(e.target.value)}
                  placeholder="Workspace/Project UUID..."
                  className={inputCls}
                />
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Description / Rationale
              </label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Reason for safety policy..."
                className={inputCls}
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={creating || !policyName.trim() || !toolName.trim()}
              className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {creating ? 'Saving Policy...' : 'Save Policy Rule'}
            </button>
          </div>
        </form>
      )}

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-400 font-semibold">Active Policies</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">{policies.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-400 font-semibold">Unique Tools Tracked</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">
            {analytics?.unique_tools || discoveredTools.length}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-400 font-semibold">Total Tool Calls Analyzed</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">
            {analytics?.total_calls || 0}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-400 font-semibold">Discovered MCP Tools</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">
            {discoveredTools.length}
          </p>
        </div>
      </div>

      {/* Main Grid: Policy Simulation & Active Policies */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Simulation Section */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Play className="h-4 w-4 text-blue-600" /> Interactive Policy Simulator
          </h2>
          <p className="text-xs text-slate-500">
            Test arbitrary tool execution payloads against registered policies and inspect rule matching.
          </p>

          <form onSubmit={handleSimulate} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Test Tool Name
              </label>
              <input
                value={simToolName}
                onChange={(e) => setSimToolName(e.target.value)}
                placeholder="query, brave_web_search, delete_record"
                className={inputCls}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Simulated Risk Score (0-100)
              </label>
              <input
                type="number"
                value={simRiskScore}
                onChange={(e) => setSimRiskScore(Number(e.target.value))}
                min={0}
                max={100}
                className={inputCls}
              />
            </div>

            <button
              type="submit"
              disabled={simulating}
              className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {simulating ? 'Simulating...' : 'Run Simulation'}
            </button>
          </form>

          {simResult && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-950 p-4 font-mono text-xs text-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Final Action:</span>
                <span
                  className={`font-bold uppercase ${
                    simResult.final_action === 'block'
                      ? 'text-red-400'
                      : simResult.final_action === 'require_approval'
                      ? 'text-amber-400'
                      : 'text-emerald-400'
                  }`}
                >
                  {simResult.final_action}
                </span>
              </div>
              <div>
                <p className="text-slate-400 font-semibold mb-1">Matched Policy Rules:</p>
                {simResult.matched_policy_names.length === 0 ? (
                  <p className="text-slate-500">No specific blocking rules matched. Default ALLOW.</p>
                ) : (
                  simResult.matched_policy_names.map((name, i) => (
                    <div key={name} className="text-slate-300">
                      • {name} — <span className="text-slate-400">{simResult.reasons[i]}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </section>

        {/* Active Policies Table */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-blue-600" /> Active Policy Rules ({policies.length})
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50/80 dark:bg-slate-950/50 text-xs uppercase tracking-wider text-slate-500 font-semibold border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-2.5 px-3 text-left">Policy Name</th>
                  <th className="py-2.5 px-3 text-left">Tool</th>
                  <th className="py-2.5 px-3 text-left">Action</th>
                  <th className="py-2.5 px-3 text-left">Scope</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {policies.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-950/40">
                    <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-white">
                      {p.name}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-xs text-blue-600 dark:text-blue-400">
                      {p.tool_name}
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                          p.action === 'block'
                            ? 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
                            : p.action === 'require_approval'
                            ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                            : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                        }`}
                      >
                        {p.action}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-xs text-slate-500">
                      {p.scope_type || 'workspace'}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => handleDeletePolicy(p.id)}
                        className="text-xs text-red-500 hover:text-red-700 font-medium"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
                {policies.length === 0 && !loading && (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-400 text-xs">
                      No tool policy rules created yet. Click &quot;Create Tool Policy&quot; above to add safety rules.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* Analytics Breakdown */}
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
                    {item.avg_duration_ms != null ? `${item.avg_duration_ms.toFixed(1)} ms` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}
