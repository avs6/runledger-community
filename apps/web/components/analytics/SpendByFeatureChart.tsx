'use client'

import type { FeatureSpend } from '@/types/api'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

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

export default function SpendByFeatureChart({ items }: Props) {
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
          formatter={(v: number | undefined) => [`$${(v ?? 0).toFixed(6)}`, 'Cost']}
          contentStyle={{ fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
