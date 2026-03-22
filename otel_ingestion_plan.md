# OTLP / OpenTelemetry / OpenInference Ingestion Plan

Date: 2026-03-21

## Objective

Add native OTLP trace ingestion to RunLedger so customers can send OpenTelemetry and OpenInference traces without being forced to adopt the RunLedger SDK first.

The goal is not to replace the RunLedger SDK. The goal is to make the SDK the best path, not the only path.

At the end of this work, RunLedger should support three adoption modes:

1. RunLedger SDK -> RunLedger canonical ingest
2. OpenTelemetry or OpenInference -> OTel Collector -> RunLedger OTLP receiver
3. OpenTelemetry or OpenInference -> RunLedger OTLP receiver directly

## Why This Matters

Today, RunLedger requires SDK adoption for first-class ingest. That creates friction with:

- enterprise buyers who already use OpenTelemetry
- platform teams that standardize on OTLP
- teams using LangChain, custom agents, or internal frameworks with existing trace emission
- customers who do not want to rewrite instrumentation before evaluating a new platform

OTLP ingestion lowers the first adoption barrier while preserving the RunLedger SDK as the richer and more finance-native option.

## Design Principles

1. OTLP is an external ingest format, not the internal storage model.
2. Normalize OTLP and OpenInference into RunLedger's existing canonical event model.
3. Preserve raw external IDs and source attributes for auditability and replay.
4. Support OpenInference first, OpenTelemetry GenAI second, generic spans third.
5. Reuse existing workspace auth, async ingest, and Celery pipeline where possible.
6. Keep privacy-first behavior intact.
7. Treat cost and request IDs as finance-critical fields.

## Current State In The Repo

Current canonical ingest lives in:

- `apps/api/runledger_api/routers/ingest.py`
- `apps/api/runledger_api/schemas/events.py`
- `apps/api/runledger_api/workers/pipeline.py`

Current canonical event types are:

- `run_start`
- `run_end`
- `span_start`
- `span_end`
- `provider_call`
- `tool_call`
- `outcome`

Current persistence model in `apps/api/runledger_api/models/events.py` includes:

- `agent_runs`
- `spans`
- `provider_calls`
- `tool_calls`
- `outcome_events`

Current gaps for OTLP-native ingest:

- no OTLP receiver route
- no external trace or span ID columns
- no raw OTLP staging
- no request ID field on `provider_calls`
- no source provenance fields for reported versus reconciled values
- no OpenTelemetry/OpenInference normalizer

## Recommended Architecture

Preferred production architecture:

```text
Application / Agent
  -> OpenTelemetry SDK or OpenInference instrumentation
  -> OTLP Exporter
  -> OpenTelemetry Collector
  -> RunLedger OTLP Receiver
  -> RunLedger Normalizer
  -> Existing Canonical Ingest Pipeline
  -> PostgreSQL / Redis / Rollups
```

RunLedger should also allow direct OTLP/HTTP ingest from applications for low-friction evaluation and local development.

## Protocol Scope

## Phase 1 protocol support

Ship OTLP/HTTP traces only.

Implement:

- `POST /v1/traces`
- content type support for OTLP protobuf over HTTP
- gzip compression support if practical
- authentication with existing Bearer API keys

Do not implement first:

- OTLP/gRPC
- metrics ingest
- logs ingest
- profiles ingest

Those can come later.

## Data Standards Priority

Normalization priority order:

1. OpenInference attributes
2. OpenTelemetry GenAI semantic conventions
3. Generic OpenTelemetry spans and resources

This order is intentional:

- OpenInference maps best to AI-native concepts like LLM, TOOL, AGENT, RETRIEVER, PROMPT, and EVALUATOR
- OpenTelemetry GenAI is important but still evolving
- generic OTel support is necessary for broad compatibility, but it is not rich enough by itself

## High-Level Ingestion Strategy

RunLedger should not write OTLP spans directly into domain tables.

Instead:

1. Receive OTLP `ExportTraceServiceRequest`
2. Authenticate workspace
3. Parse spans, resources, and scope metadata
4. Normalize spans into RunLedger canonical events
5. Feed canonical events into the existing async pipeline
6. Persist raw OTLP payloads or normalized raw spans optionally for replay/debugging

