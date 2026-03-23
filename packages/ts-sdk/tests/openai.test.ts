import { describe, it, expect, vi } from 'vitest'
import { instrumentOpenAI } from '../src/openai.js'
import { withRunLedgerContext } from '../src/context.js'
import { Transport } from '../src/transport.js'
import type { RunLedgerEvent, ProviderCallEvent, RunEndEvent } from '../src/types.js'

// ── Fake transport that collects events ───────────────────────────────────────

function makeTransport(): { transport: Transport; events: RunLedgerEvent[] } {
  const events: RunLedgerEvent[] = []
  const transport = new Transport({ apiKey: 'test', baseUrl: 'http://localhost', local: true })
  // Override enqueue to capture (local=true already prints, but we need to collect)
  transport.enqueue = (event: RunLedgerEvent) => { events.push(event) }
  return { transport, events }
}

// ── Fake OpenAI client ────────────────────────────────────────────────────────

function makeFakeOpenAI(
  result: object = {
    choices: [{ message: { role: 'assistant', content: 'Hello!' }, finish_reason: 'stop' }],
    usage: { prompt_tokens: 20, completion_tokens: 10 },
  },
) {
  return {
    chat: {
      completions: {
        create: vi.fn().mockResolvedValue(result),
      },
    },
  }
}

function makeFakeOpenAIError(error: Error) {
  return {
    chat: {
      completions: {
        create: vi.fn().mockRejectedValue(error),
      },
    },
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('instrumentOpenAI', () => {
  it('emits 5 events in correct order for a successful call', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI()
    instrumentOpenAI(client, transport)

    await client.chat.completions.create({ model: 'gpt-4o', messages: [] })

    const types = events.map(e => e.event_type)
    expect(types).toEqual(['run_start', 'span_start', 'span_end', 'provider_call', 'run_end'])
  })

  it('provider_call has correct tokens and provider', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI()
    instrumentOpenAI(client, transport)

    await client.chat.completions.create({ model: 'gpt-4o-mini', messages: [] })

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.provider).toBe('openai')
    expect(pc.model).toBe('gpt-4o-mini')
    expect(pc.input_tokens).toBe(20)
    expect(pc.output_tokens).toBe(10)
    expect(pc.status).toBe('success')
    expect(pc.latency_ms).toBeGreaterThanOrEqual(0)
  })

  it('run_end has status succeeded on success', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI()
    instrumentOpenAI(client, transport)

    await client.chat.completions.create({ model: 'gpt-4o', messages: [] })

    const re = events.find(e => e.event_type === 'run_end') as RunEndEvent
    expect(re.status).toBe('succeeded')
    expect(re.total_input_tokens).toBe(20)
    expect(re.total_output_tokens).toBe(10)
  })

  it('emits error events and re-throws on failure', async () => {
    const { transport, events } = makeTransport()
    const err = new Error('RateLimitError')
    const client = makeFakeOpenAIError(err)
    instrumentOpenAI(client, transport)

    await expect(
      client.chat.completions.create({ model: 'gpt-4o', messages: [] }),
    ).rejects.toThrow('RateLimitError')

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.status).toBe('error')
    expect(pc.error_type).toBe('Error')

    const re = events.find(e => e.event_type === 'run_end') as RunEndEvent
    expect(re.status).toBe('failed')
  })

  it('propagates context metadata into run_start', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI()
    instrumentOpenAI(client, transport)

    await withRunLedgerContext({ endUserId: 'u_ctx', featureTag: 'test-tag' }, async () => {
      await client.chat.completions.create({ model: 'gpt-4o', messages: [] })
    })

    const rs = events.find(e => e.event_type === 'run_start')!
    expect((rs as { end_user_id?: string }).end_user_id).toBe('u_ctx')
    expect((rs as { feature_tag?: string }).feature_tag).toBe('test-tag')
  })

  it('is idempotent — calling instrument twice does not double-emit events', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI()
    instrumentOpenAI(client, transport)
    instrumentOpenAI(client, transport) // second call should be no-op

    await client.chat.completions.create({ model: 'gpt-4o', messages: [] })

    // Should still only be 5 events, not 10
    expect(events).toHaveLength(5)
  })

  it('span_start has span_type=llm', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI()
    instrumentOpenAI(client, transport)

    await client.chat.completions.create({ model: 'gpt-4o', messages: [] })

    const ss = events.find(e => e.event_type === 'span_start')!
    expect((ss as { span_type: string }).span_type).toBe('llm')
  })

  it('span_start name includes model', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI()
    instrumentOpenAI(client, transport)

    await client.chat.completions.create({ model: 'gpt-4o-mini', messages: [] })

    const ss = events.find(e => e.event_type === 'span_start')!
    expect((ss as { name: string }).name).toContain('gpt-4o-mini')
  })

  it('provider_call captures provider_request_id from result.id', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI({
      id: 'chatcmpl-abc123',
      choices: [{ message: { role: 'assistant', content: 'Hi' }, finish_reason: 'stop' }],
      usage: { prompt_tokens: 10, completion_tokens: 5 },
    })
    instrumentOpenAI(client, transport)

    await client.chat.completions.create({ model: 'gpt-4o', messages: [] })

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.provider_request_id).toBe('chatcmpl-abc123')
  })

  it('provider_call omits provider_request_id when result.id is absent', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI({
      choices: [{ message: { role: 'assistant', content: 'Hi' }, finish_reason: 'stop' }],
      usage: { prompt_tokens: 10, completion_tokens: 5 },
    })
    instrumentOpenAI(client, transport)

    await client.chat.completions.create({ model: 'gpt-4o', messages: [] })

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.provider_request_id).toBeUndefined()
  })

  it('provider_call captures input_tokens_details from prompt_tokens_details', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI({
      id: 'chatcmpl-det1',
      choices: [{ message: { role: 'assistant', content: 'Hi' }, finish_reason: 'stop' }],
      usage: {
        prompt_tokens: 200,
        completion_tokens: 80,
        prompt_tokens_details: { cached_tokens: 150 },
      },
    })
    instrumentOpenAI(client, transport)

    await client.chat.completions.create({ model: 'gpt-4o', messages: [] })

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.input_tokens_details).toEqual({ cached_tokens: 150 })
    expect(pc.cached_input_tokens).toBe(150)
  })

  it('provider_call captures output_tokens_details from completion_tokens_details', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeOpenAI({
      id: 'chatcmpl-det2',
      choices: [{ message: { role: 'assistant', content: 'Hi' }, finish_reason: 'stop' }],
      usage: {
        prompt_tokens: 100,
        completion_tokens: 500,
        completion_tokens_details: { reasoning_tokens: 420 },
      },
    })
    instrumentOpenAI(client, transport)

    await client.chat.completions.create({ model: 'o1-preview', messages: [] })

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.output_tokens_details).toEqual({ reasoning_tokens: 420 })
  })
})

describe('Transport (local mode)', () => {
  it('does not throw when enqueuing events', () => {
    const transport = new Transport({ apiKey: '', baseUrl: 'http://localhost', local: true })
    expect(() => transport.enqueue({
      event_type: 'run_start',
      run_id: 'test',
      started_at: new Date().toISOString(),
    })).not.toThrow()
  })
})
