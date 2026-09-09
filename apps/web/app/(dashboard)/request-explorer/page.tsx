import { getServerSession } from 'next-auth'
import Link from 'next/link'
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  GitBranch,
  MessageSquareText,
  Network,
  Route,
  Search,
  ShieldCheck,
  Sparkles,
  Tags,
  User,
  KeyRound,
  Wrench,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getInvestigationFinopsBudgetPosture, getInvestigationGatewayRuntimePosture, getInvestigationOrgIdentityPosture, getOverviewScopePosture, getRequestExplorer, getRun, getRunGovernanceContext, getRunGraph, listGatewayRequests, listOutcomes } from '@/lib/api'
import RunStatusBadge from '@/components/runs/RunStatusBadge'
import { formatCost, formatDuration, formatTimestamp, formatTokens, truncateId, num } from '@/lib/utils'
import type {
  GatewayRequestLog,
  InvestigationFinopsBudgetPosture,
  InvestigationGatewayRuntimePosture,
  InvestigationOrgIdentityPosture,
  OutcomeResponse,
  OverviewScopePosture,
  ProviderCallDetail,
  RequestRecord,
  RunDetailResponse,
  RunGovernanceContextResponse,
  SpanDetail,
  ToolCallDetail,
} from '@/types/api'

interface PageProps {
  searchParams: {
    run_id?: string
    q?: string
    status?: string
    feature_tag?: string
    end_user_id?: string
    model?: string
    provider?: string
    optimization?: string
    page?: string
    access_group_id?: string
    api_key_id?: string
    tag?: string
    tool_name?: string
    security_event_only?: string
  }
}

type DebugFact = {
  label: string
  value: string
  icon: React.ElementType
}

function numericCost(value: string | null | undefined) {
  const parsed = Number.parseFloat(value ?? '0')
  return Number.isFinite(parsed) ? parsed : 0
}

function metadataValue(metadata: Record<string, unknown> | null | undefined, keys: string[]) {
  if (!metadata) return null
  for (const key of keys) {
    const value = metadata[key]
    if (typeof value === 'string' && value.trim()) return value
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  }
  return null
}

function firstMetadataValue(spans: SpanDetail[], keys: string[]) {
  for (const span of spans) {
    const value = metadataValue(span.metadata, keys)
    if (value) return value
  }
  return null
}

function selectedAgent(run: RunDetailResponse) {
  return (
    firstMetadataValue(run.spans, ['agent_client', 'agent', 'selected_agent', 'agent_name', 'workflow_agent']) ??
    run.spans.find((span) => span.span_type === 'agent')?.name ??
    firstMetadataValue(run.spans, ['client', 'source']) ??
    'Not captured'
  )
}

function routingEvidence(run: RunDetailResponse, gatewayMatch: GatewayRequestLog | null) {
  const routeAlias =
    firstMetadataValue(run.spans, ['route_alias', 'route', 'gateway_route', 'selected_route', 'model_alias']) ??
    gatewayMatch?.model_requested ??
    'Not captured'
  const decision =
    firstMetadataValue(run.spans, ['decision_reason', 'routing_reason', 'route_reason', 'gateway_decision']) ??
    gatewayMatch?.decision_reason ??
    'Not captured'
  return { routeAlias, decision }
}

function cacheStatus(run: RunDetailResponse, gatewayMatch: GatewayRequestLog | null) {
  const cachedTokens = run.provider_calls.reduce((sum, call) => sum + (call.cached_input_tokens ?? 0), 0)
  if (gatewayMatch?.cache_hit || cachedTokens > 0) return `Cache hit (${formatTokens(cachedTokens)} cached input tokens)`
  return 'No cache hit recorded'
}

function optimizationStatus(run: RunDetailResponse, gatewayMatch: GatewayRequestLog | null) {
  const metadataOpt = firstMetadataValue(run.spans, [
    'optimization_applied',
    'optimization',
    'compiler_applied',
    'compression_applied',
    'semantic_cache',
    'policy_mode',
  ])
  if (metadataOpt) return metadataOpt
  if (gatewayMatch?.cache_hit) return 'Cache optimization applied'
  const cachedTokens = run.provider_calls.reduce((sum, call) => sum + (call.cached_input_tokens ?? 0), 0)
  if (cachedTokens > 0) return 'Provider cached input used'
  return 'No optimization marker captured'
}

