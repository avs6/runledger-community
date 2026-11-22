'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import type { BillingPeriod } from '@/types/api'
import {
  apiErrorMessage,
  closeBillingPeriod,
  deleteBillingPeriod,
  exportPeriodCsv,
  exportPeriodSignedJson,
  getPeriodBreakdown,
  reopenBillingPeriod,
} from '@/lib/api'

interface Props {
  items: BillingPeriod[]
  apiKey: string
  onClosed?: (id: string) => void
  accessGroupId?: string
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

export default function BillingPeriodTable({ items, apiKey, onClosed, accessGroupId }: Props) {
  const [loading, setLoading] = useState<string | null>(null)
  const router = useRouter()
  const accessGroupQuery = accessGroupId ? `?access_group_id=${encodeURIComponent(accessGroupId)}` : ''

  async function handleClose(period: BillingPeriod) {
    const id = period.id
    setLoading(`close-${id}`)
    try {
      // Confirm with the amount that will be frozen (review F-19).
      const preview = await getPeriodBreakdown(apiKey, id)
      const ok = window.confirm(
        `Close ${period.period_start} – ${period.period_end}?

` +
          `Gross ${money(preview.gross_cost_usd)} · adjustments ${money(preview.total_adjustments_usd)} · ` +
          `net ${money(preview.net_cost_usd)}

` +
          'Closing freezes these numbers and signs them. Usage that arrives later will not change ' +
          'this bill unless the period is reopened.',
      )
      if (!ok) return
      await closeBillingPeriod(apiKey, id)
      onClosed?.(id)
      router.refresh()
      toast.success('Billing period closed and signed')
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to close billing period'))
    } finally {
      setLoading(null)
    }
  }

  async function handleReopen(period: BillingPeriod) {
    const reason = window.prompt(
      `Reopen ${period.period_start} – ${period.period_end}? The signed snapshot is kept as history. Reason:`,
    )
    if (!reason || reason.trim().length < 3) return
    setLoading(`reopen-${period.id}`)
    try {
      await reopenBillingPeriod(apiKey, period.id, reason.trim())
      onClosed?.(period.id)
      router.refresh()
      toast.success('Billing period reopened')
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to reopen billing period'))
    } finally {
      setLoading(null)
    }
  }

  async function handleDelete(period: BillingPeriod) {
    if (!window.confirm(`Delete the open period ${period.period_start} – ${period.period_end}?`)) return
    setLoading(`delete-${period.id}`)
    try {
      await deleteBillingPeriod(apiKey, period.id)
      onClosed?.(period.id)
      router.refresh()
      toast.success('Billing period deleted')
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to delete billing period'))
    } finally {
      setLoading(null)
    }
  }

  async function handleExportCsv(id: string) {
    setLoading(`csv-${id}`)
    try {
      const csv = await exportPeriodCsv(apiKey, id, { access_group_id: accessGroupId })
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
      const data = await exportPeriodSignedJson(apiKey, id, { access_group_id: accessGroupId })
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
                  href={`/billing/${period.id}${accessGroupQuery}`}
                  className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  {period.period_start} - {period.period_end}
                </Link>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {period.currency}
                  {period.closed_at && period.status === 'closed'
                    ? ` · Closed ${new Date(period.closed_at).toLocaleString()}${period.closed_by ? ` by ${period.closed_by}` : ''}`
                    : ' · Open period'}
                  {period.reopened_at ? ` · Reopened: ${period.reopen_reason ?? ''}` : ''}
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
                  {period.status === 'open' ? (
                    <>
                      <button
                        onClick={() => handleClose(period)}
                        disabled={loading === `close-${period.id}`}
                        className="rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {loading === `close-${period.id}` ? 'Closing...' : 'Close'}
                      </button>
                      <button
                        onClick={() => handleDelete(period)}
                        disabled={loading === `delete-${period.id}`}
                        className="rounded border border-rose-300 px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-50 dark:border-rose-800 dark:text-rose-400"
                      >
                        Delete
                      </button>
                    </>
                  ) : period.status === 'closed' ? (
                    <button
                      onClick={() => handleReopen(period)}
                      disabled={loading === `reopen-${period.id}`}
                      className="rounded border border-amber-300 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-50 disabled:opacity-50 dark:border-amber-800 dark:text-amber-300"
                    >
                      Reopen
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
