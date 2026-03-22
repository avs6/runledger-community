/**
 * Example 02 — Multi-turn conversation with session tracking
 *
 * Run with: npx tsx examples/ts/02_multi_turn.ts
 *
 * Demonstrates:
 *   - Session ID propagation across multiple turns
 *   - Context nesting (outer session, per-turn run context)
 *   - Propagation headers for cross-service tracing
 */

import OpenAI from 'openai'
import { RunLedger } from '../../packages/ts-sdk/src/index.js'

const rl = new RunLedger({
  apiKey: process.env['RUNLEDGER_API_KEY'],
  baseUrl: process.env['RUNLEDGER_BASE_URL'] ?? 'http://localhost:8000',
})

const openai = new OpenAI()
rl.instrument(openai)

const SESSION_ID = `sess_${Date.now()}`
const MESSAGES: Array<{ role: 'user' | 'assistant'; content: string }> = []

async function chat(userMessage: string): Promise<string> {
  MESSAGES.push({ role: 'user', content: userMessage })

  return rl.withContext(
    {
      endUserId: 'u_ts_multi',
      sessionId: SESSION_ID,
      featureTag: 'ts-multi-turn',
    },
    async (runId) => {
      console.log(`  [turn] run_id=${runId}`)

      // Demonstrate propagation headers — you'd attach these to outbound HTTP calls
      const hdrs = rl.propagationHeaders()
      console.log(`  [hdrs] x-runledger-session-id=${hdrs['x-runledger-session-id']}`)

      const resp = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          { role: 'system', content: 'You are a helpful assistant. Be concise.' },
          ...MESSAGES,
        ],
        max_tokens: 100,
      })

      const reply = resp.choices[0]?.message?.content ?? ''
      MESSAGES.push({ role: 'assistant', content: reply })
      return reply
    },
  )
}

async function main() {
  console.log(`Session: ${SESSION_ID}\n`)

  const turns = [
    'What is FinOps?',
    'How does it apply to LLM workloads?',
    'Give me one concrete cost-saving tactic.',
  ]

  for (const msg of turns) {
    console.log(`User: ${msg}`)
    const reply = await chat(msg)
    console.log(`Assistant: ${reply}\n`)
  }

  await rl.flush()
  console.log('✓ Session events flushed')
}

main().catch(console.error)
