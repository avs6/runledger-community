/**
 * Google Gemini instrumentation (@google/generative-ai SDK).
 *
 * Wraps `model.generateContent` and `model.generateContentStream` on every
 * `GenerativeModel` instance so calls are captured as provider_call events.
 *
 * Usage:
 * ```ts
 * import { GoogleGenerativeAI } from '@google/generative-ai'
 * import { RunLedger } from '@runledger/sdk'
 *
 * const rl = new RunLedger({ apiKey: 'rl_live_...' })
 * const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY!)
 * rl.instrumentGemini(genAI)
 *
 * const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' })
 * const result = await model.generateContent('Hello')
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

// Minimal shape of @google/generative-ai
interface GenerativeModelLike {
  model: string
  generateContent: (...args: unknown[]) => unknown
  generateContentStream?: (...args: unknown[]) => unknown
  _rl_instrumented?: boolean
}

interface GoogleGenerativeAILike {
  getGenerativeModel: (...args: unknown[]) => GenerativeModelLike
  _rl_instrumented?: boolean
}

interface GenerateContentResponse {
  usageMetadata?: {
    promptTokenCount?: number
    candidatesTokenCount?: number
    cachedContentTokenCount?: number
  }
  candidates?: Array<{
    content?: { parts?: Array<{ text?: string }> }
  }>
  text?: () => string
}

interface GenerateContentResult {
  response: GenerateContentResponse
}

// ── Main patcher ──────────────────────────────────────────────────────────────

/**
 * Instrument a GoogleGenerativeAI instance. All `getGenerativeModel()` calls
 * will return instrumented models.
 */
export function instrumentGemini(genAI: GoogleGenerativeAILike, transport: Transport): void {
  if (genAI._rl_instrumented) return

  const originalGetModel = genAI.getGenerativeModel.bind(genAI)

  genAI.getGenerativeModel = function (...args: unknown[]): GenerativeModelLike {
    const model = originalGetModel(...args) as GenerativeModelLike
    _instrumentModel(model, transport)
    return model
  }

  genAI._rl_instrumented = true
}

function _instrumentModel(model: GenerativeModelLike, transport: Transport): void {
  if (model._rl_instrumented) return

  const modelName = model.model ?? 'unknown'
  const originalGenerate = model.generateContent.bind(model)

  model.generateContent = async function (...args: unknown[]): Promise<GenerateContentResult> {
    return _wrapGenerate(originalGenerate, modelName, args, transport)
  }

  model._rl_instrumented = true
}

async function _wrapGenerate(
  original: (...args: unknown[]) => unknown,
  modelName: string,
  args: unknown[],
  transport: Transport,
): Promise<GenerateContentResult> {
  const ctx = getContextSnapshot()
  const runId = ctx.runId ?? randomUUID()
  const spanId = randomUUID()
  const now = new Date().toISOString()
  const t0 = Date.now()

  transport.enqueue(_runStart(runId, modelName, now, ctx))
  transport.enqueue(_spanStart(runId, spanId, modelName, now))

  try {
    const result = await (original(...args) as Promise<GenerateContentResult>)
    const latencyMs = Date.now() - t0
    const endedAt = new Date().toISOString()
    const response = result?.response ?? {}
    transport.enqueue(_spanEnd(runId, spanId, 'succeeded', endedAt, response))
    transport.enqueue(_providerCall(runId, spanId, modelName, response, latencyMs))
    transport.enqueue(_runEnd(runId, 'succeeded', endedAt, response))
    return result
  } catch (err) {
    const latencyMs = Date.now() - t0
    const endedAt = new Date().toISOString()
    transport.enqueue(_spanEnd(runId, spanId, 'failed', endedAt, null))
    transport.enqueue(_providerCallError(runId, spanId, modelName, err, latencyMs))
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
    name: `google:${model}`,
    started_at: startedAt,
  }
}

function _spanEnd(
  runId: string,
  spanId: string,
  status: 'succeeded' | 'failed',
  endedAt: string,
  response: GenerateContentResponse | null,
): SpanEndEvent {
  const event: SpanEndEvent = {
    event_type: 'span_end',
    run_id: runId,
    span_id: spanId,
    status,
    ended_at: endedAt,
  }
  if (response) {
    const text = _extractText(response)
    if (text) event.metadata = { response: text }
  }
  return event
}

function _providerCall(
  runId: string,
  spanId: string,
  model: string,
  response: GenerateContentResponse,
  latencyMs: number,
): ProviderCallEvent {
  const event: ProviderCallEvent = {
    event_type: 'provider_call',
    run_id: runId,
    span_id: spanId,
    provider: 'google',
    model,
    latency_ms: latencyMs,
    status: 'success',
  }
  const meta = response.usageMetadata
  if (meta?.promptTokenCount) event.input_tokens = meta.promptTokenCount
  if (meta?.candidatesTokenCount) event.output_tokens = meta.candidatesTokenCount
  if (meta?.cachedContentTokenCount) event.cached_input_tokens = meta.cachedContentTokenCount
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
    provider: 'google',
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
  response: GenerateContentResponse | null,
): RunEndEvent {
  const event: RunEndEvent = { event_type: 'run_end', run_id: runId, status, ended_at: endedAt }
  const meta = response?.usageMetadata
  if (meta?.promptTokenCount) event.total_input_tokens = meta.promptTokenCount
  if (meta?.candidatesTokenCount) event.total_output_tokens = meta.candidatesTokenCount
  return event
}

function _extractText(response: GenerateContentResponse): string | null {
  try {
    if (typeof response.text === 'function') return response.text()
    const parts = response.candidates?.[0]?.content?.parts
    if (parts) return parts.map(p => p.text ?? '').join('') || null
  } catch { /* ignore */ }
  return null
}
