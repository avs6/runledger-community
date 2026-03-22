import { describe, it, expect, vi } from 'vitest'
import { instrumentGemini } from '../src/gemini.js'
import { instrumentMistral } from '../src/mistral.js'
import { instrumentCohere } from '../src/cohere.js'
import { detectProvider } from '../src/openai.js'
import { withRunLedgerContext } from '../src/context.js'
import { Transport } from '../src/transport.js'
import type { RunLedgerEvent, ProviderCallEvent, RunEndEvent } from '../src/types.js'

// ── Shared test transport ─────────────────────────────────────────────────────

function makeTransport(): { transport: Transport; events: RunLedgerEvent[] } {
  const events: RunLedgerEvent[] = []
  const transport = new Transport({ apiKey: 'test', baseUrl: 'http://localhost', local: true })
  transport.enqueue = (event: RunLedgerEvent) => { events.push(event) }
  return { transport, events }
}

// ── detectProvider ────────────────────────────────────────────────────────────

describe('detectProvider', () => {
  it('detects openai from api.openai.com', () => {
    expect(detectProvider({ chat: { completions: { create: vi.fn() } }, baseURL: 'https://api.openai.com/v1' })).toBe('openai')
  })

  it('detects xai from api.x.ai', () => {
    expect(detectProvider({ chat: { completions: { create: vi.fn() } }, baseURL: 'https://api.x.ai/v1' })).toBe('xai')
  })

  it('detects mistral from api.mistral.ai', () => {
    expect(detectProvider({ chat: { completions: { create: vi.fn() } }, baseURL: 'https://api.mistral.ai/v1' })).toBe('mistral')
  })

  it('detects groq from api.groq.com', () => {
    expect(detectProvider({ chat: { completions: { create: vi.fn() } }, baseURL: 'https://api.groq.com/openai/v1' })).toBe('groq')
  })

  it('detects ollama from 11434 port', () => {
    expect(detectProvider({ chat: { completions: { create: vi.fn() } }, baseURL: 'http://localhost:11434/v1' })).toBe('ollama')
  })

  it('returns openai when baseURL is empty', () => {
    expect(detectProvider({ chat: { completions: { create: vi.fn() } } })).toBe('openai')
  })

  it('detects azure-openai from azure.com', () => {
    expect(detectProvider({ chat: { completions: { create: vi.fn() } }, baseURL: 'https://myendpoint.openai.azure.com/openai/deployments/gpt-4' })).toBe('azure-openai')
  })
})

// ── instrumentGemini ──────────────────────────────────────────────────────────

describe('instrumentGemini', () => {
  function makeFakeGenAI(text = 'Hello from Gemini', promptTokens = 20, candidateTokens = 10) {
    const fakeModel = {
      model: 'gemini-2.0-flash',
      generateContent: vi.fn().mockResolvedValue({
        response: {
          text: () => text,
          usageMetadata: {
            promptTokenCount: promptTokens,
            candidatesTokenCount: candidateTokens,
          },
          candidates: [],
        },
      }),
    }

    return {
      getGenerativeModel: vi.fn().mockReturnValue(fakeModel),
      _rl_instrumented: false,
    }
  }

  it('emits 5 events in correct order', async () => {
    const { transport, events } = makeTransport()
    const genAI = makeFakeGenAI()
    instrumentGemini(genAI, transport)

    const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' })
    await model.generateContent('Hello')

    const types = events.map(e => e.event_type)
    expect(types).toEqual(['run_start', 'span_start', 'span_end', 'provider_call', 'run_end'])
  })

  it('provider_call has provider=google and correct tokens', async () => {
    const { transport, events } = makeTransport()
    const genAI = makeFakeGenAI('Hi', 30, 15)
    instrumentGemini(genAI, transport)

    const model = genAI.getGenerativeModel({ model: 'gemini-1.5-pro' })
    await model.generateContent('Hi')

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.provider).toBe('google')
    expect(pc.input_tokens).toBe(30)
    expect(pc.output_tokens).toBe(15)
    expect(pc.status).toBe('success')
  })

  it('emits failed events and re-throws on error', async () => {
    const { transport, events } = makeTransport()
    const fakeModel = {
      model: 'gemini-2.0-flash',
      generateContent: vi.fn().mockRejectedValue(new Error('QuotaExceeded')),
    }
    const genAI = {
      getGenerativeModel: vi.fn().mockReturnValue(fakeModel),
      _rl_instrumented: false,
    }
    instrumentGemini(genAI, transport)
    const model = genAI.getGenerativeModel({})
    await expect(model.generateContent('Fail')).rejects.toThrow('QuotaExceeded')

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.status).toBe('error')
    const re = events.find(e => e.event_type === 'run_end') as RunEndEvent
    expect(re.status).toBe('failed')
  })

  it('is idempotent — does not double-wrap models', async () => {
    const { transport, events } = makeTransport()
    const genAI = makeFakeGenAI()
    instrumentGemini(genAI, transport)
    instrumentGemini(genAI, transport) // no-op

    const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' })
    await model.generateContent('Test')
    expect(events).toHaveLength(5) // not 10
  })

  it('propagates context into run_start', async () => {
    const { transport, events } = makeTransport()
    const genAI = makeFakeGenAI()
    instrumentGemini(genAI, transport)

    await withRunLedgerContext({ endUserId: 'u_gemini', featureTag: 'gemini-ft' }, async () => {
      const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' })
      await model.generateContent('ctx test')
    })

    const rs = events.find(e => e.event_type === 'run_start')!
    expect((rs as { end_user_id?: string }).end_user_id).toBe('u_gemini')
    expect((rs as { feature_tag?: string }).feature_tag).toBe('gemini-ft')
  })
})

