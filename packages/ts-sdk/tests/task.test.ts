import { describe, it, expect, vi } from 'vitest'
import { RunLedger } from '../src/client.js'
import type { RunLedgerEvent } from '../src/types.js'

function makeClient(): { client: RunLedger; events: RunLedgerEvent[] } {
  const client = RunLedger.fromEnv({
    apiKey: 'rl_test_abc',
    baseUrl: 'http://localhost',
    local: true,
    agent: 'cursor',
    workspace: 'Desktop Agents',
  })
  const events: RunLedgerEvent[] = []
  ;(client as unknown as { _transport: { enqueue: (event: RunLedgerEvent) => void } })._transport.enqueue = (
    event: RunLedgerEvent,
  ) => {
    events.push(event)
  }
  return { client, events }
}

describe('RunLedger task helpers', () => {
  it('fromEnv stores default task metadata', () => {
    const { client } = makeClient()
    const metadata = (client as unknown as { _defaultTaskMetadata: Record<string, unknown> })._defaultTaskMetadata
    expect(metadata.agent).toBe('cursor')
    expect(metadata.workspace).toBe('Desktop Agents')
  })

  it('withTask emits lifecycle events', async () => {
    const { client, events } = makeClient()

    await client.withTask(
      'Fix failing tests',
      { intent: 'code_generation', featureTag: 'ci-fix' },
      async (task) => {
        task.recordToolCall('npm test', { status: 'success' })
        task.recordModelCall({
          provider: 'openai',
          model: 'gpt-4o-mini',
          status: 'success',
          input_tokens: 10,
          output_tokens: 4,
          latency_ms: 120,
        })
      },
    )

    const types = events.map((event) => event.event_type)
    expect(types).toContain('run_start')
    expect(types).toContain('tool_call')
    expect(types).toContain('provider_call')
    expect(types).toContain('outcome')
    expect(types).toContain('run_end')
  })

  it('withWorkflow attributes the run to a workflow and agent', async () => {
    const { client, events } = makeClient()
    const out = await client.withWorkflow('support-triage', async () => 'ok', { agentName: 'triage-bot' })
    expect(out).toBe('ok')
    const start = events.find((event) => event.event_type === 'run_start') as Record<string, unknown>
    expect(start.workflow).toBe('support-triage')
    expect(start.agent_name).toBe('triage-bot')
  })

  it('withWorkflow records a failed outcome and rethrows', async () => {
    const { client, events } = makeClient()
    await expect(client.withWorkflow('wf', async () => { throw new Error('x') })).rejects.toThrow('x')
    const outcome = events.find((event) => event.event_type === 'outcome') as Record<string, unknown>
    expect(outcome.success).toBe(false)
  })
})
