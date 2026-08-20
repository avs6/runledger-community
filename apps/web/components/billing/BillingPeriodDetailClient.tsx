'use client'

import { useState } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import type {
  BillingAdjustmentList,
  BillingPeriod,
  PeriodBreakdown,
  ReconciliationResult,
} from '@/types/api'
import { exportPeriodCsv, exportPeriodSignedJson } from '@/lib/api'
import BreakdownTable from '@/components/billing/BreakdownTable'
import BillingAdjustmentsPanel from '@/components/billing/BillingAdjustmentsPanel'

interface Props {
  apiKey: string
  period: BillingPeriod
  reconciliation: ReconciliationResult | null
  breakdown: PeriodBreakdown | null
  adjustments: BillingAdjustmentList
  accessGroupId?: string
  apiKeyId?: string
}

type Tab = 'summary' | 'reconciliation' | 'breakdown' | 'adjustments' | 'exports'

function money(value: string | null) {
  if (!value) return '--'
  return `$${Number.parseFloat(value).toFixed(4)}`
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

function StatusBadge({ status }: { status: BillingPeriod['status'] }) {
  const cls =
    status === 'open'
      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
      : status === 'closing'
        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300'
        : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'

  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>{status}</span>
}

export default function BillingPeriodDetailClient({
  apiKey,
  period,
  reconciliation,
  breakdown,
  adjustments,
  accessGroupId,
  apiKeyId,
}: Props) {
  const [tab, setTab] = useState<Tab>('summary')
  const [loading, setLoading] = useState<'csv' | 'json' | null>(null)
  const exportScope = accessGroupId
    ? { access_group_id: accessGroupId }
    : apiKeyId
      ? { api_key_id: apiKeyId }
      : {}

  async function handleExportCsv() {
    setLoading('csv')
    try {
      const csv = await exportPeriodCsv(apiKey, period.id, exportScope)
      downloadBlob(csv, `period_${period.id}.csv`, 'text/csv')
    } catch (err) {
      console.error(err)
      toast.error('Failed to export CSV')
    } finally {
      setLoading(null)
    }
  }

  async function handleExportJson() {
    setLoading('json')
    try {
      const data = await exportPeriodSignedJson(apiKey, period.id, exportScope)
      downloadBlob(JSON.stringify(data, null, 2), `period_${period.id}.json`, 'application/json')
    } catch (err) {
      console.error(err)
      toast.error('Failed to export signed JSON')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="space-y-6">
      {accessGroupId ? (
        <div className="rounded-xl border border-blue-200/70 bg-blue-50/70 px-4 py-3 text-sm text-blue-700 dark:border-blue-900/40 dark:bg-blue-950/20 dark:text-blue-300">
          This billing period detail is scoped to the selected access group where attribution can be derived from member traffic.
        </div>
      ) : apiKeyId ? (
        <div className="rounded-xl border border-blue-200/70 bg-blue-50/70 px-4 py-3 text-sm text-blue-700 dark:border-blue-900/40 dark:bg-blue-950/20 dark:text-blue-300">
          This billing period detail is scoped to a single API key so budget and chargeback evidence can be reviewed against that owner directly.
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Gross cost</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{money(period.total_cost_usd)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Net cost</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{money(period.net_cost_usd)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Status</p>
          <div className="mt-2">
            <StatusBadge status={period.status} />
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase tracking-wide text-slate-500">Cross-feature bridges</p>
          <div className="mt-2 space-y-1 text-sm">
            <Link href={accessGroupId ? `/budgets?tab=policies&scope_type=access_group&scope_id=${encodeURIComponent(accessGroupId)}` : apiKeyId ? `/budgets?tab=policies&scope_type=api_key&scope_id=${encodeURIComponent(apiKeyId)}` : '/budgets?tab=policies'} className="block text-blue-600 hover:underline dark:text-blue-400">Budgets</Link>
            <Link href={accessGroupId ? `/chargeback?dimension=access_group&access_group_id=${encodeURIComponent(accessGroupId)}` : apiKeyId ? `/chargeback?dimension=api_key&api_key_id=${encodeURIComponent(apiKeyId)}` : '/chargeback'} className="block text-blue-600 hover:underline dark:text-blue-400">Chargeback</Link>
            <Link href="/cost-savings" className="block text-blue-600 hover:underline dark:text-blue-400">Cost &amp; Savings</Link>
          </div>
        </div>
      </div>

      {period.status === 'open' ? (
        <div className="rounded-xl border border-blue-200/70 bg-blue-50/70 px-4 py-3 text-sm text-blue-700 dark:border-blue-900/40 dark:bg-blue-950/20 dark:text-blue-300">
          This period is still open. Reconciliation and breakdown reflect current metered usage, and adjustments remain editable until the period is closed.
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {(['summary', 'reconciliation', 'breakdown', 'adjustments', 'exports'] as Tab[]).map((item) => (
          <button
            key={item}
            onClick={() => setTab(item)}
            className={`rounded-xl px-3 py-1.5 text-xs font-semibold capitalize transition ${
              tab === item
                ? 'bg-blue-600 text-white shadow-sm'
                : 'border border-slate-200 bg-white text-slate-600 hover:bg-blue-50'
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      {tab === 'summary' ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Period metadata</h2>
            <dl className="mt-4 grid gap-3 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-slate-500">Date range</dt>
                <dd className="font-medium text-slate-900 dark:text-white">{period.period_start} - {period.period_end}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-500">Currency</dt>
                <dd className="font-medium text-slate-900 dark:text-white">{period.currency}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-500">Exchange rate to USD</dt>
                <dd className="font-medium text-slate-900 dark:text-white">{period.exchange_rate_to_usd}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-500">Snapshot hash</dt>
                <dd className="font-mono text-slate-900 dark:text-white">{period.snapshot_hash || '--'}</dd>
              </div>
              {apiKeyId ? (
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-500">Scoped owner</dt>
                  <dd className="font-mono text-slate-900 dark:text-white">{apiKeyId}</dd>
                </div>
              ) : null}
            </dl>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Readiness signals</h2>
            <div className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
              <p>Reconciliation status: <span className="font-medium text-slate-900 dark:text-white">{reconciliation?.status ?? 'Unavailable'}</span></p>
              <p>Adjustments recorded: <span className="font-medium text-slate-900 dark:text-white">{adjustments.items.length}</span></p>
              <p>Breakdown rows: <span className="font-medium text-slate-900 dark:text-white">{breakdown?.by_application.length ?? 0}</span></p>
              <p>Closed at: <span className="font-medium text-slate-900 dark:text-white">{period.closed_at ? new Date(period.closed_at).toLocaleString() : 'Not closed'}</span></p>
            </div>
          </div>
        </div>
      ) : null}

      {tab === 'reconciliation' ? (
        reconciliation ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs uppercase tracking-wide text-slate-500">Provider calls sum</p>
                <p className="mt-2 font-mono text-lg text-slate-900 dark:text-white">${reconciliation.provider_calls_sum}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs uppercase tracking-wide text-slate-500">Usage daily sum</p>
                <p className="mt-2 font-mono text-lg text-slate-900 dark:text-white">${reconciliation.usage_daily_sum}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs uppercase tracking-wide text-slate-500">Delta %</p>
                <p className="mt-2 font-mono text-lg text-slate-900 dark:text-white">{reconciliation.delta_pct}%</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs uppercase tracking-wide text-slate-500">Data quality</p>
                <p className="mt-2 text-lg font-semibold text-slate-900 dark:text-white">
                  {reconciliation.orphaned_calls} orphaned / {reconciliation.duplicate_calls} duplicate
                </p>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Issues</h3>
                <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                  {reconciliation.issues.length ? reconciliation.issues.map((issue) => (
                    <li key={issue} className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300">
                      {issue}
                    </li>
                  )) : <li className="text-slate-500">No blocking reconciliation issues.</li>}
                </ul>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Warnings</h3>
                <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                  {reconciliation.warnings.length ? reconciliation.warnings.map((warning) => (
                    <li key={warning} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-300">
                      {warning}
                    </li>
                  )) : <li className="text-slate-500">No reconciliation warnings.</li>}
                </ul>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500 dark:border-slate-700">
            Reconciliation is unavailable for this period.
          </div>
        )
      ) : null}

      {tab === 'breakdown' ? (
        breakdown ? (
          <BreakdownTable breakdown={breakdown} />
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500 dark:border-slate-700">
            Breakdown is unavailable for this period.
          </div>
        )
      ) : null}

      {tab === 'adjustments' ? (
        <BillingAdjustmentsPanel
          apiKey={apiKey}
          periodId={period.id}
          initialData={adjustments}
          canEdit={period.status !== 'closed'}
        />
      ) : null}

      {tab === 'exports' ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Finance exports</h3>
            <p className="mt-2 text-sm text-slate-500">
              Export row-level CSV for spreadsheet workflows or signed JSON for evidence and downstream verification.
            </p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={handleExportCsv}
                disabled={loading === 'csv'}
                className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
              >
                {loading === 'csv' ? 'Exporting...' : 'Export CSV'}
              </button>
              <button
                onClick={handleExportJson}
                disabled={loading === 'json'}
                className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {loading === 'json' ? 'Exporting...' : 'Export signed JSON'}
              </button>
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Evidence handoff</h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
              <li>Use signed JSON when this period feeds compliance or dispute evidence.</li>
              <li>Use shared-cost policies from the main Billing page before generating chargeback outputs.</li>
              <li>Review related budgets if repeated reconciliation issues point back to runtime spend posture.</li>
              {apiKeyId ? <li>Use this scoped export when reconciling a single API key as a budget owner.</li> : null}
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  )
}
