'use client'

import Link from 'next/link'
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { Activity, BarChart3, Building2, Check, Cpu, FileCheck, FileSpreadsheet, FolderOpen, KeyRound, Layers, Network, Pencil, Plus, Radio, Receipt, Shield, Trash2, UserPlus, Users, Wallet, X } from 'lucide-react'
import { getOrgFinance, getOrgRuntime, getOrgObserve, getOrgGovernance } from '@/lib/api'
import type { OrgFinanceSummary, OrgRuntimeSummary, OrgObserveSummary, OrgGovernanceSummary } from '@/types/api'

interface OrgProfile {
  id: string
  name: string
  plan: string
  is_default: boolean
  owner_user_id: string | null
  created_at: string
}

interface OrgWorkspace {
  id: string
  name: string
  tenant_id: string
  status: 'active' | 'suspended' | 'archived'
  is_restricted: boolean
  created_at: string
}

interface OrgMember {
  user_id: string
  email: string
  full_name: string | null
  role: 'org_admin' | 'org_manager' | 'org_member' | 'org_billing_admin' | 'org_auditor'
  status: 'active' | 'invited' | 'suspended'
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

const PLAN_COLORS: Record<string, string> = {
  free: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  pro: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  enterprise: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
}

const ORG_ROLE_COLORS: Record<string, string> = {
  org_admin: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  org_manager: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  org_member: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  org_billing_admin: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  org_auditor: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
}

const ORG_ROLE_LABELS: Record<string, string> = {
  org_admin: 'Org Admin',
  org_manager: 'Org Manager',
  org_member: 'Member',
  org_billing_admin: 'Billing Admin',
  org_auditor: 'Auditor',
}

function formatMoney(value: string | number | null | undefined) {
  const numeric = Number(value ?? 0)
  return `$${numeric.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function statusTone(status: string) {
  if (status === 'ready') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
  if (status === 'partial') return 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
  if (status === 'at_risk' || status === 'missing') return 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300'
  return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
}

export default function OrgTab({ apiKey, apiBase }: { apiKey: string; apiBase: string }) {
  // ── Profile ──────────────────────────────────────────────────────────────────
  const [profile, setProfile] = useState<OrgProfile | null>(null)
  const [editName, setEditName] = useState('')
  const [savingProfile, setSavingProfile] = useState(false)
  const [finance, setFinance] = useState<OrgFinanceSummary | null>(null)
  const [runtime, setRuntime] = useState<OrgRuntimeSummary | null>(null)
  const [observe, setObserve] = useState<OrgObserveSummary | null>(null)
  const [governance, setGovernance] = useState<OrgGovernanceSummary | null>(null)

  // ── Workspaces ───────────────────────────────────────────────────────────────
  const [workspaces, setWorkspaces] = useState<OrgWorkspace[]>([])
  const [newWsName, setNewWsName] = useState('')
  const [creatingWs, setCreatingWs] = useState(false)

  // ── Members ───────────────────────────────────────────────────────────────────
  const [members, setMembers] = useState<OrgMember[]>([])
  const [showMemberForm, setShowMemberForm] = useState(false)
  const [memberForm, setMemberForm] = useState({ email: '', full_name: '', password: '', role: 'org_member' as OrgMember['role'] })
  const [submittingMember, setSubmittingMember] = useState(false)
  const [editMemberId, setEditMemberId] = useState<string | null>(null)
  const [savingMemberRole, setSavingMemberRole] = useState(false)

  const headers = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' }

  const load = useCallback(async () => {
    if (!apiKey) return
    try {
      const [profileRes, wsRes, membersRes, financeRes, runtimeRes, observeRes, governanceRes] = await Promise.all([
        fetch(`${apiBase}/org/profile`, { headers }),
        fetch(`${apiBase}/org/workspaces`, { headers }),
        fetch(`${apiBase}/org/members`, { headers }),
        getOrgFinance(apiKey).catch(() => null),
        getOrgRuntime(apiKey).catch(() => null),
        getOrgObserve(apiKey).catch(() => null),
        getOrgGovernance(apiKey).catch(() => null),
      ])
      if (profileRes.ok) {
        const p = await profileRes.json()
        setProfile(p)
        setEditName(p.name)
      }
      if (wsRes.ok) setWorkspaces(await wsRes.json())
      if (membersRes.ok) setMembers(await membersRes.json())
      setFinance(financeRes)
      setRuntime(runtimeRes)
      setObserve(observeRes)
      setGovernance(governanceRes)
    } catch {
      toast.error('Failed to load organization data')
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, apiBase])

  useEffect(() => { load() }, [load])

  // ── Profile save ─────────────────────────────────────────────────────────────
  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault()
    if (!editName.trim()) return
    setSavingProfile(true)
    try {
      const r = await fetch(`${apiBase}/org/profile`, {
        method: 'PUT', headers,
        body: JSON.stringify({ name: editName.trim() }),
      })
      if (!r.ok) throw new Error(await r.text())
      const updated = await r.json()
      setProfile(updated)
      toast.success('Organization name updated')
    } catch {
      toast.error('Failed to update organization name')
    } finally {
      setSavingProfile(false)
    }
  }

  // ── Workspace handlers ────────────────────────────────────────────────────────
  async function handleCreateWorkspace(e: React.FormEvent) {
    e.preventDefault()
    if (!newWsName.trim()) return
    setCreatingWs(true)
    try {
      const r = await fetch(`${apiBase}/org/workspaces`, {
        method: 'POST', headers,
        body: JSON.stringify({ name: newWsName.trim() }),
      })
      if (!r.ok) throw new Error(await r.text())
      const ws = await r.json()
      setWorkspaces((prev) => [...prev, ws])
      setNewWsName('')
      toast.success('Workspace created')
    } catch {
      toast.error('Failed to create workspace')
    } finally {
      setCreatingWs(false)
    }
  }

  async function handleDeleteWorkspace(wsId: string) {
    if (!confirm('Delete this workspace? All data in it will be lost.')) return
    try {
      const r = await fetch(`${apiBase}/org/workspaces/${wsId}`, { method: 'DELETE', headers })
      if (!r.ok) {
        const msg = await r.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      setWorkspaces((prev) => prev.filter((w) => w.id !== wsId))
      toast.success('Workspace deleted')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete workspace')
    }
  }

  // ── Member handlers ───────────────────────────────────────────────────────────
  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault()
    if (!memberForm.email.trim() || !memberForm.password.trim()) return
    setSubmittingMember(true)
    try {
      const r = await fetch(`${apiBase}/org/members/invite`, {
        method: 'POST', headers,
        body: JSON.stringify({
          email: memberForm.email.trim(),
          full_name: memberForm.full_name.trim() || null,
          temporary_password: memberForm.password,
          role: memberForm.role,
        }),
      })
      if (!r.ok) {
        const msg = await r.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      const member: OrgMember = await r.json()
      setMembers((prev) => [...prev, member])
      setMemberForm({ email: '', full_name: '', password: '', role: 'org_member' })
      setShowMemberForm(false)
      toast.success(`${member.email} added to organization`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to add member')
    } finally {
      setSubmittingMember(false)
    }
  }

  async function handleSaveMemberRole(userId: string, role: OrgMember['role']) {
    setSavingMemberRole(true)
    // Optimistic update
    setMembers((prev) => prev.map((m) => m.user_id === userId ? { ...m, role: role as OrgMember['role'] } : m))
    try {
      const r = await fetch(`${apiBase}/org/members/${userId}/role`, {
        method: 'PUT', headers, body: JSON.stringify({ role }),
      })
      if (!r.ok) throw new Error()
      toast.success('Role updated')
      setEditMemberId(null)
    } catch {
      toast.error('Failed to update role')
      load() // revert optimistic
    } finally {
      setSavingMemberRole(false)
    }
  }

  async function handleToggleMemberStatus(userId: string, currentStatus: OrgMember['status']) {
    const newStatus = currentStatus === 'suspended' ? 'active' : 'suspended'
    try {
      const r = await fetch(`${apiBase}/org/members/${userId}/status`, {
        method: 'PUT', headers,
        body: JSON.stringify({ status: newStatus }),
      })
      if (!r.ok) {
        const msg = await r.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      const updated: OrgMember = await r.json()
      setMembers((prev) => prev.map((m) => m.user_id === userId ? { ...m, status: updated.status } : m))
      toast.success(newStatus === 'suspended' ? 'Member suspended' : 'Member reactivated')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to update member status')
    }
  }

  async function handleToggleWorkspaceStatus(wsId: string, currentStatus: OrgWorkspace['status']) {
    const newStatus = currentStatus === 'suspended' ? 'active' : 'suspended'
    try {
      const r = await fetch(`${apiBase}/org/workspaces/${wsId}/status`, {
        method: 'PUT', headers,
        body: JSON.stringify({ status: newStatus }),
      })
      if (!r.ok) {
        const msg = await r.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      const updated: OrgWorkspace = await r.json()
      setWorkspaces((prev) => prev.map((w) => w.id === wsId ? { ...w, status: updated.status } : w))
      toast.success(newStatus === 'suspended' ? 'Workspace suspended' : 'Workspace reactivated')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to update workspace status')
    }
  }

  async function handleRemoveMember(userId: string, email: string) {
    if (!confirm(`Remove ${email} from this organization?`)) return
    try {
      const r = await fetch(`${apiBase}/org/members/${userId}`, { method: 'DELETE', headers })
      if (!r.ok) {
        const msg = await r.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      setMembers((prev) => prev.filter((m) => m.user_id !== userId))
      toast.success(`${email} removed from organization`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to remove member')
    }
  }

  const planLabel = profile?.plan
    ? profile.plan.charAt(0).toUpperCase() + profile.plan.slice(1)
    : ''

  return (
    <div className="space-y-8">

      {/* ── Organization Profile ─────────────────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Building2 className="h-5 w-5 text-indigo-500" />
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Organization Profile</h2>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <div className="flex items-center gap-4 mb-5">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-indigo-600 text-white text-2xl font-bold">
              {profile?.name?.[0]?.toUpperCase() ?? '?'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">{profile?.name ?? '—'}</span>
                {profile?.is_default && (
                  <span className="rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 px-2 py-0.5 text-xs font-medium">Default</span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PLAN_COLORS[profile?.plan ?? ''] ?? ''}`}>
                  {planLabel} Plan
                </span>
                {profile?.created_at && (
                  <span className="text-xs text-gray-400">
                    Since {new Date(profile.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          </div>

          <form onSubmit={handleSaveProfile} className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Organization Name</label>
              <input
                className={inputCls + ' w-full'}
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="My Organization"
                required
              />
            </div>
            <button
              type="submit"
              disabled={savingProfile || editName.trim() === profile?.name}
              className="rounded bg-indigo-600 px-4 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {savingProfile ? 'Saving…' : 'Save'}
            </button>
          </form>
        </div>
      </section>

      {/* ── Financial Posture ───────────────────────────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <Wallet className="h-5 w-5 text-indigo-500" />
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Financial Posture</h2>
          <span className="ml-auto text-xs text-gray-400">Read-only org rollup</span>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Use the org console to review cross-workspace finance posture, then jump into the owning FinOps surfaces to act. Budgets, billing, chargeback, and compliance stay owned by their dedicated workflows.
          </p>

          {finance ? (
            <>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">30d spend</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{formatMoney(finance.org_spend_30d_usd)}</div>
                  <div className="mt-1 text-xs text-slate-500">Across {finance.workspaces.length} workspaces</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Budgets</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{finance.active_budget_count}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {finance.active_override_count} overrides, {finance.active_notification_count} notification channels
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Billing</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{finance.overdue_billing_period_count}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    overdue periods, {finance.open_billing_period_count} open and {finance.closed_billing_period_count} closed
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Chargeback</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{finance.chargeback_ready_workspace_count}/{finance.workspaces.length}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    workspaces ready, {finance.chargeback_rule_count} active rules
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Ledger readiness</div>
                  <div className="mt-2">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusTone(finance.ledger_readiness_status)}`}>
                      {finance.ledger_readiness_status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-slate-500">
                    {finance.ledger_ready_workspace_count} ready, {finance.ledger_partial_workspace_count} partial, {finance.ledger_at_risk_workspace_count} at risk
                  </div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <Link href="/budgets?tab=policies" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-blue-300 hover:bg-blue-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Wallet className="h-4 w-4 text-blue-600" />Budgets</div>
                  <p className="mt-1 text-xs text-slate-500">Policy list, budget detail, overrides, and notifications stay owned here.</p>
                </Link>
                <Link href="/billing" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-blue-300 hover:bg-blue-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><FileSpreadsheet className="h-4 w-4 text-blue-600" />Billing</div>
                  <p className="mt-1 text-xs text-slate-500">Review periods, reconciliation posture, breakdowns, and finance exports.</p>
                </Link>
                <Link href="/chargeback?dimension=workspace" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-blue-300 hover:bg-blue-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Receipt className="h-4 w-4 text-blue-600" />Chargeback</div>
                  <p className="mt-1 text-xs text-slate-500">Confirm allocation coverage and workflow ownership evidence.</p>
                </Link>
                <Link href="/settings?tab=compliance" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-blue-300 hover:bg-blue-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><FileCheck className="h-4 w-4 text-blue-600" />Compliance</div>
                  <p className="mt-1 text-xs text-slate-500">Ledger readiness remains platform-owned and lives under compliance settings.</p>
                </Link>
                <Link href="/budgets?tab=detail" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-blue-300 hover:bg-blue-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Wallet className="h-4 w-4 text-blue-600" />Budget Detail</div>
                  <p className="mt-1 text-xs text-slate-500">Drill into individual budget allocations, usage, and override history.</p>
                </Link>
                <Link href="/billing?tab=detail" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-blue-300 hover:bg-blue-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><FileSpreadsheet className="h-4 w-4 text-blue-600" />Billing Period Detail</div>
                  <p className="mt-1 text-xs text-slate-500">Review individual billing period line items and reconciliation status.</p>
                </Link>
              </div>

              <div className="mt-5 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs text-slate-500 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium">Workspace</th>
                      <th className="px-4 py-2 text-left font-medium">30d spend</th>
                      <th className="px-4 py-2 text-left font-medium">Budgets</th>
                      <th className="px-4 py-2 text-left font-medium">Billing</th>
                      <th className="px-4 py-2 text-left font-medium">Chargeback</th>
                      <th className="px-4 py-2 text-left font-medium">Ledger</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {finance.workspaces.map((workspace) => (
                      <tr key={workspace.workspace_id} className="bg-white dark:bg-gray-900">
                        <td className="px-4 py-3">
                          <div className="font-medium text-slate-900 dark:text-white">{workspace.workspace_name}</div>
                          <div className="text-xs text-slate-500">{workspace.chargeback_rule_count} chargeback rules</div>
                        </td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{formatMoney(workspace.spend_30d_usd)}</td>
                        <td className="px-4 py-3 text-xs text-slate-500">
                          <div>{workspace.active_budget_count} active budgets</div>
                          <div>{workspace.active_override_count} overrides, {workspace.active_notification_count} notifications</div>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-500">
                          <div>{workspace.overdue_billing_periods} overdue</div>
                          <div>{workspace.open_billing_periods} open, {workspace.closed_billing_periods} closed</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${statusTone(workspace.chargeback_status)}`}>
                            {workspace.chargeback_status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${statusTone(workspace.ledger_readiness_status)}`}>
                              {workspace.ledger_readiness_status.replace('_', ' ')}
                            </span>
                            <span className="text-xs text-slate-500">score {workspace.ledger_evidence_score}/5</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="mt-4 rounded-xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
              Financial posture data is unavailable right now.
            </div>
          )}
        </div>
      </section>

      {/* ── Runtime Posture ──────────────────────────────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <Radio className="h-5 w-5 text-indigo-500" />
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Runtime Posture</h2>
          <span className="ml-auto text-xs text-gray-400">Read-only org rollup</span>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Gateway routes, routing policies, guardrails, and rate limits across all workspaces. Jump into the owning surfaces to configure.
          </p>

          {runtime ? (
            <>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Active routes</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{runtime.total_active_routes}</div>
                  <div className="mt-1 text-xs text-slate-500">Across {runtime.workspaces.length} workspaces</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Providers</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{runtime.total_distinct_providers}</div>
                  <div className="mt-1 text-xs text-slate-500">Distinct provider integrations</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Routing policies</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{runtime.total_routing_policies}</div>
                  <div className="mt-1 text-xs text-slate-500">Active traffic policies</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Guardrails</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{runtime.total_active_guardrails}</div>
                  <div className="mt-1 text-xs text-slate-500">Active content safety rules</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Rate limits</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{runtime.total_rate_limited_routes}</div>
                  <div className="mt-1 text-xs text-slate-500">Routes with per-user RPM limits</div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <Link href="/provider-profiles" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-violet-300 hover:bg-violet-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Radio className="h-4 w-4 text-violet-600" />Provider Profiles</div>
                  <p className="mt-1 text-xs text-slate-500">Provider configuration and model routing setup.</p>
                </Link>
                <Link href="/gateway" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-violet-300 hover:bg-violet-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Activity className="h-4 w-4 text-violet-600" />Model Gateway</div>
                  <p className="mt-1 text-xs text-slate-500">Routes, routing policies, and traffic management.</p>
                </Link>
                <Link href="/guardrails" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-violet-300 hover:bg-violet-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Shield className="h-4 w-4 text-violet-600" />Guardrails</div>
                  <p className="mt-1 text-xs text-slate-500">Content safety rules and policy enforcement.</p>
                </Link>
                <Link href="/gateway?tab=rate-limits" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-violet-300 hover:bg-violet-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><BarChart3 className="h-4 w-4 text-violet-600" />Rate Limits</div>
                  <p className="mt-1 text-xs text-slate-500">Per-user and per-route rate limit tiers.</p>
                </Link>
              </div>

              <div className="mt-5 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs text-slate-500 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium">Workspace</th>
                      <th className="px-4 py-2 text-left font-medium">Routes</th>
                      <th className="px-4 py-2 text-left font-medium">Providers</th>
                      <th className="px-4 py-2 text-left font-medium">Policies</th>
                      <th className="px-4 py-2 text-left font-medium">Guardrails</th>
                      <th className="px-4 py-2 text-left font-medium">Rate limits</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {runtime.workspaces.map((ws) => (
                      <tr key={ws.workspace_id} className="bg-white dark:bg-gray-900">
                        <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{ws.workspace_name}</td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{ws.active_route_count}</td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{ws.distinct_provider_count}</td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{ws.routing_policy_count}</td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{ws.active_guardrail_count}</td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{ws.rate_limited_route_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="mt-4 rounded-xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
              Runtime posture data is unavailable right now.
            </div>
          )}
        </div>
      </section>

      {/* ── Observability Posture ─────────────────────────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-indigo-500" />
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Observability Posture</h2>
          <span className="ml-auto text-xs text-gray-400">Read-only org rollup</span>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Run volume, request traffic, model usage, and monitoring alert coverage across all workspaces. Jump into Observe surfaces to investigate.
          </p>

          {observe ? (
            <>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">30d runs</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{observe.total_run_count_30d.toLocaleString()}</div>
                  <div className="mt-1 text-xs text-slate-500">Across {observe.workspaces.length} workspaces</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">30d requests</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{observe.total_request_count_30d.toLocaleString()}</div>
                  <div className="mt-1 text-xs text-slate-500">Provider calls processed</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Models</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{observe.total_distinct_models}</div>
                  <div className="mt-1 text-xs text-slate-500">Distinct models in use</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">30d errors</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{observe.total_error_count_30d.toLocaleString()}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {observe.total_request_count_30d > 0
                      ? `${((observe.total_error_count_30d / observe.total_request_count_30d) * 100).toFixed(1)}% error rate`
                      : 'No traffic'}
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Alert rules</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{observe.total_active_alert_rules}</div>
                  <div className="mt-1 text-xs text-slate-500">Active monitoring rules</div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <Link href="/analytics" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-teal-300 hover:bg-teal-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><BarChart3 className="h-4 w-4 text-teal-600" />Analytics</div>
                  <p className="mt-1 text-xs text-slate-500">Spend, usage, and model performance overview.</p>
                </Link>
                <Link href="/runs" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-teal-300 hover:bg-teal-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Activity className="h-4 w-4 text-teal-600" />Runs</div>
                  <p className="mt-1 text-xs text-slate-500">Run list, detail, and execution traces.</p>
                </Link>
                <Link href="/analytics?tab=model-usage" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-teal-300 hover:bg-teal-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><BarChart3 className="h-4 w-4 text-teal-600" />Model Usage</div>
                  <p className="mt-1 text-xs text-slate-500">Model distribution, cost trends, and token usage.</p>
                </Link>
                <Link href="/monitoring" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-teal-300 hover:bg-teal-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Radio className="h-4 w-4 text-teal-600" />Monitoring</div>
                  <p className="mt-1 text-xs text-slate-500">Alert rules, thresholds, and incident posture.</p>
                </Link>
                <Link href="/analytics?tab=billing-summary" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-teal-300 hover:bg-teal-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Receipt className="h-4 w-4 text-teal-600" />Billing Summary</div>
                  <p className="mt-1 text-xs text-slate-500">Aggregate billing summaries and cost breakdowns.</p>
                </Link>
                <Link href="/outcomes" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-teal-300 hover:bg-teal-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><BarChart3 className="h-4 w-4 text-teal-600" />Outcomes & ROI</div>
                  <p className="mt-1 text-xs text-slate-500">AI outcome tracking and return on investment metrics.</p>
                </Link>
                <Link href="/analytics?tab=users" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-teal-300 hover:bg-teal-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Users className="h-4 w-4 text-teal-600" />Analytics Users</div>
                  <p className="mt-1 text-xs text-slate-500">Per-user analytics, usage patterns, and activity trends.</p>
                </Link>
              </div>

              <div className="mt-5 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs text-slate-500 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium">Workspace</th>
                      <th className="px-4 py-2 text-left font-medium">Runs (30d)</th>
                      <th className="px-4 py-2 text-left font-medium">Requests (30d)</th>
                      <th className="px-4 py-2 text-left font-medium">Models</th>
                      <th className="px-4 py-2 text-left font-medium">Errors (30d)</th>
                      <th className="px-4 py-2 text-left font-medium">Alert rules</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {observe.workspaces.map((ws) => (
                      <tr key={ws.workspace_id} className="bg-white dark:bg-gray-900">
                        <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{ws.workspace_name}</td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{ws.run_count_30d.toLocaleString()}</td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{ws.request_count_30d.toLocaleString()}</td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{ws.distinct_model_count}</td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{ws.error_count_30d.toLocaleString()}</td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">{ws.active_alert_rule_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="mt-4 rounded-xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
              Observability posture data is unavailable right now.
            </div>
          )}
        </div>
      </section>

      {/* ── Safety & Governance Posture ─────────────────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <Shield className="h-5 w-5 text-indigo-500" />
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Safety & Governance Posture</h2>
          <span className="ml-auto text-xs text-gray-400">Read-only org rollup</span>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Tool inventory, policies, approvals, and tagging across all workspaces. Jump into governance surfaces to configure.
          </p>

          {governance ? (
            <>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Tools</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{governance.tool_count}</div>
                  <div className="mt-1 text-xs text-slate-500">{governance.mcp_server_count} MCP servers, {governance.search_tool_count} search tools</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Tool policies</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{governance.tool_policy_count}</div>
                  <div className="mt-1 text-xs text-slate-500">Active tool governance rules</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Approvals</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{governance.approval_count}</div>
                  <div className="mt-1 text-xs text-slate-500">Approval records across workspaces</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Tags</div>
                  <div className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">{governance.tag_count}</div>
                  <div className="mt-1 text-xs text-slate-500">Classification and metadata tags</div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <Link href="/tools" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Cpu className="h-4 w-4 text-indigo-600" />Tool Registry</div>
                  <p className="mt-1 text-xs text-slate-500">MCP servers, search tools, and tool inventory.</p>
                </Link>
                <Link href="/tool-policies" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Shield className="h-4 w-4 text-indigo-600" />Tool Policies</div>
                  <p className="mt-1 text-xs text-slate-500">Governance rules for tool access and usage.</p>
                </Link>
                <Link href="/governance" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><FileCheck className="h-4 w-4 text-indigo-600" />Governance Pack</div>
                  <p className="mt-1 text-xs text-slate-500">Approval workflows, audit trails, and compliance evidence.</p>
                </Link>
                <Link href="/tags" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Layers className="h-4 w-4 text-indigo-600" />Tags</div>
                  <p className="mt-1 text-xs text-slate-500">Metadata tags for classification and filtering.</p>
                </Link>
              </div>
            </>
          ) : (
            <div className="mt-4 rounded-xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
              Governance posture data is unavailable right now.
            </div>
          )}
        </div>
      </section>

      {/* ── Org Administration ────────────────────────────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <Building2 className="h-5 w-5 text-indigo-500" />
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Org Administration</h2>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Quick links to org-wide administration surfaces for users, access, keys, and platform configuration.
          </p>

          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Link href="/users" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Users className="h-4 w-4 text-indigo-600" />Users</div>
              <p className="mt-1 text-xs text-slate-500">Manage organization members and user accounts.</p>
            </Link>
            <Link href="/access-groups" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Shield className="h-4 w-4 text-indigo-600" />Access Groups</div>
              <p className="mt-1 text-xs text-slate-500">Group-based permissions and dashboard filtering profiles.</p>
            </Link>
            <Link href="/api-keys" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><KeyRound className="h-4 w-4 text-indigo-600" />API Keys</div>
              <p className="mt-1 text-xs text-slate-500">Workspace-scoped keys for SDK, gateway, and MCP auth.</p>
            </Link>
            <Link href="/onboarding" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Plus className="h-4 w-4 text-indigo-600" />Onboarding</div>
              <p className="mt-1 text-xs text-slate-500">Guided setup wizard for new workspace configuration.</p>
            </Link>
            <Link href="/monitoring/telemetry" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Activity className="h-4 w-4 text-indigo-600" />Telemetry</div>
              <p className="mt-1 text-xs text-slate-500">Platform telemetry, traces, and diagnostic data.</p>
            </Link>
            <Link href="/mcp-registry" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Network className="h-4 w-4 text-indigo-600" />MCP Registry</div>
              <p className="mt-1 text-xs text-slate-500">Registered MCP servers and tool integrations.</p>
            </Link>
            <Link href="/ai-hub" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Cpu className="h-4 w-4 text-indigo-600" />AI Hub</div>
              <p className="mt-1 text-xs text-slate-500">Central AI operations hub and model management.</p>
            </Link>
            <Link href="/settings" className="rounded-xl border border-slate-200 px-4 py-3 transition hover:border-indigo-300 hover:bg-indigo-50/50 dark:border-slate-800 dark:hover:bg-slate-800/70">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><FileCheck className="h-4 w-4 text-indigo-600" />Platform Settings</div>
              <p className="mt-1 text-xs text-slate-500">SMTP, webhooks, compliance, and deployment-wide controls.</p>
            </Link>
          </div>
        </div>
      </section>

      {/* ── Workspaces ───────────────────────────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <FolderOpen className="h-5 w-5 text-indigo-500" />
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Workspaces</h2>
          <span className="ml-auto text-xs text-gray-400">{workspaces.length} workspace{workspaces.length !== 1 ? 's' : ''}</span>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          {workspaces.length === 0 ? (
            <div className="p-6 text-center text-sm text-gray-400">No workspaces yet</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">Name</th>
                  <th className="px-4 py-2 text-left font-medium">Created</th>
                  <th className="px-4 py-2 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {workspaces.map((ws) => (
                  <tr key={ws.id} className="bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/60">
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                      <div className="flex items-center gap-2">
                        {ws.name}
                        {ws.status === 'suspended' && (
                          <span className="rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 px-2 py-0.5 text-[10px] font-medium">
                            Suspended
                          </span>
                        )}
                        {ws.is_restricted && (
                          <span className="rounded-full bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 px-2 py-0.5 text-[10px] font-medium">
                            Restricted
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{new Date(ws.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleToggleWorkspaceStatus(ws.id, ws.status)}
                          title={ws.status === 'suspended' ? 'Reactivate workspace' : 'Suspend workspace'}
                          className={`p-1 text-xs rounded px-2 py-0.5 ${
                            ws.status === 'suspended'
                              ? 'text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20'
                              : 'text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20'
                          }`}
                        >
                          {ws.status === 'suspended' ? 'Unsuspend' : 'Suspend'}
                        </button>
                        <button
                          onClick={() => handleDeleteWorkspace(ws.id)}
                          disabled={workspaces.length <= 1}
                          title={workspaces.length <= 1 ? 'Cannot delete the last workspace' : 'Delete workspace'}
                          className="p-1 text-gray-400 hover:text-red-500 disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <form onSubmit={handleCreateWorkspace} className="mt-3 flex gap-2">
          <input
            className={inputCls + ' flex-1'}
            value={newWsName}
            onChange={(e) => setNewWsName(e.target.value)}
            placeholder="New workspace name…"
          />
          <button
            type="submit"
            disabled={creatingWs || !newWsName.trim()}
            className="flex items-center gap-1.5 rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
            {creatingWs ? 'Creating…' : 'Add'}
          </button>
        </form>
      </section>

      {/* ── Members ──────────────────────────────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Users className="h-5 w-5 text-indigo-500" />
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Members</h2>
          <span className="ml-auto text-xs text-gray-400">{members.length} member{members.length !== 1 ? 's' : ''}</span>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          {members.length === 0 ? (
            <div className="p-6 text-center text-sm text-gray-400">No members yet</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">Member</th>
                  <th className="px-4 py-2 text-left font-medium">Role</th>
                  <th className="px-4 py-2 text-left font-medium">Status</th>
                  <th className="px-4 py-2 text-left font-medium">Joined</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {members.map((m) => (
                  <tr key={m.user_id} className="bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/60">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 text-white text-xs font-bold">
                          {((m.full_name ?? m.email)[0] ?? '?').toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium text-gray-900 dark:text-gray-100 truncate">{m.full_name ?? <span className="text-gray-400 italic">No name</span>}</p>
                          <p className="text-xs text-gray-400 truncate">{m.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {editMemberId === m.user_id ? (
                        <div className="flex items-center gap-1.5">
                          <select
                            defaultValue={m.role}
                            id={`role-select-${m.user_id}`}
                            className={inputCls + ' py-0.5 text-xs'}
                          >
                            <option value="org_admin">Org Admin</option>
                            <option value="org_manager">Org Manager</option>
                            <option value="org_member">Member</option>
                            <option value="org_billing_admin">Billing Admin</option>
                            <option value="org_auditor">Auditor</option>
                          </select>
                          <button
                            onClick={() => {
                              const sel = document.getElementById(`role-select-${m.user_id}`) as HTMLSelectElement
                              handleSaveMemberRole(m.user_id, sel.value as OrgMember['role'])
                            }}
                            disabled={savingMemberRole}
                            className="p-1 rounded text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 disabled:opacity-50"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => setEditMemberId(null)} className="p-1 rounded text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700">
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          {(m.role === 'org_admin' || m.role === 'org_manager') && <Shield className="h-3.5 w-3.5 text-amber-500 shrink-0" />}
                          <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${ORG_ROLE_COLORS[m.role] ?? ''}`}>
                            {ORG_ROLE_LABELS[m.role] ?? m.role}
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                        m.status === 'active'
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                          : m.status === 'suspended'
                          ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                          : 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                      }`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${
                          m.status === 'active' ? 'bg-emerald-500'
                          : m.status === 'suspended' ? 'bg-amber-500'
                          : 'bg-blue-400'
                        }`} />
                        {m.status === 'active' ? 'Active' : m.status === 'suspended' ? 'Suspended' : 'Invited'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">{new Date(m.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setEditMemberId(editMemberId === m.user_id ? null : m.user_id)}
                          className="p-1 text-gray-400 hover:text-indigo-500"
                          title="Edit role"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleToggleMemberStatus(m.user_id, m.status)}
                          title={m.status === 'suspended' ? 'Reactivate member' : 'Suspend member'}
                          className={`p-1 text-xs rounded ${
                            m.status === 'suspended'
                              ? 'text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20'
                              : 'text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20'
                          }`}
                        >
                          {m.status === 'suspended' ? 'Unsuspend' : 'Suspend'}
                        </button>
                        <button
                          onClick={() => handleRemoveMember(m.user_id, m.email)}
                          className="p-1 text-gray-400 hover:text-red-500"
                          title="Remove from organization"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Add member form */}
        {showMemberForm ? (
          <div className="mt-3 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 p-4">
            <div className="flex items-center gap-2 mb-3">
              <UserPlus className="h-4 w-4 text-indigo-500" />
              <span className="text-sm font-medium text-gray-800 dark:text-gray-200">Add to organization</span>
            </div>
            <form onSubmit={handleAddMember} className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <input
                type="email"
                value={memberForm.email}
                onChange={(e) => setMemberForm((f) => ({ ...f, email: e.target.value }))}
                placeholder="Email address *"
                className={inputCls + ' w-full'}
                required autoFocus
              />
              <input
                value={memberForm.full_name}
                onChange={(e) => setMemberForm((f) => ({ ...f, full_name: e.target.value }))}
                placeholder="Full name (optional)"
                className={inputCls + ' w-full'}
              />
              <input
                type="password"
                value={memberForm.password}
                onChange={(e) => setMemberForm((f) => ({ ...f, password: e.target.value }))}
                placeholder="Temporary password *"
                className={inputCls + ' w-full'}
                required
              />
              <div className="flex gap-2">
                <select
                  value={memberForm.role}
                  onChange={(e) => setMemberForm((f) => ({ ...f, role: e.target.value as OrgMember['role'] }))}
                  className={inputCls + ' flex-1'}
                >
                  <option value="org_member">Member</option>
                  <option value="org_admin">Org Admin</option>
                  <option value="org_manager">Org Manager</option>
                  <option value="org_billing_admin">Billing Admin</option>
                  <option value="org_auditor">Auditor</option>
                </select>
                <button
                  type="submit"
                  disabled={submittingMember || !memberForm.email.trim() || !memberForm.password.trim()}
                  className="flex items-center gap-1 rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
                >
                  <UserPlus className="h-3.5 w-3.5" />
                  {submittingMember ? 'Adding…' : 'Add'}
                </button>
              </div>
            </form>
            <button onClick={() => setShowMemberForm(false)} className="mt-2 text-xs text-gray-400 hover:text-gray-600">Cancel</button>
          </div>
        ) : (
          <button
            onClick={() => setShowMemberForm(true)}
            className="mt-3 flex items-center gap-1.5 rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
          >
            <UserPlus className="h-4 w-4" />
            Add Member
          </button>
        )}
      </section>

    </div>
  )
}
