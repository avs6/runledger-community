'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  createOutcome,
  deleteOutcome,
  getOutcomeSummary,
  getOutcomeTrend,
  getOutcomesFinopsPosture,
  getInvestigationOrgIdentityPosture,
  getQualityCorrelation,
  getWorkflowROI,
  listOutcomes,
  updateOutcome,
} from '@/lib/api'
import type {
  OutcomeList,
  OutcomeResponse,
  OutcomeSummary,
  OutcomeTrend,
  OutcomesFinopsPosture,
  InvestigationOrgIdentityPosture,
  QualityOutcomeCorrelation,
  WorkflowROIList,
} from '@/types/api'
import type { ValueType } from 'recharts/types/component/DefaultTooltipContent'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Link from 'next/link'
import { Building2, ChevronDown, ChevronUp, Pencil, Plus, Save, Trash2, Wallet, X } from 'lucide-react'
import { num } from '@/lib/utils'

const WINDOWS = [7, 14, 30, 90]
const LEDGER_PAGE_SIZE = 12

type DraftOutcome = {
  outcome_type: string
  success: boolean
  run_id: string
  session_id: string
  end_user_id: string
  value_usd: string
  labels: string
}

const emptyDraft: DraftOutcome = {
  outcome_type: '',
  success: true,
  run_id: '',
  session_id: '',
  end_user_id: '',
  value_usd: '',
  labels: '{}',
}

function valueToNumber(value: ValueType | undefined): number | null {
  if (typeof value === 'number') return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  if (Array.isArray(value) && value.length > 0) return valueToNumber(value[0])
  return null
}

function parseLabels(raw: string) {
  const trimmed = raw.trim()
  if (!trimmed) return {}
  const parsed = JSON.parse(trimmed)
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed as Record<string, unknown>
  throw new Error('Labels must be a JSON object')
}

