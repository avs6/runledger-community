import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
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

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Budgets</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Manage spend policy as one control plane: budgets own the rules, overrides stay inside
          the rule lifecycle, and notifications turn breaches into action.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Link
          href="/gateway#gateway-quota-tiers"
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/40 dark:border-slate-800 dark:bg-slate-950"
        >
          <p className="text-xs uppercase tracking-wide text-slate-500">Budget Tiers</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
            {tiers.items.length}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Shared quota presets stay collapsed into Gateway where runtime controls belong.
          </p>
        </Link>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <p className="text-xs uppercase tracking-wide text-slate-500">Overrides</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">Embedded</p>
          <p className="mt-2 text-sm text-slate-500">
            Temporary exceptions now live inside Budgets instead of on a separate product island.
          </p>
        </div>
        <Link
          href="/gateway#gateway-model-quotas"
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/40 dark:border-slate-800 dark:bg-slate-950"
        >
          <p className="text-xs uppercase tracking-wide text-slate-500">Model Budgets</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">Gateway</p>
          <p className="mt-2 text-sm text-slate-500">
            Per-key model quotas remain owned by Gateway so runtime ownership stays coherent.
          </p>
        </Link>
      </div>

      {finopsPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 dark:border-emerald-900 dark:bg-emerald-950/40">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">FinOps Internal Posture</h2>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">{finopsPosture.period_days}d window</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Budgets</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.budget_context.total_budgets}</p>
              <p className="text-xs text-slate-400">{finopsPosture.budget_context.active_budgets} active · ${finopsPosture.budget_context.total_limit_usd.toFixed(2)} limit</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Billing Periods</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.billing_context.total_periods}</p>
              <p className="text-xs text-slate-400">{finopsPosture.billing_context.open_periods} open · ${finopsPosture.billing_context.total_billed_usd.toFixed(2)} billed</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Chargeback Rules</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.chargeback_context.total_rules}</p>
              <p className="text-xs text-slate-400">{finopsPosture.chargeback_context.active_rules} active</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Ledger Snapshots</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.ledger_context.total_snapshots}</p>
              <p className="text-xs text-slate-400">latest: {finopsPosture.ledger_context.latest_snapshot_date}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Overrides</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.override_context.total_overrides}</p>
              <p className="text-xs text-slate-400">{finopsPosture.override_context.active_overrides} active</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Notifications</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.notification_context.total_notifications}</p>
              <p className="text-xs text-slate-400">${finopsPosture.notification_context.spend_30d.toFixed(2)} 30d spend</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/billing" className="text-emerald-700 hover:underline dark:text-emerald-400">Billing →</Link>
            <Link href="/chargeback" className="text-emerald-700 hover:underline dark:text-emerald-400">Chargeback →</Link>
            <Link href="/settings?tab=compliance" className="text-emerald-700 hover:underline dark:text-emerald-400">Ledger →</Link>
          </div>
        </div>
      )}

      {budgetScopePosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Budget Scope & Governance Context</h2>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">{budgetScopePosture.period_days}d window</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Identity Scope</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{budgetScopePosture.identity_context.workspace_users} users</p>
              <p className="text-xs text-slate-400">{budgetScopePosture.identity_context.api_keys} keys · {budgetScopePosture.identity_context.access_groups} groups</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Runtime</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{budgetScopePosture.runtime_context.routes} routes</p>
              <p className="text-xs text-slate-400">{budgetScopePosture.runtime_context.active_providers_30d} providers · {budgetScopePosture.runtime_context.cache_configs} caches</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Governance</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{budgetScopePosture.governance_context.alert_rules} alert rules</p>
              <p className="text-xs text-slate-400">{budgetScopePosture.governance_context.audit_events_30d} audit events · {budgetScopePosture.governance_context.tags} tags</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Spend</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">${budgetScopePosture.spend_context.total_spend_30d.toFixed(2)}</p>
              <p className="text-xs text-slate-400">{budgetScopePosture.identity_context.hub_models} hub models</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/analytics/users" className="text-emerald-600 hover:underline dark:text-emerald-400">Users →</Link>
            <Link href="/api-keys" className="text-emerald-600 hover:underline dark:text-emerald-400">API Keys →</Link>
            <Link href="/access-groups" className="text-emerald-600 hover:underline dark:text-emerald-400">Access Groups →</Link>
            <Link href="/ai-hub" className="text-emerald-600 hover:underline dark:text-emerald-400">AI Hub →</Link>
            <Link href="/gateway" className="text-emerald-600 hover:underline dark:text-emerald-400">Gateway →</Link>
            <Link href="/alerts" className="text-emerald-600 hover:underline dark:text-emerald-400">Alert Rules →</Link>
            <Link href="/audit" className="text-emerald-600 hover:underline dark:text-emerald-400">Audit Log →</Link>
            <Link href="/tags" className="text-emerald-600 hover:underline dark:text-emerald-400">Tags →</Link>
          </div>
        </div>
      )}

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
    </div>
  )
}
