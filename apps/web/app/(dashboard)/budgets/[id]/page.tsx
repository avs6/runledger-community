import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getBudgetBreaches } from '@/lib/api'
import BreachHistoryTable from '@/components/budgets/BreachHistoryTable'

interface PageProps {
  params: { id: string }
}

export default async function BudgetBreachesPage({ params }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return notFound()

  const data = await getBudgetBreaches(session.apiKey, params.id)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link
          href="/budgets"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ChevronLeft className="h-4 w-4" />
          Budgets
        </Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-semibold">Breach History</h1>
      </div>

      <p className="text-sm text-gray-500">
        Budget <span className="font-mono text-xs text-gray-700">{params.id}</span>
      </p>

      <BreachHistoryTable items={data.items} />
    </div>
  )
}