function money(value: string | null | undefined, digits = 4) {
  if (!value) return '—'
  const parsed = Number.parseFloat(value)
  if (!Number.isFinite(parsed)) return '—'
  return `$${num(parsed).toFixed(digits)}`
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

function outcomePill(success: boolean) {
  return success
    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
    : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
}

function draftFromOutcome(outcome: OutcomeResponse): DraftOutcome {
  return {
    outcome_type: outcome.outcome_type,
    success: outcome.success,
    run_id: outcome.run_id ?? '',
    session_id: outcome.session_id ?? '',
    end_user_id: outcome.end_user_id ?? '',
    value_usd: outcome.value_usd ?? '',
    labels: JSON.stringify(outcome.labels ?? {}, null, 2),
  }
}

const inputCls = 'w-full rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white'
const labelCls = 'text-[10px] font-semibold uppercase tracking-widest text-slate-400'

function OutcomeForm({
  title,
  submitLabel,
  draft,
  setDraft,
  onSubmit,
  onCancel,
  busy,
}: {
  title: string
  submitLabel: string
  draft: DraftOutcome
  setDraft: React.Dispatch<React.SetStateAction<DraftOutcome>>
  onSubmit: () => void
  onCancel?: () => void
  busy: boolean
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-xs font-semibold text-slate-800 dark:text-white">{title}</h2>
        {onCancel && (
          <button type="button" onClick={onCancel} className="rounded-md p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <div className="mt-2 grid gap-2 md:grid-cols-3">
        <div>
          <label className={labelCls}>Outcome type</label>
          <input value={draft.outcome_type} onChange={(e) => setDraft(p => ({ ...p, outcome_type: e.target.value }))} placeholder="refund_resolved" className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Value (USD)</label>
          <input value={draft.value_usd} onChange={(e) => setDraft(p => ({ ...p, value_usd: e.target.value }))} placeholder="12.00" className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Run ID</label>
          <input value={draft.run_id} onChange={(e) => setDraft(p => ({ ...p, run_id: e.target.value }))} placeholder="Optional" className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Session ID</label>
          <input value={draft.session_id} onChange={(e) => setDraft(p => ({ ...p, session_id: e.target.value }))} placeholder="Optional" className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>End user</label>
          <input value={draft.end_user_id} onChange={(e) => setDraft(p => ({ ...p, end_user_id: e.target.value }))} placeholder="Optional" className={inputCls} />
        </div>
        <div className="flex items-end gap-2">
          <label className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600 dark:border-slate-600 dark:text-slate-300">
            <input type="checkbox" checked={draft.success} onChange={(e) => setDraft(p => ({ ...p, success: e.target.checked }))} className="h-3 w-3" />
            Success
          </label>
          <button
            type="button"
            disabled={busy || !draft.outcome_type.trim()}
            onClick={onSubmit}
            className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="h-3 w-3" />
            {busy ? 'Saving…' : submitLabel}
          </button>
        </div>
      </div>
      <div className="mt-2">
        <label className={labelCls}>Labels JSON</label>
        <textarea
          value={draft.labels}
          onChange={(e) => setDraft(p => ({ ...p, labels: e.target.value }))}
          rows={2}
          className={`${inputCls} font-mono`}
        />
      </div>
    </div>
  )
}

export default function OutcomesPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const [windowDays, setWindowDays] = useState(30)
  const [summary, setSummary] = useState<OutcomeSummary | null>(null)
  const [trend, setTrend] = useState<OutcomeTrend | null>(null)
  const [workflows, setWorkflows] = useState<WorkflowROIList | null>(null)
  const [quality, setQuality] = useState<QualityOutcomeCorrelation[] | null>(null)
  const [ledger, setLedger] = useState<OutcomeList | null>(null)
  const [loading, setLoading] = useState(true)
  const [ledgerLoading, setLedgerLoading] = useState(true)
  const [ledgerOffset, setLedgerOffset] = useState(0)
  const [filterOutcomeType, setFilterOutcomeType] = useState('')
  const [filterSuccess, setFilterSuccess] = useState<'all' | 'true' | 'false'>('all')
  const [creating, setCreating] = useState(false)
  const [draft, setDraft] = useState<DraftOutcome>(emptyDraft)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<DraftOutcome>(emptyDraft)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [finopsPosture, setFinopsPosture] = useState<OutcomesFinopsPosture | null>(null)
  const [orgIdentityPosture, setOrgIdentityPosture] = useState<InvestigationOrgIdentityPosture | null>(null)
  const [showForm, setShowForm] = useState(false)

  const loadAnalytics = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [s, t, w, q] = await Promise.all([
        getOutcomeSummary(apiKey, windowDays),
        getOutcomeTrend(apiKey, windowDays),
        getWorkflowROI(apiKey, windowDays),
        getQualityCorrelation(apiKey, windowDays),
      ])
      setSummary(s)
      setTrend(t)
      setWorkflows(w)
      setQuality(q)
    } catch {
      toast.error('Failed to load outcome analytics')
    } finally {
      setLoading(false)
    }
  }, [apiKey, windowDays])

  const loadLedger = useCallback(async () => {
    if (!apiKey) return
    setLedgerLoading(true)
    try {
      const data = await listOutcomes(apiKey, {
        outcome_type: filterOutcomeType || undefined,
        success: filterSuccess === 'all' ? undefined : filterSuccess === 'true',
        limit: LEDGER_PAGE_SIZE,
        offset: ledgerOffset,
      })
      setLedger(data)
    } catch {
      toast.error('Failed to load outcomes ledger')
    } finally {
      setLedgerLoading(false)
    }
  }, [apiKey, filterOutcomeType, filterSuccess, ledgerOffset])

  useEffect(() => { void loadAnalytics() }, [loadAnalytics])
  useEffect(() => { void loadLedger() }, [loadLedger])

  useEffect(() => {
    if (!apiKey) return
    getOutcomesFinopsPosture(apiKey).then(setFinopsPosture).catch(() => {})
    getInvestigationOrgIdentityPosture(apiKey).then(setOrgIdentityPosture).catch(() => {})
  }, [apiKey])

  const trendByType = useMemo(
    () =>
      trend
        ? trend.items.reduce<Record<string, { day: string; success_rate: number; cost_per_success: number | null }[]>>(
            (acc, pt) => {
              if (!acc[pt.outcome_type]) acc[pt.outcome_type] = []
              acc[pt.outcome_type].push({
                day: pt.day,
                success_rate: parseFloat(pt.success_rate) * 100,
                cost_per_success: pt.cost_per_success_usd ? parseFloat(pt.cost_per_success_usd) : null,
              })
              return acc
            },
            {}
          )
        : {},
    [trend]
  )

  const trendTypes = Object.keys(trendByType)
  const selectedTrendType = trendTypes[0] ?? null
  const trendChartData = selectedTrendType ? trendByType[selectedTrendType] : []
  const ledgerPageCount = ledger ? Math.max(1, Math.ceil(ledger.total / LEDGER_PAGE_SIZE)) : 1
  const currentPage = Math.floor(ledgerOffset / LEDGER_PAGE_SIZE) + 1

  async function handleCreate() {
    if (!apiKey) return
    try {
      setCreating(true)
      await createOutcome(apiKey, {
        outcome_type: draft.outcome_type.trim(),
        success: draft.success,
        run_id: draft.run_id.trim() || null,
        session_id: draft.session_id.trim() || null,
        end_user_id: draft.end_user_id.trim() || null,
        value_usd: draft.value_usd.trim() || null,
        labels: parseLabels(draft.labels),
      })
      setDraft(emptyDraft)
      setShowForm(false)
      setLedgerOffset(0)
      await Promise.all([loadLedger(), loadAnalytics()])
      toast.success('Outcome recorded')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create outcome')
    } finally {
      setCreating(false)
    }
  }

  async function handleUpdate(id: string) {
    if (!apiKey) return
    try {
      setSavingId(id)
      await updateOutcome(apiKey, id, {
        outcome_type: editDraft.outcome_type.trim(),
        success: editDraft.success,
        run_id: editDraft.run_id.trim() || null,
        session_id: editDraft.session_id.trim() || null,
        end_user_id: editDraft.end_user_id.trim() || null,
        value_usd: editDraft.value_usd.trim() || null,
        labels: parseLabels(editDraft.labels),
      })
      setEditingId(null)
      await Promise.all([loadLedger(), loadAnalytics()])
      toast.success('Outcome updated')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update outcome')
    } finally {
      setSavingId(null)
    }
  }

  async function handleDelete(id: string) {
    if (!apiKey) return
    try {
      setDeletingId(id)
      await deleteOutcome(apiKey, id)
      if (ledger && ledger.items.length === 1 && ledgerOffset > 0) {
        setLedgerOffset(Math.max(0, ledgerOffset - LEDGER_PAGE_SIZE))
      }
      await Promise.all([loadLedger(), loadAnalytics()])
      toast.success('Outcome deleted')
    } catch {
      toast.error('Failed to delete outcome')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">Outcomes & ROI</h1>
          <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">Business outcomes, ROI attribution, and workflow cost analysis.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex overflow-hidden rounded-lg border border-slate-200 bg-white text-xs shadow-sm dark:border-slate-700 dark:bg-slate-900">
            {WINDOWS.map(w => (
              <button
                key={w}
                onClick={() => setWindowDays(w)}
                className={`px-2.5 py-1 transition-colors ${windowDays === w ? 'bg-blue-600 font-medium text-white' : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'}`}
              >
                {w}d
              </button>
            ))}
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
          >
            <Plus className="h-3 w-3" />
            Record
          </button>
        </div>
      </div>

      {/* Collapsible create form */}
      {showForm && (
        <OutcomeForm
          title="Record Outcome"
          submitLabel="Create"
          draft={draft}
          setDraft={setDraft}
          onSubmit={handleCreate}
          onCancel={() => setShowForm(false)}
          busy={creating}
        />
      )}

      {/* Analytics */}
      {loading ? (
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map(i => <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />)}
        </div>
      ) : (
        <>
          {/* Summary cards */}
          {summary && summary.items.length > 0 && (
            <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
              {summary.items.map(item => (
                <div key={item.outcome_type} className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs font-semibold text-slate-800 dark:text-slate-200">{item.outcome_type}</span>
                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                      parseFloat(item.success_rate) >= 0.8
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : parseFloat(item.success_rate) >= 0.5
                          ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                    }`}>
                      {(parseFloat(item.success_rate) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-baseline gap-3">
                    <div>
                      <span className="text-lg font-bold text-slate-950 dark:text-white">{item.count}</span>
                      <span className="ml-1 text-[10px] text-slate-400">outcomes</span>
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">{money(item.cost_per_success_usd, 4)}</span>
                      <span className="ml-0.5 text-[10px] text-slate-400">/success</span>
                    </div>
                  </div>
                  {item.roi !== null && (
                    <p className={`mt-1 text-[11px] font-semibold ${parseFloat(item.roi) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      ROI: {parseFloat(item.roi).toFixed(1)}%
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {summary && summary.items.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 p-6 text-center text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-900/40">
              No outcomes in the last {windowDays} days. Use <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">rl.outcome()</code> or the form above.
            </div>
          )}

          {/* Trend chart + context side by side */}
          <div className="grid gap-3 xl:grid-cols-2">
            {trendChartData.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="mb-2 text-xs font-semibold text-slate-700 dark:text-slate-300">Success Rate Trend — {selectedTrendType}</p>
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={trendChartData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
                    <XAxis dataKey="day" tick={{ fontSize: 10 }} />
                    <YAxis tickFormatter={v => `${v.toFixed(0)}%`} domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Tooltip formatter={(value) => { const n = valueToNumber(value); return n !== null ? `${num(n).toFixed(1)}%` : '' }} />
                    <Line type="monotone" dataKey="success_rate" stroke="#6366f1" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Context postures side by side */}
            <div className="space-y-2">
              {finopsPosture && (
                <div className="rounded-xl border border-emerald-200/60 bg-emerald-50/30 p-3 dark:border-emerald-800/40 dark:bg-emerald-950/20">
                  <div className="flex items-center gap-1.5">
                    <Wallet className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                    <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">FinOps Context</span>
                  </div>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {[
                      { l: 'Budgets', v: `${finopsPosture.budget_context.active_budgets}/${finopsPosture.budget_context.budgets}` },
                      { l: 'Breaches', v: `${finopsPosture.budget_context.breach_count}` },
                      { l: 'Billing', v: `${finopsPosture.billing_context.open_billing_periods}/${finopsPosture.billing_context.billing_periods}` },
                      { l: 'Outcomes 30d', v: `${finopsPosture.spend_context.outcomes_30d}` },
                    ].map(c => (
                      <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] dark:border-emerald-800 dark:bg-emerald-950/40">
                        <span className="font-medium text-emerald-500 dark:text-emerald-400">{c.l}</span>
                        <span className="font-bold text-emerald-700 dark:text-emerald-300">{c.v}</span>
                      </span>
                    ))}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {['Budgets', 'Billing', 'Chargeback', 'Ledger'].map(l => (
                      <Link key={l} href={`/${l.toLowerCase()}`} className="text-[10px] font-semibold text-emerald-600 hover:underline dark:text-emerald-400">{l}</Link>
                    ))}
                  </div>
                </div>
              )}

              {orgIdentityPosture && (
                <div className="rounded-xl border border-blue-200/60 bg-blue-50/30 p-3 dark:border-blue-800/40 dark:bg-blue-950/20">
                  <div className="flex items-center gap-1.5">
                    <Building2 className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                    <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">Workspace & Identity</span>
                  </div>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {[
                      { l: 'Workspace', v: orgIdentityPosture.org_context.workspace_name },
                      { l: 'Users', v: `${orgIdentityPosture.org_context.workspace_users}` },
                      { l: 'End Users 30d', v: `${orgIdentityPosture.user_context.distinct_end_users_30d}` },
                      { l: 'API Keys', v: `${orgIdentityPosture.api_key_context.active_keys}/${orgIdentityPosture.api_key_context.total_keys}` },
                    ].map(c => (
                      <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] dark:border-blue-800 dark:bg-blue-950/40">
                        <span className="font-medium text-blue-500 dark:text-blue-400">{c.l}</span>
                        <span className="font-bold text-blue-700 dark:text-blue-300">{c.v}</span>
                      </span>
                    ))}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {['Workspaces', 'Users', 'API Keys', 'Organization'].map(l => (
                      <Link key={l} href={`/${l.toLowerCase().replace(' ', '-')}`} className="text-[10px] font-semibold text-blue-600 hover:underline dark:text-blue-400">{l}</Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Workflow ROI table */}
          {workflows && workflows.items.length > 0 && (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="border-b border-slate-100 px-3 py-2 dark:border-slate-800">
                <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Workflow ROI by Feature Tag</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-[10px] uppercase text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                    <tr>
                      <th className="px-3 py-1.5 text-left">Feature Tag</th>
                      <th className="px-3 py-1.5 text-left">Outcome</th>
                      <th className="px-3 py-1.5 text-right">Runs</th>
                      <th className="px-3 py-1.5 text-right">Success</th>
                      <th className="px-3 py-1.5 text-right">Cost</th>
                      <th className="px-3 py-1.5 text-right">Value</th>
                      <th className="px-3 py-1.5 text-right">ROI</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {workflows.items.map((row, i) => (
                      <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                        <td className="px-3 py-1.5 font-mono font-medium text-slate-800 dark:text-slate-200">{row.feature_tag}</td>
                        <td className="px-3 py-1.5 text-slate-500">{row.outcome_type}</td>
                        <td className="px-3 py-1.5 text-right text-slate-500">{row.run_count}</td>
                        <td className="px-3 py-1.5 text-right text-slate-500">{(parseFloat(row.success_rate) * 100).toFixed(1)}%</td>
                        <td className="px-3 py-1.5 text-right text-slate-500">{money(row.total_cost_usd, 4)}</td>
                        <td className="px-3 py-1.5 text-right text-slate-500">{money(row.total_value_usd, 2)}</td>
                        <td className={`px-3 py-1.5 text-right font-medium ${row.roi === null ? 'text-slate-400' : parseFloat(row.roi) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          {row.roi !== null ? `${parseFloat(row.roi).toFixed(1)}%` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Quality correlation table */}
          {quality && quality.length > 0 && (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="border-b border-slate-100 px-3 py-2 dark:border-slate-800">
                <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Quality Score vs Success Rate</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-[10px] uppercase text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                    <tr>
                      <th className="px-3 py-1.5 text-left">Outcome Type</th>
                      <th className="px-3 py-1.5 text-right">Avg Score</th>
                      <th className="px-3 py-1.5 text-right">Success Rate</th>
                      <th className="px-3 py-1.5 text-right">Samples</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {quality.map((row, i) => (
                      <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                        <td className="px-3 py-1.5 text-slate-800 dark:text-slate-200">{row.outcome_type}</td>
                        <td className="px-3 py-1.5 text-right text-slate-500">{row.avg_score ? parseFloat(row.avg_score).toFixed(1) : '—'}</td>
                        <td className="px-3 py-1.5 text-right text-slate-500">{(parseFloat(row.success_rate) * 100).toFixed(1)}%</td>
                        <td className="px-3 py-1.5 text-right text-slate-500">{row.sample_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Outcome Ledger */}
      <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Outcome Ledger</p>
          <div className="flex items-center gap-2">
            <input
              value={filterOutcomeType}
              onChange={(e) => { setLedgerOffset(0); setFilterOutcomeType(e.target.value) }}
              placeholder="Filter type"
              className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
            />
            <select
              value={filterSuccess}
              onChange={(e) => { setLedgerOffset(0); setFilterSuccess(e.target.value as 'all' | 'true' | 'false') }}
              className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
            >
              <option value="all">All</option>
              <option value="true">Success</option>
              <option value="false">Failed</option>
            </select>
          </div>
        </div>

        <div className="mt-2 space-y-1.5">
          {editingId && (
            <OutcomeForm
              title="Edit Outcome"
              submitLabel="Save"
              draft={editDraft}
              setDraft={setEditDraft}
              onSubmit={() => handleUpdate(editingId)}
              onCancel={() => setEditingId(null)}
              busy={savingId === editingId}
            />
          )}

          {ledgerLoading ? (
            <div className="space-y-1.5">
              {[0, 1, 2].map(i => <div key={i} className="h-12 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />)}
            </div>
          ) : ledger && ledger.items.length > 0 ? (
            ledger.items.map(item => (
              <div key={item.id} className="rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2 dark:border-slate-800 dark:bg-slate-950/40">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">{item.outcome_type}</span>
                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${outcomePill(item.success)}`}>
                      {item.success ? 'OK' : 'Fail'}
                    </span>
                    <span className="text-[10px] text-slate-400">{formatDate(item.created_at)}</span>
                    {item.value_usd && <span className="text-[10px] font-medium text-slate-600 dark:text-slate-300">{money(item.value_usd, 2)}</span>}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => { setEditingId(item.id); setEditDraft(draftFromOutcome(item)) }}
                      className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
                    >
                      <Pencil className="h-3 w-3" />
                    </button>
                    <button
                      disabled={deletingId === item.id}
                      onClick={() => handleDelete(item.id)}
                      className="rounded p-1 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30 disabled:opacity-50"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
                <div className="mt-1 flex flex-wrap gap-3 text-[10px] text-slate-400">
                  {item.run_id && <span>Run: <span className="font-mono">{item.run_id.slice(0, 8)}</span></span>}
                  {item.session_id && <span>Session: <span className="font-mono">{item.session_id.slice(0, 8)}</span></span>}
                  {item.end_user_id && <span>User: <span className="font-mono">{item.end_user_id}</span></span>}
                </div>
              </div>
            ))
          ) : (
            <div className="py-4 text-center text-xs text-slate-400 dark:text-slate-500">No outcomes match filters.</div>
          )}
        </div>

        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
          <span>Page {currentPage}/{ledgerPageCount} &middot; {ledger?.total.toLocaleString() ?? 0} total</span>
          <div className="flex gap-1">
            <button
              disabled={currentPage <= 1}
              onClick={() => setLedgerOffset(Math.max(0, ledgerOffset - LEDGER_PAGE_SIZE))}
              className="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              Prev
            </button>
            <button
              disabled={currentPage >= ledgerPageCount}
              onClick={() => setLedgerOffset(ledgerOffset + LEDGER_PAGE_SIZE)}
              className="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