function promptPreview(run: RunDetailResponse) {
  const firstUser = run.input_payload?.find((message) => message.role === 'user') ?? run.input_payload?.[0]
  return firstUser?.content ?? 'Prompt not captured. Enable sampled or full Data Capture to inspect prompt text.'
}

function responsePreview(run: RunDetailResponse) {
  if (run.output_payload == null) return 'Final response not captured.'
  if (typeof run.output_payload === 'string') return run.output_payload
  return JSON.stringify(run.output_payload, null, 2)
}

function matchingGatewayRequest(run: RunDetailResponse, requests: GatewayRequestLog[]) {
  const runStarted = new Date(run.started_at).getTime()
  const models = new Set(run.provider_calls.map((call) => call.model))
  return (
    requests.find((request) => {
      const requestAt = new Date(request.created_at).getTime()
      const closeInTime = Math.abs(requestAt - runStarted) < 5 * 60_000
      const modelMatch = request.model_used ? models.has(request.model_used) : models.has(request.model_requested)
      return closeInTime && modelMatch
    }) ?? null
  )
}

function requestHref(current: PageProps['searchParams'], updates: Record<string, string | null | undefined>) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(current)) {
    if (value) params.set(key, value)
  }
  for (const [key, value] of Object.entries(updates)) {
    if (value) params.set(key, value)
    else params.delete(key)
  }
  const qs = params.toString()
  return `/request-explorer${qs ? `?${qs}` : ''}`
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-800/90 ${className}`}>
      {children}
    </div>
  )
}

function Chip({ label, value, icon: Icon }: { label: string; value: string; icon: React.ElementType }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs dark:border-slate-700 dark:bg-slate-800" title={value}>
      <Icon className="h-3 w-3 text-blue-600 dark:text-blue-400" />
      <span className="font-medium text-slate-500 dark:text-slate-400">{label}</span>
      <span className="max-w-[140px] truncate font-semibold text-slate-900 dark:text-slate-100">{value}</span>
    </span>
  )
}

function RunList({ requests, selectedRunId, searchParams }: { requests: RequestRecord[]; selectedRunId: string | null; searchParams: PageProps['searchParams'] }) {
  if (requests.length === 0) {
    return (
      <Card className="p-6 text-center">
        <p className="text-sm font-semibold text-slate-950 dark:text-slate-100">No requests found</p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Try widening the filters or sending traffic through SDK, Gateway, or OTLP.</p>
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-200 px-3 py-2 dark:border-slate-700">
        <h2 className="text-xs font-semibold text-slate-950 dark:text-slate-100">{requests.length} Requests</h2>
      </div>
      <div className="max-h-[calc(100vh-280px)] overflow-y-auto">
        {requests.map((request) => {
          const selected = request.run_id === selectedRunId
          const totalTokens = (request.input_tokens ?? 0) + (request.output_tokens ?? 0)
          return (
            <Link
              key={request.id}
              href={requestHref(searchParams, { run_id: request.run_id })}
              className={`block border-b border-slate-100 px-3 py-2 transition hover:bg-blue-50 dark:border-slate-700/50 dark:hover:bg-blue-900/20 ${selected ? 'bg-blue-50 ring-1 ring-inset ring-blue-200 dark:bg-blue-900/30 dark:ring-blue-500/30' : ''}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] font-semibold text-slate-950 dark:text-slate-100">{truncateId(request.run_id, 10)}</span>
                <RunStatusBadge status={request.status === 'success' ? 'succeeded' : request.status === 'error' ? 'failed' : request.status as 'running' | 'succeeded' | 'failed' | 'cancelled'} />
              </div>
              <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                <span className="truncate">{request.model}</span>
                <span>{formatCost(request.cost_usd)}</span>
                <span>{formatTokens(totalTokens)}</span>
              </div>
            </Link>
          )
        })}
      </div>
    </Card>
  )
}

