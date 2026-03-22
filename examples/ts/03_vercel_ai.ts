/**
 * Example 03 — Vercel AI SDK integration pattern
 *
 * Run with: npx tsx examples/ts/03_vercel_ai.ts
 *
 * Since Vercel AI SDK (ai package) uses the OpenAI provider underneath,
 * instrumenting the OpenAI client handles tracking automatically.
 *
 * This example shows a Vercel AI SDK streaming pattern where RunLedger
 * captures token usage from the final stream chunk.
 */

import OpenAI from 'openai'
import { RunLedger } from '../../packages/ts-sdk/src/index.js'

const rl = new RunLedger({
  apiKey: process.env['RUNLEDGER_API_KEY'],
  baseUrl: process.env['RUNLEDGER_BASE_URL'] ?? 'http://localhost:8000',
})

const openai = new OpenAI()
rl.instrument(openai)

async function main() {
  console.log('Streaming response with RunLedger tracking...\n')

  await rl.withContext({ endUserId: 'u_ts_stream', featureTag: 'ts-streaming' }, async (runId) => {
    console.log(`Run ID: ${runId}`)

    const stream = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: 'List 3 benefits of FinOps for AI teams, one per line.' }],
      stream: true,
      // stream_options allows usage to be sent in the final chunk
      stream_options: { include_usage: true },
      max_tokens: 150,
    })

    process.stdout.write('Assistant: ')
    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content ?? ''
      process.stdout.write(content)
    }
    console.log('\n')
  })

  await rl.flush()
  console.log('✓ Streaming events flushed to RunLedger')
}

main().catch(console.error)
