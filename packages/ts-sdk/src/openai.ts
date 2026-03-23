/**
 * OpenAI Node.js SDK instrumentation.
 *
 * Wraps `openai.chat.completions.create` (both streaming and non-streaming)
 * to emit RunLedger events without changing the caller API surface.
 *
 * Usage:
 * ```ts
 * import OpenAI from 'openai'
 * import { RunLedger } from '@runledger/sdk'
 *
 * const rl = new RunLedger({ apiKey: 'rl_live_...' })
 * const openai = new OpenAI()
 * rl.instrument(openai)
 *
 * // All subsequent calls are tracked automatically.
 * const resp = await openai.chat.completions.create({ model: 'gpt-4o', messages: [...] })
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

// Minimal OpenAI shape — avoids hard dependency on openai package types
interface OpenAILike {
  chat: {
    completions: {
      create: (...args: unknown[]) => unknown
    }
  }
  baseURL?: string
  _rl_instrumented?: boolean
}

interface CompletionParams {
  model?: string
  messages?: unknown[]
  stream?: boolean
  [key: string]: unknown
}

interface ChatCompletion {
  usage?: {
    prompt_tokens?: number
    completion_tokens?: number
    prompt_tokens_details?: { cached_tokens?: number }
  }
  choices?: Array<{
    message?: { content?: string | null; role?: string }
    finish_reason?: string
  }>
}

interface ChatCompletionChunk {
  choices?: Array<{
    delta?: { content?: string | null }
    finish_reason?: string | null
  }>
  usage?: {
    prompt_tokens?: number
    completion_tokens?: number
  }
  model?: string
}

type AsyncIterable_<T> = AsyncIterable<T> & { finalChatCompletion?(): Promise<ChatCompletion> }

// ── Main patcher ──────────────────────────────────────────────────────────────

/** Detect the provider name from an OpenAI-compatible client's baseURL. */
export function detectProvider(client: OpenAILike): string {
  const url = (client.baseURL ?? '').toLowerCase()
  if (!url || url.includes('openai.com')) return 'openai'
  if (url.includes('x.ai') || url.includes('xai.com')) return 'xai'
  if (url.includes('mistral.ai')) return 'mistral'
  if (url.includes('cohere.com')) return 'cohere'
  if (url.includes('anthropic.com')) return 'anthropic'
  if (url.includes('googleapis.com') || url.includes('generativelanguage')) return 'google'
  if (url.includes('11434') || url.includes('ollama')) return 'ollama'
  if (url.includes('together.xyz') || url.includes('togetherai')) return 'together'
  if (url.includes('fireworks.ai')) return 'fireworks'
  if (url.includes('groq.com')) return 'groq'
  if (url.includes('perplexity.ai')) return 'perplexity'
  if (url.includes('azure.com') || url.includes('openai.azure')) return 'azure-openai'
  // Fallback: extract second-level domain
  try {
    const host = new URL(url).hostname
    const parts = host.split('.')
    return parts.length >= 2 ? parts[parts.length - 2] : host
  } catch { return 'unknown' }
}

export function instrumentOpenAI(client: OpenAILike, transport: Transport): void {
  if (client._rl_instrumented) return

  const provider = detectProvider(client)
  const originalCreate = client.chat.completions.create.bind(client.chat.completions)

  client.chat.completions.create = function (...args: unknown[]): unknown {
    const params = (args[0] ?? {}) as CompletionParams
    const rest = args.slice(1)
    if (params?.stream) {
      return _wrapStreaming(originalCreate, params, rest, transport, provider)
    }
    return _wrapNonStreaming(originalCreate, params, rest, transport, provider)
  }

  client._rl_instrumented = true
}

// ── Non-streaming ─────────────────────────────────────────────────────────────

async function _wrapNonStreaming(
  original: (...args: unknown[]) => unknown,
  params: CompletionParams,
  rest: unknown[],
  transport: Transport,
  provider = 'openai',
): Promise<ChatCompletion> {
  const ctx = getContextSnapshot()
  const runId = ctx.runId ?? randomUUID()
  const spanId = randomUUID()
  const model = params.model ?? 'unknown'
  const now = new Date().toISOString()
  const t0 = Date.now()

  transport.enqueue(_runStart(runId, model, now, ctx))
  transport.enqueue(_spanStart(runId, spanId, model, now))

  try {
    const result = await (original(params, ...rest) as Promise<ChatCompletion>)
    const latencyMs = Date.now() - t0
    const endedAt = new Date().toISOString()
    transport.enqueue(_spanEnd(runId, spanId, 'succeeded', endedAt, result))
    transport.enqueue(_providerCall(runId, spanId, model, result, latencyMs, provider))
    transport.enqueue(_runEnd(runId, 'succeeded', endedAt, result))
    return result
  } catch (err) {
    const latencyMs = Date.now() - t0
    const endedAt = new Date().toISOString()
    transport.enqueue(_spanEnd(runId, spanId, 'failed', endedAt, null))
    transport.enqueue(_providerCallError(runId, spanId, model, err, latencyMs, provider))
    transport.enqueue(_runEnd(runId, 'failed', endedAt, null))
    throw err
  }
}

// ── Streaming ─────────────────────────────────────────────────────────────────

