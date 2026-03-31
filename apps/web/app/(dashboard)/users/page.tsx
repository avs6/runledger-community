'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  Users, UserPlus, Trash2, RefreshCw, Search, X, Shield, Building2,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'

const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ── Shared styles ─────────────────────────────────────────────────────────────

const inputCls =
  'rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 px-3 py-1.5 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500'

const TABLE_HEAD =
  'px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400'

// ── Types ─────────────────────────────────────────────────────────────────────

interface WorkspaceUser {
  user_id: string
  workspace_id: string
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  last_login_at: string | null
  joined_at: string
}

interface OrgMember {
  user_id: string
  tenant_id: string
  role: string
  email: string
  full_name: string | null
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

type WorkspaceRoleOption = 'workspace_admin' | 'member' | 'viewer'

// ── Shared sub-components ─────────────────────────────────────────────────────

const WS_ROLE_COLORS: Record<string, string> = {
  workspace_admin: 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
  member: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  viewer: 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300',
}

const ORG_ROLE_COLORS: Record<string, string> = {
  org_admin: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  org_member: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
}

function RoleBadge({ role, colors }: { role: string; colors: Record<string, string> }) {
  const cls = colors[role] ?? colors.member ?? 'bg-slate-100 text-slate-700'
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {role === 'workspace_admin' && <Shield className="h-3 w-3" />}
      {role === 'org_admin' && <Shield className="h-3 w-3" />}
      {role.replace('_', ' ')}
    </span>
  )
}

function Avatar({ name, email, color = 'from-violet-500 to-indigo-500' }: { name: string | null; email: string; color?: string }) {
  const initial = ((name ?? email)[0] ?? '?').toUpperCase()
  return (
    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${color} text-white text-xs font-bold`}>
      {initial}
    </div>
  )
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${
      active
        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
        : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
    }`}>
      <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-emerald-500' : 'bg-slate-400'}`} />
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}

