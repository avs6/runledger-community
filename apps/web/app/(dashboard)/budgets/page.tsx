'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { Plus } from 'lucide-react'
import type { Budget } from '@/types/api'
import { getBudgets } from '@/lib/api'
import BudgetList from '@/components/budgets/BudgetList'
import CreateBudgetModal from '@/components/budgets/CreateBudgetModal'

export default function BudgetsPage() {
  const { data: session } = useSession()
  const [budgets, setBudgets] = useState<Budget[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)

  const load = useCallback(async () => {
    if (!session?.apiKey) return
    setLoading(true)
    try {
      const data = await getBudgets(session.apiKey)
      setBudgets(data.items)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [session?.apiKey])

  useEffect(() => {
    load()
  }, [load])

  function handleCreated(budget: Budget) {
    setBudgets((prev) => [budget, ...prev])
  }

  function handleDeleted(id: string) {
    setBudgets((prev) => prev.filter((b) => b.id !== id))
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Budgets</h1>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          New Budget
        </button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : (
        <BudgetList
          items={budgets}
          apiKey={session?.apiKey ?? ''}
          onDeleted={handleDeleted}
        />
      )}

      {showModal && session?.apiKey && (
        <CreateBudgetModal
          apiKey={session.apiKey}
          onCreated={handleCreated}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
