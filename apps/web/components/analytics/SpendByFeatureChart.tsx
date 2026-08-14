'use client'

import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'
import type { FeatureSpend } from '@/types/api'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { ValueType } from 'recharts/types/component/DefaultTooltipContent'

const COLORS = [
  '#6366f1',
  '#8b5cf6',
  '#a78bfa',
  '#c4b5fd',
  '#818cf8',
  '#4f46e5',
  '#7c3aed',
  '#6d28d9',
]

interface Props {
  items: FeatureSpend[]
}

function valueToNumber(value: ValueType | undefined): number | null {
  if (typeof value === 'number') return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  if (Array.isArray(value) && value.length > 0) {
    return valueToNumber(value[0])
  }
  return null
}

export default function SpendByFeatureChart({ items }: Props) {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => { setMounted(true) }, [])

  const isDark = mounted && resolvedTheme === 'dark'
  const tooltipStyle = {
    backgroundColor: isDark ? '#1f2937' : '#ffffff',
    border: `1px solid ${isDark ? '#374151' : '#e5e7eb'}`,
    color: isDark ? '#f3f4f6' : '#111827',
    fontSize: 12,
  }
  const legendColor = isDark ? '#9ca3af' : '#6b7280'

  if (items.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        No data for this period
      </div>
    )
  }

  const chartData = items.map((f) => ({
    name: f.feature_tag ?? '(untagged)',
    value: parseFloat(f.cost_usd),
  }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          dataKey="value"
          paddingAngle={2}
        >
          {chartData.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => {
            const numeric = valueToNumber(value) ?? 0
            return [`$${numeric.toFixed(6)}`, 'Cost']
          }}
          contentStyle={tooltipStyle}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: legendColor }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
