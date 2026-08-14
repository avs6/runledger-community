'use client'

import { useState } from 'react'
import { X } from 'lucide-react'
import type { BillingPeriod } from '@/types/api'
import { createBillingPeriod } from '@/lib/api'

function lastDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

function defaultDates() {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-950 dark:text-white">New Billing Period</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block text-sm">
            <span className="font-medium text-slate-700 dark:text-slate-300">Period Start</span>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              required
              className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium text-slate-700 dark:text-slate-300">Period End</span>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              required
              className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            />
          </label>

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
