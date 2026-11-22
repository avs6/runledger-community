'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  BarChart3,
  Download,
  Pencil,
  Plus,
  Receipt,
  Shield,
  ShieldCheck,
  Trash2,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import ChargebackRulesPanel from '@/components/chargeback/ChargebackRulesPanel'
import CostCenterReportPanel from '@/components/chargeback/CostCenterReportPanel'
import { exportChargebackReport, getChargebackReport, listChargebackRules } from '@/lib/api'
import type { ChargebackReport, ChargebackRuleResponse } from '@/types/api'
import { num } from '@/lib/utils'

type Tab = 'overview' | 'rules' | 'cost-centers' | 'allocations' | 'exceptions' | 'exports'

const DIMENSIONS = [
  { value: 'feature_tag', label: 'Workflow tag' },
  { value: 'application', label: 'Application' },
  { value: 'api_key', label: 'API key' },
  { value: 'access_group', label: 'Access group' },
  { value: 'end_user', label: 'End user' },
  { value: 'model', label: 'Model' },
  { value: 'provider', label: 'Provider' },
  { value: 'intent', label: 'Intent' },
  { value: 'workspace', label: 'Workspace' },
] as const

type DimensionType = (typeof DIMENSIONS)[number]['value']

function buildLast12Months(): string[] {
  const months: string[] = []
  const now = new Date()
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }
  return months
}

