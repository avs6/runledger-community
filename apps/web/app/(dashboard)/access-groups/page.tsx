'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  Plus,
  Users,
  Shield,
  DollarSign,
  Trash2,
  Edit2,
  X,
  UserPlus,
  UserMinus,
  Layers,
} from 'lucide-react'
import {
  getAccessGroups,
  getAccessGroupDashboard,
  createAccessGroup,
  updateAccessGroup,
  deleteAccessGroup,
  getAccessGroupMembers,
  addAccessGroupMember,
  removeAccessGroupMember,
  listOrgUsers,
  listGuardrailRules,
  listGuardrailTemplates,
  type OrgUser,
} from '@/lib/api'
import type {
  AccessGroupDashboardItem,
  AccessGroupMemberResponse,
  GuardrailRuleResponse,
  GuardrailTemplate,
} from '@/types/api'
import { useRole } from '@/components/rbac/useRole'

function budgetLabel(budget: number | null, period: string | null) {
  if (budget == null) return 'No budget cap'
  return `$${budget.toFixed(2)}${period ? ` / ${period}` : ''}`
}

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

export default function AccessGroupsPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey
  const { isWorkspaceAdmin } = useRole()
  const canManage = isWorkspaceAdmin

  const [groups, setGroups] = useState<AccessGroupDashboardItem[]>([])
  const [loading, setLoading] = useState(true)

  // ── Create / Edit modal state ──────────────────────────────────────────────
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingGroup, setEditingGroup] = useState<AccessGroupDashboardItem | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [budgetUsd, setBudgetUsd] = useState<number | ''>('')
  const [budgetPeriod, setBudgetPeriod] = useState('monthly')
  const [guardrailProfile, setGuardrailProfile] = useState('default')
  const [saving, setSaving] = useState(false)

  // ── Member management modal state ──────────────────────────────────────────
  const [managingGroup, setManagingGroup] = useState<AccessGroupDashboardItem | null>(null)
  const [groupMembers, setGroupMembers] = useState<AccessGroupMemberResponse[]>([])
  const [allUsers, setAllUsers] = useState<OrgUser[]>([])
  const [guardrailRules, setGuardrailRules] = useState<GuardrailRuleResponse[]>([])
  const [guardrailTemplates, setGuardrailTemplates] = useState<GuardrailTemplate[]>([])
  const [selectedUserId, setSelectedUserId] = useState('')
  const [loadingMembers, setLoadingMembers] = useState(false)
  const [addingMember, setAddingMember] = useState(false)

  async function loadData() {
    if (!apiKey) return
    setLoading(true)
    try {
      const [dashboardRes, rulesRes, tplRes] = await Promise.all([
        getAccessGroupDashboard(apiKey),
        listGuardrailRules(apiKey).catch(() => ({ items: [], total: 0 })),
        listGuardrailTemplates(apiKey).catch(() => []),
      ])
      setGroups(dashboardRes.groups)
      setGuardrailRules(rulesRes.items)
      setGuardrailTemplates(tplRes)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load access groups')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [apiKey])

  function resetForm() {
    setName('')
    setDescription('')
    setBudgetUsd('')
    setBudgetPeriod('monthly')
    setGuardrailProfile('default')
    setEditingGroup(null)
  }

  function openEdit(group: AccessGroupDashboardItem) {
    if (!canManage) return
    setEditingGroup(group)
    setName(group.name)
    setDescription('')
    setBudgetUsd(group.budget_usd ?? '')
    setBudgetPeriod(group.budget_period ?? 'monthly')
    setGuardrailProfile(group.guardrail_profile ?? 'default')
    setShowCreateModal(true)
  }

  async function handleSaveGroup(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !name.trim() || !canManage) return
    setSaving(true)
    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || undefined,
        budget_usd: budgetUsd !== '' ? Number(budgetUsd) : undefined,
        budget_period: budgetPeriod,
        guardrail_profile: guardrailProfile,
      }

      if (editingGroup) {
        await updateAccessGroup(apiKey, editingGroup.id, payload)
        toast.success('Access group updated')
      } else {
        await createAccessGroup(apiKey, payload)
        toast.success('Access group created')
      }
      setShowCreateModal(false)
      resetForm()
      loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to save access group')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteGroup(group: AccessGroupDashboardItem) {
    if (!apiKey || !canManage || !confirm(`Deactivate access group "${group.name}"?`)) return
    try {
      await deleteAccessGroup(apiKey, group.id)
      toast.success('Access group deactivated')
      loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete access group')
    }
  }

  async function openMemberManagement(group: AccessGroupDashboardItem) {
    if (!apiKey || !canManage) return
    setManagingGroup(group)
    setLoadingMembers(true)
    try {
      const [membersRes, usersRes] = await Promise.all([
        getAccessGroupMembers(apiKey, group.id),
        listOrgUsers(apiKey).catch(() => []),
      ])
      setGroupMembers(membersRes.items)
      setAllUsers(usersRes)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load group members')
    } finally {
      setLoadingMembers(false)
    }
  }

  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !managingGroup || !selectedUserId || !canManage) return
    setAddingMember(true)
    try {
      await addAccessGroupMember(apiKey, managingGroup.id, { user_id: selectedUserId })
      toast.success('Member added to access group')
      setSelectedUserId('')
      openMemberManagement(managingGroup)
      loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to add member')
    } finally {
      setAddingMember(false)
    }
  }

  async function handleRemoveMember(userId: string) {
    if (!apiKey || !managingGroup || !canManage) return
    try {
      await removeAccessGroupMember(apiKey, managingGroup.id, userId)
      toast.success('Member removed')
      openMemberManagement(managingGroup)
      loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to remove member')
    }
  }

  if (!apiKey) return <div className="p-8 text-slate-500">Sign in to view access groups.</div>

  const totalMembers = groups.reduce((sum, g) => sum + g.member_count, 0)
  const activeGroups = groups.filter((g) => g.is_active).length

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Access Groups
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Group-based permissions with dashboard filtering profiles, guardrails, and budget envelopes.
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            <Link href="/gateway" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Gateway</Link>
            <Link href="/provider-profiles" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Provider Profiles</Link>
            <Link href="/rate-limits" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Rate Limits</Link>
            <Link href="/guardrails" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Guardrails</Link>
            <Link href="/mcp-registry" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">MCP Registry</Link>
            <Link href="/organizations" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">All Organizations</Link>
            <Link href="/settings" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Platform Settings</Link>
          </div>
        </div>
        <button
          onClick={() => {
            if (!canManage) return
            resetForm()
            setShowCreateModal(true)
          }}
          disabled={!canManage}
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition"
        >
          <Plus className="h-4 w-4" />
          {canManage ? 'Create Access Group' : 'Workspace Admin Required'}
        </button>
      </div>

      {!canManage && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-200">
          Access Groups are workspace-scoped governance controls. You can review the dashboard here, but editing groups and membership requires workspace-admin access.
        </div>
      )}

      {/* Overview Stat Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <div className="flex items-center gap-3">
            <span className="rounded-xl bg-blue-50 p-2.5 text-blue-600 dark:bg-blue-950 dark:text-blue-400">
              <Layers className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Active Groups</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{activeGroups}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <div className="flex items-center gap-3">
            <span className="rounded-xl bg-emerald-50 p-2.5 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400">
              <Users className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Assigned Members</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{totalMembers}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <div className="flex items-center gap-3">
            <span className="rounded-xl bg-indigo-50 p-2.5 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400">
              <Shield className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Guardrail Envelopes</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{groups.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Group Cards Grid */}
      {loading ? (
        <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          Loading access groups...
        </div>
      ) : groups.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
          No access groups configured yet. Click &quot;Create Access Group&quot; to define workspace governance profiles.
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {groups.map((group) => (
            <div
              key={group.id}
              className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{group.name}</h3>
                    <span
                      className={`mt-1 inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                        group.is_active
                          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                      }`}
                    >
                      {group.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => openEdit(group)}
                      disabled={!canManage}
                      title="Edit group"
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteGroup(group)}
                      disabled={!canManage}
                      title="Deactivate group"
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40 dark:hover:text-rose-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-slate-400" />
                    <span>{group.member_count} member{group.member_count !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4 text-slate-400" />
                    <span>{budgetLabel(group.budget_usd, group.budget_period)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-slate-400" />
                    <span>Guardrails: <strong className="font-medium text-slate-800 dark:text-slate-200">{group.guardrail_profile || 'default'}</strong></span>
                  </div>
                </div>

                {group.dashboard_filters && Object.keys(group.dashboard_filters).length > 0 && (
                  <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
                    <p className="font-semibold text-slate-700 dark:text-slate-200 mb-1">Dashboard Filters</p>
                    <pre className="overflow-x-auto font-mono text-[11px]">
                      {JSON.stringify(group.dashboard_filters, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800">
                <div className="grid gap-2">
                  <div className="grid grid-cols-3 gap-2">
                    <Link
                      href={`/budgets?tab=policies&scope_type=access_group&scope_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Budgets
                    </Link>
                    <Link
                      href={`/billing?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Billing
                    </Link>
                    <Link
                      href={`/chargeback?dimension=access_group&access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Chargeback
                    </Link>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Link
                      href={`/analytics?scope=workspace&access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Overview
                    </Link>
                    <Link
                      href={`/runs?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Runs
                    </Link>
                    <Link
                      href={`/request-flow?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Flow
                    </Link>
                    <Link
                      href={`/request-explorer?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Explorer
                    </Link>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <Link
                      href={`/approvals?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Approvals
                    </Link>
                    <Link
                      href={`/audit?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Audit Log
                    </Link>
                    <Link
                      href={`/governance?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Governance
                    </Link>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <Link
                      href={`/agents?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Agents
                    </Link>
                    <Link
                      href={`/workflows?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Workflows
                    </Link>
                    <Link
                      href={`/evaluations?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Evaluations
                    </Link>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <Link
                      href={`/experiments?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Experiments
                    </Link>
                    <Link
                      href={`/replay?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Replay
                    </Link>
                    <Link
                      href={`/playground?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Playground
                    </Link>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Link
                      href={`/optimization-opportunities?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Optimization
                    </Link>
                    <Link
                      href={`/optimization-simulator?access_group_id=${encodeURIComponent(group.id)}`}
                      className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      Simulator
                    </Link>
                  </div>
                  <button
                    onClick={() => openMemberManagement(group)}
                    disabled={!canManage}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                  >
                    <Users className="h-3.5 w-3.5" />
                    Manage Members ({group.member_count})
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Create / Edit Access Group Modal ───────────────────────────────── */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900 dark:border dark:border-slate-800">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {editingGroup ? 'Edit Access Group' : 'Create Access Group'}
              </h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveGroup} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Group Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Finance Analytics Team"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  placeholder="Brief description of the group's purpose..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className={`${inputCls} min-h-16`}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Budget Cap (USD)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="e.g. 500.00"
                    value={budgetUsd}
                    onChange={(e) => setBudgetUsd(e.target.value ? Number(e.target.value) : '')}
                    className={inputCls}
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Budget Period
                  </label>
                  <select
                    value={budgetPeriod}
                    onChange={(e) => setBudgetPeriod(e.target.value)}
                    className={inputCls}
                  >
                    <option value="monthly">Monthly</option>
                    <option value="quarterly">Quarterly</option>
                    <option value="yearly">Yearly</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Guardrail Safety Profile / Rule Enforcement
                </label>
                <select
                  value={guardrailProfile}
                  onChange={(e) => setGuardrailProfile(e.target.value)}
                  className={inputCls}
                >
                  <option value="default">Default Workspace Safety</option>
                  <option value="strict">Strict Protection (High Sensitivity)</option>
                  <option value="lenient">Lenient (Development / Sandbox)</option>
                  <optgroup label="Active Workspace Rules">
                    {guardrailRules.map((r) => (
                      <option key={r.id} value={`rule:${r.name}`}>
                        {r.name} ({r.severity.toUpperCase()} • {r.mode})
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Safety Templates">
                    {guardrailTemplates.map((t) => (
                      <option key={t.template_id} value={`template:${t.template_id}`}>
                        Template: {t.name}
                      </option>
                    ))}
                  </optgroup>
                </select>
              </div>

              <div className="mt-6 flex justify-end gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !name.trim()}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : editingGroup ? 'Update Group' : 'Create Group'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Manage Members Modal ───────────────────────────────────────────── */}
      {managingGroup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900 dark:border dark:border-slate-800">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                  Manage Group Members
                </h2>
                <p className="text-xs text-slate-500">{managingGroup.name}</p>
              </div>
              <button
                onClick={() => setManagingGroup(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Add Member Form */}
            <form onSubmit={handleAddMember} className="mt-4 flex gap-2">
              <select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                className={`${inputCls} flex-1`}
              >
                <option value="">Select a user to add...</option>
                {allUsers
                  .filter((u) => !groupMembers.some((m) => m.user_id === u.id))
                  .map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.full_name || user.email} ({user.email})
                    </option>
                  ))}
              </select>
              <button
                type="submit"
                disabled={addingMember || !selectedUserId}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
              >
                <UserPlus className="h-4 w-4" />
                Add Member
              </button>
            </form>

            {/* Existing Members Table */}
            <div className="mt-6">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
                Current Members ({groupMembers.length})
              </h4>
              {loadingMembers ? (
                <p className="text-xs text-slate-400">Loading members...</p>
              ) : groupMembers.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-xs text-slate-500">
                  No users assigned to this access group yet.
                </div>
              ) : (
                <div className="max-h-60 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-800">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 text-left font-medium text-slate-500 dark:bg-slate-800/60">
                      <tr>
                        <th className="px-3 py-2">User ID / Email</th>
                        <th className="px-3 py-2">Role</th>
                        <th className="px-3 py-2 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {groupMembers.map((m) => {
                        const matchedUser = allUsers.find((u) => u.id === m.user_id)
                        return (
                          <tr key={m.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                            <td className="px-3 py-2.5 font-medium text-slate-800 dark:text-slate-200">
                              {matchedUser ? `${matchedUser.full_name || matchedUser.email} (${matchedUser.email})` : m.user_id}
                            </td>
                            <td className="px-3 py-2.5 text-slate-500">{m.role || 'member'}</td>
                            <td className="px-3 py-2.5 text-right">
                              <button
                                onClick={() => handleRemoveMember(m.user_id)}
                                title="Remove member"
                                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40"
                              >
                                <UserMinus className="h-3.5 w-3.5" />
                                Remove
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end pt-4 border-t border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setManagingGroup(null)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
