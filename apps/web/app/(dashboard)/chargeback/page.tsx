'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  BarChart3,
  Download,
  Pencil,
  Plus,
  Receipt,
  ShieldCheck,
  Trash2,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import {
  createChargebackRule,
  deleteChargebackRule,
  exportChargebackReport,
  getChargebackReport,
  listChargebackRules,
  updateChargebackRule,
} from '@/lib/api'
import type { ChargebackReport, ChargebackRuleResponse } from '@/types/api'

type Tab = 'overview' | 'rules' | 'allocations' | 'exceptions' | 'exports'

const ALLOCATION_TYPES = [
  { value: 'direct', label: 'Direct allocation' },
  { value: 'proportional', label: 'Proportional' },
  { value: 'fixed', label: 'Fixed weight' },
  { value: 'shared_weight', label: 'Shared weight' },
  { value: 'showback', label: 'Showback only' },
] as const

const DIMENSIONS = [
  { value: 'feature_tag', label: 'Workflow tag' },
  { value: 'application', label: 'Application' },
  { value: 'end_user', label: 'End user' },
  { value: 'model', label: 'Model' },
  { value: 'provider', label: 'Provider' },
  { value: 'intent', label: 'Intent' },
  { value: 'workspace', label: 'Workspace' },
] as const

type AllocationType = (typeof ALLOCATION_TYPES)[number]['value']
type DimensionType = (typeof DIMENSIONS)[number]['value']
type RuleFormState = {
  allocation_type: AllocationType
  dimension: DimensionType
  weight: string
  require_approval: boolean
}

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

const DEFAULT_RULE: RuleFormState = {
  allocation_type: ALLOCATION_TYPES[0].value,
  dimension: DIMENSIONS[0].value,
  weight: '1.0',
  require_approval: false,
}

