'use client'

import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { Budget } from '@/types/api'
import BudgetList from './BudgetList'
import CreateBudgetModal from './CreateBudgetModal'

interface Props {
  initialItems: Budget[]
  apiKey: string
}

export default function BudgetManager({ initialItems, apiKey }: Props) {
  const [items, setItems] = useState(initialItems)
  const [showCreate, setShowCreate] = useState(false)

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" /> New Budget
        </button>
      </div>

      <BudgetList
        items={items}
        apiKey={apiKey}
        onDeleted={(id) => setItems((prev) => prev.filter((item) => item.id !== id))}
      />

      {showCreate && (
        <CreateBudgetModal
          apiKey={apiKey}
          onClose={() => setShowCreate(false)}
          onCreated={(budget) => setItems((prev) => [budget, ...prev])}
        />
      )}
    </div>
  )
}
