# @runledger/sdk

TypeScript / Node.js SDK for RunLedger — billing-grade observability, budget enforcement, and analytics for AI agents.

Instruments OpenAI, Gemini, Mistral, and Cohere clients with zero changes to your existing code.

## Installation

Not yet published to npm. Install from the repo:

```bash
npm install /path/to/runledger/packages/ts-sdk
# or
pnpm add /path/to/runledger/packages/ts-sdk
```

Peer dependency (only needed for `rl.instrument(openai)`):

```bash
npm install openai
```

## Quick start

### OpenAI

```typescript
import OpenAI from 'openai'
import { RunLedger } from '@runledger/sdk'

const rl = new RunLedger({ apiKey: process.env.RUNLEDGER_API_KEY })
const openai = new OpenAI()

rl.instrument(openai)   // wraps chat.completions.create — streaming + non-streaming

const result = await rl.withContext(
  { endUserId: 'u_123', featureTag: 'support-chat', deploymentVersion: 'v1.0' },
  async (runId) => {
    console.log('Run ID:', runId)
    return await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: 'Hello!' }],
    })
  },
)

await rl.flush()  // call before process.exit()
```

### OpenAI-compatible providers

Provider is auto-detected from `client.baseURL`:

```typescript
// Groq
const groq = new OpenAI({ apiKey: process.env.GROQ_API_KEY, baseURL: 'https://api.groq.com/openai/v1' })
rl.instrument(groq)

// Azure OpenAI
const azure = new OpenAI({ apiKey: '...', baseURL: 'https://your-resource.openai.azure.com/...' })
rl.instrument(azure)

// Local Ollama
const ollama = new OpenAI({ apiKey: 'ollama', baseURL: 'http://localhost:11434/v1' })
rl.instrument(ollama)  // cost recorded as $0.00
```

### Gemini

```typescript
import { GoogleGenerativeAI } from '@google/generative-ai'

const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY!)
rl.instrumentGemini(genAI)

const model = genAI.getGenerativeModel({ model: 'gemini-1.5-flash' })
const result = await model.generateContent('Explain RunLedger in one sentence.')
```

### Mistral

```typescript
import { Mistral } from '@mistralai/mistralai'

const mistral = new Mistral({ apiKey: process.env.MISTRAL_API_KEY })
rl.instrumentMistral(mistral)

const resp = await mistral.chat.complete({
  model: 'mistral-small-latest',
  messages: [{ role: 'user', content: 'Hello!' }],
})
```

### Cohere

```typescript
import { CohereClientV2 } from 'cohere-ai'

const cohere = new CohereClientV2({ token: process.env.COHERE_API_KEY })
rl.instrumentCohere(cohere)

const resp = await cohere.chat({
  model: 'command-r-plus',
  messages: [{ role: 'user', content: 'Hello!' }],
})
```

## Context

```typescript
// withContext tags all instrumented calls with run/user/session metadata
await rl.withContext(
  {
    endUserId: 'u_123',
    sessionId: 'sess_abc',
    featureTag: 'checkout-assistant',
    deploymentVersion: 'v2.1',
  },
  async (runId) => {
    // All provider calls here are linked to runId
  },
)
```

Contexts can be nested — inner context fields override outer for that scope.

## Cross-service context propagation

```typescript
// Service A — outgoing request
const headers = rl.propagationHeaders()
// { 'x-runledger-run-id': '...', 'x-runledger-session-id': '...' }
fetch('https://service-b/', { headers: { ...headers } })

// Service B — incoming request
const ctx = RunLedger.contextFromHeaders(Object.fromEntries(req.headers))
await rl.withContext(ctx, async () => {
  // all calls tagged with the same run as Service A
})
```

## Configuration

```typescript
const rl = new RunLedger({
  apiKey: 'rl_live_...',                      // or RUNLEDGER_API_KEY env var
  baseUrl: 'https://api.runledger.io',        // or RUNLEDGER_BASE_URL env var
  local: false,                               // true = print events to stdout, no HTTP
  budgetCheck: false,                         // pre-call budget enforcement
  privacyMode: 'metadata_only',              // metadata_only | errors_only | sampled | full
})
```

## Lifecycle

```typescript
await rl.flush()      // flush buffered events (call before await-ing process exit)
await rl.shutdown()   // flush + stop background flush timer
```

## TypeScript examples

See `examples/ts/` in the repo:

| File | Demonstrates |
|------|-------------|
| `01_openai_basic.ts` | OpenAI instrumentation, `withContext`, flush |
| `02_multi_turn.ts` | Multi-turn chat with `sessionId` |
| `03_vercel_ai.ts` | Vercel AI SDK integration |

Run with:

```bash
npx tsx examples/ts/01_openai_basic.ts
```
