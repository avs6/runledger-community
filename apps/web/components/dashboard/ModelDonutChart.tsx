'use client'

import { useEffect, useRef, useState } from 'react'
import { useTheme } from 'next-themes'
import type { ModelSpend } from '@/types/api'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import ChartTooltip from './ChartTooltip'
import ChartExportButton from './ChartExportButton'

const PALETTE = [
  '#14b8a6', '#6366f1', '#8b5cf6', '#06b6d4', '#f97316',
  '#10b981', '#ec4899', '#f59e0b', '#3b82f6', '#ef4444',
]

interface Props {
  items: ModelSpend[]
  showExport?: boolean
}

export default function ModelDonutChart({ items, showExport = true }: Props) {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const chartWrapRef = useRef<HTMLDivElement>(null)
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
  const data = items.slice(0, 8).map((m, i) => ({
    name: m.model,
    value: parseFloat(m.cost_usd),
    pct: total > 0 ? (parseFloat(m.cost_usd) / total * 100).toFixed(1) : '0',
    color: PALETTE[i % PALETTE.length],
  }))

  return (
    <div ref={chartWrapRef} className="relative">
      {showExport && (
        <div className="absolute right-0 top-0 z-10">
          <ChartExportButton
            chartRef={chartWrapRef}
            filename="spend-by-model"
            data={items.map(m => ({ model: m.model, provider: m.provider, cost_usd: m.cost_usd, calls: m.call_count }))}
          />
        </div>
      )}
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
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} stroke="transparent" className="cursor-pointer transition-opacity hover:opacity-80" />
            ))}
          </Pie>
          <Tooltip
            content={
              <ChartTooltip
                formatRows={(payload: ReadonlyArray<{ payload?: Record<string, unknown> }>) =>
                  payload.map((p: { payload?: Record<string, unknown> }) => {
                    const entry = p.payload as typeof data[number]
                    return {
                      label: entry.name,
                      value: `$${entry.value.toFixed(6)} (${entry.pct}%)`,
                      color: entry.color,
                    }
                  })
                }
              />
            }
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
    </div>
  )
}
