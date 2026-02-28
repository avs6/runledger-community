'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { Plus } from 'lucide-react'
import { toast } from 'sonner'
import type { BillingPeriod } from '@/types/api'
import { getBillingPeriods } from '@/lib/api'
import BillingPeriodTable from '@/components/billing/BillingPeriodTable'
import CreatePeriodModal from '@/components/billing/CreatePeriodModal'

export default function BillingPage() {
  const { data: session } = useSession()
  const [periods, setPeriods] = useState<BillingPeriod[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)

  const load = useCallback(async () => {
    if (!session?.apiKey) return
    setLoading(true)
    try {
      const data = await getBillingPeriods(session.apiKey)
      setPeriods(data.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load billing periods')
    } finally {
      setLoading(false)
    }
  }, [session?.apiKey])

  useEffect(() => {
    load()
  }, [load])

  function handleCreated(period: BillingPeriod) {
    setPeriods((prev) => [period, ...prev])
    toast.success('Billing period created')
  }

  function handleClosed(id: string) {
    setPeriods((prev) =>
      prev.map((p) => (p.id === id ? { ...p, status: 'closed' as const } : p))
    )
    toast.success('Period closed and signed')
    // Reload to get updated total_cost_usd + snapshot_hash
    load()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Billing</h1>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          New Period
        </button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : (
        <BillingPeriodTable
          items={periods}
          apiKey={session?.apiKey ?? ''}
          onClosed={handleClosed}
        />
      )}

      {showModal && session?.apiKey && (
        <CreatePeriodModal
          apiKey={session.apiKey}
          onCreated={handleCreated}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
