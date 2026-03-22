/**
 * Mistral AI instrumentation (@mistralai/mistralai SDK).
 *
 * Wraps `client.chat.complete` and `client.chat.stream` so every call is
 * captured as a provider_call event.
 *
 * Usage:
 * ```ts
 * import { Mistral } from '@mistralai/mistralai'
 * import { RunLedger } from '@runledger/sdk'
 *
 * const rl = new RunLedger({ apiKey: 'rl_live_...' })
 * const client = new Mistral({ apiKey: process.env.MISTRAL_API_KEY! })
 * rl.instrumentMistral(client)
 *
 * const response = await client.chat.complete({
 *   model: 'mistral-large-latest',
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

// Minimal Mistral client shape
interface MistralChatLike {
  complete: (...args: unknown[]) => unknown
  _rl_instrumented?: boolean
}

interface MistralClientLike {
  chat: MistralChatLike
  _rl_instrumented?: boolean
}

interface MistralChatResponse {
  usage?: {
    promptTokens?: number
    completionTokens?: number
  }
  choices?: Array<{
    message?: { content?: string | null; role?: string }
    finishReason?: string
  }>
}

// ── Main patcher ──────────────────────────────────────────────────────────────

export function instrumentMistral(client: MistralClientLike, transport: Transport): void {
  if (client._rl_instrumented) return

  const chat = client.chat
  if (!chat || typeof chat.complete !== 'function') return

  const originalComplete = chat.complete.bind(chat)

  chat.complete = async function (...args: unknown[]): Promise<MistralChatResponse> {
    const params = (args[0] ?? {}) as Record<string, unknown>
    const model = String(params['model'] ?? 'unknown')
    return _wrapComplete(originalComplete, model, args, transport)
  }

  client._rl_instrumented = true
  chat._rl_instrumented = true
}

async function _wrapComplete(
  original: (...args: unknown[]) => unknown,
  model: string,
  args: unknown[],
  transport: Transport,
): Promise<MistralChatResponse> {
  const ctx = getContextSnapshot()
  const runId = ctx.runId ?? randomUUID()
  const spanId = randomUUID()
  const now = new Date().toISOString()
  const t0 = Date.now()

  transport.enqueue(_runStart(runId, model, now, ctx))
  transport.enqueue(_spanStart(runId, spanId, model, now))

  try {
    const result = await (original(...args) as Promise<MistralChatResponse>)
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
    name: `mistral:${model}`,
    started_at: startedAt,
  }
}

function _spanEnd(
  runId: string,
  spanId: string,
  status: 'succeeded' | 'failed',
  endedAt: string,
  result: MistralChatResponse | null,
): SpanEndEvent {
  const event: SpanEndEvent = {
    event_type: 'span_end',
    run_id: runId,
    span_id: spanId,
    status,
    ended_at: endedAt,
  }
  const content = result?.choices?.[0]?.message?.content
  if (content) event.metadata = { response: content, finish_reason: result?.choices?.[0]?.finishReason }
  return event
}

function _providerCall(
  runId: string,
  spanId: string,
  model: string,
  result: MistralChatResponse,
  latencyMs: number,
): ProviderCallEvent {
  const event: ProviderCallEvent = {
    event_type: 'provider_call',
    run_id: runId,
    span_id: spanId,
    provider: 'mistral',
    model,
    latency_ms: latencyMs,
    status: 'success',
  }
  if (result.usage?.promptTokens) event.input_tokens = result.usage.promptTokens
  if (result.usage?.completionTokens) event.output_tokens = result.usage.completionTokens
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
    provider: 'mistral',
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
  result: MistralChatResponse | null,
): RunEndEvent {
  const event: RunEndEvent = { event_type: 'run_end', run_id: runId, status, ended_at: endedAt }
  if (result?.usage?.promptTokens) event.total_input_tokens = result.usage.promptTokens
  if (result?.usage?.completionTokens) event.total_output_tokens = result.usage.completionTokens
  return event
}
