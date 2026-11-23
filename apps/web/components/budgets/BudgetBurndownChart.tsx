'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getBudgetBurndown } from '@/lib/api'
import type { BudgetBurndown } from '@/types/api'
import { AsyncCard } from '@/components/ui/async-card'
import { CHART_SERIES, CHART_UI, STATUS_HEX } from '@/lib/tokens'

function fmtMoney(v: number) {
  return `$${v.toFixed(v < 1 ? 4 : 2)}`
}

/**
 * Burn-down for one budget: cumulative spend this period, the run-rate forecast to
 * the end of the period, the limit, and the forecast-to-breach date (ENH).
 */
export default function BudgetBurndownChart({ apiKey, budgetId }: { apiKey: string; budgetId: string }) {
  const [data, setData] = useState<BudgetBurndown | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      setData(await getBudgetBurndown(apiKey, budgetId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load burn-down')
    }
  }, [apiKey, budgetId])

  useEffect(() => {
    void load()
  }, [load])

  const hourly = data?.period_type === 'daily'
  const rows = useMemo(() => {
    if (!data) return []
    const lastActual = [...data.points].reverse().find((p) => !p.forecast)
    return data.points.map((p) => {
      const d = new Date(p.date)
      const label = hourly
        ? d.toLocaleTimeString([], { hour: '2-digit' })
        : d.toLocaleDateString([], { month: 'short', day: 'numeric' })
      const value = Number(p.cumulative_usd)
      return {
        label,
        actual: p.forecast ? null : value,
        // The forecast line starts at the last actual point so the two connect.
        forecast: p.forecast || p === lastActual ? value : null,
      }
    })
  }, [data, hourly])

  const limit = data ? Number(data.limit_usd) : 0
  const breachText = !data
    ? ''
    : data.already_breached
      ? 'Limit already reached this period.'
      : data.forecast_breach_date
        ? `At the current run rate the limit is reached ${new Date(data.forecast_breach_date).toLocaleString(
            [],
            hourly ? { hour: '2-digit', minute: '2-digit' } : { month: 'short', day: 'numeric' }
          )}.`
        : 'Not forecast to breach this period at the current run rate.'

  return (
    <AsyncCard
      title="Burn-down"
      description={breachText || 'Cumulative spend this period with a run-rate forecast.'}
      loading={data === null && !error}
      error={error}
      onRetry={load}
      empty={data !== null && data.points.length === 0}
      emptyTitle="No spend yet"
    >
      {data && (
        <div>
          <dl className="mb-3 grid grid-cols-3 gap-2 text-xs">
            <div>
              <dt className="text-slate-500">Spent</dt>
              <dd className="font-semibold tabular-nums">{fmtMoney(Number(data.current_spend_usd))}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Daily run rate</dt>
              <dd className="font-semibold tabular-nums">{fmtMoney(Number(data.daily_run_rate_usd))}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Projected this period</dt>
              <dd className="font-semibold tabular-nums">
                {data.projected_period_spend_usd ? fmtMoney(Number(data.projected_period_spend_usd)) : '—'}
              </dd>
            </div>
          </dl>
          <div className="h-56" role="img" aria-label={`Budget burn-down chart. ${breachText}`}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={CHART_UI.grid} strokeDasharray="3 3" />
                <XAxis dataKey="label" stroke={CHART_UI.axis} fontSize={11} minTickGap={16} />
                <YAxis stroke={CHART_UI.axis} fontSize={11} tickFormatter={(v: number) => `$${v}`} width={56} />
                <Tooltip formatter={(v) => fmtMoney(Number(v ?? 0))} />
                <ReferenceLine
                  y={limit}
                  stroke={STATUS_HEX.error}
                  strokeDasharray="4 4"
                  label={{ value: 'limit', fill: STATUS_HEX.error, fontSize: 11, position: 'insideTopRight' }}
                />
                <Line type="monotone" dataKey="actual" name="Spent" stroke={CHART_SERIES[0]} dot={false} strokeWidth={2} connectNulls={false} />
                <Line type="monotone" dataKey="forecast" name="Forecast" stroke={CHART_SERIES[3]} dot={false} strokeDasharray="5 4" strokeWidth={2} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </AsyncCard>
  )
}
