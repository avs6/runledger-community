import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getInvestigationFinopsBudgetPosture, getInvestigationGatewayRuntimePosture, getInvestigationOrgIdentityPosture, getOverviewScopePosture, getRun, getRunGovernanceContext, getRunGraph } from '@/lib/api'
import CancelRunButton from '@/components/runs/CancelRunButton'
import RunSummaryBar from '@/components/runs/RunSummaryBar'
import RunGraph from '@/components/dag/RunGraph'
import PayloadViewer from '@/components/runs/PayloadViewer'
import RunScorePanel from '@/components/runs/RunScorePanel'
import {
  ChevronLeft, Cpu, Wrench, Layers, AlertTriangle,
} from 'lucide-react'
import { formatCost, formatTokens, formatDuration } from '@/lib/utils'
import type { InvestigationFinopsBudgetPosture, InvestigationGatewayRuntimePosture, InvestigationOrgIdentityPosture, OverviewScopePosture, ProviderCallDetail, RunGovernanceContextResponse, SpanDetail, ToolCallDetail } from '@/types/api'

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

function GovernanceEvidencePanel({ governance, scopePosture }: { governance: RunGovernanceContextResponse | null; scopePosture: OverviewScopePosture | null }) {
  if (!governance) return null
  return (
    <div className="rounded-xl border border-cyan-200/80 bg-cyan-50/70 p-4 dark:border-cyan-900/40 dark:bg-cyan-950/20">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Governance evidence</p>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
            Tags: {governance.tags.length ? governance.tags.join(', ') : 'none'} • Security events: {governance.security_events.length} • Alert firings: {governance.alert_evidence.length} • Audit events: {governance.audit_events.length}
            {scopePosture && <> • Pending approvals: {scopePosture.tool_context.pending_approvals} • Capture policies: {scopePosture.tool_context.capture_policies}</>}
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

function FinopsBudgetPanel({ finops, runCost }: { finops: InvestigationFinopsBudgetPosture | null; runCost: number }) {
  if (!finops) return null
  const fmt = (v: number) => (v >= 1 ? `$${v.toFixed(2)}` : v >= 0.001 ? `$${v.toFixed(4)}` : `$${v.toFixed(6)}`)
  return (
    <div className="rounded-xl border border-emerald-200/80 bg-emerald-50/70 p-4 dark:border-emerald-900/40 dark:bg-emerald-950/20">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Budget context</p>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
            Run cost: {fmt(runCost)} • Active budgets: {finops.budget_context.active_budgets} • In breach: {finops.budget_context.breach_count} • 30d spend: {fmt(finops.spend_context.total_spend_30d)} of {fmt(finops.budget_context.total_limit_usd)} limit
          </p>
        </div>
        <div className="flex flex-wrap gap-3 text-xs font-semibold text-emerald-800 dark:text-emerald-100">
          <Link href="/budgets" className="hover:underline">Budgets</Link>
          <Link href="/budgets?view=detail" className="hover:underline">Budget Detail</Link>
          <Link href="/billing" className="hover:underline">Billing Periods</Link>
          <Link href="/chargeback" className="hover:underline">Chargeback</Link>
          <Link href="/model-budgets" className="hover:underline">Model Budgets</Link>
        </div>
      </div>
    </div>
  )
}

function GatewayRuntimePanel({ gateway }: { gateway: InvestigationGatewayRuntimePosture | null }) {
  if (!gateway) return null
  return (
    <div className="rounded-xl border border-violet-200/80 bg-violet-50/70 p-4 dark:border-violet-900/40 dark:bg-violet-950/20">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Gateway runtime context</p>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
            {gateway.provider_context.distinct_providers} providers, {gateway.provider_context.active_routes} active routes • {gateway.guardrail_context.active_rules} guardrail rules ({gateway.guardrail_context.events_30d} events, {gateway.guardrail_context.blocks_30d} blocks) • {gateway.cache_context.enabled_configs} cache configs ({gateway.cache_context.total_hits.toLocaleString()} hits, ${gateway.cache_context.savings_usd.toFixed(2)} saved) • {gateway.rate_limit_context.routes_with_rpm_limits} routes with RPM limits
          </p>
        </div>
        <div className="flex flex-wrap gap-3 text-xs font-semibold text-violet-800 dark:text-violet-100">
          <Link href="/provider-profiles" className="hover:underline">Provider Profiles</Link>
          <Link href="/gateway" className="hover:underline">Gateway Routes</Link>
          <Link href="/guardrails" className="hover:underline">Guardrails</Link>
          <Link href="/cache-config" className="hover:underline">Response Cache</Link>
          <Link href="/rate-limits" className="hover:underline">Rate Limits</Link>
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

  let run, graph
  let governance: RunGovernanceContextResponse | null = null
  let finops: InvestigationFinopsBudgetPosture | null = null
  let gatewayRuntime: InvestigationGatewayRuntimePosture | null = null
  let orgPosture: InvestigationOrgIdentityPosture | null = null
  let scopePosture: OverviewScopePosture | null = null
  try {
    ;[run, graph, governance, finops, gatewayRuntime, orgPosture, scopePosture] = await Promise.all([
      getRun(session.apiKey, params.run_id, { access_group_id: accessGroupId }),
      getRunGraph(session.apiKey, params.run_id, { access_group_id: accessGroupId }),
      getRunGovernanceContext(session.apiKey, params.run_id, { access_group_id: accessGroupId }).catch(() => null),
      getInvestigationFinopsBudgetPosture(session.apiKey, { access_group_id: accessGroupId }).catch(() => null),
      getInvestigationGatewayRuntimePosture(session.apiKey, { access_group_id: accessGroupId }).catch(() => null),
      getInvestigationOrgIdentityPosture(session.apiKey).catch(() => null),
      getOverviewScopePosture(session.apiKey).catch(() => null),
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
          href={accessGroupId ? `/runs?access_group_id=${encodeURIComponent(accessGroupId)}` : '/runs'}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
        >
          <ChevronLeft className="h-4 w-4" />
          Runs
        </Link>
      </div>

      {/* Summary bar */}
      <RunSummaryBar run={run} />

      {accessGroup && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100">
          This run is being viewed inside the <span className="font-semibold">{accessGroup.name}</span> access-group investigation scope.
        </div>
      )}

      <div className="rounded-2xl border border-blue-200 bg-blue-50/60 p-5 shadow-sm dark:border-blue-800 dark:bg-blue-950/40">
        <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-blue-700 dark:text-blue-400">Identity Provenance</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-blue-200 bg-white/80 px-4 py-3 dark:border-blue-800 dark:bg-slate-900/60">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600 dark:text-blue-400">End User</p>
            <p className="mt-1 truncate font-mono text-sm font-semibold text-slate-950 dark:text-slate-50">{run.end_user_id ?? 'Not captured'}</p>
          </div>
          <div className="rounded-xl border border-blue-200 bg-white/80 px-4 py-3 dark:border-blue-800 dark:bg-slate-900/60">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600 dark:text-blue-400">API Key</p>
            <p className="mt-1 truncate font-mono text-sm font-semibold text-slate-950 dark:text-slate-50">{run.api_key_id ? run.api_key_id.slice(0, 12) + '…' : 'Not captured'}</p>
          </div>
          <div className="rounded-xl border border-blue-200 bg-white/80 px-4 py-3 dark:border-blue-800 dark:bg-slate-900/60">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600 dark:text-blue-400">Model</p>
            <p className="mt-1 truncate text-sm font-semibold text-slate-950 dark:text-slate-50">{run.primary_model ?? 'Unknown'}</p>
          </div>
          <div className="rounded-xl border border-blue-200 bg-white/80 px-4 py-3 dark:border-blue-800 dark:bg-slate-900/60">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600 dark:text-blue-400">Feature Tag</p>
            <p className="mt-1 truncate text-sm font-semibold text-slate-950 dark:text-slate-50">{run.feature_tag ?? 'Untagged'}</p>
          </div>
        </div>
        {orgPosture && (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-xl border border-blue-200 bg-white/80 px-4 py-3 dark:border-blue-800 dark:bg-slate-900/60">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600 dark:text-blue-400">Workspace</p>
              <p className="mt-1 truncate text-sm font-semibold text-slate-950 dark:text-slate-50">{orgPosture.org_context.workspace_name}</p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">{orgPosture.org_context.workspace_users} users</p>
            </div>
            <div className="rounded-xl border border-blue-200 bg-white/80 px-4 py-3 dark:border-blue-800 dark:bg-slate-900/60">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600 dark:text-blue-400">MCP Registry</p>
              <p className="mt-1 text-sm font-semibold text-slate-950 dark:text-slate-50">{orgPosture.mcp_context.servers} servers</p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">{orgPosture.mcp_context.tool_calls_30d} tool calls (30d)</p>
            </div>
            <div className="rounded-xl border border-blue-200 bg-white/80 px-4 py-3 dark:border-blue-800 dark:bg-slate-900/60">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600 dark:text-blue-400">Telemetry</p>
              <p className="mt-1 text-sm font-semibold text-slate-950 dark:text-slate-50">{orgPosture.telemetry_context.batches_30d} batches</p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">{orgPosture.telemetry_context.runs_30d} runs (30d)</p>
            </div>
          </div>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          <Link href="/organization" className="text-xs text-blue-700 hover:underline dark:text-blue-400">Organization</Link>
          <Link href="/workspaces" className="text-xs text-blue-700 hover:underline dark:text-blue-400">Workspaces</Link>
          {run.end_user_id && <Link href={`/runs?end_user_id=${encodeURIComponent(run.end_user_id)}`} className="text-xs text-blue-700 hover:underline dark:text-blue-400">User Runs</Link>}
          {run.api_key_id && <Link href={`/runs?api_key_id=${encodeURIComponent(run.api_key_id)}`} className="text-xs text-blue-700 hover:underline dark:text-blue-400">API Key Runs</Link>}
          <Link href="/users" className="text-xs text-blue-700 hover:underline dark:text-blue-400">Users</Link>
          <Link href="/api-keys" className="text-xs text-blue-700 hover:underline dark:text-blue-400">API Keys</Link>
          <Link href="/telemetry" className="text-xs text-blue-700 hover:underline dark:text-blue-400">Telemetry</Link>
          <Link href="/mcp-registry" className="text-xs text-blue-700 hover:underline dark:text-blue-400">MCP Registry</Link>
        </div>
      </div>

      <GovernanceEvidencePanel governance={governance} scopePosture={scopePosture} />
      <FinopsBudgetPanel finops={finops} runCost={run.total_cost_usd ?? 0} />
      <GatewayRuntimePanel gateway={gatewayRuntime} />

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200/80 bg-white p-4 dark:border-slate-700/60 dark:bg-slate-900">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Run actions</p>
          <p className="mt-1 text-xs text-slate-500">Cancel a stuck run directly from the UI when it is still marked as running.</p>
        </div>
        <CancelRunButton runId={run.id} status={run.status} />
      </div>

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
