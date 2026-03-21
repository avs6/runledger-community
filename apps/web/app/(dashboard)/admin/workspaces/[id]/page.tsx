'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useParams, useRouter } from 'next/navigation'
import {
  ArrowLeft, LayoutGrid, Users, RefreshCw, Search, Plus, Trash2,
  Save, Shield, ShieldOff, Archive, Building2, ChevronDown,
} from 'lucide-react'

// ── Types ────────────────────────────────────────────────────────────────────

interface Workspace {
  id: string
  tenant_id: string
  tenant_name: string
  name: string
  status: string
  is_restricted: boolean
  created_at: string
  member_count: number
}

interface Member {
  user_id: string
  email: string
  full_name: string
  is_active: boolean
  role: string
  status: string
}

interface AllUser {
  id: string
  email: string
  full_name: string
}

interface Org {
  id: string
  name: string
  is_default: boolean
}

// ── Constants ────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  suspended: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  archived: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
}

const WS_ROLES = [
  { value: 'workspace_admin', label: 'Admin' },
  { value: 'workspace_editor', label: 'Editor' },
  { value: 'workspace_contributor', label: 'Contributor' },
  { value: 'member', label: 'Member' },
  { value: 'viewer', label: 'Viewer' },
]

const ROLE_COLORS: Record<string, string> = {
  workspace_admin: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
  workspace_editor: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
  workspace_contributor: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  member: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  viewer: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
}

const ROLE_LABELS: Record<string, string> = {
  workspace_admin: 'Admin',
  workspace_editor: 'Editor',
  workspace_contributor: 'Contributor',
  member: 'Member',
  viewer: 'Viewer',
}

function inp(extra?: string) {
  return `mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500 ${extra ?? ''}`
}

type Tab = 'overview' | 'members'

// ── Page ─────────────────────────────────────────────────────────────────────

