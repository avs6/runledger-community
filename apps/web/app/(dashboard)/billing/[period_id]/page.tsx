import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import {
  getBillingPeriod,
  getPeriodBreakdown,
  getReconciliation,
  listBillingAdjustments,
  getBillingOrgScopePosture,
  getBillingCrossFeaturePosture,
  getBillingDetailEvidencePosture,
} from '@/lib/api'
import BillingPeriodDetailClient from '@/components/billing/BillingPeriodDetailClient'
import type { BillingAdjustmentList, BillingOrgScopePosture, BillingCrossFeaturePosture, BillingDetailEvidencePosture, PeriodBreakdown, ReconciliationResult } from '@/types/api'

export default async function BillingPeriodDetailPage({
  params,
  searchParams,
}: {
  params: { period_id: string }
  searchParams?: { access_group_id?: string; api_key_id?: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const accessGroupId = searchParams?.access_group_id
  const apiKeyId = searchParams?.api_key_id

  let period
  try {
    period = await getBillingPeriod(session.apiKey, params.period_id)
  } catch {
    notFound()
  }

  const billingOrgPosture: BillingOrgScopePosture | null = await getBillingOrgScopePosture(session.apiKey).catch(() => null)
  const billingCrossPosture: BillingCrossFeaturePosture | null = await getBillingCrossFeaturePosture(session.apiKey).catch(() => null)
  const evidencePosture: BillingDetailEvidencePosture | null = await getBillingDetailEvidencePosture(session.apiKey).catch(() => null)

  let reconciliation: ReconciliationResult | null = null
  let breakdown: PeriodBreakdown | null = null
  let adjustments: BillingAdjustmentList = {
    items: [],
    total_credits_usd: '0',
    total_surcharges_usd: '0',
    net_adjustment_usd: '0',
  }

  await Promise.allSettled([
    getReconciliation(session.apiKey, params.period_id, {
      access_group_id: accessGroupId,
      api_key_id: apiKeyId,
    }).then((result) => {
      reconciliation = result
    }),
    getPeriodBreakdown(session.apiKey, params.period_id, {
      access_group_id: accessGroupId,
      api_key_id: apiKeyId,
    }).then((result) => {
      breakdown = result
    }),
    listBillingAdjustments(session.apiKey, params.period_id).then((result) => {
      adjustments = result
    }),
  ])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link
          href={
            accessGroupId
              ? `/billing?access_group_id=${encodeURIComponent(accessGroupId)}`
              : apiKeyId
                ? `/api-keys/${encodeURIComponent(apiKeyId)}`
                : '/billing'
          }
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
        >
          <ChevronLeft className="h-4 w-4" />
          Billing
        </Link>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            {period.period_start} - {period.period_end}
          </h1>
          <p className="mt-0.5 font-mono text-xs text-gray-400">{params.period_id}</p>
        </div>
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

      {evidencePosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Billing Detail Evidence Context</h2>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">{evidencePosture.period_days}d window</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Identity</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{evidencePosture.identity_context.workspace_users} users</p>
              <p className="text-xs text-slate-400">{evidencePosture.identity_context.api_keys} keys · {evidencePosture.identity_context.access_groups} groups</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Gateway</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{evidencePosture.gateway_context.active_routes} routes</p>
              <p className="text-xs text-slate-400">{evidencePosture.gateway_context.distinct_models_30d} models</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Sessions</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{evidencePosture.observe_context.sessions_30d}</p>
              <p className="text-xs text-slate-400">{evidencePosture.observe_context.requests_30d.toLocaleString()} requests</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Replay</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{evidencePosture.build_context.replay_experiments} experiments</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Spend</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">${evidencePosture.spend_context.total_spend_30d.toFixed(2)}</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/analytics/users" className="text-emerald-600 hover:underline dark:text-emerald-400">Users →</Link>
            <Link href="/api-keys" className="text-emerald-600 hover:underline dark:text-emerald-400">API Keys →</Link>
            <Link href="/access-groups" className="text-emerald-600 hover:underline dark:text-emerald-400">Access Groups →</Link>
            <Link href="/gateway" className="text-emerald-600 hover:underline dark:text-emerald-400">Gateway →</Link>
            <Link href="/sessions" className="text-emerald-600 hover:underline dark:text-emerald-400">Sessions →</Link>
            <Link href="/request-explorer" className="text-emerald-600 hover:underline dark:text-emerald-400">Request Explorer →</Link>
            <Link href="/replay" className="text-emerald-600 hover:underline dark:text-emerald-400">Replay Lab →</Link>
            <Link href="/organizations" className="text-emerald-600 hover:underline dark:text-emerald-400">Organizations →</Link>
          </div>
        </div>
      )}

      <BillingPeriodDetailClient
        apiKey={session.apiKey}
        period={period}
        reconciliation={reconciliation}
        breakdown={breakdown}
        adjustments={adjustments}
        accessGroupId={accessGroupId}
        apiKeyId={apiKeyId}
      />
    </div>
  )
}
