import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'
import { getBillingPeriods, getBillingSummary } from '@/lib/api'
import BillingWorkspaceClient from '@/components/billing/BillingWorkspaceClient'

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

  const [periods, summary] = await Promise.all([
    getBillingPeriods(session.apiKey, { access_group_id: accessGroupId }),
    getBillingSummary(session.apiKey, summaryMonths).catch(() => ({ workspace_id: '', periods: [] })),
  ])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Billing</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Operate billing periods, review reconciliation quality, manage shared-cost policies, and export finance-ready evidence in one place.
        </p>
      </div>

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
