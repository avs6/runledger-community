'use client'

import { useState } from 'react'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { routes } from '@/lib/routes'
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
  const { confirm, dialog } = useConfirm()
  const [loading, setLoading] = useState<string | null>(null)
  const router = useRouter()
  const accessGroupQuery = accessGroupId ? `?access_group_id=${encodeURIComponent(accessGroupId)}` : ''

  async function handleClose(period: BillingPeriod) {
    const id = period.id
    setLoading(`close-${id}`)
    try {
      // Confirm with the amount that will be frozen (review F-19).
      const preview = await getPeriodBreakdown(apiKey, id)
      const ok = await confirm({
        title: `Close ${period.period_start} – ${period.period_end}?`,
        description:
          `Gross ${money(preview.gross_cost_usd)} · adjustments ${money(preview.total_adjustments_usd)} · ` +
          `net ${money(preview.net_cost_usd)}. Closing freezes these numbers and signs them. Usage that ` +
          'arrives later will not change this bill unless the period is reopened.',
        confirmLabel: 'Close period',
      })
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
    if (!(await confirm({ title: `Delete the open period ${period.period_start} – ${period.period_end}?`, confirmLabel: 'Delete', destructive: true }))) return
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

  const range = (period: BillingPeriod) => `${period.period_start} – ${period.period_end}`

  const columns: DataTableColumn<BillingPeriod>[] = [
    {
      key: 'period_start',
      header: 'Period',
      sortable: true,
      value: (period) => period.period_start,
      render: (period) => (
        <div>
          <Link
            href={`${routes.billingPeriodId(period.id)}${accessGroupQuery}`}
            className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            {range(period)}
          </Link>
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {period.currency}
            {period.closed_at && period.status === 'closed'
              ? ` · Closed ${new Date(period.closed_at).toLocaleString()}${period.closed_by ? ` by ${period.closed_by}` : ''}`
              : ' · Open period'}
            {period.reopened_at ? ` · Reopened: ${period.reopen_reason ?? ''}` : ''}
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (period) => <StatusBadge status={period.status} />,
    },
    {
      key: 'total_cost_usd',
      header: 'Gross',
      sortable: true,
      value: (period) => Number(period.total_cost_usd ?? 0),
      render: (period) => <span className="font-mono">{money(period.total_cost_usd)}</span>,
    },
    {
      key: 'net_cost_usd',
      header: 'Net',
      sortable: true,
      value: (period) => Number(period.net_cost_usd ?? 0),
      render: (period) => <span className="font-mono">{money(period.net_cost_usd)}</span>,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (period) => (
        <div className="flex justify-end gap-2">
          {period.status === 'open' ? (
            <>
              <button
                type="button"
                onClick={() => handleClose(period)}
                disabled={loading === `close-${period.id}`}
                aria-label={`Close period ${range(period)}`}
                className="rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading === `close-${period.id}` ? 'Closing...' : 'Close'}
              </button>
              <button
                type="button"
                onClick={() => handleDelete(period)}
                disabled={loading === `delete-${period.id}`}
                aria-label={`Delete period ${range(period)}`}
                className="rounded border border-rose-300 px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-50 dark:border-rose-800 dark:text-rose-400"
              >
                Delete
              </button>
            </>
          ) : period.status === 'closed' ? (
            <button
              type="button"
              onClick={() => handleReopen(period)}
              disabled={loading === `reopen-${period.id}`}
              aria-label={`Reopen period ${range(period)}`}
              className="rounded border border-amber-300 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-50 disabled:opacity-50 dark:border-amber-800 dark:text-amber-300"
            >
              Reopen
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => handleExportCsv(period.id)}
            disabled={loading === `csv-${period.id}`}
            aria-label={`Export period ${range(period)} as CSV`}
            className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            CSV
          </button>
          <button
            type="button"
            onClick={() => handleExportJson(period.id)}
            disabled={loading === `json-${period.id}`}
            aria-label={`Export period ${range(period)} as signed JSON`}
            className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            Signed JSON
          </button>
        </div>
      ),
    },
  ]

  return (
    <>
      <DataTable
        label="Billing periods"
        rows={items}
        columns={columns}
        rowKey={(period) => period.id}
        urlPrefix="bp_"
        searchPlaceholder="Search periods"
        csvFileName="billing-periods.csv"
        emptyTitle="No billing periods yet"
        emptyDescription="Create one to get started."
      />
      {dialog}
    </>
  )
}
