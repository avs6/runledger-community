/**
 * Example 01 — Basic OpenAI instrumentation with @runledger/sdk
 *
 * Run with: npx tsx examples/ts/01_openai_basic.ts
 *
 * Prerequisites:
 *   export RUNLEDGER_API_KEY=rl_test_...
 *   export OPENAI_API_KEY=sk-...
 */

import OpenAI from 'openai'
import { RunLedger } from '../../packages/ts-sdk/src/index.js'

const rl = new RunLedger({
  apiKey: process.env['RUNLEDGER_API_KEY'],
  baseUrl: process.env['RUNLEDGER_BASE_URL'] ?? 'http://localhost:8000',
})

const openai = new OpenAI()

// Instrument once — all subsequent calls are automatically tracked.
rl.instrument(openai)

async function main() {
  console.log('Sending request through RunLedger-instrumented OpenAI client...\n')

  const result = await rl.withContext(
    {
      endUserId: 'u_ts_demo',
      featureTag: 'ts-sdk-demo',
      deploymentVersion: 'v1.0',
    },
    async (runId) => {
      console.log(`Run ID: ${runId}`)

      const response = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          { role: 'system', content: 'You are a concise assistant.' },
          { role: 'user', content: 'Summarise what RunLedger does in one sentence.' },
        ],
        max_tokens: 80,
      })

      return response.choices[0]?.message?.content ?? ''
    },
  )

  console.log('Response:', result)

  // Flush buffered events to RunLedger
  await rl.flush()
  console.log('\n✓ Events flushed to RunLedger')
}

main().catch(console.error)
