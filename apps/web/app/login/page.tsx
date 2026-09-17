'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { signIn } from 'next-auth/react'
import { useTheme } from 'next-themes'
import { BarChart3, CheckCircle2, Gauge, LockKeyhole, Moon, Route, Shield, Sun } from 'lucide-react'
import RunLedgerLogo, { RunLedgerMark } from '@/components/brand/RunLedgerLogo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8201'

interface AuthProvider {
  id: string
  name: string
  type: string
}

export default function LoginPage() {
  const router = useRouter()
  const { resolvedTheme, setTheme } = useTheme()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [ssoProviders, setSsoProviders] = useState<AuthProvider[]>([])
  const [ssoLoading, setSsoLoading] = useState<string | null>(null)
  const [ldapProvider, setLdapProvider] = useState<AuthProvider | null>(null)
  const [ldapUsername, setLdapUsername] = useState('')
  const [ldapPassword, setLdapPassword] = useState('')

  useEffect(() => {
    fetch(`${API_URL}/auth/providers`)
      .then((res) => (res.ok ? res.json() : { providers: [] }))
      .then((data) => setSsoProviders(data.providers ?? []))
      .catch(() => {})
  }, [])

  async function handleSsoLogin(provider: AuthProvider) {
    if (provider.type === 'ldap') {
      setLdapProvider(provider)
      return
    }

    setSsoLoading(provider.id)
    setError('')
    try {
      const isOauth2 = provider.type === 'oauth2'
      const callbackPath = isOauth2 ? '/auth/oauth2/callback' : '/auth/oidc/callback'
      const redirectUri = `${window.location.origin}${callbackPath}`
      const apiPath = isOauth2
        ? `${API_URL}/auth/oauth2/${provider.id}/authorize?redirect_uri=${encodeURIComponent(redirectUri)}`
        : `${API_URL}/auth/oidc/${provider.id}/authorize?redirect_uri=${encodeURIComponent(redirectUri)}`
      const res = await fetch(apiPath)
      if (!res.ok) {
        setError('Failed to start SSO login.')
        setSsoLoading(null)
        return
      }
      const data = await res.json()
      sessionStorage.setItem(isOauth2 ? 'oauth2_provider_id' : 'oidc_provider_id', provider.id)
      window.location.href = data.authorization_url
    } catch {
      setError('Failed to start SSO login.')
      setSsoLoading(null)
    }
  }

  async function handleLdapSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!ldapProvider) return
    setSsoLoading(ldapProvider.id)
    setError('')

    const result = await signIn('ldap-login', {
      username: ldapUsername,
      password: ldapPassword,
      provider_id: ldapProvider.id,
      redirect: false,
    })

    setSsoLoading(null)

    if (result?.error) {
      setError('LDAP authentication failed.')
    } else {
      router.push('/dashboard')
    }
  }

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
    <main className="min-h-screen overflow-hidden bg-[#f3f6fa] text-slate-950 dark:bg-[#0a0e1a] dark:text-slate-50">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(147,197,253,0.26),transparent_28rem),radial-gradient(circle_at_85%_25%,rgba(203,213,225,0.36),transparent_24rem),linear-gradient(135deg,#f8fafc,#edf3f9_58%,#f3f6fa)] dark:bg-[radial-gradient(circle_at_18%_18%,rgba(59,130,246,0.12),transparent_28rem),radial-gradient(circle_at_85%_25%,rgba(51,65,85,0.2),transparent_24rem),linear-gradient(135deg,#0a0e1a,#0f172a_58%,#0a0e1a)]" />
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-300/45 to-transparent dark:via-blue-500/25" />

      <button
        onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
        className="absolute right-5 top-5 z-10 rounded-xl border border-slate-200/80 bg-white/80 p-2.5 text-slate-500 shadow-sm backdrop-blur transition-colors hover:bg-blue-50 hover:text-slate-700 dark:border-slate-700/60 dark:bg-slate-800/80 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
        aria-label="Toggle theme"
      >
        {resolvedTheme === 'dark' ? <Sun className="h-4.5 w-4.5" /> : <Moon className="h-4.5 w-4.5" />}
      </button>

      <div className="relative grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
        <section className="hidden flex-col justify-between border-r border-slate-200/80 bg-[#eef3f8]/65 p-10 lg:flex xl:p-14 dark:border-slate-700/50 dark:bg-[#0d1225]/80">
          <RunLedgerLogo
            markSize={40}
            wordmarkClassName="text-base text-slate-950 dark:text-slate-50"
            taglineClassName="text-blue-700 dark:text-blue-400"
          />

          <div className="max-w-xl">
            <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800 dark:border-blue-800/60 dark:bg-blue-950/50 dark:text-blue-300">
              <LockKeyhole className="h-3.5 w-3.5" />
              Self-hosted AI operations control
            </div>
            <h1 className="max-w-lg font-display text-4xl font-semibold tracking-[-0.055em] text-slate-950 xl:text-5xl dark:text-slate-50">
              The ledger for every AI request, route, and dollar.
            </h1>
            <p className="mt-5 max-w-md text-base leading-7 text-slate-600 dark:text-slate-400">
              RunLedger gives platform teams one place to observe agent traffic, enforce budgets, explain routing decisions, and prove savings.
            </p>

            <div className="mt-10 grid max-w-2xl gap-3 sm:grid-cols-3">
              {[
                { label: 'Requests traced', value: '18.2M', icon: Route },
                { label: 'Savings modeled', value: '$28K', icon: BarChart3 },
                { label: 'Budget guardrails', value: '<5ms', icon: Gauge },
              ].map(({ label, value, icon: Icon }) => (
                <div key={label} className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm backdrop-blur dark:border-slate-700/60 dark:bg-slate-800/60 dark:shadow-black/20">
                  <Icon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  <div className="mt-4 font-display text-2xl font-semibold tracking-[-0.045em] text-slate-950 tabular-nums dark:text-slate-50">{value}</div>
                  <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid max-w-2xl grid-cols-2 gap-3 text-sm text-slate-600 dark:text-slate-400">
            {[
              'Provider-neutral metering',
              'Workspace and org controls',
              'Inline gateway enforcement',
              'Out-of-band observability',
            ].map((item) => (
              <div key={item} className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
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
                wordmarkClassName="text-lg text-slate-950 dark:text-slate-50"
                taglineClassName="text-blue-700 dark:text-blue-400"
              />
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white/90 p-7 shadow-xl shadow-slate-200/70 backdrop-blur-xl dark:border-slate-700/60 dark:bg-slate-800/80 dark:shadow-black/30">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-700 dark:text-blue-400">Secure Access</p>
                  <h2 className="mt-2 font-display text-2xl font-semibold tracking-[-0.045em] text-slate-950 dark:text-slate-50">Sign in</h2>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Enter your workspace credentials.</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-blue-50 p-2 dark:border-slate-700/60 dark:bg-blue-950/40">
                  <RunLedgerMark size={34} />
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="email" className="text-sm font-medium text-slate-700 dark:text-slate-300">
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
                    className="h-11 border-slate-300 bg-[#f8fafc] text-slate-950 placeholder:text-slate-400 focus:border-blue-500 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-900/60 dark:text-slate-50 dark:placeholder:text-slate-500 dark:focus:border-blue-500 dark:focus:ring-blue-500/30"
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
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="h-11 border-slate-300 bg-[#f8fafc] text-slate-950 placeholder:text-slate-400 focus:border-blue-500 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-900/60 dark:text-slate-50 dark:placeholder:text-slate-500 dark:focus:border-blue-500 dark:focus:ring-blue-500/30"
                  />
                </div>

                {error && (
                  <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-300">
                    {error}
                  </p>
                )}

                <Button
                  type="submit"
                  className="h-11 w-full bg-blue-600 font-semibold text-white shadow-lg shadow-blue-900/15 hover:bg-blue-500 dark:shadow-blue-950/40"
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

              {ssoProviders.length > 0 && (
                <>
                  <div className="my-5 flex items-center gap-3">
                    <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
                    <span className="text-xs font-medium text-slate-400 dark:text-slate-500">or</span>
                    <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
                  </div>
                  <div className="space-y-2.5">
                    {ssoProviders.map((provider) => (
                      <Button
                        key={provider.id}
                        type="button"
                        variant="outline"
                        className="h-11 w-full gap-2 border-slate-300 font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                        onClick={() => handleSsoLogin(provider)}
                        disabled={ssoLoading === provider.id}
                      >
                        {ssoLoading === provider.id ? (
                          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-400/30 border-t-slate-600" />
                        ) : (
                          <Shield className="h-4 w-4" />
                        )}
                        Continue with {provider.name}
                      </Button>
                    ))}
                  </div>
                </>
              )}

              {ldapProvider && (
                <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-5 dark:border-slate-700/60 dark:bg-slate-900/60">
                  <div className="mb-3 flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                      Sign in with {ldapProvider.name}
                    </p>
                    <button
                      type="button"
                      onClick={() => { setLdapProvider(null); setLdapUsername(''); setLdapPassword(''); setError('') }}
                      className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                    >
                      Cancel
                    </button>
                  </div>
                  <form onSubmit={handleLdapSubmit} className="space-y-3">
                    <Input
                      type="text"
                      placeholder="Username"
                      value={ldapUsername}
                      onChange={(e) => setLdapUsername(e.target.value)}
                      required
                      autoFocus
                      className="h-10 border-slate-300 bg-white text-slate-950 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-50"
                    />
                    <Input
                      type="password"
                      placeholder="Password"
                      value={ldapPassword}
                      onChange={(e) => setLdapPassword(e.target.value)}
                      required
                      className="h-10 border-slate-300 bg-white text-slate-950 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-50"
                    />
                    <Button
                      type="submit"
                      className="h-10 w-full bg-blue-600 font-semibold text-white hover:bg-blue-500"
                      disabled={ssoLoading === ldapProvider.id}
                    >
                      {ssoLoading === ldapProvider.id ? (
                        <span className="flex items-center gap-2">
                          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                          Signing in...
                        </span>
                      ) : (
                        'Sign in'
                      )}
                    </Button>
                  </form>
                </div>
              )}
            </div>

            <p className="mt-5 text-center text-xs text-slate-500 dark:text-slate-500">
              AI usage, cost, routing, and governance in one control plane.
            </p>
          </div>
        </section>
      </div>
    </main>
  )
}
