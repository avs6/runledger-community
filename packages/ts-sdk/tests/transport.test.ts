import { afterEach, describe, expect, it, vi } from 'vitest'
import { Transport } from '../src/transport.js'

describe('Transport (review I-25)', () => {
  afterEach(() => vi.restoreAllMocks())

  it('bounds the queue by dropping the oldest events', async () => {
    const fetchMock = vi.fn(async () => new Response('{}', { status: 202 }))
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    const t = new Transport({ apiKey: 'k', baseUrl: 'http://x', flushIntervalMs: 60_000, maxQueueSize: 3 })
    // Fill below the batch size so nothing auto-flushes.
    for (let i = 0; i < 5; i++) t.enqueue({ event_type: 'run_start', run_id: String(i) } as never)
    await t.shutdown()
    const sent = fetchMock.mock.calls.flatMap(c => JSON.parse((c[1] as RequestInit).body as string).events)
    expect(sent.map((e: { run_id: string }) => e.run_id)).toEqual(['2', '3', '4'])
  })

  it('flush drains every queued event across several batches', async () => {
    const fetchMock = vi.fn(async () => new Response('{}', { status: 202 }))
    vi.stubGlobal('fetch', fetchMock)
    const t = new Transport({ apiKey: 'k', baseUrl: 'http://x', flushIntervalMs: 60_000 })
    for (let i = 0; i < 120; i++) t.enqueue({ event_type: 'run_start', run_id: String(i) } as never)
    await t.flush()
    const sent = fetchMock.mock.calls.flatMap(c => JSON.parse((c[1] as RequestInit).body as string).events)
    expect(sent).toHaveLength(120)
    await t.shutdown()
  })

  it('does not retry client errors', async () => {
    const fetchMock = vi.fn(async () => new Response('{}', { status: 403 }))
    vi.stubGlobal('fetch', fetchMock)
    const t = new Transport({ apiKey: 'k', baseUrl: 'http://x', flushIntervalMs: 60_000 })
    t.enqueue({ event_type: 'run_start', run_id: '1' } as never)
    await t.shutdown()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
