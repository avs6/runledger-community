import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'
import { getBudgets } from '@/lib/api'
import BudgetManager from '@/components/budgets/BudgetManager'

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

      <BudgetManager initialItems={budgets.items} apiKey={session.apiKey} />
    </div>
  )
}
