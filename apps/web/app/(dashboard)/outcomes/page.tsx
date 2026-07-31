'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  getOutcomeSummary,
  getOutcomeTrend,
  getWorkflowROI,
  getQualityCorrelation,
} from '@/lib/api'
import type {
  OutcomeSummary,
  OutcomeTrend,
  WorkflowROIList,
  QualityOutcomeCorrelation,
} from '@/types/api'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

const WINDOWS = [7, 14, 30, 90]
const COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#3b82f6', '#8b5cf6']

export default function OutcomesPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const [windowDays, setWindowDays] = useState(30)
  const [summary, setSummary] = useState<OutcomeSummary | null>(null)
  const [trend, setTrend] = useState<OutcomeTrend | null>(null)
  const [workflows, setWorkflows] = useState<WorkflowROIList | null>(null)
  const [quality, setQuality] = useState<QualityOutcomeCorrelation[] | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!apiKey) return
    setLoading(true)
    Promise.all([
      getOutcomeSummary(apiKey, windowDays),
      getOutcomeTrend(apiKey, windowDays),
      getWorkflowROI(apiKey, windowDays),
      getQualityCorrelation(apiKey, windowDays),
    ])
      .then(([s, t, w, q]) => {
        setSummary(s)
        setTrend(t)
        setWorkflows(w)
        setQuality(q)
      })
      .catch(() => toast.error('Failed to load outcome data'))
      .finally(() => setLoading(false))
  }, [apiKey, windowDays])

  const trendByType = trend
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
    : {}

  const trendTypes = Object.keys(trendByType)
  const trendChartData = trendTypes.length > 0
    ? trendByType[trendTypes[0]]
    : []

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-950">Outcomes &amp; ROI</h1>
          <p className="mt-1 text-sm text-slate-600">
            Business outcome tracking — cost-per-success, success rates, and ROI by workflow
          </p>
        </div>
        <select
          value={windowDays}
          onChange={e => setWindowDays(Number(e.target.value))}
          className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-800 shadow-sm"
        >
          {WINDOWS.map(w => (
            <option key={w} value={w}>Last {w}d</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-100" />
          ))}
        </div>
      ) : (
        <>
          {/* Summary KPI cards */}
          {summary && summary.items.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {summary.items.map(item => (
                <div
                  key={item.outcome_type}
                  className="space-y-2 rounded-xl border border-slate-300 bg-white/90 p-4 shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="truncate text-sm font-medium text-slate-700">
                      {item.outcome_type}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
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
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
                    <div>
                      <div className="text-lg font-bold text-slate-950">
                        {item.count}
                      </div>
                      <div>outcomes</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-slate-950">
                        {item.cost_per_success_usd
                          ? `$${parseFloat(item.cost_per_success_usd).toFixed(4)}`
                          : '—'}
                      </div>
                      <div>cost/success</div>
                    </div>
                  </div>
                  {item.roi !== null && (
                    <div className={`text-sm font-semibold ${
                      parseFloat(item.roi) >= 0
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}>
                      ROI: {parseFloat(item.roi).toFixed(1)}%
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {summary && summary.items.length === 0 && (
            <div className="rounded-xl border border-slate-300 bg-white/90 p-8 text-center text-slate-600 shadow-sm">
              No outcomes recorded in the last {windowDays} days.
              <br />
              <span className="text-xs mt-1 block">
                Use <code className="rounded bg-slate-100 px-1">rl.outcome()</code> in your SDK to start tracking.
              </span>
            </div>
          )}

          {/* Trend chart */}
          {trendChartData.length > 0 && (
            <div className="rounded-xl border border-slate-300 bg-white/90 p-4 shadow-sm">
              <h2 className="mb-3 text-sm font-semibold text-slate-950">
                Success Rate Trend — {trendTypes[0]}
              </h2>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={trendChartData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={v => `${v.toFixed(0)}%`} domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number | undefined) => v !== undefined ? `${v.toFixed(1)}%` : ''} />
                  <Line
                    type="monotone"
                    dataKey="success_rate"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={false}
                    name="Success Rate %"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Workflow ROI table */}
          {workflows && workflows.items.length > 0 && (
            <div className="overflow-hidden rounded-xl border border-slate-300 bg-white/90 shadow-sm">
              <div className="border-b border-slate-200 p-4">
                <h2 className="text-sm font-semibold text-slate-950">Workflow ROI by Feature Tag</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-100 text-xs uppercase text-slate-600">
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
                  <tbody className="divide-y divide-slate-200">
                    {workflows.items.map((row, i) => (
                      <tr key={i} className="text-slate-800 hover:bg-blue-50/45">
                        <td className="px-4 py-2 font-mono text-xs text-slate-950">{row.feature_tag}</td>
                        <td className="px-4 py-2 text-slate-700">{row.outcome_type}</td>
                        <td className="px-4 py-2 text-right text-slate-950">{row.run_count}</td>
                        <td className="px-4 py-2 text-right text-slate-950">
                          {(parseFloat(row.success_rate) * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-2 text-right text-slate-950">${parseFloat(row.total_cost_usd).toFixed(4)}</td>
                        <td className="px-4 py-2 text-right text-slate-950">
                          {row.total_value_usd ? `$${parseFloat(row.total_value_usd).toFixed(2)}` : '—'}
                        </td>
                        <td className={`px-4 py-2 text-right font-medium ${
                          row.roi === null
                            ? 'text-gray-400'
                            : parseFloat(row.roi) >= 0
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}>
                          {row.roi !== null ? `${parseFloat(row.roi).toFixed(1)}%` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Quality correlation */}
          {quality && quality.length > 0 && (
            <div className="overflow-hidden rounded-xl border border-slate-300 bg-white/90 shadow-sm">
              <div className="border-b border-slate-200 p-4">
                <h2 className="text-sm font-semibold text-slate-950">Quality Score vs Success Rate Correlation</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-100 text-xs uppercase text-slate-600">
                    <tr>
                      <th className="px-4 py-2 text-left">Outcome Type</th>
                      <th className="px-4 py-2 text-right">Avg Score</th>
                      <th className="px-4 py-2 text-right">Success Rate</th>
                      <th className="px-4 py-2 text-right">Sample Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {quality.map((row, i) => (
                      <tr key={i} className="text-slate-800 hover:bg-blue-50/45">
                        <td className="px-4 py-2 text-slate-950">{row.outcome_type}</td>
                        <td className="px-4 py-2 text-right text-slate-950">
                          {row.avg_score ? parseFloat(row.avg_score).toFixed(1) : '—'}
                        </td>
                        <td className="px-4 py-2 text-right text-slate-950">
                          {(parseFloat(row.success_rate) * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-2 text-right text-slate-950">{row.sample_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
