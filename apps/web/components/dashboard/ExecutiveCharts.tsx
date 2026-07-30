'use client'

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export interface ExecutiveTrendPoint {
  period: string
  projected: number
  actual: number
  optimized: number
}

export interface ExecutiveWaterfallPoint {
  name: string
  value: number
  kind: 'start' | 'saving' | 'end'
}

export interface ExecutiveSavingsPoint {
  name: string
  value: number
  color: string
}

function money(value: number) {
  if (!Number.isFinite(value)) return '$0'
  if (Math.abs(value) >= 1) return `$${value.toFixed(2)}`
  if (Math.abs(value) >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

export function ExecutiveTrendChart({ data }: { data: ExecutiveTrendPoint[] }) {
  if (data.length === 0) {
    return <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">No trend data for this period</div>
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 12, right: 18, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="executiveActual" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2563eb" stopOpacity={0.22} />
            <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="executiveOptimized" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#059669" stopOpacity={0.18} />
            <stop offset="95%" stopColor="#059669" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(15,23,42,0.06)" vertical={false} />
        <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={money} width={70} />
        <Tooltip
          formatter={(value: unknown, name: unknown) => [money(Number(value)), String(name ?? '')]}
          contentStyle={{ borderRadius: 12, border: '1px solid #dbe3ee', boxShadow: '0 10px 30px rgba(15,23,42,0.12)' }}
        />
        <Area type="monotone" dataKey="projected" stroke="#94a3b8" strokeDasharray="5 5" strokeWidth={2} fill="transparent" name="Projected" />
        <Area type="monotone" dataKey="actual" stroke="#2563eb" strokeWidth={2.5} fill="url(#executiveActual)" name="Actual" />
        <Area type="monotone" dataKey="optimized" stroke="#059669" strokeWidth={2.5} fill="url(#executiveOptimized)" name="Optimized" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function ExecutiveWaterfallChart({ data }: { data: ExecutiveWaterfallPoint[] }) {
  if (data.length === 0) {
    return <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">No savings waterfall yet</div>
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 14, right: 14, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="rgba(15,23,42,0.06)" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={money} width={70} />
        <Tooltip
          formatter={(value: unknown) => money(Number(value))}
          contentStyle={{ borderRadius: 12, border: '1px solid #dbe3ee', boxShadow: '0 10px 30px rgba(15,23,42,0.12)' }}
        />
        <Bar dataKey="value" radius={[8, 8, 0, 0]}>
          {data.map((point) => (
            <Cell
              key={point.name}
              fill={point.kind === 'saving' ? '#10b981' : point.kind === 'end' ? '#2563eb' : '#64748b'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function ExecutiveSavingsBars({ data }: { data: ExecutiveSavingsPoint[] }) {
  const total = data.reduce((sum, point) => sum + point.value, 0)
  if (total <= 0) {
    return <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">No savings attribution captured yet</div>
  }

  return (
    <div className="space-y-4">
      {data.map((point) => {
        const width = Math.max((point.value / total) * 100, 3)
        return (
          <div key={point.name}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="font-medium text-slate-700">{point.name}</span>
              <span className="font-mono font-semibold text-slate-900">{money(point.value)}</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full" style={{ width: `${width}%`, backgroundColor: point.color }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
