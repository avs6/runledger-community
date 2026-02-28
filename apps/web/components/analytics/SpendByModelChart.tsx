'use client'

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
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => `$${v.toFixed(3)}`}
        />
        <YAxis
          type="category"
          dataKey="model"
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={120}
        />
        <Tooltip
          formatter={(v: number | undefined) => [`$${(v ?? 0).toFixed(6)}`, undefined]}
          contentStyle={{ fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="input" name="Input" stackId="a" fill="#6366f1" />
        <Bar dataKey="output" name="Output" stackId="a" fill="#a5b4fc" />
      </BarChart>
    </ResponsiveContainer>
  )
}
