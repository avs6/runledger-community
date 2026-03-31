'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import {
  Building2, Plus, Trash2, Search, RefreshCw, X, ChevronRight,
  Users, LayoutGrid,
} from 'lucide-react'

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

interface CreateForm {
  name: string
  plan: string
  admin_email: string
  admin_password: string
  admin_full_name: string
}

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  suspended: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  archived: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
}

const PLAN_COLORS: Record<string, string> = {
  free: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  starter: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  growth: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
  enterprise: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
}
const PLANS = ['free', 'starter', 'growth', 'enterprise']

function inp(extra?: string) {
  return `mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 ${extra ?? ''}`
}

export default function AdminTenantsPage() {
  const { data: session } = useSession()
  const router = useRouter()
  const s = session as Record<string, unknown> | null
  const apiKey = s?.apiKey as string
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [tenants, setTenants] = useState<Tenant[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<CreateForm>({
    name: '', plan: 'free', admin_email: '', admin_password: '', admin_full_name: '',
  })
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')

  const headers = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' }

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const url = `${apiBase}/platform/orgs${search ? `?search=${encodeURIComponent(search)}` : ''}`
      const r = await fetch(url, { headers })
      if (r.ok) setTenants(await r.json())
    } finally {
      setLoading(false)
    }
  }, [apiKey, search, apiBase])

  useEffect(() => { load() }, [load])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      const r = await fetch(`${apiBase}/platform/orgs`, {
        method: 'POST', headers,
        body: JSON.stringify(form),
      })
      if (!r.ok) {
        const d = await r.json()
        setError(d.detail || 'Failed to create organization')
        return
      }
      setShowForm(false)
      setForm({ name: '', plan: 'free', admin_email: '', admin_password: '', admin_full_name: '' })
      await load()
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (t: Tenant) => {
    if (t.is_default) { setActionError('The default organization cannot be deleted.'); return }
    if (!confirm(`Delete organization "${t.name}" and ALL its data? This cannot be undone.`)) return
    setActionError('')
    const r = await fetch(`${apiBase}/platform/orgs/${t.id}`, { method: 'DELETE', headers })
    if (!r.ok) {
      const d = await r.json().catch(() => ({}))
      setActionError(d.detail || 'Failed to delete organization.')
      return
    }
    await load()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Organizations</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {tenants.length} organization{tenants.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Organization
        </button>
      </div>

      {actionError && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400 flex items-center justify-between">
          <span>{actionError}</span>
          <button onClick={() => setActionError('')}><X className="h-4 w-4" /></button>
        </div>
      )}

      {/* Create form */}
      {showForm && (
        <div className="rounded-xl border border-violet-200 bg-violet-50/50 p-5 dark:border-violet-800 dark:bg-violet-900/10">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Create New Organization</h3>
          {error && <p className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">{error}</p>}
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Organization Name *</label>
              <input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className={inp()} placeholder="Acme Corp" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Plan</label>
              <select value={form.plan} onChange={e => setForm({ ...form, plan: e.target.value })} className={inp()}>
                {PLANS.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Admin Email *</label>
              <input required type="email" value={form.admin_email} onChange={e => setForm({ ...form, admin_email: e.target.value })} className={inp()} placeholder="admin@acme.com" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Admin Password *</label>
              <input required type="password" value={form.admin_password} onChange={e => setForm({ ...form, admin_password: e.target.value })} className={inp()} placeholder="••••••••" />
            </div>
            <div className="sm:col-span-2">
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Admin Full Name</label>
              <input value={form.admin_full_name} onChange={e => setForm({ ...form, admin_full_name: e.target.value })} className={inp()} placeholder="Jane Smith" />
            </div>
            <div className="sm:col-span-2 flex gap-2 pt-1">
              <button type="submit" disabled={creating}
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors">
                {creating ? 'Creating...' : 'Create Organization'}
              </button>
              <button type="button" onClick={() => { setShowForm(false); setError('') }}
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
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search organizations..."
          className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800/50 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        ) : tenants.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Building2 className="h-10 w-10 text-slate-300 dark:text-slate-600" />
            <p className="text-sm text-slate-500">{search ? 'No organizations match your search' : 'No organizations yet'}</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Organization</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Plan</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Workspaces</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Members</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
              {tenants.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => router.push(`/admin/tenants/${t.id}`)}
                  className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-500 text-white font-bold text-xs shrink-0">
                        {t.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900 dark:text-white">{t.name}</p>
                        {t.is_default && <span className="text-[10px] text-violet-600 dark:text-violet-400 font-medium">Default Org</span>}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${PLAN_COLORS[t.plan] || PLAN_COLORS.free}`}>
                      {t.plan.charAt(0).toUpperCase() + t.plan.slice(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_COLORS[t.status] || STATUS_COLORS.active}`}>
                      {t.status ? t.status.charAt(0).toUpperCase() + t.status.slice(1) : 'Active'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1 text-slate-600 dark:text-slate-300">
                      <LayoutGrid className="h-3.5 w-3.5" />
                      <span>{t.workspace_count}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1 text-slate-600 dark:text-slate-300">
                      <Users className="h-3.5 w-3.5" />
                      <span>{t.member_count}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs whitespace-nowrap">
                    {new Date(t.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => router.push(`/admin/tenants/${t.id}`)}
                        className="rounded-lg px-2.5 py-1.5 text-xs text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-900/20 font-medium transition-colors flex items-center gap-1"
                      >
                        Manage <ChevronRight className="h-3.5 w-3.5" />
                      </button>
                      {!t.is_default && (
                        <button
                          onClick={() => handleDelete(t)}
                          className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 transition-colors"
                          title="Delete organization"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
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
