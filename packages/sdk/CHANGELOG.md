# Changelog — runledger-sdk

All notable changes to the Python SDK are documented here.
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.7.0] — 2026-03-24

### Added
- **`RunLedgerOTLPExporter`** — OTel-compatible `SpanExporter` that ships traces to
  RunLedger's `/v1/traces` endpoint. Drop-in for any OpenInference or OTel pipeline.
- **`RunLedger.instrument_otel(tracer_provider)`** — one-line attachment of the
  OTLP exporter to an existing `TracerProvider`.
- `spans_to_otlp_json()` helper for converting OTel `ReadableSpan` objects to
  OTLP JSON format without depending on the protobuf exporter package.

### Changed
- `__version__` bumped to `0.7.0`.

---

## [0.6.0] — 2026-03-22

### Added
- **`RunLedger.instrument_mcp(session)`** — captures MCP `call_tool` invocations
  as `tool_call` events; works with any `mcp.ClientSession`.
- `instrument_mcp_session()` standalone function.
- `ToolBlockedError` exception raised when a tool is blocked by the registry.

---

## [0.5.0] — 2026-03-20

### Added
- **Gemini, Mistral, Cohere wrappers** — `instrument_gemini()`, `instrument_mistral()`,
  `instrument_cohere()` monkey-patch their respective client libraries.
- Multi-provider auto-detection in transport (infers provider from `base_url`).
- `provider_request_id` captured from API responses (OpenAI `result.id`,
  Anthropic `result.id`).
- `input_tokens_details` / `output_tokens_details` (cached, reasoning, audio tokens).

---

## [0.4.0] — 2026-03-15

### Added
- **Anthropic SDK support** — `instrument_anthropic()` patches `anthropic.Anthropic`
  and `AsyncAnthropic`; streaming + async supported.
- `RunLedger.instrument_anthropic()` convenience method.
- Budget check pre-call hook for Anthropic (same as OpenAI).
- `cache_creation_input_tokens` extracted from Anthropic responses.

---

## [0.3.0] — 2026-03-10

### Added
- **LangChain `RunLedgerCallbackHandler`** — plugs into any LangChain chain or
  LangGraph graph via `callbacks=[handler]`.
- **LangGraph node wrapper** — `RunLedgerNodeWrapper` / `instrument_graph()` for
  per-node cost attribution.
- `rl.callback_handler()` convenience factory.

---

## [0.2.0] — 2026-03-01

### Added
- **`rl.score(run_id, value, scorer, dimension)`** — emit evaluation scores linked
  to runs.
- **`rl.outcome(run_id, outcome_type, value, label, workflow)`** — record binary /
  revenue / score outcomes for ROI tracking.
- **`rl.get_prompt(name, version)`** — fetch prompt from server with 60-second
  in-memory cache and `{{variable}}` substitution.
- `RunLedgerBudgetExceededError` — raised when pre-call budget check fails.

### Changed
- Transport now batches events (configurable `batch_size`, `flush_interval`).
- `RunLedger(budget_check=True)` enables pre-call enforcement.

---

## [0.1.0] — 2026-02-15

### Added
- **OpenAI wrapper** — `rl.instrument()` monkey-patches `openai.OpenAI` and
  `AsyncOpenAI`; captures tokens, latency, model, cost.
- Context propagation via `contextvars` — `run_id`, `session_id`, `end_user_id`,
  `feature_tag`, `deployment_version`.
- `RunLedger(api_key, base_url, privacy_mode)` client class.
- `run_start()`, `run_end()`, `span_start()`, `span_end()`, `provider_call()`,
  `tool_call()` low-level event methods.
- `flush()` / `shutdown()` for graceful drain.
- Async transport with retry (3 attempts, exponential backoff, jitter).
- CLI: `runledger validate`, `runledger runs`, `runledger status`.
