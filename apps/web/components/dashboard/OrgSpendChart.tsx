'use client'

import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'
import type { OrgDashboardWorkspace } from '@/types/api'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const PALETTE = ['#14b8a6', '#6366f1', '#8b5cf6', '#06b6d4', '#f97316', '#10b981', '#ec4899', '#f59e0b']

interface Props { workspaces: OrgDashboardWorkspace[] }

export default function OrgSpendChart({ workspaces }: Props) {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => { setMounted(true) }, [])
  const isDark = mounted && resolvedTheme === 'dark'

  const data = workspaces
    .slice(0, 10)
    .map(ws => ({ name: ws.name, cost: parseFloat(ws.cost_usd) || 0 }))
    .filter(d => d.cost > 0)

  if (data.length === 0) {
    return (
      <div className="flex h-52 items-center justify-center text-sm text-muted-foreground">
        No spend data yet
      </div>
    )
  }

  const tickColor = isDark ? '#6b7280' : '#9ca3af'
  const gridColor = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)'

  return (
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
          formatter={(v: unknown) => [`$${((v as number) ?? 0).toFixed(6)}`, 'Spend']}
          contentStyle={{
            backgroundColor: isDark ? '#0f172a' : '#ffffff',
            border: `1px solid ${isDark ? '#1e293b' : '#e2e8f0'}`,
            borderRadius: 10,
            fontSize: 12,
          }}
        />
        <Bar dataKey="cost" radius={[0, 4, 4, 0]} maxBarSize={18}>
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
