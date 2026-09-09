'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import { ScrollText, Plus, Trash2, ShieldCheck, X, Zap, Clock, CheckCircle2, XCircle, Ban, Pencil } from 'lucide-react'
import {
  getApprovalSummary,
  getApprovalsAlertFinopsPosture,
  getGovernanceInternalPosture,
  getApprovalsRuntimePosture,
  getExceptionWorkflowsOrgPosture,
  getExceptionWorkflowsGatewayPosture,
  listApprovals,
  createApproval,
  approveApproval,
  denyApproval,
  cancelApproval,
  listAutoApprovalPolicies,
  createAutoApprovalPolicy,
  updateAutoApprovalPolicy,
  deleteAutoApprovalPolicy,
} from '@/lib/api'
import { useRole } from '@/components/rbac/useRole'
import { num } from '@/lib/utils'
import type {
  ApprovalResponse,
  ApprovalSummary,
  ApprovalRequestType,
  ApprovalsAlertFinopsPosture,
  ExceptionWorkflowsOrgPosture,
  ExceptionWorkflowsGatewayPosture,
  GovernanceInternalPosture,
  ApprovalsRuntimePosture,
  AutoApprovalPolicy,
} from '@/types/api'

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500'

const REQUEST_TYPE_LABELS: Record<ApprovalRequestType, string> = {
  budget_increase: 'Budget Increase',
  prompt_promote: 'Prompt → Production',
  tool_allow: 'Allow Privileged Tool',
  capture_policy_full: 'Full Payload Capture',
  shadow_routing: 'Shadow Routing',
  premium_model_use: 'Use Premium Model',
  external_mcp_tool: 'External MCP Tool',
  long_agent_session: 'Long Agent Session',
  sensitive_export: 'Sensitive Data Export',
  route_policy_change: 'Route Policy Change',
}

