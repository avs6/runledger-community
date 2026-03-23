import Link from 'next/link'
import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'

export const dynamic = 'force-dynamic'

function RunLedgerLogo({ size = 48 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="lp-grad" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0f766e" />
          <stop offset="100%" stopColor="#0891b2" />
        </linearGradient>
      </defs>
      <rect width="56" height="56" rx="14" fill="url(#lp-grad)" />
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

const FEATURES = [
  {
    icon: '⚡',
    title: 'Sub-5ms Budget Enforcement',
    desc: 'Redis-backed hot path checks every provider call against your budgets before it fires. No polling, no latency hit.',
  },
  {
    icon: '📊',
    title: 'Billing-grade Metering',
    desc: 'Every token, latency, cost, and model version tracked to the span level. Partitioned Postgres with materialized rollups.',
  },
  {
    icon: '💸',
    title: 'Chargeback & Cost Attribution',
    desc: 'Allocate spend by team, feature, environment, or end-user. Close billing periods with tamper-evident HMAC-signed snapshots.',
  },
  {
    icon: '🔀',
    title: 'Intelligent Model Routing',
    desc: 'Route by cost, latency, quality, or canary weight. Gateway caches prompts and forwards to any OpenAI-compatible endpoint.',
  },
  {
    icon: '🧪',
    title: 'Prompt Management & Evals',
    desc: 'Version, diff, and promote prompts across environments. Score runs with human or LLM judges and detect regressions.',
  },
  {
    icon: '🔒',
    title: 'Privacy & Audit Governance',
    desc: 'METADATA_ONLY by default. FULL, SAMPLED, and ERRORS_ONLY capture modes. Ledger snapshots for compliance.',
  },
]

const PLANS = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    events: '10,000 events / mo',
    cta: 'Get started free',
    href: '/signup',
    highlight: false,
    features: ['Full observability', 'Run explorer + DAG', 'Basic analytics', '1 workspace'],
  },
  {
    name: 'Starter',
    price: '$49',
    period: '/month',
    events: '500,000 events / mo',
    cta: 'Start free trial',
    href: '/signup',
    highlight: true,
    features: ['Everything in Free', 'Budget enforcement', 'Slack alerts', 'Prompt management', '5 workspaces'],
  },
  {
    name: 'Growth',
    price: '$199',
    period: '/month',
    events: '5M events / mo',
    cta: 'Start free trial',
    href: '/signup',
    highlight: false,
    features: ['Everything in Starter', 'Chargeback + billing export', 'Replay harness', 'RBAC', 'Unlimited workspaces'],
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    events: '100M+ events / mo',
    cta: 'Contact sales',
    href: 'mailto:sales@runledger.io',
    highlight: false,
    features: ['Everything in Growth', 'SSO / SAML', 'Custom retention', 'Dedicated support', 'SLA'],
  },
]

const PROVIDERS = ['OpenAI', 'Anthropic', 'Gemini', 'Mistral', 'Cohere', 'Ollama']

