'use client'

import { useEffect, useRef, useState } from 'react'
import { useTheme } from 'next-themes'
import type { FeatureSpend } from '@/types/api'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import ChartTooltip from './ChartTooltip'
import ChartExportButton from './ChartExportButton'

const PALETTE = ['#14b8a6', '#6366f1', '#8b5cf6', '#06b6d4', '#f97316', '#10b981', '#ec4899', '#f59e0b']

interface Props {
  items: FeatureSpend[]
  showExport?: boolean
}

export default function FeatureBarsChart({ items, showExport = true }: Props) {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const chartWrapRef = useRef<HTMLDivElement>(null)
  useEffect(() => { setMounted(true) }, [])
  const isDark = mounted && resolvedTheme === 'dark'

  if (items.length === 0) {
    return (
      <div className="flex h-52 items-center justify-center text-sm text-muted-foreground">
        No feature data
      </div>
    )
  }

  const data = items.slice(0, 8).map((f, i) => ({
    name: f.feature_tag ?? '(untagged)',
    cost: parseFloat(f.cost_usd),
    runs: f.run_count,
    color: PALETTE[i % PALETTE.length],
  }))

  const tickColor = isDark ? '#6b7280' : '#9ca3af'
  const gridColor = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)'

  return (
    <div ref={chartWrapRef} className="relative">
      {showExport && (
        <div className="absolute right-0 top-0 z-10">
          <ChartExportButton
            chartRef={chartWrapRef}
            filename="spend-by-feature"
            data={items.map(f => ({ feature: f.feature_tag, cost_usd: f.cost_usd, runs: f.run_count }))}
          />
        </div>
      )}
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 0, right: 16, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="0" stroke={gridColor} horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 10, fill: tickColor }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => v >= 0.01 ? `$${v.toFixed(2)}` : `$${v.toFixed(4)}`}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: tickColor }}
            tickLine={false}
            axisLine={false}
            width={96}
          />
          <Tooltip
            content={
              <ChartTooltip
                formatRows={(payload: ReadonlyArray<{ payload?: Record<string, unknown> }>) =>
                  payload.map((p: { payload?: Record<string, unknown> }) => {
                    const entry = p.payload as typeof data[number]
                    return {
                      label: entry.name,
                      value: `$${entry.cost.toFixed(6)} · ${entry.runs} runs`,
                      color: entry.color,
                    }
                  })
                }
              />
            }
          />
          <Bar dataKey="cost" radius={[0, 4, 4, 0]} maxBarSize={18}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} className="cursor-pointer transition-opacity hover:opacity-80" />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
