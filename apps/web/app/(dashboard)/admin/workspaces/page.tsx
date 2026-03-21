'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import {
  LayoutGrid, Plus, Trash2, Search, RefreshCw, X, ChevronRight,
  ChevronLeft, Building2, Users,
} from 'lucide-react'

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

interface Org {
  id: string
  name: string
  is_default: boolean
}

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  suspended: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  archived: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
}

function inp(extra?: string) {
  return `mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500 ${extra ?? ''}`
}

export default function AdminWorkspacesPage() {
  const { data: session } = useSession()
  const router = useRouter()
  const s = session as Record<string, unknown> | null
  const apiKey = s?.apiKey as string
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [search, setSearch] = useState('')
  const [orgFilter, setOrgFilter] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 50
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Create form
  const [showForm, setShowForm] = useState(false)
  const [orgs, setOrgs] = useState<Org[]>([])
  const [form, setForm] = useState({ name: '', org_id: '' })
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  const headers = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' }

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const params = new URLSearchParams({ skip: String(page * pageSize), limit: String(pageSize + 1) })
      if (search) params.set('search', search)
      if (orgFilter) params.set('org_id', orgFilter)
      const r = await fetch(`${apiBase}/platform/workspaces?${params}`, { headers })
      if (r.ok) {
        const data: Workspace[] = await r.json()
        setHasMore(data.length > pageSize)
        setWorkspaces(data.slice(0, pageSize))
      }
    } finally {
      setLoading(false)
    }
  }, [apiKey, search, orgFilter, page, apiBase])

  useEffect(() => { load() }, [load])
  useEffect(() => { setPage(0) }, [search, orgFilter])

  const loadOrgs = async () => {
    if (orgs.length > 0) return
    const r = await fetch(`${apiBase}/platform/orgs?limit=200`, { headers })
    if (r.ok) setOrgs(await r.json())
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.org_id) { setCreateError('Please select an organization'); return }
    setCreating(true)
    setCreateError('')
    try {
      const r = await fetch(`${apiBase}/platform/orgs/${form.org_id}/workspaces`, {
        method: 'POST', headers,
        body: JSON.stringify({ name: form.name }),
      })
      if (!r.ok) {
        const d = await r.json()
        setCreateError(d.detail || 'Failed to create workspace')
        return
      }
      setShowForm(false)
      setForm({ name: '', org_id: '' })
      await load()
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (ws: Workspace, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm(`Delete workspace "${ws.name}"? This cannot be undone.`)) return
    setError('')
    const r = await fetch(`${apiBase}/platform/workspaces/${ws.id}`, { method: 'DELETE', headers })
    if (!r.ok) {
      const d = await r.json().catch(() => ({}))
      setError(d.detail || 'Failed to delete workspace')
      return
    }
    await load()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Workspaces</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">All workspaces across all organizations</p>
        </div>
        <button
          onClick={() => { setShowForm(true); loadOrgs() }}
          className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 transition-colors"
        >
          <Plus className="h-4 w-4" /> New Workspace
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
        <div className="rounded-xl border border-teal-200 bg-teal-50/50 p-5 dark:border-teal-800 dark:bg-teal-900/10">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Create New Workspace</h3>
          {createError && <p className="mb-3 text-sm text-red-600 dark:text-red-400">{createError}</p>}
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Workspace Name *</label>
              <input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className={inp()} placeholder="e.g. Production" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Organization *</label>
              <select required value={form.org_id} onChange={e => setForm({ ...form, org_id: e.target.value })} className={inp()}>
                <option value="">Select organization…</option>
                {orgs.map(o => <option key={o.id} value={o.id}>{o.name}{o.is_default ? ' (Default)' : ''}</option>)}
              </select>
            </div>
            <div className="sm:col-span-2 flex gap-2 pt-1">
              <button type="submit" disabled={creating}
                className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 transition-colors">
                {creating ? 'Creating...' : 'Create Workspace'}
              </button>
              <button type="button" onClick={() => { setShowForm(false); setCreateError('') }}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800 transition-colors">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search workspaces or organizations..."
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>
        <select
          value={orgFilter}
          onChange={e => setOrgFilter(e.target.value)}
          onFocus={loadOrgs}
          className="rounded-lg border border-slate-200 bg-white py-2 px-3 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500 min-w-[180px]"
        >
          <option value="">All organizations</option>
          {orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800/50 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        ) : workspaces.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <LayoutGrid className="h-10 w-10 text-slate-300 dark:text-slate-600" />
            <p className="text-sm text-slate-500">{search || orgFilter ? 'No workspaces match your filters' : 'No workspaces yet'}</p>
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Workspace</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Organization</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Members</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Created</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                {workspaces.map(ws => (
                  <tr
                    key={ws.id}
                    onClick={() => router.push(`/admin/workspaces/${ws.id}`)}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400 shrink-0">
                          <LayoutGrid className="h-4 w-4" />
                        </div>
                        <span className="font-medium text-slate-900 dark:text-white">{ws.name}</span>
                        {ws.is_restricted && (
                          <span className="rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300 px-1.5 py-0.5 text-[10px] font-semibold">Restricted</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={e => { e.stopPropagation(); router.push(`/admin/tenants/${ws.tenant_id}`) }}
                        className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300 hover:text-teal-600 dark:hover:text-teal-400 transition-colors"
                      >
                        <Building2 className="h-3.5 w-3.5 shrink-0" />
                        <span className="text-sm">{ws.tenant_name}</span>
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_COLORS[ws.status] || STATUS_COLORS.active}`}>
                        {ws.status ? ws.status.charAt(0).toUpperCase() + ws.status.slice(1) : 'Active'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1 text-slate-600 dark:text-slate-300">
                        <Users className="h-3.5 w-3.5" />
                        <span>{ws.member_count}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs whitespace-nowrap">
                      {new Date(ws.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => router.push(`/admin/workspaces/${ws.id}`)}
                          className="rounded-lg px-2.5 py-1.5 text-xs text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 font-medium transition-colors flex items-center gap-1"
                        >
                          Manage <ChevronRight className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={e => handleDelete(ws, e)}
                          className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 transition-colors"
                          title="Delete workspace"
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
                Page {page + 1} · {workspaces.length} workspace{workspaces.length !== 1 ? 's' : ''}
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
