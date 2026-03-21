'use client'

import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'
import type { SpendOverTime } from '@/types/api'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

interface Props {
  data: SpendOverTime
}

function fmtPeriod(period: string, granularity: string) {
  const d = new Date(period)
  if (granularity === 'hourly')
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

export default function DashboardAreaChart({ data }: Props) {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => { setMounted(true) }, [])

  const isDark = mounted && resolvedTheme === 'dark'
  const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'
  const tickColor = isDark ? '#6b7280' : '#9ca3af'
  const tooltipBg = isDark ? '#0f172a' : '#ffffff'
  const tooltipBorder = isDark ? '#1e293b' : '#e2e8f0'

  const chartData = data.points.map(p => ({
    period: fmtPeriod(p.period, data.granularity),
    cost: parseFloat(p.cost_usd),
  }))

  const maxVal = Math.max(...chartData.map(d => d.cost), 0)
  const avgVal = chartData.length ? chartData.reduce((s, d) => s + d.cost, 0) / chartData.length : 0

  if (chartData.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        No spend data for this period
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="dashAreaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#14b8a6" stopOpacity={isDark ? 0.35 : 0.25} />
            <stop offset="95%" stopColor="#14b8a6" stopOpacity={0} />
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
          formatter={(v: unknown) => [`$${((v as number) ?? 0).toFixed(6)}`, 'Spend']}
          labelStyle={{ fontSize: 11, color: isDark ? '#94a3b8' : '#64748b', marginBottom: 4 }}
          contentStyle={{
            backgroundColor: tooltipBg,
            border: `1px solid ${tooltipBorder}`,
            borderRadius: 10,
            fontSize: 12,
            boxShadow: '0 4px 24px rgba(0,0,0,0.12)',
          }}
        />
        {avgVal > 0 && (
          <ReferenceLine
            y={avgVal}
            stroke={isDark ? 'rgba(99,102,241,0.4)' : 'rgba(99,102,241,0.35)'}
            strokeDasharray="4 4"
            label={{ value: 'avg', position: 'right', fontSize: 10, fill: isDark ? '#818cf8' : '#6366f1' }}
          />
        )}
        <Area
          type="monotone"
          dataKey="cost"
          stroke="#14b8a6"
          strokeWidth={2.5}
          fill="url(#dashAreaGrad)"
          dot={false}
          activeDot={{ r: 5, strokeWidth: 0, fill: '#14b8a6' }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
