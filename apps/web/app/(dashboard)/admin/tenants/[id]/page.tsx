'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useParams, useRouter } from 'next/navigation'
import {
  ArrowLeft, Building2, LayoutGrid, Users, RefreshCw, Search,
  Plus, Trash2, X, Save, Shield, ShieldOff, Archive,
  ChevronDown,
} from 'lucide-react'

// ── Types ───────────────────────────────────────────────────────────────────

interface Tenant {
  id: string
  name: string
  plan: string
  status: 'active' | 'suspended' | 'archived'
  is_default: boolean
  owner_user_id: string | null
  created_at: string
  workspace_count: number
  member_count: number
}

interface Workspace {
  id: string
  tenant_id: string
  name: string
  slug?: string
  created_at: string
}

interface Member {
  user_id: string
  email: string
  full_name: string
  is_active: boolean
  is_platform_admin: boolean
  role: string
  status: string
}

interface AllUser {
  id: string
  email: string
  full_name: string
}

// ── Constants ────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  suspended: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  archived: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
}

const PLAN_COLORS: Record<string, string> = {
  free: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  starter: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  growth: 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
  enterprise: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
}

const PLANS = ['free', 'starter', 'growth', 'enterprise']

const ORG_ROLES = [
  { value: 'org_member', label: 'Member' },
  { value: 'org_manager', label: 'Manager' },
  { value: 'org_admin', label: 'Org Admin' },
  { value: 'org_billing_admin', label: 'Billing Admin' },
  { value: 'org_auditor', label: 'Auditor' },
]

const ROLE_LABELS: Record<string, string> = {
  org_admin: 'Org Admin',
  org_manager: 'Manager',
  org_member: 'Member',
  org_billing_admin: 'Billing Admin',
  org_auditor: 'Auditor',
}

const ROLE_COLORS: Record<string, string> = {
  org_admin: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
  org_manager: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
  org_member: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  org_billing_admin: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  org_auditor: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
}

function inp(extra?: string) {
  return `mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500 ${extra ?? ''}`
}

type Tab = 'overview' | 'workspaces' | 'members'

// ── Page ─────────────────────────────────────────────────────────────────────

