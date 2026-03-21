'use client'

import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'
import type { ModelSpend } from '@/types/api'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

const PALETTE = [
  '#14b8a6', '#6366f1', '#8b5cf6', '#06b6d4', '#f97316',
  '#10b981', '#ec4899', '#f59e0b', '#3b82f6', '#ef4444',
]

interface Props { items: ModelSpend[] }

export default function ModelDonutChart({ items }: Props) {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => { setMounted(true) }, [])
  const isDark = mounted && resolvedTheme === 'dark'

  if (items.length === 0) {
    return (
      <div className="flex h-52 items-center justify-center text-sm text-muted-foreground">
        No model data
      </div>
    )
  }

  const total = items.reduce((s, m) => s + parseFloat(m.cost_usd), 0)
  const data = items.slice(0, 8).map(m => ({
    name: m.model,
    value: parseFloat(m.cost_usd),
    pct: total > 0 ? (parseFloat(m.cost_usd) / total * 100).toFixed(1) : '0',
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="45%"
          innerRadius="52%"
          outerRadius="78%"
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} stroke="transparent" />
          ))}
        </Pie>
        <Tooltip
          formatter={(v: unknown) => [`$${((v as number) ?? 0).toFixed(6)}`, 'Spend']}
          contentStyle={{
            backgroundColor: isDark ? '#0f172a' : '#ffffff',
            border: `1px solid ${isDark ? '#1e293b' : '#e2e8f0'}`,
            borderRadius: 10,
            fontSize: 12,
          }}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(value: unknown, entry: unknown) => {
            const label = String(value)
            const pct = (entry as { payload?: { pct?: string } })?.payload?.pct
            return (
              <span style={{ fontSize: 11, color: isDark ? '#94a3b8' : '#64748b' }}>
                {label.length > 16 ? label.slice(0, 14) + '…' : label}
                {pct && <span style={{ marginLeft: 4, opacity: 0.7 }}>{pct}%</span>}
              </span>
            )
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
