# OTLP/HTTP Ingestion

RunLedger accepts traces, metrics, and logs from any OpenTelemetry-compatible
sender over OTLP/HTTP, as **protobuf** (the default of OpenTelemetry HTTP exporters)
or **JSON**, optionally gzip-compressed. No RunLedger SDK is required — any app that
already emits OTel signals can point its exporter at RunLedger directly.

## Endpoints

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/v1/traces` | Primary OTLP/HTTP receiver (protobuf or JSON) |
| `POST` | `/otlp/v1/traces` | Compatibility alias (for collectors that prefix `/otlp`) |
| `POST` | `/v1/metrics` | Primary OTLP/HTTP metrics receiver (rolled up per series per day) |
| `POST` | `/otlp/v1/metrics` | Compatibility alias for metrics |
| `POST` | `/v1/logs` | Primary OTLP/HTTP logs receiver (Claude Code usage, errors and tool events become runs) |
| `POST` | `/otlp/v1/logs` | Compatibility alias for logs |
| `GET`  | `/v1/traces/stats` | Ingestion stats (24h + 7d) |
| `GET`  | `/v1/traces/batches` | Paginated batch history (runs created / traces dropped per batch) |
| `GET`  | `/v1/traces/insights` | 7-day attribution coverage and ingest health |
| `GET`  | `/v1/metrics/series` | Metric series with totals over `days` (filter with `name`) |
| `GET`  | `/v1/metrics/usage` | GenAI tokens / cost reported by metrics vs recorded by RunLedger |
| `GET`  | `/providers/pricing/unpriced` | Model calls with no price, by provider and model |

Auth: `Authorization: Bearer <RunLedger API key>` on all routes. Use a key with the
`ingest` scope (see [API key scopes](administration/api-keys.mdx)). Spans are attributed
to the key that sent them.

## What becomes a run

- **Gating.** With `OTLP_RUN_GATING=llm` (default) a trace becomes a run only if it
  contains an LLM, embedding, agent or tool span or `gen_ai.*` attributes. Other traces
  (file-system, HTTP plumbing) are counted as **dropped** and never create noise runs.
  Set the resource attribute `runledger.capture=all` to keep every trace from a source,
  or `OTLP_RUN_GATING=all` globally. Later batches of a trace that already has a run are
  always kept.
- **Out-of-order batches.** A batch that holds only child spans never ends the run;
  only the trace's root span sets the end time and status. The run keeps the earliest
  start time seen.
- **Long runs.** Open runs are closed as `cancelled` only after
  `OTLP_INACTIVITY_TIMEOUT_MINUTES` (default 15) without span activity.
- **Cached tokens** (`gen_ai.usage.cache_read_input_tokens`,
  `llm.token_count.prompt_details.cached_tokens`) are priced at the cached-input rate.

## Metrics

Every data point sent to `/v1/metrics` is folded into one row per **series per UTC day**.
A series is the metric name, `service.name` and up to 8 low-cardinality point attributes
(ids, sessions and prompts are left out, so exporters can't explode the table).

| Metric kind | What the rollup keeps |
|---|---|
| Sum, delta temporality | `total` adds every point |
| Sum, cumulative temporality | `total` adds the increase since the previous point (a drop counts as a counter reset); the last value carries over to the next day |
| Histogram / exponential histogram / summary | `total` = sum of observed values, `observations` = their count |
| Gauge | `last`, `min`, `max` |

**GenAI usage reconciliation.** Token and cost metrics — `gen_ai.client.token.usage`
(by `gen_ai.token.type`) and Claude Code's `claude_code.token.usage` (by `type`) and
`claude_code.cost.usage` — are summed and compared with the usage RunLedger recorded
from every source (gateway, SDK, ingest, OTLP traces and logs). A low **token coverage**
means a client exports metrics but its calls are not reaching RunLedger as traces, logs
or events. Metrics never create runs or spend on their own, so nothing is double counted.

Rollups are kept for `OTLP_METRIC_RETENTION_DAYS` (default 395).

## Unpriced model calls

A call to a model with no pricing still records its tokens, but has no cost, so spend,
budgets and chargeback undercount it. Enrichment marks such calls and skips them for an
hour; `GET /providers/pricing/unpriced` lists them by provider and model. The Telemetry
page shows the count and the provider pricing page lists the models. Adding pricing for a
model prices its existing calls on the next enrichment run (every 60 seconds).

## Raw data, privacy and retention

- Raw batch payloads are stored only when the workspace capture policy is `FULL`.
- Raw spans are always scrubbed; prompt, response and tool-argument attributes are kept
  only under `FULL`.
- Raw batches and raw spans are deleted after `OTLP_RAW_RETENTION_DAYS` (default 14).
- Limits: request body `INGEST_MAX_BODY_BYTES` (10 MB), inflated gzip body
  `OTLP_MAX_DECOMPRESSED_BYTES` (50 MB).

## Adoption modes

### Mode 1 — Direct (no Collector)

Your app's OTel SDK exports directly to RunLedger:

```bash
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:8201/v1/traces
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://localhost:8201/v1/metrics
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://localhost:8201/v1/logs
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer rl_your_key"
# Tag the workflow these signals belong to
export OTEL_RESOURCE_ATTRIBUTES="runledger.feature_tag=support-triage"
```

### Mode 2 — Via OTel Collector

Your app exports to a Collector; the Collector forwards to RunLedger.
Useful when you want fan-out to multiple backends (Jaeger, Tempo, RunLedger).

```yaml
# otel-collector-config.yaml
exporters:
  otlphttp/runledger:
    endpoint: "http://localhost:8201"
    headers:
      Authorization: "Bearer ${RUNLEDGER_API_KEY}"
