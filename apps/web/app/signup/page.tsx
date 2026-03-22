'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { signIn } from 'next-auth/react'
import { signInWithPopup } from 'firebase/auth'
import { auth, googleProvider, isFirebaseConfigured } from '@/lib/firebase'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { MailCheck } from 'lucide-react'

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
  const [socialLoading, setSocialLoading] = useState(false)
  const [apiKey, setApiKey] = useState<string | null>(null)

  function set(field: string) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, [field]: e.target.value }))
  }

  async function handleGoogleSignIn() {
    setSocialLoading(true)
    setError('')
    try {
      const result = await signInWithPopup(auth, googleProvider)
      const idToken = await result.user.getIdToken()
      const res = await signIn('firebase', { idToken, redirect: false })
      if (res?.error) {
        setError('Google sign-in failed. Please try again.')
      } else {
        router.push('/dashboard')
      }
    } catch {
      setError('Google sign-in failed. Please try again.')
    } finally {
      setSocialLoading(false)
    }
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
      <div className="flex min-h-screen items-center justify-center bg-slate-950 px-6">
        <div className="w-full max-w-md space-y-6 text-center">
          <MailCheck className="mx-auto h-14 w-14 text-teal-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Check your email</h1>
            <p className="mt-2 text-slate-400 text-sm leading-relaxed">
              We sent your credentials and a verification link to <span className="text-slate-200 font-medium">{form.email}</span>.
              Click the link in that email to activate your account.
            </p>
          </div>

          <div className="rounded-xl border border-slate-700 bg-slate-900 p-5 text-left space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Your API Key (also in the email)</p>
            <div className="rounded-lg bg-slate-950 border border-slate-800 p-3 font-mono text-sm break-all text-teal-300 select-all">
              {apiKey}
            </div>
            <Button
              type="button"
              className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
              onClick={() => {
                navigator.clipboard.writeText(apiKey)
                toast.success('API key copied!')
              }}
            >
              Copy API Key
            </Button>
          </div>

          <Button
            type="button"
            className="w-full bg-gradient-to-r from-teal-600 to-cyan-600 text-white hover:from-teal-500 hover:to-cyan-500"
            onClick={() => router.push('/login')}
          >
            Go to Sign In
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-slate-950">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 bg-gradient-to-br from-slate-900 to-slate-950 border-r border-slate-800">
        <div className="flex items-center gap-3">
          <RunLedgerLogo size={36} />
          <div>
            <div className="text-sm font-semibold text-white leading-none">RunLedger</div>
            <div className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-teal-400 leading-none">
              Control Plane
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full bg-teal-900/40 border border-teal-700/40 px-3 py-1">
              <div className="h-1.5 w-1.5 rounded-full bg-teal-400" />
              <span className="text-xs font-medium text-teal-300">Free plan · 10,000 events/month</span>
            </div>
            <p className="text-2xl font-semibold text-white leading-snug">
              Start tracking AI costs<br />in minutes.
            </p>
            <p className="text-slate-400 text-sm leading-relaxed max-w-sm">
              One SDK call and every token, cost, and latency is captured automatically. No credit card required.
            </p>
          </div>

          <div className="flex flex-col gap-2.5">
            {[
              'Free forever for OSS projects',
              'OpenAI, Anthropic, Gemini, Mistral, Cohere',
              'LangChain & LangGraph native support',
              'Upgrade to paid plan anytime',
            ].map(f => (
              <div key={f} className="flex items-center gap-2 text-sm text-slate-300">
                <div className="h-1.5 w-1.5 rounded-full bg-teal-400 shrink-0" />
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
            <div className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.2em] text-teal-400">
              FinOps Control Plane
            </div>
          </div>
        </div>

        <div className="w-full max-w-sm space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Create your account</h1>
            <p className="mt-1 text-sm text-slate-400">Free plan · No credit card required</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="full_name" className="text-sm font-medium text-slate-300">Full name</Label>
              <Input
                id="full_name"
                type="text"
                required
                value={form.full_name}
                onChange={set('full_name')}
                placeholder="Alice Smith"
                autoComplete="name"
                autoFocus
                className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:border-teal-500 focus:ring-teal-500/20"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="org_name" className="text-sm font-medium text-slate-300">Organization</Label>
              <Input
                id="org_name"
                type="text"
                required
                value={form.org_name}
                onChange={set('org_name')}
                placeholder="Acme Corp"
                className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:border-teal-500 focus:ring-teal-500/20"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm font-medium text-slate-300">Email</Label>
              <Input
                id="email"
                type="email"
                required
                value={form.email}
                onChange={set('email')}
                placeholder="alice@example.com"
                autoComplete="email"
                className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:border-teal-500 focus:ring-teal-500/20"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm font-medium text-slate-300">Password</Label>
              <Input
                id="password"
                type="password"
                required
                minLength={8}
                value={form.password}
                onChange={set('password')}
                placeholder="8+ characters"
                autoComplete="new-password"
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
              disabled={loading}
              className="w-full bg-gradient-to-r from-teal-600 to-cyan-600 text-white hover:from-teal-500 hover:to-cyan-500"
            >
              {loading ? 'Creating account…' : 'Create account'}
            </Button>
          </form>

          {isFirebaseConfigured && (
            <>
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-800" />
                </div>
                <div className="relative flex justify-center text-xs text-slate-600 uppercase tracking-wider">
                  <span className="bg-slate-950 px-3">or</span>
                </div>
              </div>

              <Button
                type="button"
                variant="outline"
                className="w-full border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800 hover:text-white hover:border-slate-600 flex items-center gap-2.5"
                onClick={handleGoogleSignIn}
                disabled={socialLoading}
              >
                {socialLoading ? (
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-400/40 border-t-slate-200" />
                ) : (
                  <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                )}
                Continue with Google
              </Button>
            </>
          )}

          <p className="text-center text-sm text-slate-500">
            Already have an account?{' '}
            <Link href="/login" className="font-medium text-teal-400 hover:text-teal-300">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
