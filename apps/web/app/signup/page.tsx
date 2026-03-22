'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

function RunLedgerLogo({ size = 56 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="rl-grad-s" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0f766e" />
          <stop offset="100%" stopColor="#0891b2" />
        </linearGradient>
      </defs>
      <rect width="56" height="56" rx="14" fill="url(#rl-grad-s)" />
      <rect x="9" y="33" width="9" height="13" rx="2" fill="white" fillOpacity="0.65" />
      <rect x="23" y="22" width="9" height="24" rx="2" fill="white" />
      <rect x="37" y="13" width="9" height="33" rx="2" fill="white" fillOpacity="0.88" />
      <polyline points="13.5,33 27.5,22 41.5,13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <circle cx="13.5" cy="33" r="1.5" fill="white" />
      <circle cx="27.5" cy="22" r="1.5" fill="white" />
      <circle cx="41.5" cy="13" r="1.5" fill="white" />
    </svg>
  )
}

export default function SignupPage() {
  const router = useRouter()
  const [form, setForm] = useState({ email: '', password: '', full_name: '', org_name: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiKey, setApiKey] = useState<string | null>(null)

  function set(field: string) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail ?? 'Signup failed')
        return
      }
      setApiKey(data.api_key)
      toast.success('Account created!')
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (apiKey) {
    return (
      <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
        <div className="absolute inset-0 bg-gradient-to-br from-teal-50 via-white to-cyan-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950" />
        <div className="relative z-10 w-full max-w-md space-y-6">
          <div className="flex flex-col items-center gap-3 text-center">
            <RunLedgerLogo size={56} />
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Account Created</h1>
          </div>
          <Card className="border-slate-200/80 bg-white/85 shadow-xl backdrop-blur-md dark:border-slate-700/60 dark:bg-slate-900/85">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-slate-900 dark:text-white">Your API Key</CardTitle>
              <CardDescription className="text-slate-500 dark:text-slate-400">
                Copy this key — it will not be shown again.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-md bg-slate-100 p-3 font-mono text-sm break-all text-slate-800 dark:bg-slate-800 dark:text-slate-200 select-all">
                {apiKey}
              </div>
              <Button
                className="w-full bg-teal-600 hover:bg-teal-700 text-white"
                onClick={() => {
                  navigator.clipboard.writeText(apiKey)
                  toast.success('API key copied!')
                }}
              >
                Copy API Key
              </Button>
              <Button variant="outline" className="w-full" onClick={() => router.push('/login')}>
                Go to Login
              </Button>
            </CardContent>
          </Card>
          <p className="text-center text-xs text-slate-500 dark:text-slate-400">
            Set <code className="font-mono">RUNLEDGER_API_KEY={apiKey.slice(0, 20)}...</code> in your SDK config.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="absolute inset-0 bg-gradient-to-br from-teal-50 via-white to-cyan-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950" />
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-teal-300/20 blur-3xl dark:bg-teal-700/15" />
      <div className="pointer-events-none absolute -bottom-32 -right-20 h-96 w-96 rounded-full bg-cyan-300/20 blur-3xl dark:bg-cyan-700/15" />

      <div className="relative z-10 w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <RunLedgerLogo size={56} />
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">RunLedger</h1>
            <p className="mt-0.5 text-xs font-semibold uppercase tracking-[0.2em] text-teal-600 dark:text-teal-400">
              FinOps Control Plane
            </p>
          </div>
        </div>

        <Card className="border-slate-200/80 bg-white/85 shadow-xl backdrop-blur-md dark:border-slate-700/60 dark:bg-slate-900/85">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-slate-900 dark:text-white">Create your account</CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400">
              Free plan · 10,000 events/month · No credit card required
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="full_name" className="text-sm font-medium text-slate-700 dark:text-slate-300">Full name</Label>
                <Input id="full_name" type="text" required value={form.full_name} onChange={set('full_name')} placeholder="Alice Smith" autoComplete="name" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="org_name" className="text-sm font-medium text-slate-700 dark:text-slate-300">Organization</Label>
                <Input id="org_name" type="text" required value={form.org_name} onChange={set('org_name')} placeholder="Acme Corp" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-sm font-medium text-slate-700 dark:text-slate-300">Email</Label>
                <Input id="email" type="email" required value={form.email} onChange={set('email')} placeholder="alice@example.com" autoComplete="email" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-sm font-medium text-slate-700 dark:text-slate-300">Password</Label>
                <Input id="password" type="password" required minLength={8} value={form.password} onChange={set('password')} placeholder="8+ characters" autoComplete="new-password" />
              </div>

              {error && (
                <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">
                  {error}
                </p>
              )}

              <Button type="submit" disabled={loading} className="w-full bg-teal-600 hover:bg-teal-700 text-white">
                {loading ? 'Creating account…' : 'Create account'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-sm text-slate-500 dark:text-slate-400">
          Already have an account?{' '}
          <Link href="/login" className="font-medium text-teal-600 hover:text-teal-700 dark:text-teal-400">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
