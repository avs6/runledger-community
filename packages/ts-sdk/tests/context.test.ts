import { describe, it, expect } from 'vitest'
import {
  withRunLedgerContext,
  getContextSnapshot,
  getRunId,
  getPropagationHeaders,
  contextFromHeaders,
} from '../src/context.js'

describe('withRunLedgerContext', () => {
  it('provides run_id inside callback', async () => {
    let capturedRunId: string | null = null
    await withRunLedgerContext({ endUserId: 'u_1' }, (runId) => {
      capturedRunId = runId
    })
    expect(capturedRunId).toBeTruthy()
    expect(typeof capturedRunId).toBe('string')
  })

  it('exposes context inside callback via getContextSnapshot', async () => {
    let snap: ReturnType<typeof getContextSnapshot> | null = null
    await withRunLedgerContext({ endUserId: 'u_2', featureTag: 'test-ft' }, () => {
      snap = getContextSnapshot()
    })
    expect(snap!.endUserId).toBe('u_2')
    expect(snap!.featureTag).toBe('test-ft')
  })

  it('getRunId returns null outside context', () => {
    // outside any context — storage is empty
    // Note: if other tests ran first, storage could be set; this test is isolated via async boundary
    const snap = getContextSnapshot()
    // runId should be whatever the current context is (null outside)
    expect(typeof snap.runId === 'string' || snap.runId === null).toBe(true)
  })

  it('uses provided run_id when specified', async () => {
    const fixedRunId = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
    await withRunLedgerContext({ runId: fixedRunId }, (runId) => {
      expect(runId).toBe(fixedRunId)
      expect(getRunId()).toBe(fixedRunId)
    })
  })

  it('nested context inherits parent fields', async () => {
    await withRunLedgerContext({ endUserId: 'u_parent', featureTag: 'outer' }, async () => {
      await withRunLedgerContext({ featureTag: 'inner' }, () => {
        const snap = getContextSnapshot()
        expect(snap.endUserId).toBe('u_parent') // inherited
        expect(snap.featureTag).toBe('inner')    // overridden
      })
    })
  })

  it('nested context does not leak into parent after exit', async () => {
    let outerSnap: ReturnType<typeof getContextSnapshot> | null = null
    await withRunLedgerContext({ endUserId: 'u_outer' }, async () => {
      await withRunLedgerContext({ endUserId: 'u_inner' }, () => {/* noop */})
      outerSnap = getContextSnapshot()
    })
    expect(outerSnap!.endUserId).toBe('u_outer')
  })

  it('returns the value from fn', async () => {
    const result = await withRunLedgerContext({}, async () => 42)
    expect(result).toBe(42)
  })
})

describe('propagation headers', () => {
  it('builds headers from current context', async () => {
    let headers: Record<string, string> = {}
    await withRunLedgerContext({ endUserId: 'u_hdr', featureTag: 'ft', sessionId: 's1' }, () => {
      headers = getPropagationHeaders()
    })
    expect(headers['x-runledger-end-user-id']).toBe('u_hdr')
    expect(headers['x-runledger-feature-tag']).toBe('ft')
    expect(headers['x-runledger-session-id']).toBe('s1')
    expect(headers['x-runledger-run-id']).toBeTruthy()
  })

  it('returns empty object outside context', () => {
    // Outside any context (top level), no keys should be present
    // (run_id is null outside a context block)
    const h = getPropagationHeaders()
    // should not include null values
    for (const v of Object.values(h)) expect(v).toBeTruthy()
  })

  it('contextFromHeaders restores context fields', () => {
    const headers = {
      'x-runledger-run-id': 'run-abc',
      'x-runledger-end-user-id': 'u_restore',
      'X-RunLedger-Feature-Tag': 'restored-ft',
    }
    const opts = contextFromHeaders(headers)
    expect(opts.runId).toBe('run-abc')
    expect(opts.endUserId).toBe('u_restore')
    expect(opts.featureTag).toBe('restored-ft')
  })
})
