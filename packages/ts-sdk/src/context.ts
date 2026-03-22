import { AsyncLocalStorage } from 'node:async_hooks'
import { randomUUID } from 'node:crypto'
import type { RunLedgerContextData, ContextOptions } from './types.js'

// ── Storage ───────────────────────────────────────────────────────────────────

const _storage = new AsyncLocalStorage<RunLedgerContextData>()

const _empty: RunLedgerContextData = {
  runId: null,
  endUserId: null,
  sessionId: null,
  featureTag: null,
  deploymentVersion: null,
}

/** Return the current context, or an empty context if outside a RunLedgerContext. */
export function getContextSnapshot(): RunLedgerContextData {
  return _storage.getStore() ?? { ..._empty }
}

/** Return the current run ID (auto-generated if inside a context, null otherwise). */
export function getRunId(): string | null {
  return _storage.getStore()?.runId ?? null
}

// ── RunLedgerContext ──────────────────────────────────────────────────────────

/**
 * Runs a callback inside a RunLedger context.
 *
 * All instrumented calls within `fn` will be associated with this context's
 * run_id and metadata. Contexts can be nested — inner contexts override
 * specific fields while inheriting others.
 *
 * @example
 * ```ts
 * const runId = await withRunLedgerContext({ endUserId: 'u_123' }, async () => {
 *   const resp = await openai.chat.completions.create({ ... })
 *   return getRunId()
 * })
 * ```
 */
export function withRunLedgerContext<T>(
  options: ContextOptions,
  fn: (runId: string) => T | Promise<T>,
): Promise<T> {
  const parent = _storage.getStore() ?? { ..._empty }
  const runId = options.runId ?? parent.runId ?? randomUUID()

  const ctx: RunLedgerContextData = {
    runId,
    endUserId: options.endUserId ?? parent.endUserId,
    sessionId: options.sessionId ?? parent.sessionId,
    featureTag: options.featureTag ?? parent.featureTag,
    deploymentVersion: options.deploymentVersion ?? parent.deploymentVersion,
  }

  return new Promise<T>((resolve, reject) => {
    _storage.run(ctx, () => {
      try {
        const result = fn(runId)
        Promise.resolve(result).then(resolve, reject)
      } catch (err) {
        reject(err)
      }
    })
  })
}

// ── Propagation headers ───────────────────────────────────────────────────────

const HEADER_RUN_ID = 'x-runledger-run-id'
const HEADER_END_USER_ID = 'x-runledger-end-user-id'
const HEADER_SESSION_ID = 'x-runledger-session-id'
const HEADER_FEATURE_TAG = 'x-runledger-feature-tag'
const HEADER_DEPLOYMENT_VERSION = 'x-runledger-deployment-version'

/** Build HTTP headers from the current context for cross-service propagation. */
export function getPropagationHeaders(): Record<string, string> {
  const ctx = getContextSnapshot()
  const headers: Record<string, string> = {}
  if (ctx.runId) headers[HEADER_RUN_ID] = ctx.runId
  if (ctx.endUserId) headers[HEADER_END_USER_ID] = ctx.endUserId
  if (ctx.sessionId) headers[HEADER_SESSION_ID] = ctx.sessionId
  if (ctx.featureTag) headers[HEADER_FEATURE_TAG] = ctx.featureTag
  if (ctx.deploymentVersion) headers[HEADER_DEPLOYMENT_VERSION] = ctx.deploymentVersion
  return headers
}

/** Restore context from incoming HTTP headers (on the receiving service). */
export function contextFromHeaders(headers: Record<string, string>): ContextOptions {
  const lc: Record<string, string> = {}
  for (const [k, v] of Object.entries(headers)) lc[k.toLowerCase()] = v
  return {
    runId: lc[HEADER_RUN_ID],
    endUserId: lc[HEADER_END_USER_ID],
    sessionId: lc[HEADER_SESSION_ID],
    featureTag: lc[HEADER_FEATURE_TAG],
    deploymentVersion: lc[HEADER_DEPLOYMENT_VERSION],
  }
}
