import { getServerSession } from 'next-auth'
import { notFound, redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'
import { getBudget, getBudgetBreaches, listBudgetOverrides } from '@/lib/api'
import BudgetDetailClient from '@/components/budgets/BudgetDetailClient'

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function BudgetDetailPage({ params }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  const { id } = await params

  try {
    const [budget, breaches, overrides] = await Promise.all([
      getBudget(session.apiKey, id),
      getBudgetBreaches(session.apiKey, id),
      listBudgetOverrides(session.apiKey, id).catch(() => ({ items: [] })),
    ])

    return (
      <BudgetDetailClient
        apiKey={session.apiKey}
        initialBudget={budget}
        initialBreaches={breaches.items}
        initialOverrides={overrides.items}
      />
    )
  } catch {
    return notFound()
  }
}
