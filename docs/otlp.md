# OTLP/HTTP Trace Ingestion

RunLedger accepts traces from any OpenTelemetry-compatible sender via a standard
OTLP/HTTP JSON endpoint. No RunLedger SDK is required — any app that already emits
OTel traces can point its exporter at RunLedger directly.

## Endpoints

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/v1/traces` | Primary OTLP/HTTP JSON receiver |
| `POST` | `/otlp/v1/traces` | Compatibility alias (for collectors that prefix `/otlp`) |
| `GET`  | `/v1/traces/stats` | Ingestion stats (24h + 7d) |
| `GET`  | `/v1/traces/batches` | Paginated batch history |

Auth: `Authorization: Bearer <RunLedger API key>` on all routes.

## Adoption modes

### Mode 1 — Direct (no Collector)

Your app's OTel SDK exports directly to RunLedger:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=https://YOUR_API/v1/traces
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer rl_your_key"
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

RunLedger ships a pre-configured Collector in `docker-compose.yml`:

```bash
docker compose --profile otel up otel-collector
# Listens on localhost:4318 (HTTP) and localhost:4317 (gRPC)
```

Then point your OTel SDK at `http://localhost:4318` (no auth needed — the
Collector adds the Bearer header when forwarding).

### Mode 3 — RunLedger SDK (recommended)

The `runledger-sdk` wraps OpenAI / Anthropic / LangChain and emits structured
events with full billing metadata automatically. Use OTLP for apps that already
have OTel instrumentation and can't add the SDK.

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
| `413` | Payload exceeds 10 MB limit |
| `415` | Protobuf content type (use JSON) |
| `422` | JSON parse error or OTLP structure invalid |
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

The **Control Plane -> OTLP** page shows:
- 24h and 7d aggregate stats (batches, traces, spans received)
- A table of recent ingest batches with status and error details
- A quick-start code snippet for your exporter configuration
