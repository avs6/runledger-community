'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  LayoutGrid, Plus, Trash2, RefreshCw, Search, X, Star,
  Users, ChevronDown, ChevronUp, UserPlus, Check, Pencil,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'

const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Workspace {
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
  role: string
  is_active: boolean
}

interface WorkspaceMember {
  user_id: string
  email: string
  full_name: string | null
  role: string
}

type WsRole = 'workspace_admin' | 'workspace_editor' | 'workspace_contributor' | 'member' | 'viewer'

const inputCls =
  'rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 px-3 py-1.5 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500'

const WS_ROLE_COLORS: Record<string, string> = {
  workspace_admin: 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
  workspace_editor: 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
  workspace_contributor: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300',
  member: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  viewer: 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300',
}

function Avatar({ name, email }: { name: string | null; email: string }) {
  const ch = ((name ?? email)[0] ?? '?').toUpperCase()
  return (
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-500 text-white text-sm font-bold uppercase shadow-sm">
      {ch}
    </div>
  )
}

function SkeletonCards() {
  return (
    <>
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 space-y-3 animate-pulse">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-slate-200 dark:bg-slate-700 shrink-0" />
            <div className="flex-1 space-y-1.5">
              <div className="h-4 rounded bg-slate-200 dark:bg-slate-700 w-3/4" />
              <div className="h-3 rounded bg-slate-200 dark:bg-slate-700 w-1/2" />
            </div>
          </div>
        </div>
      ))}
    </>
  )
}

// ── Member-assignment panel shown after workspace creation ────────────────────

