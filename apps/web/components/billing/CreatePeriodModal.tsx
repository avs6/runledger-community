'use client'

import { useState } from 'react'
import type { BillingPeriod } from '@/types/api'
import { createBillingPeriod } from '@/lib/api'
import { X } from 'lucide-react'

function lastDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

function defaultDates() {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1 // 1-indexed
  const start = `${year}-${String(month).padStart(2, '0')}-01`
  const end = `${year}-${String(month).padStart(2, '0')}-${lastDayOfMonth(year, month)}`
  return { start, end }
}

interface Props {
  apiKey: string
  onCreated: (period: BillingPeriod) => void
  onClose: () => void
}

export default function CreatePeriodModal({ apiKey, onCreated, onClose }: Props) {
  const { start: defaultStart, end: defaultEnd } = defaultDates()
  const [periodStart, setPeriodStart] = useState(defaultStart)
  const [periodEnd, setPeriodEnd] = useState(defaultEnd)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const period = await createBillingPeriod(apiKey, {
        period_start: periodStart,
        period_end: periodEnd,
      })
      onCreated(period)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create period')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">New Billing Period</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Period Start</label>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              required
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Period End</label>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              required
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
