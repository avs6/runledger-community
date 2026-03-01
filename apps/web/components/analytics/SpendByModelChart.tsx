'use client'

import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'
import type { ModelSpend } from '@/types/api'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

interface Props {
  items: ModelSpend[]
}

export default function SpendByModelChart({ items }: Props) {
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

  if (items.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        No data for this period
      </div>
    )
  }

  const chartData = items.slice(0, 10).map((m) => ({
    model: m.model,
    input: parseFloat(m.cost_usd) * (m.input_tokens / (m.input_tokens + m.output_tokens || 1)),
    output: parseFloat(m.cost_usd) * (m.output_tokens / (m.input_tokens + m.output_tokens || 1)),
  }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart
        layout="vertical"
        data={chartData}
        margin={{ top: 4, right: 16, left: 8, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: tickColor }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => `$${v.toFixed(3)}`}
        />
        <YAxis
          type="category"
          dataKey="model"
          tick={{ fontSize: 11, fill: tickColor }}
          tickLine={false}
          axisLine={false}
          width={120}
        />
        <Tooltip
          formatter={(v: number | undefined) => [`$${(v ?? 0).toFixed(6)}`, undefined]}
          contentStyle={tooltipStyle}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: tickColor }} />
        <Bar dataKey="input" name="Input" stackId="a" fill="#6366f1" />
        <Bar dataKey="output" name="Output" stackId="a" fill="#a5b4fc" />
      </BarChart>
    </ResponsiveContainer>
  )
}