This preserves your current architecture and minimizes rewrite risk.

## New Components To Add

### API routes

Add:

- `apps/api/runledger_api/routers/otlp.py`

Mount:

- `POST /v1/traces`
- `POST /otlp/v1/traces` as optional compatibility alias

### Services

Add:

- `apps/api/runledger_api/services/otlp_parse.py`
- `apps/api/runledger_api/services/otlp_normalize.py`
- `apps/api/runledger_api/services/otlp_mapping.py`
- `apps/api/runledger_api/services/otlp_privacy.py`

Optional:

- `apps/api/runledger_api/services/otlp_replay.py`

### Workers

Optional but recommended:

- `apps/api/runledger_api/workers/otlp_finalize.py`

Purpose:

- resolve incomplete traces
- synthesize missing `run_end`
- close traces after inactivity timeout

### Tests

Add:

- `apps/api/tests/test_otlp_ingest.py`
- `apps/api/tests/test_otlp_mapping.py`
- `apps/api/tests/test_otlp_privacy.py`
- `apps/api/tests/test_otlp_finalize.py`

### Documentation

Add:

- `docs/otlp.md`
- `docs/openinference.md`
- `docs/collector.md`

## Schema Changes

## 1. Add source identity fields

These should be added to preserve external provenance.

### `agent_runs`

Add:

- `source_type TEXT NULL`
  - values: `runledger_sdk`, `otlp`, `openinference`, `imported`, `unknown`
- `external_trace_id TEXT NULL`
- `external_trace_state TEXT NULL`
- `resource_attributes JSONB NULL`

Indexes:

- `(workspace_id, external_trace_id)` unique where `external_trace_id IS NOT NULL`

### `spans`

Add:

- `external_span_id TEXT NULL`
- `external_parent_span_id TEXT NULL`
- `trace_flags TEXT NULL`
- `instrumentation_scope_name TEXT NULL`
- `instrumentation_scope_version TEXT NULL`
- `source_span_kind TEXT NULL`
- `source_attributes JSONB NULL`

Indexes:

- `(run_id, external_span_id)` unique where `external_span_id IS NOT NULL`

### `provider_calls`

Add:

- `provider_request_id TEXT NULL`
- `reported_cost_usd NUMERIC(14,8) NULL`
- `cost_source TEXT NULL`
  - values: `reported`, `pricing_engine`, `invoice_reconciled`, `manual`, `unknown`
- `model_provider TEXT NULL`
  - hosting provider if different from model system, for example Azure-hosted OpenAI
- `input_tokens_details JSONB NULL`
- `output_tokens_details JSONB NULL`

Indexes:

- `(workspace_id, provider, provider_request_id)` where `provider_request_id IS NOT NULL`

### `tool_calls`

Add:

- `external_span_id TEXT NULL`
- `tool_arguments JSONB NULL`
- `tool_result_summary JSONB NULL`

### Optional raw staging tables

Add:

#### `otlp_ingest_batches`

- `id UUID PK`
- `workspace_id UUID`
- `received_at TIMESTAMPTZ`
- `content_type TEXT`
- `encoding TEXT`
- `trace_count INT`
- `span_count INT`
- `status TEXT`
- `error TEXT NULL`
- `raw_payload BYTEA NULL` or object-storage reference

#### `otlp_spans_raw`

- `id UUID PK`
- `workspace_id UUID`
- `batch_id UUID`
- `external_trace_id TEXT`
- `external_span_id TEXT`
- `external_parent_span_id TEXT NULL`
- `span_name TEXT`
- `start_time TIMESTAMPTZ`
- `end_time TIMESTAMPTZ NULL`
- `status_code TEXT NULL`
- `resource_attributes JSONB`
- `scope_attributes JSONB`
- `span_attributes JSONB`
- `events JSONB`
- `links JSONB`
- `normalized BOOLEAN DEFAULT FALSE`

These raw tables are recommended, not mandatory for day one. They make replay, debugging, and parser evolution much safer.

## ID Strategy

RunLedger currently uses UUIDs for run and span IDs. OTLP trace IDs and span IDs are not stored in the same shape.

