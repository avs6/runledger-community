'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import { ScrollText, Plus, Trash2 } from 'lucide-react'
import {
  getApprovalSummary,
  listApprovals,
  createApproval,
  approveApproval,
  denyApproval,
  cancelApproval,
  listAutoApprovalPolicies,
  createAutoApprovalPolicy,
  deleteAutoApprovalPolicy,
} from '@/lib/api'
import { useRole } from '@/components/rbac/useRole'
import type {
  ApprovalResponse,
  ApprovalSummary,
  ApprovalRequestType,
  AutoApprovalPolicy,
} from '@/types/api'

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

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  approved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  denied: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  cancelled: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
}

const REQUEST_TYPES: ApprovalRequestType[] = [
  'budget_increase',
  'prompt_promote',
  'tool_allow',
  'capture_policy_full',
  'shadow_routing',
  'premium_model_use',
  'external_mcp_tool',
  'long_agent_session',
  'sensitive_export',
  'route_policy_change',
]

export default function ApprovalsPage() {
  const { data: session } = useSession()
  const { isWorkspaceAdmin } = useRole()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const [summary, setSummary] = useState<ApprovalSummary | null>(null)
  const [approvals, setApprovals] = useState<ApprovalResponse[]>([])
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState<string>('pending')
  const [loading, setLoading] = useState(true)

  const [showCreate, setShowCreate] = useState(false)
  const [createType, setCreateType] = useState<ApprovalRequestType>('budget_increase')
  const [createReason, setCreateReason] = useState('')
  const [createLoading, setCreateLoading] = useState(false)

  const [deciding, setDeciding] = useState<{ id: string; action: 'approve' | 'deny' } | null>(null)
  const [decisionNote, setDecisionNote] = useState('')

  // Auto-approval policies
  const [autoPolicies, setAutoPolicies] = useState<AutoApprovalPolicy[]>([])
  const [loadingPolicies, setLoadingPolicies] = useState(false)
  const [showPolicyForm, setShowPolicyForm] = useState(false)
  const [policyType, setPolicyType] = useState<ApprovalRequestType>('budget_increase')
  const [policyCondition, setPolicyCondition] = useState('')
  const [creatingPolicy, setCreatingPolicy] = useState(false)

  const loadData = useCallback(async () => {
    if (!apiKey || !isWorkspaceAdmin) return
    setLoading(true)
    try {
      const [s, list] = await Promise.all([
        getApprovalSummary(apiKey),
        listApprovals(apiKey, { status: statusFilter || undefined, limit: 100 }),
      ])
      setSummary(s)
      setApprovals(list.items)
      setTotal(list.total)
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
      await createApproval(apiKey, {
        request_type: createType,
        reason: createReason || undefined,
      })
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
        toast.success('Approval approved')
      } else {
        await denyApproval(apiKey, deciding.id, decisionNote || undefined)
        toast.success('Approval denied')
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
      await createAutoApprovalPolicy(apiKey, {
        request_type: policyType,
        condition: policyCondition.trim(),
      })
      toast.success('Auto-approval policy created')
      setShowPolicyForm(false)
      setPolicyCondition('')
      loadPolicies()
    } catch {
      toast.error('Failed to create policy')
    } finally {
      setCreatingPolicy(false)
    }
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
        <h1 className="text-2xl font-bold text-slate-950 dark:text-white">Approvals</h1>
        <p className="mt-4 text-sm text-slate-500">Approvals require workspace-admin access.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-950 dark:text-white">Approvals</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Governance workflow for sensitive actions — budget increases, production deploys, and more
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/audit?action=approval"
            className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <ScrollText className="h-4 w-4" /> Audit Trail
          </Link>
          <button
            onClick={() => setShowCreate(true)}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Request Approval
          </button>
        </div>
      </div>

      {/* Summary strip */}
      {summary && (
        <div className="grid grid-cols-4 gap-3">
          {(['pending', 'approved', 'denied', 'cancelled'] as const).map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s === statusFilter ? '' : s)}
              className={`rounded-xl border p-3 text-left shadow-sm transition-colors ${
                statusFilter === s
                  ? 'border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-950/40'
                  : 'border-slate-300 bg-white/90 hover:bg-blue-50/45 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800'
              }`}
            >
              <div className="text-2xl font-bold text-slate-950 dark:text-white">{summary[s]}</div>
              <div className="mt-0.5 text-xs capitalize text-slate-600 dark:text-slate-400">{s}</div>
            </button>
          ))}
        </div>
      )}

      {/* Approvals table */}
      <div className="overflow-hidden rounded-xl border border-slate-300 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-3 border-b border-slate-200 p-4 dark:border-slate-700">
          <h2 className="flex-1 text-sm font-semibold text-slate-950 dark:text-white">
            {statusFilter ? `${statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)} Approvals` : 'All Approvals'}
            {!loading && <span className="ml-2 font-normal text-slate-500">({total})</span>}
          </h2>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="denied">Denied</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        {loading ? (
          <div className="divide-y divide-slate-200 dark:divide-slate-700">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="animate-pulse p-4">
                <div className="mb-2 h-4 w-1/3 rounded bg-slate-100 dark:bg-slate-700" />
                <div className="h-3 w-1/2 rounded bg-slate-100 dark:bg-slate-700" />
              </div>
            ))}
          </div>
        ) : approvals.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-600 dark:text-slate-400">
            No approvals found.
          </div>
        ) : (
          <div className="divide-y divide-slate-200 dark:divide-slate-700">
            {approvals.map(approval => {
              const filteredEntries = Object.entries(approval.request).filter(([k]) => k !== '_reason')
              const requestContextStr: string | null = filteredEntries.length > 0
                ? JSON.stringify(Object.fromEntries(filteredEntries))
                : null
              const reasonStr = approval.request._reason != null ? String(approval.request._reason) : null
              return (
                <div key={approval.id} className="p-4 text-slate-800 hover:bg-blue-50/45 dark:text-slate-200 dark:hover:bg-slate-800/40">
                  <div className="flex items-start gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-slate-950 dark:text-white">
                          {REQUEST_TYPE_LABELS[approval.request_type] ?? approval.request_type}
                        </span>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[approval.status] ?? STATUS_COLORS.cancelled}`}>
                          {approval.status}
                        </span>
                      </div>
                      <div className="mt-1 space-y-0.5 text-xs text-slate-600 dark:text-slate-400">
                        {approval.requested_by && (
                          <div>Requested by: <span className="font-mono">{approval.requested_by}</span></div>
                        )}
                        <div>
                          {new Date(approval.created_at).toLocaleString()}
                          {approval.decided_at && (
                            <> &rarr; decided {new Date(approval.decided_at).toLocaleString()}</>
                          )}
                        </div>
                        {approval.decided_by && (
                          <div>Decided by: <span className="font-mono">{approval.decided_by}</span></div>
                        )}
                        {approval.decision_note && (
                          <div className="italic">&ldquo;{approval.decision_note}&rdquo;</div>
                        )}
                        {requestContextStr !== null && (
                          <div className="mt-1 max-w-lg truncate rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                            {requestContextStr}
                          </div>
                        )}
                        {reasonStr !== null && <div>Reason: {reasonStr}</div>}
                      </div>
                    </div>

                    {approval.status === 'pending' && (
                      <div className="flex shrink-0 gap-2">
                        <button
                          onClick={() => { setDeciding({ id: approval.id, action: 'approve' }); setDecisionNote('') }}
                          className="rounded-lg bg-green-600 px-3 py-1 text-xs text-white hover:bg-green-700"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => { setDeciding({ id: approval.id, action: 'deny' }); setDecisionNote('') }}
                          className="rounded-lg bg-red-600 px-3 py-1 text-xs text-white hover:bg-red-700"
                        >
                          Deny
                        </button>
                        <button
                          onClick={() => handleCancel(approval.id)}
                          className="rounded-lg border px-3 py-1 text-xs hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Auto-Approval Policies */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Auto-Approval Policies</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Automatically approve requests matching specific conditions.
            </p>
          </div>
          <button
            onClick={() => setShowPolicyForm(!showPolicyForm)}
            className="flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
          >
            <Plus className="h-4 w-4" />
            {showPolicyForm ? 'Cancel' : 'Add Policy'}
          </button>
        </div>

        {showPolicyForm && (
          <div className="mb-4 flex flex-wrap items-end gap-3 border-b border-slate-200 pb-4 dark:border-slate-700">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Request Type</label>
              <select
                value={policyType}
                onChange={(e) => setPolicyType(e.target.value as ApprovalRequestType)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              >
                {REQUEST_TYPES.map(t => (
                  <option key={t} value={t}>{REQUEST_TYPE_LABELS[t]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Condition</label>
              <input
                type="text"
                placeholder='e.g. workspace:engineering or user:admin@*'
                value={policyCondition}
                onChange={(e) => setPolicyCondition(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              />
            </div>
            <button
              onClick={handleCreatePolicy}
              disabled={creatingPolicy}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {creatingPolicy ? 'Creating…' : 'Create'}
            </button>
          </div>
        )}

        {loadingPolicies ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : autoPolicies.length === 0 ? (
          <p className="text-sm text-slate-400">No auto-approval policies configured.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="pb-2 font-medium text-slate-500">Request Type</th>
                  <th className="pb-2 font-medium text-slate-500">Condition</th>
                  <th className="pb-2 font-medium text-slate-500">Created By</th>
                  <th className="pb-2 font-medium text-slate-500">Created</th>
                  <th className="pb-2" />
                </tr>
              </thead>
              <tbody>
                {autoPolicies.map((p) => (
                  <tr key={p.id} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-3">{REQUEST_TYPE_LABELS[p.request_type] ?? p.request_type}</td>
                    <td className="py-3 font-mono text-xs">{p.condition}</td>
                    <td className="py-3 text-xs text-slate-500">{p.created_by ?? '—'}</td>
                    <td className="py-3 text-xs text-slate-500">{new Date(p.created_at).toLocaleDateString()}</td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleDeletePolicy(p.id)}
                        className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create approval modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md space-y-4 rounded-xl bg-white p-6 text-slate-800 shadow-xl dark:bg-slate-900 dark:text-slate-200">
            <h3 className="text-lg font-semibold text-slate-950 dark:text-white">Request Approval</h3>
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium">Request Type</label>
                <select
                  value={createType}
                  onChange={e => setCreateType(e.target.value as ApprovalRequestType)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                >
                  {REQUEST_TYPES.map(t => (
                    <option key={t} value={t}>{REQUEST_TYPE_LABELS[t]}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Reason (optional)</label>
                <textarea
                  value={createReason}
                  onChange={e => setCreateReason(e.target.value)}
                  placeholder="Why is this change needed?"
                  rows={3}
                  className="w-full resize-none rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowCreate(false)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={createLoading}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {createLoading ? 'Submitting…' : 'Submit Request'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Decision modal */}
      {deciding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 text-slate-800 shadow-xl dark:bg-slate-900 dark:text-slate-200">
            <h3 className="text-lg font-semibold capitalize text-slate-950 dark:text-white">
              {deciding.action} approval?
            </h3>
            <div>
              <label className="mb-1 block text-sm font-medium">Note (optional)</label>
              <textarea
                value={decisionNote}
                onChange={e => setDecisionNote(e.target.value)}
                placeholder="Reason for your decision…"
                rows={3}
                className="w-full resize-none rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeciding(null)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                Back
              </button>
              <button
                onClick={handleDecide}
                className={`rounded-lg px-4 py-2 text-sm text-white ${
                  deciding.action === 'approve'
                    ? 'bg-green-600 hover:bg-green-700'
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                Confirm {deciding.action}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