export default async function LandingPage() {
  const session = await getServerSession(authOptions)
  if (session) redirect('/dashboard')

  return (
    <div className="min-h-screen bg-slate-950 text-white">

      {/* ── Nav ── */}
      <header className="sticky top-0 z-50 border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-2.5">
            <RunLedgerLogo size={32} />
            <div>
              <div className="text-sm font-semibold leading-none text-white">RunLedger</div>
              <div className="mt-0.5 text-[9px] font-bold uppercase tracking-[0.18em] text-teal-400 leading-none">
                Control Plane
              </div>
            </div>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-sm text-slate-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How it works</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/signup"
              className="rounded-lg bg-gradient-to-r from-teal-600 to-cyan-600 px-4 py-2 text-sm font-semibold text-white shadow hover:from-teal-500 hover:to-cyan-500 transition-all"
            >
              Get started free
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="relative overflow-hidden px-6 pb-24 pt-20 text-center">
        {/* Background glow */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="h-[500px] w-[800px] rounded-full bg-teal-900/20 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-3xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-teal-700/40 bg-teal-900/30 px-4 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-teal-400 animate-pulse" />
            <span className="text-xs font-medium text-teal-300">Open-source · Self-hostable · Free tier</span>
          </div>

          <h1 className="mb-5 text-5xl font-bold leading-tight tracking-tight md:text-6xl">
            Billing-grade observability
            <br />
            <span className="bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">
              for AI agents.
            </span>
          </h1>

          <p className="mx-auto mb-8 max-w-xl text-lg text-slate-400 leading-relaxed">
            Track every token, enforce budgets in under 5ms, and understand the full economics of every agent run — across OpenAI, Anthropic, Gemini, and more.
          </p>

          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Link
              href="/signup"
              className="w-full sm:w-auto rounded-xl bg-gradient-to-r from-teal-600 to-cyan-600 px-8 py-3.5 text-base font-semibold text-white shadow-lg hover:from-teal-500 hover:to-cyan-500 transition-all"
            >
              Start for free
            </Link>
            <Link
              href="/login"
              className="w-full sm:w-auto rounded-xl border border-slate-700 bg-slate-900 px-8 py-3.5 text-base font-semibold text-slate-200 hover:bg-slate-800 hover:border-slate-600 transition-all"
            >
              Sign in
            </Link>
          </div>

          <p className="mt-4 text-xs text-slate-600">No credit card required · 10,000 events/month free</p>

          {/* Provider logos */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            <span className="text-xs text-slate-600 uppercase tracking-wider">Works with</span>
            {PROVIDERS.map(p => (
              <span key={p} className="text-sm font-medium text-slate-500">{p}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how-it-works" className="border-y border-slate-800/60 bg-slate-900/40 px-6 py-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="mb-10 text-center text-3xl font-bold">Up and running in 2 minutes</h2>
          <div className="grid gap-6 md:grid-cols-3">
            {[
              {
                step: '01',
                title: 'Install the SDK',
                code: 'pip install runledger-sdk',
                desc: 'One package for Python. TypeScript SDK available for Node.js.',
              },
              {
                step: '02',
                title: 'Wrap your client',
                code: 'rl.instrument(openai_client)',
                desc: 'One line wraps OpenAI, Anthropic, Gemini, Mistral, or Cohere.',
              },
              {
                step: '03',
                title: 'See everything',
                code: 'runledger.io/dashboard',
                desc: 'Every run, span, cost, and budget appears in real time.',
              },
            ].map(({ step, title, code, desc }) => (
              <div key={step} className="rounded-xl border border-slate-800 bg-slate-900 p-6">
                <div className="mb-3 text-xs font-bold tracking-widest text-teal-500">{step}</div>
                <h3 className="mb-2 text-base font-semibold text-white">{title}</h3>
                <div className="mb-3 rounded-lg bg-slate-950 px-3 py-2 font-mono text-sm text-teal-300">{code}</div>
                <p className="text-sm text-slate-400">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <div className="mb-14 text-center">
            <h2 className="mb-3 text-3xl font-bold">Everything you need to control AI spend</h2>
            <p className="text-slate-400">Production-grade from day one. Not prototype quality.</p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon, title, desc }) => (
              <div
                key={title}
                className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 hover:border-slate-700 transition-colors"
              >
                <div className="mb-3 text-2xl">{icon}</div>
                <h3 className="mb-2 text-base font-semibold text-white">{title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Social proof strip ── */}
      <section className="border-y border-slate-800/60 bg-slate-900/40 px-6 py-12">
        <div className="mx-auto max-w-4xl">
          <div className="grid grid-cols-2 gap-8 text-center md:grid-cols-4">
            {[
              { stat: '<5ms', label: 'Budget enforcement p99' },
              { stat: '6+', label: 'Provider integrations' },
              { stat: '100%', label: 'Async, non-blocking SDK' },
              { stat: 'OSS', label: 'MIT licensed core' },
            ].map(({ stat, label }) => (
              <div key={label}>
                <div className="text-3xl font-bold text-teal-400">{stat}</div>
                <div className="mt-1 text-sm text-slate-500">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <div className="mb-14 text-center">
            <h2 className="mb-3 text-3xl font-bold">Simple, transparent pricing</h2>
            <p className="text-slate-400">Start free. Upgrade when you need more.</p>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
            {PLANS.map(plan => (
              <div
                key={plan.name}
                className={`relative flex flex-col rounded-xl border p-6 ${
                  plan.highlight
                    ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                    : 'border-slate-800 bg-slate-900/60'
                }`}
              >
                {plan.highlight && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-teal-600 px-3 py-0.5 text-xs font-semibold text-white">
                    Most popular
                  </div>
                )}
                <div className="mb-4">
                  <div className="text-base font-semibold text-white">{plan.name}</div>
                  <div className="mt-1 flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-white">{plan.price}</span>
                    <span className="text-sm text-slate-500">{plan.period}</span>
                  </div>
                  <div className="mt-1 text-xs font-medium text-teal-400">{plan.events}</div>
                </div>
                <ul className="mb-6 flex-1 space-y-2">
                  {plan.features.map(f => (
                    <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                      <span className="text-teal-500">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href={plan.href}
                  className={`block rounded-lg px-4 py-2.5 text-center text-sm font-semibold transition-all ${
                    plan.highlight
                      ? 'bg-gradient-to-r from-teal-600 to-cyan-600 text-white hover:from-teal-500 hover:to-cyan-500'
                      : 'border border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700'
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="px-6 pb-24">
        <div className="mx-auto max-w-2xl rounded-2xl border border-teal-800/40 bg-gradient-to-br from-teal-950/60 to-cyan-950/40 p-12 text-center">
          <h2 className="mb-3 text-3xl font-bold">Ready to control your AI spend?</h2>
          <p className="mb-8 text-slate-400">
            Set up in minutes. No infrastructure to manage. Free forever for OSS projects.
          </p>
          <Link
            href="/signup"
            className="inline-block rounded-xl bg-gradient-to-r from-teal-600 to-cyan-600 px-10 py-3.5 text-base font-semibold text-white shadow-lg hover:from-teal-500 hover:to-cyan-500 transition-all"
          >
            Create your free account
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-slate-800/60 px-6 py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2">
            <RunLedgerLogo size={24} />
            <span className="text-sm text-slate-500">RunLedger</span>
          </div>
          <div className="flex gap-6 text-sm text-slate-600">
            <Link href="/login" className="hover:text-slate-400 transition-colors">Sign in</Link>
            <Link href="/signup" className="hover:text-slate-400 transition-colors">Sign up</Link>
            <a href="https://github.com/avs6/runledger" className="hover:text-slate-400 transition-colors">GitHub</a>
          </div>
          <p className="text-xs text-slate-700">© {new Date().getFullYear()} RunLedger. MIT License.</p>
        </div>
      </footer>

    </div>
  )
}