Recommended strategy:

- preserve the original OTLP IDs as strings
- generate deterministic internal UUIDs for compatibility

Implementation:

- internal `run_id` = `uuid5(NAMESPACE_URL, "otlp-trace:<workspace_id>:<trace_id_hex>")`
- internal `span_id` = `uuid5(NAMESPACE_URL, "otlp-span:<workspace_id>:<trace_id_hex>:<span_id_hex>")`

Benefits:

- idempotent ingest
- deterministic replays
- no current schema rewrite
- full preservation of source IDs for debugging and exports

## Authentication And Tenancy

Reuse the existing workspace authentication model from:

- `apps/api/runledger_api/core/deps.py`

OTLP receiver should use:

- `Authorization: Bearer <RunLedger API Key>`

Rules:

- workspace identity comes from API key auth
- never trust workspace identity from OTLP resource attributes
- workspace mapping from user-supplied attrs is forbidden

Allow these resource or span attributes as metadata only:

- `service.name`
- `service.version`
- deployment environment
- session or end-user IDs
- custom feature tags

But they must not override tenancy.

## Rate Limiting

Reuse the ingest rate limiting tier in:

- `apps/api/runledger_api/core/ratelimit.py`

OTLP routes should use the same ingest rate limiter initially.

Later, if needed, add a separate OTLP tier with:

- higher burst window
- larger payload-aware enforcement
- collector-friendly limits

## OTLP Receiver Route

## Route definition

Primary route:

- `POST /v1/traces`

Optional compatibility route:

- `POST /otlp/v1/traces`

Request handling steps:

1. validate auth
2. read body
3. detect protobuf versus JSON
4. decompress if gzip
5. parse OTLP payload
6. persist optional raw batch record
7. normalize spans into canonical events
8. enqueue canonical events via existing Celery worker
9. return OTLP-compatible success response

## Failure behavior

Return:

- `401` for invalid API key
- `413` for oversized payloads
- `415` for unsupported content type
- `422` for unparseable OTLP
- `202` or `200` style OTLP success depending on implementation choice

Recommendation:

- return success only after durable accept
- if using raw batch staging, success after staging write is ideal

## Normalization Model

## Trace to Run mapping

One AI trace becomes one RunLedger run.

Preferred root detection rules:

1. if OpenInference span kind `AGENT` exists at the root, use it as run root
2. else if OpenInference span kind `CHAIN` exists at the root, use it as run root
3. else use the root span of the trace
4. if trace includes many non-AI spans, keep only the AI-relevant subtree in RunLedger domain tables and preserve full raw trace in staging

## Span kind mapping

### OpenInference kinds

Map:

- `AGENT` -> `agent`
- `CHAIN` -> `chain`
- `LLM` -> `llm`
- `TOOL` -> `tool`
- `RETRIEVER` -> `retrieval`
- `PROMPT` -> `chain` initially with metadata
- `EVALUATOR` -> `chain` initially with metadata
- `GUARDRAIL` -> `chain` initially with metadata
- `EMBEDDING` -> `retrieval` initially or `chain` with metadata depending on usage

### Generic OTel fallback

If no AI-specific kind exists:

- classify span names and attrs heuristically
- if still ambiguous, map to `chain`

## Canonical event synthesis

For each accepted trace:

1. synthesize one `run_start`
2. synthesize `span_start` for each kept span
3. synthesize `span_end` for each ended span
4. synthesize `provider_call` for each LLM span
5. synthesize `tool_call` for each TOOL span
6. synthesize `run_end` when root span is ended or after finalization timeout

## Out-of-order spans

OTLP spans may arrive:

- after their children
- in separate export batches
- retried
- partially ended

To support this safely:

- dedupe by workspace + external trace ID + external span ID
- allow partial traces
- store raw span or normalized intermediate record before final projection
- run a finalizer job that closes stale traces after inactivity timeout

Recommended inactivity timeout:

- 2 to 5 minutes configurable

## OpenInference Mapping Details

OpenInference should be the first-class mapping target.

Important attributes to extract:

### Run-level context

- `session.id`
- `user.id` or equivalent if present
- tags
- metadata
- `service.name`
- `service.version`

