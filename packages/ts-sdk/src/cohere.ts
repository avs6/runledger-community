/**
 * Cohere instrumentation (cohere-ai v7+ SDK, CohereClientV2).
 *
 * Wraps `client.chat` so every call is captured as a provider_call event.
 *
 * Usage:
 * ```ts
 * import { CohereClientV2 } from 'cohere-ai'
 * import { RunLedger } from '@runledger/sdk'
 *
 * const rl = new RunLedger({ apiKey: 'rl_live_...' })
 * const co = new CohereClientV2({ token: process.env.COHERE_API_KEY! })
 * rl.instrumentCohere(co)
 *
 * const response = await co.chat({
 *   model: 'command-r-plus',
 *   messages: [{ role: 'user', content: 'Hello' }],
 * })
 * ```
 */

import { randomUUID } from 'node:crypto'
import { getContextSnapshot } from './context.js'
import type { Transport } from './transport.js'
import type {
  RunStartEvent, RunEndEvent,
  SpanStartEvent, SpanEndEvent,
  ProviderCallEvent,
} from './types.js'

// Minimal Cohere v2 shape
interface CohereV2ClientLike {
  chat: (...args: unknown[]) => unknown
  _rl_instrumented?: boolean
}

interface CohereChatResponse {
  usage?: {
    tokens?: {
      inputTokens?: number
      outputTokens?: number
    }
    billedUnits?: {
      inputTokens?: number
      outputTokens?: number
    }
  }
  message?: {
    content?: Array<{ type?: string; text?: string }>
    role?: string
  }
  finishReason?: string
}

// ── Main patcher ──────────────────────────────────────────────────────────────

export function instrumentCohere(client: CohereV2ClientLike, transport: Transport): void {
  if (client._rl_instrumented) return

  const originalChat = client.chat.bind(client)

  client.chat = async function (...args: unknown[]): Promise<CohereChatResponse> {
    const params = (args[0] ?? {}) as Record<string, unknown>
    const model = String(params['model'] ?? 'unknown')
    return _wrapChat(originalChat, model, args, transport)
  }

  client._rl_instrumented = true
}

async function _wrapChat(
  original: (...args: unknown[]) => unknown,
  model: string,
  args: unknown[],
  transport: Transport,
): Promise<CohereChatResponse> {
  const ctx = getContextSnapshot()
  const runId = ctx.runId ?? randomUUID()
  const spanId = randomUUID()
  const now = new Date().toISOString()
  const t0 = Date.now()

  transport.enqueue(_runStart(runId, model, now, ctx))
  transport.enqueue(_spanStart(runId, spanId, model, now))

  try {
    const result = await (original(...args) as Promise<CohereChatResponse>)
    const latencyMs = Date.now() - t0
    const endedAt = new Date().toISOString()
    transport.enqueue(_spanEnd(runId, spanId, 'succeeded', endedAt, result))
    transport.enqueue(_providerCall(runId, spanId, model, result, latencyMs))
    transport.enqueue(_runEnd(runId, 'succeeded', endedAt, result))
    return result
  } catch (err) {
    const latencyMs = Date.now() - t0
    const endedAt = new Date().toISOString()
    transport.enqueue(_spanEnd(runId, spanId, 'failed', endedAt, null))
    transport.enqueue(_providerCallError(runId, spanId, model, err, latencyMs))
    transport.enqueue(_runEnd(runId, 'failed', endedAt, null))
    throw err
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function _extractUsage(result: CohereChatResponse): [number | undefined, number | undefined] {
  const tokens = result.usage?.tokens
  if (tokens?.inputTokens !== undefined) return [tokens.inputTokens, tokens.outputTokens]
  const billed = result.usage?.billedUnits
  if (billed?.inputTokens !== undefined) return [billed.inputTokens, billed.outputTokens]
  return [undefined, undefined]
}

function _extractText(result: CohereChatResponse): string | null {
  const parts = result.message?.content
  if (!parts) return null
  return parts.filter(p => p.type === 'text').map(p => p.text ?? '').join('') || null
}

// ── Event builders ─────────────────────────────────────────────────────────────

function _runStart(
  runId: string,
  model: string,
  startedAt: string,
  ctx: ReturnType<typeof getContextSnapshot>,
): RunStartEvent {
  const event: RunStartEvent = { event_type: 'run_start', run_id: runId, started_at: startedAt }
  if (ctx.endUserId) event.end_user_id = ctx.endUserId
  if (ctx.sessionId) event.session_id = ctx.sessionId
  if (ctx.featureTag) event.feature_tag = ctx.featureTag
  if (ctx.deploymentVersion) event.deployment_version = ctx.deploymentVersion
  if (model !== 'unknown') event.agent_name = model
  return event
}

function _spanStart(runId: string, spanId: string, model: string, startedAt: string): SpanStartEvent {
  return {
    event_type: 'span_start',
    run_id: runId,
    span_id: spanId,
    span_type: 'llm',
    name: `cohere:${model}`,
    started_at: startedAt,
  }
}

function _spanEnd(
  runId: string,
  spanId: string,
  status: 'succeeded' | 'failed',
  endedAt: string,
  result: CohereChatResponse | null,
): SpanEndEvent {
  const event: SpanEndEvent = {
    event_type: 'span_end',
    run_id: runId,
    span_id: spanId,
    status,
    ended_at: endedAt,
  }
  if (result) {
    const text = _extractText(result)
    if (text) event.metadata = { response: text }
  }
  return event
}

function _providerCall(
  runId: string,
  spanId: string,
  model: string,
  result: CohereChatResponse,
  latencyMs: number,
): ProviderCallEvent {
  const event: ProviderCallEvent = {
    event_type: 'provider_call',
    run_id: runId,
    span_id: spanId,
    provider: 'cohere',
    model,
    latency_ms: latencyMs,
    status: 'success',
  }
  const [inputTokens, outputTokens] = _extractUsage(result)
  if (inputTokens !== undefined) event.input_tokens = inputTokens
  if (outputTokens !== undefined) event.output_tokens = outputTokens
  return event
}

function _providerCallError(
  runId: string,
  spanId: string,
  model: string,
  err: unknown,
  latencyMs: number,
): ProviderCallEvent {
  return {
    event_type: 'provider_call',
    run_id: runId,
    span_id: spanId,
    provider: 'cohere',
    model,
    latency_ms: latencyMs,
    status: 'error',
    error_type: err instanceof Error ? err.constructor.name : 'UnknownError',
  }
}

function _runEnd(
  runId: string,
  status: 'succeeded' | 'failed',
  endedAt: string,
  result: CohereChatResponse | null,
): RunEndEvent {
  const event: RunEndEvent = { event_type: 'run_end', run_id: runId, status, ended_at: endedAt }
  const [inputTokens, outputTokens] = result ? _extractUsage(result) : [undefined, undefined]
  if (inputTokens !== undefined) event.total_input_tokens = inputTokens
  if (outputTokens !== undefined) event.total_output_tokens = outputTokens
  return event
}
