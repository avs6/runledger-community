import Link from 'next/link'
import { ArrowRight, Lightbulb, Maximize2, Minimize2, RotateCcw, Search, Sparkles, Users, ZoomIn, ZoomOut } from 'lucide-react'
import type { GatewayRequestLog, OutcomeResponse, RunDetailResponse, RunFlowRecord, RunFlowResponse, RunListItem } from '@/types/api'
import { formatCost, formatTokens } from '@/lib/utils'
import RequestFlowDownloadButtons from './RequestFlowDownloadButtons'

export type RequestFlowMode =
  | 'request-intent-model-result'
  | 'user-intent-model'
  | 'prompt-skill-agent-model-tool-result'
  | 'request-route-provider-outcome'
  | 'workspace-app-agent-model-cost'

export type RequestFlowMetric = 'requests' | 'cost' | 'tokens' | 'savings'
export type RequestFlowScope = 'workspace' | 'org' | 'platform'
export type RequestFlowDensity = 'compact' | 'comfortable' | 'presentation'

type NodeLayer = {
  key: string
  label: string
}

type FlowNode = {
  id: string
  key: string
  label: string
  layer: number
  value: number
  cost: number
  inputTokens: number
  outputTokens: number
  latencyTotal: number
  latencyCount: number
  successCount: number
  savings: number
  runIds: Set<string>
}

type FlowLink = {
  source: string
  target: string
  value: number
  cost: number
  inputTokens: number
  outputTokens: number
  latencyTotal: number
  latencyCount: number
  successCount: number
  savings: number
  runIds: Set<string>
  hints: Record<string, string>
}

type EnrichedRun = {
  run: RunListItem
  record?: RunFlowRecord
  detail: RunDetailResponse | null
  gateway: GatewayRequestLog | null
  outcome: OutcomeResponse | null
  cost: number
  inputTokens: number
  outputTokens: number
  latencyMs: number | null
  success: boolean
  savings: number
}

const COLORS = [
  '#2563eb',
  '#0891b2',
  '#16a34a',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#0f766e',
  '#db2777',
  '#64748b',
  '#ea580c',
]

const FLOW_MODES: Array<{ key: RequestFlowMode; label: string; description: string; layers: NodeLayer[] }> = [
  {
    key: 'request-intent-model-result',
    label: 'Request to result',
    description: 'The executive view of where requests go by intent, selected model, and final status.',
    layers: [
      { key: 'request', label: 'Requests' },
      { key: 'intent', label: 'Intent' },
      { key: 'model', label: 'Model' },
      { key: 'result', label: 'Result' },
    ],
  },
  {
    key: 'user-intent-model',
    label: 'User to model',
    description: 'Shows which users or service accounts are driving intents and model selection.',
    layers: [
      { key: 'user', label: 'User' },
      { key: 'intent', label: 'Intent' },
      { key: 'model', label: 'Model' },
    ],
  },
  {
    key: 'prompt-skill-agent-model-tool-result',
    label: 'Prompt lifecycle',
    description: 'Follows a task from prompt capture through skill, agent, model, tool, and result.',
    layers: [
      { key: 'prompt', label: 'Prompt' },
      { key: 'skill', label: 'Skill' },
      { key: 'agent', label: 'Agent' },
      { key: 'model', label: 'Model' },
      { key: 'tool', label: 'Tool' },
      { key: 'result', label: 'Result' },
    ],
  },
  {
    key: 'request-route-provider-outcome',
    label: 'Route to outcome',
    description: 'Connects incoming traffic to Gateway routing, provider selection, and business outcome.',
    layers: [
      { key: 'request', label: 'Request' },
      { key: 'route', label: 'Route' },
      { key: 'provider', label: 'Provider' },
      { key: 'outcome', label: 'Outcome' },
    ],
  },
  {
    key: 'workspace-app-agent-model-cost',
    label: 'Workspace cost flow',
    description: 'Groups traffic by workspace, app, agent, model, and cost band for FinOps triage.',
    layers: [
      { key: 'workspace', label: 'Workspace' },
      { key: 'application', label: 'Application' },
      { key: 'agent', label: 'Agent' },
      { key: 'model', label: 'Model' },
      { key: 'cost', label: 'Cost' },
    ],
  },
]

const METRICS: Array<{ key: RequestFlowMetric; label: string }> = [
  { key: 'requests', label: 'Requests' },
  { key: 'cost', label: 'Cost' },
  { key: 'tokens', label: 'Tokens' },
  { key: 'savings', label: 'Savings' },
]

const SCOPES: Array<{ key: RequestFlowScope; label: string }> = [
  { key: 'workspace', label: 'Workspace' },
  { key: 'org', label: 'Org' },
  { key: 'platform', label: 'Platform' },
]

const DENSITIES: Array<{ key: RequestFlowDensity; label: string }> = [
  { key: 'compact', label: 'Compact' },
  { key: 'comfortable', label: 'Comfortable' },
  { key: 'presentation', label: 'Presentation' },
]

const TOP_N_OPTIONS = [6, 8, 10, 12, 16]

const DENSITY_CONFIG: Record<
  RequestFlowDensity,
  {
    height: number
    nodeWidth: number
    nodeHeight: number
    labelMax: number
    rowPadding: number
    layerSpacing: number
  }
