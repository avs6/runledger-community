'use client'

import { Suspense, useEffect, useState, useCallback, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { DataTable, type DataTableColumn, type DataTableQuery } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { PageHeader } from '@/components/ui/page-header'
import { apiFetchPage } from '@/lib/api/client'
import type { StaticRoute } from '@/lib/routes'
import { ScrollText, Plus, Trash2, ShieldCheck, X, Zap, Clock, CheckCircle2, XCircle, Ban, Pencil } from 'lucide-react'
import { getApprovalSummary, createApproval, approveApproval, denyApproval, cancelApproval, listAutoApprovalPolicies, createAutoApprovalPolicy, updateAutoApprovalPolicy, deleteAutoApprovalPolicy } from '@/lib/api'
import { useRole } from '@/components/rbac/useRole'
import { num } from '@/lib/utils'
import type { ApprovalResponse, ApprovalSummary, ApprovalRequestType, AutoApprovalPolicy } from '@/types/api'

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
  model_access: 'Model Access (AI Hub)',
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

const AUDIT: StaticRoute = '/audit'
const QUICK_LINKS: { href: StaticRoute; label: string }[] = [
  { href: '/audit', label: 'Audit Log' },
  { href: '/security', label: 'Security' },
  { href: '/data-capture', label: 'Data Capture' },
  { href: '/tool-registry', label: 'Tool Governance' },
  { href: '/governance-pack', label: 'Audit Pack' },
  { href: '/alert-rules', label: 'Alert Rules' },
  { href: '/budgets', label: 'Budgets' },
]

/** Same rule as the API (review S-15): a request is approved by someone other than its requester. */
function isOwnRequest(approval: ApprovalResponse, me: string | null | undefined): boolean {
  return Boolean(approval.requested_by && me && approval.requested_by.trim().toLowerCase() === me.trim().toLowerCase())
}

export default function ApprovalsPage() {
  return (
    <Suspense fallback={<div className="p-4 text-xs text-slate-400">Loading…</div>}>
      <Approvals />
    </Suspense>
  )
}

function Approvals() {
  const { data: session } = useSession()
  const { isWorkspaceAdmin } = useRole()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const me = (session?.user as { email?: string } | undefined)?.email
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const { confirm, dialog } = useConfirm()
  // Tab and status filter live in the URL (shareable, survive reloads).
  const tab: Tab = params.get('tab') === 'policies' ? 'policies' : 'queue'
  const statusFilter = params.get('status') ?? 'pending'
  const setUrl = useCallback((patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params.toString())
    for (const [k, v] of Object.entries(patch)) {
      if (v === null) next.delete(k)
      else next.set(k, v)
    }
    next.delete('approvals_page')
    router.replace(`${pathname}${next.toString() ? `?${next}` : ''}`, { scroll: false })
  }, [params, pathname, router])
  const setTab = (t: Tab) => setUrl({ tab: t === 'queue' ? null : t })
  const setStatusFilter = (v: string) => setUrl({ status: v === 'pending' ? null : v })
  const [summary, setSummary] = useState<ApprovalSummary | null>(null)
  const [reload, setReload] = useState(0)

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
    try {
      setSummary(await getApprovalSummary(apiKey))
    } catch {
      toast.error('Failed to load approval counts')
    }
    setReload((n) => n + 1)
  }, [apiKey, isWorkspaceAdmin])

  const fetchPage = useCallback(
    (q: DataTableQuery) => {
      const qs = new URLSearchParams({ limit: String(q.limit), offset: String(q.offset) })
      if (statusFilter && statusFilter !== 'all') qs.set('status', statusFilter)
      if (q.q) qs.set('requested_by', q.q)
      return apiFetchPage<ApprovalResponse>(`/approvals?${qs}`, apiKey)
    },
    [apiKey, statusFilter],
  )

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
    } catch (err) {
      const msg = err instanceof Error && err.message.includes('Separation of duties')
        ? 'Separation of duties: someone other than the requester must approve this.'
        : 'Failed to record decision'
      toast.error(msg)
    }
  }

  const handleCancel = async (id: string) => {
    if (!apiKey || !isWorkspaceAdmin) return
    const ok = await confirm({ title: 'Cancel this approval request?', description: 'The request is closed without a decision and any held change is released.', confirmLabel: 'Cancel request', destructive: true })
    if (!ok) return
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
    const ok = await confirm({ title: 'Delete this auto-approval policy?', description: 'Matching requests will wait for a human decision again.', confirmLabel: 'Delete', destructive: true })
    if (!ok) return
    try {
      await deleteAutoApprovalPolicy(apiKey, id)
      toast.success('Policy deleted')
      loadPolicies()
    } catch {
      toast.error('Failed to delete policy')
    }
  }

  const queueColumns: DataTableColumn<ApprovalResponse>[] = useMemo(() => [
    {
      key: 'request_type',
      header: 'Request',
      value: (a) => REQUEST_TYPE_LABELS[a.request_type] ?? a.request_type,
      render: (a) => {
        const entries = Object.entries(a.request).filter(([k]) => k !== '_reason')
        const reason = a.request._reason != null ? String(a.request._reason) : null
        return (
          <div className="min-w-0 max-w-md">
            <p className="text-xs font-semibold text-slate-900 dark:text-white">{REQUEST_TYPE_LABELS[a.request_type] ?? a.request_type}</p>
            {reason && <p className="text-[11px] text-slate-500">Reason: {reason}</p>}
            {entries.length > 0 && (
              <p className="mt-0.5 truncate font-mono text-[10px] text-slate-500">{JSON.stringify(Object.fromEntries(entries))}</p>
            )}
          </div>
        )
      },
    },
    {
      key: 'status',
      header: 'Status',
      render: (a) => {
        const chip = STATUS_CHIP[a.status] ?? STATUS_CHIP.cancelled
        const StatusIcon = chip.icon
        return (
          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${chip.cls}`}>
            <StatusIcon className="h-2.5 w-2.5" aria-hidden="true" />
            {a.status}
          </span>
        )
      },
    },
    { key: 'requested_by', header: 'Requested by', render: (a) => <span className="font-mono text-[11px]">{a.requested_by ?? '—'}</span> },
    {
      key: 'decided_by',
      header: 'Decision',
      value: (a) => a.decided_by ?? '',
      render: (a) => a.decided_by ? (
        <span className="text-[11px] text-slate-500">
          <span className="font-mono">{a.decided_by}</span>
          {a.decision_note && <span className="block italic text-slate-400">&ldquo;{a.decision_note}&rdquo;</span>}
        </span>
      ) : <span className="text-slate-400">—</span>,
    },
    { key: 'created_at', header: 'Requested', render: (a) => <span className="whitespace-nowrap text-[11px] text-slate-500">{new Date(a.created_at).toLocaleString()}</span> },
    {
      key: 'actions',
      header: 'Actions',
      render: (a) => a.status !== 'pending' ? null : (
        <div className="flex shrink-0 justify-end gap-1.5">
          <button
            type="button"
            disabled={isOwnRequest(a, me)}
            title={isOwnRequest(a, me) ? 'Separation of duties: you requested this, so someone else must approve it' : undefined}
            onClick={() => { setDeciding({ id: a.id, action: 'approve' }); setDecisionNote('') }}
            aria-label={`Approve ${REQUEST_TYPE_LABELS[a.request_type] ?? a.request_type} request`}
            className="rounded-md bg-emerald-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Approve
          </button>
          <button type="button" onClick={() => { setDeciding({ id: a.id, action: 'deny' }); setDecisionNote('') }} aria-label={`Deny ${REQUEST_TYPE_LABELS[a.request_type] ?? a.request_type} request`} className="rounded-md bg-rose-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-rose-500">Deny</button>
          <button type="button" onClick={() => void handleCancel(a.id)} aria-label="Cancel this request" className="rounded-md border border-slate-200 px-2.5 py-1 text-[10px] text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800">Cancel</button>
        </div>
      ),
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [me])

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
      {dialog}
      <PageHeader
        title="Governance Approvals"
        icon={ShieldCheck}
        description="Exception workflows for sensitive actions. Requests are decided by someone other than the requester, and every step is audited."
        actions={
          <div className="flex items-center gap-2">
            <Link href={`${AUDIT}?action=approval`} className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
              <ScrollText className="h-3.5 w-3.5" aria-hidden="true" /> Audit Trail
            </Link>
            <button type="button" onClick={() => setShowCreate(true)} className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700">
              Request Approval
            </button>
          </div>
        }
      />
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        {/* Summary KPI strip */}
        {summary && (
          <div className="mt-4 grid grid-cols-4 gap-2">
            {(['pending', 'approved', 'denied', 'cancelled'] as const).map((s) => {
              const chip = STATUS_CHIP[s]
              const Icon = chip.icon
              return (
                <button
                  key={s}
                  type="button"
                  aria-pressed={statusFilter === s}
                  onClick={() => setStatusFilter(s === statusFilter ? 'all' : s)}
                  className={`rounded-lg border px-3 py-2 text-left transition-all ${
                    statusFilter === s
                      ? 'border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-950/40'
                      : 'border-slate-200 bg-slate-50/80 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/60 dark:hover:bg-slate-800'
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    <Icon className="h-3.5 w-3.5 text-slate-400 dark:text-slate-500" />
                    <span className="text-xl font-bold text-slate-900 dark:text-white">{summary[s]}</span>
                  </div>
                  <p className="mt-0.5 text-[10px] capitalize text-slate-500 dark:text-slate-400">{s}</p>
                </button>
              )
            })}
          </div>
        )}

      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800/80">
        {[
          { key: 'queue' as Tab, label: 'Approval Queue', icon: ShieldCheck },
          { key: 'policies' as Tab, label: 'Auto-Approval Policies', icon: Zap },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            aria-pressed={tab === key}
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
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              {statusFilter === 'all' ? 'All approvals' : `${statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)} approvals`}
            </h2>
            <select
              aria-label="Filter approvals by status"
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              <option value="all">All statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="denied">Denied</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
          {apiKey && (
            <DataTable
              key={`${statusFilter}:${reload}`}
              label="Approval requests"
              urlPrefix="approvals_"
              fetchPage={fetchPage}
              rowKey={(a) => a.id}
              columns={queueColumns}
              searchPlaceholder="Filter by requester…"
              csvFileName="approvals.csv"
              emptyTitle="No approvals found"
              emptyDescription="Requests from budgets, prompts, tools and clients appear here."
            />
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
                          <button type="button" onClick={() => handleEditPolicy(p)} aria-label={`Edit policy ${p.condition}`} className="rounded-md border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
                            <Pencil className="h-3 w-3" aria-hidden="true" />
                          </button>
                          <button type="button" onClick={() => void handleDeletePolicy(p.id)} aria-label={`Delete policy ${p.condition}`} className="rounded-md border border-red-200 p-1.5 text-red-500 hover:bg-red-50 dark:border-red-900/40 dark:hover:bg-red-950/30">
                            <Trash2 className="h-3 w-3" aria-hidden="true" />
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
        {QUICK_LINKS.map((l) => (
          <Link key={l.href} href={l.href} className="rounded-full bg-indigo-50 px-2.5 py-1 text-[10px] font-medium text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-100 dark:bg-indigo-950/30 dark:text-indigo-400 dark:ring-indigo-800 dark:hover:bg-indigo-950/50">
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
