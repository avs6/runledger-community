import Link from 'next/link'
import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import { ChevronLeft } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getUserFinance, getUserGovernance } from '@/lib/api'

function money(value: string | null | undefined) {
  if (!value) return '$0.00'
  return `$${Number.parseFloat(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

export default async function UserDetailPage({
  params,
}: {
  params: { user_id: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let finance
  try {
    finance = await getUserFinance(session.apiKey, params.user_id)
  } catch {
    notFound()
  }

  let governance
  try {
    governance = await getUserGovernance(session.apiKey, params.user_id)
  } catch {
    governance = null
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Link
          href="/users"
          className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
        >
          <ChevronLeft className="h-4 w-4" />
          Users
        </Link>
      </div>

      <div>
        <h1 className="text-2xl font-semibold text-slate-950 dark:text-slate-100">
          {finance.full_name || finance.email}
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {finance.email} &middot; {finance.user_id}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <p className="text-xs uppercase tracking-wide text-slate-500">30d Spend</p>
          <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-100">
            {money(finance.spend_30d_usd)}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <p className="text-xs uppercase tracking-wide text-slate-500">Total Spend</p>
          <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-100">
            {money(finance.spend_total_usd)}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <p className="text-xs uppercase tracking-wide text-slate-500">30d Runs</p>
          <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-100">
            {finance.run_count_30d.toLocaleString()}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <p className="text-xs uppercase tracking-wide text-slate-500">30d Calls</p>
          <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-100">
            {finance.call_count_30d.toLocaleString()}
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <p className="text-xs uppercase tracking-wide text-slate-500">Budget Exposure</p>
        {finance.budgets.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-slate-600 dark:text-slate-400">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">Period</th>
                  <th className="text-right p-2">Limit (USD)</th>
                  <th className="text-left p-2">Action</th>
                  <th className="text-left p-2">Status</th>
                  <th className="p-2"></th>
                </tr>
              </thead>
              <tbody>
                {finance.budgets.map((b) => (
                  <tr key={b.budget_id} className="border-t">
                    <td className="p-2">{b.period_type}</td>
                    <td className="text-right p-2">{money(b.limit_usd)}</td>
                    <td className="p-2">{b.scope_type}</td>
                    <td className="p-2">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          b.is_active
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                            : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                        }`}
                      >
                        {b.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="p-2">
                      <Link
                        href={`/budgets/${b.budget_id}`}
                        className="text-xs text-blue-600 hover:underline dark:text-blue-300"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
            No budgets scoped to this user.
          </p>
        )}
      </div>

      {governance && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <p className="text-xs uppercase tracking-wide text-slate-500">Governance Footprint</p>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-2xl font-semibold text-slate-950 dark:text-slate-100">{governance.approval_count}</p>
              <p className="text-xs text-slate-500">Approvals</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-slate-950 dark:text-slate-100">{governance.audit_event_count}</p>
              <p className="text-xs text-slate-500">Audit Events</p>
            </div>
          </div>
          {governance.recent_approvals.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Recent Approvals</p>
              <div className="mt-2 space-y-1">
                {governance.recent_approvals.map((a) => (
                  <Link
                    key={a.id}
                    href={`/approvals?status=${a.status}`}
                    className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"
                  >
                    <span className="text-slate-700 dark:text-slate-300">{a.request_type}</span>
                    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                      a.status === 'approved' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' :
                      a.status === 'denied' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' :
                      'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
                    }`}>{a.status}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}
          {governance.recent_audit_events.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Recent Audit Events</p>
              <div className="mt-2 space-y-1">
                {governance.recent_audit_events.map((e) => (
                  <div
                    key={e.id}
                    className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-sm dark:border-slate-800"
                  >
                    <span className="text-slate-700 dark:text-slate-300">{e.action}</span>
                    <span className="text-xs text-slate-500">{new Date(e.created_at).toLocaleDateString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <Link
          href={`/runs?end_user_id=${finance.user_id}`}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          View Runs
        </Link>
        <Link
          href={`/analytics?scope=workspace&end_user_id=${finance.user_id}`}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Analytics
        </Link>
        <Link
          href={`/chargeback?dimension=end_user&end_user_id=${finance.user_id}`}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Chargeback
        </Link>
        <Link
          href={`/approvals?requested_by=${encodeURIComponent(finance.email)}`}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Approvals
        </Link>
        <Link
          href={`/audit?actor_user_id=${finance.user_id}`}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Audit Log
        </Link>
        <Link
          href={`/governance?user_id=${finance.user_id}`}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Governance Pack
        </Link>
      </div>
    </div>
  )
}