> = {
  compact: {
    height: 460,
    nodeWidth: 140,
    nodeHeight: 44,
    labelMax: 18,
    rowPadding: 18,
    layerSpacing: 250,
  },
  comfortable: {
    height: 580,
    nodeWidth: 160,
    nodeHeight: 52,
    labelMax: 22,
    rowPadding: 24,
    layerSpacing: 305,
  },
  presentation: {
    height: 760,
    nodeWidth: 190,
    nodeHeight: 62,
    labelMax: 28,
    rowPadding: 30,
    layerSpacing: 380,
  },
}

function cleanLabel(value: string | null | undefined, fallback: string) {
  const label = value?.trim()
  return label && label.length > 0 ? label : fallback
}

function numeric(value: string | number | null | undefined) {
  const parsed = typeof value === 'number' ? value : parseFloat(value ?? '0')
  return Number.isFinite(parsed) ? parsed : 0
}

function metadataValue(detail: RunDetailResponse | null, keys: string[]) {
  for (const span of detail?.spans ?? []) {
    for (const key of keys) {
      const value = span.metadata?.[key]
      if (typeof value === 'string' && value.trim()) return value
      if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    }
  }
  return null
}

function modelProvider(model: string | null | undefined) {
  const value = cleanLabel(model, 'Provider unknown')
  if (value.includes('/')) return value.split('/')[0]
  if (value.toLowerCase().includes('claude')) return 'Anthropic'
  if (value.toLowerCase().includes('gpt') || value.toLowerCase().includes('o3')) return 'OpenAI'
  if (value.toLowerCase().includes('gemini')) return 'Google'
  if (value.toLowerCase().includes('llama') || value.toLowerCase().includes('qwen') || value.toLowerCase().includes('deepseek')) return 'Local / Ollama'
  return 'Provider unknown'
}

function costBand(cost: number) {
  if (cost <= 0) return 'No cost'
  if (cost < 0.001) return '< $0.001'
  if (cost < 0.01) return '$0.001 - $0.01'
  if (cost < 0.1) return '$0.01 - $0.10'
  return '$0.10+'
}

function runTokens(run: RunListItem, detail: RunDetailResponse | null) {
  const input = run.total_input_tokens ?? detail?.provider_calls.reduce((sum, call) => sum + (call.input_tokens ?? 0), 0) ?? 0
  const output = run.total_output_tokens ?? detail?.provider_calls.reduce((sum, call) => sum + (call.output_tokens ?? 0), 0) ?? 0
  return { input, output }
}

function matchingGateway(run: RunListItem, requests: GatewayRequestLog[]) {
  if (requests.length === 0) return null
  const runTime = new Date(run.started_at).getTime()
  const runModel = run.primary_model?.toLowerCase()
  const matches = requests
    .map((request) => ({
      request,
      distance: Math.abs(new Date(request.created_at).getTime() - runTime),
    }))
    .filter(({ request, distance }) => {
      const modelMatch = !runModel || request.model_used?.toLowerCase() === runModel || request.model_requested.toLowerCase() === runModel
      return modelMatch && distance <= 5 * 60 * 1000
    })
    .sort((a, b) => a.distance - b.distance)
  return matches[0]?.request ?? null
}

function matchingOutcome(run: RunListItem, outcomes: OutcomeResponse[]) {
  return outcomes.find((outcome) => outcome.run_id === run.id) ?? null
}

function estimateSavings(run: RunListItem, detail: RunDetailResponse | null, gateway: GatewayRequestLog | null) {
  const cachedTokens = detail?.provider_calls.reduce((sum, call) => sum + (call.cached_input_tokens ?? 0), 0) ?? 0
  const totalTokens = (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0)
  const cost = numeric(run.total_cost_usd)
  if (cachedTokens > 0 && totalTokens > 0 && cost > 0) return cost * (cachedTokens / Math.max(totalTokens - cachedTokens, 1))
  if (gateway?.cache_hit) return Math.max(cost, 0.000001)
  return 0
}

function enrichRuns(
  runs: RunListItem[],
  details: RunDetailResponse[],
  gatewayRequests: GatewayRequestLog[],
  outcomes: OutcomeResponse[]
): EnrichedRun[] {
  const detailsByRun = new Map(details.map((detail) => [detail.id, detail]))
  return runs.map((run) => {
    const detail = detailsByRun.get(run.id) ?? null
    const gateway = matchingGateway(run, gatewayRequests)
    const outcome = matchingOutcome(run, outcomes)
    const tokens = runTokens(run, detail)
    return {
      run,
      detail,
      gateway,
      outcome,
      cost: numeric(run.total_cost_usd),
      inputTokens: tokens.input,
      outputTokens: tokens.output,
      latencyMs: run.duration_ms ?? gateway?.latency_ms ?? null,
      success: outcome?.success ?? run.status === 'succeeded',
      savings: estimateSavings(run, detail, gateway),
    }
  })
}

function enrichFlowRecords(records: RunFlowRecord[]): EnrichedRun[] {
  return records.map((record) => ({
    run: {
      id: record.id,
      api_key_id: null,
      status: record.status as RunListItem['status'],
      end_user_id: record.end_user_id,
      session_id: null,
      feature_tag: record.feature_tag,
      deployment_version: null,
      total_cost_usd: record.total_cost_usd,
      total_input_tokens: record.total_input_tokens,
      total_output_tokens: record.total_output_tokens,
      started_at: record.started_at,
      ended_at: null,
      duration_ms: record.latency_ms,
      primary_model: record.primary_model,
    },
    record,
    detail: null,
    gateway: null,
    outcome: null,
    cost: numeric(record.total_cost_usd),
    inputTokens: record.total_input_tokens,
    outputTokens: record.total_output_tokens,
    latencyMs: record.latency_ms,
    success: record.success,
    savings: numeric(record.savings_usd),
  }))
}