// ── instrumentMistral ─────────────────────────────────────────────────────────

describe('instrumentMistral', () => {
  function makeFakeClient(promptTokens = 25, completionTokens = 12) {
    return {
      chat: {
        complete: vi.fn().mockResolvedValue({
          usage: { promptTokens, completionTokens },
          choices: [{ message: { content: 'Bonjour!', role: 'assistant' }, finishReason: 'stop' }],
        }),
        _rl_instrumented: false,
      },
      _rl_instrumented: false,
    }
  }

  it('emits 5 events in correct order', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeClient()
    instrumentMistral(client, transport)

    await client.chat.complete({ model: 'mistral-large-latest', messages: [] })

    const types = events.map(e => e.event_type)
    expect(types).toEqual(['run_start', 'span_start', 'span_end', 'provider_call', 'run_end'])
  })

  it('provider_call has provider=mistral and correct tokens', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeClient(40, 20)
    instrumentMistral(client, transport)

    await client.chat.complete({ model: 'mistral-small-latest', messages: [] })

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.provider).toBe('mistral')
    expect(pc.model).toBe('mistral-small-latest')
    expect(pc.input_tokens).toBe(40)
    expect(pc.output_tokens).toBe(20)
  })

  it('emits failed events and re-throws', async () => {
    const client = {
      chat: {
        complete: vi.fn().mockRejectedValue(new Error('RateLimit')),
        _rl_instrumented: false,
      },
      _rl_instrumented: false,
    }
    const { transport, events } = makeTransport()
    instrumentMistral(client, transport)

    await expect(client.chat.complete({ model: 'mistral-large-latest', messages: [] })).rejects.toThrow('RateLimit')

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.status).toBe('error')
    expect(pc.error_type).toBe('Error')
  })

  it('is idempotent', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeClient()
    instrumentMistral(client, transport)
    instrumentMistral(client, transport) // no-op

    await client.chat.complete({ model: 'mistral-large-latest', messages: [] })
    expect(events).toHaveLength(5)
  })
})

// ── instrumentCohere ──────────────────────────────────────────────────────────

describe('instrumentCohere', () => {
  function makeFakeClient(inputTokens = 30, outputTokens = 15) {
    return {
      chat: vi.fn().mockResolvedValue({
        usage: { tokens: { inputTokens, outputTokens } },
        message: { content: [{ type: 'text', text: 'Command response' }] },
      }),
      _rl_instrumented: false,
    }
  }

  it('emits 5 events in correct order', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeClient()
    instrumentCohere(client, transport)

    await client.chat({ model: 'command-r-plus', messages: [] })

    const types = events.map(e => e.event_type)
    expect(types).toEqual(['run_start', 'span_start', 'span_end', 'provider_call', 'run_end'])
  })

  it('provider_call has provider=cohere and correct tokens', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeClient(50, 25)
    instrumentCohere(client, transport)

    await client.chat({ model: 'command-r', messages: [] })

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.provider).toBe('cohere')
    expect(pc.model).toBe('command-r')
    expect(pc.input_tokens).toBe(50)
    expect(pc.output_tokens).toBe(25)
  })

  it('emits error events and re-throws', async () => {
    const client = {
      chat: vi.fn().mockRejectedValue(new Error('Unavailable')),
      _rl_instrumented: false,
    }
    const { transport, events } = makeTransport()
    instrumentCohere(client, transport)

    await expect(client.chat({ model: 'command-r-plus', messages: [] })).rejects.toThrow('Unavailable')

    const pc = events.find(e => e.event_type === 'provider_call') as ProviderCallEvent
    expect(pc.status).toBe('error')
    const re = events.find(e => e.event_type === 'run_end') as RunEndEvent
    expect(re.status).toBe('failed')
  })

  it('is idempotent', async () => {
    const { transport, events } = makeTransport()
    const client = makeFakeClient()
    instrumentCohere(client, transport)
    instrumentCohere(client, transport) // no-op

    await client.chat({ model: 'command-r-plus', messages: [] })
    expect(events).toHaveLength(5)
  })
})
