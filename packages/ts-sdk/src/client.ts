import { Transport } from './transport.js'
import { withRunLedgerContext, getContextSnapshot, getPropagationHeaders, contextFromHeaders } from './context.js'
import { instrumentOpenAI } from './openai.js'
import { instrumentGemini } from './gemini.js'
import { instrumentMistral } from './mistral.js'
import { instrumentCohere } from './cohere.js'
import type { RunLedgerOptions, ContextOptions } from './types.js'

/**
 * RunLedger client — the main entry point for the TypeScript SDK.
 *
 * @example
 * ```ts
 * import OpenAI from 'openai'
 * import { RunLedger } from '@runledger/sdk'
 *
 * const rl = new RunLedger({ apiKey: process.env.RUNLEDGER_API_KEY })
 * const openai = new OpenAI()
 * rl.instrument(openai)
 *
 * await rl.withContext({ endUserId: 'u_123', featureTag: 'support' }, async () => {
 *   const resp = await openai.chat.completions.create({
 *     model: 'gpt-4o',
 *     messages: [{ role: 'user', content: 'Hello' }],
 *   })
 * })
 *
 * await rl.flush()
 * ```
 */
export class RunLedger {
  private readonly _transport: Transport
  private readonly _opts: Required<Pick<RunLedgerOptions, 'baseUrl' | 'local' | 'budgetCheck' | 'privacyMode'>>

  constructor(opts: RunLedgerOptions = {}) {
    const apiKey = opts.apiKey ?? process.env['RUNLEDGER_API_KEY'] ?? ''
    const baseUrl =
      opts.baseUrl ?? process.env['RUNLEDGER_BASE_URL'] ?? 'https://api.runledger.io'
    const local = opts.local ?? process.env['RUNLEDGER_LOCAL'] === 'true'

    if (!local && !apiKey) {
      throw new Error(
        'RUNLEDGER_API_KEY is required. Pass it as apiKey option or set the RUNLEDGER_API_KEY env var.',
      )
    }

    this._opts = {
      baseUrl,
      local,
      budgetCheck: opts.budgetCheck ?? false,
      privacyMode: opts.privacyMode ?? 'metadata_only',
    }

    this._transport = new Transport({ apiKey, baseUrl, local })
  }

  // ── Instrumentation ────────────────────────────────────────────────────────

  /**
   * Instrument an OpenAI-compatible client (openai, xAI/Grok, Azure OpenAI, Groq,
   * Together, Fireworks, Perplexity). Provider is auto-detected from `client.baseURL`.
   *
   * Safe to call multiple times (idempotent).
   *
   * @param client An `openai.OpenAI` or compatible instance.
   */
  instrument(client: object): void {
    instrumentOpenAI(client as Parameters<typeof instrumentOpenAI>[0], this._transport)
  }

  /**
   * Instrument a `GoogleGenerativeAI` instance from `@google/generative-ai`.
   * All `getGenerativeModel()` calls will return instrumented models.
   *
   * @param genAI A `GoogleGenerativeAI` instance.
   */
  instrumentGemini(genAI: object): void {
    instrumentGemini(genAI as Parameters<typeof instrumentGemini>[0], this._transport)
  }

  /**
   * Instrument a Mistral `Mistral` client from `@mistralai/mistralai`.
   * Wraps `client.chat.complete`.
   *
   * @param client A `Mistral` client instance.
   */
  instrumentMistral(client: object): void {
    instrumentMistral(client as Parameters<typeof instrumentMistral>[0], this._transport)
  }

  /**
   * Instrument a Cohere `CohereClientV2` from `cohere-ai`.
   * Wraps `client.chat`.
   *
   * @param client A `CohereClientV2` instance.
   */
  instrumentCohere(client: object): void {
    instrumentCohere(client as Parameters<typeof instrumentCohere>[0], this._transport)
  }

  // ── Context ────────────────────────────────────────────────────────────────

  /**
   * Run an async function inside a RunLedger context.
   *
   * All instrumented calls within `fn` will be tagged with the provided
   * metadata. Contexts can be nested — inner overrides outer for specific fields.
   *
   * @returns Whatever `fn` returns.
   *
   * @example
   * ```ts
   * const result = await rl.withContext({ endUserId: 'u_123', featureTag: 'rag' }, async () => {
   *   return await openai.chat.completions.create({ ... })
   * })
   * ```
   */
  withContext<T>(options: ContextOptions, fn: (runId: string) => T | Promise<T>): Promise<T> {
    return withRunLedgerContext(options, fn)
  }

  /**
   * Return HTTP headers carrying the current RunLedger context.
   * Use to propagate context across service boundaries.
   */
  propagationHeaders(): Record<string, string> {
    return getPropagationHeaders()
  }

  /**
   * Restore RunLedger context from incoming HTTP headers.
   * Use on the receiving service side.
   */
  static contextFromHeaders(headers: Record<string, string>): ContextOptions {
    return contextFromHeaders(headers)
  }

  /**
   * Return the current context snapshot (useful for reading run_id etc.).
   */
  getContext() {
    return getContextSnapshot()
  }

  // ── Flush / shutdown ───────────────────────────────────────────────────────

  /** Flush all buffered events to the RunLedger API. */
  async flush(): Promise<void> {
    await this._transport.flush()
  }

  /** Flush and shut down the background flush timer. Call at process exit. */
  async shutdown(): Promise<void> {
    await this._transport.shutdown()
  }
}
