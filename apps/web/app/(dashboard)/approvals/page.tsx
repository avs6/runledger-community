'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  getApprovalSummary,
  listApprovals,
  createApproval,
  approveApproval,
  denyApproval,
  cancelApproval,
} from '@/lib/api'
import { useRole } from '@/components/rbac/useRole'
import type { ApprovalResponse, ApprovalSummary, ApprovalRequestType } from '@/types/api'

const REQUEST_TYPE_LABELS: Record<ApprovalRequestType, string> = {
  budget_increase: 'Budget Increase',
  prompt_promote: 'Prompt → Production',
  tool_allow: 'Allow Privileged Tool',
  capture_policy_full: 'Full Payload Capture',
  shadow_routing: 'Shadow Routing',
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

  // Create form state
  const [showCreate, setShowCreate] = useState(false)
  const [createType, setCreateType] = useState<ApprovalRequestType>('budget_increase')
  const [createReason, setCreateReason] = useState('')
  const [createLoading, setCreateLoading] = useState(false)

  // Decision note modal
  const [deciding, setDeciding] = useState<{ id: string; action: 'approve' | 'deny' } | null>(null)
  const [decisionNote, setDecisionNote] = useState('')

  const loadData = async () => {
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
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, statusFilter, isWorkspaceAdmin])

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

  if (!isWorkspaceAdmin) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Approvals</h1>
        <p className="mt-4 text-sm text-slate-500">Approvals require workspace-admin access.</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Approvals</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Governance workflow for sensitive actions — budget increases, production deploys, and more
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700"
        >
          Request Approval
        </button>
      </div>

      {/* Summary strip */}
      {summary && (
        <div className="grid grid-cols-4 gap-3">
          {(['pending', 'approved', 'denied', 'cancelled'] as const).map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s === statusFilter ? '' : s)}
              className={`rounded-xl border p-3 text-left transition-colors ${
                statusFilter === s
                  ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20'
                  : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/50'
              }`}
            >
              <div className="text-2xl font-bold">{summary[s]}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 capitalize mt-0.5">{s}</div>
            </button>
          ))}
        </div>
      )}

      {/* Approvals table */}
      <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-xl overflow-hidden">
        <div className="p-4 border-b dark:border-gray-700 flex items-center gap-3">
          <h2 className="text-sm font-semibold flex-1">
            {statusFilter ? `${statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)} Approvals` : 'All Approvals'}
            {!loading && <span className="ml-2 text-gray-400 font-normal">({total})</span>}
          </h2>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="text-xs border rounded px-2 py-1 bg-white dark:bg-gray-800 dark:border-gray-600"
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="denied">Denied</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        {loading ? (
          <div className="divide-y dark:divide-gray-700">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="p-4 animate-pulse">
                <div className="h-4 bg-gray-100 dark:bg-gray-700 rounded w-1/3 mb-2" />
                <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : approvals.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400 text-sm">
            No approvals found.
            <br />
            <span className="text-xs mt-1 block">
              Sensitive actions like promoting prompts to production will appear here.
            </span>
          </div>
        ) : (
          <div className="divide-y dark:divide-gray-700">
            {approvals.map(approval => {
              const filteredEntries = Object.entries(approval.request).filter(([k]) => k !== '_reason')
              const requestContextStr: string | null = filteredEntries.length > 0
                ? JSON.stringify(Object.fromEntries(filteredEntries))
                : null
              const reasonStr = approval.request._reason != null ? String(approval.request._reason) : null
              return (
              <div key={approval.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/30">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm">
                        {REQUEST_TYPE_LABELS[approval.request_type] ?? approval.request_type}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          STATUS_COLORS[approval.status] ?? STATUS_COLORS.cancelled
                        }`}
                      >
                        {approval.status}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 space-y-0.5">
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
                      {/* Request context */}
                      {requestContextStr !== null && (
                        <div className="font-mono text-xs bg-gray-100 dark:bg-gray-700/50 rounded px-2 py-1 mt-1 max-w-lg truncate">
                          {requestContextStr}
                        </div>
                      )}
                      {reasonStr !== null && (
                        <div>Reason: {reasonStr}</div>
                      )}
                    </div>
                  </div>

                  {/* Action buttons for pending approvals */}
                  {approval.status === 'pending' && (
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => { setDeciding({ id: approval.id, action: 'approve' }); setDecisionNote('') }}
                        className="px-3 py-1 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => { setDeciding({ id: approval.id, action: 'deny' }); setDecisionNote('') }}
                        className="px-3 py-1 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700"
                      >
                        Deny
                      </button>
                      <button
                        onClick={() => handleCancel(approval.id)}
                        className="px-3 py-1 text-xs border dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
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

      {/* Create approval modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-lg font-semibold">Request Approval</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Request Type</label>
                <select
                  value={createType}
                  onChange={e => setCreateType(e.target.value as ApprovalRequestType)}
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:border-gray-600"
                >
                  {REQUEST_TYPES.map(t => (
                    <option key={t} value={t}>{REQUEST_TYPE_LABELS[t]}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Reason (optional)</label>
                <textarea
                  value={createReason}
                  onChange={e => setCreateReason(e.target.value)}
                  placeholder="Why is this change needed?"
                  rows={3}
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:border-gray-600 resize-none"
                />
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 rounded p-2">
                Once approved, use the approval ID when performing the sensitive action.
                For example, pass <code className="bg-gray-200 dark:bg-gray-600 rounded px-1">?approval_id=&lt;id&gt;</code> to{' '}
                <code className="bg-gray-200 dark:bg-gray-600 rounded px-1">POST /prompts/&#123;name&#125;/promote</code>.
              </div>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-sm border dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={createLoading}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
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
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
            <h3 className="text-lg font-semibold capitalize">
              {deciding.action} approval?
            </h3>
            <div>
              <label className="block text-sm font-medium mb-1">Note (optional)</label>
              <textarea
                value={decisionNote}
                onChange={e => setDecisionNote(e.target.value)}
                placeholder="Reason for your decision…"
                rows={3}
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:border-gray-600 resize-none"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setDeciding(null)}
                className="px-4 py-2 text-sm border dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Back
              </button>
              <button
                onClick={handleDecide}
                className={`px-4 py-2 text-sm text-white rounded-lg ${
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
