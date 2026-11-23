import { redirect } from 'next/navigation'

/** Model budgets are budgets with scope_type=model (review G-01). */
export default function ModelBudgetsPage() {
  redirect('/budgets?scope_type=model')
}