async function* _wrapStreaming(
  original: (...args: unknown[]) => unknown,
  params: CompletionParams,
  rest: unknown[],
  transport: Transport,
  provider = 'openai',
): AsyncGenerator<ChatCompletionChunk> {
  const ctx = getContextSnapshot()
  const runId = ctx.runId ?? randomUUID()
  const spanId = randomUUID()
  const model = params.model ?? 'unknown'
  const now = new Date().toISOString()
  const t0 = Date.now()

  transport.enqueue(_runStart(runId, model, now, ctx))
  transport.enqueue(_spanStart(runId, spanId, model, now))

  let promptTokens = 0
  let completionTokens = 0

  try {
    const stream = original(params, ...rest) as AsyncIterable_<ChatCompletionChunk>
    for await (const chunk of stream) {
      // Accumulate usage from the final chunk (many providers send usage on last chunk)
      if (chunk.usage) {
        promptTokens = chunk.usage.prompt_tokens ?? promptTokens
        completionTokens = chunk.usage.completion_tokens ?? completionTokens
      }
      yield chunk
    }

    const latencyMs = Date.now() - t0
    const endedAt = new Date().toISOString()
    const syntheticResult: ChatCompletion = {
      usage: { prompt_tokens: promptTokens, completion_tokens: completionTokens },
    }
    transport.enqueue(_spanEnd(runId, spanId, 'succeeded', endedAt, null))
    transport.enqueue(_providerCall(runId, spanId, model, syntheticResult, latencyMs, provider))
    transport.enqueue(_runEnd(runId, 'succeeded', endedAt, syntheticResult))
  } catch (err) {
    const latencyMs = Date.now() - t0
    const endedAt = new Date().toISOString()
    transport.enqueue(_spanEnd(runId, spanId, 'failed', endedAt, null))
    transport.enqueue(_providerCallError(runId, spanId, model, err, latencyMs, provider))
    transport.enqueue(_runEnd(runId, 'failed', endedAt, null))
    throw err
  }
}

// ── Event builders ────────────────────────────────────────────────────────────

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
    name: `openai:${model}`,
    started_at: startedAt,
  }
}

function _spanEnd(
  runId: string,
  spanId: string,
  status: 'succeeded' | 'failed',
  endedAt: string,
  result: ChatCompletion | null,
): SpanEndEvent {
  const event: SpanEndEvent = {
    event_type: 'span_end',
    run_id: runId,
    span_id: spanId,
    status,
    ended_at: endedAt,
  }
  if (result?.choices?.[0]?.message?.content) {
    event.metadata = {
      response: result.choices[0].message.content,
      finish_reason: result.choices[0].finish_reason,
    }
  }
  return event
}

function _providerCall(
  runId: string,
  spanId: string,
  model: string,
  result: ChatCompletion,
  latencyMs: number,
  provider = 'openai',
): ProviderCallEvent {
  const event: ProviderCallEvent = {
    event_type: 'provider_call',
    run_id: runId,
    span_id: spanId,
    provider,
    model,
    latency_ms: latencyMs,
    status: 'success',
  }
  if (result.usage?.prompt_tokens) event.input_tokens = result.usage.prompt_tokens
  if (result.usage?.completion_tokens) event.output_tokens = result.usage.completion_tokens

  // Provider request ID for invoice reconciliation
  if ((result as any).id) event.provider_request_id = (result as any).id

  // Prompt token details (cached, audio, text)
  const ptd = result.usage?.prompt_tokens_details as any
  if (ptd) {
    const cached = ptd.cached_tokens
    if (cached) event.cached_input_tokens = cached
    const inDet: Record<string, number> = {}
    if (ptd.cached_tokens) inDet.cached_tokens = ptd.cached_tokens
    if (ptd.audio_tokens) inDet.audio_tokens = ptd.audio_tokens
    if (ptd.text_tokens) inDet.text_tokens = ptd.text_tokens
    if (Object.keys(inDet).length > 0) event.input_tokens_details = inDet
  }

  // Completion token details (reasoning, audio, text)
  const ctd = (result.usage as any)?.completion_tokens_details
  if (ctd) {
    const outDet: Record<string, number> = {}
    if (ctd.reasoning_tokens) outDet.reasoning_tokens = ctd.reasoning_tokens
    if (ctd.audio_tokens) outDet.audio_tokens = ctd.audio_tokens
    if (ctd.text_tokens) outDet.text_tokens = ctd.text_tokens
    if (Object.keys(outDet).length > 0) event.output_tokens_details = outDet
  }

  return event
}

function _providerCallError(
  runId: string,
  spanId: string,
  model: string,
  err: unknown,
  latencyMs: number,
  provider = 'openai',
): ProviderCallEvent {
  return {
    event_type: 'provider_call',
    run_id: runId,
    span_id: spanId,
    provider,
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
  result: ChatCompletion | null,
): RunEndEvent {
  const event: RunEndEvent = {
    event_type: 'run_end',
    run_id: runId,
    status,
    ended_at: endedAt,
  }
  if (result?.usage?.prompt_tokens) event.total_input_tokens = result.usage.prompt_tokens
  if (result?.usage?.completion_tokens) event.total_output_tokens = result.usage.completion_tokens
  return event
}