function FilterBar({ searchParams }: { searchParams: PageProps['searchParams'] }) {
  const inputCls = "w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-900 outline-none focus:ring-2 focus:ring-blue-500/30 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
  return (
    <form action="/request-explorer" className="rounded-xl border border-slate-200 bg-white/80 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-800/80">
      {searchParams.access_group_id && <input type="hidden" name="access_group_id" value={searchParams.access_group_id} />}
      <div className="flex flex-wrap items-end gap-2">
        <div className="w-40">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Search</label>
          <input name="q" defaultValue={searchParams.q ?? ''} placeholder="Run ID, user, model..." className={inputCls} />
        </div>
        <div className="w-24">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Status</label>
          <select name="status" defaultValue={searchParams.status ?? ''} className={inputCls}>
            <option value="">Any</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        <div className="w-28">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Intent</label>
          <input name="feature_tag" defaultValue={searchParams.feature_tag ?? ''} placeholder="support-chat" className={inputCls} />
        </div>
        <div className="w-28">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Model</label>
          <input name="model" defaultValue={searchParams.model ?? ''} placeholder="gpt, claude..." className={inputCls} />
        </div>
        <div className="w-28">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Provider</label>
          <input name="provider" defaultValue={searchParams.provider ?? ''} placeholder="openai, anthropic..." className={inputCls} />
        </div>
        <div className="w-24">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Tag</label>
          <input name="tag" defaultValue={searchParams.tag ?? ''} placeholder="pci, prod..." className={inputCls} />
        </div>
        <div className="w-28">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Tool</label>
          <input name="tool_name" defaultValue={searchParams.tool_name ?? ''} placeholder="browser.search" className={inputCls} />
        </div>
        <div className="w-28">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">API Key</label>
          <input name="api_key_id" defaultValue={searchParams.api_key_id ?? ''} placeholder="key_abc123..." className={inputCls} />
        </div>
        <label className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300">
          <input type="checkbox" name="security_event_only" value="true" defaultChecked={searchParams.security_event_only === 'true'} className="h-3 w-3" />
          Security
        </label>
        <button type="submit" className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1 text-xs font-semibold text-white shadow-sm hover:bg-blue-700">
          <Search className="h-3 w-3" />
          Explore
        </button>
      </div>
    </form>
  )
}

function LifecycleCard({ title, value, detail, icon: Icon }: { title: string; value: string; detail: string; icon: React.ElementType }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-2.5 dark:border-slate-700 dark:bg-slate-900/50">
      <div className="flex items-center gap-1.5">
        <Icon className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{title}</p>
      </div>
      <p className="mt-1 truncate text-xs font-semibold text-slate-950 dark:text-slate-100" title={value}>{value}</p>
      <p className="mt-0.5 truncate text-[11px] text-slate-500 dark:text-slate-400" title={detail}>{detail}</p>
    </div>
  )
}

function PayloadPanel({ run }: { run: RunDetailResponse }) {
  const messages = run.input_payload ?? []
  return (
    <Card className="p-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-950 dark:text-slate-100">Prompt & Response</h2>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
          {messages.length} message{messages.length === 1 ? '' : 's'}
        </span>
      </div>
      <div className="mt-2 grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Prompt</p>
          <pre className="mt-1.5 max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-slate-50 p-2 text-[11px] leading-4 text-slate-700 dark:bg-slate-800 dark:text-slate-300">{promptPreview(run)}</pre>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Response</p>
          <pre className="mt-1.5 max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-slate-50 p-2 text-[11px] leading-4 text-slate-700 dark:bg-slate-800 dark:text-slate-300">{responsePreview(run)}</pre>
        </div>
      </div>
    </Card>
  )
}

function ProviderTable({ calls }: { calls: ProviderCallDetail[] }) {
  return (
    <TableCard
      title="Model Calls"
      icon={Cpu}
      empty="No model calls recorded."
      headers={['Provider', 'Model', 'Tokens', 'Cost', 'Latency', 'Status', 'Error']}
      rows={calls.map((call) => [
        call.provider,
        call.model,
        `${formatTokens(call.input_tokens)} in / ${formatTokens(call.output_tokens)} out`,
        formatCost(call.cost_usd),
        formatDuration(call.latency_ms),
        call.status,
        call.error_type ?? '-',
      ])}
    />
  )
}