function SkeletonRows({ cols, rows = 5 }: { cols: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-4 py-3">
              <div className="h-4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

// ── Tab: Workspace Users ──────────────────────────────────────────────────────

function WorkspaceUsersTab({ apiKey }: { apiKey: string }) {
  const { isWorkspaceAdmin, isOrgAdmin, isPlatformAdmin } = useRole()

  const [users, setUsers] = useState<WorkspaceUser[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<'' | WorkspaceRoleOption>('')
  const [showInviteForm, setShowInviteForm] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<WorkspaceRoleOption>('member')
  const [inviting, setInviting] = useState(false)

  const headers = useMemo(
    () => ({ Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' }),
    [apiKey]
  )

  const load = useCallback(
    async (isRefresh = false) => {
      if (!apiKey) return
      isRefresh ? setRefreshing(true) : setLoading(true)
      try {
        const res = await fetch(`${apiBase}/users`, { headers })
        if (!res.ok) throw new Error(await res.text())
        setUsers(await res.json())
      } catch {
        toast.error('Failed to load users')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiKey]
  )

  useEffect(() => { load() }, [load])

  const afterFilters = useMemo(() => {
    if (!roleFilter) return users
    return users.filter((u) => u.role === roleFilter)
  }, [users, roleFilter])

  const filtered = useMemo(() => {
    if (!search.trim()) return afterFilters
    const q = search.toLowerCase()
    return afterFilters.filter(
      (u) => u.email.toLowerCase().includes(q) || (u.full_name ?? '').toLowerCase().includes(q)
    )
  }, [afterFilters, search])

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    if (!inviteEmail.trim()) return
    setInviting(true)
    try {
      const res = await fetch(`${apiBase}/users/invite`, {
        method: 'POST', headers,
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed to invite user')
      }
      const newUser: WorkspaceUser = await res.json()
      setUsers((prev) => [...prev, newUser])
      setInviteEmail('')
      setInviteRole('member')
      setShowInviteForm(false)
      toast.success(`${newUser.email} invited to workspace`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to invite user')
    } finally {
      setInviting(false)
    }
  }

  async function handleRoleChange(userId: string, role: WorkspaceRoleOption) {
    setUsers((prev) => prev.map((u) => (u.user_id === userId ? { ...u, role } : u)))
    try {
      const res = await fetch(`${apiBase}/users/${userId}/role`, {
        method: 'PUT', headers, body: JSON.stringify({ role }),
      })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed to update role')
      }
      toast.success('Role updated')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to update role')
      load()
    }
  }

  async function handleRemove(user: WorkspaceUser) {
    if (!confirm(`Remove ${user.email} from this workspace?`)) return
    try {
      const res = await fetch(`${apiBase}/users/${user.user_id}`, { method: 'DELETE', headers })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed to remove user')
      }
      setUsers((prev) => prev.filter((u) => u.user_id !== user.user_id))
      toast.success(`${user.email} removed from workspace`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to remove user')
    }
  }

  const canManage = isWorkspaceAdmin || isOrgAdmin || isPlatformAdmin

  const roleButtons: { value: '' | WorkspaceRoleOption; label: string }[] = [
    { value: '', label: 'All' },
    { value: 'workspace_admin', label: 'Admin' },
    { value: 'member', label: 'Member' },
    { value: 'viewer', label: 'Viewer' },
  ]

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[200px] flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or email…"
            className={`${inputCls} pl-8 w-full`}
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <div className="flex rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden text-sm shrink-0">
          {roleButtons.map(({ value, label }) => (
            <button key={value} onClick={() => setRoleFilter(value)}
              className={`px-3 py-1.5 transition-colors ${
                roleFilter === value
                  ? 'bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 font-medium'
                  : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <span className="text-xs text-slate-400 shrink-0">
          {filtered.length === users.length ? `${users.length} user${users.length !== 1 ? 's' : ''}` : (
            <span className="font-medium text-violet-600 dark:text-violet-400">{filtered.length} of {users.length}</span>
          )}
        </span>

        <div className="ml-auto flex items-center gap-2 shrink-0">
          <button onClick={() => load(true)} disabled={refreshing}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          {canManage && (
            <button
              onClick={() => { setShowInviteForm((v) => !v); setInviteEmail(''); setInviteRole('member') }}
              className="flex items-center gap-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 px-3 py-1.5 text-sm font-medium text-white transition-colors"
            >
              <UserPlus className="h-4 w-4" />
              Invite User
            </button>
          )}
        </div>
      </div>

      {/* Invite form */}
      {showInviteForm && canManage && (
        <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50 p-5">
          <div className="flex items-center gap-2 mb-4">
            <UserPlus className="h-4 w-4 text-violet-500" />
            <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Invite to workspace</span>
          </div>
          <form onSubmit={handleInvite} className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                Email address <span className="text-red-400">*</span>
              </label>
              <input type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="user@example.com" className={`${inputCls} w-full`} required autoFocus />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Role</label>
              <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value as WorkspaceRoleOption)} className={inputCls}>
                <option value="workspace_admin">Admin</option>
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <button type="submit" disabled={inviting || !inviteEmail.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50">
              <UserPlus className="h-3.5 w-3.5" />
              {inviting ? 'Sending…' : 'Send Invite'}
            </button>
            <button type="button" onClick={() => setShowInviteForm(false)}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
              Cancel
            </button>
          </form>
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
              <th className={TABLE_HEAD}>User</th>
              <th className={TABLE_HEAD}>Role</th>
              <th className={TABLE_HEAD}>Status</th>
              <th className={TABLE_HEAD}>Last Login</th>
              {canManage && <th className={TABLE_HEAD} />}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? (
              <SkeletonRows cols={canManage ? 5 : 4} />
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={canManage ? 5 : 4} className="px-4 py-14 text-center">
                  <Users className="mx-auto mb-2 h-8 w-8 text-slate-300 dark:text-slate-600" />
                  <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">
                    {users.length === 0 ? 'No users in this workspace yet.' : 'No users match your filters.'}
                  </p>
                  {users.length === 0 && canManage && (
                    <button onClick={() => setShowInviteForm(true)}
                      className="inline-flex items-center gap-1.5 text-sm text-violet-600 dark:text-violet-400 hover:underline">
                      <UserPlus className="h-4 w-4" /> Invite the first user
                    </button>
                  )}
                </td>
              </tr>
            ) : (
              filtered.map((user) => (
                <tr key={user.user_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <Avatar name={user.full_name} email={user.email} />
                      <div className="min-w-0">
                        <div className="font-medium text-slate-900 dark:text-slate-100 truncate">
                          {user.full_name ?? <span className="text-slate-400 italic">No name</span>}
                        </div>
                        <div className="text-xs text-slate-400 truncate">{user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {canManage ? (
                      <select value={user.role}
                        onChange={(e) => handleRoleChange(user.user_id, e.target.value as WorkspaceRoleOption)}
                        className={`rounded-full px-2 py-0.5 text-xs font-medium border-0 cursor-pointer focus:outline-none focus:ring-2 focus:ring-violet-500 ${WS_ROLE_COLORS[user.role] ?? WS_ROLE_COLORS.member}`}>
                        <option value="workspace_admin">Admin</option>
                        <option value="member">Member</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    ) : (
                      <RoleBadge role={user.role} colors={WS_ROLE_COLORS} />
                    )}
                  </td>
                  <td className="px-4 py-3"><StatusBadge active={user.is_active} /></td>
                  <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
                    {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never'}
                  </td>
                  {canManage && (
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => handleRemove(user)} title={`Remove ${user.email}`}
                        className="p-1.5 rounded-lg text-slate-300 dark:text-slate-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Tab: Org Members ──────────────────────────────────────────────────────────

function OrgMembersTab({ apiKey }: { apiKey: string }) {
  const [members, setMembers] = useState<OrgMember[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteFullName, setInviteFullName] = useState('')
  const [invitePassword, setInvitePassword] = useState('')
  const [inviteRole, setInviteRole] = useState<'org_admin' | 'org_member'>('org_member')
  const [inviting, setInviting] = useState(false)

  const headers = useMemo(
    () => ({ Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' }),
    [apiKey]
  )

  const load = useCallback(
    async (isRefresh = false) => {
      if (!apiKey) return
      isRefresh ? setRefreshing(true) : setLoading(true)
      try {
        const res = await fetch(`${apiBase}/org/members`, { headers })
        if (!res.ok) throw new Error(await res.text())
        setMembers(await res.json())
      } catch {
        toast.error('Failed to load organization members')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiKey]
  )

  useEffect(() => { load() }, [load])

  const filtered = useMemo(() => {
    if (!search.trim()) return members
    const q = search.toLowerCase()
    return members.filter(
      (m) => m.email.toLowerCase().includes(q) || (m.full_name ?? '').toLowerCase().includes(q)
    )
  }, [members, search])

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    if (!inviteEmail.trim() || !invitePassword.trim()) return
    setInviting(true)
    try {
      const res = await fetch(`${apiBase}/org/members/invite`, {
        method: 'POST', headers,
        body: JSON.stringify({
          email: inviteEmail.trim(),
          full_name: inviteFullName.trim() || null,
          temporary_password: invitePassword,
          role: inviteRole,
        }),
      })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      const member: OrgMember = await res.json()
      setMembers((prev) => [...prev, member])
      setInviteEmail(''); setInviteFullName(''); setInvitePassword('')
      setInviteRole('org_member'); setShowForm(false)
      toast.success(`${member.email} added to organization`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to add member')
    } finally {
      setInviting(false)
    }
  }

  async function handleRoleChange(userId: string, role: 'org_admin' | 'org_member') {
    setMembers((prev) => prev.map((m) => (m.user_id === userId ? { ...m, role } : m)))
    try {
      const res = await fetch(`${apiBase}/org/members/${userId}/role`, {
        method: 'PUT', headers, body: JSON.stringify({ role }),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success('Role updated')
    } catch {
      toast.error('Failed to update role')
      load()
    }
  }

  async function handleRemove(userId: string, email: string) {
    if (!confirm(`Remove ${email} from this organization?`)) return
    try {
      const res = await fetch(`${apiBase}/org/members/${userId}`, { method: 'DELETE', headers })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      setMembers((prev) => prev.filter((m) => m.user_id !== userId))
      toast.success(`${email} removed from organization`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to remove member')
    }
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[200px] flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search members…" className={`${inputCls} pl-8 w-full`} />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <span className="text-xs text-slate-400">
          {filtered.length === members.length ? `${members.length} member${members.length !== 1 ? 's' : ''}` : (
            <span className="font-medium text-violet-600 dark:text-violet-400">{filtered.length} of {members.length}</span>
          )}
        </span>

        <div className="ml-auto flex items-center gap-2 shrink-0">
          <button onClick={() => load(true)} disabled={refreshing}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button onClick={() => { setShowForm((v) => !v); setInviteEmail(''); setInvitePassword('') }}
            className="flex items-center gap-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 px-3 py-1.5 text-sm font-medium text-white transition-colors">
            <UserPlus className="h-4 w-4" />
            Add Member
          </button>
        </div>
      </div>

      {/* Add member form */}
      {showForm && (
        <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50 p-5">
          <div className="flex items-center gap-2 mb-4">
            <UserPlus className="h-4 w-4 text-violet-500" />
            <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Add to organization</span>
          </div>
          <form onSubmit={handleInvite} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <input type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="Email address *" className={inputCls} required autoFocus />
            <input value={inviteFullName} onChange={(e) => setInviteFullName(e.target.value)}
              placeholder="Full name (optional)" className={inputCls} />
            <input type="password" value={invitePassword} onChange={(e) => setInvitePassword(e.target.value)}
              placeholder="Temporary password *" className={inputCls} required />
            <div className="flex gap-2">
              <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value as 'org_admin' | 'org_member')}
                className={inputCls + ' flex-1'}>
                <option value="org_member">Member</option>
                <option value="org_admin">Org Admin</option>
              </select>
              <button type="submit" disabled={inviting || !inviteEmail.trim() || !invitePassword.trim()}
                className="flex items-center gap-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 whitespace-nowrap">
                <UserPlus className="h-3.5 w-3.5" />
                {inviting ? 'Adding…' : 'Add'}
              </button>
            </div>
          </form>
          <button onClick={() => setShowForm(false)} className="mt-2 text-xs text-slate-400 hover:text-slate-600">Cancel</button>
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
              <th className={TABLE_HEAD}>Member</th>
              <th className={TABLE_HEAD}>Org Role</th>
              <th className={TABLE_HEAD}>Status</th>
              <th className={TABLE_HEAD}>Last Login</th>
              <th className={TABLE_HEAD} />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? (
              <SkeletonRows cols={5} />
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-14 text-center">
                  <Building2 className="mx-auto mb-2 h-8 w-8 text-slate-300 dark:text-slate-600" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {members.length === 0 ? 'No organization members yet.' : 'No members match your search.'}
                  </p>
                </td>
              </tr>
            ) : (
              filtered.map((m) => (
                <tr key={m.user_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <Avatar name={m.full_name} email={m.email} color="from-indigo-400 to-violet-500" />
                      <div className="min-w-0">
                        <div className="font-medium text-slate-900 dark:text-slate-100 truncate">
                          {m.full_name ?? <span className="text-slate-400 italic">No name</span>}
                        </div>
                        <div className="text-xs text-slate-400 truncate">{m.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {m.role === 'org_admin' && <Shield className="h-3.5 w-3.5 text-amber-500" />}
                      <select value={m.role}
                        onChange={(e) => handleRoleChange(m.user_id, e.target.value as 'org_admin' | 'org_member')}
                        className={`rounded-full px-2 py-0.5 text-xs font-medium border-0 cursor-pointer focus:outline-none ${ORG_ROLE_COLORS[m.role] ?? ''}`}>
                        <option value="org_admin">Org Admin</option>
                        <option value="org_member">Member</option>
                      </select>
                    </div>
                  </td>
                  <td className="px-4 py-3"><StatusBadge active={m.is_active} /></td>
                  <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
                    {m.last_login_at ? new Date(m.last_login_at).toLocaleString() : 'Never'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleRemove(m.user_id, m.email)}
                      className="p-1.5 rounded-lg text-slate-300 dark:text-slate-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                      title="Remove from organization">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = 'workspace' | 'org'

export default function UsersPage() {
  const { data: session } = useSession()
  const { isOrgAdmin, isPlatformAdmin } = useRole()

  const apiKey = (session as unknown as Record<string, unknown>)?.apiKey as string ?? ''
  const [activeTab, setActiveTab] = useState<Tab>('workspace')

  const showOrgTab = isOrgAdmin || isPlatformAdmin

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Users</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Manage who has access to this workspace and organization.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setActiveTab('workspace')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
            activeTab === 'workspace'
              ? 'border-violet-500 text-violet-700 dark:text-violet-400'
              : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
          }`}
        >
          Workspace Users
        </button>
        {showOrgTab && (
          <button
            onClick={() => setActiveTab('org')}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'org'
                ? 'border-violet-500 text-violet-700 dark:text-violet-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
            }`}
          >
            Org Members
          </button>
        )}
      </div>

      {activeTab === 'workspace' && <WorkspaceUsersTab apiKey={apiKey} />}
      {activeTab === 'org' && showOrgTab && <OrgMembersTab apiKey={apiKey} />}
    </div>
  )
}