```

RunLedger ships a pre-configured Collector in `docker-compose.yml`; it starts with the
stack and listens on `localhost:4318` (HTTP) and `localhost:4317` (gRPC).

Point your OTel SDK at `http://localhost:4318` and send the same
`Authorization: Bearer <RunLedger API key>` header: the bundled Collector requires it
from clients and uses it upstream. Don't filter individual spans in the Collector
(it orphans child spans); RunLedger gates at the trace level.

### Mode 3 — RunLedger SDK (recommended)

The `runledger-sdk` wraps OpenAI / Anthropic / LangChain and emits structured
events with full billing metadata automatically. Use OTLP for apps that already
have OTel instrumentation and can't add the SDK.

## Claude Code usage

Claude Code reports usage as OTLP **log events**. Send them to `/v1/logs`:

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://localhost:8201/v1/logs
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer rl_your_key"
export OTEL_RESOURCE_ATTRIBUTES="runledger.feature_tag=code-review"
# Optional: also send metrics, to check every request reached RunLedger
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://localhost:8201/v1/metrics
```

| Event | Recorded as |
|---|---|
| `claude_code.api_request` | one run per prompt, an LLM span and a priced provider call (cache reads/writes counted) |
| `claude_code.api_error` | a failed LLM span and an `error` provider call (error type / HTTP status) |
| `claude_code.tool_result` | a tool call (success / error, duration) |
| `claude_code.tool_decision` (reject) | a `denied` tool call |

`runledger.*` resource attributes set the workflow tag, end user and session the same way
as for traces.

## Attribute conventions

RunLedger parses spans using the following priority order:

| Priority | Convention | Example attributes |
|----------|-----------|-------------------|
| 1 | OpenInference | `openinference.span.kind`, `llm.model_name`, `llm.token_count.*` |
| 2 | OTel GenAI | `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.*_tokens` |
| 3 | Heuristics | span name contains `chat`, `completion`, `tool`, etc. |

### Run-context attributes

Attach these to the root span (or resource) to link traces to sessions and users:

| Attribute | Aliases | Description |
|-----------|---------|-------------|
| `runledger.session_id` | `session.id`, `openinference.session_id` | User session |
| `runledger.end_user_id` | `user.id`, `openinference.user_id`, `enduser.id` | End-user ID |
| `runledger.feature_tag` | `tag.feature`, `feature_tag` | Product feature |
| `runledger.deployment_version` | `service.version` (resource) | Deployment label |

### LLM span attributes

| Attribute | Source | Description |
|-----------|--------|-------------|
| `openinference.span.kind` | OpenInference | `LLM`, `TOOL`, `CHAIN`, `AGENT`, etc. |
| `llm.model_name` | OpenInference | Model identifier |
| `llm.provider` | OpenInference | Provider name |
| `llm.token_count.prompt` | OpenInference | Input token count |
| `llm.token_count.completion` | OpenInference | Output token count |
| `gen_ai.system` | OTel GenAI | Provider (`openai`, `anthropic`, …) |
| `gen_ai.request.model` | OTel GenAI | Model identifier |
| `gen_ai.usage.input_tokens` | OTel GenAI | Input token count |
| `gen_ai.usage.output_tokens` | OTel GenAI | Output token count |

### Message payload capture

When privacy mode is `FULL` or `SAMPLED`, RunLedger extracts prompt/completion
content from LLM spans:

| Attribute | Description |
|-----------|-------------|
| `llm.input_messages.N.message.role` | Role of the Nth input message |
| `llm.input_messages.N.message.content` | Content of the Nth input message |
| `llm.output_messages.0.message.content` | First output message content |
| `input.value` | Generic fallback for input (treated as user message) |
| `output.value` | Generic fallback for output (treated as assistant message) |

Under `METADATA_ONLY` (the default), payload content is dropped — only token
counts and latency are stored.

## Response format

On success, the endpoint returns the OTLP-spec partial success response:

```json
{"partialSuccess": {}}
```

## Error handling

| Status | Meaning |
|--------|---------|
| `200` | Accepted and enqueued |
| `401` | Missing or invalid API key |
| `403` | API key lacks the `ingest` scope |
| `413` | Body over `INGEST_MAX_BODY_BYTES`, or gzip inflates past `OTLP_MAX_DECOMPRESSED_BYTES` |
| `422` | Invalid JSON / protobuf, or OTLP structure invalid |
| `429` | Rate limit exceeded |

## Runnable example

```bash
# Clone and run the demo
cd examples
pip install httpx python-dotenv
RUNLEDGER_API_KEY=rl_your_key python 22_otlp_ingest.py
```

The example sends two traces:
1. OpenInference — AGENT + CHAIN + LLM + TOOL span hierarchy
2. OTel GenAI — Anthropic `claude-3-5-sonnet` direct LLM call

Check the **Runs** page in the dashboard after ~5 seconds for the ingested results.

## Viewing ingestion history

The **Observe -> Monitoring -> Telemetry** page shows:
- 24h and 7d aggregate stats for batches, traces, spans, metrics, and logs
- OTEL-derived 24h trend charts across traces, metrics, and logs
- top instrumented services from `service.name`
- semantic attribution coverage for `session`, `end_user`, `feature_tag`, deployment, workspace, and org labels
- **Ingest health**: runs recorded vs traces dropped (7 days), keep ratio, gating mode and unpriced calls
- **Metrics**: each metric series with its total / last value over 24h, 7d or 30d, and GenAI tokens and cost reported by metrics vs recorded by RunLedger
- A table of recent ingest batches with runs created, traces dropped, status and error details
- **Dead letters**: events the pipeline could not apply, with replay and discard
- The per-workspace **signed webhook** secret (reveal / rotate)
- A batch drill-in view with payload preview and resource-map inspection
- A quick-start code snippet for your exporter configuration

## FinOps and Governance Integration

`GET /analytics/telemetry-downstream-posture` returns a workspace-level summary of the FinOps and Safety surfaces that sit downstream of telemetry ingest:

- **FinOps**: budget count, active billing periods, chargeback rule count, and budget notification count.
- **Safety**: tool policy count, approval count, audit event count, alert rule count, active alerts, and tag count.

The Telemetry page links directly to Budgets, Billing Periods, Chargeback, Ledger, Tool Policies, Approvals, Audit Log, Alert Rules, Governance Pack, and Data Capture for workspace-level downstream context.
