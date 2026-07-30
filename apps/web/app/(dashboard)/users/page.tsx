'use client'

import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  CheckCircle2,
  Circle,
  KeyRound,
  Pencil,
  RefreshCw,
  Search,
  Shield,
  Trash2,
  UserPlus,
  X,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import { createOrgUser, listOrgUsers, updateOrgUser, type OrgUser } from '@/lib/api'

const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const inputCls =
  'rounded-lg border border-slate-300 bg-white/90 px-3 py-1.5 text-sm text-slate-800 placeholder:text-slate-400 shadow-sm shadow-slate-200/40 focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:border-slate-300 dark:bg-white/90 dark:text-slate-900 dark:shadow-slate-300/30'
const TABLE_HEAD =
  'px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-600 dark:text-slate-600'

function Avatar({ name, email }: { name: string | null; email: string }) {
  const initial = ((name ?? email)[0] ?? '?').toUpperCase()
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-slate-600 text-xs font-bold text-white">
      {initial}
    </div>
  )
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${
      active
        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-100 dark:text-emerald-700'
        : 'bg-slate-100 text-slate-500 dark:bg-slate-100 dark:text-slate-500'
    }`}>
      <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-emerald-500' : 'bg-slate-400'}`} />
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}

export default function UsersPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''
  const { isOrgAdmin } = useRole()
  const canManage = isOrgAdmin

  const [users, setUsers] = useState<OrgUser[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const [showCreate, setShowCreate] = useState(false)
  const [cEmail, setCEmail] = useState('')
  const [cName, setCName] = useState('')
  const [cPassword, setCPassword] = useState('ChangeMe123!')
  const [cSkipVerify, setCSkipVerify] = useState(true)
  const [creating, setCreating] = useState(false)

  const [editing, setEditing] = useState<OrgUser | null>(null)
  const [eName, setEName] = useState('')
  const [ePassword, setEPassword] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey || !canManage) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      setUsers(await listOrgUsers(apiKey))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }, [apiKey, canManage])

  useEffect(() => { load() }, [load])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return users
    return users.filter(
      (u) => u.email.toLowerCase().includes(q) || (u.full_name ?? '').toLowerCase().includes(q)
    )
  }, [users, search])

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    if (!cEmail.trim()) return
    setCreating(true)
    try {
      const u = await createOrgUser(apiKey, {
        email: cEmail.trim(),
        full_name: cName.trim() || null,
        temporary_password: cPassword,
        skip_verification: cSkipVerify,
      })
      setUsers((prev) => [...prev, u])
      setShowCreate(false)
      setCEmail('')
      setCName('')
      setCPassword('ChangeMe123!')
      setCSkipVerify(true)
      toast.success(`User ${u.email} created${u.email_verified ? ' (verified)' : ''}. Add them to a workspace so they can sign in.`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create user')
    } finally {
      setCreating(false)
    }
  }

  function openEdit(u: OrgUser) {
    setEditing(u)
    setEName(u.full_name ?? '')
    setEPassword('')
  }

  async function handleSaveEdit(e: FormEvent) {
    e.preventDefault()
    if (!editing) return
    setSaving(true)
    try {
      const body: { full_name?: string; password?: string } = {}
      if (eName !== (editing.full_name ?? '')) body.full_name = eName
      if (ePassword.trim()) body.password = ePassword.trim()
      const u = await updateOrgUser(apiKey, editing.id, body)
      setUsers((prev) => prev.map((x) => (x.id === u.id ? u : x)))
      setEditing(null)
      toast.success('User updated')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update user')
    } finally {
      setSaving(false)
    }
  }

  async function toggleField(u: OrgUser, field: 'is_active' | 'email_verified') {
    try {
      const updated = await updateOrgUser(apiKey, u.id, { [field]: !u[field] })
      setUsers((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))
    } catch {
      toast.error('Update failed')
    }
  }

  async function handleRemove(u: OrgUser) {
    if (!confirm(`Remove ${u.email} from this organization?`)) return
    try {
      const res = await fetch(`${apiBase}/org/members/${u.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${apiKey}` },
      })
      if (!res.ok && res.status !== 204) throw new Error('remove failed')
      setUsers((prev) => prev.filter((x) => x.id !== u.id))
      toast.success('Removed from organization')
    } catch {
      toast.error('Failed to remove user')
    }
  }

  if (!canManage) {
    return (
      <div className="p-8">
        <h1 className="font-display text-2xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-slate-950">Users</h1>
        <p className="mt-4 text-sm text-slate-500">User management is an organization-admin function.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-slate-950">Users</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-600">
            Your organization&apos;s people. Create a user here, then add them to workspaces to grant access.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white shadow-sm shadow-blue-500/20 hover:bg-blue-700"
          >
            <UserPlus className="h-4 w-4" /> New User
          </button>
          <button onClick={load} className="rounded-lg border border-slate-300 bg-white/70 p-2 text-slate-500 hover:bg-white dark:border-slate-300 dark:bg-white/70 dark:hover:bg-white">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={`Search ${users.length} users...`} className={`${inputCls} w-full pl-8`} />
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-300 bg-white/75 shadow-sm shadow-slate-300/30 dark:border-slate-300 dark:bg-white/75">
        <table className="w-full text-sm">
          <thead className="bg-slate-100/80 dark:bg-slate-100/80">
            <tr>
              <th className={TABLE_HEAD}>User</th>
              <th className={TABLE_HEAD}>Org role</th>
              <th className={TABLE_HEAD}>Verified</th>
              <th className={TABLE_HEAD}>Status</th>
              <th className={TABLE_HEAD}>Last login</th>
              <th className={TABLE_HEAD} />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-200">
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-400">Loading...</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-400">No users. Create one to get started.</td></tr>
            ) : filtered.map((u) => (
              <tr key={u.id} className="hover:bg-blue-50/60 dark:hover:bg-blue-50/60">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <Avatar name={u.full_name} email={u.email} />
                    <div>
                      <div className="font-medium text-slate-900 dark:text-slate-900">{u.full_name ?? '-'}</div>
                      <div className="text-xs text-slate-500">{u.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-100 dark:text-slate-600">
                    {u.org_role === 'org_admin' && <Shield className="h-3 w-3" />}
                    {(u.org_role ?? 'org_member').replace('org_', '')}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => toggleField(u, 'email_verified')} title="Toggle verification" className={`inline-flex items-center gap-1 text-xs ${u.email_verified ? 'text-emerald-600' : 'text-slate-400 hover:text-slate-600'}`}>
                    {u.email_verified ? <CheckCircle2 className="h-4 w-4" /> : <Circle className="h-4 w-4" />}
                    {u.email_verified ? 'Verified' : 'Unverified'}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => toggleField(u, 'is_active')} title="Toggle active"><StatusBadge active={u.is_active} /></button>
                </td>
                <td className="px-4 py-3 text-xs text-slate-500">
                  {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'never'}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-3">
                    <button onClick={() => openEdit(u)} title="Edit name / reset password" className="text-slate-400 hover:text-blue-600"><Pencil className="h-4 w-4" /></button>
                    <button onClick={() => handleRemove(u)} title="Remove from org" className="text-slate-400 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <Modal title="New user" onClose={() => setShowCreate(false)}>
          <form onSubmit={handleCreate} className="space-y-3">
            <input autoFocus type="email" required placeholder="Email" value={cEmail} onChange={(e) => setCEmail(e.target.value)} className={`${inputCls} w-full`} />
            <input type="text" placeholder="Full name (optional)" value={cName} onChange={(e) => setCName(e.target.value)} className={`${inputCls} w-full`} />
            <div>
              <label className="text-xs text-slate-500">Temporary password</label>
              <input type="text" value={cPassword} onChange={(e) => setCPassword(e.target.value)} className={`${inputCls} w-full`} />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-700">
              <input type="checkbox" checked={cSkipVerify} onChange={(e) => setCSkipVerify(e.target.checked)} className="h-4 w-4 rounded border-slate-300" />
              Skip email verification
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setShowCreate(false)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-300">Cancel</button>
              <button type="submit" disabled={creating} className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white disabled:opacity-50">{creating ? 'Creating...' : 'Create user'}</button>
            </div>
          </form>
        </Modal>
      )}

      {editing && (
        <Modal title={`Edit ${editing.email}`} onClose={() => setEditing(null)}>
          <form onSubmit={handleSaveEdit} className="space-y-3">
            <div>
              <label className="text-xs text-slate-500">Full name</label>
              <input type="text" value={eName} onChange={(e) => setEName(e.target.value)} className={`${inputCls} w-full`} />
            </div>
            <div>
              <label className="flex items-center gap-1 text-xs text-slate-500"><KeyRound className="h-3 w-3" /> New password (leave blank to keep)</label>
              <input type="text" placeholder="********" value={ePassword} onChange={(e) => setEPassword(e.target.value)} className={`${inputCls} w-full`} />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setEditing(null)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-300">Cancel</button>
              <button type="submit" disabled={saving} className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white disabled:opacity-50">{saving ? 'Saving...' : 'Save'}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border border-slate-300 bg-white p-5 shadow-xl shadow-slate-500/20 dark:border-slate-300 dark:bg-white" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-950">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="h-5 w-5" /></button>
        </div>
        {children}
      </div>
    </div>
  )
}