export default function TenantDetailPage() {
  const { data: session } = useSession()
  const router = useRouter()
  const params = useParams()
  const tenantId = params.id as string

  const s = session as Record<string, unknown> | null
  const apiKey = s?.apiKey as string
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const headers = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' }

  // ── Core state ──────────────────────────────────────────────────────────────
  const [tab, setTab] = useState<Tab>('overview')
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // ── Overview state ──────────────────────────────────────────────────────────
  const [editForm, setEditForm] = useState({ name: '', plan: '' })
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')

  // ── Workspace state ─────────────────────────────────────────────────────────
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [wsLoading, setWsLoading] = useState(false)
  const [wsSearch, setWsSearch] = useState('')
  const [showAddWs, setShowAddWs] = useState(false)
  const [wsName, setWsName] = useState('')
  const [addingWs, setAddingWs] = useState(false)
  const [wsError, setWsError] = useState('')

  // ── Member state ─────────────────────────────────────────────────────────────
  const [members, setMembers] = useState<Member[]>([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [memberSearch, setMemberSearch] = useState('')
  const [showAddMember, setShowAddMember] = useState(false)
  const [allUsers, setAllUsers] = useState<AllUser[]>([])
  const [addMemberUserId, setAddMemberUserId] = useState('')
  const [addMemberRole, setAddMemberRole] = useState('org_member')
  const [addingMember, setAddingMember] = useState(false)
  const [memberError, setMemberError] = useState('')
  const [roleMenuFor, setRoleMenuFor] = useState<string | null>(null)

  // ── Load tenant ─────────────────────────────────────────────────────────────
  const loadTenant = useCallback(async () => {
    if (!apiKey || !tenantId) return
    setLoading(true)
    try {
      const r = await fetch(`${apiBase}/platform/orgs/${tenantId}`, { headers })
      if (!r.ok) { setError('Organization not found'); return }
      const data: Tenant = await r.json()
      setTenant(data)
      setEditForm({ name: data.name, plan: data.plan })
    } catch {
      setError('Failed to load organization')
    } finally {
      setLoading(false)
    }
  }, [apiKey, tenantId, apiBase])

  // ── Load workspaces ─────────────────────────────────────────────────────────
  const loadWorkspaces = useCallback(async () => {
    if (!apiKey || !tenantId) return
    setWsLoading(true)
    try {
      const r = await fetch(`${apiBase}/platform/orgs/${tenantId}/workspaces`, { headers })
      if (r.ok) setWorkspaces(await r.json())
    } finally {
      setWsLoading(false)
    }
  }, [apiKey, tenantId, apiBase])

  // ── Load members ─────────────────────────────────────────────────────────────
  const loadMembers = useCallback(async () => {
    if (!apiKey || !tenantId) return
    setMembersLoading(true)
    try {
      const url = `${apiBase}/platform/orgs/${tenantId}/members${memberSearch ? `?search=${encodeURIComponent(memberSearch)}` : ''}`
      const r = await fetch(url, { headers })
      if (r.ok) setMembers(await r.json())
    } finally {
      setMembersLoading(false)
    }
  }, [apiKey, tenantId, apiBase, memberSearch])

  useEffect(() => { loadTenant() }, [loadTenant])
  useEffect(() => { if (tab === 'workspaces') loadWorkspaces() }, [tab, loadWorkspaces])
  useEffect(() => { if (tab === 'members') loadMembers() }, [tab, loadMembers])
  useEffect(() => { if (tab === 'members') loadMembers() }, [memberSearch])

  // ── Overview: save ──────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (!tenant) return
    setSaving(true)
    setSaveMsg('')
    const r = await fetch(`${apiBase}/platform/orgs/${tenant.id}`, {
      method: 'PUT', headers,
      body: JSON.stringify({ name: editForm.name, plan: editForm.plan }),
    })
    setSaving(false)
    if (r.ok) {
      const updated = await r.json()
      setTenant(updated)
      setSaveMsg('Saved')
      setTimeout(() => setSaveMsg(''), 2000)
    }
  }

  // ── Overview: status ────────────────────────────────────────────────────────
  const handleStatus = async (newStatus: 'active' | 'suspended' | 'archived') => {
    if (!tenant) return
    const label = newStatus === 'active' ? 'Reactivate' : newStatus === 'suspended' ? 'Suspend' : 'Archive'
    if (!confirm(`${label} organization "${tenant.name}"?`)) return
    const r = await fetch(`${apiBase}/platform/orgs/${tenant.id}/status`, {
      method: 'PUT', headers,
      body: JSON.stringify({ status: newStatus }),
    })
    if (r.ok) setTenant(await r.json())
  }

  // ── Workspaces: add ─────────────────────────────────────────────────────────
  const handleAddWorkspace = async () => {
    if (!wsName.trim() || !tenant) return
    setAddingWs(true)
    setWsError('')
    const r = await fetch(`${apiBase}/platform/orgs/${tenant.id}/workspaces`, {
      method: 'POST', headers,
      body: JSON.stringify({ name: wsName.trim() }),
    })
    setAddingWs(false)
    if (!r.ok) {
      const d = await r.json().catch(() => ({}))
      setWsError(d.detail || 'Failed to add workspace')
      return
    }
    setWsName('')
    setShowAddWs(false)
    await loadWorkspaces()
    await loadTenant()
  }

  // ── Members: load all users for picker ──────────────────────────────────────
  const loadAllUsers = async () => {
    if (allUsers.length > 0) return
    const r = await fetch(`${apiBase}/platform/users?limit=200`, { headers })
    if (r.ok) setAllUsers(await r.json())
  }

  // ── Members: add ────────────────────────────────────────────────────────────
  const handleAddMember = async () => {
    if (!addMemberUserId) return
    setAddingMember(true)
    setMemberError('')
    const r = await fetch(`${apiBase}/platform/users/${addMemberUserId}/org-assignments`, {
      method: 'POST', headers,
      body: JSON.stringify({ tenant_id: tenantId, role: addMemberRole }),
    })
    setAddingMember(false)
    if (!r.ok) {
      const d = await r.json().catch(() => ({}))
      setMemberError(d.detail || 'Failed to add member')
      return
    }
    setShowAddMember(false)
    setAddMemberUserId('')
    setAddMemberRole('org_member')
    await loadMembers()
    await loadTenant()
  }

  // ── Members: remove ─────────────────────────────────────────────────────────
  const handleRemoveMember = async (m: Member) => {
    if (!confirm(`Remove ${m.full_name || m.email} from this organization?`)) return
    const r = await fetch(`${apiBase}/platform/users/${m.user_id}/org-assignments/${tenantId}`, {
      method: 'DELETE', headers,
    })
    if (r.ok) {
      await loadMembers()
      await loadTenant()
    }
  }

  // ── Members: change role ─────────────────────────────────────────────────────
  const handleChangeRole = async (m: Member, newRole: string) => {
    setRoleMenuFor(null)
    const r = await fetch(`${apiBase}/platform/users/${m.user_id}/org-assignments/${tenantId}`, {
      method: 'PUT', headers,
      body: JSON.stringify({ tenant_id: tenantId, role: newRole }),
    })
    if (r.ok) await loadMembers()
  }

  // ── Workspaces: filter ──────────────────────────────────────────────────────
  const filteredWs = workspaces.filter(w =>
    !wsSearch || w.name.toLowerCase().includes(wsSearch.toLowerCase())
  )

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    )
  }

  if (error || !tenant) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <Building2 className="h-12 w-12 text-slate-300" />
        <p className="text-slate-500">{error || 'Organization not found'}</p>
        <button onClick={() => router.push('/admin/tenants')} className="text-teal-600 text-sm hover:underline">
          Back to Organizations
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb + header */}
      <div>
        <button
          onClick={() => router.push('/admin/tenants')}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 mb-3 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Organizations
        </button>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-teal-400 to-cyan-500 text-white font-bold">
            {tenant.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{tenant.name}</h1>
              {tenant.is_default && (
                <span className="rounded-full bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400 px-2 py-0.5 text-[10px] font-semibold">
                  Default
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${PLAN_COLORS[tenant.plan] || PLAN_COLORS.free}`}>
                {tenant.plan.charAt(0).toUpperCase() + tenant.plan.slice(1)}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_COLORS[tenant.status] || STATUS_COLORS.active}`}>
                {tenant.status ? tenant.status.charAt(0).toUpperCase() + tenant.status.slice(1) : 'Active'}
              </span>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-1"><LayoutGrid className="h-4 w-4" /> {tenant.workspace_count} workspaces</div>
            <div className="flex items-center gap-1"><Users className="h-4 w-4" /> {tenant.member_count} members</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {(['overview', 'workspaces', 'members'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t
                ? 'border-teal-600 text-teal-700 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ── Overview tab ──────────────────────────────────────────────────────── */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Edit form */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Organization Details</h3>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Name</label>
              <input value={editForm.name} onChange={e => setEditForm({ ...editForm, name: e.target.value })} className={inp()} />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Plan</label>
              <select value={editForm.plan} onChange={e => setEditForm({ ...editForm, plan: e.target.value })} className={inp()}>
                {PLANS.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
              >
                <Save className="h-4 w-4" />
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              {saveMsg && <span className="text-sm text-emerald-600 dark:text-emerald-400">{saveMsg}</span>}
            </div>
          </div>

          {/* Status actions */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Status Management</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Current status: <span className={`font-semibold ${STATUS_COLORS[tenant.status]?.split(' ')[1] || ''}`}>
                {tenant.status?.charAt(0).toUpperCase() + tenant.status?.slice(1) || 'Active'}
              </span>
            </p>
            {!tenant.is_default && (
              <div className="flex flex-col gap-2">
                {tenant.status !== 'active' && (
                  <button
                    onClick={() => handleStatus('active')}
                    className="flex items-center gap-2 rounded-lg border border-emerald-200 px-4 py-2 text-sm text-emerald-700 hover:bg-emerald-50 dark:border-emerald-800 dark:text-emerald-400 dark:hover:bg-emerald-900/20 transition-colors"
                  >
                    <ShieldOff className="h-4 w-4" /> Reactivate Organization
                  </button>
                )}
                {tenant.status !== 'suspended' && (
                  <button
                    onClick={() => handleStatus('suspended')}
                    className="flex items-center gap-2 rounded-lg border border-amber-200 px-4 py-2 text-sm text-amber-700 hover:bg-amber-50 dark:border-amber-800 dark:text-amber-400 dark:hover:bg-amber-900/20 transition-colors"
                  >
                    <Shield className="h-4 w-4" /> Suspend Organization
                  </button>
                )}
                {tenant.status !== 'archived' && (
                  <button
                    onClick={() => handleStatus('archived')}
                    className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 transition-colors"
                  >
                    <Archive className="h-4 w-4" /> Archive Organization
                  </button>
                )}
              </div>
            )}
            {tenant.is_default && (
              <p className="text-xs text-slate-400">The default organization status cannot be changed.</p>
            )}
            <div className="pt-2 border-t border-slate-100 dark:border-slate-700">
              <p className="text-xs text-slate-400 mb-2">
                Created {new Date(tenant.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Workspaces tab ─────────────────────────────────────────────────────── */}
      {tab === 'workspaces' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                value={wsSearch}
                onChange={e => setWsSearch(e.target.value)}
                placeholder="Search workspaces..."
                className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
            <button
              onClick={() => { setShowAddWs(true); setWsError('') }}
              className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 transition-colors whitespace-nowrap"
            >
              <Plus className="h-4 w-4" /> Add Workspace
            </button>
          </div>

          {showAddWs && (
            <div className="rounded-xl border border-teal-200 bg-teal-50/50 dark:border-teal-800 dark:bg-teal-900/10 p-4">
              <p className="text-sm font-semibold text-slate-900 dark:text-white mb-3">New Workspace</p>
              {wsError && <p className="mb-2 text-sm text-red-600 dark:text-red-400">{wsError}</p>}
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Workspace Name</label>
                  <input
                    value={wsName}
                    onChange={e => setWsName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleAddWorkspace()}
                    placeholder="e.g. Production"
                    autoFocus
                    className={inp()}
                  />
                </div>
                <button
                  onClick={handleAddWorkspace}
                  disabled={addingWs || !wsName.trim()}
                  className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
                >
                  {addingWs ? 'Adding…' : 'Add'}
                </button>
                <button
                  onClick={() => { setShowAddWs(false); setWsName(''); setWsError('') }}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800/50 overflow-hidden">
            {wsLoading ? (
              <div className="flex items-center justify-center py-16">
                <RefreshCw className="h-5 w-5 animate-spin text-slate-400" />
              </div>
            ) : filteredWs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <LayoutGrid className="h-10 w-10 text-slate-300 dark:text-slate-600" />
                <p className="text-sm text-slate-500">{wsSearch ? 'No workspaces match your search' : 'No workspaces yet'}</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Workspace</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Created</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                  {filteredWs.map(ws => (
                    <tr key={ws.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400">
                            <LayoutGrid className="h-3.5 w-3.5" />
                          </div>
                          <span className="font-medium text-slate-900 dark:text-white">{ws.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs">
                        {new Date(ws.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => {
                            if (!confirm(`Delete workspace "${ws.name}"? This cannot be undone.`)) return
                            fetch(`${apiBase}/platform/workspaces/${ws.id}`, { method: 'DELETE', headers })
                              .then(() => loadWorkspaces())
                          }}
                          className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 transition-colors"
                          title="Delete workspace"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ── Members tab ───────────────────────────────────────────────────────── */}
      {tab === 'members' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                value={memberSearch}
                onChange={e => setMemberSearch(e.target.value)}
                placeholder="Search members..."
                className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
            <button
              onClick={() => { setShowAddMember(true); loadAllUsers(); setMemberError('') }}
              className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 transition-colors whitespace-nowrap"
            >
              <Plus className="h-4 w-4" /> Add Member
            </button>
          </div>

          {showAddMember && (
            <div className="rounded-xl border border-teal-200 bg-teal-50/50 dark:border-teal-800 dark:bg-teal-900/10 p-4">
              <p className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Add Member to Organization</p>
              {memberError && <p className="mb-2 text-sm text-red-600 dark:text-red-400">{memberError}</p>}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">User</label>
                  <select value={addMemberUserId} onChange={e => setAddMemberUserId(e.target.value)} className={inp()}>
                    <option value="">Select user…</option>
                    {allUsers
                      .filter(u => !members.some(m => m.user_id === u.id))
                      .map(u => (
                        <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
                      ))
                    }
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Role</label>
                  <select value={addMemberRole} onChange={e => setAddMemberRole(e.target.value)} className={inp()}>
                    {ORG_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={handleAddMember}
                  disabled={addingMember || !addMemberUserId}
                  className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
                >
                  {addingMember ? 'Adding…' : 'Add Member'}
                </button>
                <button
                  onClick={() => { setShowAddMember(false); setAddMemberUserId(''); setMemberError('') }}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800/50 overflow-hidden">
            {membersLoading ? (
              <div className="flex items-center justify-center py-16">
                <RefreshCw className="h-5 w-5 animate-spin text-slate-400" />
              </div>
            ) : members.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <Users className="h-10 w-10 text-slate-300 dark:text-slate-600" />
                <p className="text-sm text-slate-500">{memberSearch ? 'No members match your search' : 'No members yet'}</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">User</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Email</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Role</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                  {members.map(m => (
                    <tr key={m.user_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold">
                            {(m.full_name || m.email).charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium text-slate-900 dark:text-white">{m.full_name || '—'}</p>
                            {m.is_platform_admin && (
                              <span className="text-[10px] text-violet-600 dark:text-violet-400 font-medium">Platform Admin</span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{m.email}</td>
                      <td className="px-4 py-3">
                        <div className="relative inline-block">
                          <button
                            onClick={() => setRoleMenuFor(roleMenuFor === m.user_id ? null : m.user_id)}
                            className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${ROLE_COLORS[m.role] || ROLE_COLORS.org_member} hover:opacity-80 transition-opacity`}
                          >
                            {ROLE_LABELS[m.role] || m.role}
                            <ChevronDown className="h-3 w-3" />
                          </button>
                          {roleMenuFor === m.user_id && (
                            <>
                              <div className="fixed inset-0 z-10" onClick={() => setRoleMenuFor(null)} />
                              <div className="absolute left-0 top-full mt-1 z-20 w-44 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 shadow-lg py-1">
                                {ORG_ROLES.map(r => (
                                  <button
                                    key={r.value}
                                    onClick={() => handleChangeRole(m, r.value)}
                                    className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${m.role === r.value ? 'text-teal-600 font-semibold' : 'text-slate-700 dark:text-slate-300'}`}
                                  >
                                    {r.label}
                                  </button>
                                ))}
                              </div>
                            </>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${m.status === 'active' || !m.status ? STATUS_COLORS.active : STATUS_COLORS[m.status] || STATUS_COLORS.active}`}>
                          {m.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => router.push(`/admin/users/${m.user_id}`)}
                            className="rounded-lg px-2.5 py-1.5 text-xs text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 font-medium transition-colors"
                          >
                            View
                          </button>
                          <button
                            onClick={() => handleRemoveMember(m)}
                            className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 transition-colors"
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
        </div>
      )}
    </div>
  )
}
