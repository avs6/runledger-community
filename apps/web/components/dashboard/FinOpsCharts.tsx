'use client'

export interface SavingsCategoryPoint {
  name: string
  value: number
  color: string
  note: string
}

export interface CostBreakdownPoint {
  name: string
  spend: number
  saved: number
  requests: number
}

export interface HeatmapRow {
  name: string
  values: Record<string, number>
}

function money(value: number) {
  if (!Number.isFinite(value)) return '$0'
  if (Math.abs(value) >= 1) return `$${value.toFixed(2)}`
  if (Math.abs(value) >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

export function SavingsAttributionCards({ data }: { data: SavingsCategoryPoint[] }) {
  const total = data.reduce((sum, item) => sum + item.value, 0)
  if (total <= 0) {
    return <div className="flex h-56 items-center justify-center text-sm text-muted-foreground">No savings attribution yet</div>
  }

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {data.map((item) => {
        const pct = total > 0 ? (item.value / total) * 100 : 0
        return (
          <div key={item.name} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-slate-950">{item.name}</p>
                <p className="mt-1 text-xs text-slate-500">{item.note}</p>
              </div>
              <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={{ backgroundColor: `${item.color}1f`, color: item.color }}>
                {pct.toFixed(0)}%
              </span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full" style={{ width: `${Math.max(pct, 3)}%`, backgroundColor: item.color }} />
            </div>
            <p className="mt-3 font-display text-2xl font-semibold tracking-[-0.04em] text-slate-950">{money(item.value)}</p>
          </div>
        )
      })}
    </div>
  )
}

export function CostBreakdownBars({ data }: { data: CostBreakdownPoint[] }) {
  const max = Math.max(...data.map((item) => item.spend + item.saved), 0)
  if (data.length === 0 || max <= 0) {
    return <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">No cost breakdown yet</div>
  }

  return (
    <div className="space-y-3">
      {data.slice(0, 10).map((item) => {
        const optimizedWidth = max > 0 ? (item.spend / max) * 100 : 0
        const savedWidth = max > 0 ? (item.saved / max) * 100 : 0
        return (
          <div key={item.name} className="rounded-2xl border border-slate-200 bg-white p-3">
            <div className="mb-2 flex items-center justify-between gap-3 text-xs">
              <span className="truncate font-semibold text-slate-800">{item.name}</span>
              <span className="font-mono font-semibold text-slate-900">
                {money(item.spend)} spend / {money(item.saved)} saved
              </span>
            </div>
            <div className="flex h-3 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full bg-blue-500" style={{ width: `${Math.max(optimizedWidth, item.spend > 0 ? 2 : 0)}%` }} />
              <div className="h-full bg-emerald-400" style={{ width: `${Math.max(savedWidth, item.saved > 0 ? 2 : 0)}%` }} />
            </div>
            <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
              <span>{item.requests.toLocaleString()} requests</span>
              <span>blue = actual, green = saved</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function CostHeatmap({ rows, columns }: { rows: HeatmapRow[]; columns: string[] }) {
  const max = Math.max(...rows.flatMap((row) => columns.map((column) => row.values[column] ?? 0)), 0)
  if (rows.length === 0 || max <= 0) {
    return <div className="flex h-56 items-center justify-center text-sm text-muted-foreground">No heatmap spend yet</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-1 text-xs">
        <thead>
          <tr>
            <th className="sticky left-0 bg-white px-2 py-1 text-left font-semibold text-slate-500">Driver</th>
            {columns.map((column) => (
              <th key={column} className="px-2 py-1 text-center font-semibold text-slate-500">{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name}>
              <td className="sticky left-0 max-w-40 truncate bg-white px-2 py-1 font-semibold text-slate-800">{row.name}</td>
              {columns.map((column) => {
                const value = row.values[column] ?? 0
                const intensity = max > 0 ? value / max : 0
                const bg = `rgba(37, 99, 235, ${0.08 + intensity * 0.72})`
                const color = intensity > 0.55 ? 'text-white' : 'text-slate-700'
                return (
                  <td key={column} title={`${row.name} ${column}: ${money(value)}`}>
                    <div className={`rounded-lg px-2 py-2 text-center font-mono font-semibold ${color}`} style={{ backgroundColor: bg }}>
                      {value > 0 ? money(value) : '-'}
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