function AssignMembersPanel({
  workspace,
  headers,
  onDone,
}: {
  workspace: Workspace
  headers: Record<string, string>
  onDone: () => void
}) {
  const [orgMembers, setOrgMembers] = useState<OrgMember[]>([])
  const [wsMembers, setWsMembers] = useState<WorkspaceMember[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedRole, setSelectedRole] = useState<Record<string, WsRole>>({})
  const [adding, setAdding] = useState<Record<string, boolean>>({})

  useEffect(() => {
    Promise.all([
      fetch(`${apiBase}/org/members`, { headers }).then((r) => r.json()),
      fetch(`${apiBase}/org/workspaces/${workspace.id}/members`, { headers }).then((r) => r.json()),
    ])
      .then(([members, wsm]) => {
        setOrgMembers(Array.isArray(members) ? members : [])
        setWsMembers(Array.isArray(wsm) ? wsm : [])
      })
      .catch(() => toast.error('Failed to load members'))
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspace.id])

  const alreadyInWs = useMemo(() => new Set(wsMembers.map((m) => m.user_id)), [wsMembers])

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
      setWsMembers((prev) => [...prev, wm])
      toast.success(`${member.email} added to workspace`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to add member')
    } finally {
      setAdding((prev) => ({ ...prev, [member.user_id]: false }))
    }
  }

  const eligible = orgMembers.filter((m) => !alreadyInWs.has(m.user_id))

  return (
    <div className="rounded-xl border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-950/30 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-violet-800 dark:text-violet-200">
            Assign members to &ldquo;{workspace.name}&rdquo;
          </h2>
          <p className="text-xs text-violet-600 dark:text-violet-400 mt-0.5">
            Add org members to this workspace. You can skip this and manage members later from the Organization page.
          </p>
        </div>
        <button onClick={onDone}
          className="rounded-lg bg-violet-600 hover:bg-violet-700 px-4 py-1.5 text-sm font-medium text-white transition-colors">
          Done
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-violet-600 dark:text-violet-400 animate-pulse">Loading org members…</p>
      ) : eligible.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {orgMembers.length === 0
            ? 'No other org members to add. Add members from the Organization page first.'
            : 'All org members are already in this workspace.'}
        </p>
      ) : (
        <div className="space-y-2">
          {eligible.map((m) => (
            <div key={m.user_id} className="flex items-center gap-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-3 py-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 text-white text-xs font-bold uppercase">
                {((m.full_name ?? m.email)[0] ?? '?').toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                  {m.full_name ?? <span className="italic text-slate-400">No name</span>}
                </div>
                <div className="text-xs text-slate-400 truncate">{m.email}</div>
              </div>
              <select
                value={selectedRole[m.user_id] ?? 'member'}
                onChange={(e) => setSelectedRole((prev) => ({ ...prev, [m.user_id]: e.target.value as WsRole }))}
                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                <option value="workspace_admin">Admin</option>
                <option value="workspace_editor">Editor</option>
                <option value="workspace_contributor">Contributor</option>
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
              </select>
              <button
                onClick={() => handleAdd(m)}
                disabled={adding[m.user_id]}
                className="flex items-center gap-1 rounded-lg bg-violet-600 hover:bg-violet-700 disabled:opacity-50 px-2.5 py-1 text-xs font-medium text-white transition-colors"
              >
                <UserPlus className="h-3 w-3" />
                {adding[m.user_id] ? 'Adding…' : 'Add'}
              </button>
            </div>
          ))}
        </div>
      )}

      {wsMembers.length > 0 && (
        <div className="pt-2 border-t border-violet-200 dark:border-violet-800">
          <p className="text-xs font-medium text-violet-700 dark:text-violet-300 mb-1.5">
            {wsMembers.length} member{wsMembers.length !== 1 ? 's' : ''} in this workspace
          </p>
          <div className="flex flex-wrap gap-1.5">
            {wsMembers.map((m) => (
              <span key={m.user_id}
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${WS_ROLE_COLORS[m.role] ?? WS_ROLE_COLORS.member}`}>
                <Check className="h-2.5 w-2.5" />
                {m.full_name ?? m.email}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Per-workspace member list (expandable) ────────────────────────────────────

function WorkspaceMembers({
  workspace,
  headers,
  canManage,
}: {
  workspace: Workspace
  headers: Record<string, string>
  canManage: boolean
}) {
  const [open, setOpen] = useState(false)
  const [members, setMembers] = useState<WorkspaceMember[]>([])
  const [loaded, setLoaded] = useState(false)
  const [loading, setLoading] = useState(false)

  async function load() {
    if (loaded) { setOpen((v) => !v); return }
    setLoading(true)
    try {
      const res = await fetch(`${apiBase}/org/workspaces/${workspace.id}/members`, { headers })
      if (!res.ok) throw new Error()
      setMembers(await res.json())
      setLoaded(true)
      setOpen(true)
    } catch {
      toast.error('Failed to load workspace members')
    } finally {
      setLoading(false)
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
      toast.success(`${email} removed from workspace`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to remove member')
    }
  }

  return (
    <div>
      <button
        onClick={load}
        disabled={loading}
        className="flex items-center gap-1 text-xs text-slate-400 hover:text-violet-600 dark:hover:text-violet-400 transition-colors mt-2"
      >
        <Users className="h-3 w-3" />
        {loading ? 'Loading…' : loaded ? `${members.length} member${members.length !== 1 ? 's' : ''}` : 'View members'}
        {loaded && (open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
      </button>
      {open && loaded && (
        <div className="mt-2 space-y-1">
          {members.length === 0 ? (
            <p className="text-xs text-slate-400">No members yet.</p>
          ) : (
            members.map((m) => (
              <div key={m.user_id} className="flex items-center gap-2 rounded-lg bg-slate-50 dark:bg-slate-800/40 px-2.5 py-1.5">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-500 text-white text-[10px] font-bold uppercase">
                  {((m.full_name ?? m.email)[0] ?? '?').toUpperCase()}
                </div>
                <span className="flex-1 text-xs text-slate-700 dark:text-slate-300 truncate">
                  {m.full_name ?? m.email}
                </span>
                <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${WS_ROLE_COLORS[m.role] ?? WS_ROLE_COLORS.member}`}>
                  {m.role.replace('workspace_', '')}
                </span>
                {canManage && (
                  <button onClick={() => handleRemove(m.user_id, m.email)}
                    className="p-0.5 text-slate-300 hover:text-red-500 transition-colors">
                    <X className="h-3 w-3" />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function WorkspacePage() {
  const { data: session, update: updateSession } = useSession()
  const { isOrgElevated, isPlatformAdmin } = useRole()

  const apiKey = (session as unknown as Record<string, unknown>)?.apiKey as string ?? ''
  const currentWorkspaceName = (session as unknown as Record<string, unknown>)?.workspaceName as string ?? ''

  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [newWsName, setNewWsName] = useState('')
  const [creating, setCreating] = useState(false)
  const [search, setSearch] = useState('')
  const [newlyCreatedWs, setNewlyCreatedWs] = useState<Workspace | null>(null)
  const [managingMembersWs, setManagingMembersWs] = useState<Workspace | null>(null)
  const [editingWorkspaceId, setEditingWorkspaceId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [renamingWorkspaceId, setRenamingWorkspaceId] = useState<string | null>(null)

  const headers = useMemo(() => ({
    Authorization: `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  }), [apiKey])

  const load = useCallback(
    async (isRefresh = false) => {
      if (!apiKey || !(isOrgElevated || isPlatformAdmin)) {
        setLoading(false)
        setRefreshing(false)
        return
      }
      isRefresh ? setRefreshing(true) : setLoading(true)
      try {
        const res = await fetch(`${apiBase}/org/workspaces/my`, { headers })
        if (!res.ok) throw new Error(await res.text())
        setWorkspaces(await res.json())
      } catch {
        toast.error('Failed to load workspaces')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiKey, isOrgElevated, isPlatformAdmin]
  )

  useEffect(() => { load() }, [load])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!newWsName.trim()) return
    setCreating(true)
    try {
      const res = await fetch(`${apiBase}/org/workspaces`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ name: newWsName.trim() }),
      })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed to create workspace')
      }
      const ws: Workspace = await res.json()
      setWorkspaces((prev) => [...prev, ws])
      setNewWsName('')
      setShowForm(false)
      setNewlyCreatedWs(ws)
      toast.success(`Workspace "${ws.name}" created`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to create workspace')
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(ws: Workspace) {
    if (!confirm(`Delete workspace "${ws.name}"? All data in it will be lost.`)) return
    try {
      const res = await fetch(`${apiBase}/org/workspaces/${ws.id}`, {
        method: 'DELETE',
        headers,
      })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed to delete workspace')
      }
      setWorkspaces((prev) => prev.filter((w) => w.id !== ws.id))
      if (newlyCreatedWs?.id === ws.id) setNewlyCreatedWs(null)
      toast.success(`Workspace "${ws.name}" deleted`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete workspace')
    }
  }

  async function handleRename(ws: Workspace) {
    const nextName = renameValue.trim()
    if (!nextName || nextName === ws.name) {
      setEditingWorkspaceId(null)
      setRenameValue('')
      return
    }
    setRenamingWorkspaceId(ws.id)
    try {
      const res = await fetch(`${apiBase}/org/workspaces/${ws.id}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({ name: nextName }),
      })
      if (!res.ok) {
        const msg = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(msg.detail || 'Failed to rename workspace')
      }
      const updated: Workspace = await res.json()
      setWorkspaces((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      if (ws.name === currentWorkspaceName) {
        await updateSession({ workspaceName: updated.name })
      }
      setEditingWorkspaceId(null)
      setRenameValue('')
      toast.success(`Workspace renamed to "${updated.name}"`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to rename workspace')
    } finally {
      setRenamingWorkspaceId(null)
    }
  }

  const filteredWorkspaces = workspaces.filter((w) =>
    w.name.toLowerCase().includes(search.toLowerCase())
  )

  const canManage = isOrgElevated || isPlatformAdmin

  if (!canManage) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Workspaces</h1>
        <p className="mt-4 text-sm text-slate-500">Workspace management requires organization admin or manager access.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Workspaces</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Manage workspaces in your organization.
          </p>
          <div className="flex flex-wrap gap-2 mt-3">
            <Link href="/gateway" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Gateway</Link>
            <Link href="/guardrails" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Guardrails</Link>
            <Link href="/sessions" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Sessions</Link>
            <Link href="/analytics?tab=model-usage" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Model Usage</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Economics</Link>
            <Link href="/analytics?tab=savings" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Cost & Savings</Link>
            <Link href="/analytics?tab=users" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Analytics Users</Link>
            <Link href="/analytics?tab=engineering" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Engineering</Link>
            <Link href="/monitoring" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Monitoring</Link>
            <Link href="/runs?tab=flow-focus" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Request Flow</Link>
            <Link href="/analytics?tab=billing" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Billing Summary</Link>
            <Link href="/analytics?tab=roi" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Outcomes & ROI</Link>
            <Link href="/budgets" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Budgets</Link>
            <Link href="/billing" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Billing Periods</Link>
            <Link href="/chargeback" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Chargeback</Link>
            <Link href="/ledger" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Ledger</Link>
            <Link href="/approvals" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Approvals</Link>
            <Link href="/audit" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Audit Log</Link>
            <Link href="/governance-pack" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Governance Pack</Link>
            <Link href="/alert-rules" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Alert Rules</Link>
            <Link href="/data-capture" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Data Capture</Link>
            <Link href="/policy-dry-run" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Policy Dry Run</Link>
          </div>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 shrink-0"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {/* Search + New Workspace */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search workspaces…"
            className={`${inputCls} pl-8 w-full`}
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        {canManage && (
          <button
            onClick={() => {
              setShowForm((v) => !v)
              setNewWsName('')
              setNewlyCreatedWs(null)
            }}
            className="ml-auto flex items-center gap-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 px-3 py-1.5 text-sm font-medium text-white transition-colors shrink-0"
          >
            <Plus className="h-4 w-4" />
            New Workspace
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && canManage && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-3">
            Create a new workspace
          </h2>
          <form onSubmit={handleCreate} className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                Workspace name
              </label>
              <input
                className={`${inputCls} w-full`}
                value={newWsName}
                onChange={(e) => setNewWsName(e.target.value)}
                placeholder="e.g. Production, Staging, Research…"
                autoFocus
                required
              />
            </div>
            <button
              type="submit"
              disabled={creating || !newWsName.trim()}
              className="rounded-lg bg-violet-600 hover:bg-violet-700 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {creating ? 'Creating…' : 'Create'}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              Cancel
            </button>
          </form>
        </div>
      )}

      {/* Member assignment panel — shown after creation OR when Manage Members is clicked */}
      {(newlyCreatedWs ?? managingMembersWs) && canManage && (
        <AssignMembersPanel
          workspace={(newlyCreatedWs ?? managingMembersWs)!}
          headers={headers}
          onDone={() => { setNewlyCreatedWs(null); setManagingMembersWs(null) }}
        />
      )}

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          <SkeletonCards />
        </div>
      ) : filteredWorkspaces.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <LayoutGrid className="mb-3 h-10 w-10 text-slate-300 dark:text-slate-600" />
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
            {search ? `No workspaces match "${search}"` : 'No workspaces yet'}
          </p>
          {!search && canManage && (
            <button
              onClick={() => setShowForm(true)}
              className="mt-3 flex items-center gap-1.5 text-sm text-violet-600 dark:text-violet-400 hover:underline"
            >
              <Plus className="h-4 w-4" /> Create your first workspace
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredWorkspaces.map((ws) => {
            const isCurrent = ws.name === currentWorkspaceName
            const isLast = workspaces.length <= 1
            const deleteDisabled = isLast || isCurrent

            return (
              <div
                key={ws.id}
                className="group relative rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 transition-shadow hover:shadow-md dark:hover:shadow-slate-800/50"
              >
                <div className="flex items-start gap-3">
                  <Avatar name={null} email={ws.name} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      {editingWorkspaceId === ws.id ? (
                        <form
                          onSubmit={(e) => {
                            e.preventDefault()
                            void handleRename(ws)
                          }}
                          className="flex items-center gap-2"
                        >
                          <input
                            value={renameValue}
                            onChange={(e) => setRenameValue(e.target.value)}
                            className={`${inputCls} h-8`}
                            autoFocus
                          />
                          <button type="submit" disabled={renamingWorkspaceId === ws.id} className="text-xs text-violet-600 hover:underline disabled:opacity-50">
                            {renamingWorkspaceId === ws.id ? 'Saving…' : 'Save'}
                          </button>
                          <button type="button" onClick={() => { setEditingWorkspaceId(null); setRenameValue('') }} className="text-xs text-slate-400 hover:text-slate-700">
                            Cancel
                          </button>
                        </form>
                      ) : (
                        <span className="font-semibold text-slate-900 dark:text-white truncate">
                          {ws.name}
                        </span>
                      )}
                      {isCurrent && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 px-2 py-0.5 text-xs font-medium shrink-0">
                          <Star className="h-3 w-3 fill-current" />
                          Current
                        </span>
                      )}
                      {ws.status === 'suspended' && (
                        <span className="inline-flex items-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 px-2 py-0.5 text-xs font-medium shrink-0">
                          Suspended
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-slate-400">
                      Created {new Date(ws.created_at).toLocaleDateString()}
                    </p>
                    <WorkspaceMembers workspace={ws} headers={headers} canManage={canManage} />
                    <div className="mt-2 flex items-center gap-3">
                      <button
                        onClick={() => {
                          setManagingMembersWs(managingMembersWs?.id === ws.id ? null : ws)
                          setNewlyCreatedWs(null)
                        }}
                        className="flex items-center gap-1 text-xs text-violet-600 dark:text-violet-400 hover:underline"
                      >
                        <UserPlus className="h-3 w-3" />
                        {managingMembersWs?.id === ws.id ? 'Close' : 'Add Members'}
                      </button>
                      <button
                        onClick={() => {
                          setEditingWorkspaceId(ws.id)
                          setRenameValue(ws.name)
                        }}
                        className="flex items-center gap-1 text-xs text-slate-500 hover:text-violet-600 dark:text-slate-400 dark:hover:text-violet-400"
                      >
                        <Pencil className="h-3 w-3" />
                        Rename
                      </button>
                    </div>
                  </div>
                </div>

                {canManage && (
                  <button
                    onClick={() => handleDelete(ws)}
                    disabled={deleteDisabled}
                    title={
                      isCurrent
                        ? 'Cannot delete the current workspace'
                        : isLast
                        ? 'Cannot delete the last workspace'
                        : `Delete workspace "${ws.name}"`
                    }
                    className="absolute top-3 right-3 p-1.5 rounded-lg text-slate-300 dark:text-slate-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 disabled:opacity-30 disabled:cursor-not-allowed transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Result count when filtering */}
      {search && !loading && (
        <p className="text-xs text-slate-400">
          Showing {filteredWorkspaces.length} of {workspaces.length} workspace
          {workspaces.length !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}
