'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import {
  Users, Plus, Trash2, Search, RefreshCw, X, ChevronRight,
  Shield, ChevronLeft,
} from 'lucide-react'

interface OrgMembership {
  tenant_id: string
  tenant_name: string
  role: string
}

interface User {
  id: string
  email: string
  username: string | null
  full_name: string
  is_active: boolean
  is_platform_admin: boolean
  last_login_at: string | null
  created_at: string
  organizations: OrgMembership[]
}

interface CreateForm {
  email: string
  full_name: string
  username: string
  password: string
}

interface Tenant {
  id: string
  name: string
  is_default: boolean
}

const ORG_ROLES = [
  { value: 'org_member', label: 'Member' },
  { value: 'org_manager', label: 'Manager' },
  { value: 'org_admin', label: 'Org Admin' },
  { value: 'org_billing_admin', label: 'Billing Admin' },
  { value: 'org_auditor', label: 'Auditor' },
]

function inp(extra?: string) {
  return `mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 ${extra ?? ''}`
}

export default function AdminUsersPage() {
  const { data: session } = useSession()
  const router = useRouter()
  const s = session as Record<string, unknown> | null
  const apiKey = s?.apiKey as string
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [users, setUsers] = useState<User[]>([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 50
  const [loading, setLoading] = useState(true)
  const [hasMore, setHasMore] = useState(false)
  const [error, setError] = useState('')

  // Create form
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<CreateForm>({ email: '', full_name: '', username: '', password: '' })
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [orgAssign, setOrgAssign] = useState<{ tenant_id: string; role: string }>({ tenant_id: '', role: 'org_member' })
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  const headers = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' }

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const params = new URLSearchParams({ skip: String(page * pageSize), limit: String(pageSize + 1) })
      if (search) params.set('search', search)
      const r = await fetch(`${apiBase}/platform/users?${params}`, { headers })
      if (r.ok) {
        const data: User[] = await r.json()
        setHasMore(data.length > pageSize)
        setUsers(data.slice(0, pageSize))
      }
    } finally {
      setLoading(false)
    }
  }, [apiKey, search, page, apiBase])

  useEffect(() => { load() }, [load])
  useEffect(() => { setPage(0) }, [search])

  const loadTenants = async () => {
    if (tenants.length > 0) return
    const r = await fetch(`${apiBase}/platform/orgs`, { headers })
    if (r.ok) setTenants(await r.json())
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setCreateError('')
    try {
      const body: Record<string, unknown> = {
        email: form.email,
        full_name: form.full_name || undefined,
        username: form.username || undefined,
        password: form.password,
        org_assignments: orgAssign.tenant_id
          ? [{ tenant_id: orgAssign.tenant_id, role: orgAssign.role }]
          : [],
      }
      const r = await fetch(`${apiBase}/platform/users`, {
        method: 'POST', headers,
        body: JSON.stringify(body),
      })
      if (!r.ok) {
        const d = await r.json()
        setCreateError(d.detail || 'Failed to create user')
        return
      }
      setShowForm(false)
      setForm({ email: '', full_name: '', username: '', password: '' })
      setOrgAssign({ tenant_id: '', role: 'org_member' })
      await load()
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (u: User, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm(`Delete user "${u.full_name || u.email}"? This cannot be undone.`)) return
    setError('')
    const r = await fetch(`${apiBase}/platform/users/${u.id}`, { method: 'DELETE', headers })
    if (!r.ok) {
      const d = await r.json().catch(() => ({}))
      setError(d.detail || 'Failed to delete user')
      return
    }
    await load()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">System Users</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">All users across all organizations</p>
        </div>
        <button
          onClick={() => { setShowForm(true); loadTenants() }}
          className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
        >
          <Plus className="h-4 w-4" /> New User
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError('')}><X className="h-4 w-4" /></button>
        </div>
      )}

      {/* Create form */}
      {showForm && (
        <div className="rounded-xl border border-violet-200 bg-violet-50/50 p-5 dark:border-violet-800 dark:bg-violet-900/10">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Create New User</h3>
          {createError && <p className="mb-3 text-sm text-red-600 dark:text-red-400">{createError}</p>}
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Email *</label>
              <input required type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className={inp()} placeholder="user@example.com" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Full Name</label>
              <input value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} className={inp()} placeholder="Jane Smith" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Username</label>
              <input value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} className={inp()} placeholder="jsmith" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Password *</label>
              <input required type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} className={inp()} placeholder="••••••••" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Add to Organization</label>
              <select value={orgAssign.tenant_id} onChange={e => setOrgAssign({ ...orgAssign, tenant_id: e.target.value })} className={inp()}>
                <option value="">None</option>
                {tenants.map(t => <option key={t.id} value={t.id}>{t.name}{t.is_default ? ' (Default)' : ''}</option>)}
              </select>
            </div>
            {orgAssign.tenant_id && (
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Org Role</label>
                <select value={orgAssign.role} onChange={e => setOrgAssign({ ...orgAssign, role: e.target.value })} className={inp()}>
                  {ORG_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
            )}
            <div className="sm:col-span-2 flex gap-2 pt-1">
              <button type="submit" disabled={creating}
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors">
                {creating ? 'Creating...' : 'Create User'}
              </button>
              <button type="button" onClick={() => { setShowForm(false); setCreateError('') }}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800 transition-colors">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search by name, email, or username..."
          className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800/50 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Users className="h-10 w-10 text-slate-300 dark:text-slate-600" />
            <p className="text-sm text-slate-500">{search ? 'No users match your search' : 'No users yet'}</p>
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">User</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Email</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Organizations</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Last Login</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                {users.map(u => (
                  <tr
                    key={u.id}
                    onClick={() => router.push(`/admin/users/${u.id}`)}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-sm font-bold shrink-0">
                          {u.is_platform_admin
                            ? <Shield className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                            : (u.full_name || u.email).charAt(0).toUpperCase()
                          }
                        </div>
                        <div>
                          <p className="font-medium text-slate-900 dark:text-white">{u.full_name || '—'}</p>
                          {u.username && <p className="text-xs text-slate-400">@{u.username}</p>}
                          {u.is_platform_admin && (
                            <span className="text-[10px] text-violet-600 dark:text-violet-400 font-semibold">Platform Admin</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{u.email}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {u.organizations.length === 0 ? (
                          <span className="text-xs text-slate-400">—</span>
                        ) : u.organizations.slice(0, 3).map(o => (
                          <span key={o.tenant_id} className="rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-0.5 text-[11px]">
                            {o.tenant_name}
                          </span>
                        ))}
                        {u.organizations.length > 3 && (
                          <span className="text-xs text-slate-400">+{u.organizations.length - 3}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${u.is_active
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                        : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs">
                      {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : 'Never'}
                    </td>
                    <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => router.push(`/admin/users/${u.id}`)}
                          className="rounded-lg px-2.5 py-1.5 text-xs text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-900/20 font-medium transition-colors flex items-center gap-1"
                        >
                          Manage <ChevronRight className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={(e) => handleDelete(u, e)}
                          className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 transition-colors"
                          title="Delete user"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 dark:border-slate-700">
              <p className="text-xs text-slate-500">
                Page {page + 1} · {users.length} user{users.length !== 1 ? 's' : ''}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
                >
                  <ChevronLeft className="h-3.5 w-3.5" /> Prev
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={!hasMore}
                  className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
                >
                  Next <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
