import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'
import {
  getBudgetRollup,
  getBudgets,
  listBudgetNotifications,
  listBudgetTiers,
} from '@/lib/api'
import BudgetManager from '@/components/budgets/BudgetManager'

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

  const [budgets, tiers, notifications, rollup] = await Promise.all([
    getBudgets(session.apiKey),
    listBudgetTiers(session.apiKey).catch(() => ({ items: [] })),
    listBudgetNotifications(session.apiKey).catch(() => ({ items: [] })),
    getBudgetRollup(session.apiKey).catch(() => null),
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