function nodeId(layer: string, label: string) {
  return `${layer}:${label}`
}

function addNode(nodes: Map<string, FlowNode>, id: string, key: string, label: string, layer: number, run: EnrichedRun) {
  const existing = nodes.get(id)
  if (existing) {
    existing.value += 1
    existing.cost += run.cost
    existing.inputTokens += run.inputTokens
    existing.outputTokens += run.outputTokens
    existing.successCount += run.success ? 1 : 0
    existing.savings += run.savings
    existing.runIds.add(run.run.id)
    if (run.latencyMs !== null) {
      existing.latencyTotal += run.latencyMs
      existing.latencyCount += 1
    }
    return
  }
  nodes.set(id, {
    id,
    key,
    label,
    layer,
    value: 1,
    cost: run.cost,
    inputTokens: run.inputTokens,
    outputTokens: run.outputTokens,
    latencyTotal: run.latencyMs ?? 0,
    latencyCount: run.latencyMs === null ? 0 : 1,
    successCount: run.success ? 1 : 0,
    savings: run.savings,
    runIds: new Set([run.run.id]),
  })
}

function addLink(links: Map<string, FlowLink>, source: string, target: string, run: EnrichedRun, hints: Record<string, string>) {
  const key = `${source}->${target}`
  const existing = links.get(key)
  if (existing) {
    existing.value += 1
    existing.cost += run.cost
    existing.inputTokens += run.inputTokens
    existing.outputTokens += run.outputTokens
    existing.successCount += run.success ? 1 : 0
    existing.savings += run.savings
    existing.runIds.add(run.run.id)
    if (run.latencyMs !== null) {
      existing.latencyTotal += run.latencyMs
      existing.latencyCount += 1
    }
    return
  }
  links.set(key, {
    source,
    target,
    value: 1,
    cost: run.cost,
    inputTokens: run.inputTokens,
    outputTokens: run.outputTokens,
    latencyTotal: run.latencyMs ?? 0,
    latencyCount: run.latencyMs === null ? 0 : 1,
    successCount: run.success ? 1 : 0,
    savings: run.savings,
    runIds: new Set([run.run.id]),
    hints,
  })
}

function categoryFor(run: EnrichedRun, key: string) {
  if (run.record) {
    const record = run.record
    switch (key) {
      case 'request':
        return 'Incoming Requests'
      case 'intent':
        return cleanLabel(record.feature_tag, 'General / Untagged')
      case 'skill':
        return record.skill
      case 'agent':
        return record.agent
      case 'model':
        return cleanLabel(record.primary_model, 'Model unknown')
      case 'tool':
        return record.tool
      case 'result':
        return record.status.charAt(0).toUpperCase() + record.status.slice(1)
      case 'route':
        return record.route
      case 'provider':
        return cleanLabel(record.provider, 'Provider unknown')
      case 'outcome':
        return record.outcome
      case 'user':
        return cleanLabel(record.end_user_id, 'Anonymous / Service')
      case 'workspace':
        return record.workspace_name
      case 'application':
        return record.application
      case 'cost':
        return record.cost_band
      case 'prompt':
        return record.prompt
      default:
        return 'Unknown'
    }
  }

  const { detail, gateway, outcome, run: item } = run
  switch (key) {
    case 'request':
      return 'Incoming Requests'
    case 'intent':
      return cleanLabel(item.feature_tag ?? metadataValue(detail, ['intent', 'task.intent', 'workflow_type']), 'General / Untagged')
    case 'skill':
      return cleanLabel(metadataValue(detail, ['skill', 'skill_name', 'selected_skill', 'runledger.skill']), 'No skill captured')
    case 'agent':
      return cleanLabel(
        metadataValue(detail, ['agent_name', 'agent', 'selected_agent', 'agent_client', 'workflow_agent']) ??
          detail?.spans.find((span) => span.span_type === 'agent')?.name,
        cleanLabel(item.feature_tag, 'Agent unknown')
      )
    case 'model':
      return cleanLabel(item.primary_model ?? detail?.provider_calls[0]?.model ?? gateway?.model_used, 'Model unknown')
    case 'tool':
      return cleanLabel(
        detail?.tool_calls[0]?.tool_name ?? detail?.spans.find((span) => span.span_type === 'tool')?.name,
        'No tool called'
      )
    case 'result':
      return item.status.charAt(0).toUpperCase() + item.status.slice(1)
    case 'route':
      return cleanLabel(gateway?.model_requested ?? metadataValue(detail, ['route_alias', 'gateway.alias']), 'Direct SDK / OTLP')
    case 'provider':
      return cleanLabel(detail?.provider_calls[0]?.provider ?? modelProvider(gateway?.model_used ?? item.primary_model), 'Provider unknown')
    case 'outcome':
      return outcome ? `${outcome.outcome_type}: ${outcome.success ? 'Success' : 'Miss'}` : item.status
    case 'user':
      return cleanLabel(item.end_user_id, 'Anonymous / Service')
    case 'workspace':
      return cleanLabel(
        metadataValue(detail, ['workspace_name', 'workspace', 'workspace_id']) ?? item.feature_tag,
        'Workspace unknown'
      )
    case 'application':
      return cleanLabel(metadataValue(detail, ['application', 'app', 'service.name', 'service']), 'App unknown')
    case 'cost':
      return costBand(run.cost)
    case 'prompt':
      return detail?.input_payload?.length ? 'Prompt captured' : cleanLabel(item.feature_tag, 'Prompt metadata only')
    default:
      return 'Unknown'
  }
}