### LLM identity and cost

- `llm.system`
- `llm.provider`
- `llm.model_name`
- `llm.token_count.prompt`
- `llm.token_count.completion`
- `llm.token_count.prompt_details.*`
- `llm.token_count.completion_details.*`
- `llm.cost.total`
- `llm.cost.prompt`
- `llm.cost.completion`

### Messages and payloads

- `llm.input_messages.*`
- `llm.output_messages.*`
- `input.value`
- `output.value`
- tool definitions and tool call attrs

### Tool fields

- `tool.name`
- `tool.id`
- `tool.parameters`
- `tool_call.function.name`
- `tool_call.function.arguments`

### Retrieval fields

- `retrieval.documents`
- `document.id`
- `document.content`
- `document.score`

## OpenTelemetry GenAI Mapping Details

Support OTel GenAI semantic conventions as a second priority.

Because these conventions are still marked development, RunLedger should:

- accept them
- map them
- store convention version if available
- not make them the only internal contract

Normalization rules:

- model identity -> `provider` and `model`
- token attrs -> `input_tokens`, `output_tokens`, cached token details
- response and prompt attrs -> span metadata subject to privacy rules
- request/response identifiers -> `provider_request_id` when available

## Generic OTel Fallback Mapping

If a trace contains no OpenInference or GenAI-specific attrs:

- still ingest spans
- preserve topology
- derive a run root
- classify known AI-looking spans by name
- avoid creating `provider_call` or `tool_call` records unless confidence is high

This ensures broad compatibility without polluting finance tables with bad heuristics.

## Request ID Capture

This is critical.

For finance-grade reconciliation, RunLedger should capture provider request IDs whenever available.

Add support in:

- Python SDK
- TypeScript SDK
- OTLP normalizer
- gateway forwarding layer

Sources of request IDs:

- provider response headers
- provider response body fields
- span attributes emitted by upstream OTel instrumentation

If the upstream trace includes provider request IDs, map them into:

- `provider_calls.provider_request_id`

If absent:

- leave null
- rely on fuzzy reconciliation later

## Cost Model

RunLedger should support both reported and server-derived costs.

Recommended fields:

- `reported_cost_usd`
- `cost_usd`
- `cost_source`

Meaning:

- `reported_cost_usd` = cost emitted by client, OpenInference, or upstream instrumentor
- `cost_usd` = RunLedger authoritative current cost used in analytics
- `cost_source` = `reported`, `pricing_engine`, `invoice_reconciled`, `manual`, `unknown`

Rules:

- if upstream reports cost, store it
- if RunLedger pricing engine can compute cost, populate authoritative `cost_usd`
- if invoice reconciliation later overrides, update authoritative `cost_usd` and `cost_source`

This makes OTLP ingest compatible with finance-grade correction later.

## Privacy And Payload Handling

Current privacy handling exists in:

- `apps/api/runledger_api/workers/pipeline.py`

This must remain true for OTLP.

Rules:

- raw prompt/response and tool payloads are never trusted as safe by default
- OTLP payload content should be treated exactly like SDK payload content
- server-side capture policy must apply after normalization

Recommended privacy model:

### `METADATA_ONLY`

- do not persist message content, prompt text, response text, tool arguments, or retrieval document content
- preserve only counts, names, IDs, durations, statuses, model identity

### `ERRORS_ONLY`

- persist payload fields only for failed spans or error cases

### `SAMPLED`

- sample payload persistence after normalization

### `FULL`

- persist content fields after scrubber processing

Collector guidance:

- recommend customers use Collector processors to redact before export if needed
- but do not depend on collectors for privacy correctness

## Recommended Collector Pattern

RunLedger should publish a recommended Collector config.

### Minimal collector flow

```yaml
receivers:
  otlp:
    protocols:
      http:
      grpc:

processors:
  batch:
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
  resource:
    attributes:
      - key: runledger.feature_tag
        value: support-chat
        action: upsert

exporters:
  otlphttp/runledger:
    endpoint: https://api.runledger.io
    headers:
      Authorization: "Bearer ${RUNLEDGER_API_KEY}"
    compression: gzip

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch, resource]
      exporters: [otlphttp/runledger]
```

