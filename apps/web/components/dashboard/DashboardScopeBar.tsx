import Link from 'next/link'

const ranges = [
  { key: '24h', label: '24h' },
  { key: '7d', label: '7d' },
  { key: '30d', label: '30d' },
  { key: '90d', label: '90d' },
] as const

export type DashboardRange = (typeof ranges)[number]['key']

export function getDashboardWindow(range: string | undefined): {
  range: DashboardRange
  from: string
  to: string
  label: string
} {
  const normalized = ranges.some((item) => item.key === range) ? (range as DashboardRange) : '7d'
  const now = new Date()
  const days = normalized === '24h' ? 1 : normalized === '30d' ? 30 : normalized === '90d' ? 90 : 7
  const from = new Date(now.getTime() - days * 24 * 3_600_000)
  return {
    range: normalized,
    from: from.toISOString(),
    to: now.toISOString(),
    label: normalized === '24h' ? 'Last 24 hours' : `Last ${days} days`,
  }
}

export default function DashboardScopeBar({
  scope,
  context,
  activeRange,
  basePath,
  dimensions,
}: {
  scope: 'Platform' | 'Organization' | 'Workspace'
  context: string
  activeRange: DashboardRange
  basePath: string
  dimensions: string[]
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/85 p-3 shadow-sm dark:border-slate-300 dark:bg-[#f2f6fb]/90">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700">
            {scope} scope
          </span>
          <span className="text-sm font-medium text-slate-700">{context}</span>
          <span className="hidden text-slate-300 sm:inline">/</span>
          <span className="text-xs text-slate-500">Filters apply to this dashboard scope only</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Time
          </span>
          <div className="flex rounded-xl bg-slate-100 p-1">
            {ranges.map((range) => (
              <Link
                key={range.key}
                href={`${basePath}${basePath.includes('?') ? '&' : '?'}range=${range.key}`}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeRange === range.key
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {range.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {dimensions.map((dimension) => (
          <span
            key={dimension}
            className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-500"
          >
            {dimension}
          </span>
        ))}
      </div>
    </div>
  )
}
