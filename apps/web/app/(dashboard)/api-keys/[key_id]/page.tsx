import Link from 'next/link'
import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import { ChevronLeft } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import {
  getApiKeyDetail,
  getBudgets,
  getBillingPeriods,
  getChargebackReport,
} from '@/lib/api'

function money(value: string | null | undefined) {
  if (!value) return '$0.00'
  return `$${Number.parseFloat(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function monthLabel() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export default async function ApiKeyDetailPage({
  params,
}: {
  params: { key_id: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let apiKeyDetail
  try {
    apiKeyDetail = await getApiKeyDetail(session.apiKey, params.key_id)
  } catch {
    notFound()
  }

  const currentPeriod = monthLabel()
  const [budgetResult, billingPeriodsResult, chargebackResult] = await Promise.allSettled([
    getBudgets(session.apiKey, {
      scope_type: 'api_key',
      scope_id: params.key_id,
      include_inactive: true,
    }),
    getBillingPeriods(session.apiKey, { api_key_id: params.key_id }),
    getChargebackReport(session.apiKey, {
      period: currentPeriod,
      dimension: 'api_key',
      api_key_id: params.key_id,
    }),
  ])

  const budgets = budgetResult.status === 'fulfilled' ? budgetResult.value.items : []
  const billingPeriods = billingPeriodsResult.status === 'fulfilled' ? billingPeriodsResult.value.items : []
  const chargeback = chargebackResult.status === 'fulfilled' ? chargebackResult.value.items[0] ?? null : null
  const chargebackItem = chargeback?.breakdown[0] ?? null
  const activeBudgets = budgets.filter((budget) => budget.is_active)

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center gap-2">
        <Link
          href="/api-keys"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
        >
          <ChevronLeft className="h-4 w-4" />
          API Keys
        </Link>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
            {apiKeyDetail.name ?? apiKeyDetail.key_prefix}
          </h1>
          <p className="mt-1 font-mono text-xs text-slate-500 dark:text-slate-400">
            {apiKeyDetail.key_prefix}… · {apiKeyDetail.id}
          </p>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            {apiKeyDetail.workspace_name ?? 'Workspace'} · {apiKeyDetail.ownership_type}
            {apiKeyDetail.owner_reference ? ` · ${apiKeyDetail.owner_reference}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/budgets?tab=policies&scope_type=api_key&scope_id=${encodeURIComponent(params.key_id)}`}
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Open budgets
          </Link>
          <Link
            href={`/chargeback?dimension=api_key&api_key_id=${encodeURIComponent(params.key_id)}`}
            className="rounded-xl bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            Open chargeback
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">This month spend</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
            {money(chargebackItem?.cost_usd)}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Active budgets</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{activeBudgets.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Budgeted coverage</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
            {chargeback ? money(chargeback.covered_cost_usd) : '$0.00'}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Billing periods</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{billingPeriods.length}</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Budget assignment</h2>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                API-key scoped budgets and their live spend posture.
              </p>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="pb-2">Period</th>
                  <th className="pb-2">Limit</th>
                  <th className="pb-2">Spend</th>
                  <th className="pb-2">Action</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {budgets.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-4 text-slate-500">
                      No budgets are assigned to this API key yet.
                    </td>
                  </tr>
                ) : (
                  budgets.map((budget) => (
                    <tr key={budget.id}>
                      <td className="py-3">{budget.period_type}</td>
                      <td className="py-3">{money(budget.limit_usd)}</td>
                      <td className="py-3">{money(budget.current_spend_usd)}</td>
                      <td className="py-3">{budget.action}</td>
                      <td className="py-3">
                        <Link
                          href={`/budgets/${budget.id}`}
                          className="text-indigo-600 hover:underline dark:text-indigo-300"
                        >
                          {budget.is_active ? 'Active' : 'Inactive'}
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
            Budget overrides stay attached to these API-key-scoped budget policies and can be reviewed from each budget detail page.
          </p>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Spend attribution</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Current-period chargeback and closed/open billing evidence for this API key.
          </p>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Chargeback period</dt>
              <dd className="font-medium text-slate-900 dark:text-white">{chargeback?.period ?? currentPeriod}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Allocated cost</dt>
              <dd className="font-medium text-slate-900 dark:text-white">{money(chargebackItem?.cost_usd)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Budget variance</dt>
              <dd className="font-medium text-slate-900 dark:text-white">{money(chargebackItem?.variance_usd)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Provider calls</dt>
              <dd className="font-medium text-slate-900 dark:text-white">{chargebackItem?.call_count ?? 0}</dd>
            </div>
          </dl>

          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Billing periods</h3>
            <div className="mt-3 space-y-2">
              {billingPeriods.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  No billing periods have attributed traffic for this API key yet.
                </p>
              ) : (
                billingPeriods.slice(0, 6).map((period) => (
                  <Link
                    key={period.id}
                    href={`/billing/${period.id}?api_key_id=${encodeURIComponent(params.key_id)}`}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800"
                  >
                    <span>{period.period_start} - {period.period_end}</span>
                    <span className="font-medium text-slate-900 dark:text-white">{money(period.net_cost_usd)}</span>
                  </Link>
                ))
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