function buildFlow(enrichedRuns: EnrichedRun[], mode: RequestFlowMode) {
  const config = FLOW_MODES.find((item) => item.key === mode) ?? FLOW_MODES[0]
  const nodes = new Map<string, FlowNode>()
  const links = new Map<string, FlowLink>()

  for (const run of enrichedRuns) {
    const labels = config.layers.map((layer, index) => ({
      ...layer,
      index,
      label: categoryFor(run, layer.key),
    }))

    labels.forEach((layer) => addNode(nodes, nodeId(layer.key, layer.label), layer.key, layer.label, layer.index, run))
    for (let index = 0; index < labels.length - 1; index += 1) {
      const source = labels[index]
      const target = labels[index + 1]
      addLink(links, nodeId(source.key, source.label), nodeId(target.key, target.label), run, {
        [source.key]: source.label,
        [target.key]: target.label,
      })
    }
  }

  return {
    config,
    nodes: Array.from(nodes.values()),
    links: Array.from(links.values()),
  }
}

function metricValue(item: FlowLink | FlowNode, metric: RequestFlowMetric) {
  if (metric === 'cost') return item.cost
  if (metric === 'tokens') return item.inputTokens + item.outputTokens
  if (metric === 'savings') return item.savings
  return item.value
}

function metricLabel(item: FlowLink | FlowNode, metric: RequestFlowMetric) {
  const value = metricValue(item, metric)
  if (metric === 'cost' || metric === 'savings') return formatCost(String(value))
  if (metric === 'tokens') return formatTokens(value)
  return `${value.toLocaleString()} reqs`
}

function avgLatency(item: FlowLink | FlowNode) {
  return item.latencyCount > 0 ? `${Math.round(item.latencyTotal / item.latencyCount).toLocaleString()} ms` : 'n/a'
}

function successRate(item: FlowLink | FlowNode) {
  return item.value > 0 ? `${Math.round((item.successCount / item.value) * 100)}%` : '0%'
}

function tooltip(item: FlowLink | FlowNode) {
  return [
    `${item.value.toLocaleString()} requests`,
    `Input tokens: ${formatTokens(item.inputTokens)}`,
    `Output tokens: ${formatTokens(item.outputTokens)}`,
    `Cost: ${formatCost(String(item.cost))}`,
    `Estimated savings: ${formatCost(String(item.savings))}`,
    `Average latency: ${avgLatency(item)}`,
    `Success rate: ${successRate(item)}`,
  ].join('\n')
}

function truncate(label: string, max = 24) {
  return label.length > max ? `${label.slice(0, max - 1)}...` : label
}

function requestExplorerHref(
  link: FlowLink,
  enrichedRuns: EnrichedRun[],
  scope: RequestFlowScope,
  accessGroupId?: string
) {
  const linkRunIds = link.runIds
  const matchingRuns = enrichedRuns.filter((item) => linkRunIds.has(item.run.id))
  const params = new URLSearchParams()
  const same = (selector: (item: EnrichedRun) => string | null | undefined) => {
    const values = new Set(matchingRuns.map(selector).filter(Boolean) as string[])
    return values.size === 1 ? Array.from(values)[0] : null
  }
  const feature = same((item) => item.run.feature_tag)
  const model = same((item) => item.run.primary_model)
  const status = same((item) => item.run.status)
  const user = same((item) => item.run.end_user_id)
  const workspace = same((item) => item.record?.workspace_id)

  if (feature) params.set('feature_tag', feature)
  if (model) params.set('model', model)
  if (status) params.set('status', status)
  if (user) params.set('end_user_id', user)
  if (workspace && scope !== 'workspace') params.set('workspace_id', workspace)
  if (accessGroupId) params.set('access_group_id', accessGroupId)
  if (!params.toString() && matchingRuns[0]) params.set('run_id', matchingRuns[0].run.id)
  return `/request-explorer${params.toString() ? `?${params.toString()}` : ''}`
}

type FlowViewOptions = {
  basePath?: string
  density?: RequestFlowDensity
  topN?: number
  zoom?: number
  collapseSmall?: boolean
  accessGroupId?: string
}

function pageHref(mode: RequestFlowMode, metric: RequestFlowMetric, scope: RequestFlowScope, options: FlowViewOptions = {}) {
  const params = new URLSearchParams({
    mode,
    metric,
    scope,
  })
  if (options.density) params.set('density', options.density)
  if (options.topN) params.set('top', String(options.topN))
  if (options.zoom && options.zoom !== 1) params.set('zoom', options.zoom.toFixed(2).replace(/\.?0+$/, ''))
  if (options.collapseSmall === false) params.set('collapse', '0')
  if (options.accessGroupId) params.set('access_group_id', options.accessGroupId)
  return `${options.basePath ?? '/request-flow'}?${params.toString()}`
}

