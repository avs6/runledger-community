'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import type { BillingPeriod } from '@/types/api'
import { closeBillingPeriod, exportPeriodCsv, exportPeriodSignedJson } from '@/lib/api'

interface Props {
  items: BillingPeriod[]
  apiKey: string
  onClosed?: (id: string) => void
}

function StatusBadge({ status }: { status: BillingPeriod['status'] }) {
  const cls =
    status === 'open'
      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
      : status === 'closing'
        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
        : 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{status}</span>
}

function downloadBlob(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function money(value: string | null) {
  if (value == null) return '--'
  return `$${Number.parseFloat(value).toFixed(4)}`
}

export default function BillingPeriodTable({ items, apiKey, onClosed }: Props) {
  const [loading, setLoading] = useState<string | null>(null)
  const router = useRouter()

  async function handleClose(id: string) {
    setLoading(`close-${id}`)
    try {
      await closeBillingPeriod(apiKey, id)
      onClosed?.(id)
      router.refresh()
      toast.success('Billing period closed')
    } catch (err) {
      console.error(err)
      toast.error('Failed to close billing period')
    } finally {
      setLoading(null)
    }
  }

  async function handleExportCsv(id: string) {
    setLoading(`csv-${id}`)
    try {
      const csv = await exportPeriodCsv(apiKey, id)
      downloadBlob(csv, `period_${id}.csv`, 'text/csv')
    } catch (err) {
      console.error(err)
      toast.error('Failed to export CSV')
    } finally {
      setLoading(null)
    }
  }

  async function handleExportJson(id: string) {
    setLoading(`json-${id}`)
    try {
      const data = await exportPeriodSignedJson(apiKey, id)
      downloadBlob(JSON.stringify(data, null, 2), `period_${id}.json`, 'application/json')
    } catch (err) {
      console.error(err)
      toast.error('Failed to export signed JSON')
    } finally {
      setLoading(null)
    }
  }

  if (items.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-gray-200 py-10 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
        No billing periods yet. Create one to get started.
      </p>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
      <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Period</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Status</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Gross</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Net</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white dark:divide-gray-700 dark:bg-gray-800">
          {items.map((period) => (
            <tr key={period.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
              <td className="px-4 py-3">
                <Link
                  href={`/billing/${period.id}`}
                  className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  {period.period_start} - {period.period_end}
                </Link>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {period.currency}
                  {period.closed_at ? ` · Closed ${new Date(period.closed_at).toLocaleString()}` : ' · Open period'}
                </div>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={period.status} />
              </td>
              <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-gray-300">
                {money(period.total_cost_usd)}
              </td>
              <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-gray-300">
                {money(period.net_cost_usd)}
              </td>
              <td className="px-4 py-3">
                <div className="flex justify-end gap-2">
                  {period.status !== 'closed' ? (
                    <button
                      onClick={() => handleClose(period.id)}
                      disabled={loading === `close-${period.id}`}
                      className="rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {loading === `close-${period.id}` ? 'Closing...' : 'Close'}
                    </button>
                  ) : null}
                  <button
                    onClick={() => handleExportCsv(period.id)}
                    disabled={loading === `csv-${period.id}`}
                    className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                  >
                    CSV
                  </button>
                  <button
                    onClick={() => handleExportJson(period.id)}
                    disabled={loading === `json-${period.id}`}
                    className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                  >
                    Signed JSON
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
