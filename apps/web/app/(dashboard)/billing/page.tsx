import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'
import { getBillingPeriods } from '@/lib/api'
import BillingPeriodTable from '@/components/billing/BillingPeriodTable'

export default async function BillingPage() {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  const periods = await getBillingPeriods(session.apiKey)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Billing Periods</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          View and manage billing periods for your workspace.
        </p>
      </div>

      <BillingPeriodTable items={periods.items} apiKey={session.apiKey} onClosed={() => {}} />
    </div>
  )
}