### Optional processors to recommend

- `attributes` for tagging
- `filter` for dropping noisy infra spans
- `transform` for normalization/redaction
- `tailsampling` later if needed

## RunLedger-Specific Attribute Extensions

To make OTel adoption practical, define a small set of RunLedger-specific optional attrs:

- `runledger.feature_tag`
- `runledger.deployment_version`
- `runledger.end_user_id`
- `runledger.session_id`
- `runledger.application_id`
- `runledger.capture_hint`

These should:

- enrich metadata only
- never override tenancy
- be documented as optional helper attrs

## API Surface Changes

### New route

- `POST /v1/traces`

### Optional management routes

- `GET /platform/otlp/health`
- `GET /platform/otlp/stats`
- `POST /platform/otlp/replay/{batch_id}`
- `GET /platform/otlp/batches`
- `GET /platform/otlp/batches/{batch_id}`

### Settings UI additions

Add OTLP settings surfaces for:

- API endpoint display
- collector example config
- auth token usage
- privacy mode notes
- raw staging toggle if enterprise/self-host only

## SDK Changes

The SDK still matters.

### Python SDK

Enhancements:

- capture provider request IDs from OpenAI and Anthropic where possible
- capture cost details fields when available
- optionally export OTel/OpenInference-compatible spans in addition to native RunLedger events
- optionally attach RunLedger helper attrs for Collector users

### TypeScript SDK

Enhancements:

- extend event types to support request IDs and cost provenance
- add optional OTel bridge helpers
- add examples for direct OTel emission and hybrid RunLedger + OTel usage

## Suggested File Changes

### API

Modify:

- `apps/api/runledger_api/main.py` to include OTLP router
- `apps/api/runledger_api/models/events.py`
- `apps/api/runledger_api/workers/pipeline.py`

Add:

- `apps/api/runledger_api/routers/otlp.py`
- `apps/api/runledger_api/services/otlp_parse.py`
- `apps/api/runledger_api/services/otlp_normalize.py`
- `apps/api/runledger_api/services/otlp_mapping.py`
- `apps/api/runledger_api/services/otlp_privacy.py`
- new Alembic migration for OTLP/source identity fields

### Python SDK

Modify:

- `packages/sdk/runledger_sdk/openai.py`
- `packages/sdk/runledger_sdk/anthropic.py`
- `packages/sdk/runledger_sdk/transport.py`

### TypeScript SDK

Modify:

- `packages/ts-sdk/src/types.ts`
- `packages/ts-sdk/src/openai.ts`
- `packages/ts-sdk/src/transport.ts`

### Docs

Add:

- `docs/otlp.md`
- `docs/openinference.md`
- `docs/collector.md`

## Rollout Plan

## Phase 0: Schema and parser foundation

Ship:

- schema fields for external IDs and request IDs
- OTLP route skeleton
- protobuf parsing
- raw batch staging

Exit criteria:

- OTLP trace payload can be accepted, authenticated, and stored in raw form

## Phase 1: OpenInference-first normalization

Ship:

- root trace to run mapping
- `AGENT`, `CHAIN`, `LLM`, `TOOL`, `RETRIEVER` mappings
- `provider_call` synthesis for LLM spans
- `tool_call` synthesis for TOOL spans
- privacy enforcement through canonical pipeline

Exit criteria:

- a realistic OpenInference trace appears in existing RunLedger run views and analytics

## Phase 2: OTel GenAI support

Ship:

- OTel GenAI attribute mapping
- convention version handling
- generic AI span fallback rules

Exit criteria:

- upstream OTel GenAI emitters can land useful runs without custom mapping

## Phase 3: Trace finalization and reliability

Ship:

- incomplete trace finalizer
- replay support from raw batches
- idempotent dedupe guarantees
- OTLP stats and diagnostics

Exit criteria:

- retries and partial batches do not create inconsistent runs

## Phase 4: Reconciliation-grade enrichment

Ship:

- request ID capture across SDKs and gateway
- reported versus authoritative cost fields
- invoice-reconciliation compatibility in OTLP-ingested runs

Exit criteria:

