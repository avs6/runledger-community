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
