'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { signIn } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

function RunLedgerLogo({ size = 56 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="rl-grad" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0f766e" />
          <stop offset="100%" stopColor="#0891b2" />
        </linearGradient>
      </defs>
      {/* Background rounded square */}
      <rect width="56" height="56" rx="14" fill="url(#rl-grad)" />
      {/* Bar 1 — short */}
      <rect x="9" y="33" width="9" height="13" rx="2" fill="white" fillOpacity="0.65" />
      {/* Bar 2 — medium */}
      <rect x="23" y="22" width="9" height="24" rx="2" fill="white" />
      {/* Bar 3 — tall */}
      <rect x="37" y="13" width="9" height="33" rx="2" fill="white" fillOpacity="0.88" />
      {/* Trend line connecting bar tops */}
      <polyline
        points="13.5,33 27.5,22 41.5,13"
        stroke="white"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Small dot on each top */}
      <circle cx="13.5" cy="33" r="1.5" fill="white" />
      <circle cx="27.5" cy="22" r="1.5" fill="white" />
      <circle cx="41.5" cy="13" r="1.5" fill="white" />
    </svg>
  )
}

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    const result = await signIn('credentials', {
      email,
      password,
      redirect: false,
    })

    setLoading(false)

    if (result?.error) {
      setError('Invalid email or password.')
    } else {
      router.push('/dashboard')
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-teal-50 via-white to-cyan-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950" />

      {/* Decorative blobs */}
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-teal-300/20 blur-3xl dark:bg-teal-700/15" />
      <div className="pointer-events-none absolute -bottom-32 -right-20 h-96 w-96 rounded-full bg-cyan-300/20 blur-3xl dark:bg-cyan-700/15" />
      <div className="pointer-events-none absolute left-1/2 top-1/4 h-64 w-64 -translate-x-1/2 rounded-full bg-teal-200/10 blur-2xl dark:bg-teal-600/10" />

      {/* Subtle grid pattern */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.015] dark:opacity-[0.03]"
        style={{
          backgroundImage: 'linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative z-10 w-full max-w-sm space-y-6">
        {/* Logo + brand name above the card */}
        <div className="flex flex-col items-center gap-3 text-center">
          <RunLedgerLogo size={56} />
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              RunLedger
            </h1>
            <p className="mt-0.5 text-xs font-semibold uppercase tracking-[0.2em] text-teal-600 dark:text-teal-400">
              FinOps Control Plane
            </p>
          </div>
        </div>

        {/* Login card */}
        <Card className="border-slate-200/80 bg-white/85 shadow-xl backdrop-blur-md dark:border-slate-700/60 dark:bg-slate-900/85">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-slate-900 dark:text-white">Sign in</CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400">
              Enter your credentials to access your workspace
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoFocus
                  className="bg-white/60 dark:bg-slate-800/60"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  className="bg-white/60 dark:bg-slate-800/60"
                />
              </div>
              {error && (
                <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">
                  {error}
                </p>
              )}
              <Button
                type="submit"
                className="w-full bg-gradient-to-r from-teal-600 to-cyan-600 text-white shadow-md hover:from-teal-700 hover:to-cyan-700 dark:from-teal-500 dark:to-cyan-500 dark:hover:from-teal-600 dark:hover:to-cyan-600"
                disabled={loading}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                    Signing in…
                  </span>
                ) : (
                  'Sign in'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-sm text-slate-500 dark:text-slate-400">
          Don&apos;t have an account?{' '}
          <Link href="/signup" className="font-medium text-teal-600 hover:text-teal-700 dark:text-teal-400">
            Sign up free
          </Link>
        </p>

        {/* Footer */}
        <p className="text-center text-xs text-slate-400 dark:text-slate-600">
          Billing-grade observability for AI agents
        </p>
      </div>
    </div>
  )
}
