import { redirect } from 'next/navigation'

export default function BudgetOverridesCompatibilityPage() {
  redirect('/budgets?tab=overrides')
}
