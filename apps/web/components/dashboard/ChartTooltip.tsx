'use client'

import type { Props as DefaultTooltipContentProps, Payload, NameType, ValueType } from 'recharts/types/component/DefaultTooltipContent'

type Row = {
  label: string
  value: string
  color?: string
}

interface ChartTooltipProps<TValue extends ValueType = number, TName extends NameType = string>
  extends DefaultTooltipContentProps<TValue, TName> {
  formatRows?: (payload: ReadonlyArray<Payload<TValue, TName>>) => Row[]
}

export default function ChartTooltip<TValue extends ValueType = number, TName extends NameType = string>({
  payload,
  label,
  formatRows,
}: ChartTooltipProps<TValue, TName>) {
  if (!payload?.length) return null

  const rows: Row[] = formatRows
    ? formatRows(payload)
    : payload.map((p: Payload<TValue, TName>) => ({
        label: String(p.name ?? ''),
        value: typeof p.value === 'number'
          ? p.value >= 1 ? `$${p.value.toFixed(2)}` : `$${p.value.toFixed(6)}`
          : String(p.value ?? ''),
        color: typeof p.color === 'string' ? p.color : undefined,
      }))

  return (
    <div className="rounded-xl border border-slate-200 bg-white/95 px-3.5 py-2.5 shadow-xl backdrop-blur-sm dark:border-slate-300 dark:bg-[#f0f4f8]/95">
      {label && (
        <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          {String(label)}
        </p>
      )}
      <div className="space-y-1">
        {rows.map((row, i) => (
          <div key={i} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-xs text-slate-600">
              {row.color && <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: row.color }} />}
              {row.label}
            </span>
            <span className="text-xs font-semibold tabular-nums text-slate-900">{row.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
