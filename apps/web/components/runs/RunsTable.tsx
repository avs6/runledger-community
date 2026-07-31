'use client'

import { useRef, useState, useCallback } from 'react'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { XCircle } from 'lucide-react'
import type { RunListItem } from '@/types/api'
import RunStatusBadge from './RunStatusBadge'
import { formatCost, formatTokens, formatDuration, formatAge, formatTimestamp } from '@/lib/utils'
import { modelColor } from '@/lib/modelColors'

const DEFAULT_WIDTHS = [240, 120, 120, 150, 190, 100, 100, 95, 160]

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
      setWidths(prev => {
        const w = [...prev]
        w[col] = next
        return w
      })
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
      setCancelling(prev => {
        const s = new Set(prev)
        s.delete(runId)
        return s
      })
    }
  }

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white/70 py-16 text-center text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-400">
        No runs found.
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white/95 shadow-sm ring-1 ring-white/70 dark:border-slate-700 dark:bg-slate-900/80 dark:ring-slate-800">
      <div className="overflow-x-auto">
        <table className="w-full min-w-max border-collapse text-sm" style={{ tableLayout: 'fixed' }}>
          <colgroup>
            {widths.map((w, i) => <col key={i} style={{ width: w }} />)}
          </colgroup>
          <thead className="sticky top-0 z-10">
            <tr className="border-b border-slate-200 bg-slate-50/95 backdrop-blur dark:border-slate-700 dark:bg-slate-900/95">
              {HEADERS.map((h, i) => (
                <th
                  key={h}
                  className={`relative select-none py-2.5 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400 ${i >= 5 ? 'text-right pr-4' : 'text-left pl-4'}`}
                >
                  {h}
                  {i < HEADERS.length - 1 && (
                    <span
                      onMouseDown={e => onMouseDown(i, e)}
                      className="absolute right-0 top-0 h-full w-1 cursor-col-resize bg-transparent hover:bg-blue-400/40 dark:hover:bg-blue-500/30"
                    />
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {items.map((run) => {
              const isCancelled = cancelledIds.has(run.id)
              const effectiveStatus = isCancelled ? 'cancelled' : run.status
              const isRunning = effectiveStatus === 'running'
              const totalTokens = (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0)
              const color = modelColor(run.primary_model)

              return (
                <tr
                  key={run.id}
                  className="group transition-colors hover:bg-blue-50/55 dark:hover:bg-slate-800/70"
                >
                  <td className="py-2 pl-4 pr-2 font-mono text-[11px]">
                    <Link
                      href={`/runs/${run.id}`}
                      title={run.id}
                      className="block truncate font-semibold text-blue-700 underline-offset-2 hover:underline dark:text-blue-300"
                    >
                      {run.id}
                    </Link>
                  </td>
                  <td className="py-2 pl-4">
                    <div className="flex items-center gap-1.5">
                      <RunStatusBadge status={effectiveStatus} />
                      {isRunning && (
                        <button
                          onClick={() => handleCancel(run.id)}
                          disabled={cancelling.has(run.id)}
                          title="Cancel stuck run"
                          className="flex items-center gap-0.5 rounded px-1 py-0.5 text-[10px] font-medium text-red-500 transition-colors hover:bg-red-50 hover:text-red-700 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-900/20"
                        >
                          <XCircle className="h-3 w-3" />
                          {cancelling.has(run.id) ? '...' : 'Cancel'}
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="truncate py-2 pl-4 pr-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                    {run.end_user_id ?? '-'}
                  </td>
                  <td className="py-2 pl-4 pr-2">
                    <span className="inline-flex max-w-full items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      <span className="truncate">{run.feature_tag ?? '-'}</span>
                    </span>
                  </td>
                  <td className="py-2 pl-4 pr-2">
                    <span
                      className="inline-flex max-w-full items-center gap-1.5 rounded-full border bg-white px-2 py-0.5 font-mono text-[11px] font-semibold text-slate-700 shadow-sm dark:bg-slate-950 dark:text-slate-200"
                      style={{ borderColor: `${color}55`, boxShadow: `inset 3px 0 0 ${color}` }}
                      title={run.primary_model ?? undefined}
                    >
                      <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
                      <span className="truncate">{run.primary_model ?? '-'}</span>
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-right font-mono text-[11px] font-semibold text-slate-900 dark:text-slate-100">
                    {formatCost(run.total_cost_usd)}
                  </td>
                  <td className="py-2 pr-4 text-right font-mono text-[11px] text-slate-700 dark:text-slate-300">
                    {formatTokens(totalTokens)}
                  </td>
                  <td className="py-2 pr-4 text-right font-mono text-[11px] text-slate-500 dark:text-slate-400">
                    {formatDuration(run.duration_ms)}
                  </td>
                  <td className="py-2 pr-4 text-right text-[11px] text-slate-500 dark:text-slate-400">
                    {run.started_at ? (
                      <span title={formatAge(run.started_at)}>
                        {formatTimestamp(run.started_at)}
                      </span>
                    ) : '-'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
