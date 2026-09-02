import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getBillingPeriods, getBillingSummary, getBillingOrgScopePosture, getBillingCrossFeaturePosture, getBillingReconciliationPosture } from '@/lib/api'
import BillingWorkspaceClient from '@/components/billing/BillingWorkspaceClient'
import type { BillingOrgScopePosture, BillingCrossFeaturePosture, BillingReconciliationPosture } from '@/types/api'

export default async function BillingPage({
  searchParams,
}: {
  searchParams?: { tab?: string; months?: string; access_group_id?: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  const tab = searchParams?.tab === 'summary'
    ? 'summary'
    : searchParams?.tab === 'shared-costs'
      ? 'shared-costs'
      : 'periods'
  const summaryMonths = [3, 6, 12].includes(Number(searchParams?.months))
    ? Number(searchParams?.months)
    : 6
  const accessGroupId = searchParams?.access_group_id

  const [periods, summary, billingOrgPosture, billingCrossPosture, reconciliationPosture] = await Promise.all([
    getBillingPeriods(session.apiKey, { access_group_id: accessGroupId }),
    getBillingSummary(session.apiKey, summaryMonths).catch(() => ({ workspace_id: '', periods: [] })),
    getBillingOrgScopePosture(session.apiKey).catch(() => null) as Promise<BillingOrgScopePosture | null>,
    getBillingCrossFeaturePosture(session.apiKey).catch(() => null) as Promise<BillingCrossFeaturePosture | null>,
    getBillingReconciliationPosture(session.apiKey).catch(() => null) as Promise<BillingReconciliationPosture | null>,
  ])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Billing</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Operate billing periods, review reconciliation quality, manage shared-cost policies, and export finance-ready evidence in one place.
        </p>
      </div>

      {billingOrgPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 dark:border-emerald-900 dark:bg-emerald-950/40">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Billing × Org Scope Context</h2>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">{billingOrgPosture.period_days}d window</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Periods</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{billingOrgPosture.billing_context.total_periods}</p>
              <p className="text-xs text-slate-400">{billingOrgPosture.billing_context.open_periods} open · {billingOrgPosture.billing_context.closed_periods} closed</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Total Billed</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">${billingOrgPosture.billing_context.total_billed_usd.toFixed(2)}</p>
              <p className="text-xs text-slate-400">{billingOrgPosture.spend_context.total_spend_30d.toFixed(2)} 30d spend</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Org Scope</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{billingOrgPosture.org_context.access_groups} groups</p>
              <p className="text-xs text-slate-400">{billingOrgPosture.org_context.api_keys} keys · {billingOrgPosture.org_context.workspace_users} users</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Attribution</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{billingOrgPosture.attribution_context.calls_30d.toLocaleString()} calls</p>
              <p className="text-xs text-slate-400">{billingOrgPosture.attribution_context.distinct_models} models</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/access-groups" className="text-emerald-700 hover:underline dark:text-emerald-400">Access Groups →</Link>
            <Link href="/api-keys" className="text-emerald-700 hover:underline dark:text-emerald-400">API Keys →</Link>
            <Link href="/organizations" className="text-emerald-700 hover:underline dark:text-emerald-400">Organization →</Link>
            <Link href="/telemetry" className="text-emerald-700 hover:underline dark:text-emerald-400">Telemetry →</Link>
            <Link href="/ai-hub" className="text-emerald-700 hover:underline dark:text-emerald-400">AI Hub →</Link>
          </div>
        </div>
      )}

      {billingCrossPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Billing × Cross-Feature Context</h2>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">{billingCrossPosture.period_days}d window</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Gateway</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{billingCrossPosture.gateway_context.routes} routes</p>
              <p className="text-xs text-slate-400">{billingCrossPosture.gateway_context.active_providers_30d} providers · {billingCrossPosture.gateway_context.cache_configs} caches</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Safety</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{billingCrossPosture.safety_context.alert_rules} alert rules</p>
              <p className="text-xs text-slate-400">{billingCrossPosture.safety_context.tool_registry_count} tools · {billingCrossPosture.safety_context.tags} tags</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Platform</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{billingCrossPosture.platform_context.total_organizations} orgs</p>
              <p className="text-xs text-slate-400">{billingCrossPosture.safety_context.audit_events_30d} audit events</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Spend</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">${billingCrossPosture.spend_context.total_spend_30d.toFixed(2)}</p>
              <p className="text-xs text-slate-400">{billingCrossPosture.gateway_context.distinct_models_30d} models · {billingCrossPosture.gateway_context.rate_limit_endpoints} rate limits</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/gateway" className="text-emerald-600 hover:underline dark:text-emerald-400">Gateway →</Link>
            <Link href="/tool-registry" className="text-emerald-600 hover:underline dark:text-emerald-400">Tool Registry →</Link>
            <Link href="/alerts" className="text-emerald-600 hover:underline dark:text-emerald-400">Alert Rules →</Link>
            <Link href="/audit" className="text-emerald-600 hover:underline dark:text-emerald-400">Audit Log →</Link>
            <Link href="/tags" className="text-emerald-600 hover:underline dark:text-emerald-400">Tags →</Link>
            <Link href="/settings" className="text-emerald-600 hover:underline dark:text-emerald-400">Platform →</Link>
          </div>
        </div>
      )}

      {reconciliationPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Billing Reconciliation Context</h2>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">{reconciliationPosture.period_days}d window</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Identity</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{reconciliationPosture.identity_context.workspace_users} users</p>
              <p className="text-xs text-slate-400">{reconciliationPosture.identity_context.api_keys} keys · {reconciliationPosture.identity_context.access_groups} groups</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Providers</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{reconciliationPosture.provider_context.active_providers_30d} active</p>
              <p className="text-xs text-slate-400">{reconciliationPosture.provider_context.distinct_models_30d} models · {reconciliationPosture.provider_context.cache_configs} caches</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Optimization</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{reconciliationPosture.optimization_context.billing_periods} periods</p>
              <p className="text-xs text-slate-400">${reconciliationPosture.optimization_context.cache_savings_usd.toFixed(2)} cache savings</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Evidence</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{reconciliationPosture.evidence_context.alert_rules} alert rules</p>
              <p className="text-xs text-slate-400">{reconciliationPosture.evidence_context.audit_events_30d} audit events</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Spend</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">${reconciliationPosture.spend_context.total_spend_30d.toFixed(2)}</p>
              <p className="text-xs text-slate-400">{reconciliationPosture.optimization_context.alert_rules} cost alerts</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/analytics/users" className="text-emerald-600 hover:underline dark:text-emerald-400">Users →</Link>
            <Link href="/api-keys" className="text-emerald-600 hover:underline dark:text-emerald-400">API Keys →</Link>
            <Link href="/access-groups" className="text-emerald-600 hover:underline dark:text-emerald-400">Access Groups →</Link>
            <Link href="/gateway" className="text-emerald-600 hover:underline dark:text-emerald-400">Gateway →</Link>
            <Link href="/alerts" className="text-emerald-600 hover:underline dark:text-emerald-400">Alert Rules →</Link>
            <Link href="/audit" className="text-emerald-600 hover:underline dark:text-emerald-400">Audit Log →</Link>
            <Link href="/optimization" className="text-emerald-600 hover:underline dark:text-emerald-400">Optimization →</Link>
            <Link href="/settings" className="text-emerald-600 hover:underline dark:text-emerald-400">Platform →</Link>
          </div>
        </div>
      )}

      <BillingWorkspaceClient
        apiKey={session.apiKey}
        initialPeriods={periods.items}
        summary={summary}
        initialTab={tab}
        initialMonths={summaryMonths}
        accessGroupId={accessGroupId}
      />
    </div>
  )
}