function flowLinkHref(basePath: string, mode: RequestFlowMode, metric: RequestFlowMetric, scope: RequestFlowScope, options: FlowViewOptions) {
  return pageHref(mode, metric, scope, { ...options, basePath })
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function aggregateOtherNodes(
  nodes: FlowNode[],
  links: FlowLink[],
  layers: NodeLayer[],
  topN: number,
  collapseSmall: boolean,
  metric: RequestFlowMetric
) {
  if (!collapseSmall) {
    const layerGroups = layers.map((_, layer) =>
      nodes.filter((node) => node.layer === layer).sort((a, b) => metricValue(b, metric) - metricValue(a, metric)).slice(0, topN)
    )
    const visibleIds = new Set(layerGroups.flat().map((node) => node.id))
    return {
      layerGroups,
      links: links.filter((link) => visibleIds.has(link.source) && visibleIds.has(link.target)),
    }
  }

  const visibleByLayer = new Map<number, Set<string>>()
  const otherNodes = new Map<number, FlowNode>()
  const otherId = (layer: number) => nodeId(layers[layer]?.key ?? `layer-${layer}`, 'Other')
  const cloneNode = (node: FlowNode): FlowNode => ({
    ...node,
    runIds: new Set(node.runIds),
  })
  const mergeNode = (target: FlowNode, source: FlowNode) => {
    target.value += source.value
    target.cost += source.cost
    target.inputTokens += source.inputTokens
    target.outputTokens += source.outputTokens
    target.latencyTotal += source.latencyTotal
    target.latencyCount += source.latencyCount
    target.successCount += source.successCount
    target.savings += source.savings
    source.runIds.forEach((runId) => target.runIds.add(runId))
  }

  const layerGroups = layers.map((layer, index) => {
    const sorted = nodes.filter((node) => node.layer === index).sort((a, b) => metricValue(b, metric) - metricValue(a, metric))
    const keep = sorted.slice(0, topN).map(cloneNode)
    visibleByLayer.set(index, new Set(keep.map((node) => node.id)))
    const overflow = sorted.slice(topN)
    if (overflow.length > 0) {
      const other: FlowNode = {
        id: otherId(index),
        key: layer.key,
        label: 'Other',
        layer: index,
        value: 0,
        cost: 0,
        inputTokens: 0,
        outputTokens: 0,
        latencyTotal: 0,
        latencyCount: 0,
        successCount: 0,
        savings: 0,
        runIds: new Set(),
      }
      overflow.forEach((node) => mergeNode(other, node))
      otherNodes.set(index, other)
      keep.push(other)
    }
    return keep
  })

  const nodesById = new Map(layerGroups.flat().map((node) => [node.id, node]))
  const linkGroups = new Map<string, FlowLink>()

  for (const link of links) {
    const sourceNode = nodes.find((node) => node.id === link.source)
    const targetNode = nodes.find((node) => node.id === link.target)
    if (!sourceNode || !targetNode) continue
    const sourceVisible = visibleByLayer.get(sourceNode.layer)?.has(sourceNode.id)
    const targetVisible = visibleByLayer.get(targetNode.layer)?.has(targetNode.id)
    const source = sourceVisible ? sourceNode.id : otherNodes.get(sourceNode.layer)?.id
    const target = targetVisible ? targetNode.id : otherNodes.get(targetNode.layer)?.id
    if (!source || !target || source === target || !nodesById.has(source) || !nodesById.has(target)) continue
    const key = `${source}->${target}`
    const existing = linkGroups.get(key)
    if (existing) {
      existing.value += link.value
      existing.cost += link.cost
      existing.inputTokens += link.inputTokens
      existing.outputTokens += link.outputTokens
      existing.latencyTotal += link.latencyTotal
      existing.latencyCount += link.latencyCount
      existing.successCount += link.successCount
      existing.savings += link.savings
      link.runIds.forEach((runId) => existing.runIds.add(runId))
      continue
    }
    linkGroups.set(key, {
      ...link,
      source,
      target,
      runIds: new Set(link.runIds),
    })
  }

  return {
    layerGroups,
    links: Array.from(linkGroups.values()),
  }
}

function svgEscape(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function flowSvgDownloadUrl({
  config,
  layerX,
  layerGroups,
  links,
  positions,
  width,
  height,
  nodeWidth,
  nodeHeight,
  metric,
}: {
  config: (typeof FLOW_MODES)[number]
  layerX: number[]
  layerGroups: FlowNode[][]
  links: FlowLink[]
  positions: Map<string, { x: number; y: number; color: string }>
  width: number
  height: number
  nodeWidth: number
  nodeHeight: number
  metric: RequestFlowMetric
}) {
  const maxLink = Math.max(...links.map((link) => metricValue(link, metric)), 1)
  const paths = links
    .map((link) => {
      const source = positions.get(link.source)
      const target = positions.get(link.target)
      if (!source || !target) return ''
      const strokeWidth = 2 + (metricValue(link, metric) / maxLink) * 24
      const d = `M ${source.x + nodeWidth} ${source.y} C ${source.x + nodeWidth + 90} ${source.y}, ${target.x - 90} ${target.y}, ${target.x} ${target.y}`
      return `<path d="${d}" fill="none" stroke="${target.color}" stroke-opacity="0.34" stroke-width="${strokeWidth}" stroke-linecap="round" />`
    })
    .join('')
  const labels = config.layers
    .map((layer, index) => `<text x="${layerX[index]}" y="38" fill="#475569" font-size="12" font-family="Aptos, Segoe UI, sans-serif" font-weight="700" letter-spacing="2">${svgEscape(layer.label.toUpperCase())}</text>`)
    .join('')
  const nodeMarkup = layerGroups
    .flat()
    .map((node) => {
      const pos = positions.get(node.id)
      if (!pos) return ''
      const y = pos.y - nodeHeight / 2
      return `<g transform="translate(${pos.x}, ${y})"><rect width="${nodeWidth}" height="${nodeHeight}" rx="14" fill="#ffffff" stroke="#d7e1ec" /><rect width="5" height="${nodeHeight}" rx="3" fill="${pos.color}" /><text x="16" y="${nodeHeight * 0.42}" fill="#0f172a" font-size="13" font-family="Aptos, Segoe UI, sans-serif" font-weight="700">${svgEscape(truncate(node.label, 24))}</text><text x="16" y="${nodeHeight * 0.72}" fill="#64748b" font-size="11" font-family="Aptos, Segoe UI, sans-serif">${svgEscape(metricLabel(node, metric))}</text></g>`
    })
    .join('')
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#f8fbff" />${paths}${labels}${nodeMarkup}</svg>`
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

function topList(enrichedRuns: EnrichedRun[], key: string, limit = 5) {
  const groups = new Map<string, { label: string; runs: number; cost: number; tokens: number }>()
  for (const run of enrichedRuns) {
    const label = categoryFor(run, key)
    const existing = groups.get(label) ?? { label, runs: 0, cost: 0, tokens: 0 }
    existing.runs += 1
    existing.cost += run.cost
    existing.tokens += run.inputTokens + run.outputTokens
    groups.set(label, existing)
  }
  return Array.from(groups.values()).sort((a, b) => b.cost - a.cost || b.runs - a.runs).slice(0, limit)
}

function recommendations(enrichedRuns: EnrichedRun[]) {
  const total = enrichedRuns.length
  const cacheable = enrichedRuns.filter((run) => !run.gateway?.cache_hit && categoryFor(run, 'intent') !== 'General / Untagged').length
  const failed = enrichedRuns.filter((run) => !run.success).length
  const unknownAgent = enrichedRuns.filter((run) => categoryFor(run, 'agent') === 'Agent unknown').length
  const highCost = [...enrichedRuns].sort((a, b) => b.cost - a.cost)[0]
  const recs: string[] = []

  if (total > 0 && cacheable / total > 0.35) recs.push('Cache repeatable intent traffic and compare savings from Request Explorer.')
  if (total > 0 && failed / total > 0.1) recs.push('Investigate failed request paths and compare model/route choices.')
  if (total > 0 && unknownAgent / total > 0.25) recs.push('Add agent_name or agent_client metadata so cost can be attributed to agents.')
  if (highCost && highCost.cost > 0) recs.push(`Review the highest-cost path first: ${cleanLabel(highCost.run.feature_tag, highCost.run.id)}.`)
  return recs.length ? recs : ['Traffic looks clean for this sample. Add richer skill/tool metadata to unlock deeper optimization advice.']
}

function InfoCard({
  title,
  icon,
  children,
}: {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/85 p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-950">
        {icon}
        {title}
      </div>
      {children}
    </div>
  )
}

export default function RequestFlowSankey({
  flow,
  runs,
  runDetails,
  gatewayRequests,
  outcomes,
  scope,
  mode,
  metric,
  density = 'comfortable',
  topN = 8,
  zoom = 1,
  collapseSmall = true,
  focus = false,
  basePath = '/request-flow',
  accessGroupId,
}: {
  flow?: RunFlowResponse | null
  runs?: RunListItem[]
  runDetails?: RunDetailResponse[]
  gatewayRequests?: GatewayRequestLog[]
  outcomes?: OutcomeResponse[]
  scope: RequestFlowScope
  mode: RequestFlowMode
  metric: RequestFlowMetric
  density?: RequestFlowDensity
  topN?: number
  zoom?: number
  collapseSmall?: boolean
  focus?: boolean
  basePath?: string
  accessGroupId?: string
}) {
  const sample = flow ? flow.items : (runs ?? []).slice(0, 200)
  const enrichedRuns = flow
    ? enrichFlowRecords(flow.items)
    : enrichRuns(runs ?? [], runDetails ?? [], gatewayRequests ?? [], outcomes ?? [])
  const { config, nodes, links } = buildFlow(enrichedRuns, mode)
  const normalizedTopN = clamp(topN, 3, 24)
  const normalizedZoom = clamp(zoom, 0.5, 4)
  const activeDensity = DENSITY_CONFIG[density] ? density : 'comfortable'
  const densityConfig = DENSITY_CONFIG[activeDensity]
  const viewOptions = {
    density: activeDensity,
    topN: normalizedTopN,
    zoom: normalizedZoom,
    collapseSmall,
    accessGroupId,
  }

  if (sample.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white/80 p-10 text-center">
        <p className="text-sm font-semibold text-slate-900">No request flow yet</p>
        <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
          Send traffic through the SDK, OTLP, or Gateway and this view will map requests into intent, model, tool, and result paths.
        </p>
      </div>
    )
  }

  const { layerGroups, links: visibleLinks } = aggregateOtherNodes(nodes, links, config.layers, normalizedTopN, collapseSmall, metric)
  const maxLink = Math.max(...visibleLinks.map((link) => metricValue(link, metric)), 1)
  const positions = new Map<string, { x: number; y: number; color: string }>()
  const layerCount = Math.max(config.layers.length, 2)
  const maxLayerItems = Math.max(...layerGroups.map((group) => group.length), 1)
  const minLayerHeight = 110 + maxLayerItems * (densityConfig.nodeHeight + densityConfig.rowPadding)
  const diagramWidth = Math.max(
    focus ? 3200 : 1120,
    160 + (layerCount - 1) * (focus ? densityConfig.layerSpacing * 1.35 : densityConfig.layerSpacing) + densityConfig.nodeWidth + 140,
  )
  const diagramHeight = Math.max(densityConfig.height, minLayerHeight)
  const layerX = config.layers.map((_, index) => 70 + index * ((diagramWidth - densityConfig.nodeWidth - 140) / (layerCount - 1)))

  layerGroups.forEach((group, layer) => {
    const availableHeight = diagramHeight - 120
    const gap = Math.max(densityConfig.nodeHeight + densityConfig.rowPadding, availableHeight / Math.max(group.length, 1))
    group.forEach((node, index) => {
      positions.set(node.id, {
        x: layerX[layer],
        y: 72 + gap * index + gap / 2,
        color: COLORS[(index + layer) % COLORS.length],
      })
    })
  })

  const topPrompts = topList(enrichedRuns, 'prompt')
  const topUsers = topList(enrichedRuns, 'user')
  const topAgents = topList(enrichedRuns, 'agent')
  const recs = recommendations(enrichedRuns)
  const focusHref = pageHref(config.key, metric, scope, { ...viewOptions, basePath: '/request-flow/focus', zoom: 1 })
  const exitHref = pageHref(config.key, metric, scope, { ...viewOptions, basePath: '/request-flow', zoom: 1 })
  const svgId = focus ? 'request-flow-focus-svg' : 'request-flow-svg'
  const fileBase = `runledger-request-flow-${config.key}`
  const svgDownloadUrl = flowSvgDownloadUrl({
    config,
    layerX,
    layerGroups,
    links: visibleLinks,
    positions,
    width: diagramWidth,
    height: diagramHeight,
    nodeWidth: densityConfig.nodeWidth,
    nodeHeight: densityConfig.nodeHeight,
    metric,
  })

  return (
    <div className={focus ? 'space-y-4' : 'space-y-4'}>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="font-display text-lg font-semibold tracking-[-0.03em] text-slate-950">AI Request Flow</h2>
              <p className="mt-1 max-w-3xl text-xs text-slate-500">{config.description}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700">
                {(flow?.sampled_runs ?? sample.length).toLocaleString()} of {(flow?.total_runs ?? sample.length).toLocaleString()} runs
              </span>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                {scope} scope / {flow?.workspace_count ?? 1} workspace{(flow?.workspace_count ?? 1) === 1 ? '' : 's'}
              </span>
              <Link
                href={accessGroupId ? `/request-explorer?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-explorer'}
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
              >
                Request Explorer <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <RequestFlowDownloadButtons svgId={svgId} svgHref={svgDownloadUrl} fileBase={fileBase} />
              <Link
                href={focus ? exitHref : focusHref}
                className="inline-flex items-center gap-1.5 rounded-full bg-slate-900 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-700"
              >
                {focus ? 'Exit Focus' : 'Expand Flow'} {focus ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
              </Link>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {SCOPES.map((item) => (
              <Link
                key={item.key}
                href={flowLinkHref(basePath, config.key, metric, item.key, viewOptions)}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                  item.key === scope
                    ? 'bg-slate-900 text-white'
                    : 'border border-slate-200 bg-slate-50 text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {FLOW_MODES.map((item) => (
              <Link
                key={item.key}
                href={flowLinkHref(basePath, item.key, metric, scope, viewOptions)}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                  item.key === config.key
                    ? 'bg-slate-900 text-white'
                    : 'border border-slate-200 bg-slate-50 text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {METRICS.map((item) => (
              <Link
                key={item.key}
                href={flowLinkHref(basePath, config.key, item.key, scope, viewOptions)}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                  item.key === metric
                    ? 'bg-blue-100 text-blue-700'
                    : 'border border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-900'
                }`}
              >
                Thickness: {item.label}
              </Link>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Density</span>
            {DENSITIES.map((item) => (
              <Link
                key={item.key}
                href={flowLinkHref(basePath, config.key, metric, scope, { ...viewOptions, density: item.key })}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                  item.key === activeDensity
                    ? 'bg-slate-900 text-white'
                    : 'border border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-900'
                }`}
              >
                {item.label}
              </Link>
            ))}
            <span className="ml-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Top</span>
            {TOP_N_OPTIONS.map((item) => (
              <Link
                key={item}
                href={flowLinkHref(basePath, config.key, metric, scope, { ...viewOptions, topN: item })}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                  item === normalizedTopN
                    ? 'bg-slate-900 text-white'
                    : 'border border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-900'
                }`}
              >
                {item}
              </Link>
            ))}
            <Link
              href={flowLinkHref(basePath, config.key, metric, scope, { ...viewOptions, collapseSmall: !collapseSmall })}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                collapseSmall
                  ? 'bg-blue-100 text-blue-700'
                  : 'border border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-900'
              }`}
            >
              {collapseSmall ? 'Other: On' : 'Other: Off'}
            </Link>
            {focus ? (
              <>
                <span className="ml-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Zoom</span>
                <Link
                  href={flowLinkHref(basePath, config.key, metric, scope, { ...viewOptions, zoom: clamp(normalizedZoom - 0.25, 0.5, 4) })}
                  className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700"
                >
                  <ZoomOut className="h-3.5 w-3.5" /> Out
                </Link>
                <Link
                  href={flowLinkHref(basePath, config.key, metric, scope, { ...viewOptions, zoom: 1 })}
                  className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700"
                >
                  <RotateCcw className="h-3.5 w-3.5" /> Fit
                </Link>
                <Link
                  href={flowLinkHref(basePath, config.key, metric, scope, { ...viewOptions, zoom: clamp(normalizedZoom + 0.25, 0.5, 4) })}
                  className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700"
                >
                  <ZoomIn className="h-3.5 w-3.5" /> In
                </Link>
                {[2, 3, 4].map((item) => (
                  <Link
                    key={item}
                    href={flowLinkHref(basePath, config.key, metric, scope, { ...viewOptions, zoom: item })}
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      Math.round(normalizedZoom * 100) === item * 100
                        ? 'bg-slate-900 text-white'
                        : 'border border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-700'
                    }`}
                  >
                    {item * 100}%
                  </Link>
                ))}
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">{Math.round(normalizedZoom * 100)}%</span>
              </>
            ) : null}
          </div>
        </div>

        <div className="overflow-auto bg-gradient-to-br from-white via-slate-50 to-blue-50/50">
          <svg
            id={svgId}
            width={diagramWidth}
            height={diagramHeight}
            viewBox={`0 0 ${diagramWidth} ${diagramHeight}`}
            style={{
              width: `${diagramWidth * normalizedZoom}px`,
              height: `${diagramHeight * normalizedZoom}px`,
              minWidth: `${diagramWidth * normalizedZoom}px`,
            }}
            className="block bg-gradient-to-br from-white via-slate-50 to-blue-50/50"
          >
            <defs>
              <filter id="flow-shadow" x="-10%" y="-10%" width="120%" height="120%">
                <feDropShadow dx="0" dy="8" stdDeviation="10" floodColor="#334155" floodOpacity="0.16" />
              </filter>
            </defs>

            {visibleLinks.map((link, index) => {
              const source = positions.get(link.source)
              const target = positions.get(link.target)
              if (!source || !target) return null
              const width = 2 + (metricValue(link, metric) / maxLink) * 24
              const color = target.color
              const d = `M ${source.x + densityConfig.nodeWidth} ${source.y} C ${source.x + densityConfig.nodeWidth + 90} ${source.y}, ${target.x - 90} ${target.y}, ${target.x} ${target.y}`
              return (
                <a key={`${link.source}-${link.target}-${index}`} href={requestExplorerHref(link, enrichedRuns, scope, accessGroupId)}>
                  <path
                    d={d}
                    fill="none"
                    stroke={color}
                    strokeOpacity="0.34"
                    strokeWidth={width}
                    strokeLinecap="round"
                    className="transition-opacity hover:opacity-80"
                  >
                    <title>{tooltip(link)}</title>
                  </path>
                </a>
              )
            })}

            {config.layers.map((layer, index) => (
              <text key={layer.key} x={layerX[index]} y="38" className="fill-slate-500 text-[11px] font-bold uppercase tracking-[0.16em]">
                {layer.label}
              </text>
            ))}

            {layerGroups.flat().map((node) => {
              const pos = positions.get(node.id)
              if (!pos) return null
              return (
                <g key={node.id} transform={`translate(${pos.x}, ${pos.y - densityConfig.nodeHeight / 2})`} filter="url(#flow-shadow)">
                  <rect width={densityConfig.nodeWidth} height={densityConfig.nodeHeight} rx="14" className="fill-white stroke-slate-200" />
                  <rect x="0" width="5" height={densityConfig.nodeHeight} rx="2.5" fill={pos.color} />
                  <text x="16" y={densityConfig.nodeHeight * 0.4} className="fill-slate-950 text-[12px] font-semibold">
                    {truncate(node.label, densityConfig.labelMax)}
                  </text>
                  <text x="16" y={densityConfig.nodeHeight * 0.7} className="fill-slate-500 text-[10.5px]">
                    {metricLabel(node, metric)}
                  </text>
                  <title>{tooltip(node)}</title>
                </g>
              )
            })}
          </svg>
        </div>
      </div>

      <div className={`grid gap-4 lg:grid-cols-4 ${focus ? 'hidden' : ''}`}>
        <InfoCard title="Top Prompts" icon={<Search className="h-4 w-4 text-blue-600" />}>
          <RankedList items={topPrompts} />
        </InfoCard>
        <InfoCard title="Top Users" icon={<Users className="h-4 w-4 text-blue-600" />}>
          <RankedList items={topUsers} />
        </InfoCard>
        <InfoCard title="Top Agents" icon={<Sparkles className="h-4 w-4 text-blue-600" />}>
          <RankedList items={topAgents} />
        </InfoCard>
        <InfoCard title="Optimization Hints" icon={<Lightbulb className="h-4 w-4 text-amber-600" />}>
          <div className="space-y-2">
            {recs.slice(0, 4).map((rec) => (
              <p key={rec} className="rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
                {rec}
              </p>
            ))}
          </div>
        </InfoCard>
      </div>
    </div>
  )
}

function RankedList({ items }: { items: Array<{ label: string; runs: number; cost: number; tokens: number }> }) {
  if (items.length === 0) {
    return <p className="text-xs text-slate-500">No data yet.</p>
  }
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.label} className="rounded-xl bg-slate-50 px-3 py-2">
          <div className="flex items-center justify-between gap-3">
            <p className="truncate text-xs font-semibold text-slate-800">{item.label}</p>
            <p className="shrink-0 text-xs text-slate-500">{item.runs} reqs</p>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            {formatCost(String(item.cost))} / {formatTokens(item.tokens)}
          </p>
        </div>
      ))}
    </div>
  )
}