function ToolTable({ calls }: { calls: ToolCallDetail[] }) {
  return (
    <TableCard
      title="Tools Called"
      icon={Wrench}
      empty="No tool calls recorded."
      headers={['Tool', 'Type', 'Risk', 'Duration', 'Status']}
      rows={calls.map((call) => [
        call.tool_name,
        call.tool_type,
        call.risk_score == null ? '-' : num(call.risk_score).toFixed(2),
        formatDuration(call.duration_ms),
        call.status,
      ])}
    />
  )
}

function SpanTable({ spans }: { spans: SpanDetail[] }) {
  return (
    <TableCard
      title="Trace Spans"
      icon={GitBranch}
      empty="No spans recorded."
      headers={['Type', 'Name', 'Status', 'Cost', 'Metadata']}
      rows={spans.map((span) => [
        span.span_type,
        span.name,
        span.status,
        formatCost(span.cost_usd),
        span.metadata ? Object.keys(span.metadata).slice(0, 4).join(', ') || '-' : '-',
      ])}
    />
  )
}

function OutcomeTable({ outcomes }: { outcomes: OutcomeResponse[] }) {
  return (
    <TableCard
      title="Outcome"
      icon={ShieldCheck}
      empty="No outcome linked to this request."
      headers={['Type', 'Result', 'Value', 'Labels', 'Recorded']}
      rows={outcomes.map((outcome) => [
        outcome.outcome_type,
        outcome.success ? 'success' : 'failed',
        formatCost(outcome.value_usd),
        Object.keys(outcome.labels ?? {}).join(', ') || '-',
        formatTimestamp(outcome.created_at),
      ])}
    />
  )
}

