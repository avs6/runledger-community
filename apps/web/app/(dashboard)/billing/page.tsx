import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { FileSpreadsheet, Shield } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getBillingPeriods, getBillingSummary, getBillingOrgScopePosture, getBillingCrossFeaturePosture, getBillingReconciliationPosture } from '@/lib/api'
import BillingWorkspaceClient from '@/components/billing/BillingWorkspaceClient'
import type { BillingOrgScopePosture, BillingCrossFeaturePosture, BillingReconciliationPosture } from '@/types/api'
import { num } from '@/lib/utils'

export default async function BillingPage({
  searchParams,
}: {
  searchParams?: Promise<{ tab?: string; months?: string; access_group_id?: string }>
}) {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  const sp = (await searchParams) ?? {}
  const tab = sp.tab === 'summary'
    ? 'summary'
    : sp.tab === 'shared-costs'
      ? 'shared-costs'
      : 'periods'
  const summaryMonths = [3, 6, 12].includes(Number(sp.months))
    ? Number(sp.months)
    : 6
  const accessGroupId = sp.access_group_id

  const [periods, summary, billingOrgPosture, billingCrossPosture, reconciliationPosture] = await Promise.all([
    getBillingPeriods(session.apiKey, { access_group_id: accessGroupId }),
    getBillingSummary(session.apiKey, summaryMonths).catch(() => ({ workspace_id: '', periods: [] })),
    getBillingOrgScopePosture(session.apiKey).catch(() => null) as Promise<BillingOrgScopePosture | null>,
    getBillingCrossFeaturePosture(session.apiKey).catch(() => null) as Promise<BillingCrossFeaturePosture | null>,
    getBillingReconciliationPosture(session.apiKey).catch(() => null) as Promise<BillingReconciliationPosture | null>,
  ])

  const postureChips: string[] = []
  if (billingOrgPosture) {
    postureChips.push(`${billingOrgPosture.billing_context.total_periods} periods`)
    postureChips.push(`${billingOrgPosture.billing_context.open_periods} open`)
    postureChips.push(`$${num(billingOrgPosture.billing_context.total_billed_usd).toFixed(2)} billed`)
    postureChips.push(`${billingOrgPosture.org_context.access_groups} groups`)
    postureChips.push(`${billingOrgPosture.org_context.api_keys} keys`)
    postureChips.push(`${billingOrgPosture.attribution_context.calls_30d} calls 30d`)
  }
  if (reconciliationPosture) {
    postureChips.push(`${reconciliationPosture.provider_context.active_providers_30d} providers`)
    postureChips.push(`${reconciliationPosture.provider_context.distinct_models_30d} models`)
    postureChips.push(`$${num(reconciliationPosture.optimization_context.cache_savings_usd).toFixed(2)} cache savings`)
  }

  return (
    <div className="space-y-5">
      {/* ── Hero ── */}
      <section className="relative isolate overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-emerald-950 to-teal-950 px-6 py-8 text-white shadow-lg">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(16,185,129,0.15),transparent_60%)]" />
        <div className="relative">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-6 w-6 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight">Billing</h1>
          </div>
          <p className="mt-1.5 max-w-xl text-[11px] leading-relaxed text-slate-300">
            Operate billing periods, review reconciliation quality, manage shared-cost policies, and export finance-ready evidence in one place.
          </p>
          {postureChips.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {postureChips.map((c) => (
                <span key={c} className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] font-medium text-slate-300 ring-1 ring-white/10">
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* KPI strip */}
        <div className="relative mt-6 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {[
            { label: 'Periods', value: billingOrgPosture ? String(billingOrgPosture.billing_context.total_periods) : String(periods.items.length) },
            { label: 'Open', value: billingOrgPosture ? String(billingOrgPosture.billing_context.open_periods) : '—' },
            { label: 'Total Billed', value: billingOrgPosture ? `$${num(billingOrgPosture.billing_context.total_billed_usd).toFixed(2)}` : '—' },
            { label: '30d Spend', value: billingOrgPosture ? `$${num(billingOrgPosture.spend_context.total_spend_30d).toFixed(2)}` : '—' },
            { label: 'Access Groups', value: billingOrgPosture ? String(billingOrgPosture.org_context.access_groups) : '—' },
            { label: 'API Keys', value: billingOrgPosture ? String(billingOrgPosture.org_context.api_keys) : '—' },
          ].map((kpi) => (
            <div key={kpi.label} className="rounded-lg bg-white/5 px-3 py-2 ring-1 ring-white/10">
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">{kpi.label}</p>
              <p className="mt-0.5 truncate text-sm font-bold">{kpi.value}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Context panels ── */}
      {billingOrgPosture && (
        <div className="rounded-xl border border-emerald-200/50 bg-gradient-to-r from-emerald-50/60 to-teal-50/60 p-4 dark:border-emerald-800/30 dark:from-emerald-950/30 dark:to-teal-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-xs font-bold text-emerald-900 dark:text-emerald-200">Billing × Org Scope Context</h2>
            <span className="ml-auto text-[10px] text-emerald-500 dark:text-emerald-400">{billingOrgPosture.period_days}d window</span>
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
        <div className="rounded-xl border border-emerald-200/50 bg-gradient-to-r from-teal-50/60 to-emerald-50/60 p-4 dark:border-teal-800/30 dark:from-teal-950/30 dark:to-emerald-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="h-4 w-4 text-teal-600 dark:text-teal-400" />
            <h2 className="text-xs font-bold text-teal-900 dark:text-teal-200">Billing × Cross-Feature Context</h2>
            <span className="ml-auto text-[10px] text-teal-500 dark:text-teal-400">{billingCrossPosture.period_days}d window</span>
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

      {reconciliationPosture && (
        <div className="rounded-xl border border-emerald-200/50 bg-gradient-to-r from-emerald-50/60 to-green-50/60 p-4 dark:border-emerald-800/30 dark:from-emerald-950/30 dark:to-green-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-xs font-bold text-emerald-900 dark:text-emerald-200">Billing Reconciliation Context</h2>
            <span className="ml-auto text-[10px] text-emerald-500 dark:text-emerald-400">{reconciliationPosture.period_days}d window</span>
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
            {[
              { label: 'Identity', value: `${reconciliationPosture.identity_context.workspace_users} users · ${reconciliationPosture.identity_context.api_keys} keys` },
              { label: 'Providers', value: `${reconciliationPosture.provider_context.active_providers_30d} active · ${reconciliationPosture.provider_context.distinct_models_30d} models` },
              { label: 'Optimization', value: `${reconciliationPosture.optimization_context.billing_periods} periods · $${num(reconciliationPosture.optimization_context.cache_savings_usd).toFixed(2)} savings` },
              { label: 'Evidence', value: `${reconciliationPosture.evidence_context.alert_rules} alerts · ${reconciliationPosture.evidence_context.audit_events_30d} events` },
              { label: 'Spend', value: `$${num(reconciliationPosture.spend_context.total_spend_30d).toFixed(2)}` },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg bg-white/80 p-2.5 dark:bg-slate-800/60">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">{label}</p>
                <p className="mt-0.5 text-xs font-bold text-slate-900 dark:text-white">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Billing client */}
      <BillingWorkspaceClient
        apiKey={session.apiKey}
        initialPeriods={periods.items}
        summary={summary}
        initialTab={tab}
        initialMonths={summaryMonths}
        accessGroupId={accessGroupId}
      />

      {/* ── Quick-nav footer ── */}
      <div className="flex flex-wrap gap-2 pt-2">
        {[
          { label: 'Cost & Savings', href: '/cost-savings' },
          { label: 'Budgets', href: '/budgets' },
          { label: 'Chargeback', href: '/chargeback' },
          { label: 'Access Groups', href: '/access-groups' },
          { label: 'API Keys', href: '/api-keys' },
          { label: 'Gateway', href: '/gateway' },
          { label: 'Alert Rules', href: '/alert-rules' },
          { label: 'Audit Log', href: '/audit' },
          { label: 'Telemetry', href: '/telemetry' },
        ].map(({ label, href }) => (
          <Link
            key={label}
            href={href}
            className="rounded-full border border-emerald-200 bg-emerald-50/80 px-3 py-1 text-[11px] font-semibold text-emerald-700 transition hover:bg-emerald-100 dark:border-emerald-800/50 dark:bg-emerald-950/30 dark:text-emerald-300 dark:hover:bg-emerald-900/40"
          >
            {label}
          </Link>
        ))}
      </div>
    </div>
  )
}
