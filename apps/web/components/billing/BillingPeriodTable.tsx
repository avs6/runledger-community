'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { BillingPeriod } from '@/types/api'
import { closeBillingPeriod, exportPeriodCsv, exportPeriodSignedJson } from '@/lib/api'

interface Props {
  items: BillingPeriod[]
  apiKey: string
  onClosed: (id: string) => void
}

function StatusBadge({ status }: { status: BillingPeriod['status'] }) {
  const cls =
    status === 'open'
      ? 'bg-blue-100 text-blue-700'
      : status === 'closing'
        ? 'bg-yellow-100 text-yellow-700'
        : 'bg-green-100 text-green-700'
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

  async function handleClose(id: string) {
    setLoading(`close-${id}`)
    try {
      await closeBillingPeriod(apiKey, id)
      onClosed(id)
    } catch (err) {
      console.error(err)
      alert('Failed to close period')
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
      alert('Failed to export CSV')
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
      alert('Failed to export JSON')
    } finally {
      setLoading(null)
    }
  }

  if (items.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-gray-200 py-10 text-center text-sm text-gray-500">
        No billing periods yet. Create one to get started.
      </p>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Period</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600">Total Cost</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {items.map((p) => (
            <tr key={p.id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <Link
                  href={`/billing/${p.id}`}
                  className="font-medium text-indigo-600 hover:underline"
                >
                  {p.period_start} — {p.period_end}
                </Link>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={p.status} />
              </td>
              <td className="px-4 py-3 text-right font-mono text-gray-700">
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
                    className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    CSV
                  </button>
                  <button
                    onClick={() => handleExportJson(p.id)}
                    disabled={loading === `json-${p.id}`}
                    className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    JSON
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
