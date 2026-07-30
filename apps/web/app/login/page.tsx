'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { signIn } from 'next-auth/react'
import { BarChart3, CheckCircle2, Gauge, LockKeyhole, Route } from 'lucide-react'
import RunLedgerLogo, { RunLedgerMark } from '@/components/brand/RunLedgerLogo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

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
    <main className="min-h-screen overflow-hidden bg-[#f3f6fa] text-slate-950">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(147,197,253,0.26),transparent_28rem),radial-gradient(circle_at_85%_25%,rgba(203,213,225,0.36),transparent_24rem),linear-gradient(135deg,#f8fafc,#edf3f9_58%,#f3f6fa)]" />
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-300/45 to-transparent" />

      <div className="relative grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
        <section className="hidden flex-col justify-between border-r border-slate-200/80 bg-[#eef3f8]/65 p-10 lg:flex xl:p-14">
          <RunLedgerLogo
            markSize={40}
            wordmarkClassName="text-base text-slate-950"
            taglineClassName="text-blue-700"
          />

          <div className="max-w-xl">
            <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
              <LockKeyhole className="h-3.5 w-3.5" />
              Self-hosted AI operations control
            </div>
            <h1 className="max-w-lg font-display text-4xl font-semibold tracking-[-0.055em] text-slate-950 xl:text-5xl">
              The ledger for every AI request, route, and dollar.
            </h1>
            <p className="mt-5 max-w-md text-base leading-7 text-slate-600">
              RunLedger gives platform teams one place to observe agent traffic, enforce budgets, explain routing decisions, and prove savings.
            </p>

            <div className="mt-10 grid max-w-2xl gap-3 sm:grid-cols-3">
              {[
                { label: 'Requests traced', value: '18.2M', icon: Route },
                { label: 'Savings modeled', value: '$28K', icon: BarChart3 },
                { label: 'Budget guardrails', value: '<5ms', icon: Gauge },
              ].map(({ label, value, icon: Icon }) => (
                <div key={label} className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm backdrop-blur">
                  <Icon className="h-4 w-4 text-blue-600" />
                  <div className="mt-4 font-display text-2xl font-semibold tracking-[-0.045em] text-slate-950 tabular-nums">{value}</div>
                  <div className="mt-1 text-xs text-slate-500">{label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid max-w-2xl grid-cols-2 gap-3 text-sm text-slate-600">
            {[
              'Provider-neutral metering',
              'Workspace and org controls',
              'Inline gateway enforcement',
              'Out-of-band observability',
            ].map((item) => (
              <div key={item} className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-blue-600" />
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className="flex items-center justify-center px-6 py-12">
          <div className="w-full max-w-md">
            <div className="mb-10 flex justify-center lg:hidden">
              <RunLedgerLogo
                markSize={42}
                wordmarkClassName="text-lg text-slate-950"
                taglineClassName="text-blue-700"
              />
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white/90 p-7 shadow-xl shadow-slate-200/70 backdrop-blur-xl">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-700">Secure Access</p>
                  <h2 className="mt-2 font-display text-2xl font-semibold tracking-[-0.045em] text-slate-950">Sign in</h2>
                  <p className="mt-1 text-sm text-slate-500">Enter your workspace credentials.</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-blue-50 p-2">
                  <RunLedgerMark size={34} />
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="email" className="text-sm font-medium text-slate-700">
                    Email
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    autoFocus
                    className="h-11 border-slate-300 bg-[#f8fafc] text-slate-950 placeholder:text-slate-400 focus:border-blue-500 focus:ring-blue-500/20"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="password" className="text-sm font-medium text-slate-700">
                    Password
                  </Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="h-11 border-slate-300 bg-[#f8fafc] text-slate-950 placeholder:text-slate-400 focus:border-blue-500 focus:ring-blue-500/20"
                  />
                </div>

                {error && (
                  <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    {error}
                  </p>
                )}

                <Button
                  type="submit"
                  className="h-11 w-full bg-blue-600 font-semibold text-white shadow-lg shadow-blue-900/15 hover:bg-blue-500"
                  disabled={loading}
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Signing in...
                    </span>
                  ) : (
                    'Continue to RunLedger'
                  )}
                </Button>
              </form>
            </div>

            <p className="mt-5 text-center text-xs text-slate-500">
              AI usage, cost, routing, and governance in one control plane.
            </p>
          </div>
        </section>
      </div>
    </main>
  )
}
