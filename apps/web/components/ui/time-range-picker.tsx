'use client'

export const TIME_RANGES = ['1h', '24h', '7d', '30d', '90d'] as const
export type TimeRange = (typeof TIME_RANGES)[number]

const RANGE_MS: Record<TimeRange, number> = {
  '1h': 3_600_000,
  '24h': 86_400_000,
  '7d': 7 * 86_400_000,
  '30d': 30 * 86_400_000,
  '90d': 90 * 86_400_000,
}

/** `from`/`to` ISO timestamps for a preset range ending now (the `from`/`to` params most list endpoints take). */
export function rangeToWindow(range: TimeRange, now = Date.now()): { from: string; to: string } {
  return { from: new Date(now - RANGE_MS[range]).toISOString(), to: new Date(now).toISOString() }
}

/** Segmented preset picker for time windows. Pair with URL state so the range survives reloads. */
export function TimeRangePicker({
  value,
  onChange,
  ranges = TIME_RANGES,
  label = 'Time range',
}: {
  value: TimeRange
  onChange: (range: TimeRange) => void
  ranges?: readonly TimeRange[]
  label?: string
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-lg border border-slate-200 p-0.5 dark:border-slate-700">
      {ranges.map((r) => (
        <button
          key={r}
          type="button"
          role="radio"
          aria-checked={value === r}
          onClick={() => onChange(r)}
          className={`rounded-md px-2.5 py-1 text-xs font-medium ${value === r ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800'}`}
        >
          {r}
        </button>
      ))}
    </div>
  )
}
