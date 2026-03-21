import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getRun, getRunGraph } from '@/lib/api'
import RunSummaryBar from '@/components/runs/RunSummaryBar'
import RunGraph from '@/components/dag/RunGraph'
import PayloadViewer from '@/components/runs/PayloadViewer'
import RunScorePanel from '@/components/runs/RunScorePanel'
import {
  ChevronLeft, Cpu, Wrench, Layers, AlertTriangle,
} from 'lucide-react'
import { formatCost, formatTokens, formatDuration } from '@/lib/utils'
import type { ProviderCallDetail, SpanDetail, ToolCallDetail } from '@/types/api'

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    success: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    succeeded: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    error: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    cancelled: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  }
  const cls = map[status.toLowerCase()] ?? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${cls}`}>
      {status}
    </span>
  )
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionHeader({ icon, title, count }: { icon: React.ReactNode; title: string; count: number }) {
  return (
    <div className="flex items-center gap-2 border-b border-slate-200/80 pb-2 dark:border-slate-700/60">
      <span className="text-slate-500 dark:text-slate-400">{icon}</span>
      <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{title}</h2>
      <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
        {count}
      </span>
    </div>
  )
}

// ── Provider calls table ──────────────────────────────────────────────────────

function ProviderCallsTable({ calls }: { calls: ProviderCallDetail[] }) {
  if (calls.length === 0) return (
    <p className="py-4 text-center text-sm text-muted-foreground">No provider calls</p>
  )
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-100 dark:border-slate-800">
            {['Provider', 'Model', 'Input', 'Output', 'Cached', 'Cost', 'Latency', 'Status', 'Error'].map(h => (
              <th key={h} className="py-2 pr-4 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400 first:pl-0">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {calls.map(c => (
            <tr key={c.id} className="border-b border-slate-50 hover:bg-slate-50/60 dark:border-slate-800/60 dark:hover:bg-slate-800/30">
              <td className="py-2 pr-4 font-medium text-slate-700 dark:text-slate-300">{c.provider}</td>
              <td className="py-2 pr-4 font-mono text-slate-500 dark:text-slate-400">{c.model}</td>
              <td className="py-2 pr-4 font-mono text-slate-600 dark:text-slate-400">
                {c.input_tokens != null ? formatTokens(c.input_tokens) : '—'}
              </td>
              <td className="py-2 pr-4 font-mono text-slate-600 dark:text-slate-400">
                {c.output_tokens != null ? formatTokens(c.output_tokens) : '—'}
              </td>
              <td className="py-2 pr-4 font-mono text-slate-500 dark:text-slate-400">
                {c.cached_input_tokens != null ? formatTokens(c.cached_input_tokens) : '—'}
              </td>
              <td className="py-2 pr-4 font-mono font-medium text-slate-700 dark:text-slate-300">
                {formatCost(c.cost_usd)}
              </td>
              <td className="py-2 pr-4 font-mono text-slate-500 dark:text-slate-400">
                {c.latency_ms != null ? formatDuration(c.latency_ms) : '—'}
              </td>
              <td className="py-2 pr-4"><StatusPill status={c.status} /></td>
              <td className="py-2 pr-4 font-mono text-red-500 dark:text-red-400">
                {c.error_type ?? '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Spans table ───────────────────────────────────────────────────────────────

function SpansTable({ spans }: { spans: SpanDetail[] }) {
  if (spans.length === 0) return (
    <p className="py-4 text-center text-sm text-muted-foreground">No spans</p>
  )
  const SPAN_TYPE_COLORS: Record<string, string> = {
    llm: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
    chain: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
    tool: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    agent: 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
    retrieval: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300',
    run: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-100 dark:border-slate-800">
            {['Type', 'Name', 'Status', 'Cost', 'Duration', 'Parent'].map(h => (
              <th key={h} className="py-2 pr-4 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400 first:pl-0">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {spans.map(s => (
            <tr key={s.id} className="border-b border-slate-50 hover:bg-slate-50/60 dark:border-slate-800/60 dark:hover:bg-slate-800/30">
              <td className="py-2 pr-4">
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${SPAN_TYPE_COLORS[s.span_type] ?? SPAN_TYPE_COLORS.run}`}>
                  {s.span_type}
                </span>
              </td>
              <td className="max-w-[220px] truncate py-2 pr-4 font-medium text-slate-700 dark:text-slate-300">
                {s.name}
              </td>
              <td className="py-2 pr-4"><StatusPill status={s.status} /></td>
              <td className="py-2 pr-4 font-mono text-slate-600 dark:text-slate-400">
                {formatCost(s.cost_usd)}
              </td>
              <td className="py-2 pr-4 font-mono text-slate-500 dark:text-slate-400">
                {s.ended_at && s.started_at
                  ? formatDuration(new Date(s.ended_at).getTime() - new Date(s.started_at).getTime())
                  : '—'}
              </td>
              <td className="py-2 pr-4 font-mono text-slate-400 dark:text-slate-500">
                {s.parent_span_id ? s.parent_span_id.slice(0, 8) + '…' : 'root'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Tool calls table ──────────────────────────────────────────────────────────

function ToolCallsTable({ calls }: { calls: ToolCallDetail[] }) {
  if (calls.length === 0) return (
    <p className="py-4 text-center text-sm text-muted-foreground">No tool calls</p>
  )
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-100 dark:border-slate-800">
            {['Tool', 'Type', 'Risk Score', 'Duration', 'Status'].map(h => (
              <th key={h} className="py-2 pr-4 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400 first:pl-0">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {calls.map(t => {
            const risk = t.risk_score ?? 0
            const riskColor = risk >= 0.8
              ? 'text-red-600 dark:text-red-400'
              : risk >= 0.5
              ? 'text-amber-600 dark:text-amber-400'
              : 'text-emerald-600 dark:text-emerald-400'
            return (
              <tr key={t.id} className="border-b border-slate-50 hover:bg-slate-50/60 dark:border-slate-800/60 dark:hover:bg-slate-800/30">
                <td className="py-2 pr-4 font-semibold text-slate-700 dark:text-slate-300">{t.tool_name}</td>
                <td className="py-2 pr-4 text-slate-500 dark:text-slate-400">{t.tool_type}</td>
                <td className={`py-2 pr-4 font-mono font-semibold ${riskColor}`}>
                  {t.risk_score != null ? t.risk_score.toFixed(2) : '—'}
                </td>
                <td className="py-2 pr-4 font-mono text-slate-500 dark:text-slate-400">
                  {formatDuration(t.duration_ms)}
                </td>
                <td className="py-2 pr-4"><StatusPill status={t.status} /></td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default async function RunDetailPage({
  params,
}: {
  params: { run_id: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let run, graph
  try {
    ;[run, graph] = await Promise.all([
      getRun(session.apiKey, params.run_id),
      getRunGraph(session.apiKey, params.run_id),
    ])
  } catch {
    notFound()
  }

  const hasError = run.status === 'failed'

  return (
    <div className="flex flex-col gap-5">
      {/* Back nav */}
      <div className="flex items-center gap-2">
        <Link
          href="/runs"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
        >
          <ChevronLeft className="h-4 w-4" />
          Runs
        </Link>
      </div>

      {/* Summary bar */}
      <RunSummaryBar run={run} />

      {/* Error banner */}
      {hasError && (
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 dark:border-red-800/50 dark:bg-red-950/30">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
          <div>
            <p className="text-sm font-semibold text-red-700 dark:text-red-400">Run failed</p>
            {run.provider_calls.filter(c => c.error_type).map(c => (
              <p key={c.id} className="mt-0.5 font-mono text-xs text-red-600 dark:text-red-400">
                {c.provider}/{c.model}: {c.error_type}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* DAG graph */}
      <div className="min-h-0 h-[340px] rounded-xl border border-gray-200 overflow-hidden dark:border-gray-700">
        <RunGraph graphNodes={graph.nodes} graphEdges={graph.edges} />
      </div>

      {/* Payload viewer */}
      {(run.input_payload != null || run.output_payload != null) && (
        <PayloadViewer run={run} />
      )}

      {/* Provider calls */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-4 dark:border-slate-700/60 dark:bg-slate-900">
        <div className="mb-3">
          <SectionHeader
            icon={<Cpu className="h-4 w-4" />}
            title="Provider Calls"
            count={run.provider_calls.length}
          />
        </div>
        <ProviderCallsTable calls={run.provider_calls} />
      </div>

      {/* Spans */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-4 dark:border-slate-700/60 dark:bg-slate-900">
        <div className="mb-3">
          <SectionHeader
            icon={<Layers className="h-4 w-4" />}
            title="Spans"
            count={run.spans.length}
          />
        </div>
        <SpansTable spans={run.spans} />
      </div>

      {/* Tool calls */}
      {run.tool_calls.length > 0 && (
        <div className="rounded-xl border border-slate-200/80 bg-white p-4 dark:border-slate-700/60 dark:bg-slate-900">
          <div className="mb-3">
            <SectionHeader
              icon={<Wrench className="h-4 w-4" />}
              title="Tool Calls"
              count={run.tool_calls.length}
            />
          </div>
          <ToolCallsTable calls={run.tool_calls} />
        </div>
      )}

      {/* Evaluate this run */}
      <RunScorePanel runId={run.id} />
    </div>
  )
}
