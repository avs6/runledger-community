'use client'

import { useEffect, useRef, useState } from 'react'
import { useTheme } from 'next-themes'
import type { SpendOverTime } from '@/types/api'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Brush,
} from 'recharts'
import ChartTooltip from './ChartTooltip'
import ChartExportButton from './ChartExportButton'

interface Props {
  data: SpendOverTime
  showExport?: boolean
}

function fmtPeriod(period: string, granularity: string) {
  const d = new Date(period)
  if (granularity === 'hourly')
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

export default function DashboardAreaChart({ data, showExport = true }: Props) {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const chartWrapRef = useRef<HTMLDivElement>(null)
  useEffect(() => { setMounted(true) }, [])

  const isDark = mounted && resolvedTheme === 'dark'
  const gridColor = isDark ? 'rgba(71,85,105,0.14)' : 'rgba(0,0,0,0.05)'
  const tickColor = isDark ? '#64748b' : '#9ca3af'

  const chartData = data.points.map(p => ({
    period: fmtPeriod(p.period, data.granularity),
    cost: parseFloat(p.cost_usd),
  }))

  const avgVal = chartData.length ? chartData.reduce((s, d) => s + d.cost, 0) / chartData.length : 0

  if (chartData.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        No spend data for this period
      </div>
    )
  }

  return (
    <div ref={chartWrapRef} className="relative">
      {showExport && (
        <div className="absolute right-2 top-0 z-10">
          <ChartExportButton
            chartRef={chartWrapRef}
            filename="spend-over-time"
            data={chartData}
          />
        </div>
      )}
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="dashAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563eb" stopOpacity={isDark ? 0.20 : 0.25} />
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="0" stroke={gridColor} vertical={false} />
          <XAxis
            dataKey="period"
            tick={{ fontSize: 11, fill: tickColor }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: tickColor }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => v >= 1 ? `$${v.toFixed(2)}` : `$${v.toFixed(4)}`}
            width={64}
          />
          <Tooltip
            content={
              <ChartTooltip
                formatRows={(payload: ReadonlyArray<{ value?: number }>) =>
                  payload.map((p: { value?: number }) => ({
                    label: 'Spend',
                    value: `$${(p.value ?? 0).toFixed(6)}`,
                    color: '#2563eb',
                  }))
                }
              />
            }
          />
          {avgVal > 0 && (
            <ReferenceLine
              y={avgVal}
              stroke={isDark ? 'rgba(37,99,235,0.35)' : 'rgba(99,102,241,0.35)'}
              strokeDasharray="4 4"
              label={{ value: 'avg', position: 'right', fontSize: 10, fill: isDark ? '#2563eb' : '#6366f1' }}
            />
          )}
          <Area
            type="monotone"
            dataKey="cost"
            stroke="#2563eb"
            strokeWidth={2.5}
            fill="url(#dashAreaGrad)"
            dot={false}
            activeDot={{ r: 5, strokeWidth: 2, fill: '#2563eb', stroke: '#fff' }}
          />
          {chartData.length > 14 && (
            <Brush
              dataKey="period"
              height={28}
              stroke="#94a3b8"
              fill={isDark ? '#f1f5f9' : '#f8fafc'}
              travellerWidth={8}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