function TableCard({
  title,
  icon: Icon,
  empty,
  headers,
  rows,
}: {
  title: string
  icon: React.ElementType
  empty: string
  headers: string[]
  rows: string[][]
}) {
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-1.5 border-b border-slate-200 px-3 py-2 dark:border-slate-700">
        <Icon className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
        <h2 className="text-xs font-semibold text-slate-950 dark:text-slate-100">{title}</h2>
        <span className="ml-auto rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500 dark:bg-slate-700 dark:text-slate-400">{rows.length}</span>
      </div>
      {rows.length === 0 ? (
        <p className="p-4 text-center text-xs text-slate-500 dark:text-slate-400">{empty}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-900/50">
                {headers.map((header) => (
                  <th key={header} className="px-2.5 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${title}-${index}`} className="border-b border-slate-100 dark:border-slate-700/50">
                  {row.map((cell, cellIndex) => (
                    <td key={`${title}-${index}-${cellIndex}`} className="max-w-[220px] truncate px-2.5 py-1.5 text-[11px] text-slate-700 dark:text-slate-300" title={cell}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

function RequestDetail({
  run,
  graphNodeCount,
  outcomes,
  gatewayMatch,
  accessGroupId,
  governance,
  finops,
  orgIdentity,
  gatewayRuntime,
  scopePosture,
}: {
  run: RunDetailResponse
  graphNodeCount: number
  outcomes: OutcomeResponse[]
  gatewayMatch: GatewayRequestLog | null
  accessGroupId?: string
  governance: RunGovernanceContextResponse | null
  finops: InvestigationFinopsBudgetPosture | null
  orgIdentity: InvestigationOrgIdentityPosture | null
  gatewayRuntime: InvestigationGatewayRuntimePosture | null
  scopePosture: OverviewScopePosture | null
}) {
  const totalTokens = (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0)
  const { routeAlias, decision } = routingEvidence(run, gatewayMatch)
  const model = run.provider_calls[0]?.model ?? firstMetadataValue(run.spans, ['model', 'selected_model']) ?? 'Not captured'
  const provider = run.provider_calls[0]?.provider ?? firstMetadataValue(run.spans, ['provider']) ?? 'Not captured'
  const outcomeLabel =
    outcomes[0] ? `${outcomes[0].outcome_type}: ${outcomes[0].success ? 'success' : 'failed'}` : 'No outcome linked'

  const facts: DebugFact[] = [
    { label: 'Intent', value: run.feature_tag ?? 'General / Untagged', icon: Tags },
    { label: 'Agent', value: selectedAgent(run), icon: BrainCircuit },
    { label: 'Model', value: model, icon: Cpu },
    { label: 'Provider', value: provider, icon: Network },
    { label: 'Cost', value: formatCost(run.total_cost_usd), icon: DollarSign },
    { label: 'Latency', value: formatDuration(run.duration_ms), icon: Clock },
    { label: 'Tokens', value: formatTokens(totalTokens), icon: Activity },
    { label: 'End User', value: run.end_user_id ?? 'Not captured', icon: User },
    { label: 'API Key', value: run.api_key_id ? truncateId(run.api_key_id, 12) : 'Not captured', icon: KeyRound },
  ]

  return (
    <div className="space-y-3">
      <Card className="p-3">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-950 dark:text-slate-100">Request {truncateId(run.id, 12)}</h2>
            <RunStatusBadge status={run.status} />
            <span className="text-[11px] text-slate-500 dark:text-slate-400">{formatTimestamp(run.started_at)} · {graphNodeCount} nodes</span>
          </div>
          <Link href={accessGroupId ? `/runs/${run.id}?access_group_id=${encodeURIComponent(accessGroupId)}` : `/runs/${run.id}`} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-sm hover:bg-blue-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
            Open run detail <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </Card>

      <div className="flex flex-wrap gap-1.5">
        {facts.map((fact) => (
          <Chip key={fact.label} label={fact.label} value={fact.value} icon={fact.icon} />
        ))}
      </div>

      <Card className="p-3">
        <h2 className="text-xs font-semibold text-slate-950 dark:text-slate-100">Request Lifecycle</h2>
        <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          <LifecycleCard title="Prompt" value={run.input_payload ? 'Captured' : 'Not captured'} detail={run.input_payload ? `${run.input_payload.length} input message(s)` : 'Enable Data Capture.'} icon={MessageSquareText} />
          <LifecycleCard title="Cache" value={cacheStatus(run, gatewayMatch)} detail="Provider cached-token evidence and Gateway cache logs." icon={Sparkles} />
          <LifecycleCard title="Route" value={routeAlias} detail={decision} icon={Route} />
          <LifecycleCard title="Outcome" value={outcomeLabel} detail={optimizationStatus(run, gatewayMatch)} icon={CheckCircle2} />
        </div>
      </Card>

      {governance && (
        <Card className="p-3">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-xs font-semibold text-slate-950 dark:text-slate-100">Governance</h2>
            <div className="flex flex-wrap gap-1.5 text-[10px] font-semibold text-cyan-700 dark:text-cyan-400">
              <Link href="/tool-registry" className="hover:underline">Registry</Link>
              <Link href="/tool-policies" className="hover:underline">Policies</Link>
              <Link href="/security" className="hover:underline">Security</Link>
              <Link href="/audit" className="hover:underline">Audit</Link>
              <Link href="/tags" className="hover:underline">Tags</Link>
            </div>
          </div>
          <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            <LifecycleCard title="Tags" value={governance.tags.length ? governance.tags.join(', ') : 'No tags'} detail="Governance drill-through tags" icon={Tags} />
            <LifecycleCard title="Tool Policies" value={String(governance.tool_evidence.reduce((sum, item) => sum + item.matched_policy_count, 0))} detail={`${governance.tool_evidence.length} tools matched`} icon={Wrench} />
            <LifecycleCard title="Security Events" value={String(governance.security_events.length)} detail="Correlated by run/tool/user" icon={ShieldCheck} />
            <LifecycleCard title="Alerts / Audit" value={`${governance.alert_evidence.length} / ${governance.audit_events.length}`} detail="Alert firings and audit events" icon={Activity} />
          </div>
        </Card>
      )}

      {finops && (
        <Card className="p-3">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-xs font-semibold text-slate-950 dark:text-slate-100">Budget Context</h2>
            <div className="flex flex-wrap gap-1.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">
              <Link href="/budgets" className="hover:underline">Budgets</Link>
              <Link href="/billing" className="hover:underline">Billing</Link>
              <Link href="/chargeback" className="hover:underline">Chargeback</Link>
            </div>
          </div>
          <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            <LifecycleCard title="Active Budgets" value={`${finops.budget_context.active_budgets} / ${finops.budget_context.budgets}`} detail={`${finops.budget_context.breach_count} in breach`} icon={DollarSign} />
            <LifecycleCard title="Budget Limit" value={formatCost(finops.budget_context.total_limit_usd)} detail={`${finops.budget_context.active_overrides} overrides`} icon={ShieldCheck} />
            <LifecycleCard title="30d Spend" value={formatCost(finops.spend_context.total_spend_30d)} detail={`${finops.spend_context.total_runs_30d.toLocaleString()} runs`} icon={Activity} />
            <LifecycleCard title="Billing" value={`${finops.billing_context.open_billing_periods} open`} detail={`${finops.billing_context.chargeback_rules} chargeback rules`} icon={Clock} />
          </div>
        </Card>
      )}

      {orgIdentity && (
        <Card className="p-3">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-xs font-semibold text-slate-950 dark:text-slate-100">Org Identity</h2>
            <div className="flex flex-wrap gap-1.5 text-[10px] font-semibold text-blue-700 dark:text-blue-400">
              <Link href="/organization" className="hover:underline">Org</Link>
              <Link href="/users" className="hover:underline">Users</Link>
              <Link href="/api-keys" className="hover:underline">Keys</Link>
              <Link href="/mcp-registry" className="hover:underline">MCP</Link>
            </div>
          </div>
          <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            <LifecycleCard title="Users" value={String(orgIdentity.user_context.workspace_users)} detail={`${orgIdentity.user_context.distinct_end_users_30d} end users (30d)`} icon={User} />
            <LifecycleCard title="API Keys" value={`${orgIdentity.api_key_context.active_keys} active`} detail={`${orgIdentity.api_key_context.total_keys} total`} icon={KeyRound} />
            <LifecycleCard title="MCP Servers" value={String(orgIdentity.mcp_context.servers)} detail={`${orgIdentity.mcp_context.tool_calls_30d.toLocaleString()} calls (30d)`} icon={Network} />
            <LifecycleCard title="Telemetry" value={`${orgIdentity.telemetry_context.batches_30d.toLocaleString()} batches`} detail={`${orgIdentity.telemetry_context.runs_30d.toLocaleString()} runs`} icon={Activity} />
          </div>
        </Card>
      )}

      {gatewayRuntime && (
        <Card className="p-3">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-xs font-semibold text-slate-950 dark:text-slate-100">Gateway Runtime</h2>
            <div className="flex flex-wrap gap-1.5 text-[10px] font-semibold text-violet-700 dark:text-violet-400">
              <Link href="/provider-profiles" className="hover:underline">Providers</Link>
              <Link href="/gateway" className="hover:underline">Routes</Link>
              <Link href="/guardrails" className="hover:underline">Guardrails</Link>
              <Link href="/cache-config" className="hover:underline">Cache</Link>
            </div>
          </div>
          <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            <LifecycleCard title="Providers" value={`${gatewayRuntime.provider_context.distinct_providers} providers`} detail={`${gatewayRuntime.provider_context.active_routes} routes`} icon={Network} />
            <LifecycleCard title="Guardrails" value={`${gatewayRuntime.guardrail_context.active_rules} rules`} detail={`${gatewayRuntime.guardrail_context.blocks_30d} blocks (30d)`} icon={ShieldCheck} />
            <LifecycleCard title="Cache" value={`${gatewayRuntime.cache_context.total_hits.toLocaleString()} hits`} detail={`$${num(gatewayRuntime.cache_context.savings_usd).toFixed(2)} saved`} icon={Sparkles} />
            <LifecycleCard title="Rate Limits" value={`${gatewayRuntime.rate_limit_context.routes_with_rpm_limits} RPM-limited`} detail={`${gatewayRuntime.rate_limit_context.routes_with_cost_limits} cost-limited`} icon={Clock} />
          </div>
        </Card>
      )}

      <PayloadPanel run={run} />

      <div className="grid gap-3 xl:grid-cols-2">
        <ProviderTable calls={run.provider_calls} />
        <ToolTable calls={run.tool_calls} />
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        <OutcomeTable outcomes={outcomes} />
        <SpanTable spans={run.spans} />
      </div>
    </div>
  )
}

export default async function RequestExplorerPage({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const page = Number.parseInt(searchParams.page ?? '1', 10)
  const accessGroupId = searchParams.access_group_id
  const accessGroupDashboard = accessGroupId
    ? await getAccessGroupDashboard(session.apiKey, accessGroupId).catch(() => null)
    : null
  const accessGroup = accessGroupDashboard?.groups[0] ?? null
  let requestExplorer: Awaited<ReturnType<typeof getRequestExplorer>>
  try {
    requestExplorer = await getRequestExplorer(session.apiKey, {
      q: searchParams.q,
      status: searchParams.status,
      intent: searchParams.feature_tag,
      end_user_id: searchParams.end_user_id,
      model: searchParams.model,
      provider: searchParams.provider,
      optimization: searchParams.optimization,
      access_group_id: accessGroupId,
      tag: searchParams.tag,
      tool_name: searchParams.tool_name,
      security_event_only: searchParams.security_event_only === 'true',
      page: Number.isFinite(page) && page > 0 ? page : 1,
      page_size: 50,
    })
  } catch {
    requestExplorer = { items: [], total: 0, page: 1, page_size: 50 }
  }
  const selectedId = searchParams.run_id ?? requestExplorer.items[0]?.run_id ?? null

  const [runResult, governanceResult, graphResult, outcomesResult, gatewayResult, finopsResult, orgIdentityResult, gatewayRuntimeResult, scopePostureResult] = selectedId
    ? await Promise.allSettled([
        getRun(session.apiKey, selectedId, { access_group_id: accessGroupId }),
        getRunGovernanceContext(session.apiKey, selectedId, { access_group_id: accessGroupId }),
        getRunGraph(session.apiKey, selectedId, { access_group_id: accessGroupId }),
        listOutcomes(session.apiKey, { run_id: selectedId, limit: 20 }),
        listGatewayRequests(session.apiKey, { limit: 100 }),
        getInvestigationFinopsBudgetPosture(session.apiKey, { access_group_id: accessGroupId }),
        getInvestigationOrgIdentityPosture(session.apiKey),
        getInvestigationGatewayRuntimePosture(session.apiKey, { access_group_id: accessGroupId }),
        getOverviewScopePosture(session.apiKey),
      ])
    : []

  const selectedRun = runResult?.status === 'fulfilled' ? runResult.value : null
  const governance = governanceResult?.status === 'fulfilled' ? governanceResult.value : null
  const finops = finopsResult?.status === 'fulfilled' ? finopsResult.value : null
  const orgIdentity = orgIdentityResult?.status === 'fulfilled' ? orgIdentityResult.value : null
  const gatewayRuntimePosture = gatewayRuntimeResult?.status === 'fulfilled' ? gatewayRuntimeResult.value : null
  const scopePosture = scopePostureResult?.status === 'fulfilled' ? scopePostureResult.value : null
  const graphNodeCount = graphResult?.status === 'fulfilled' ? graphResult.value.nodes.length : 0
  const outcomes = outcomesResult?.status === 'fulfilled' ? outcomesResult.value.items : []
  const gatewayRequests = gatewayResult?.status === 'fulfilled' ? gatewayResult.value.items : []
  const gatewayMatch = selectedRun ? matchingGatewayRequest(selectedRun, gatewayRequests) : null
  const failedCount = requestExplorer.items.filter((request) => request.status === 'error' || request.status === 'failed').length
  const highCostRequest = requestExplorer.items.reduce<RequestRecord | null>((winner, request) => {
    if (!winner) return request
    return numericCost(request.cost_usd) > numericCost(winner.cost_usd) ? request : winner
  }, null)
  const pageCount = Math.max(1, Math.ceil(requestExplorer.total / requestExplorer.page_size))

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-950 dark:text-slate-100">Request Explorer</h1>
          <p className="text-xs text-slate-600 dark:text-slate-400">Debug individual AI requests — prompt, route, tools, cost, latency, cache, outcome.</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Link href={accessGroupId ? `/analytics?scope=workspace&access_group_id=${encodeURIComponent(accessGroupId)}` : '/analytics'} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-700 shadow-sm hover:bg-blue-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
            Analytics <ArrowRight className="h-3 w-3" />
          </Link>
          <Link href={accessGroupId ? `/request-flow?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-flow'} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-700 shadow-sm hover:bg-blue-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
            Flow <Route className="h-3 w-3" />
          </Link>
          {highCostRequest && (
            <Link href={requestHref(searchParams, { run_id: highCostRequest.run_id })} className="inline-flex items-center gap-1 rounded-lg bg-slate-950 px-2 py-1 text-xs font-semibold text-white shadow-sm hover:bg-slate-800 dark:bg-blue-600 dark:hover:bg-blue-700">
              Highest cost <DollarSign className="h-3 w-3" />
            </Link>
          )}
        </div>
      </div>

      <FilterBar searchParams={searchParams} />

      {accessGroup && (
        <div className="rounded-lg border border-blue-200 bg-blue-50/80 px-3 py-2 text-xs text-blue-900 dark:border-blue-700 dark:bg-blue-900/30 dark:text-blue-200">
          Filtered to <span className="font-semibold">{accessGroup.name}</span> access group.
        </div>
      )}

      <div className="flex flex-wrap items-center gap-1.5">
        <Chip label="Loaded" value={requestExplorer.items.length.toLocaleString()} icon={GitBranch} />
        <Chip label="Failures" value={failedCount.toLocaleString()} icon={ShieldCheck} />
        <Chip label="Highest" value={highCostRequest ? formatCost(highCostRequest.cost_usd) : '$0.00'} icon={DollarSign} />
        <Chip label="Gateway" value={gatewayResult?.status === 'fulfilled' ? 'Available' : 'Unavailable'} icon={Route} />
        <span className="ml-auto text-[11px] text-slate-500 dark:text-slate-400">
          Page {requestExplorer.page}/{pageCount} · {requestExplorer.total.toLocaleString()} total
          {requestExplorer.page > 1 && (
            <Link href={requestHref(searchParams, { page: String(requestExplorer.page - 1) })} className="ml-2 font-semibold text-blue-600 hover:underline dark:text-blue-400">Prev</Link>
          )}
          {requestExplorer.page < pageCount && (
            <Link href={requestHref(searchParams, { page: String(requestExplorer.page + 1) })} className="ml-2 font-semibold text-blue-600 hover:underline dark:text-blue-400">Next</Link>
          )}
        </span>
      </div>

      <div className="grid gap-3 xl:grid-cols-[280px_1fr]">
        <RunList requests={requestExplorer.items} selectedRunId={selectedRun?.id ?? selectedId} searchParams={searchParams} />
        {selectedRun ? (
          <RequestDetail run={selectedRun} graphNodeCount={graphNodeCount} outcomes={outcomes} gatewayMatch={gatewayMatch} accessGroupId={accessGroupId} governance={governance} finops={finops} orgIdentity={orgIdentity} gatewayRuntime={gatewayRuntimePosture} scopePosture={scopePosture} />
        ) : (
          <Card className="flex items-center justify-center p-8 text-center">
            <div>
              <p className="text-sm font-semibold text-slate-950 dark:text-slate-100">Select a request</p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Choose a run from the list to inspect it.</p>
            </div>
          </Card>
        )}
      </div>

      <div className="grid gap-2 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-800/90">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Workflow</p>
          <p className="mt-1 text-xs font-semibold text-slate-950 dark:text-slate-100">Start in Analytics, narrow with Request Flow, inspect here.</p>
        </div>
        <Link
          href={accessGroupId ? `/runs?access_group_id=${encodeURIComponent(accessGroupId)}` : '/runs'}
          className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/70 dark:border-slate-700 dark:bg-slate-800/90 dark:hover:border-blue-600 dark:hover:bg-blue-900/20"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Run Detail</p>
          <p className="mt-1 text-xs font-semibold text-slate-950 dark:text-slate-100">Open the full run investigation page</p>
        </Link>
        <Link
          href="/sessions"
          className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/70 dark:border-slate-700 dark:bg-slate-800/90 dark:hover:border-blue-600 dark:hover:bg-blue-900/20"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Sessions</p>
          <p className="mt-1 text-xs font-semibold text-slate-950 dark:text-slate-100">Pivot into session-level investigation</p>
        </Link>
      </div>
    </div>
  )
}
