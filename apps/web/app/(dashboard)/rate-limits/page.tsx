'use client'

import { useSession } from 'next-auth/react'

const TIERS = [
  {
    name: 'Ingest',
    description: 'Run ingestion, OTLP, and gateway proxy endpoints',
    rpm: 600,
    endpoints: ['/ingest/*', '/v1/chat/completions', '/otlp/*'],
    headers: true,
  },
  {
    name: 'Analytics',
    description: 'Dashboard reads, cost queries, and reporting endpoints',
    rpm: 120,
    endpoints: ['/analytics/*', '/budgets/*', '/runs/*'],
    headers: true,
  },
  {
    name: 'Management',
    description: 'CRUD operations for settings, keys, budgets, and admin',
    rpm: 60,
    endpoints: ['/settings/*', '/api-keys/*', '/budgets (writes)', '/admin/*'],
    headers: true,
  },
]

const HEADERS = [
  { name: 'X-RateLimit-Limit-Requests', description: 'Maximum requests allowed in the current window' },
  { name: 'X-RateLimit-Remaining-Requests', description: 'Requests remaining before throttling' },
  { name: 'X-RateLimit-Limit-Tokens', description: 'Maximum tokens allowed (when applicable)' },
  { name: 'X-RateLimit-Remaining-Tokens', description: 'Tokens remaining in the current window' },
  { name: 'X-RateLimit-Reset', description: 'Seconds until the rate limit window resets' },
]

export default function RateLimitsPage() {
  const { data: session } = useSession()
  if (!session) return null

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-[-0.04em] text-slate-950 dark:text-slate-50">
          Rate Limits
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          RunLedger uses a three-tier sliding-window rate limiter. Every response includes rate limit headers.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {TIERS.map((tier) => (
          <div
            key={tier.name}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">{tier.name}</h3>
            <p className="mt-1 text-xs text-slate-500">{tier.description}</p>
            <div className="mt-4 flex items-baseline gap-1">
              <span className="text-3xl font-bold text-slate-900 dark:text-white">{tier.rpm}</span>
              <span className="text-sm text-slate-500">req/min</span>
            </div>
            <div className="mt-4 space-y-1">
              {tier.endpoints.map((ep) => (
                <div key={ep} className="rounded bg-slate-50 px-2 py-1 font-mono text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                  {ep}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-white">Response Headers</h2>
        <p className="mb-4 text-sm text-slate-500">
          Every API response includes these headers so clients can implement backoff and throttling.
        </p>
        <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Header</th>
                <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {HEADERS.map((h) => (
                <tr key={h.name} className="bg-white dark:bg-slate-900">
                  <td className="px-4 py-3 font-mono text-xs font-medium text-blue-600 dark:text-blue-400">{h.name}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{h.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-white">Budget Tier Rate Limits</h2>
        <p className="text-sm text-slate-500">
          API keys assigned to a <a href="/budget-tiers" className="text-blue-600 underline dark:text-blue-400">Budget Tier</a> inherit
          the tier&apos;s RPM and TPM limits. These override the default sliding-window limits above.
          Use <a href="/model-budgets" className="text-blue-600 underline dark:text-blue-400">Model Budgets</a> for per-model rate controls.
        </p>
      </div>

      <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 dark:border-amber-900/50 dark:bg-amber-950/20">
        <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-300">429 Too Many Requests</h3>
        <p className="mt-1 text-xs text-amber-700 dark:text-amber-400">
          When a rate limit is exceeded, RunLedger returns HTTP 429 with a <code className="rounded bg-amber-100 px-1 dark:bg-amber-900/40">Retry-After</code> header
          indicating how many seconds to wait. Clients should implement exponential backoff.
        </p>
      </div>
    </div>
  )
}
