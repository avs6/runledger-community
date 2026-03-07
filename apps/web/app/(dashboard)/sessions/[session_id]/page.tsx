'use client'

import { use } from 'react'
import { useSession } from 'next-auth/react'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { toast } from 'sonner'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { getSession, getSessionCostOverTurns } from '@/lib/api'
import type { SessionDetail, TurnCostResponse } from '@/types/api'
import { formatCost, formatDuration } from '@/lib/utils'

function RunStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    succeeded: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    cancelled: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  }
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        colors[status] ?? colors.cancelled
      }`}
    >
      {status}
    </span>
  )
}

interface ChartPoint {
  turn: number
  cumulative: number
  cost: number
}

export default function SessionDetailPage({
  params,
}: {
  params: Promise<{ session_id: string }>
}) {
  const { session_id } = use(params)
  const { data: authSession } = useSession()
  const [detail, setDetail] = useState<SessionDetail | null>(null)
  const [turns, setTurns] = useState<TurnCostResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!authSession?.apiKey) return
    const apiKey = authSession.apiKey
    setLoading(true)

    Promise.all([
      getSession(apiKey, session_id),
      getSessionCostOverTurns(apiKey, session_id),
    ])
      .then(([d, t]) => {
        setDetail(d)
        setTurns(t)
      })
      .catch(() => toast.error('Failed to load session'))
      .finally(() => setLoading(false))
  }, [authSession?.apiKey, session_id])

  const chartData: ChartPoint[] = (turns?.turns ?? []).map((t) => ({
    turn: t.turn_number,
    cumulative: parseFloat(t.cumulative_cost_usd),
    cost: parseFloat(t.cost_usd ?? '0'),
  }))

  if (loading) {
    return (
      <div className="flex flex-col gap-6 animate-pulse">
        <div className="h-8 w-48 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="h-48 rounded-lg bg-gray-200 dark:bg-gray-700" />
        <div className="h-64 rounded-lg bg-gray-200 dark:bg-gray-700" />
      </div>
    )
  }

  if (!detail) return null

  const totalDurationMs =
    detail.started_at && detail.ended_at
      ? new Date(detail.ended_at).getTime() - new Date(detail.started_at).getTime()
      : null

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <Link
          href="/sessions"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
        >
          <ChevronLeft className="h-4 w-4" />
          Sessions
        </Link>
      </div>

      {/* Header */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3">
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <span className="text-xs text-gray-400 dark:text-gray-500">Session</span>
            <p
              className="mt-0.5 font-mono text-sm text-gray-900 dark:text-gray-100"
              title={detail.session_id}
            >
              {detail.session_id.length > 32
                ? detail.session_id.slice(0, 32) + '…'
                : detail.session_id}
            </p>
          </div>
          {detail.end_user_id && (
            <div>
              <span className="text-xs text-gray-400 dark:text-gray-500">User</span>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-gray-100">
                {detail.end_user_id}
              </p>
            </div>
          )}
          <div>
            <span className="text-xs text-gray-400 dark:text-gray-500">Turns</span>
            <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-gray-100">
              {detail.run_count}
            </p>
          </div>
          <div>
            <span className="text-xs text-gray-400 dark:text-gray-500">Total Cost</span>
            <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-gray-100">
              {formatCost(detail.total_cost_usd)}
            </p>
          </div>
          {totalDurationMs != null && (
            <div>
              <span className="text-xs text-gray-400 dark:text-gray-500">Duration</span>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-gray-100">
                {formatDuration(totalDurationMs)}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Cumulative cost chart */}
      {chartData.length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-4">
          <h2 className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
            Cumulative Cost Over Turns
          </h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="turn"
                tick={{ fontSize: 12, fill: '#9ca3af' }}
                label={{ value: 'Turn', position: 'insideBottom', offset: -2, fill: '#9ca3af', fontSize: 11 }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                tickFormatter={(v: number) => `$${v.toFixed(4)}`}
              />
              <Tooltip
                formatter={(v: unknown) => [`$${(v as number).toFixed(6)}`, '']}
                labelFormatter={(l: unknown) => `Turn ${l}`}
                contentStyle={{
                  background: 'var(--tooltip-bg, #fff)',
                  border: '1px solid #e5e7eb',
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Line
                type="monotone"
                dataKey="cumulative"
                name="Cumulative"
                stroke="#6366f1"
                strokeWidth={2}
                dot={{ r: 3, fill: '#6366f1' }}
                activeDot={{ r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="cost"
                name="This turn"
                stroke="#a5b4fc"
                strokeWidth={1.5}
                strokeDasharray="4 2"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Run timeline */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Runs</h2>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {detail.runs.map((r) => (
            <Link
              key={r.id}
              href={`/runs/${r.id}`}
              className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-indigo-50 dark:bg-indigo-950 text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                {r.turn_number}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-gray-500 dark:text-gray-400">
                    {r.id.slice(0, 12)}…
                  </span>
                  <RunStatusBadge status={r.status} />
                  {r.feature_tag && (
                    <span className="rounded bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 text-xs text-gray-600 dark:text-gray-300">
                      {r.feature_tag}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-300">
                <span>{formatCost(r.total_cost_usd)}</span>
                <span className="text-gray-400 dark:text-gray-500">
                  {r.duration_ms != null ? formatDuration(r.duration_ms) : '—'}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
