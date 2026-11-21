'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { KeyRound, LogOut, MailOpen, MonitorSmartphone } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  acceptInvitation,
  apiErrorMessage,
  changeMyPassword,
  declineInvitation,
  getMyInvitations,
  getMySessions,
  revokeMySession,
  type PendingInvitation,
  type SessionKey,
} from '@/lib/api'

function fmt(ts: string | null): string {
  return ts ? new Date(ts).toLocaleString() : '—'
}

export default function AccountPage() {
  const { data: session, update } = useSession()
  const apiKey = session?.apiKey ?? ''
  const forced = useSearchParams().get('changePassword') === '1' || Boolean(session?.mustChangePassword)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [sessions, setSessions] = useState<SessionKey[]>([])
  const [invitations, setInvitations] = useState<PendingInvitation[]>([])
  const [loadError, setLoadError] = useState('')

  const load = useCallback(async () => {
    if (!apiKey) return
    try {
      const [s, i] = await Promise.all([getMySessions(apiKey), getMyInvitations(apiKey)])
      setSessions(s)
      setInvitations(i)
      setLoadError('')
    } catch (err) {
      setLoadError(apiErrorMessage(err, 'Could not load account data'))
    }
  }, [apiKey])

  useEffect(() => { load() }, [load])

  async function submitPassword(e: React.FormEvent) {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match')
      return
    }
    setSaving(true)
    try {
      await changeMyPassword(apiKey, currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      await update({ refresh: true })
      toast.success('Password changed. Your other sessions were signed out.')
      load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Could not change password'))
    } finally {
      setSaving(false)
    }
  }

  async function revoke(s: SessionKey) {
    if (!window.confirm(`Sign out the session in ${s.workspace_name ?? 'this workspace'}?`)) return
    try {
      await revokeMySession(apiKey, s.id)
      toast.success('Session signed out')
      load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Could not revoke session'))
    }
  }

  async function respond(inv: PendingInvitation, accept: boolean) {
    try {
      if (accept) await acceptInvitation(apiKey, inv.tenant_id)
      else await declineInvitation(apiKey, inv.tenant_id)
      toast.success(accept ? `Joined ${inv.tenant_name}` : 'Invitation declined')
      if (accept) await update({ refresh: true })
      load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Could not update invitation'))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">Account</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">{session?.user?.email}</p>
      </div>

      {loadError && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{loadError}</p>}

      <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700/60 dark:bg-slate-900/60">
        <h2 className="flex items-center gap-2 text-base font-semibold"><KeyRound className="h-4 w-4" /> Password</h2>
        {forced && (
          <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-300">
            You signed in with a temporary password. Choose your own password to continue.
          </p>
        )}
        <form onSubmit={submitPassword} className="mt-4 grid max-w-md gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="current">Current password</Label>
            <Input id="current" type="password" autoComplete="current-password" required value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new">New password</Label>
            <Input id="new" type="password" autoComplete="new-password" required value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            <p className="text-xs text-slate-500">At least 12 characters, with a letter and a digit.</p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm">Confirm new password</Label>
            <Input id="confirm" type="password" autoComplete="new-password" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
          </div>
          <Button type="submit" disabled={saving} className="w-fit">{saving ? 'Saving…' : 'Change password'}</Button>
        </form>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700/60 dark:bg-slate-900/60">
        <h2 className="flex items-center gap-2 text-base font-semibold"><MailOpen className="h-4 w-4" /> Organization invitations</h2>
        {invitations.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No pending invitations.</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100 dark:divide-slate-800">
            {invitations.map((inv) => (
              <li key={inv.tenant_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="text-sm font-medium">{inv.tenant_name}</p>
                  <p className="text-xs text-slate-500">Role {inv.role.replace('org_', '')}{inv.invited_by_email ? ` · invited by ${inv.invited_by_email}` : ''} · {fmt(inv.created_at)}</p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => respond(inv, true)}>Accept</Button>
                  <Button size="sm" variant="outline" onClick={() => respond(inv, false)}>Decline</Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700/60 dark:bg-slate-900/60">
        <h2 className="flex items-center gap-2 text-base font-semibold"><MonitorSmartphone className="h-4 w-4" /> Active sessions</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Workspace</th>
                <th className="py-2 pr-4">Started</th>
                <th className="py-2 pr-4">Last used</th>
                <th className="py-2 pr-4">Expires</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {sessions.length === 0 ? (
                <tr><td colSpan={5} className="py-3 text-slate-500">No active sessions.</td></tr>
              ) : sessions.map((s) => (
                <tr key={s.id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-2 pr-4">{s.workspace_name ?? s.workspace_id}{s.current && <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700">this session</span>}</td>
                  <td className="py-2 pr-4">{fmt(s.created_at)}</td>
                  <td className="py-2 pr-4">{fmt(s.last_used_at)}</td>
                  <td className="py-2 pr-4">{fmt(s.expires_at)}</td>
                  <td className="py-2 text-right">
                    {!s.current && (
                      <Button size="sm" variant="outline" onClick={() => revoke(s)} aria-label={`Sign out session in ${s.workspace_name ?? 'workspace'}`}>
                        <LogOut className="mr-1 h-3.5 w-3.5" /> Sign out
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
