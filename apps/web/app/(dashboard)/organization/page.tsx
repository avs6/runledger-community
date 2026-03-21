'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  Building2, FolderOpen, Users, Plus, Trash2, RefreshCw,
  Shield, UserPlus, Search, X, ChevronDown, ChevronUp, Check,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'

const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ── Types ─────────────────────────────────────────────────────────────────────

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
  created_at: string
}

interface OrgMember {
  user_id: string
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

interface WorkspaceMember {
  user_id: string
  email: string
  full_name: string | null
  role: string
}

type WsRole = 'workspace_admin' | 'member' | 'viewer'

// ── Styles ────────────────────────────────────────────────────────────────────

const inputCls =
  'rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 px-3 py-1.5 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500'

const TABLE_HEAD =
  'px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400'

const PLAN_COLORS: Record<string, string> = {
  free: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  pro: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  enterprise: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
}

const WS_ROLE_COLORS: Record<string, string> = {
  workspace_admin: 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
  member: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  viewer: 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300',
}

const ORG_ROLE_COLORS: Record<string, string> = {
  org_admin: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  org_member: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
}

// ── Shared sub-components ─────────────────────────────────────────────────────

function Avatar({
  name, email, color = 'from-teal-400 to-cyan-500',
}: { name: string | null; email: string; color?: string }) {
  const ch = ((name ?? email)[0] ?? '?').toUpperCase()
  return (
    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${color} text-white text-xs font-bold`}>
      {ch}
    </div>
  )
}

function StatusDot({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
      active
        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
        : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
    }`}>
      <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-emerald-500' : 'bg-slate-400'}`} />
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}

function SkeletonRows({ cols, rows = 4 }: { cols: number; rows?: number }) {
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

// ── Profile Tab ───────────────────────────────────────────────────────────────

function ProfileTab({ headers }: { headers: Record<string, string> }) {
  const [profile, setProfile] = useState<OrgProfile | null>(null)
  const [editName, setEditName] = useState('')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${apiBase}/org/profile`, { headers })
      .then((r) => r.json())
      .then((p) => { setProfile(p); setEditName(p.name) })
      .catch(() => toast.error('Failed to load organization profile'))
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!editName.trim()) return
    setSaving(true)
    try {
      const r = await fetch(`${apiBase}/org/profile`, {
        method: 'PUT', headers,
        body: JSON.stringify({ name: editName.trim() }),
      })
      if (!r.ok) throw new Error(await r.text())
      const updated = await r.json()
      setProfile(updated)
      toast.success('Organization updated')
    } catch {
      toast.error('Failed to update organization')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 animate-pulse h-40" />
  }

  const planLabel = profile?.plan
    ? profile.plan.charAt(0).toUpperCase() + profile.plan.slice(1)
    : ''

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500 to-cyan-600 text-white text-2xl font-bold shadow-sm">
            {profile?.name?.[0]?.toUpperCase() ?? '?'}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{profile?.name ?? '—'}</h2>
            <div className="flex items-center gap-2 mt-1">
              {profile?.plan && (
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PLAN_COLORS[profile.plan] ?? ''}`}>
                  {planLabel} Plan
                </span>
              )}
              {profile?.is_default && (
                <span className="rounded-full bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 px-2 py-0.5 text-xs font-medium">
                  Default
                </span>
              )}
              {profile?.created_at && (
                <span className="text-xs text-slate-400">
                  Since {new Date(profile.created_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="border-t border-slate-100 dark:border-slate-800 pt-5">
          <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-4">Edit Organization</h3>
          <form onSubmit={handleSave} className="flex items-end gap-3 max-w-lg">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                Organization Name
              </label>
              <input
                className={`${inputCls} w-full`}
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="My Organization"
                required
              />
            </div>
            <button
              type="submit"
              disabled={saving || editName.trim() === profile?.name}
              className="rounded-lg bg-teal-600 hover:bg-teal-700 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </form>
        </div>
      </div>

      {/* Org details */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-4">Details</h3>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <dt className="text-xs text-slate-400 mb-0.5">Organization ID</dt>
            <dd className="text-sm font-mono text-slate-700 dark:text-slate-300">{profile?.id ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400 mb-0.5">Plan</dt>
            <dd><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PLAN_COLORS[profile?.plan ?? ''] ?? ''}`}>{planLabel}</span></dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400 mb-0.5">Default Org</dt>
            <dd className="text-sm text-slate-700 dark:text-slate-300">{profile?.is_default ? 'Yes' : 'No'}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400 mb-0.5">Created</dt>
            <dd className="text-sm text-slate-700 dark:text-slate-300">
              {profile?.created_at ? new Date(profile.created_at).toLocaleString() : '—'}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  )
}

// ── Workspace members inline panel ────────────────────────────────────────────

function WorkspaceMemberPanel({
  workspace, headers,
}: { workspace: OrgWorkspace; headers: Record<string, string> }) {
  const [open, setOpen] = useState(false)
  const [members, setMembers] = useState<WorkspaceMember[]>([])
  const [orgMembers, setOrgMembers] = useState<OrgMember[]>([])
  const [loaded, setLoaded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [adding, setAdding] = useState<Record<string, boolean>>({})
  const [selectedRole, setSelectedRole] = useState<Record<string, WsRole>>({})
  const [showAddForm, setShowAddForm] = useState(false)

  async function load() {
    if (loaded) { setOpen((v) => !v); return }
    setLoading(true)
    try {
      const [wmRes, omRes] = await Promise.all([
        fetch(`${apiBase}/org/workspaces/${workspace.id}/members`, { headers }),
        fetch(`${apiBase}/org/members`, { headers }),
      ])
      setMembers(wmRes.ok ? await wmRes.json() : [])
      setOrgMembers(omRes.ok ? await omRes.json() : [])
      setLoaded(true)
      setOpen(true)
    } catch {
      toast.error('Failed to load workspace members')
    } finally {
      setLoading(false)
    }
  }

  async function handleAdd(member: OrgMember) {
    const role = selectedRole[member.user_id] ?? 'member'
    setAdding((prev) => ({ ...prev, [member.user_id]: true }))
    try {
      const res = await fetch(`${apiBase}/org/workspaces/${workspace.id}/members`, {
        method: 'POST', headers,
        body: JSON.stringify({ user_id: member.user_id, role }),
      })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      const wm: WorkspaceMember = await res.json()
      setMembers((prev) => [...prev, wm])
      toast.success(`${member.email} added`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to add member')
    } finally {
      setAdding((prev) => ({ ...prev, [member.user_id]: false }))
    }
  }

  async function handleRemove(userId: string, email: string) {
    if (!confirm(`Remove ${email} from workspace "${workspace.name}"?`)) return
    try {
      const res = await fetch(`${apiBase}/org/workspaces/${workspace.id}/members/${userId}`, {
        method: 'DELETE', headers,
      })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      setMembers((prev) => prev.filter((m) => m.user_id !== userId))
      toast.success(`${email} removed`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to remove member')
    }
  }

  const alreadyInWs = useMemo(() => new Set(members.map((m) => m.user_id)), [members])
  const eligible = orgMembers.filter((m) => !alreadyInWs.has(m.user_id))

  return (
    <div>
      <button
        onClick={load}
        disabled={loading}
        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors mt-2"
      >
        <Users className="h-3 w-3" />
        {loading ? 'Loading…' : loaded ? `${members.length} member${members.length !== 1 ? 's' : ''}` : 'Manage members'}
        {loaded && (open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
      </button>

      {open && loaded && (
        <div className="mt-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 p-3 space-y-2">
          {/* Current members */}
          {members.length === 0 ? (
            <p className="text-xs text-slate-400">No members yet.</p>
          ) : (
            members.map((m) => (
              <div key={m.user_id} className="flex items-center gap-2 rounded bg-white dark:bg-slate-900 px-2.5 py-1.5 border border-slate-100 dark:border-slate-700">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-teal-400 to-cyan-500 text-white text-[10px] font-bold uppercase">
                  {((m.full_name ?? m.email)[0] ?? '?').toUpperCase()}
                </div>
                <span className="flex-1 text-xs text-slate-700 dark:text-slate-300 truncate">
                  {m.full_name ?? m.email}
                </span>
                <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${WS_ROLE_COLORS[m.role] ?? WS_ROLE_COLORS.member}`}>
                  {m.role.replace('workspace_', '')}
                </span>
                <button onClick={() => handleRemove(m.user_id, m.email)}
                  className="p-0.5 text-slate-300 hover:text-red-500 transition-colors">
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))
          )}

          {/* Add member */}
          <button
            onClick={() => setShowAddForm((v) => !v)}
            className="flex items-center gap-1 text-xs text-teal-600 dark:text-teal-400 hover:underline"
          >
            <UserPlus className="h-3 w-3" />
            {showAddForm ? 'Cancel' : 'Add member'}
          </button>

          {showAddForm && eligible.length === 0 && (
            <p className="text-xs text-slate-400">All org members are already in this workspace.</p>
          )}

          {showAddForm && eligible.map((m) => (
            <div key={m.user_id} className="flex items-center gap-2 rounded bg-white dark:bg-slate-900 px-2.5 py-1.5 border border-dashed border-slate-200 dark:border-slate-700">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 text-white text-[10px] font-bold uppercase">
                {((m.full_name ?? m.email)[0] ?? '?').toUpperCase()}
              </div>
              <span className="flex-1 text-xs text-slate-700 dark:text-slate-300 truncate">{m.full_name ?? m.email}</span>
              <select
                value={selectedRole[m.user_id] ?? 'member'}
                onChange={(e) => setSelectedRole((prev) => ({ ...prev, [m.user_id]: e.target.value as WsRole }))}
                className="rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-1.5 py-0.5 text-xs"
              >
                <option value="workspace_admin">Admin</option>
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
              </select>
              <button
                onClick={() => handleAdd(m)}
                disabled={adding[m.user_id]}
                className="flex items-center gap-0.5 rounded bg-teal-600 hover:bg-teal-700 disabled:opacity-50 px-2 py-0.5 text-[10px] font-medium text-white"
              >
                <Check className="h-2.5 w-2.5" />
                {adding[m.user_id] ? '…' : 'Add'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Workspaces Tab ────────────────────────────────────────────────────────────

function WorkspacesTab({ headers }: { headers: Record<string, string> }) {
  const [workspaces, setWorkspaces] = useState<OrgWorkspace[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [newlyCreatedWs, setNewlyCreatedWs] = useState<OrgWorkspace | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${apiBase}/org/workspaces`, { headers })
      if (!res.ok) throw new Error()
      setWorkspaces(await res.json())
    } catch {
      toast.error('Failed to load workspaces')
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => { load() }, [load])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    setCreating(true)
    try {
      const res = await fetch(`${apiBase}/org/workspaces`, {
        method: 'POST', headers, body: JSON.stringify({ name: newName.trim() }),
      })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      const ws: OrgWorkspace = await res.json()
      setWorkspaces((prev) => [...prev, ws])
      setNewName('')
      setShowForm(false)
      setNewlyCreatedWs(ws)
      toast.success(`Workspace "${ws.name}" created`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to create workspace')
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(ws: OrgWorkspace) {
    if (!confirm(`Delete workspace "${ws.name}"? All data will be lost.`)) return
    try {
      const res = await fetch(`${apiBase}/org/workspaces/${ws.id}`, { method: 'DELETE', headers })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      setWorkspaces((prev) => prev.filter((w) => w.id !== ws.id))
      if (newlyCreatedWs?.id === ws.id) setNewlyCreatedWs(null)
      toast.success(`Workspace "${ws.name}" deleted`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete workspace')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-xs text-slate-400 ml-auto">{workspaces.length} workspace{workspaces.length !== 1 ? 's' : ''}</span>
        <button
          onClick={() => { setShowForm((v) => !v); setNewName('') }}
          className="flex items-center gap-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 px-3 py-1.5 text-sm font-medium text-white transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Workspace
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <form onSubmit={handleCreate} className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Workspace name</label>
              <input className={`${inputCls} w-full`} value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Production, Staging…" autoFocus required />
            </div>
            <button type="submit" disabled={creating || !newName.trim()}
              className="rounded-lg bg-teal-600 hover:bg-teal-700 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50">
              {creating ? 'Creating…' : 'Create'}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50">
              Cancel
            </button>
          </form>
        </div>
      )}

      {/* Newly created — show assign members inline */}
      {newlyCreatedWs && (
        <div className="rounded-xl border border-teal-200 dark:border-teal-800 bg-teal-50 dark:bg-teal-950/30 p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-teal-800 dark:text-teal-200">
              &ldquo;{newlyCreatedWs.name}&rdquo; created — assign members below
            </p>
            <button onClick={() => setNewlyCreatedWs(null)}
              className="text-xs text-teal-600 dark:text-teal-400 hover:underline">Done</button>
          </div>
          <WorkspaceMemberPanel workspace={newlyCreatedWs} headers={headers} />
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        {loading ? (
          <div className="p-8 text-center">
            <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
          </div>
        ) : workspaces.length === 0 ? (
          <div className="p-10 text-center">
            <FolderOpen className="mx-auto mb-3 h-8 w-8 text-slate-300 dark:text-slate-600" />
            <p className="text-sm text-slate-400">No workspaces yet.</p>
            <button onClick={() => setShowForm(true)}
              className="mt-2 text-sm text-teal-600 dark:text-teal-400 hover:underline">
              Create the first workspace
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                <th className={TABLE_HEAD}>Workspace</th>
                <th className={TABLE_HEAD}>Created</th>
                <th className={TABLE_HEAD}>Members</th>
                <th className={TABLE_HEAD} />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {workspaces.map((ws) => (
                <tr key={ws.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-400 to-cyan-500 text-white text-xs font-bold uppercase">
                        {ws.name[0] ?? '?'}
                      </div>
                      <span className="font-medium text-slate-900 dark:text-white">{ws.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">{new Date(ws.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <WorkspaceMemberPanel workspace={ws} headers={headers} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(ws)}
                      disabled={workspaces.length <= 1}
                      title={workspaces.length <= 1 ? 'Cannot delete the last workspace' : `Delete "${ws.name}"`}
                      className="p-1.5 rounded-lg text-slate-300 dark:text-slate-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
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
  )
}

// ── Members Tab ───────────────────────────────────────────────────────────────

function MembersTab({ headers }: { headers: Record<string, string> }) {
  const [members, setMembers] = useState<OrgMember[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'org_member' as 'org_admin' | 'org_member' })
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(async (isRefresh = false) => {
    isRefresh ? setRefreshing(true) : setLoading(true)
    try {
      const res = await fetch(`${apiBase}/org/members`, { headers })
      if (!res.ok) throw new Error()
      setMembers(await res.json())
    } catch {
      toast.error('Failed to load members')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = useMemo(() => {
    if (!search.trim()) return members
    const q = search.toLowerCase()
    return members.filter((m) =>
      m.email.toLowerCase().includes(q) || (m.full_name ?? '').toLowerCase().includes(q)
    )
  }, [members, search])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!form.email.trim() || !form.password.trim()) return
    setSubmitting(true)
    try {
      const res = await fetch(`${apiBase}/org/members/invite`, {
        method: 'POST', headers,
        body: JSON.stringify({
          email: form.email.trim(),
          full_name: form.full_name.trim() || null,
          temporary_password: form.password,
          role: form.role,
        }),
      })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed')
      }
      const member: OrgMember = await res.json()
      setMembers((prev) => [...prev, member])
      setForm({ email: '', full_name: '', password: '', role: 'org_member' })
      setShowForm(false)
      toast.success(`${member.email} added to organization`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to add member')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRoleChange(userId: string, role: 'org_admin' | 'org_member') {
    setMembers((prev) => prev.map((m) => (m.user_id === userId ? { ...m, role } : m)))
    try {
      const res = await fetch(`${apiBase}/org/members/${userId}/role`, {
        method: 'PUT', headers, body: JSON.stringify({ role }),
      })
      if (!res.ok) throw new Error()
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
      toast.success(`${email} removed`)
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
          {filtered.length === members.length
            ? `${members.length} member${members.length !== 1 ? 's' : ''}`
            : <span className="text-teal-600 dark:text-teal-400 font-medium">{filtered.length} of {members.length}</span>}
        </span>
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => load(true)} disabled={refreshing}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => { setShowForm((v) => !v); setForm({ email: '', full_name: '', password: '', role: 'org_member' }) }}
            className="flex items-center gap-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 px-3 py-1.5 text-sm font-medium text-white transition-colors"
          >
            <UserPlus className="h-4 w-4" />
            Add Member
          </button>
        </div>
      </div>

      {/* Add member form */}
      {showForm && (
        <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50 p-5">
          <div className="flex items-center gap-2 mb-4">
            <UserPlus className="h-4 w-4 text-teal-500" />
            <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Add to organization</span>
          </div>
          <form onSubmit={handleAdd} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <input type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              placeholder="Email address *" className={inputCls} required autoFocus />
            <input value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
              placeholder="Full name (optional)" className={inputCls} />
            <input type="password" value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              placeholder="Temporary password *" className={inputCls} required />
            <div className="flex gap-2">
              <select value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as 'org_admin' | 'org_member' }))}
                className={`${inputCls} flex-1`}>
                <option value="org_member">Member</option>
                <option value="org_admin">Org Admin</option>
              </select>
              <button type="submit" disabled={submitting || !form.email.trim() || !form.password.trim()}
                className="flex items-center gap-1 rounded-lg bg-teal-600 hover:bg-teal-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 whitespace-nowrap">
                <UserPlus className="h-3.5 w-3.5" />
                {submitting ? 'Adding…' : 'Add'}
              </button>
            </div>
          </form>
          <button onClick={() => setShowForm(false)} className="mt-2 text-xs text-slate-400 hover:text-slate-600">Cancel</button>
        </div>
      )}

      {/* Members table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
              <th className={TABLE_HEAD}>Member</th>
              <th className={TABLE_HEAD}>Org Role</th>
              <th className={TABLE_HEAD}>Status</th>
              <th className={TABLE_HEAD}>Last Login</th>
              <th className={TABLE_HEAD}>Joined</th>
              <th className={TABLE_HEAD} />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? (
              <SkeletonRows cols={6} />
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-14 text-center">
                  <Users className="mx-auto mb-2 h-8 w-8 text-slate-300 dark:text-slate-600" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {members.length === 0 ? 'No organization members yet.' : 'No members match your search.'}
                  </p>
                  {members.length === 0 && (
                    <button onClick={() => setShowForm(true)}
                      className="mt-2 flex items-center gap-1.5 mx-auto text-sm text-teal-600 dark:text-teal-400 hover:underline">
                      <UserPlus className="h-4 w-4" /> Add first member
                    </button>
                  )}
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
                          {m.full_name ?? <span className="text-slate-400 italic text-sm">No name</span>}
                        </div>
                        <div className="text-xs text-slate-400 truncate">{m.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {m.role === 'org_admin' && <Shield className="h-3.5 w-3.5 text-amber-500 shrink-0" />}
                      <select value={m.role}
                        onChange={(e) => handleRoleChange(m.user_id, e.target.value as 'org_admin' | 'org_member')}
                        className={`rounded-full px-2 py-0.5 text-xs font-medium border-0 cursor-pointer focus:outline-none ${ORG_ROLE_COLORS[m.role] ?? ''}`}>
                        <option value="org_admin">Org Admin</option>
                        <option value="org_member">Member</option>
                      </select>
                    </div>
                  </td>
                  <td className="px-4 py-3"><StatusDot active={m.is_active} /></td>
                  <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
                    {m.last_login_at ? new Date(m.last_login_at).toLocaleString() : 'Never'}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
                    {new Date(m.created_at).toLocaleDateString()}
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

type Tab = 'profile' | 'workspaces' | 'members'

export default function OrganizationPage() {
  const { data: session } = useSession()
  const { isOrgAdmin, isPlatformAdmin } = useRole()
  const [activeTab, setActiveTab] = useState<Tab>('profile')

  const apiKey = (session as unknown as Record<string, unknown>)?.apiKey as string ?? ''
  const headers = useMemo(() => ({
    Authorization: `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  }), [apiKey])

  if (!isOrgAdmin && !isPlatformAdmin) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800 mb-4">
          <Building2 className="h-7 w-7 text-slate-400 dark:text-slate-500" />
        </div>
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-1">
          Org Admin Access Required
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-xs">
          Contact your organization administrator to request access.
        </p>
      </div>
    )
  }

  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'profile', label: 'Profile', icon: Building2 },
    { id: 'workspaces', label: 'Workspaces', icon: FolderOpen },
    { id: 'members', label: 'Members', icon: Users },
  ]

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Organization</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Manage your organization profile, workspaces, and members.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === id
                ? 'border-teal-500 text-teal-700 dark:text-teal-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'profile' && <ProfileTab headers={headers} />}
      {activeTab === 'workspaces' && <WorkspacesTab headers={headers} />}
      {activeTab === 'members' && <MembersTab headers={headers} />}
    </div>
  )
}
