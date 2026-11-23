import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getRun, getRunGovernanceContext, getRunGraph } from '@/lib/api'
import CancelRunButton from '@/components/runs/CancelRunButton'
import RunSummaryBar from '@/components/runs/RunSummaryBar'
import RunGraph from '@/components/dag/RunGraph'
import PayloadViewer from '@/components/runs/PayloadViewer'
import RunScorePanel from '@/components/runs/RunScorePanel'
import {
  ChevronLeft, Cpu, Wrench, Layers, AlertTriangle,
} from 'lucide-react'
import { formatCost, formatTokens, formatDuration, num } from '@/lib/utils'
import type { ProviderCallDetail, RunDetailResponse, RunGovernanceContextResponse, SpanDetail, ToolCallDetail } from '@/types/api'
import CopyId from '@/components/observe/CopyId'
import TraceWaterfall from '@/components/observe/TraceWaterfall'
import { SectionError } from '@/components/ui/async-card'

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
    agent: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
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
                  {t.risk_score != null ? num(t.risk_score).toFixed(2) : '—'}
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

function GovernanceEvidencePanel({ governance }: { governance: RunGovernanceContextResponse | null }) {
  if (!governance) return null
  return (
    <div className="rounded-xl border border-cyan-200/80 bg-cyan-50/70 p-4 dark:border-cyan-900/40 dark:bg-cyan-950/20">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Governance evidence</p>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
            Tags: {governance.tags.length ? governance.tags.join(', ') : 'none'} • Security events: {governance.security_events.length} • Alert firings: {governance.alert_evidence.length} • Audit events: {governance.audit_events.length}
          </p>
        </div>
        <div className="flex flex-wrap gap-3 text-xs font-semibold text-cyan-800 dark:text-cyan-100">
          <Link href="/tool-registry" className="hover:underline">Tool Registry</Link>
          <Link href="/tool-policies" className="hover:underline">Tool Policies</Link>
          <Link href="/approvals" className="hover:underline">Approvals</Link>
          <Link href="/data-capture" className="hover:underline">Data Capture</Link>
          <Link href="/security" className="hover:underline">Security</Link>
          <Link href="/alert-rules" className="hover:underline">Alert Rules</Link>
          <Link href="/audit" className="hover:underline">Audit Log</Link>
          <Link href="/governance-pack" className="hover:underline">Governance Pack</Link>
          <Link href="/tags" className="hover:underline">Tags</Link>
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default async function RunDetailPage({
  params,
  searchParams,
}: {
  params: { run_id: string }
  searchParams?: { access_group_id?: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null
  const accessGroupId = searchParams?.access_group_id
  const accessGroupDashboard = accessGroupId
    ? await getAccessGroupDashboard(session.apiKey, accessGroupId).catch(() => null)
    : null
  const accessGroup = accessGroupDashboard?.groups[0] ?? null

  // Only a 404 is "not found"; any other failure surfaces in error.tsx with a retry,
  // and a failed graph or governance load degrades just that card (review O-19).
  let run: RunDetailResponse
  try {
    run = await getRun(session.apiKey, params.run_id, { access_group_id: accessGroupId })
  } catch (err) {
    if (err instanceof Error && /API (404|422)/.test(err.message)) notFound()
    throw err
  }
  const [graphResult, governance] = await Promise.all([
    getRunGraph(session.apiKey, params.run_id, { access_group_id: accessGroupId })
      .then(g => ({ graph: g, error: null as string | null }))
      .catch((err: unknown) => ({ graph: null, error: err instanceof Error ? err.message : 'Graph failed to load' })),
    getRunGovernanceContext(session.apiKey, params.run_id, { access_group_id: accessGroupId }).catch(() => null),
  ])
  const graph = graphResult.graph

  const hasError = run.status === 'failed'

  return (
    <div className="flex flex-col gap-3">
      {/* Back nav */}
      <div className="flex items-center gap-2">
        <Link
          href={accessGroupId ? `/runs?access_group_id=${encodeURIComponent(accessGroupId)}` : '/runs'}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Runs
        </Link>
        <span className="font-mono text-xs text-slate-500">{run.id}</span>
        <CopyId value={run.id} label="Copy run id" />
        <Link href={`/runs/compare?a=${encodeURIComponent(run.id)}`} className="ml-auto text-xs font-semibold text-blue-600 hover:underline dark:text-blue-400">
          Compare with…
        </Link>
      </div>

      {/* Summary bar */}
      <RunSummaryBar run={run} />

      {/* Error banner */}
      {hasError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 dark:border-red-800/50 dark:bg-red-950/30">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
          <div>
            <p className="text-xs font-semibold text-red-700 dark:text-red-400">Run failed</p>
            {run.provider_calls.filter(c => c.error_type).map(c => (
              <p key={c.id} className="mt-0.5 font-mono text-[11px] text-red-600 dark:text-red-400">
                {c.provider}/{c.model}: {c.error_type}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* DAG graph — hero */}
      <div className="min-h-0 h-[480px] rounded-xl border border-gray-200 overflow-hidden dark:border-gray-700">
        {graph ? (
          <RunGraph graphNodes={graph.nodes} graphEdges={graph.edges} />
        ) : (
          <div className="p-3"><SectionError message={`Run graph failed to load: ${graphResult.error}`} /></div>
        )}
      </div>

      {accessGroup && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100">
          Viewing inside <span className="font-semibold">{accessGroup.name}</span> access-group scope.
        </div>
      )}

      {/* Identity provenance — compact chips */}
      <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-3 dark:border-blue-800 dark:bg-blue-950/40">
        <div className="flex items-center justify-between gap-2">
          <p className="text-[10px] font-bold uppercase tracking-wider text-blue-700 dark:text-blue-400">Identity Provenance</p>
          <div className="flex flex-wrap gap-1.5 text-[10px] font-semibold text-blue-700 dark:text-blue-400">
            <Link href="/organization" className="hover:underline">Org</Link>
            <Link href="/users" className="hover:underline">Users</Link>
            <Link href="/api-keys" className="hover:underline">Keys</Link>
            <Link href="/monitoring/telemetry" className="hover:underline">Telemetry</Link>
            <Link href="/mcp-registry" className="hover:underline">MCP</Link>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {[
            { label: 'End User', value: run.end_user_id ?? 'Not captured' },
            { label: 'API Key', value: run.api_key_id ? run.api_key_id.slice(0, 12) + '…' : 'Not captured' },
            { label: 'Model', value: run.primary_model ?? 'Unknown' },
            { label: 'Feature', value: run.feature_tag ?? 'Untagged' },
          ].map(({ label, value }) => (
            <span key={label} className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-white/80 px-2 py-0.5 text-[11px] dark:border-blue-800 dark:bg-slate-900/60">
              <span className="font-medium text-blue-600 dark:text-blue-400">{label}</span>
              <span className="max-w-[160px] truncate font-semibold text-slate-900 dark:text-slate-100">{value}</span>
            </span>
          ))}
        </div>
      </div>

      <GovernanceEvidencePanel governance={governance} />

      {/* Run actions — inline */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200/80 bg-white px-3 py-2 dark:border-slate-700/60 dark:bg-slate-900">
        <p className="text-xs text-slate-500 dark:text-slate-400">Cancel a stuck run when it is still marked as running.</p>
        <CancelRunButton runId={run.id} status={run.status} />
      </div>

      {/* Payload viewer — captured payloads only for roles allowed to read them (O-05) */}
      {run.payloads_redacted && (
        <p role="note" className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
          This run has captured prompts and responses, but your role or API key scope can&apos;t read them.
        </p>
      )}
      {(run.input_payload != null || run.output_payload != null) && (
        <PayloadViewer run={run} />
      )}

      {/* Trace waterfall */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-3 dark:border-slate-700/60 dark:bg-slate-900">
        <div className="mb-2">
          <SectionHeader icon={<Layers className="h-3.5 w-3.5" />} title="Trace waterfall" count={run.spans.length} />
        </div>
        <TraceWaterfall runId={run.id} startedAt={run.started_at} endedAt={run.ended_at} spans={run.spans} calls={run.provider_calls} />
      </div>

      {/* Provider calls + Spans side by side on wide screens */}
      <div className="grid gap-3 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-200/80 bg-white p-3 dark:border-slate-700/60 dark:bg-slate-900">
          <div className="mb-2">
            <SectionHeader
              icon={<Cpu className="h-3.5 w-3.5" />}
              title="Provider Calls"
              count={run.provider_calls.length}
            />
          </div>
          <ProviderCallsTable calls={run.provider_calls} />
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3 dark:border-slate-700/60 dark:bg-slate-900">
          <div className="mb-2">
            <SectionHeader
              icon={<Layers className="h-3.5 w-3.5" />}
              title="Spans"
              count={run.spans.length}
            />
          </div>
          <SpansTable spans={run.spans} />
        </div>
      </div>

      {/* Tool calls */}
      {run.tool_calls.length > 0 && (
        <div className="rounded-xl border border-slate-200/80 bg-white p-3 dark:border-slate-700/60 dark:bg-slate-900">
          <div className="mb-2">
            <SectionHeader
              icon={<Wrench className="h-3.5 w-3.5" />}
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
