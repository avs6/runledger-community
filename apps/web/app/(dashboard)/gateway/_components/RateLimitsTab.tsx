'use client'

import Link from 'next/link'
import { SectionError } from '@/components/ui/async-card'
import { useGateway } from './useGatewayState'

export function RateLimitsTab() {
  const {
    rateLimitOverview,
    sectionErrors,
    loadTabData,
  } = useGateway()
  return (
  <div className="space-y-3">
  {sectionErrors.rateLimits && <SectionError message={sectionErrors.rateLimits} onRetry={() => void loadTabData('rate-limits', true)} />}
  {/* ui-fixes #2: this tab reports limits; they are set on routes and budget tiers. */}
  <p role="note" className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
    Overview only. Per-user RPM is set on each route (Routes tab); per-key requests/min, tokens/min and allowed models are set on budget tiers (Advanced tab), and both are enforced by the gateway.
  </p>

  {rateLimitOverview && (
    <section className="space-y-4">
      <div>
        <h2 className="text-base font-semibold dark:text-white">Rate Limit Controls</h2>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          Gateway owns live throttles and quota mechanics on traffic. FinOps budgets own the spend policy around that traffic, so these controls should be reviewed together.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {rateLimitOverview.tiers.map((tier) => (
          <div key={tier.key} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold dark:text-white">{tier.name}</h3>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                {tier.rpm.toLocaleString()} rpm
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{tier.description}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
              {tier.endpoints.map((endpoint) => (
                <span key={endpoint} className="rounded-full bg-indigo-100 px-2 py-0.5 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                  {endpoint}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 p-4">
          <h3 className="text-sm font-semibold dark:text-white">Gateway-owned runtime throttles</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-white px-3 py-3 dark:bg-slate-900/50">
              <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Routes with per-user RPM</p>
              <p className="mt-1 text-2xl font-semibold dark:text-white">{rateLimitOverview.route_rate_limited_count}</p>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                {rateLimitOverview.route_rate_limited_aliases.length > 0 ? rateLimitOverview.route_rate_limited_aliases.join(', ') : 'No route-level per-user throttles configured yet.'}
              </p>
            </div>
            <div className="rounded-lg bg-white px-3 py-3 dark:bg-slate-900/50">
              <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Pass-through endpoints with RPM</p>
              <p className="mt-1 text-2xl font-semibold dark:text-white">{rateLimitOverview.passthrough_rate_limited_count}</p>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                {rateLimitOverview.passthrough_rate_limited_slugs.length > 0 ? rateLimitOverview.passthrough_rate_limited_slugs.join(', ') : 'No pass-through endpoint throttles configured yet.'}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 p-4">
          <h3 className="text-sm font-semibold dark:text-white">FinOps-owned quota controls</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-white px-3 py-3 dark:bg-slate-900/50">
              <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Budget tiers with RPM/TPM</p>
              <p className="mt-1 text-2xl font-semibold dark:text-white">{rateLimitOverview.budget_tier_rate_limited_count}</p>
              <a href="#gateway-quota-tiers" className="mt-2 inline-block text-xs font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-300">
                Open Budget Tiers
              </a>
            </div>
            <div className="rounded-lg bg-white px-3 py-3 dark:bg-slate-900/50">
              <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Model budgets with RPM/TPM</p>
              <p className="mt-1 text-2xl font-semibold dark:text-white">{rateLimitOverview.model_budget_rate_limited_count}</p>
              <a href="#gateway-model-quotas" className="mt-2 inline-block text-xs font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-300">
                Open Model Budgets
              </a>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 p-4">
          <h3 className="text-sm font-semibold dark:text-white">Spend policy linkage</h3>
          <div className="mt-3 rounded-lg bg-white px-3 py-3 dark:bg-slate-900/50">
            <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Budget policy control plane</p>
            <p className="mt-1 text-2xl font-semibold dark:text-white">Budgets</p>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Use Budgets for provider-profile, API-key, access-group, and workspace spend actions. Keep runtime throttles here, but review enforcement outcomes in FinOps.
            </p>
            <Link href="/budgets" className="mt-2 inline-block text-xs font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-300">
              Open Budgets
            </Link>
          </div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-3">
        <Link href="/budgets" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Budgets</Link>
        <Link href="/billing" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Billing Periods</Link>
        <Link href="/chargeback" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Chargeback</Link>
        <Link href="/workspace" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Workspaces</Link>
        <Link href="/organizations" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">All Organizations</Link>
        <Link href="/settings" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Platform Settings</Link>
      </div>
    </section>
  )}

  </div>
  )
}