export default function ChargebackPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const { canManageOrgSettings } = useRole()

  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [rules, setRules] = useState<ChargebackRuleResponse[]>([])
  const [loadingRules, setLoadingRules] = useState(true)
  const [showRuleForm, setShowRuleForm] = useState(false)
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null)
  const [savingRule, setSavingRule] = useState(false)
  const [ruleForm, setRuleForm] = useState(DEFAULT_RULE)

  const months = useMemo(() => buildLast12Months(), [])
  const [selectedPeriod, setSelectedPeriod] = useState(months[0])
  const [reportDimension, setReportDimension] = useState('feature_tag')
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
      })
      setReport(data.items[0] ?? null)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load chargeback report')
    } finally {
      setLoadingReport(false)
    }
  }, [apiKey, canManageOrgSettings, selectedPeriod, reportDimension])

  useEffect(() => {
    void fetchRules()
  }, [fetchRules])

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

  function resetRuleForm() {
    setEditingRuleId(null)
    setRuleForm(DEFAULT_RULE)
    setShowRuleForm(false)
  }

  async function handleSaveRule() {
    try {
      setSavingRule(true)
      if (editingRuleId) {
        await updateChargebackRule(apiKey, editingRuleId, {
          allocation_type: ruleForm.allocation_type,
          dimension: ruleForm.dimension,
          weight: ruleForm.weight,
          status: 'active',
        })
        toast.success('Chargeback rule updated')
      } else {
        await createChargebackRule(apiKey, {
          allocation_type: ruleForm.allocation_type,
          dimension: ruleForm.dimension,
          weight: ruleForm.weight,
          require_approval: ruleForm.require_approval,
        })
        toast.success('Chargeback rule created')
      }
      resetRuleForm()
      await fetchRules()
    } catch (err) {
      console.error(err)
      toast.error('Failed to save chargeback rule')
    } finally {
      setSavingRule(false)
    }
  }

  async function handleDeleteRule(ruleId: string) {
    if (!window.confirm('Delete this chargeback rule?')) return
    try {
      await deleteChargebackRule(apiKey, ruleId)
      toast.success('Chargeback rule deleted')
      if (editingRuleId === ruleId) resetRuleForm()
      await fetchRules()
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete chargeback rule')
    }
  }

  async function handleExport(format: 'csv' | 'json') {
    try {
      setExporting(format)
      const raw = await exportChargebackReport(apiKey, {
        period: selectedPeriod,
        dimension: reportDimension,
        format,
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
      <div className="mx-auto max-w-5xl space-y-4 p-6">
        <div className="flex items-center gap-3">
          <Receipt className="h-7 w-7 text-indigo-500" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Chargeback</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Chargeback management is available to organization admins and managers.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Receipt className="h-7 w-7 text-indigo-500" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Chargeback</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Allocate AI cost across workflow tags, applications, users, providers, and other modern ownership dimensions.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {([
          ['overview', 'Overview'],
          ['rules', 'Rules'],
          ['allocations', 'Allocations'],
          ['exceptions', 'Exceptions'],
          ['exports', 'Exports'],
        ] as Array<[Tab, string]>).map(([value, label]) => (
          <button
            key={value}
            onClick={() => setActiveTab(value)}
            className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === value
                ? 'bg-blue-600 text-white shadow-sm'
                : 'border border-slate-200 bg-white text-slate-600 hover:bg-blue-50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_auto_auto_auto]">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-500">Period</span>
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-800"
          >
            {months.map((month) => (
              <option key={month} value={month}>
                {month}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-500">Dimension</span>
          <select
            value={reportDimension}
            onChange={(e) => setReportDimension(e.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-800"
          >
            {DIMENSIONS.map((dimension) => (
              <option key={dimension.value} value={dimension.value}>
                {dimension.label}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={() => void fetchReport()}
          className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Refresh
        </button>
        <button
          onClick={() => setShowRuleForm((current) => !current)}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
        >
          <Plus className="h-4 w-4" />
          Rule
        </button>
      </div>

      {activeTab === 'overview' ? (
        loadingReport ? (
          <p className="text-sm text-slate-500">Loading chargeback overview...</p>
        ) : report ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs uppercase tracking-wide text-slate-500">Total cost</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{money(report.total_cost_usd)}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs uppercase tracking-wide text-slate-500">Budget-covered</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{money(report.covered_cost_usd)}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs uppercase tracking-wide text-slate-500">Unallocated</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{money(report.unallocated_cost_usd)}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs uppercase tracking-wide text-slate-500">Rule count</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{rules.length}</p>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-blue-600" />
                  <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Top allocations</h2>
                </div>
                <div className="mt-4 space-y-3">
                  {report.breakdown.slice(0, 6).map((item) => (
                    <div key={`${item.dimension}-${item.dimension_value}`} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-700 dark:text-slate-300">{item.dimension_value}</span>
                        <span className="font-mono text-slate-900 dark:text-white">{money(item.cost_usd)}</span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800">
                        <div
                          className="h-2 rounded-full bg-blue-500"
                          style={{ width: `${Math.min(100, Number.parseFloat(item.pct_of_total))}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>{pct(item.pct_of_total)} of total</span>
                        <span>{item.coverage_status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Bundle C posture</h2>
                </div>
                <ul className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                  <li>Chargeback now runs on real backend report and export endpoints instead of UI-only assumptions.</li>
                  <li>Budget variance is shown where the current budget scope model already aligns to the chosen dimension.</li>
                  <li>Unallocated buckets are explicit so allocation gaps are visible instead of silently disappearing.</li>
                  <li>Deeper access-group and API-key-native attribution can layer on later without reopening legacy team/project concepts.</li>
                </ul>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500 dark:border-slate-700">
            No chargeback report data is available for this period and dimension yet.
          </div>
        )
      ) : null}

      {activeTab === 'rules' ? (
        <div className="space-y-4">
          {showRuleForm ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="grid gap-4 md:grid-cols-4">
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-500">Allocation type</span>
                  <select
                    value={ruleForm.allocation_type}
                    onChange={(e) =>
                      setRuleForm((current) => ({
                        ...current,
                        allocation_type: e.target.value as AllocationType,
                      }))
                    }
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-800"
                  >
                    {ALLOCATION_TYPES.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-500">Dimension</span>
                  <select
                    value={ruleForm.dimension}
                    onChange={(e) =>
                      setRuleForm((current) => ({
                        ...current,
                        dimension: e.target.value as DimensionType,
                      }))
                    }
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-800"
                  >
                    {DIMENSIONS.map((dimension) => (
                      <option key={dimension.value} value={dimension.value}>
                        {dimension.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-500">Weight (0-1)</span>
                  <input
                    value={ruleForm.weight}
                    onChange={(e) => setRuleForm((current) => ({ ...current, weight: e.target.value }))}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-800"
                  />
                </label>
                <label className="flex items-end gap-2 pb-2 text-sm text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={ruleForm.require_approval}
                    onChange={(e) => setRuleForm((current) => ({ ...current, require_approval: e.target.checked }))}
                  />
                  Require approval
                </label>
              </div>
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => void handleSaveRule()}
                  disabled={savingRule}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
                >
                  {savingRule ? 'Saving...' : editingRuleId ? 'Save rule' : 'Create rule'}
                </button>
                <button
                  onClick={resetRuleForm}
                  className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : null}

          <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                <tr>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Type</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Dimension</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Weight</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Status</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Created</th>
                  <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loadingRules ? (
                  <tr className="bg-white dark:bg-slate-900">
                    <td colSpan={6} className="px-4 py-6 text-center text-slate-500">Loading rules...</td>
                  </tr>
                ) : rules.length === 0 ? (
                  <tr className="bg-white dark:bg-slate-900">
                    <td colSpan={6} className="px-4 py-6 text-center text-slate-500">No chargeback rules yet.</td>
                  </tr>
                ) : (
                  rules.map((rule) => (
                    <tr key={rule.id} className="bg-white dark:bg-slate-900">
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{rule.allocation_type}</td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{rule.dimension}</td>
                      <td className="px-4 py-3 font-mono text-slate-900 dark:text-white">{rule.weight}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                          rule.status === 'active'
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                            : rule.status === 'pending_approval'
                              ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                              : 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                        }`}>
                          {rule.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-500">{new Date(rule.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => {
                              setEditingRuleId(rule.id)
                              setRuleForm({
                                allocation_type: rule.allocation_type as AllocationType,
                                dimension: rule.dimension as DimensionType,
                                weight: rule.weight,
                                require_approval: rule.status === 'pending_approval',
                              })
                              setShowRuleForm(true)
                            }}
                            className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => void handleDeleteRule(rule.id)}
                            className="rounded-lg border border-rose-200 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-900/40 dark:text-rose-300 dark:hover:bg-rose-950/30"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {activeTab === 'allocations' ? (
        loadingReport ? (
          <p className="text-sm text-slate-500">Loading allocation report...</p>
        ) : report ? (
          <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                <tr>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Value</th>
                  <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Allocation</th>
                  <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Cost</th>
                  <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">% of total</th>
                  <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Runs</th>
                  <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Calls</th>
                  <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Budget</th>
                  <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Variance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {report.breakdown.length === 0 ? (
                  <tr className="bg-white dark:bg-slate-900">
                    <td colSpan={8} className="px-4 py-6 text-center text-slate-500">No allocation rows for this period.</td>
                  </tr>
                ) : (
                  report.breakdown.map((item) => (
                    <tr key={`${item.dimension}-${item.dimension_value}`} className="bg-white dark:bg-slate-900">
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{item.dimension_value}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                          item.allocation_status === 'allocated'
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                        }`}>
                          {item.allocation_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-slate-900 dark:text-white">{money(item.cost_usd)}</td>
                      <td className="px-4 py-3 text-right text-slate-700 dark:text-slate-300">{pct(item.pct_of_total)}</td>
                      <td className="px-4 py-3 text-right text-slate-700 dark:text-slate-300">{item.run_count}</td>
                      <td className="px-4 py-3 text-right text-slate-700 dark:text-slate-300">{item.call_count}</td>
                      <td className="px-4 py-3 text-right font-mono text-slate-700 dark:text-slate-300">
                        {item.budget_usd ? money(item.budget_usd) : '--'}
                      </td>
                      <td className={`px-4 py-3 text-right font-mono ${
                        item.variance_usd && Number.parseFloat(item.variance_usd) > 0
                          ? 'text-rose-600 dark:text-rose-400'
                          : 'text-slate-700 dark:text-slate-300'
                      }`}>
                        {item.variance_usd ? money(item.variance_usd) : '--'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500 dark:border-slate-700">
            No allocation data is available for this selection.
          </div>
        )
      ) : null}

      {activeTab === 'exceptions' ? (
        loadingReport ? (
          <p className="text-sm text-slate-500">Loading allocation exceptions...</p>
        ) : report ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Allocation exceptions</h2>
              <p className="mt-2 text-sm text-slate-500">
                Unallocated or weakly covered rows stay visible here so finance operators can fix attribution gaps instead of losing them in aggregate totals.
              </p>
            </div>
            <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-700">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                  <tr>
                    <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Value</th>
                    <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Allocation</th>
                    <th className="px-4 py-3 font-medium text-slate-600 dark:text-slate-300">Coverage</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Cost</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Runs</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-600 dark:text-slate-300">Calls</th>
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
                        <tr key={`${item.dimension}-${item.dimension_value}`} className="bg-white dark:bg-slate-900">
                          <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{item.dimension_value}</td>
                          <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{item.allocation_status}</td>
                          <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{item.coverage_status}</td>
                          <td className="px-4 py-3 text-right font-mono text-slate-900 dark:text-white">
                            {money(item.cost_usd)}
                          </td>
                          <td className="px-4 py-3 text-right text-slate-700 dark:text-slate-300">{item.run_count}</td>
                          <td className="px-4 py-3 text-right text-slate-700 dark:text-slate-300">{item.call_count}</td>
                        </tr>
                      ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500 dark:border-slate-700">
            No allocation exception data is available for this selection.
          </div>
        )
      ) : null}

      {activeTab === 'exports' ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Export chargeback evidence</h2>
            <p className="mt-2 text-sm text-slate-500">
              Export the allocation report for downstream finance review, spreadsheet workflows, or compliance packaging.
            </p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => void handleExport('csv')}
                disabled={exporting !== null}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
              >
                <Download className="h-4 w-4" />
                {exporting === 'csv' ? 'Exporting...' : 'Export CSV'}
              </button>
              <button
                onClick={() => void handleExport('json')}
                disabled={exporting !== null}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                <Download className="h-4 w-4" />
                {exporting === 'json' ? 'Exporting...' : 'Export JSON'}
              </button>
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Current Bundle C scope</h2>
            <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
              <li>Modern report dimensions: workflow tag, application, end user, provider, model, intent, and workspace.</li>
              <li>Budget variance appears where the current budget scope types already line up with chargeback.</li>
              <li>Access-group and API-key-native allocation can deepen later without reintroducing teams or projects.</li>
              <li>Shared-cost policy preview remains in Billing because that is the period-preparation surface, not the allocation reporting owner.</li>
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  )
}
