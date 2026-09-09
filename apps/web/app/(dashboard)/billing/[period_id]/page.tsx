import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ChevronLeft, FileSpreadsheet, Shield } from 'lucide-react'
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
import { num } from '@/lib/utils'

export default async function BillingPeriodDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ period_id: string }>
  searchParams?: Promise<{ access_group_id?: string; api_key_id?: string }>
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const { period_id } = await params
  const sp = (await searchParams) ?? {}
  const accessGroupId = sp.access_group_id
  const apiKeyId = sp.api_key_id

  let period
  try {
    period = await getBillingPeriod(session.apiKey, period_id)
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
    getReconciliation(session.apiKey, period_id, {
      access_group_id: accessGroupId,
      api_key_id: apiKeyId,
    }).then((result) => {
      reconciliation = result
    }),
    getPeriodBreakdown(session.apiKey, period_id, {
      access_group_id: accessGroupId,
      api_key_id: apiKeyId,
    }).then((result) => {
      breakdown = result
    }),
    listBillingAdjustments(session.apiKey, period_id).then((result) => {
      adjustments = result
    }),
  ])

  const postureChips: string[] = []
  if (billingOrgPosture) {
    postureChips.push(`${billingOrgPosture.billing_context.total_periods} periods`)
    postureChips.push(`$${num(billingOrgPosture.billing_context.total_billed_usd).toFixed(2)} billed`)
    postureChips.push(`${billingOrgPosture.org_context.access_groups} groups`)
    postureChips.push(`${billingOrgPosture.attribution_context.calls_30d} calls 30d`)
  }
  if (evidencePosture) {
    postureChips.push(`${evidencePosture.identity_context.workspace_users} users`)
    postureChips.push(`${evidencePosture.observe_context.sessions_30d} sessions`)
    postureChips.push(`${evidencePosture.observe_context.requests_30d.toLocaleString()} requests`)
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <Link
          href={
            accessGroupId
              ? `/billing?access_group_id=${encodeURIComponent(accessGroupId)}`
              : apiKeyId
                ? `/api-keys/${encodeURIComponent(apiKeyId)}`
                : '/billing'
          }
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Billing
        </Link>
      </div>

      {/* ── Hero ── */}
      <section className="relative isolate overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-emerald-950 to-teal-950 px-6 py-7 text-white shadow-lg">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(16,185,129,0.15),transparent_60%)]" />
        <div className="relative">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight">{period.period_start} — {period.period_end}</h1>
          </div>
          <p className="mt-1 font-mono text-[10px] text-slate-400">{period_id}</p>
          {postureChips.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {postureChips.map((c) => (
                <span key={c} className="rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-medium text-slate-200 ring-1 ring-white/20">
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ── Context panels ── */}
      {billingOrgPosture && (
        <div className="rounded-xl border border-emerald-300 bg-gradient-to-r from-emerald-50 to-teal-50 p-4 dark:border-emerald-800/30 dark:from-emerald-950/30 dark:to-teal-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-xs font-bold text-emerald-900 dark:text-emerald-200">Billing × Org Scope</h2>
            <span className="ml-auto text-[10px] text-emerald-500">{billingOrgPosture.period_days}d window</span>
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {[
              { label: 'Periods', value: `${billingOrgPosture.billing_context.open_periods} open · ${billingOrgPosture.billing_context.closed_periods} closed` },
              { label: 'Total Billed', value: `$${num(billingOrgPosture.billing_context.total_billed_usd).toFixed(2)}` },
              { label: 'Org Scope', value: `${billingOrgPosture.org_context.access_groups} groups · ${billingOrgPosture.org_context.workspace_users} users` },
              { label: 'Attribution', value: `${billingOrgPosture.attribution_context.calls_30d.toLocaleString()} calls · ${billingOrgPosture.attribution_context.distinct_models} models` },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg bg-white/80 p-2.5 dark:bg-slate-800/60">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">{label}</p>
                <p className="mt-0.5 text-xs font-bold text-slate-900 dark:text-white">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {billingCrossPosture && (
        <div className="rounded-xl border border-teal-300 bg-gradient-to-r from-teal-50 to-emerald-50 p-4 dark:border-teal-800/30 dark:from-teal-950/30 dark:to-emerald-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="h-4 w-4 text-teal-600 dark:text-teal-400" />
            <h2 className="text-xs font-bold text-teal-900 dark:text-teal-200">Cross-Feature Context</h2>
            <span className="ml-auto text-[10px] text-teal-500">{billingCrossPosture.period_days}d window</span>
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {[
              { label: 'Gateway', value: `${billingCrossPosture.gateway_context.routes} routes · ${billingCrossPosture.gateway_context.active_providers_30d} providers` },
              { label: 'Safety', value: `${billingCrossPosture.safety_context.alert_rules} alerts · ${billingCrossPosture.safety_context.tool_registry_count} tools` },
              { label: 'Platform', value: `${billingCrossPosture.platform_context.total_organizations} orgs · ${billingCrossPosture.safety_context.audit_events_30d} events` },
              { label: 'Spend', value: `$${num(billingCrossPosture.spend_context.total_spend_30d).toFixed(2)} · ${billingCrossPosture.gateway_context.distinct_models_30d} models` },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg bg-white/80 p-2.5 dark:bg-slate-800/60">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-teal-600 dark:text-teal-400">{label}</p>
                <p className="mt-0.5 text-xs font-bold text-slate-900 dark:text-white">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {evidencePosture && (
        <div className="rounded-xl border border-emerald-300 bg-gradient-to-r from-emerald-50 to-green-50 p-4 dark:border-emerald-800/30 dark:from-emerald-950/30 dark:to-green-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-xs font-bold text-emerald-900 dark:text-emerald-200">Detail Evidence Context</h2>
            <span className="ml-auto text-[10px] text-emerald-500">{evidencePosture.period_days}d window</span>
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
            {[
              { label: 'Identity', value: `${evidencePosture.identity_context.workspace_users} users · ${evidencePosture.identity_context.api_keys} keys` },
              { label: 'Gateway', value: `${evidencePosture.gateway_context.active_routes} routes · ${evidencePosture.gateway_context.distinct_models_30d} models` },
              { label: 'Sessions', value: `${evidencePosture.observe_context.sessions_30d} · ${evidencePosture.observe_context.requests_30d.toLocaleString()} reqs` },
              { label: 'Replay', value: `${evidencePosture.build_context.replay_experiments} experiments` },
              { label: 'Spend', value: `$${num(evidencePosture.spend_context.total_spend_30d).toFixed(2)}` },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg bg-white/80 p-2.5 dark:bg-slate-800/60">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">{label}</p>
                <p className="mt-0.5 text-xs font-bold text-slate-900 dark:text-white">{value}</p>
              </div>
            ))}
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
