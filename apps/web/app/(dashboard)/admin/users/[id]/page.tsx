'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useParams, useRouter } from 'next/navigation'
import {
  ArrowLeft, Users, RefreshCw, Save, Trash2, Plus, Shield,
  ChevronDown, Building2, KeyRound,
} from 'lucide-react'

// ── Types ────────────────────────────────────────────────────────────────────

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

interface Tenant {
  id: string
  name: string
  is_default: boolean
}

// ── Constants ────────────────────────────────────────────────────────────────

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
  org_manager: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
  org_member: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  org_billing_admin: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  org_auditor: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
}

function inp(extra?: string) {
  return `mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 ${extra ?? ''}`
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function UserDetailPage() {
  const { data: session } = useSession()
  const router = useRouter()
  const params = useParams()
  const userId = params.id as string

  const s = session as Record<string, unknown> | null
  const apiKey = s?.apiKey as string
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const headers = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' }

  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Profile state
  const [profileForm, setProfileForm] = useState({ full_name: '', username: '', is_active: true })
  const [savingProfile, setSavingProfile] = useState(false)
  const [profileMsg, setProfileMsg] = useState('')
  const [profileError, setProfileError] = useState('')

  // Password reset
  const [showPwForm, setShowPwForm] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [savingPw, setSavingPw] = useState(false)
  const [pwMsg, setPwMsg] = useState('')

  // Org membership
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [showAddOrg, setShowAddOrg] = useState(false)
  const [addOrgId, setAddOrgId] = useState('')
  const [addOrgRole, setAddOrgRole] = useState('org_member')
  const [addingOrg, setAddingOrg] = useState(false)
  const [orgError, setOrgError] = useState('')
  const [roleMenuFor, setRoleMenuFor] = useState<string | null>(null)

  // ── Load user ───────────────────────────────────────────────────────────────
  const loadUser = useCallback(async () => {
    if (!apiKey || !userId) return
    setLoading(true)
    try {
      const r = await fetch(`${apiBase}/platform/users/${userId}`, { headers })
      if (!r.ok) { setError('User not found'); return }
      const data: User = await r.json()
      setUser(data)
      setProfileForm({ full_name: data.full_name || '', username: data.username || '', is_active: data.is_active })
    } catch {
      setError('Failed to load user')
    } finally {
      setLoading(false)
    }
  }, [apiKey, userId, apiBase])

  const loadTenants = async () => {
    if (tenants.length > 0) return
    const r = await fetch(`${apiBase}/platform/orgs`, { headers })
    if (r.ok) setTenants(await r.json())
  }

  useEffect(() => { loadUser() }, [loadUser])

  // ── Save profile ────────────────────────────────────────────────────────────
  const handleSaveProfile = async () => {
    setSavingProfile(true)
    setProfileMsg('')
    setProfileError('')
    const r = await fetch(`${apiBase}/platform/users/${userId}`, {
      method: 'PUT', headers,
      body: JSON.stringify({
        full_name: profileForm.full_name || undefined,
        username: profileForm.username || undefined,
        is_active: profileForm.is_active,
      }),
    })
    setSavingProfile(false)
    if (r.ok) {
      const updated = await r.json()
      setUser(prev => prev ? { ...prev, ...updated } : null)
      setProfileMsg('Saved')
      setTimeout(() => setProfileMsg(''), 2000)
    } else {
      const d = await r.json().catch(() => ({}))
      setProfileError(d.detail || 'Failed to save')
    }
  }

  // ── Reset password ──────────────────────────────────────────────────────────
  const handleResetPassword = async () => {
    if (!newPassword.trim()) return
    setSavingPw(true)
    const r = await fetch(`${apiBase}/platform/users/${userId}`, {
      method: 'PUT', headers,
      body: JSON.stringify({ password: newPassword }),
    })
    setSavingPw(false)
    if (r.ok) {
      setNewPassword('')
      setShowPwForm(false)
      setPwMsg('Password updated')
      setTimeout(() => setPwMsg(''), 3000)
    }
  }

  // ── Add org ─────────────────────────────────────────────────────────────────
  const handleAddOrg = async () => {
    if (!addOrgId) return
    setAddingOrg(true)
    setOrgError('')
    const r = await fetch(`${apiBase}/platform/users/${userId}/org-assignments`, {
      method: 'POST', headers,
      body: JSON.stringify({ tenant_id: addOrgId, role: addOrgRole }),
    })
    setAddingOrg(false)
    if (!r.ok) {
      const d = await r.json().catch(() => ({}))
      setOrgError(d.detail || 'Failed to add to organization')
      return
    }
    setShowAddOrg(false)
    setAddOrgId('')
    setAddOrgRole('org_member')
    await loadUser()
  }

  // ── Remove org ──────────────────────────────────────────────────────────────
  const handleRemoveOrg = async (o: OrgMembership) => {
    if (!confirm(`Remove from organization "${o.tenant_name}"?`)) return
    const r = await fetch(`${apiBase}/platform/users/${userId}/org-assignments/${o.tenant_id}`, {
      method: 'DELETE', headers,
    })
    if (r.ok) await loadUser()
  }

  // ── Change org role ─────────────────────────────────────────────────────────
  const handleChangeOrgRole = async (o: OrgMembership, newRole: string) => {
    setRoleMenuFor(null)
    const r = await fetch(`${apiBase}/platform/users/${userId}/org-assignments/${o.tenant_id}`, {
      method: 'PUT', headers,
      body: JSON.stringify({ tenant_id: o.tenant_id, role: newRole }),
    })
    if (r.ok) await loadUser()
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    )
  }

  if (error || !user) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <Users className="h-12 w-12 text-slate-300" />
        <p className="text-slate-500">{error || 'User not found'}</p>
        <button onClick={() => router.push('/admin/users')} className="text-violet-600 text-sm hover:underline">
          Back to Users
        </button>
      </div>
    )
  }

  const availableTenants = tenants.filter(t => !user.organizations.some(o => o.tenant_id === t.id))

  return (
    <div className="space-y-6">
      {/* Breadcrumb + header */}
      <div>
        <button
          onClick={() => router.push('/admin/users')}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 mb-3 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> System Users
        </button>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-lg font-bold shrink-0">
            {user.is_platform_admin
              ? <Shield className="h-5 w-5 text-violet-600 dark:text-violet-400" />
              : (user.full_name || user.email).charAt(0).toUpperCase()
            }
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{user.full_name || user.email}</h1>
              {user.is_platform_admin && (
                <span className="rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 px-2.5 py-0.5 text-[11px] font-semibold flex items-center gap-1">
                  <Shield className="h-3 w-3" /> Platform Admin
                </span>
              )}
              <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${user.is_active
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{user.email}</p>
          </div>
          <div className="ml-auto text-xs text-slate-400">
            Joined {new Date(user.created_at).toLocaleDateString()}
            {user.last_login_at && <> · Last login {new Date(user.last_login_at).toLocaleDateString()}</>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Profile ──────────────────────────────────────────────────────── */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Profile</h3>
          <div>
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Email</label>
            <input value={user.email} disabled className={`${inp()} opacity-60 cursor-not-allowed`} />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Full Name</label>
            <input value={profileForm.full_name} onChange={e => setProfileForm({ ...profileForm, full_name: e.target.value })} className={inp()} placeholder="Jane Smith" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Username</label>
            <input value={profileForm.username} onChange={e => setProfileForm({ ...profileForm, username: e.target.value })} className={inp()} placeholder="jsmith" />
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={profileForm.is_active}
                onChange={e => setProfileForm({ ...profileForm, is_active: e.target.checked })}
                className="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
              />
              <span className="text-sm text-slate-700 dark:text-slate-300">Account Active</span>
            </label>
          </div>
          {profileError && <p className="text-sm text-red-600 dark:text-red-400">{profileError}</p>}
          <div className="flex items-center gap-2">
            <button
              onClick={handleSaveProfile}
              disabled={savingProfile}
              className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors"
            >
              <Save className="h-4 w-4" />
              {savingProfile ? 'Saving...' : 'Save Changes'}
            </button>
            {profileMsg && <span className="text-sm text-emerald-600 dark:text-emerald-400">{profileMsg}</span>}
          </div>
        </div>

        {/* ── Security ─────────────────────────────────────────────────────── */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Security</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Reset this user&apos;s password. They will need to use the new password on their next login.</p>
          {pwMsg && <p className="text-sm text-emerald-600 dark:text-emerald-400">{pwMsg}</p>}
          {!showPwForm ? (
            <button
              onClick={() => setShowPwForm(true)}
              className="flex items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >
              <KeyRound className="h-4 w-4" /> Reset Password
            </button>
          ) : (
            <div className="space-y-2">
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400">New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                placeholder="Min. 8 characters"
                className={inp()}
                autoFocus
              />
              <div className="flex gap-2 pt-1">
                <button
                  onClick={handleResetPassword}
                  disabled={savingPw || newPassword.length < 8}
                  className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors"
                >
                  {savingPw ? 'Saving...' : 'Set Password'}
                </button>
                <button
                  onClick={() => { setShowPwForm(false); setNewPassword('') }}
                  className="rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="pt-2 border-t border-slate-100 dark:border-slate-700">
            <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">Danger Zone</p>
            <button
              onClick={() => {
                if (!confirm(`Delete user "${user.full_name || user.email}"? This cannot be undone.`)) return
                fetch(`${apiBase}/platform/users/${userId}`, { method: 'DELETE', headers })
                  .then(r => { if (r.ok) router.push('/admin/users') })
              }}
              className="flex items-center gap-2 rounded-lg border border-red-200 dark:border-red-900/50 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            >
              <Trash2 className="h-4 w-4" /> Delete User
            </button>
          </div>
        </div>
      </div>

      {/* ── Organization Memberships ──────────────────────────────────────────── */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-700">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Organization Memberships</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{user.organizations.length} organization{user.organizations.length !== 1 ? 's' : ''}</p>
          </div>
          <button
            onClick={() => { setShowAddOrg(true); loadTenants(); setOrgError('') }}
            className="flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
          >
            <Plus className="h-4 w-4" /> Add to Org
          </button>
        </div>

        {showAddOrg && (
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 bg-violet-50/40 dark:bg-violet-900/10">
            {orgError && <p className="mb-2 text-sm text-red-600 dark:text-red-400">{orgError}</p>}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Organization</label>
                <select value={addOrgId} onChange={e => setAddOrgId(e.target.value)} className={inp()}>
                  <option value="">Select organization…</option>
                  {availableTenants.map(t => (
                    <option key={t.id} value={t.id}>{t.name}{t.is_default ? ' (Default)' : ''}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Role</label>
                <select value={addOrgRole} onChange={e => setAddOrgRole(e.target.value)} className={inp()}>
                  {ORG_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
            </div>
            <div className="flex gap-2 mt-3">
              <button
                onClick={handleAddOrg}
                disabled={addingOrg || !addOrgId}
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors"
              >
                {addingOrg ? 'Adding…' : 'Add to Organization'}
              </button>
              <button
                onClick={() => { setShowAddOrg(false); setAddOrgId(''); setOrgError('') }}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {user.organizations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <Building2 className="h-8 w-8 text-slate-300 dark:text-slate-600" />
            <p className="text-sm text-slate-500">Not a member of any organization</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Organization</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Role</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
              {user.organizations.map(o => (
                <tr key={o.tenant_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-500 text-white font-bold text-xs shrink-0">
                        {o.tenant_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <button
                          onClick={() => router.push(`/admin/tenants/${o.tenant_id}`)}
                          className="font-medium text-slate-900 dark:text-white hover:text-violet-600 dark:hover:text-violet-400 transition-colors"
                        >
                          {o.tenant_name}
                        </button>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <div className="relative inline-block">
                      <button
                        onClick={() => setRoleMenuFor(roleMenuFor === o.tenant_id ? null : o.tenant_id)}
                        className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${ROLE_COLORS[o.role] || ROLE_COLORS.org_member} hover:opacity-80 transition-opacity`}
                      >
                        {ROLE_LABELS[o.role] || o.role}
                        <ChevronDown className="h-3 w-3" />
                      </button>
                      {roleMenuFor === o.tenant_id && (
                        <>
                          <div className="fixed inset-0 z-10" onClick={() => setRoleMenuFor(null)} />
                          <div className="absolute left-0 top-full mt-1 z-20 w-44 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 shadow-lg py-1">
                            {ORG_ROLES.map(r => (
                              <button
                                key={r.value}
                                onClick={() => handleChangeOrgRole(o, r.value)}
                                className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${o.role === r.value ? 'text-violet-600 font-semibold' : 'text-slate-700 dark:text-slate-300'}`}
                              >
                                {r.label}
                              </button>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => handleRemoveOrg(o)}
                      className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 transition-colors"
                      title="Remove from organization"
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
