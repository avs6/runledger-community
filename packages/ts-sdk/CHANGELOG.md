# Changelog — @runledger/sdk (TypeScript)

All notable changes to the TypeScript SDK are documented here.
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.6.0]

### Changed
- Version aligned with the published package. No API changes since 0.4.0 — the current
  surface is `instrument()` (OpenAI), `instrumentGemini()` / `instrumentMistral()` /
  `instrumentCohere()`, `withContext()`, `propagationHeaders()`, and `flush()`.
- Confirmed current: multi-provider detection (`detectProvider`) and invoice-reconciliation
  fields (`provider_request_id`, `input_tokens_details` / `output_tokens_details`).

---

## [0.4.0] — 2026-03-24

### Added
- `provider_request_id` captured from OpenAI API responses (`result.id`).
- `TokenDetails` type with `cached_tokens`, `reasoning_tokens`, `audio_tokens`.
- `ProviderCallEvent` gains `input_tokens_details` / `output_tokens_details`.
- Streaming support in `src/openai.ts` — instruments `stream()` calls.

### Changed
- `src/transport.ts`: batch retry uses exponential backoff with jitter.

---

## [0.3.0] — 2026-03-20

### Added
- **Gemini, Mistral, Cohere instrumentors** — `instrumentGemini()`,
  `instrumentMistral()`, `instrumentCohere()` on the `RunLedger` class.
- Multi-provider auto-detection from `baseURL` (infers provider for cost routing).
- `propagationHeaders()` — returns `{ 'X-RunLedger-Run-Id': ..., ... }` for
  passing context to downstream services.
- Vercel AI SDK integration example (`examples/ts/03_vercel_ai.ts`).

---

## [0.2.0] — 2026-03-15

### Added
- `withContext(fn, ctx)` — wraps an async function with RunLedger context using
  `AsyncLocalStorage` (Node.js native, no external dep).
- `flush()` / `shutdown()` for graceful batch drain.
- Multi-turn conversation example (`examples/ts/02_multi_turn.ts`).

---

## [0.1.0] — 2026-03-01

### Added
- **`RunLedger` class** with `instrument(openaiClient)` for OpenAI tracing.
- `AsyncLocalStorage` context propagation — `run_id`, `session_id`,
  `end_user_id`, `feature_tag`, `deployment_version`.
- `src/transport.ts` — batched HTTP transport with retry.
- `src/context.ts` — context store and propagation helpers.
- Vitest test suite (9 tests).
- `examples/ts/01_openai_basic.ts`.
