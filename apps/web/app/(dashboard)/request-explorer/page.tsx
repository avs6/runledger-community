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
import { formatCost, formatDuration, formatTimestamp, formatTokens, truncateId } from '@/lib/utils'
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
    <div className={`rounded-2xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-300 dark:bg-white/90 ${className}`}>
      {children}
    </div>
  )
}

function FactCard({ fact }: { fact: DebugFact }) {
  const Icon = fact.icon
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{fact.label}</p>
        <Icon className="h-4 w-4 text-blue-600" />
      </div>
      <p className="mt-2 truncate text-sm font-semibold text-slate-950" title={fact.value}>
        {fact.value}
      </p>
    </Card>
  )
}

function RunList({ requests, selectedRunId, searchParams }: { requests: RequestRecord[]; selectedRunId: string | null; searchParams: PageProps['searchParams'] }) {
  if (requests.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-sm font-semibold text-slate-950">No requests found</p>
        <p className="mt-1 text-sm text-slate-500">Try widening the filters or sending traffic through SDK, Gateway, or OTLP.</p>
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">Recent Requests</h2>
        <p className="mt-1 text-xs text-slate-500">Select one request to inspect prompt, route, tools, cost, and outcome.</p>
      </div>
      <div className="max-h-[640px] overflow-y-auto">
        {requests.map((request) => {
          const selected = request.run_id === selectedRunId
          const totalTokens = (request.input_tokens ?? 0) + (request.output_tokens ?? 0)
          return (
            <Link
              key={request.id}
              href={requestHref(searchParams, { run_id: request.run_id })}
              className={`block border-b border-slate-100 px-4 py-3 transition hover:bg-blue-50 ${selected ? 'bg-blue-50 ring-1 ring-inset ring-blue-200' : ''}`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-xs font-semibold text-slate-950">{truncateId(request.run_id, 10)}</span>
                <RunStatusBadge status={request.status === 'success' ? 'succeeded' : request.status === 'error' ? 'failed' : request.status as 'running' | 'succeeded' | 'failed' | 'cancelled'} />
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-500">
                <span className="truncate">{request.intent ?? 'General / Untagged'}</span>
                <span className="truncate text-right font-mono">{request.model}</span>
                <span>{formatCost(request.cost_usd)}</span>
                <span className="text-right">{formatTokens(totalTokens)} tokens</span>
              </div>
              <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                <span>{request.provider}</span>
                <span>{request.end_user_id ?? 'No user'}</span>
              </div>
            </Link>
          )
        })}
      </div>
    </Card>
  )
}

function FilterBar({ searchParams }: { searchParams: PageProps['searchParams'] }) {
  return (
    <form action="/request-explorer" className="grid gap-3 rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm dark:border-slate-300 dark:bg-white/80 md:grid-cols-11">
      {searchParams.access_group_id && <input type="hidden" name="access_group_id" value={searchParams.access_group_id} />}
      <div className="md:col-span-2">
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Search</label>
        <input
          name="q"
          defaultValue={searchParams.q ?? ''}
          placeholder="Run ID, user, model..."
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-blue-500/30"
        />
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Status</label>
        <select name="status" defaultValue={searchParams.status ?? ''} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900">
          <option value="">Any</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
          <option value="running">Running</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Intent</label>
        <input name="feature_tag" defaultValue={searchParams.feature_tag ?? ''} placeholder="support-chat" className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900" />
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Model</label>
        <input name="model" defaultValue={searchParams.model ?? ''} placeholder="gpt, claude..." className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900" />
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Provider</label>
        <input name="provider" defaultValue={searchParams.provider ?? ''} placeholder="openai, anthropic..." className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900" />
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Optimization</label>
        <input name="optimization" defaultValue={searchParams.optimization ?? ''} placeholder="cache, routing..." className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900" />
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Gov Tag</label>
        <input name="tag" defaultValue={searchParams.tag ?? ''} placeholder="pci, prod..." className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900" />
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Tool</label>
        <input name="tool_name" defaultValue={searchParams.tool_name ?? ''} placeholder="browser.search" className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900" />
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">API Key</label>
        <input name="api_key_id" defaultValue={searchParams.api_key_id ?? ''} placeholder="key_abc123..." className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900" />
      </div>
      <div className="flex items-end">
        <label className="flex h-[42px] w-full items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900">
          <input type="checkbox" name="security_event_only" value="true" defaultChecked={searchParams.security_event_only === 'true'} />
          Security only
        </label>
      </div>
      <div className="flex items-end gap-2">
        <button type="submit" className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700">
          <Search className="h-4 w-4" />
          Explore
        </button>
      </div>
    </form>
  )
}

function LifecycleCard({ title, value, detail, icon: Icon }: { title: string; value: string; detail: string; icon: React.ElementType }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-blue-600" />
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</p>
      </div>
      <p className="mt-2 text-sm font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p>
    </div>
  )
}

