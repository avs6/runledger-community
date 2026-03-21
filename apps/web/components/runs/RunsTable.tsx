'use client'

import { useRef, useState, useCallback } from 'react'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { XCircle } from 'lucide-react'
import type { RunListItem } from '@/types/api'
import RunStatusBadge from './RunStatusBadge'
import { formatCost, formatTokens, formatDuration, formatAge, formatTimestamp } from '@/lib/utils'

// Default column widths in px
const DEFAULT_WIDTHS = [200, 130, 140, 140, 180, 90, 90, 90, 130]

const HEADERS = [
  'Run ID', 'Status', 'End User', 'Feature', 'Model',
  'Cost', 'Tokens', 'Duration', 'Started',
]

const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function RunsTable({ items }: { items: RunListItem[] }) {
  const { data: session } = useSession()
  const apiKey = (session as Record<string, unknown> | null)?.apiKey as string | undefined

  const [widths, setWidths] = useState<number[]>(DEFAULT_WIDTHS)
  const dragging = useRef<{ col: number; startX: number; startW: number } | null>(null)
  const [cancelledIds, setCancelledIds] = useState<Set<string>>(new Set())
  const [cancelling, setCancelling] = useState<Set<string>>(new Set())

  const onMouseDown = useCallback((col: number, e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = { col, startX: e.clientX, startW: widths[col] }

    function onMove(mv: MouseEvent) {
      if (!dragging.current) return
      const { col, startX, startW } = dragging.current
      const delta = mv.clientX - startX
      const next = Math.max(60, startW + delta)
      setWidths(prev => { const w = [...prev]; w[col] = next; return w })
    }
    function onUp() {
      dragging.current = null
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [widths])

  async function handleCancel(runId: string) {
    if (!apiKey || cancelling.has(runId)) return
    setCancelling(prev => new Set(prev).add(runId))
    try {
      const resp = await fetch(`${apiBase}/runs/${runId}/cancel`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${apiKey}` },
      })
      if (resp.ok) {
        setCancelledIds(prev => new Set(prev).add(runId))
      }
    } finally {
      setCancelling(prev => { const s = new Set(prev); s.delete(runId); return s })
    }
  }

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-200 py-16 text-center text-sm text-gray-400 dark:border-gray-700 dark:text-gray-500">
        No runs found.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      <table className="w-full min-w-max border-collapse text-sm" style={{ tableLayout: 'fixed' }}>
        <colgroup>
          {widths.map((w, i) => <col key={i} style={{ width: w }} />)}
        </colgroup>
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            {HEADERS.map((h, i) => (
              <th
                key={h}
                className={`relative select-none py-2.5 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 ${i >= 5 ? 'text-right pr-4' : 'text-left pl-4'}`}
              >
                {h}
                {/* Drag handle — not on last column */}
                {i < HEADERS.length - 1 && (
                  <span
                    onMouseDown={e => onMouseDown(i, e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize bg-transparent hover:bg-teal-400/40 dark:hover:bg-teal-500/30"
                  />
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((run) => {
            const isCancelled = cancelledIds.has(run.id)
            const effectiveStatus = isCancelled ? 'cancelled' : run.status
            const isRunning = effectiveStatus === 'running'

            return (
              <tr
                key={run.id}
                className="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
              >
                {/* Run ID — full UUID, monospace, link */}
                <td className="py-2.5 pl-4 pr-2 font-mono text-xs">
                  <Link
                    href={`/runs/${run.id}`}
                    title={run.id}
                    className="block truncate text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    {run.id}
                  </Link>
                </td>
                <td className="py-2.5 pl-4">
                  <div className="flex items-center gap-1.5">
                    <RunStatusBadge status={effectiveStatus} />
                    {isRunning && (
                      <button
                        onClick={() => handleCancel(run.id)}
                        disabled={cancelling.has(run.id)}
                        title="Cancel stuck run"
                        className="flex items-center gap-0.5 rounded px-1 py-0.5 text-[10px] font-medium text-red-500 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:hover:bg-red-900/20 disabled:opacity-50 transition-colors"
                      >
                        <XCircle className="h-3 w-3" />
                        {cancelling.has(run.id) ? '…' : 'Cancel'}
                      </button>
                    )}
                  </div>
                </td>
                <td className="truncate py-2.5 pl-4 pr-2 text-xs text-gray-600 dark:text-gray-400">
                  {run.end_user_id ?? '—'}
                </td>
                <td className="truncate py-2.5 pl-4 pr-2 text-xs text-gray-600 dark:text-gray-400">
                  {run.feature_tag ?? '—'}
                </td>
                <td className="truncate py-2.5 pl-4 pr-2 font-mono text-xs text-gray-500 dark:text-gray-400">
                  {run.primary_model ?? '—'}
                </td>
                <td className="py-2.5 pr-4 text-right font-mono text-xs text-gray-900 dark:text-gray-100">
                  {formatCost(run.total_cost_usd)}
                </td>
                <td className="py-2.5 pr-4 text-right font-mono text-xs text-gray-900 dark:text-gray-100">
                  {formatTokens((run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0))}
                </td>
                <td className="py-2.5 pr-4 text-right text-xs text-gray-500 dark:text-gray-400">
                  {formatDuration(run.duration_ms)}
                </td>
                <td className="py-2.5 pr-4 text-right text-xs text-gray-400 dark:text-gray-500">
                  {run.started_at ? (
                    <span title={formatAge(run.started_at)}>
                      {formatTimestamp(run.started_at)}
                    </span>
                  ) : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