export default function WorkspaceDetailPage() {
  const { data: session } = useSession()
  const router = useRouter()
  const params = useParams()
  const workspaceId = params.id as string

  const s = session as Record<string, unknown> | null
  const apiKey = s?.apiKey as string
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const headers = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' }

  // ── Core state ──────────────────────────────────────────────────────────────
  const [tab, setTab] = useState<Tab>('overview')
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // ── Overview state ──────────────────────────────────────────────────────────
  const [editName, setEditName] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [orgs, setOrgs] = useState<Org[]>([])
  const [moveOrgId, setMoveOrgId] = useState('')
  const [movingOrg, setMovingOrg] = useState(false)
  const [moveMsg, setMoveMsg] = useState('')

  // ── Member state ─────────────────────────────────────────────────────────────
  const [members, setMembers] = useState<Member[]>([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [memberSearch, setMemberSearch] = useState('')
  const [memberPage, setMemberPage] = useState(0)
  const memberPageSize = 50
  const [memberHasMore, setMemberHasMore] = useState(false)
  const [showAddMember, setShowAddMember] = useState(false)
  const [allUsers, setAllUsers] = useState<AllUser[]>([])
  const [addUserId, setAddUserId] = useState('')
  const [addRole, setAddRole] = useState('member')
  const [addingMember, setAddingMember] = useState(false)
  const [memberError, setMemberError] = useState('')
  const [roleMenuFor, setRoleMenuFor] = useState<string | null>(null)

  // ── Load workspace ──────────────────────────────────────────────────────────
  const loadWorkspace = useCallback(async () => {
    if (!apiKey || !workspaceId) return
    setLoading(true)
    try {
      const r = await fetch(`${apiBase}/platform/workspaces/${workspaceId}`, { headers })
      if (!r.ok) { setError('Workspace not found'); return }
      const data: Workspace = await r.json()
      setWorkspace(data)
      setEditName(data.name)
      setMoveOrgId(data.tenant_id)
    } catch {
      setError('Failed to load workspace')
    } finally {
      setLoading(false)
    }
  }, [apiKey, workspaceId, apiBase])

  // ── Load members ─────────────────────────────────────────────────────────────
  const loadMembers = useCallback(async () => {
    if (!apiKey || !workspaceId) return
    setMembersLoading(true)
    try {
      const params = new URLSearchParams({
        skip: String(memberPage * memberPageSize),
        limit: String(memberPageSize + 1),
      })
      if (memberSearch) params.set('search', memberSearch)
      const r = await fetch(`${apiBase}/platform/workspaces/${workspaceId}/members?${params}`, { headers })
      if (r.ok) {
        const data: Member[] = await r.json()
        setMemberHasMore(data.length > memberPageSize)
        setMembers(data.slice(0, memberPageSize))
      }
    } finally {
      setMembersLoading(false)
    }
  }, [apiKey, workspaceId, apiBase, memberSearch, memberPage])

  const loadOrgs = async () => {
    if (orgs.length > 0) return
    const r = await fetch(`${apiBase}/platform/orgs?limit=200`, { headers })
    if (r.ok) setOrgs(await r.json())
  }

  const loadAllUsers = async () => {
    if (allUsers.length > 0) return
    const r = await fetch(`${apiBase}/platform/users?limit=200`, { headers })
    if (r.ok) setAllUsers(await r.json())
  }

  useEffect(() => { loadWorkspace() }, [loadWorkspace])
  useEffect(() => { if (tab === 'members') loadMembers() }, [tab, loadMembers])
  useEffect(() => { if (tab === 'members') { setMemberPage(0); loadMembers() } }, [memberSearch])

  // ── Save name ───────────────────────────────────────────────────────────────
  const handleSaveName = async () => {
    if (!workspace) return
    setSaving(true)
    setSaveMsg('')
    const r = await fetch(`${apiBase}/platform/workspaces/${workspace.id}`, {
      method: 'PUT', headers,
      body: JSON.stringify({ name: editName }),
    })
    setSaving(false)
    if (r.ok) {
      const updated: Workspace = await r.json()
      setWorkspace(updated)
      setSaveMsg('Saved')
      setTimeout(() => setSaveMsg(''), 2000)
    }
  }

  // ── Move org ────────────────────────────────────────────────────────────────
  const handleMoveOrg = async () => {
    if (!workspace || moveOrgId === workspace.tenant_id) return
    setMovingOrg(true)
    setMoveMsg('')
    const r = await fetch(`${apiBase}/platform/workspaces/${workspace.id}/org`, {
      method: 'PUT', headers,
      body: JSON.stringify({ tenant_id: moveOrgId }),
    })
    setMovingOrg(false)
    if (r.ok) {
      const updated: Workspace = await r.json()
      setWorkspace(updated)
      setMoveMsg(`Moved to ${updated.tenant_name}`)
      setTimeout(() => setMoveMsg(''), 3000)
    }
  }

  // ── Status ──────────────────────────────────────────────────────────────────
  const handleStatus = async (newStatus: string) => {
    if (!workspace) return
    const label = newStatus === 'active' ? 'Reactivate' : newStatus === 'suspended' ? 'Suspend' : 'Archive'
    if (!confirm(`${label} workspace "${workspace.name}"?`)) return
    const r = await fetch(`${apiBase}/platform/workspaces/${workspace.id}/status`, {
      method: 'PUT', headers,
      body: JSON.stringify({ status: newStatus }),
    })
    if (r.ok) setWorkspace(await r.json())
  }

  // ── Add member ──────────────────────────────────────────────────────────────
  const handleAddMember = async () => {
    if (!addUserId) return
    setAddingMember(true)
    setMemberError('')
    const r = await fetch(`${apiBase}/platform/workspaces/${workspaceId}/members`, {
      method: 'POST', headers,
      body: JSON.stringify({ user_id: addUserId, role: addRole }),
    })
    setAddingMember(false)
    if (!r.ok) {
      const d = await r.json().catch(() => ({}))
      setMemberError(d.detail || 'Failed to add member')
      return
    }
    setShowAddMember(false)
    setAddUserId('')
    setAddRole('member')
    await loadMembers()
    await loadWorkspace()
  }

  // ── Update role ─────────────────────────────────────────────────────────────
  const handleChangeRole = async (m: Member, newRole: string) => {
    setRoleMenuFor(null)
    const r = await fetch(`${apiBase}/platform/workspaces/${workspaceId}/members/${m.user_id}`, {
      method: 'PUT', headers,
      body: JSON.stringify({ user_id: m.user_id, role: newRole }),
    })
    if (r.ok) await loadMembers()
  }

  // ── Remove member ───────────────────────────────────────────────────────────
  const handleRemoveMember = async (m: Member) => {
    if (!confirm(`Remove ${m.full_name || m.email} from this workspace?`)) return
    const r = await fetch(`${apiBase}/platform/workspaces/${workspaceId}/members/${m.user_id}`, {
      method: 'DELETE', headers,
    })
    if (r.ok) {
      await loadMembers()
      await loadWorkspace()
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    )
  }

  if (error || !workspace) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <LayoutGrid className="h-12 w-12 text-slate-300" />
        <p className="text-slate-500">{error || 'Workspace not found'}</p>
        <button onClick={() => router.push('/admin/workspaces')} className="text-teal-600 text-sm hover:underline">
          Back to Workspaces
        </button>
      </div>
    )
  }

  const availableUsers = allUsers.filter(u => !members.some(m => m.user_id === u.id))

  return (
    <div className="space-y-6">
      {/* Breadcrumb + header */}
      <div>
        <button
          onClick={() => router.push('/admin/workspaces')}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 mb-3 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Workspaces
        </button>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400">
            <LayoutGrid className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{workspace.name}</h1>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_COLORS[workspace.status] || STATUS_COLORS.active}`}>
                {workspace.status ? workspace.status.charAt(0).toUpperCase() + workspace.status.slice(1) : 'Active'}
              </span>
              {workspace.is_restricted && (
                <span className="rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300 px-2 py-0.5 text-[11px] font-semibold">Restricted</span>
              )}
            </div>
            <button
              onClick={() => router.push(`/admin/tenants/${workspace.tenant_id}`)}
              className="flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors mt-0.5"
            >
              <Building2 className="h-3.5 w-3.5" /> {workspace.tenant_name}
            </button>
          </div>
          <div className="ml-auto flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400">
            <Users className="h-4 w-4" /> {workspace.member_count} members
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {(['overview', 'members'] as Tab[]).map(t => (
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
          {/* Edit name */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Workspace Details</h3>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Name</label>
              <input value={editName} onChange={e => setEditName(e.target.value)} className={inp()} />
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleSaveName}
                disabled={saving}
                className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
              >
                <Save className="h-4 w-4" />
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              {saveMsg && <span className="text-sm text-emerald-600 dark:text-emerald-400">{saveMsg}</span>}
            </div>
            <div className="pt-2 border-t border-slate-100 dark:border-slate-700">
              <p className="text-xs text-slate-400">Created {new Date(workspace.created_at).toLocaleDateString()}</p>
            </div>
          </div>

          {/* Move to org */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Organization Assignment</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Currently in <button onClick={() => router.push(`/admin/tenants/${workspace.tenant_id}`)} className="text-teal-600 hover:underline font-medium">{workspace.tenant_name}</button>.
              Move this workspace to a different organization.
            </p>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Move to Organization</label>
              <select
                value={moveOrgId}
                onChange={e => setMoveOrgId(e.target.value)}
                onFocus={loadOrgs}
                className={inp()}
              >
                {orgs.length === 0 && <option value={workspace.tenant_id}>{workspace.tenant_name} (current)</option>}
                {orgs.map(o => (
                  <option key={o.id} value={o.id}>
                    {o.name}{o.id === workspace.tenant_id ? ' (current)' : ''}{o.is_default ? ' — Default' : ''}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleMoveOrg}
                disabled={movingOrg || moveOrgId === workspace.tenant_id}
                className="flex items-center gap-2 rounded-lg bg-slate-700 dark:bg-slate-600 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 dark:hover:bg-slate-500 disabled:opacity-40 transition-colors"
              >
                <Building2 className="h-4 w-4" />
                {movingOrg ? 'Moving...' : 'Move Workspace'}
              </button>
              {moveMsg && <span className="text-sm text-emerald-600 dark:text-emerald-400">{moveMsg}</span>}
            </div>
          </div>

          {/* Status actions */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Status Management</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Current: <span className="font-semibold">{workspace.status?.charAt(0).toUpperCase() + workspace.status?.slice(1) || 'Active'}</span>
            </p>
            <div className="flex flex-col gap-2">
              {workspace.status !== 'active' && (
                <button onClick={() => handleStatus('active')} className="flex items-center gap-2 rounded-lg border border-emerald-200 px-4 py-2 text-sm text-emerald-700 hover:bg-emerald-50 dark:border-emerald-800 dark:text-emerald-400 dark:hover:bg-emerald-900/20 transition-colors">
                  <ShieldOff className="h-4 w-4" /> Reactivate
                </button>
              )}
              {workspace.status !== 'suspended' && (
                <button onClick={() => handleStatus('suspended')} className="flex items-center gap-2 rounded-lg border border-amber-200 px-4 py-2 text-sm text-amber-700 hover:bg-amber-50 dark:border-amber-800 dark:text-amber-400 dark:hover:bg-amber-900/20 transition-colors">
                  <Shield className="h-4 w-4" /> Suspend
                </button>
              )}
              {workspace.status !== 'archived' && (
                <button onClick={() => handleStatus('archived')} className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 transition-colors">
                  <Archive className="h-4 w-4" /> Archive
                </button>
              )}
            </div>
          </div>

          {/* Danger zone */}
          <div className="rounded-xl border border-red-200 dark:border-red-900/50 bg-white dark:bg-slate-800/50 p-5 space-y-3">
            <h3 className="text-sm font-semibold text-red-700 dark:text-red-400">Danger Zone</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Permanently delete this workspace and all its data.</p>
            <button
              onClick={() => {
                if (!confirm(`Delete workspace "${workspace.name}"? This cannot be undone.`)) return
                fetch(`${apiBase}/platform/workspaces/${workspace.id}`, { method: 'DELETE', headers })
                  .then(r => { if (r.ok) router.push('/admin/workspaces') })
              }}
              className="flex items-center gap-2 rounded-lg border border-red-200 dark:border-red-900/50 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            >
              <Trash2 className="h-4 w-4" /> Delete Workspace
            </button>
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
                placeholder="Search members by name or email..."
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
              <p className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Add Member to Workspace</p>
              {memberError && <p className="mb-2 text-sm text-red-600 dark:text-red-400">{memberError}</p>}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">User</label>
                  <select value={addUserId} onChange={e => setAddUserId(e.target.value)} className={inp()}>
                    <option value="">Select user…</option>
                    {availableUsers.map(u => (
                      <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Role</label>
                  <select value={addRole} onChange={e => setAddRole(e.target.value)} className={inp()}>
                    {WS_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={handleAddMember}
                  disabled={addingMember || !addUserId}
                  className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
                >
                  {addingMember ? 'Adding…' : 'Add Member'}
                </button>
                <button
                  onClick={() => { setShowAddMember(false); setAddUserId(''); setMemberError('') }}
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
              <>
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
                            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold shrink-0">
                              {(m.full_name || m.email).charAt(0).toUpperCase()}
                            </div>
                            <button
                              onClick={() => router.push(`/admin/users/${m.user_id}`)}
                              className="font-medium text-slate-900 dark:text-white hover:text-teal-600 dark:hover:text-teal-400 transition-colors"
                            >
                              {m.full_name || '—'}
                            </button>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{m.email}</td>
                        <td className="px-4 py-3">
                          <div className="relative inline-block">
                            <button
                              onClick={() => setRoleMenuFor(roleMenuFor === m.user_id ? null : m.user_id)}
                              className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${ROLE_COLORS[m.role] || ROLE_COLORS.member} hover:opacity-80 transition-opacity`}
                            >
                              {ROLE_LABELS[m.role] || m.role}
                              <ChevronDown className="h-3 w-3" />
                            </button>
                            {roleMenuFor === m.user_id && (
                              <>
                                <div className="fixed inset-0 z-10" onClick={() => setRoleMenuFor(null)} />
                                <div className="absolute left-0 top-full mt-1 z-20 w-44 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 shadow-lg py-1">
                                  {WS_ROLES.map(r => (
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
                          <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${m.is_active
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                            : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                            {m.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => handleRemoveMember(m)}
                            className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 transition-colors"
                            title="Remove from workspace"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Member pagination */}
                <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 dark:border-slate-700">
                  <p className="text-xs text-slate-500">Page {memberPage + 1} · {members.length} member{members.length !== 1 ? 's' : ''}</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setMemberPage(p => Math.max(0, p - 1))}
                      disabled={memberPage === 0}
                      className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
                    >
                      ← Prev
                    </button>
                    <button
                      onClick={() => setMemberPage(p => p + 1)}
                      disabled={!memberHasMore}
                      className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
                    >
                      Next →
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