const STATUS_CHIP: Record<string, { cls: string; icon: typeof Clock }> = {
  pending: { cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400', icon: Clock },
  approved: { cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400', icon: CheckCircle2 },
  denied: { cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', icon: XCircle },
  cancelled: { cls: 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400', icon: Ban },
}

const REQUEST_TYPES: ApprovalRequestType[] = [
  'budget_increase', 'prompt_promote', 'tool_allow', 'capture_policy_full',
  'shadow_routing', 'premium_model_use', 'external_mcp_tool', 'long_agent_session',
  'sensitive_export', 'route_policy_change',
]

type Tab = 'queue' | 'policies'

export default function ApprovalsPage() {
  const { data: session } = useSession()
  const { isWorkspaceAdmin } = useRole()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const [tab, setTab] = useState<Tab>('queue')
  const [summary, setSummary] = useState<ApprovalSummary | null>(null)
  const [approvals, setApprovals] = useState<ApprovalResponse[]>([])
  const [finopsPosture, setFinopsPosture] = useState<ApprovalsAlertFinopsPosture | null>(null)
  const [orgPosture, setOrgPosture] = useState<ExceptionWorkflowsOrgPosture | null>(null)
  const [gatewayPosture, setGatewayPosture] = useState<ExceptionWorkflowsGatewayPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<ApprovalsRuntimePosture | null>(null)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState<string>('pending')
  const [loading, setLoading] = useState(true)

  const [showCreate, setShowCreate] = useState(false)
  const [createType, setCreateType] = useState<ApprovalRequestType>('budget_increase')
  const [createReason, setCreateReason] = useState('')
  const [createLoading, setCreateLoading] = useState(false)

  const [deciding, setDeciding] = useState<{ id: string; action: 'approve' | 'deny' } | null>(null)
  const [decisionNote, setDecisionNote] = useState('')

  const [autoPolicies, setAutoPolicies] = useState<AutoApprovalPolicy[]>([])
  const [loadingPolicies, setLoadingPolicies] = useState(false)
  const [showPolicyForm, setShowPolicyForm] = useState(false)
  const [policyType, setPolicyType] = useState<ApprovalRequestType>('budget_increase')
  const [policyCondition, setPolicyCondition] = useState('')
  const [creatingPolicy, setCreatingPolicy] = useState(false)
  const [editingPolicyId, setEditingPolicyId] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    if (!apiKey || !isWorkspaceAdmin) return
    setLoading(true)
    try {
      const [s, list, posture, orgP, gwP, govInt, rtP] = await Promise.all([
        getApprovalSummary(apiKey),
        listApprovals(apiKey, { status: statusFilter || undefined, limit: 100 }),
        getApprovalsAlertFinopsPosture(apiKey).catch(() => null),
        getExceptionWorkflowsOrgPosture(apiKey).catch(() => null),
        getExceptionWorkflowsGatewayPosture(apiKey).catch(() => null),
        getGovernanceInternalPosture(apiKey).catch(() => null),
        getApprovalsRuntimePosture(apiKey).catch(() => null),
      ])
      setSummary(s)
      setApprovals(list.items)
      setTotal(list.total)
      setFinopsPosture(posture)
      setOrgPosture(orgP)
      setGatewayPosture(gwP)
      setGovInternal(govInt)
      setRuntimePosture(rtP)
    } catch {
      toast.error('Failed to load approvals')
    } finally {
      setLoading(false)
    }
  }, [apiKey, statusFilter, isWorkspaceAdmin])

  useEffect(() => { loadData() }, [loadData])

  const loadPolicies = useCallback(async () => {
    if (!apiKey || !isWorkspaceAdmin) return
    setLoadingPolicies(true)
    try {
      const res = await listAutoApprovalPolicies(apiKey)
      setAutoPolicies(res.items)
    } catch {
      toast.error('Failed to load auto-approval policies')
    } finally {
      setLoadingPolicies(false)
    }
  }, [apiKey, isWorkspaceAdmin])

  useEffect(() => { loadPolicies() }, [loadPolicies])

  const handleCreate = async () => {
    if (!apiKey || !isWorkspaceAdmin) return
    setCreateLoading(true)
    try {
      await createApproval(apiKey, { request_type: createType, reason: createReason || undefined })
      toast.success('Approval request submitted')
      setShowCreate(false)
      setCreateReason('')
      loadData()
    } catch {
      toast.error('Failed to create approval request')
    } finally {
      setCreateLoading(false)
    }
  }

  const handleDecide = async () => {
    if (!apiKey || !deciding || !isWorkspaceAdmin) return
    try {
      if (deciding.action === 'approve') {
        await approveApproval(apiKey, deciding.id, decisionNote || undefined)
        toast.success('Approved')
      } else {
        await denyApproval(apiKey, deciding.id, decisionNote || undefined)
        toast.success('Denied')
      }
      setDeciding(null)
      setDecisionNote('')
      loadData()
    } catch {
      toast.error('Failed to record decision')
    }
  }

  const handleCancel = async (id: string) => {
    if (!apiKey || !isWorkspaceAdmin) return
    try {
      await cancelApproval(apiKey, id)
      toast.success('Approval cancelled')
      loadData()
    } catch {
      toast.error('Failed to cancel approval')
    }
  }

  const handleCreatePolicy = async () => {
    if (!apiKey || !policyCondition.trim()) return
    setCreatingPolicy(true)
    try {
      if (editingPolicyId) {
        await updateAutoApprovalPolicy(apiKey, editingPolicyId, { request_type: policyType, condition: policyCondition.trim() })
        toast.success('Auto-approval policy updated')
      } else {
        await createAutoApprovalPolicy(apiKey, { request_type: policyType, condition: policyCondition.trim() })
        toast.success('Auto-approval policy created')
      }
      setShowPolicyForm(false)
      setEditingPolicyId(null)
      setPolicyType('budget_increase')
      setPolicyCondition('')
      loadPolicies()
    } catch {
      toast.error(`Failed to ${editingPolicyId ? 'update' : 'create'} policy`)
    } finally {
      setCreatingPolicy(false)
    }
  }

  const handleEditPolicy = (policy: AutoApprovalPolicy) => {
    setEditingPolicyId(policy.id)
    setShowPolicyForm(true)
    setPolicyType(policy.request_type)
    setPolicyCondition(policy.condition)
  }

  const handleDeletePolicy = async (id: string) => {
    if (!apiKey) return
    try {
      await deleteAutoApprovalPolicy(apiKey, id)
      toast.success('Policy deleted')
      loadPolicies()
    } catch {
      toast.error('Failed to delete policy')
    }
  }

  if (!isWorkspaceAdmin) {
    return (
      <div className="p-8">
        <h1 className="text-lg font-bold text-slate-900 dark:text-white">Approvals</h1>
        <p className="mt-2 text-xs text-slate-500">Approvals require workspace-admin access.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4">
      {/* Hero header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950 to-violet-950 p-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(99,102,241,0.15),transparent_60%)]" />
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/20 ring-1 ring-indigo-400/30">
              <ShieldCheck className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Governance Approvals</h1>
              <p className="text-xs text-indigo-200/70">Exception workflows for sensitive actions — budget, deploy, export &amp; more</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/audit?action=approval" className="flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-medium text-white/80 ring-1 ring-white/10 hover:bg-white/20">
              <ScrollText className="h-3.5 w-3.5" /> Audit Trail
            </Link>
            <button onClick={() => setShowCreate(true)} className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:from-indigo-400 hover:to-violet-400">
              Request Approval
            </button>
          </div>
        </div>

        {/* Summary KPI strip */}
        {summary && (
          <div className="relative mt-4 grid grid-cols-4 gap-2">
            {(['pending', 'approved', 'denied', 'cancelled'] as const).map((s) => {
              const chip = STATUS_CHIP[s]
              const Icon = chip.icon
              return (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s === statusFilter ? '' : s)}
                  className={`rounded-lg px-3 py-2 text-left transition-all ${
                    statusFilter === s ? 'bg-white/15 ring-1 ring-white/30' : 'bg-white/5 ring-1 ring-white/10 hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    <Icon className="h-3.5 w-3.5 text-slate-400" />
                    <span className="text-xl font-bold text-white">{summary[s]}</span>
                  </div>
                  <p className="mt-0.5 text-[10px] capitalize text-slate-400">{s}</p>
                </button>
              )
            })}
          </div>
        )}

        {/* Posture chips */}
        <div className="relative mt-3 flex flex-wrap gap-1.5">
          {finopsPosture && (
            <>
              <span className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] text-slate-300 ring-1 ring-white/10">
                <span className="font-semibold text-white">{finopsPosture.budget_context.total_budgets}</span> budgets
              </span>
              <span className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] text-slate-300 ring-1 ring-white/10">
                <span className="font-semibold text-white">{finopsPosture.budget_context.breach_count_30d}</span> breaches 30d
              </span>
              <span className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] text-slate-300 ring-1 ring-white/10">
                <span className="font-semibold text-white">{finopsPosture.alert_context.budget_alert_rules}</span> alert rules
              </span>
            </>
          )}
          {orgPosture && (
            <>
              <span className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] text-slate-300 ring-1 ring-white/10">
                <span className="font-semibold text-white">{orgPosture.user_context.total_users}</span> users
              </span>
              <span className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] text-slate-300 ring-1 ring-white/10">
                <span className="font-semibold text-white">{orgPosture.access_group_context.total_groups}</span> groups
              </span>
            </>
          )}
          {runtimePosture && (
            <>
              <span className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] text-slate-300 ring-1 ring-white/10">
                <span className="font-semibold text-white">{runtimePosture.observe_evidence.runs_30d}</span> runs 30d
              </span>
              <span className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] text-slate-300 ring-1 ring-white/10">
                <span className="font-semibold text-white">{runtimePosture.gateway_escalation.guardrail_rules}</span> guardrails
              </span>
            </>
          )}
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800/80">
        {[
          { key: 'queue' as Tab, label: 'Approval Queue', icon: ShieldCheck },
          { key: 'policies' as Tab, label: 'Auto-Approval Policies', icon: Zap },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === key
                ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Queue tab */}
      {tab === 'queue' && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900 overflow-hidden">
          <div className="flex items-center gap-3 border-b border-slate-200 px-4 py-2.5 dark:border-slate-700">
            <h2 className="flex-1 text-xs font-bold uppercase tracking-wider text-slate-500">
              {statusFilter ? `${statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)} Approvals` : 'All Approvals'}
              {!loading && <span className="ml-1 font-normal text-slate-400">({total})</span>}
            </h2>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="denied">Denied</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          {loading ? (
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="animate-pulse px-4 py-3">
                  <div className="mb-1.5 h-3 w-1/3 rounded bg-slate-100 dark:bg-slate-700" />
                  <div className="h-2.5 w-1/2 rounded bg-slate-100 dark:bg-slate-700" />
                </div>
              ))}
            </div>
          ) : approvals.length === 0 ? (
            <div className="px-4 py-10 text-center text-xs text-slate-400">No approvals found.</div>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {approvals.map(approval => {
                const filteredEntries = Object.entries(approval.request).filter(([k]) => k !== '_reason')
                const requestContextStr: string | null = filteredEntries.length > 0 ? JSON.stringify(Object.fromEntries(filteredEntries)) : null
                const reasonStr = approval.request._reason != null ? String(approval.request._reason) : null
                const chip = STATUS_CHIP[approval.status] ?? STATUS_CHIP.cancelled
                const StatusIcon = chip.icon
                return (
                  <div key={approval.id} className="px-4 py-3 hover:bg-indigo-50/30 dark:hover:bg-indigo-950/10">
                    <div className="flex items-start gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-xs font-semibold text-slate-900 dark:text-white">
                            {REQUEST_TYPE_LABELS[approval.request_type] ?? approval.request_type}
                          </span>
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${chip.cls}`}>
                            <StatusIcon className="h-2.5 w-2.5" />
                            {approval.status}
                          </span>
                        </div>
                        <div className="mt-1 space-y-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                          {approval.requested_by && <div>By: <span className="font-mono">{approval.requested_by}</span></div>}
                          <div>
                            {new Date(approval.created_at).toLocaleString()}
                            {approval.decided_at && <> &rarr; {new Date(approval.decided_at).toLocaleString()}</>}
                          </div>
                          {approval.decided_by && <div>Decided by: <span className="font-mono">{approval.decided_by}</span></div>}
                          {approval.decision_note && <div className="italic text-slate-400">&ldquo;{approval.decision_note}&rdquo;</div>}
                          {requestContextStr && (
                            <div className="mt-1 max-w-lg truncate rounded-md bg-slate-50 px-2 py-1 font-mono text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-400">{requestContextStr}</div>
                          )}
                          {reasonStr && <div>Reason: {reasonStr}</div>}
                        </div>
                      </div>
                      {approval.status === 'pending' && (
                        <div className="flex shrink-0 gap-1.5">
                          <button onClick={() => { setDeciding({ id: approval.id, action: 'approve' }); setDecisionNote('') }} className="rounded-md bg-emerald-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-emerald-500">Approve</button>
                          <button onClick={() => { setDeciding({ id: approval.id, action: 'deny' }); setDecisionNote('') }} className="rounded-md bg-red-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-red-500">Deny</button>
                          <button onClick={() => handleCancel(approval.id)} className="rounded-md border border-slate-200 px-2.5 py-1 text-[10px] text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800">Cancel</button>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Auto-Approval Policies tab */}
      {tab === 'policies' && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-indigo-500" />
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Auto-Approval Policies</p>
              </div>
              <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Automatically approve requests matching specific conditions.</p>
            </div>
            <button
              onClick={() => {
                if (showPolicyForm) { setShowPolicyForm(false); setEditingPolicyId(null); setPolicyType('budget_increase'); setPolicyCondition('') }
                else setShowPolicyForm(true)
              }}
              className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:from-indigo-500 hover:to-violet-500"
            >
              {showPolicyForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              {showPolicyForm ? 'Cancel' : 'Add Policy'}
            </button>
          </div>

          {showPolicyForm && (
            <div className="mb-4 grid gap-2 rounded-lg border border-indigo-200 bg-indigo-50/40 p-3 dark:border-indigo-800 dark:bg-indigo-950/20 md:grid-cols-3">
              <label className="text-xs">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Request Type</span>
                <select value={policyType} onChange={(e) => setPolicyType(e.target.value as ApprovalRequestType)} className={inputCls}>
                  {REQUEST_TYPES.map(t => <option key={t} value={t}>{REQUEST_TYPE_LABELS[t]}</option>)}
                </select>
              </label>
              <label className="text-xs">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Condition</span>
                <input type="text" placeholder='e.g. workspace:engineering' value={policyCondition} onChange={(e) => setPolicyCondition(e.target.value)} className={inputCls} />
              </label>
              <div className="flex items-end">
                <button onClick={handleCreatePolicy} disabled={creatingPolicy} className="rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-1.5 text-xs font-semibold text-white hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50">
                  {creatingPolicy ? 'Saving...' : editingPolicyId ? 'Save' : 'Create'}
                </button>
              </div>
            </div>
          )}

          {loadingPolicies ? (
            <p className="text-xs text-slate-400">Loading...</p>
          ) : autoPolicies.length === 0 ? (
            <p className="text-xs text-slate-400">No auto-approval policies configured.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="px-3 py-2 font-medium text-slate-500">Request Type</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Condition</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Created By</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Created</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {autoPolicies.map((p) => (
                    <tr key={p.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-indigo-50/30 dark:hover:bg-indigo-950/10">
                      <td className="px-3 py-2 font-medium text-slate-700 dark:text-slate-200">{REQUEST_TYPE_LABELS[p.request_type] ?? p.request_type}</td>
                      <td className="px-3 py-2 font-mono text-[11px] text-slate-500">{p.condition}</td>
                      <td className="px-3 py-2 text-[11px] text-slate-500">{p.created_by ?? '—'}</td>
                      <td className="px-3 py-2 text-[11px] text-slate-500">{new Date(p.created_at).toLocaleDateString()}</td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={() => handleEditPolicy(p)} className="rounded-md border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
                            <Pencil className="h-3 w-3" />
                          </button>
                          <button onClick={() => handleDeletePolicy(p.id)} className="rounded-md border border-red-200 p-1.5 text-red-500 hover:bg-red-50 dark:border-red-900/40 dark:hover:bg-red-950/30">
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Create approval modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md space-y-3 rounded-xl bg-white p-5 shadow-xl dark:bg-slate-900">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Request Approval</h3>
            <div className="space-y-2">
              <label className="block text-[10px] font-medium text-slate-500">Request Type</label>
              <select value={createType} onChange={e => setCreateType(e.target.value as ApprovalRequestType)} className={inputCls}>
                {REQUEST_TYPES.map(t => <option key={t} value={t}>{REQUEST_TYPE_LABELS[t]}</option>)}
              </select>
              <label className="block text-[10px] font-medium text-slate-500">Reason (optional)</label>
              <textarea value={createReason} onChange={e => setCreateReason(e.target.value)} placeholder="Why is this change needed?" rows={3} className={`resize-none ${inputCls}`} />
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button onClick={() => setShowCreate(false)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">Cancel</button>
              <button onClick={handleCreate} disabled={createLoading} className="rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-1.5 text-xs font-semibold text-white hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50">
                {createLoading ? 'Submitting...' : 'Submit Request'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Decision modal */}
      {deciding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-sm space-y-3 rounded-xl bg-white p-5 shadow-xl dark:bg-slate-900">
            <h3 className="text-sm font-bold capitalize text-slate-900 dark:text-white">{deciding.action} approval?</h3>
            <div>
              <label className="mb-1 block text-[10px] font-medium text-slate-500">Note (optional)</label>
              <textarea value={decisionNote} onChange={e => setDecisionNote(e.target.value)} placeholder="Reason for your decision..." rows={3} className={`resize-none ${inputCls}`} />
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeciding(null)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">Back</button>
              <button onClick={handleDecide} className={`rounded-lg px-4 py-1.5 text-xs font-semibold text-white ${deciding.action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-red-600 hover:bg-red-500'}`}>
                Confirm {deciding.action}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Quick nav footer */}
      <div className="flex flex-wrap gap-1.5 pt-2">
        {[
          { href: '/audit', label: 'Audit Log' },
          { href: '/security', label: 'Security' },
          { href: '/data-capture', label: 'Data Capture' },
          { href: '/tool-registry', label: 'Tool Governance' },
          { href: '/governance-pack', label: 'Audit Pack' },
          { href: '/alert-rules', label: 'Alert Rules' },
          { href: '/budgets', label: 'Budgets' },
        ].map((l) => (
          <Link key={l.href} href={l.href} className="rounded-full bg-indigo-50 px-2.5 py-1 text-[10px] font-medium text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-100 dark:bg-indigo-950/30 dark:text-indigo-400 dark:ring-indigo-800 dark:hover:bg-indigo-950/50">
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
