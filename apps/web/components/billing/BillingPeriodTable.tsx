'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import type { BillingPeriod } from '@/types/api'
import { closeBillingPeriod, exportPeriodCsv, exportPeriodSignedJson, exportPeriodQuickbooks, exportPeriodNetsuite } from '@/lib/api'

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
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {status}
    </span>
  )
}

function downloadBlob(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
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
    } catch (err) {
      console.error(err)
      toast.error('Failed to close period')
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
      toast.error('Failed to export JSON')
    } finally {
      setLoading(null)
    }
  }

  async function handleExportQb(id: string) {
    setLoading(`qb-${id}`)
    try {
      const csv = await exportPeriodQuickbooks(apiKey, id)
      downloadBlob(csv, `period_${id}_quickbooks.csv`, 'text/csv')
    } catch (err) {
      console.error(err)
      toast.error('Failed to export QuickBooks CSV')
    } finally {
      setLoading(null)
    }
  }

  async function handleExportNetsuite(id: string) {
    setLoading(`ns-${id}`)
    try {
      const csv = await exportPeriodNetsuite(apiKey, id)
      downloadBlob(csv, `period_${id}_netsuite.csv`, 'text/csv')
    } catch (err) {
      console.error(err)
      toast.error('Failed to export NetSuite CSV')
    } finally {
      setLoading(null)
    }
  }

  if (items.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-gray-200 dark:border-gray-700 py-10 text-center text-sm text-gray-500 dark:text-gray-400">
        No billing periods yet. Create one to get started.
      </p>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Period</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Status</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Total Cost</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-800">
          {items.map((p) => (
            <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
              <td className="px-4 py-3">
                <Link
                  href={`/billing/${p.id}`}
                  className="font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
                >
                  {p.period_start} — {p.period_end}
                </Link>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={p.status} />
              </td>
              <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-gray-300">
                {p.total_cost_usd != null ? `$${parseFloat(p.total_cost_usd).toFixed(4)}` : '—'}
              </td>
              <td className="px-4 py-3">
                <div className="flex justify-end gap-2">
                  {p.status !== 'closed' && (
                    <button
                      onClick={() => handleClose(p.id)}
                      disabled={loading === `close-${p.id}`}
                      className="rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {loading === `close-${p.id}` ? 'Closing…' : 'Close'}
                    </button>
                  )}
                  <button
                    onClick={() => handleExportCsv(p.id)}
                    disabled={loading === `csv-${p.id}`}
                    className="rounded border border-gray-300 dark:border-gray-600 px-2 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                  >
                    CSV
                  </button>
                  <button
                    onClick={() => handleExportJson(p.id)}
                    disabled={loading === `json-${p.id}`}
                    className="rounded border border-gray-300 dark:border-gray-600 px-2 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                  >
                    JSON
                  </button>
                  <button
                    onClick={() => handleExportQb(p.id)}
                    disabled={loading === `qb-${p.id}`}
                    className="rounded border border-gray-300 dark:border-gray-600 px-2 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                  >
                    QB
                  </button>
                  <button
                    onClick={() => handleExportNetsuite(p.id)}
                    disabled={loading === `ns-${p.id}`}
                    className="rounded border border-gray-300 dark:border-gray-600 px-2 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                  >
                    NS
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
