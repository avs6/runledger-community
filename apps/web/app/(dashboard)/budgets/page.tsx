import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getBudgets, listBudgetTiers } from '@/lib/api'
import BudgetManager from '@/components/budgets/BudgetManager'

export default async function BudgetsPage() {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  const [budgets, tiers] = await Promise.all([
    getBudgets(session.apiKey),
    listBudgetTiers(session.apiKey).catch(() => ({ items: [] })),
  ])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Budgets</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage spend limits, tiers, overrides, and model-level guardrails from one place.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/budget-tiers" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/40 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Budget Tiers</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{tiers.items.length}</p>
          <p className="mt-2 text-sm text-slate-500">Shared policy presets for spend, RPM, TPM, and allowed model sets.</p>
        </Link>
        <Link href="/budget-overrides" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/40 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Overrides</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">Temporary</p>
          <p className="mt-2 text-sm text-slate-500">Review short-lived budget exceptions without leaving the spend-control workflow.</p>
        </Link>
        <Link href="/model-budgets" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/40 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Model Budgets</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">Per Key</p>
          <p className="mt-2 text-sm text-slate-500">Pin tighter limits to expensive models or wildcard model families for sensitive keys.</p>
        </Link>
      </div>

      <BudgetManager initialItems={budgets.items} apiKey={session.apiKey} />
    </div>
  )
}
