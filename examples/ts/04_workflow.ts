/**
 * Example 04 — Attribute work to a RunLedger workflow with @runledger/sdk
 *
 * Run with: npx tsx examples/ts/04_workflow.ts
 *
 * Prerequisites:
 *   export RUNLEDGER_API_KEY=rl_test_...
 *   A workflow whose feature tag is "support-triage" (create it on /workflows), or pass
 *   the workflow's id or name instead: the server resolves it in your workspace.
 */

import { RunLedger } from '../../packages/ts-sdk/src/index.js'

const rl = new RunLedger({
  apiKey: process.env['RUNLEDGER_API_KEY'],
  baseUrl: process.env['RUNLEDGER_BASE_URL'] ?? 'http://localhost:8201',
})

async function main() {
  // Each call is one run of the workflow, attributed at ingest. A thrown error is
  // recorded as a failed run and rethrown.
  const label = await rl.withWorkflow(
    'support-triage',
    async (task) => {
      const span = task.recordSpan('classify', { spanType: 'llm' })
      task.recordModelCall({
        provider: 'openai',
        model: 'gpt-4o-mini',
        span_id: span,
        status: 'success',
        input_tokens: 420,
        output_tokens: 60,
        latency_ms: 700,
        cost_usd: 0.0009,
      })
      return 'billing'
    },
    { agentName: 'triage-bot' },
  )
  console.log(`classified as ${label}`)
  await rl.shutdown()
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
