import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { Shield, Wallet } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import {
  getBudgetRollup,
  getBudgets,
  listBudgetNotifications,
  listBudgetTiers,
  getFinOpsInternalPosture,
  getBudgetScopeGovernancePosture,
} from '@/lib/api'
import BudgetManager from '@/components/budgets/BudgetManager'
import type { BudgetScopeGovernancePosture, FinOpsInternalPosture } from '@/types/api'
import { num } from '@/lib/utils'

interface PageProps {
  searchParams?: Promise<Record<string, string | string[] | undefined>>
}

export default async function BudgetsPage({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  const params = (await searchParams) ?? {}
  const requestedTab = Array.isArray(params.tab) ? params.tab[0] : params.tab
  const requestedScopeType = Array.isArray(params.scope_type) ? params.scope_type[0] : params.scope_type
  const requestedScopeId = Array.isArray(params.scope_id) ? params.scope_id[0] : params.scope_id
  const requestedCreate = Array.isArray(params.create) ? params.create[0] : params.create
  const initialTab =
    requestedTab === 'overrides' || requestedTab === 'notifications'
      ? requestedTab
      : 'policies'
  const initialScopeType =
    requestedScopeType === 'workspace' ||
    requestedScopeType === 'end_user' ||
    requestedScopeType === 'feature_tag' ||
    requestedScopeType === 'app' ||
    requestedScopeType === 'access_group' ||
    requestedScopeType === 'api_key' ||
    requestedScopeType === 'provider_profile'
      ? requestedScopeType
      : undefined

  const [budgets, tiers, notifications, rollup, finopsPosture, budgetScopePosture] = await Promise.all([
    getBudgets(session.apiKey, {
      scope_type: initialScopeType,
      scope_id: requestedScopeId,
    }),
    listBudgetTiers(session.apiKey).catch(() => ({ items: [] })),
    listBudgetNotifications(session.apiKey).catch(() => ({ items: [] })),
    getBudgetRollup(session.apiKey).catch(() => null),
    getFinOpsInternalPosture(session.apiKey).catch(() => null) as Promise<FinOpsInternalPosture | null>,
    getBudgetScopeGovernancePosture(session.apiKey).catch(() => null) as Promise<BudgetScopeGovernancePosture | null>,
  ])

  const postureChips: string[] = []
  if (finopsPosture) {
    postureChips.push(`${finopsPosture.budget_context.total_budgets} budgets`)
    postureChips.push(`${finopsPosture.budget_context.active_budgets} active`)
    postureChips.push(`$${num(finopsPosture.budget_context.total_limit_usd).toFixed(2)} limit`)
    postureChips.push(`${finopsPosture.billing_context.open_periods} open periods`)
    postureChips.push(`${finopsPosture.chargeback_context.active_rules} CB rules`)
    postureChips.push(`${finopsPosture.override_context.active_overrides} overrides`)
    postureChips.push(`${finopsPosture.notification_context.total_notifications} notifications`)
  }
  if (budgetScopePosture) {
    postureChips.push(`${budgetScopePosture.identity_context.workspace_users} users`)
    postureChips.push(`${budgetScopePosture.runtime_context.routes} routes`)
    postureChips.push(`${budgetScopePosture.governance_context.alert_rules} alert rules`)
  }

  return (
    <div className="space-y-5">
      {/* ── Hero ── */}
      <section className="relative isolate overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 px-6 py-8 text-white shadow-lg">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(99,102,241,0.15),transparent_60%)]" />
        <div className="relative">
          <div className="flex items-center gap-2">
            <Wallet className="h-6 w-6 text-blue-400" />
            <h1 className="text-2xl font-bold tracking-tight">Budgets</h1>
          </div>
          <p className="mt-1.5 max-w-xl text-[11px] leading-relaxed text-slate-300">
            Manage spend policy as one control plane: budgets own the rules, overrides stay inside the rule lifecycle, and notifications turn breaches into action.
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
            { label: 'Budget Tiers', value: String(tiers.items.length) },
            { label: 'Total Budgets', value: String(budgets.items.length) },
            { label: 'Current Spend', value: rollup ? `$${num(Number.parseFloat(rollup.current_spend_usd)).toFixed(2)}` : '$0' },
            { label: 'Notifications', value: String(notifications.items.length) },
            { label: 'Overrides', value: finopsPosture ? String(finopsPosture.override_context.total_overrides) : '0' },
            { label: 'Ledger Snaps', value: finopsPosture ? String(finopsPosture.ledger_context.total_snapshots) : '0' },
          ].map((kpi) => (
            <div key={kpi.label} className="rounded-lg bg-white/5 px-3 py-2 ring-1 ring-white/10">
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">{kpi.label}</p>
              <p className="mt-0.5 truncate text-sm font-bold">{kpi.value}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Quick reference cards */}
      <div className="grid gap-3 md:grid-cols-3">
        <Link
          href="/gateway#gateway-quota-tiers"
          className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/40 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-800 dark:hover:bg-blue-950/20"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Budget Tiers</p>
          <p className="mt-1.5 text-xl font-bold text-slate-900 dark:text-white">{tiers.items.length}</p>
          <p className="mt-1.5 text-[11px] text-slate-500">Shared quota presets in Gateway where runtime controls belong.</p>
        </Link>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Overrides</p>
          <p className="mt-1.5 text-xl font-bold text-slate-900 dark:text-white">Embedded</p>
          <p className="mt-1.5 text-[11px] text-slate-500">Temporary exceptions live inside Budgets, not on a separate island.</p>
        </div>
        <Link
          href="/gateway#gateway-model-quotas"
          className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/40 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-800 dark:hover:bg-blue-950/20"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Model Budgets</p>
          <p className="mt-1.5 text-xl font-bold text-slate-900 dark:text-white">Gateway</p>
          <p className="mt-1.5 text-[11px] text-slate-500">Per-key model quotas remain owned by Gateway for runtime coherence.</p>
        </Link>
      </div>

      {/* ── Context panels ── */}
      {finopsPosture && (
        <div className="rounded-xl border border-blue-200/50 bg-gradient-to-r from-blue-50/60 to-indigo-50/60 p-4 dark:border-blue-800/30 dark:from-blue-950/30 dark:to-indigo-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <h2 className="text-xs font-bold text-blue-900 dark:text-blue-200">FinOps Internal Posture</h2>
            <span className="ml-auto text-[10px] text-blue-500 dark:text-blue-400">{finopsPosture.period_days}d window</span>
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6">
            {[
              { label: 'Budgets', value: `${finopsPosture.budget_context.active_budgets}/${finopsPosture.budget_context.total_budgets}` },
              { label: 'Billing Periods', value: `${finopsPosture.billing_context.open_periods}/${finopsPosture.billing_context.total_periods}` },
              { label: 'CB Rules', value: `${finopsPosture.chargeback_context.active_rules}/${finopsPosture.chargeback_context.total_rules}` },
              { label: 'Ledger Snaps', value: String(finopsPosture.ledger_context.total_snapshots) },
              { label: 'Overrides', value: `${finopsPosture.override_context.active_overrides}/${finopsPosture.override_context.total_overrides}` },
              { label: '30d Spend', value: `$${num(finopsPosture.notification_context.spend_30d).toFixed(2)}` },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg bg-white/80 p-2.5 dark:bg-slate-800/60">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">{label}</p>
                <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-white">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {budgetScopePosture && (
        <div className="rounded-xl border border-indigo-200/50 bg-gradient-to-r from-indigo-50/60 to-violet-50/60 p-4 dark:border-indigo-800/30 dark:from-indigo-950/30 dark:to-violet-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-xs font-bold text-indigo-900 dark:text-indigo-200">Budget Scope & Governance Context</h2>
            <span className="ml-auto text-[10px] text-indigo-500 dark:text-indigo-400">{budgetScopePosture.period_days}d window</span>
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {[
              { label: 'Identity', value: `${budgetScopePosture.identity_context.workspace_users} users · ${budgetScopePosture.identity_context.api_keys} keys` },
              { label: 'Runtime', value: `${budgetScopePosture.runtime_context.routes} routes · ${budgetScopePosture.runtime_context.active_providers_30d} providers` },
              { label: 'Governance', value: `${budgetScopePosture.governance_context.alert_rules} alerts · ${budgetScopePosture.governance_context.tags} tags` },
              { label: 'Spend', value: `$${num(budgetScopePosture.spend_context.total_spend_30d).toFixed(2)}` },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg bg-white/80 p-2.5 dark:bg-slate-800/60">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">{label}</p>
                <p className="mt-0.5 text-xs font-bold text-slate-900 dark:text-white">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Budget Manager client component */}
      <BudgetManager
        initialItems={budgets.items}
        notifications={notifications.items}
        rollup={rollup}
        apiKey={session.apiKey}
        initialTab={initialTab}
        initialScopeType={initialScopeType}
        initialScopeId={requestedScopeId}
        autoOpenCreate={requestedCreate === '1'}
      />

      {/* ── Quick-nav footer ── */}
      <div className="flex flex-wrap gap-2 pt-2">
        {[
          { label: 'Cost & Savings', href: '/cost-savings' },
          { label: 'Billing', href: '/billing' },
          { label: 'Chargeback', href: '/chargeback' },
          { label: 'Gateway Tiers', href: '/gateway#gateway-quota-tiers' },
          { label: 'Model Quotas', href: '/gateway#gateway-model-quotas' },
          { label: 'Alert Rules', href: '/alert-rules' },
          { label: 'Tags', href: '/tags' },
          { label: 'Audit Log', href: '/audit' },
        ].map(({ label, href }) => (
          <Link
            key={label}
            href={href}
            className="rounded-full border border-blue-200 bg-blue-50/80 px-3 py-1 text-[11px] font-semibold text-blue-700 transition hover:bg-blue-100 dark:border-blue-800/50 dark:bg-blue-950/30 dark:text-blue-300 dark:hover:bg-blue-900/40"
          >
            {label}
          </Link>
        ))}
      </div>
    </div>
  )
}
