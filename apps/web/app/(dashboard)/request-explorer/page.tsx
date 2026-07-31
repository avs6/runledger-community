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
  Wrench,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getRun, getRunGraph, getRuns, listGatewayRequests, listOutcomes } from '@/lib/api'
import RunStatusBadge from '@/components/runs/RunStatusBadge'
import { formatCost, formatDuration, formatTimestamp, formatTokens, truncateId } from '@/lib/utils'
import type {
  GatewayRequestLog,
  OutcomeResponse,
  ProviderCallDetail,
  RunDetailResponse,
  RunListItem,
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

function RunList({ runs, selectedId, searchParams }: { runs: RunListItem[]; selectedId: string | null; searchParams: PageProps['searchParams'] }) {
  if (runs.length === 0) {
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
        {runs.map((run) => {
          const selected = run.id === selectedId
          const totalTokens = (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0)
          return (
            <Link
              key={run.id}
              href={requestHref(searchParams, { run_id: run.id })}
              className={`block border-b border-slate-100 px-4 py-3 transition hover:bg-blue-50 ${selected ? 'bg-blue-50 ring-1 ring-inset ring-blue-200' : ''}`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-xs font-semibold text-slate-950">{truncateId(run.id, 10)}</span>
                <RunStatusBadge status={run.status} />
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-500">
                <span className="truncate">{run.feature_tag ?? 'General / Untagged'}</span>
                <span className="truncate text-right font-mono">{run.primary_model ?? 'Model unknown'}</span>
                <span>{formatCost(run.total_cost_usd)}</span>
                <span className="text-right">{formatTokens(totalTokens)} tokens</span>
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
    <form action="/request-explorer" className="grid gap-3 rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm dark:border-slate-300 dark:bg-white/80 md:grid-cols-6">
      <div className="md:col-span-2">
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Search</label>
        <input
          name="q"
          defaultValue={searchParams.q ?? ''}
          placeholder="Run ID, user, feature..."
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
}: {
  run: RunDetailResponse
  graphNodeCount: number
  outcomes: OutcomeResponse[]
  gatewayMatch: GatewayRequestLog | null
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
          <Link href={`/runs/${run.id}`} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50">
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

  const runs = await getRuns(session.apiKey, {
    limit: 50,
    search: searchParams.q,
    status: searchParams.status,
    feature_tag: searchParams.feature_tag,
    end_user_id: searchParams.end_user_id,
    model: searchParams.model,
  })
  const selectedId = searchParams.run_id ?? runs.items[0]?.id ?? null

  const [runResult, graphResult, outcomesResult, gatewayResult] = selectedId
    ? await Promise.allSettled([
        getRun(session.apiKey, selectedId),
        getRunGraph(session.apiKey, selectedId),
        listOutcomes(session.apiKey, { run_id: selectedId, limit: 20 }),
        listGatewayRequests(session.apiKey, { limit: 100 }),
      ])
    : []

  const selectedRun = runResult?.status === 'fulfilled' ? runResult.value : null
  const graphNodeCount = graphResult?.status === 'fulfilled' ? graphResult.value.nodes.length : 0
  const outcomes = outcomesResult?.status === 'fulfilled' ? outcomesResult.value.items : []
  const gatewayRequests = gatewayResult?.status === 'fulfilled' ? gatewayResult.value.items : []
  const gatewayMatch = selectedRun ? matchingGatewayRequest(selectedRun, gatewayRequests) : null
  const failedCount = runs.items.filter((run) => run.status === 'failed').length
  const highCostRun = runs.items.reduce<RunListItem | null>((winner, run) => {
    if (!winner) return run
    return numericCost(run.total_cost_usd) > numericCost(winner.total_cost_usd) ? run : winner
  }, null)

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
          <Link href="/request-flow" className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50">
            Back to flow <Route className="h-4 w-4" />
          </Link>
          {highCostRun && (
            <Link href={requestHref(searchParams, { run_id: highCostRun.id })} className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-800">
              Inspect highest cost <DollarSign className="h-4 w-4" />
            </Link>
          )}
        </div>
      </div>

      <FilterBar searchParams={searchParams} />

      <div className="grid gap-4 md:grid-cols-4">
        <FactCard fact={{ label: 'Requests loaded', value: runs.items.length.toLocaleString(), icon: GitBranch }} />
        <FactCard fact={{ label: 'Failures', value: failedCount.toLocaleString(), icon: ShieldCheck }} />
        <FactCard fact={{ label: 'Highest cost', value: highCostRun ? formatCost(highCostRun.total_cost_usd) : '$0.00', icon: DollarSign }} />
        <FactCard fact={{ label: 'Gateway log', value: gatewayResult?.status === 'fulfilled' ? 'Available' : 'Unavailable for role', icon: Route }} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <RunList runs={runs.items} selectedId={selectedRun?.id ?? selectedId} searchParams={searchParams} />
        {selectedRun ? (
          <RequestDetail run={selectedRun} graphNodeCount={graphNodeCount} outcomes={outcomes} gatewayMatch={gatewayMatch} />
        ) : (
          <Card className="p-12 text-center">
            <p className="text-base font-semibold text-slate-950">Select a request</p>
            <p className="mt-2 text-sm text-slate-500">Choose a recent run from the list to open its engineering debug view.</p>
          </Card>
        )}
      </div>
    </div>
  )
}
