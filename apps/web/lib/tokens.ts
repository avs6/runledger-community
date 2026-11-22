/**
 * Design tokens for places that need literal colour values (chart libraries set SVG
 * attributes, where CSS variables aren't resolved). Everywhere else, use the Tailwind
 * tokens (`text-status-error`, `bg-severity-high`, `text-scope-workspace`, …) backed by the
 * CSS variables in app/globals.css. This is the only file where raw hex is allowed
 * (eslint: no-restricted-syntax).
 */

/** Categorical series colours for charts, in order. */
export const CHART_SERIES = [
  '#6366f1', // indigo
  '#0ea5e9', // sky
  '#10b981', // emerald
  '#f59e0b', // amber
  '#f43f5e', // rose
  '#8b5cf6', // violet
  '#14b8a6', // teal
  '#64748b', // slate
] as const

/** Chart chrome: axes, grid lines and muted labels. */
export const CHART_UI = {
  axis: '#94a3b8',
  grid: '#e2e8f0',
  gridDark: '#334155',
  label: '#64748b',
} as const

/** Status colours matching the --status-* CSS variables (light theme). */
export const STATUS_HEX = {
  success: '#0f8a5f',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#2563eb',
  neutral: '#64748b',
} as const

/** Series colour for index `i`, cycling through CHART_SERIES. */
export function seriesColor(i: number): string {
  return CHART_SERIES[((i % CHART_SERIES.length) + CHART_SERIES.length) % CHART_SERIES.length]
}
