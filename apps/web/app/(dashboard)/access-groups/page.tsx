import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getAccessGroups } from '@/lib/api'

function budgetLabel(budget: number | null, period: string | null) {
  if (budget == null) return 'No budget'
  return `$${budget.toFixed(2)}${period ? ` / ${period}` : ''}`
}

export default async function AccessGroupsPage() {
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) return <p className="p-8 text-slate-500">Sign in to view access groups.</p>

  try {
    const [groups, dashboard] = await Promise.all([
      getAccessGroups(apiKey),
      getAccessGroupDashboard(apiKey),
    ])

    return (
      <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Access Groups
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Group-based permissions with dashboard filtering profiles and budget envelopes.
            </p>
          </div>
          <span className="text-sm text-slate-500">{groups.total} configured groups</span>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Active Groups</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
              {groups.items.filter((group) => group.is_active).length}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Members</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
              {groups.items.reduce((sum, group) => sum + group.member_count, 0)}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Filter Profiles</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
              {dashboard.groups.filter((group) => Object.keys(group.dashboard_filters).length > 0).length}
            </p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {dashboard.groups.map((group) => (
            <div key={group.id} className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">{group.name}</h2>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold uppercase text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {group.is_active ? 'active' : 'inactive'}
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-500">{group.member_count} member{group.member_count !== 1 ? 's' : ''}</p>
              <p className="mt-1 text-sm text-slate-500">{budgetLabel(group.budget_usd, group.budget_period)}</p>
              <p className="mt-1 text-sm text-slate-500">Guardrails: {group.guardrail_profile || 'default'}</p>
              <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-800/70 dark:text-slate-300">
                <p className="font-semibold text-slate-700 dark:text-slate-200">Dashboard filters</p>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(group.dashboard_filters, null, 2)}
                </pre>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  } catch {
    return <p className="p-8 text-slate-500">Failed to load access groups.</p>
  }
}
