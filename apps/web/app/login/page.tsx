'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { signIn } from 'next-auth/react'
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
      <rect width="56" height="56" rx="14" fill="url(#rl-grad)" />
      <rect x="9" y="33" width="9" height="13" rx="2" fill="white" fillOpacity="0.65" />
      <rect x="23" y="22" width="9" height="24" rx="2" fill="white" />
      <rect x="37" y="13" width="9" height="33" rx="2" fill="white" fillOpacity="0.88" />
      <polyline points="13.5,33 27.5,22 41.5,13" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
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
    <div className="flex min-h-screen bg-slate-950">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between border-r border-slate-800/80 bg-[radial-gradient(circle_at_20%_15%,rgba(20,184,166,0.10),transparent_28rem),linear-gradient(135deg,#0f172a,#020617)] p-12">
        <div className="flex items-center gap-3">
          <RunLedgerLogo size={36} />
          <div>
            <div className="text-sm font-semibold text-white leading-none">RunLedger</div>
            <div className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-teal-300 leading-none">
              Control Plane
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <blockquote className="space-y-3">
            <p className="text-2xl font-semibold text-white leading-snug">
              Billing-grade observability<br />for AI agents.
            </p>
            <p className="text-slate-400 text-sm leading-relaxed max-w-sm">
              Track every token, enforce budgets, and understand the economics of every agent run — in real time.
            </p>
          </blockquote>

          <div className="flex flex-col gap-2.5">
            {[
              'Usage accounting across all providers',
              'Budget guardrails with <5ms enforcement',
              'Chargeback & cost attribution by team',
              'Prompt versioning & evaluation scores',
            ].map(f => (
              <div key={f} className="flex items-center gap-2 text-sm text-slate-300">
                <div className="h-1.5 w-1.5 rounded-full bg-teal-300 shrink-0" />
                {f}
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs text-slate-600">© {new Date().getFullYear()} RunLedger</p>
      </div>

      {/* Right panel — form */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        {/* Mobile logo */}
        <div className="mb-8 flex flex-col items-center gap-3 lg:hidden">
          <RunLedgerLogo size={48} />
          <div className="text-center">
            <div className="text-xl font-bold text-white">RunLedger</div>
            <div className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.2em] text-teal-300">
              FinOps Control Plane
            </div>
          </div>
        </div>

        <div className="w-full max-w-sm space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Sign in</h1>
            <p className="mt-1 text-sm text-slate-400">Enter your credentials to access your workspace</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm font-medium text-slate-300">
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
                className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:border-teal-500 focus:ring-teal-500/20"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm font-medium text-slate-300">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:border-teal-500 focus:ring-teal-500/20"
              />
            </div>

            {error && (
              <p className="rounded-md bg-red-950/60 border border-red-800/50 px-3 py-2 text-sm text-red-400">
                {error}
              </p>
            )}

            <Button
              type="submit"
              className="w-full bg-teal-600 text-white shadow-md shadow-teal-950/20 hover:bg-teal-500"
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

          <p className="text-center text-xs text-slate-600">
            Billing-grade observability for AI agents
          </p>
        </div>
      </div>
    </div>
  )
}