function money(value: string) {
  return `$${Number.parseFloat(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function pct(value: string) {
  return `${Number.parseFloat(value).toFixed(1)}%`
}

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-rose-500'

const TABS: Array<[Tab, string]> = [
  ['overview', 'Overview'],
  ['rules', 'Rules'],
  ['cost-centers', 'Cost centers'],
  ['allocations', 'Allocations'],
  ['exceptions', 'Exceptions'],
  ['exports', 'Exports'],
]

export default function ChargebackPage() {
  const searchParams = useSearchParams()
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const { canManageOrgSettings } = useRole()

  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [rules, setRules] = useState<ChargebackRuleResponse[]>([])
  const [loadingRules, setLoadingRules] = useState(true)

  const months = useMemo(() => buildLast12Months(), [])
  const requestedDimension = searchParams.get('dimension')
  const requestedAccessGroupId = searchParams.get('access_group_id') ?? ''
  const requestedApiKeyId = searchParams.get('api_key_id') ?? ''
  const initialDimension: DimensionType =
    requestedDimension && DIMENSIONS.some((item) => item.value === requestedDimension)
      ? (requestedDimension as DimensionType)
      : 'feature_tag'
  const [selectedPeriod, setSelectedPeriod] = useState(months[0])
  const [reportDimension, setReportDimension] = useState<DimensionType>(initialDimension)
  const [report, setReport] = useState<ChargebackReport | null>(null)
  const [loadingReport, setLoadingReport] = useState(false)
  const [exporting, setExporting] = useState<'csv' | 'json' | null>(null)

  const fetchRules = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    try {
      setLoadingRules(true)
      const data = await listChargebackRules(apiKey)
      setRules(data.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load chargeback rules')
    } finally {
      setLoadingRules(false)
    }
  }, [apiKey, canManageOrgSettings])

  const fetchReport = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    try {
      setLoadingReport(true)
      const data = await getChargebackReport(apiKey, {
        period: selectedPeriod,
        dimension: reportDimension,
        access_group_id: requestedAccessGroupId || undefined,
        api_key_id: requestedApiKeyId || undefined,
      })
      setReport(data.items[0] ?? null)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load chargeback report')
    } finally {
      setLoadingReport(false)
    }
  }, [apiKey, canManageOrgSettings, selectedPeriod, reportDimension, requestedAccessGroupId, requestedApiKeyId])

  useEffect(() => {
    void fetchRules()
    if (apiKey) {
    }
  }, [fetchRules, apiKey])

  useEffect(() => {
    if (
      activeTab === 'overview' ||
      activeTab === 'allocations' ||
      activeTab === 'exceptions' ||
      activeTab === 'exports'
    ) {
      void fetchReport()
    }
  }, [activeTab, fetchReport])

  const refreshCounters = useCallback(() => {
    void fetchRules()
    }, [fetchRules, apiKey])

  async function handleExport(format: 'csv' | 'json') {
    try {
      setExporting(format)
      const raw = await exportChargebackReport(apiKey, {
        period: selectedPeriod,
        dimension: reportDimension,
        format,
        access_group_id: requestedAccessGroupId || undefined,
        api_key_id: requestedApiKeyId || undefined,
      })
      const blob = new Blob([raw], { type: format === 'csv' ? 'text/csv' : 'application/json' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `chargeback-${selectedPeriod}-${reportDimension}.${format}`
      anchor.click()
      URL.revokeObjectURL(url)
      toast.success(`Chargeback export ready (${format.toUpperCase()})`)
    } catch (err) {
      console.error(err)
      toast.error(`Failed to export ${format.toUpperCase()}`)
    } finally {
      setExporting(null)
    }
  }


  if (!canManageOrgSettings) {
    return (
      <div className="space-y-5">
        <section className="rounded-2xl border border-slate-200 bg-white/90 px-6 py-8 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <div className="flex items-center gap-3">
            <Receipt className="h-6 w-6 text-rose-600 dark:text-rose-400" />
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-950 dark:text-white">Chargeback</h1>
              <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                Chargeback management is available to organization admins and managers.
              </p>
            </div>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* ── Hero ── */}
      <section className="rounded-2xl border border-slate-200 bg-white/90 px-6 py-8 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Receipt className="h-6 w-6 text-rose-600 dark:text-rose-400" />
              <h1 className="text-2xl font-bold tracking-tight text-slate-950 dark:text-white">Chargeback</h1>
            </div>
            <p className="mt-1.5 max-w-xl text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
              Allocate AI cost across workflow tags, applications, users, providers, and other modern ownership dimensions — with rules, reports, and finance-ready exports.
            </p>
          </div>
          <button
            onClick={() => setActiveTab('rules')}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-gradient-to-r from-rose-600 to-orange-600 px-4 py-2 text-xs font-semibold text-white shadow-md transition hover:brightness-110"
          >
            <Plus className="h-3.5 w-3.5" /> Rules &amp; cost centers
          </button>
        </div>

        {/* KPI strip — from report + rules */}
        <div className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
          {[
            { label: 'Total Cost', value: report ? money(report.total_cost_usd) : '—' },
            { label: 'Covered', value: report ? money(report.covered_cost_usd) : '—' },
            { label: 'Unallocated', value: report ? money(report.unallocated_cost_usd) : '—' },
            { label: 'Rules', value: String(rules.length) },
            { label: 'Period', value: selectedPeriod },
            { label: 'Dimension', value: DIMENSIONS.find((d) => d.value === reportDimension)?.label ?? reportDimension },
            { label: 'Breakdown Rows', value: report ? String(report.breakdown.length) : '0' },
            { label: 'Exceptions', value: report ? String(report.breakdown.filter((r) => r.allocation_status !== 'allocated' || r.coverage_status !== 'budgeted').length) : '0' },
          ].map((kpi) => (
            <div key={kpi.label} className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">{kpi.label}</p>
              <p className="mt-0.5 truncate text-sm font-bold text-slate-900 dark:text-white">{kpi.value}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Period + dimension controls */}
      <div className="flex flex-wrap items-end gap-3">
        <label className="block text-xs">
          <span className="mb-1 block font-semibold text-slate-500 dark:text-slate-400">Period</span>
          <select value={selectedPeriod} onChange={(e) => setSelectedPeriod(e.target.value)} className={inputCls}>
            {months.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>
        <label className="block text-xs">
          <span className="mb-1 block font-semibold text-slate-500 dark:text-slate-400">Dimension</span>
          <select value={reportDimension} onChange={(e) => setReportDimension(e.target.value as DimensionType)} className={inputCls}>
            {DIMENSIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
          </select>
        </label>
        <button
          onClick={() => void fetchReport()}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Refresh
        </button>
      </div>

      {/* Tab bar */}
      <div className="rounded-lg bg-slate-100 p-1 dark:bg-slate-800/80">
        <nav className="flex flex-wrap gap-1">
          {TABS.map(([value, label]) => (
            <button
              key={value}
              onClick={() => setActiveTab(value)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                activeTab === value
                  ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Tab content ── */}

      {activeTab === 'overview' && (
        loadingReport ? (
          <p className="text-xs text-slate-500">Loading chargeback overview…</p>
        ) : report ? (
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart3 className="h-4 w-4 text-rose-500" />
                  <h2 className="text-xs font-bold text-slate-900 dark:text-white">Top Allocations</h2>
                </div>
                <div className="space-y-3">
                  {report.breakdown.slice(0, 6).map((item) => (
                    <div key={`${item.dimension}-${item.dimension_value}`} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-700 dark:text-slate-300">{item.dimension_value}</span>
                        <span className="font-mono font-semibold text-slate-900 dark:text-white">{money(item.cost_usd)}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800">
                        <div
                          className="h-1.5 rounded-full bg-gradient-to-r from-rose-500 to-orange-500"
                          style={{ width: `${Math.min(100, Number.parseFloat(item.pct_of_total))}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-slate-500">
                        <span>{pct(item.pct_of_total)} of total</span>
                        <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${
                          item.coverage_status === 'budgeted'
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                        }`}>{item.coverage_status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <div className="flex items-center gap-2 mb-4">
                  <ShieldCheck className="h-4 w-4 text-emerald-500" />
                  <h2 className="text-xs font-bold text-slate-900 dark:text-white">Chargeback Posture</h2>
                </div>
                <ul className="space-y-2 text-[11px] text-slate-600 dark:text-slate-300">
                  <li>Chargeback runs on real backend report and export endpoints.</li>
                  <li>Budget variance shown where scope aligns to chosen dimension.</li>
                  <li>Unallocated buckets are explicit so gaps are visible.</li>
                  <li>Access-group and API-key attribution can layer on later.</li>
                </ul>
                <div className="mt-3 flex flex-wrap gap-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                  {[
                    { label: 'Tool Registry', href: '/tool-registry' },
                    { label: 'Budgets', href: '/budgets' },
                    { label: 'Budget Detail', href: '/budgets?view=detail' },
                    { label: 'Ledger', href: '/ledger' },
                  ].map(({ label, href }) => (
                    <Link key={label} href={href} className="text-[10px] font-semibold text-rose-600 hover:underline dark:text-rose-400">{label}</Link>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-300 p-6 text-xs text-slate-500 dark:border-slate-700">
            No chargeback report data is available for this period and dimension yet.
          </div>
        )
      )}

      {activeTab === 'rules' && <ChargebackRulesPanel apiKey={apiKey} period={selectedPeriod} onChange={refreshCounters} />}

      {activeTab === 'cost-centers' && <CostCenterReportPanel apiKey={apiKey} period={selectedPeriod} />}

      {activeTab === 'allocations' && (
        loadingReport ? (
          <p className="text-xs text-slate-500">Loading allocation report…</p>
        ) : report ? (
          <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                    {['Value', 'Allocation', 'Cost', '% of Total', 'Runs', 'Calls', 'Budget', 'Variance'].map((h) => (
                      <th key={h} className={`px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500 ${['Cost', '% of Total', 'Runs', 'Calls', 'Budget', 'Variance'].includes(h) ? 'text-right' : 'text-left'}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {report.breakdown.length === 0 ? (
                    <tr className="bg-white dark:bg-slate-900">
                      <td colSpan={8} className="px-4 py-6 text-center text-slate-500">No allocation rows for this period.</td>
                    </tr>
                  ) : (
                    report.breakdown.map((item) => (
                      <tr key={`${item.dimension}-${item.dimension_value}`} className="bg-white hover:bg-rose-50/30 dark:bg-slate-900 dark:hover:bg-slate-800/50">
                        <td className="px-4 py-2.5 font-semibold text-slate-900 dark:text-white">{item.dimension_value}</td>
                        <td className="px-4 py-2.5">
                          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            item.allocation_status === 'allocated'
                              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                              : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                          }`}>
                            {item.allocation_status}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono font-semibold text-slate-900 dark:text-white">{money(item.cost_usd)}</td>
                        <td className="px-4 py-2.5 text-right text-slate-700 dark:text-slate-300">{pct(item.pct_of_total)}</td>
                        <td className="px-4 py-2.5 text-right text-slate-700 dark:text-slate-300">{item.run_count}</td>
                        <td className="px-4 py-2.5 text-right text-slate-700 dark:text-slate-300">{item.call_count}</td>
                        <td className="px-4 py-2.5 text-right font-mono text-slate-700 dark:text-slate-300">
                          {item.budget_usd ? money(item.budget_usd) : '—'}
                        </td>
                        <td className={`px-4 py-2.5 text-right font-mono ${
                          item.variance_usd && Number.parseFloat(item.variance_usd) > 0
                            ? 'text-rose-600 dark:text-rose-400'
                            : 'text-slate-700 dark:text-slate-300'
                        }`}>
                          {item.variance_usd ? money(item.variance_usd) : '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-300 p-6 text-xs text-slate-500 dark:border-slate-700">
            No allocation data is available for this selection.
          </div>
        )
      )}

      {activeTab === 'exceptions' && (
        loadingReport ? (
          <p className="text-xs text-slate-500">Loading allocation exceptions…</p>
        ) : report ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-800/30 dark:bg-amber-950/20">
              <h2 className="text-xs font-bold text-amber-900 dark:text-amber-200">Allocation Exceptions</h2>
              <p className="mt-1 text-[11px] text-amber-800/80 dark:text-amber-300/70">
                Unallocated or weakly covered rows stay visible here so finance operators can fix attribution gaps.
              </p>
            </div>
            <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                      {['Value', 'Allocation', 'Coverage', 'Cost', 'Runs', 'Calls'].map((h) => (
                        <th key={h} className={`px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500 ${['Cost', 'Runs', 'Calls'].includes(h) ? 'text-right' : 'text-left'}`}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {report.breakdown.filter(
                      (item) =>
                        item.allocation_status !== 'allocated' || item.coverage_status !== 'budgeted'
                    ).length === 0 ? (
                      <tr className="bg-white dark:bg-slate-900">
                        <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                          No allocation exceptions for this selection.
                        </td>
                      </tr>
                    ) : (
                      report.breakdown
                        .filter(
                          (item) =>
                            item.allocation_status !== 'allocated' ||
                            item.coverage_status !== 'budgeted'
                        )
                        .map((item) => (
                          <tr key={`${item.dimension}-${item.dimension_value}`} className="bg-white hover:bg-rose-50/30 dark:bg-slate-900 dark:hover:bg-slate-800/50">
                            <td className="px-4 py-2.5 font-semibold text-slate-900 dark:text-white">{item.dimension_value}</td>
                            <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300">{item.allocation_status}</td>
                            <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300">{item.coverage_status}</td>
                            <td className="px-4 py-2.5 text-right font-mono font-semibold text-slate-900 dark:text-white">{money(item.cost_usd)}</td>
                            <td className="px-4 py-2.5 text-right text-slate-700 dark:text-slate-300">{item.run_count}</td>
                            <td className="px-4 py-2.5 text-right text-slate-700 dark:text-slate-300">{item.call_count}</td>
                          </tr>
                        ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-300 p-6 text-xs text-slate-500 dark:border-slate-700">
            No allocation exception data is available for this selection.
          </div>
        )
      )}

      {activeTab === 'exports' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="text-xs font-bold text-slate-900 dark:text-white">Export Chargeback Evidence</h2>
            <p className="mt-2 text-[11px] text-slate-500">
              Export the allocation report for downstream finance review, spreadsheet workflows, or compliance packaging.
            </p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => void handleExport('csv')}
                disabled={exporting !== null}
                className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-rose-600 to-orange-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:brightness-110 disabled:opacity-50"
              >
                <Download className="h-3.5 w-3.5" />
                {exporting === 'csv' ? 'Exporting…' : 'Export CSV'}
              </button>
              <button
                onClick={() => void handleExport('json')}
                disabled={exporting !== null}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-4 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                <Download className="h-3.5 w-3.5" />
                {exporting === 'json' ? 'Exporting…' : 'Export JSON'}
              </button>
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="text-xs font-bold text-slate-900 dark:text-white">Current Scope</h2>
            <ul className="mt-3 space-y-1.5 text-[11px] text-slate-600 dark:text-slate-300">
              <li>Modern report dimensions: workflow tag, application, end user, provider, model, intent, and workspace.</li>
              <li>Budget variance appears where scope types align with chargeback.</li>
              <li>Access-group and API-key-native allocation can deepen later.</li>
              <li>Shared-cost policy preview remains in Billing (period-preparation surface).</li>
            </ul>
          </div>
        </div>
      )}




      {/* ── Quick-nav footer ── */}
      <div className="flex flex-wrap gap-2 pt-2">
        {[
          { label: 'Cost & Savings', href: '/cost-savings' },
          { label: 'Budgets', href: '/budgets' },
          { label: 'Billing', href: '/billing' },
          { label: 'Access Groups', href: '/access-groups' },
          { label: 'API Keys', href: '/api-keys' },
          { label: 'Gateway', href: '/gateway' },
          { label: 'Tags', href: '/tags' },
          { label: 'Audit Log', href: '/audit' },
          { label: 'Monitoring', href: '/monitoring' },
        ].map(({ label, href }) => (
          <Link
            key={label}
            href={href}
            className="rounded-full border border-rose-200 bg-rose-50/80 px-3 py-1 text-[11px] font-semibold text-rose-700 transition hover:bg-rose-100 dark:border-rose-800/50 dark:bg-rose-950/30 dark:text-rose-300 dark:hover:bg-rose-900/40"
          >
            {label}
          </Link>
        ))}
      </div>
    </div>
  )
}
