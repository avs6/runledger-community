'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  createOutcome,
  deleteOutcome,
  getOutcomeSummary,
  getOutcomeTrend,
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
import { Pencil, Plus, Save, Trash2, X } from 'lucide-react'

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
  return `$${parsed.toFixed(digits)}`
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
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-950 dark:text-white">{title}</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Record a business outcome directly from the UI and link it to a run, session, or end user.
          </p>
        </div>
        {onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <X className="h-4 w-4" />
            Cancel
          </button>
        ) : null}
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Outcome type</label>
          <input
            value={draft.outcome_type}
            onChange={(e) => setDraft((prev) => ({ ...prev, outcome_type: e.target.value }))}
            placeholder="refund_resolved"
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Value (USD)</label>
          <input
            value={draft.value_usd}
            onChange={(e) => setDraft((prev) => ({ ...prev, value_usd: e.target.value }))}
            placeholder="12.00"
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Run ID</label>
          <input
            value={draft.run_id}
            onChange={(e) => setDraft((prev) => ({ ...prev, run_id: e.target.value }))}
            placeholder="Optional run UUID"
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Session ID</label>
          <input
            value={draft.session_id}
            onChange={(e) => setDraft((prev) => ({ ...prev, session_id: e.target.value }))}
            placeholder="Optional session ID"
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">End user</label>
          <input
            value={draft.end_user_id}
            onChange={(e) => setDraft((prev) => ({ ...prev, end_user_id: e.target.value }))}
            placeholder="Optional end user ID"
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          />
        </div>
        <div className="flex items-end">
          <label className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-200">
            <input
              type="checkbox"
              checked={draft.success}
              onChange={(e) => setDraft((prev) => ({ ...prev, success: e.target.checked }))}
            />
            Successful outcome
          </label>
        </div>
        <div className="md:col-span-2">
          <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Labels JSON</label>
          <textarea
            value={draft.labels}
            onChange={(e) => setDraft((prev) => ({ ...prev, labels: e.target.value }))}
            rows={4}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          />
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          disabled={busy || !draft.outcome_type.trim()}
          onClick={onSubmit}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {busy ? 'Saving…' : submitLabel}
        </button>
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

  useEffect(() => {
    void loadAnalytics()
  }, [loadAnalytics])

  useEffect(() => {
    void loadLedger()
  }, [loadLedger])

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
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-950 dark:text-white">Outcomes &amp; ROI</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Record business outcomes, review the outcome ledger, and connect success, value, and cost to workflow ROI.
          </p>
        </div>
        <select
          value={windowDays}
          onChange={(e) => setWindowDays(Number(e.target.value))}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
        >
          {WINDOWS.map((w) => (
            <option key={w} value={w}>
              Last {w}d
            </option>
          ))}
        </select>
      </div>

      <OutcomeForm
        title="Record Outcome"
        submitLabel="Create outcome"
        draft={draft}
        setDraft={setDraft}
        onSubmit={handleCreate}
        busy={creating}
      />

      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
          ))}
        </div>
      ) : (
        <>
          {summary && summary.items.length > 0 && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {summary.items.map((item) => (
                <div key={item.outcome_type} className="space-y-2 rounded-xl border border-slate-300 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate text-sm font-medium text-slate-700 dark:text-slate-200">{item.outcome_type}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        parseFloat(item.success_rate) >= 0.8
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : parseFloat(item.success_rate) >= 0.5
                            ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                            : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}
                    >
                      {(parseFloat(item.success_rate) * 100).toFixed(1)}% success
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 dark:text-slate-400">
                    <div>
                      <div className="text-lg font-bold text-slate-950 dark:text-white">{item.count}</div>
                      <div>outcomes</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-slate-950 dark:text-white">{money(item.cost_per_success_usd, 4)}</div>
                      <div>cost/success</div>
                    </div>
                  </div>
                  {item.roi !== null ? (
                    <div className={`text-sm font-semibold ${parseFloat(item.roi) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      ROI: {parseFloat(item.roi).toFixed(1)}%
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}

          {summary && summary.items.length === 0 ? (
            <div className="rounded-xl border border-slate-300 bg-white/90 p-8 text-center text-slate-600 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
              No outcomes recorded in the last {windowDays} days.
              <br />
              <span className="mt-1 block text-xs">
                Use <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">rl.outcome()</code> or the form above to start tracking.
              </span>
            </div>
          ) : null}

          {trendChartData.length > 0 ? (
            <div className="rounded-xl border border-slate-300 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-3 text-sm font-semibold text-slate-950 dark:text-white">Success Rate Trend — {selectedTrendType}</h2>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={trendChartData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v) => `${v.toFixed(0)}%`} domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(value) => {
                      const numeric = valueToNumber(value)
                      return numeric !== null ? `${numeric.toFixed(1)}%` : ''
                    }}
                  />
                  <Line type="monotone" dataKey="success_rate" stroke="#6366f1" strokeWidth={2} dot={false} name="Success Rate %" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : null}

          {workflows && workflows.items.length > 0 ? (
            <div className="overflow-hidden rounded-xl border border-slate-300 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="border-b border-slate-200 p-4 dark:border-slate-700">
                <h2 className="text-sm font-semibold text-slate-950 dark:text-white">Workflow ROI by Feature Tag</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-100 text-xs uppercase text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    <tr>
                      <th className="px-4 py-2 text-left">Feature Tag</th>
                      <th className="px-4 py-2 text-left">Outcome Type</th>
                      <th className="px-4 py-2 text-right">Runs</th>
                      <th className="px-4 py-2 text-right">Success Rate</th>
                      <th className="px-4 py-2 text-right">Total Cost</th>
                      <th className="px-4 py-2 text-right">Total Value</th>
                      <th className="px-4 py-2 text-right">ROI</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                    {workflows.items.map((row, i) => (
                      <tr key={i} className="text-slate-800 hover:bg-blue-50/45 dark:text-slate-200 dark:hover:bg-slate-800">
                        <td className="px-4 py-2 font-mono text-xs text-slate-950 dark:text-white">{row.feature_tag}</td>
                        <td className="px-4 py-2">{row.outcome_type}</td>
                        <td className="px-4 py-2 text-right">{row.run_count}</td>
                        <td className="px-4 py-2 text-right">{(parseFloat(row.success_rate) * 100).toFixed(1)}%</td>
                        <td className="px-4 py-2 text-right">{money(row.total_cost_usd, 4)}</td>
                        <td className="px-4 py-2 text-right">{money(row.total_value_usd, 2)}</td>
                        <td className={`px-4 py-2 text-right font-medium ${row.roi === null ? 'text-gray-400' : parseFloat(row.roi) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          {row.roi !== null ? `${parseFloat(row.roi).toFixed(1)}%` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {quality && quality.length > 0 ? (
            <div className="overflow-hidden rounded-xl border border-slate-300 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="border-b border-slate-200 p-4 dark:border-slate-700">
                <h2 className="text-sm font-semibold text-slate-950 dark:text-white">Quality Score vs Success Rate Correlation</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-100 text-xs uppercase text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    <tr>
                      <th className="px-4 py-2 text-left">Outcome Type</th>
                      <th className="px-4 py-2 text-right">Avg Score</th>
                      <th className="px-4 py-2 text-right">Success Rate</th>
                      <th className="px-4 py-2 text-right">Sample Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                    {quality.map((row, i) => (
                      <tr key={i} className="text-slate-800 hover:bg-blue-50/45 dark:text-slate-200 dark:hover:bg-slate-800">
                        <td className="px-4 py-2">{row.outcome_type}</td>
                        <td className="px-4 py-2 text-right">{row.avg_score ? parseFloat(row.avg_score).toFixed(1) : '—'}</td>
                        <td className="px-4 py-2 text-right">{(parseFloat(row.success_rate) * 100).toFixed(1)}%</td>
                        <td className="px-4 py-2 text-right">{row.sample_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-950 dark:text-white">Outcome Ledger</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Manage the actual recorded outcomes behind the ROI analytics with filtering, edit, and delete controls.
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:flex">
            <input
              value={filterOutcomeType}
              onChange={(e) => {
                setLedgerOffset(0)
                setFilterOutcomeType(e.target.value)
              }}
              placeholder="Filter by outcome type"
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
            />
            <select
              value={filterSuccess}
              onChange={(e) => {
                setLedgerOffset(0)
                setFilterSuccess(e.target.value as 'all' | 'true' | 'false')
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
            >
              <option value="all">All outcomes</option>
              <option value="true">Successful only</option>
              <option value="false">Failed only</option>
            </select>
          </div>
        </div>

        <div className="mt-4 space-y-4">
          {editingId ? (
            <OutcomeForm
              title="Edit Outcome"
              submitLabel="Save changes"
              draft={editDraft}
              setDraft={setEditDraft}
              onSubmit={() => handleUpdate(editingId)}
              onCancel={() => setEditingId(null)}
              busy={savingId === editingId}
            />
          ) : null}

          {ledgerLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
              ))}
            </div>
          ) : ledger && ledger.items.length > 0 ? (
            <div className="space-y-3">
              {ledger.items.map((item) => (
                <div key={item.id} className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-700 dark:bg-slate-800/60">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-slate-950 dark:text-white">{item.outcome_type}</span>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${outcomePill(item.success)}`}>
                          {item.success ? 'Success' : 'Failed'}
                        </span>
                        <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                          {formatDate(item.created_at)}
                        </span>
                      </div>
                      <div className="grid gap-2 text-sm text-slate-600 dark:text-slate-300 md:grid-cols-2 xl:grid-cols-4">
                        <div>Run: <span className="font-mono text-xs">{item.run_id ?? '—'}</span></div>
                        <div>Session: <span className="font-mono text-xs">{item.session_id ?? '—'}</span></div>
                        <div>User: <span className="font-mono text-xs">{item.end_user_id ?? '—'}</span></div>
                        <div>Value: <span className="font-medium">{money(item.value_usd, 2)}</span></div>
                      </div>
                      <pre className="max-h-36 overflow-auto rounded-lg bg-white p-3 text-xs text-slate-700 dark:bg-slate-900 dark:text-slate-200">
                        {JSON.stringify(item.labels ?? {}, null, 2)}
                      </pre>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setEditingId(item.id)
                          setEditDraft(draftFromOutcome(item))
                        }}
                        className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
                      >
                        <Pencil className="h-4 w-4" />
                        Edit
                      </button>
                      <button
                        type="button"
                        disabled={deletingId === item.id}
                        onClick={() => handleDelete(item.id)}
                        className="inline-flex items-center gap-2 rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-950/30 disabled:opacity-50"
                      >
                        <Trash2 className="h-4 w-4" />
                        {deletingId === item.id ? 'Deleting…' : 'Delete'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-400">
              No outcomes match the current filters.
            </div>
          )}
        </div>

        <div className="mt-4 flex items-center justify-between text-sm text-slate-600 dark:text-slate-300">
          <span>
            Page {currentPage} of {ledgerPageCount} · {ledger?.total.toLocaleString() ?? 0} outcomes
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() => setLedgerOffset(Math.max(0, ledgerOffset - LEDGER_PAGE_SIZE))}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={currentPage >= ledgerPageCount}
              onClick={() => setLedgerOffset(ledgerOffset + LEDGER_PAGE_SIZE)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
