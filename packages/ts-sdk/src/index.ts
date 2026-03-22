/**
 * @runledger/sdk — RunLedger TypeScript SDK
 *
 * Instrument OpenAI (and other LLM clients) with billing-grade observability,
 * budget enforcement, and analytics.
 *
 * @example
 * ```ts
 * import OpenAI from 'openai'
 * import { RunLedger, withRunLedgerContext } from '@runledger/sdk'
 *
 * const rl = new RunLedger({ apiKey: process.env.RUNLEDGER_API_KEY })
 * const openai = new OpenAI()
 * rl.instrument(openai)
 *
 * await rl.withContext({ endUserId: 'u_123', featureTag: 'support' }, async () => {
 *   const resp = await openai.chat.completions.create({ model: 'gpt-4o', messages: [...] })
 * })
 *
 * await rl.flush()
 * ```
 */

export { RunLedger } from './client.js'
export {
  withRunLedgerContext,
  getContextSnapshot,
  getRunId,
  getPropagationHeaders,
  contextFromHeaders,
} from './context.js'
export { instrumentOpenAI, detectProvider } from './openai.js'
export { instrumentGemini } from './gemini.js'
export { instrumentMistral } from './mistral.js'
export { instrumentCohere } from './cohere.js'
export type {
  RunLedgerOptions,
  ContextOptions,
  RunLedgerContextData,
  RunLedgerEvent,
  RunStartEvent,
  RunEndEvent,
  SpanStartEvent,
  SpanEndEvent,
  ProviderCallEvent,
} from './types.js'
