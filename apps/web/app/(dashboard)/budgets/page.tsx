import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'
import { getBudgets } from '@/lib/api'
import BudgetList from '@/components/budgets/BudgetList'

export default async function BudgetsPage() {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  const budgets = await getBudgets(session.apiKey)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Budgets</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage spend limits and guardrails for your workspaces.
        </p>
      </div>

      {budgets.items.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center dark:border-gray-800 dark:bg-gray-900">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No budgets configured yet. Create one via the API.
          </p>
        </div>
      ) : (
        <BudgetList items={budgets.items} apiKey={session.apiKey} onDeleted={() => {}} />
      )}
    </div>
  )
}
