import CopyId from '@/components/observe/CopyId'
import { formatCost, formatDuration } from '@/lib/utils'
import type { ProviderCallDetail, SpanDetail } from '@/types/api'

const TYPE_BAR: Record<string, string> = {
  llm: 'bg-violet-500',
  chain: 'bg-indigo-500',
  tool: 'bg-amber-500',
  agent: 'bg-sky-500',
  retrieval: 'bg-cyan-500',
}

interface Row {
  span: SpanDetail
  depth: number
}

/** Order spans parent-first (depth-first by start time) so the waterfall reads as a tree. */
function orderSpans(spans: SpanDetail[]): Row[] {
  const byParent = new Map<string | null, SpanDetail[]>()
  const ids = new Set(spans.map(s => s.id))
  for (const s of spans) {
    const parent = s.parent_span_id && ids.has(s.parent_span_id) ? s.parent_span_id : null
    const list = byParent.get(parent) ?? []
    list.push(s)
    byParent.set(parent, list)
  }
  byParent.forEach(list => list.sort((a, b) => a.started_at.localeCompare(b.started_at)))
  const out: Row[] = []
  const walk = (parent: string | null, depth: number) => {
    for (const s of byParent.get(parent) ?? []) {
      out.push({ span: s, depth })
      walk(s.id, depth + 1)
    }
  }
  walk(null, 0)
  return out
}

/**
 * Trace waterfall: one bar per span on a shared time axis, nested by parent, with the
 * provider call (model, latency) and copyable span ids.
 */
export default function TraceWaterfall({
  runId,
  startedAt,
  endedAt,
  spans,
  calls,
}: {
  runId: string
  startedAt: string
  endedAt: string | null
  spans: SpanDetail[]
  calls: ProviderCallDetail[]
}) {
  if (spans.length === 0) {
    return <p className="py-4 text-center text-sm text-muted-foreground">No spans recorded for this run.</p>
  }
  const t0 = new Date(startedAt).getTime()
  const ends = spans.map(s => new Date(s.ended_at ?? s.started_at).getTime())
  const tEnd = Math.max(endedAt ? new Date(endedAt).getTime() : t0, ...ends, t0 + 1)
  const total = tEnd - t0
  const callBySpan = new Map(calls.filter(c => c.span_id).map(c => [c.span_id as string, c]))
  const rows = orderSpans(spans)

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-[11px] text-slate-500">
        <span>
          Run <span className="font-mono">{runId.slice(0, 8)}</span>
          <CopyId value={runId} label="Copy run id" />
        </span>
        <span>{formatDuration(total)} total</span>
      </div>
      <ol className="space-y-1" aria-label="Trace waterfall">
        {rows.map(({ span, depth }) => {
          const start = new Date(span.started_at).getTime() - t0
          const end = new Date(span.ended_at ?? span.started_at).getTime() - t0
          const left = Math.max(0, (start / total) * 100)
          const width = Math.max(0.6, ((end - start) / total) * 100)
          const call = callBySpan.get(span.id)
          const failed = span.status === 'failed'
          return (
            <li key={span.id} className="grid grid-cols-[minmax(160px,34%)_1fr] items-center gap-2 text-xs">
              <div className="flex min-w-0 items-center" style={{ paddingLeft: depth * 12 }}>
                <span className={`mr-1.5 h-2 w-2 shrink-0 rounded-sm ${TYPE_BAR[span.span_type] ?? 'bg-slate-400'}`} aria-hidden />
                <span className="truncate font-medium text-slate-700 dark:text-slate-200" title={span.name}>{span.name}</span>
                <CopyId value={span.id} label={`Copy span id ${span.name}`} />
              </div>
              <div className="relative h-5 rounded bg-slate-100 dark:bg-slate-800">
                <div
                  className={`absolute top-0.5 h-4 rounded ${failed ? 'bg-status-error' : TYPE_BAR[span.span_type] ?? 'bg-slate-400'}`}
                  style={{ left: `${left}%`, width: `${Math.min(width, 100 - left)}%` }}
                  title={`${span.span_type} · ${formatDuration(end - start)}${call ? ` · ${call.model}` : ''}`}
                />
                <span className="absolute inset-y-0 right-1 flex items-center gap-2 text-[10px] text-slate-500">
                  {call && <span className="font-mono">{call.model}</span>}
                  {span.cost_usd && <span>{formatCost(span.cost_usd)}</span>}
                  <span>{formatDuration(end - start)}</span>
                </span>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