- OTLP-ingested provider calls are usable in future invoice reconciliation workflows

## Testing Plan

## Unit tests

Add tests for:

- OTLP protobuf parsing
- trace ID and span ID deterministic UUID generation
- OpenInference span kind mapping
- OTel GenAI attribute mapping
- privacy filtering on normalized spans
- request ID extraction and persistence

## Integration tests

Add tests for:

- direct `POST /v1/traces` happy path
- Collector-style batched payloads
- mixed trace with AI and non-AI spans
- retries and duplicate payloads
- out-of-order spans
- incomplete traces finalized after timeout
- OTLP trace -> canonical events -> run explorer visibility

## Performance tests

Add tests for:

- large batched OTLP payloads
- high-cardinality attribute payloads
- gzip-compressed traces
- burst ingest from Collector

## Security and privacy tests

Add tests for:

- invalid API key rejection
- workspace isolation
- privacy modes applied to OTLP-ingested payloads
- staged raw payload access restrictions
- oversized payload rejection

## Acceptance Criteria

The OTLP project is successful when all of the following are true:

1. A customer can point an OTel Collector at RunLedger and see runs without adopting the RunLedger SDK.
2. OpenInference traces map cleanly into runs, spans, provider calls, and tool calls.
3. Existing privacy modes still behave correctly.
4. OTLP ingest is idempotent across retries.
5. External trace IDs and provider request IDs are preserved.
6. OTLP-ingested data can later participate in finance-grade reconciliation workflows.
7. The RunLedger SDK still produces richer data than raw OTel, so it remains the premium path.

## Risks

### Risk 1: OTLP support becomes a generic observability project

Mitigation:

- traces only
- AI-focused mapping only
- normalize into RunLedger domain model

### Risk 2: Evolving OTel GenAI conventions break compatibility

Mitigation:

- OpenInference-first mapping
- store convention version where available
- keep RunLedger canonical schema stable

### Risk 3: Out-of-order or partial traces create broken runs

Mitigation:

- raw staging
- deterministic IDs
- finalizer job
- replay tools

### Risk 4: Privacy leakage through staged OTLP payloads

Mitigation:

- enterprise-gated raw staging if needed
- encryption or object-storage references
- strict access control
- configurable retention for raw payloads

### Risk 5: OTLP users expect full feature parity with SDK users

Mitigation:

- document that OTLP gives compatibility
- document that SDK gives better finance, policy, and runtime controls

## Product Positioning Guidance

Once OTLP support exists, the sales and onboarding story becomes:

"If you already emit OpenTelemetry or OpenInference, point your collector at RunLedger and start ingesting immediately. If you want richer finance-grade controls, request IDs, runtime budget enforcement, and deeper policy integration, layer in the RunLedger SDK."

That is much easier to sell than:

"First, replace your instrumentation."

## Immediate Implementation Order

If this starts now, the recommended order is:

1. schema migration for external IDs, request IDs, and cost provenance
2. OTLP/HTTP route and protobuf parser
3. raw batch staging
4. OpenInference mapping to canonical events
5. privacy enforcement through current pipeline
6. finalizer job for incomplete traces
7. SDK enhancements for request IDs and reported cost details
8. OTel GenAI mapping
9. Collector docs and examples

## Recommended Deliverables

Minimum first release:

- `POST /v1/traces`
- Bearer auth
- OpenInference mapping
- run/span/provider/tool projection
- external ID preservation
- privacy-safe payload handling
- collector docs

Strong second release:

- OTel GenAI mapping
- raw replay
- request ID capture
- cost provenance fields
- diagnostics pages

## References

External references:

- OpenTelemetry OTLP specification
- OpenTelemetry semantic conventions for generative AI systems
- OpenInference specification
- OpenInference traces and semantic conventions

Internal code references:

- `apps/api/runledger_api/routers/ingest.py`
- `apps/api/runledger_api/schemas/events.py`
- `apps/api/runledger_api/workers/pipeline.py`
- `apps/api/runledger_api/models/events.py`
- `apps/api/runledger_api/core/deps.py`
- `packages/sdk/runledger_sdk/openai.py`
- `packages/ts-sdk/src/types.ts`

