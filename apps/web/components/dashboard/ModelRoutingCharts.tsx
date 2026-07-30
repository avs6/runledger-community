'use client'

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export interface ModelTimelinePoint {
  period: string
  [key: string]: string | number
}

export interface ModelTimelineDetail {
  inputTokens: number
  outputTokens: number
  cost: number
  cacheSavings: number
  latencyMs: number | null
  outcomeRate: number
}

export interface RoutingSlice {
  name: string
  value: number
  color: string
}

export interface QualityCostPoint {
  model: string
  cost: number
  latency: number
  quality: number
}

function money(value: number) {
  if (!Number.isFinite(value)) return '$0'
  if (Math.abs(value) >= 1) return `$${value.toFixed(2)}`
  if (Math.abs(value) >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

function formatLatency(ms: number | null) {
  if (ms === null || !Number.isFinite(ms)) return 'n/a'
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.round(ms)}ms`
}

export function StackedResourceTimeline({
  data,
  keys,
  colors,
  details,
}: {
  data: ModelTimelinePoint[]
  keys: string[]
  colors: Record<string, string>
  details?: Record<string, Record<string, ModelTimelineDetail>>
}) {
  if (data.length === 0 || keys.length === 0) {
    return <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">No model usage trend yet</div>
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="rgba(15,23,42,0.06)" vertical={false} />
        <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v}%`} width={44} />
        <Tooltip
          content={({ active, label, payload }) => {
            if (!active || !payload?.length) return null
            const periodDetails = details?.[String(label)] ?? {}
            return (
              <div className="min-w-72 rounded-2xl border border-slate-200 bg-white p-3 text-xs shadow-xl">
                <div className="mb-2 font-semibold text-slate-950">{String(label)}</div>
                <div className="space-y-2">
                  {payload
                    .filter((entry) => Number(entry.value) > 0)
                    .map((entry) => {
                      const name = String(entry.name ?? '')
                      const detail = periodDetails[name]
                      return (
                        <div key={name} className="rounded-xl bg-slate-50 p-2">
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-semibold text-slate-700">{name}</span>
                            <span className="font-mono font-semibold text-slate-950">{Number(entry.value).toFixed(1)}%</span>
                          </div>
                          {detail && (
                            <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1 text-slate-500">
                              <span>Input: {detail.inputTokens.toLocaleString()}</span>
                              <span>Output: {detail.outputTokens.toLocaleString()}</span>
                              <span>Cost: {money(detail.cost)}</span>
                              <span>Cache saved: {money(detail.cacheSavings)}</span>
                              <span>Latency: {formatLatency(detail.latencyMs)}</span>
                              <span>Outcome: {detail.outcomeRate.toFixed(0)}%</span>
                            </div>
                          )}
                        </div>
                      )
                    })}
                </div>
              </div>
            )
          }}
          contentStyle={{ borderRadius: 12, border: '1px solid #dbe3ee', boxShadow: '0 10px 30px rgba(15,23,42,0.12)' }}
        />
        {keys.map((key) => (
          <Bar key={key} dataKey={key} stackId="models" fill={colors[key] ?? '#64748b'} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

export function RoutingDistribution({ data }: { data: RoutingSlice[] }) {
  const total = data.reduce((sum, item) => sum + item.value, 0)
  if (total <= 0) {
    return <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">No routing distribution yet</div>
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[240px_1fr] lg:items-center">
      <ResponsiveContainer width="100%" height={230}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={58} outerRadius={92} paddingAngle={2}>
            {data.map((slice) => (
              <Cell key={slice.name} fill={slice.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value: unknown) => `${Number(value).toLocaleString()} requests`} />
        </PieChart>
      </ResponsiveContainer>
      <div className="space-y-3">
        {data.map((slice) => {
          const pct = total > 0 ? (slice.value / total) * 100 : 0
          return (
            <div key={slice.name}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="flex items-center gap-2 font-medium text-slate-700">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: slice.color }} />
                  {slice.name}
                </span>
                <span className="font-mono font-semibold text-slate-900">{pct.toFixed(0)}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full" style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: slice.color }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function ModelQualityCostBars({ data }: { data: QualityCostPoint[] }) {
  if (data.length === 0) {
    return <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">No model comparison data yet</div>
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 18, left: 8, bottom: 0 }}>
        <CartesianGrid stroke="rgba(15,23,42,0.06)" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} tickFormatter={money} />
        <YAxis type="category" dataKey="model" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} width={140} />
        <Tooltip
          formatter={(value: unknown, name: unknown) => [name === 'latency' ? `${Number(value).toFixed(0)}ms` : money(Number(value)), String(name ?? '')]}
          contentStyle={{ borderRadius: 12, border: '1px solid #dbe3ee', boxShadow: '0 10px 30px rgba(15,23,42,0.12)' }}
        />
        <Bar dataKey="cost" fill="#2563eb" radius={[0, 8, 8, 0]} maxBarSize={20} name="cost" />
      </BarChart>
    </ResponsiveContainer>
  )
}