function PayloadPanel({ run }: { run: RunDetailResponse }) {
  const messages = run.input_payload ?? []
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-950">Prompt And Response</h2>
          <p className="mt-1 text-xs text-slate-500">Shown when Data Capture is sampled or full.</p>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
          {messages.length} input message{messages.length === 1 ? '' : 's'}
        </span>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Prompt</p>
          <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-700">{promptPreview(run)}</pre>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Final response</p>
          <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-700">{responsePreview(run)}</pre>
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
        call.risk_score == null ? '-' : call.risk_score.toFixed(2),
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
      <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-4">
        <Icon className="h-4 w-4 text-blue-600" />
        <h2 className="text-base font-semibold text-slate-950">{title}</h2>
        <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">{rows.length}</span>
      </div>
      {rows.length === 0 ? (
        <p className="p-8 text-center text-sm text-slate-500">{empty}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80">
                {headers.map((header) => (
                  <th key={header} className="px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${title}-${index}`} className="border-b border-slate-100">
                  {row.map((cell, cellIndex) => (
                    <td key={`${title}-${index}-${cellIndex}`} className="max-w-[280px] truncate px-4 py-2 text-xs text-slate-700" title={cell}>
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
    <div className="space-y-5">
      <Card className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold text-slate-950">Request {truncateId(run.id, 12)}</h2>
              <RunStatusBadge status={run.status} />
            </div>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Started {formatTimestamp(run.started_at)}. Session {run.session_id ?? 'not captured'}. Graph has {graphNodeCount} node{graphNodeCount === 1 ? '' : 's'}.
            </p>
          </div>
          <Link href={accessGroupId ? `/runs/${run.id}?access_group_id=${encodeURIComponent(accessGroupId)}` : `/runs/${run.id}`} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50">
            Open run detail <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {facts.map((fact) => (
          <FactCard key={fact.label} fact={fact} />
        ))}
      </div>

      <Card className="p-5">
        <h2 className="text-base font-semibold text-slate-950">Request Lifecycle</h2>
        <p className="mt-1 text-sm text-slate-500">Explains the path with the fields RunLedger captures today.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <LifecycleCard title="Prompt" value={run.input_payload ? 'Captured' : 'Not captured'} detail={run.input_payload ? `${run.input_payload.length} input message(s)` : 'Enable Data Capture for prompt text.'} icon={MessageSquareText} />
          <LifecycleCard title="Cache" value={cacheStatus(run, gatewayMatch)} detail="Uses provider cached-token evidence and Gateway cache logs when available." icon={Sparkles} />
          <LifecycleCard title="Route" value={routeAlias} detail={decision} icon={Route} />
          <LifecycleCard title="Outcome" value={outcomeLabel} detail={optimizationStatus(run, gatewayMatch)} icon={CheckCircle2} />
        </div>
      </Card>

      {governance && (
        <Card className="p-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-950">Governance Evidence</h2>
              <p className="mt-1 text-sm text-slate-500">Inline runtime evidence for tool governance, security, alerting, audit, and governance-pack posture.{scopePosture && ` ${scopePosture.tool_context.capture_policies} capture policies configured.`}</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-semibold text-cyan-700">
              <Link href="/tool-registry" className="hover:underline">Tool Registry</Link>
              <Link href="/tool-policies" className="hover:underline">Tool Policies</Link>
              <Link href="/data-capture" className="hover:underline">Data Capture</Link>
              <Link href="/security" className="hover:underline">Security</Link>
              <Link href="/alert-rules" className="hover:underline">Alert Rules</Link>
              <Link href="/audit" className="hover:underline">Audit Log</Link>
              <Link href="/governance-pack" className="hover:underline">Governance Pack</Link>
              <Link href="/tags" className="hover:underline">Tags</Link>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <LifecycleCard title="Tags" value={governance.tags.length ? governance.tags.join(', ') : 'No tags'} detail="Request and feature tags available for governance drill-through." icon={Tags} />
            <LifecycleCard title="Tool Policies" value={String(governance.tool_evidence.reduce((sum, item) => sum + item.matched_policy_count, 0))} detail={`${governance.tool_evidence.length} tools with policy evidence`} icon={Wrench} />
            <LifecycleCard title="Security Events" value={String(governance.security_events.length)} detail="Correlated by run, tool, or end user." icon={ShieldCheck} />
            <LifecycleCard title="Alerts / Audit" value={`${governance.alert_evidence.length} / ${governance.audit_events.length}`} detail="Recent alert firings and governance audit events in the same runtime window." icon={Activity} />
          </div>
        </Card>
      )}

      {finops && (
        <Card className="p-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-950">Budget Context</h2>
              <p className="mt-1 text-sm text-slate-500">FinOps budget posture for this request&apos;s workspace — budget utilization, billing periods, and chargeback attribution.</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-semibold text-emerald-700">
              <Link href="/budgets" className="hover:underline">Budgets</Link>
              <Link href="/billing" className="hover:underline">Billing Periods</Link>
              <Link href="/chargeback" className="hover:underline">Chargeback</Link>
              <Link href="/model-budgets" className="hover:underline">Model Budgets</Link>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <LifecycleCard title="Active Budgets" value={`${finops.budget_context.active_budgets} / ${finops.budget_context.budgets}`} detail={`${finops.budget_context.breach_count} budget(s) in breach`} icon={DollarSign} />
            <LifecycleCard title="Budget Limit" value={formatCost(finops.budget_context.total_limit_usd)} detail={`${finops.budget_context.active_overrides} active overrides`} icon={ShieldCheck} />
            <LifecycleCard title="30d Spend" value={formatCost(finops.spend_context.total_spend_30d)} detail={`${finops.spend_context.total_runs_30d.toLocaleString()} runs`} icon={Activity} />
            <LifecycleCard title="Billing" value={`${finops.billing_context.open_billing_periods} open`} detail={`${finops.billing_context.chargeback_rules} chargeback rules`} icon={Clock} />
          </div>
        </Card>
      )}

      {orgIdentity && (
        <Card className="p-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-950">Org Identity Context</h2>
              <p className="mt-1 text-sm text-slate-500">Organization identity posture — workspace users, API keys, telemetry, and MCP registry correlation for this request.</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-semibold text-blue-700">
              <Link href="/organization" className="hover:underline">Organization</Link>
              <Link href="/users" className="hover:underline">Users</Link>
              <Link href="/api-keys" className="hover:underline">API Keys</Link>
              <Link href="/telemetry" className="hover:underline">Telemetry</Link>
              <Link href="/mcp-registry" className="hover:underline">MCP Registry</Link>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <LifecycleCard title="Workspace Users" value={String(orgIdentity.user_context.workspace_users)} detail={`${orgIdentity.user_context.distinct_end_users_30d} distinct end users (30d)`} icon={User} />
            <LifecycleCard title="API Keys" value={`${orgIdentity.api_key_context.active_keys} active`} detail={`${orgIdentity.api_key_context.total_keys} total, ${orgIdentity.api_key_context.keys_with_traffic_30d} with traffic`} icon={KeyRound} />
            <LifecycleCard title="MCP Servers" value={String(orgIdentity.mcp_context.servers)} detail={`${orgIdentity.mcp_context.tool_calls_30d.toLocaleString()} tool calls (30d)`} icon={Network} />
            <LifecycleCard title="Telemetry" value={`${orgIdentity.telemetry_context.batches_30d.toLocaleString()} batches`} detail={`${orgIdentity.telemetry_context.runs_30d.toLocaleString()} runs (30d)`} icon={Activity} />
          </div>
        </Card>
      )}

      {gatewayRuntime && (
        <Card className="p-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-950">Gateway Runtime Context</h2>
              <p className="mt-1 text-sm text-slate-500">Provider routing, guardrails, cache, and rate limits for this request&apos;s workspace.</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-semibold text-violet-700">
              <Link href="/provider-profiles" className="hover:underline">Provider Profiles</Link>
              <Link href="/gateway" className="hover:underline">Gateway Routes</Link>
              <Link href="/guardrails" className="hover:underline">Guardrails</Link>
              <Link href="/cache-config" className="hover:underline">Response Cache</Link>
              <Link href="/rate-limits" className="hover:underline">Rate Limits</Link>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <LifecycleCard title="Providers" value={`${gatewayRuntime.provider_context.distinct_providers} providers`} detail={`${gatewayRuntime.provider_context.active_routes} active routes, ${gatewayRuntime.provider_context.routing_policies} policies`} icon={Network} />
            <LifecycleCard title="Guardrails" value={`${gatewayRuntime.guardrail_context.active_rules} rules`} detail={`${gatewayRuntime.guardrail_context.events_30d.toLocaleString()} events, ${gatewayRuntime.guardrail_context.blocks_30d} blocks (30d)`} icon={ShieldCheck} />
            <LifecycleCard title="Cache" value={`${gatewayRuntime.cache_context.total_hits.toLocaleString()} hits`} detail={`${gatewayRuntime.cache_context.enabled_configs} configs, $${gatewayRuntime.cache_context.savings_usd.toFixed(2)} saved`} icon={Sparkles} />
            <LifecycleCard title="Rate Limits" value={`${gatewayRuntime.rate_limit_context.routes_with_rpm_limits} RPM-limited`} detail={`${gatewayRuntime.rate_limit_context.routes_with_cost_limits} cost-limited routes`} icon={Clock} />
          </div>
        </Card>
      )}

      <PayloadPanel run={run} />

      <div className="grid gap-5 xl:grid-cols-2">
        <ProviderTable calls={run.provider_calls} />
        <ToolTable calls={run.tool_calls} />
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
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
  const requestExplorer = await getRequestExplorer(session.apiKey, {
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
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950">Request Explorer</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Debug individual AI requests from prompt to route, model, tool calls, cost, latency, cache behavior, and final outcome.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={accessGroupId ? `/analytics?scope=workspace&access_group_id=${encodeURIComponent(accessGroupId)}` : '/analytics'} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50">
            Analytics Overview <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href={accessGroupId ? `/request-flow?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-flow'} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50">
            Back to flow <Route className="h-4 w-4" />
          </Link>
          {highCostRequest && (
            <Link href={requestHref(searchParams, { run_id: highCostRequest.run_id })} className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-800">
              Inspect highest cost <DollarSign className="h-4 w-4" />
            </Link>
          )}
        </div>
      </div>

      <FilterBar searchParams={searchParams} />

      {accessGroup && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/80 px-4 py-3 text-sm text-blue-900">
          Request Explorer is filtered to the <span className="font-semibold">{accessGroup.name}</span> access group.
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <FactCard fact={{ label: 'Requests loaded', value: requestExplorer.items.length.toLocaleString(), icon: GitBranch }} />
        <FactCard fact={{ label: 'Failures', value: failedCount.toLocaleString(), icon: ShieldCheck }} />
        <FactCard fact={{ label: 'Highest cost', value: highCostRequest ? formatCost(highCostRequest.cost_usd) : '$0.00', icon: DollarSign }} />
        <FactCard fact={{ label: 'Gateway log', value: gatewayResult?.status === 'fulfilled' ? 'Available' : 'Unavailable for role', icon: Route }} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <RunList requests={requestExplorer.items} selectedRunId={selectedRun?.id ?? selectedId} searchParams={searchParams} />
        {selectedRun ? (
          <RequestDetail run={selectedRun} graphNodeCount={graphNodeCount} outcomes={outcomes} gatewayMatch={gatewayMatch} accessGroupId={accessGroupId} governance={governance} finops={finops} orgIdentity={orgIdentity} gatewayRuntime={gatewayRuntimePosture} scopePosture={scopePosture} />
        ) : (
          <Card className="p-12 text-center">
            <p className="text-base font-semibold text-slate-950">Select a request</p>
            <p className="mt-2 text-sm text-slate-500">Choose a recent run from the list to open its engineering debug view.</p>
          </Card>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Observe Workflow</p>
          <h2 className="mt-2 text-lg font-semibold text-slate-950">Use this after the flow view narrows the problem</h2>
          <p className="mt-2 text-sm text-slate-600">
            Start in Analytics Overview for scope health, move to Request Flow for routing causality, then use Request Explorer to inspect the exact run, prompt path, tools, route, and outcome evidence behind an edge.
          </p>
        </div>
        <Link
          href={accessGroupId ? `/runs?access_group_id=${encodeURIComponent(accessGroupId)}` : '/runs'}
          className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/70"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Run Detail</p>
          <h2 className="mt-2 text-lg font-semibold text-slate-950">Open the full run investigation page</h2>
          <p className="mt-2 text-sm text-slate-600">
            Jump into the run DAG, provider-call breakdown, payload capture, and cancellation flow when you need the dedicated execution-level view.
          </p>
        </Link>
        <Link
          href="/sessions"
          className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/70"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Conversation Context</p>
          <h2 className="mt-2 text-lg font-semibold text-slate-950">Pivot into Sessions</h2>
          <p className="mt-2 text-sm text-slate-600">
            Follow the same issue across multiple turns when cost, latency, or failure patterns span a whole conversation rather than a single request.
          </p>
        </Link>
      </div>

      <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white/90 px-4 py-3 text-sm text-slate-600 shadow-sm">
        <span>
          Page {requestExplorer.page} of {pageCount} • {requestExplorer.total.toLocaleString()} requests
        </span>
        <div className="flex items-center gap-2">
          {requestExplorer.page > 1 && (
            <Link
              href={requestHref(searchParams, { page: String(requestExplorer.page - 1) })}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-50"
            >
              Previous
            </Link>
          )}
          {requestExplorer.page < pageCount && (
            <Link
              href={requestHref(searchParams, { page: String(requestExplorer.page + 1) })}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-50"
            >
              Next
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
