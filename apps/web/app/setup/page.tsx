'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import RunLedgerLogo from '@/components/brand/RunLedgerLogo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

/**
 * First-run setup (review P-01). Production deployments seed no default account; the
 * operator proves they run this deployment with ADMIN_SECRET and creates the first
 * platform admin. Once one exists the API refuses (409) and this page says so.
 */
export default function SetupPage() {
  const router = useRouter()
  const [status, setStatus] = useState<'loading' | 'needed' | 'done' | 'error'>('loading')
  const [form, setForm] = useState({ admin_secret: '', email: '', full_name: '', org_name: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetch('/api/setup', { cache: 'no-store' })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error())))
      .then((data) => setStatus(data?.needs_bootstrap ? 'needed' : 'done'))
      .catch(() => setStatus('error'))
  }, [])

  function update(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) {
      setError('Passwords do not match')
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch('/api/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          admin_secret: form.admin_secret,
          email: form.email,
          full_name: form.full_name,
          org_name: form.org_name,
          password: form.password,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setError(typeof data.detail === 'string' ? data.detail : 'Setup failed')
        if (res.status === 409) setStatus('done')
        return
      }
      router.push(`/login?setup=done&email=${encodeURIComponent(form.email)}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4 dark:bg-slate-950">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <RunLedgerLogo />
        <h1 className="mt-4 text-xl font-semibold text-slate-900 dark:text-slate-50">Set up RunLedger</h1>

        {status === 'loading' && <p className="mt-4 text-sm text-slate-500">Checking this deployment…</p>}

        {status === 'error' && (
          <p role="alert" className="mt-4 text-sm text-red-700 dark:text-red-300">
            The RunLedger API is unreachable. Check that the API is running, then reload.
          </p>
        )}

        {status === 'done' && (
          <div className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
            <p>This deployment already has a platform admin. Sign in, then manage users from the Users page.</p>
            {error && <p role="alert" className="text-red-700 dark:text-red-300">{error}</p>}
            <Button asChild className="w-full">
              <Link href="/login">Go to sign in</Link>
            </Button>
          </div>
        )}

        {status === 'needed' && (
          <form onSubmit={handleSubmit} className="mt-4 space-y-3" aria-label="Create the first platform admin">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Create the first platform admin. Enter the <code>ADMIN_SECRET</code> this deployment was started with to
              prove you operate it. This works once.
            </p>
            <div className="space-y-1.5">
              <Label htmlFor="admin_secret">Admin secret</Label>
              <Input id="admin_secret" type="password" autoComplete="off" required value={form.admin_secret} onChange={update('admin_secret')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email">Admin email</Label>
              <Input id="email" type="email" autoComplete="username" required value={form.email} onChange={update('email')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="full_name">Full name</Label>
              <Input id="full_name" value={form.full_name} onChange={update('full_name')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="org_name">Organization name</Label>
              <Input id="org_name" placeholder="Default Organization" value={form.org_name} onChange={update('org_name')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" autoComplete="new-password" required minLength={12} value={form.password} onChange={update('password')} aria-describedby="password-help" />
              <p id="password-help" className="text-xs text-slate-500">At least 12 characters with a letter and a digit.</p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirm">Confirm password</Label>
              <Input id="confirm" type="password" autoComplete="new-password" required value={form.confirm} onChange={update('confirm')} />
            </div>
            {error && (
              <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-300">
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create platform admin'}
            </Button>
          </form>
        )}
      </div>
    </main>
  )
}
