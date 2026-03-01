'use client'

import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'
import type { SpendOverTime } from '@/types/api'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

interface Props {
  data: SpendOverTime
}

function fmtPeriod(period: string, granularity: string): string {
  const d = new Date(period)
  if (granularity === 'hourly') {
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

export default function SpendOverTimeChart({ data }: Props) {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => { setMounted(true) }, [])

  const isDark = mounted && resolvedTheme === 'dark'
  const gridColor = isDark ? '#374151' : '#e5e7eb'
  const tickColor = isDark ? '#9ca3af' : '#6b7280'
  const tooltipStyle = {
    backgroundColor: isDark ? '#1f2937' : '#ffffff',
    border: `1px solid ${isDark ? '#374151' : '#e5e7eb'}`,
    color: isDark ? '#f3f4f6' : '#111827',
    fontSize: 12,
  }

  if (data.points.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        No data for this period
      </div>
    )
  }

  const chartData = data.points.map((p) => ({
    period: fmtPeriod(p.period, data.granularity),
    cost: parseFloat(p.cost_usd),
  }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
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
          tickFormatter={(v: number) => `$${v.toFixed(3)}`}
          width={60}
        />
        <Tooltip
          formatter={(v: number | undefined) => [`$${(v ?? 0).toFixed(6)}`, 'Cost']}
          labelStyle={{ fontSize: 12, color: isDark ? '#f3f4f6' : '#111827' }}
          contentStyle={tooltipStyle}
        />
        <Line
          type="monotone"
          dataKey="cost"
          stroke="#6366f1"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
