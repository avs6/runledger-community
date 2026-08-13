# OTel Collector Integration

This guide shows how to configure an OpenTelemetry Collector to forward traces,
metrics, and logs to RunLedger while deriving span metrics, enforcing collector
auth, and exposing self-observability endpoints.

---

## Why Use the Collector?

You don't have to. RunLedger accepts OTLP/HTTP directly from any application.

However, the Collector is recommended for:

- **Batching** — reduce network overhead from high-frequency agents
- **Redaction** — strip PII before it leaves your network
- **Filtering** — drop noisy infra spans before they reach RunLedger
- **Fan-out** — send traces to both RunLedger and your existing observability backend
- **Attribute enrichment** — add `runledger.feature_tag`, `runledger.end_user_id`, etc.

---

## Quick Start

### 1. Install the Collector

```bash
# Docker
docker run --rm -p 4317:4317 -p 4318:4318 \
  -v $(pwd)/otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml \
  otel/opentelemetry-collector-contrib:latest
```

Or use the Docker Compose observability profile included in the RunLedger repo:

```bash
docker compose --profile observability up
```

This starts the Collector at:

- `localhost:4317` for OTLP/gRPC
- `localhost:4318` for OTLP/HTTP
- `localhost:13133` for collector health
- `localhost:8888` for collector self-metrics
- `localhost:8889` for span-derived metrics
- `localhost:55679` for zPages

`otel` remains available as a compatibility alias, but `observability` is the canonical local profile name.

### 2. Configure the Collector

Create `otel-collector-config.yaml`:

```yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  bearertokenauth:
    token: "${RUNLEDGER_API_KEY}"
  zpages:
    endpoint: 0.0.0.0:55679

receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
        auth:
          authenticator: bearertokenauth
      grpc:
        endpoint: 0.0.0.0:4317
        auth:
          authenticator: bearertokenauth

connectors:
  spanmetrics:
    histogram:
      explicit:
        buckets: [5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2s, 5s]
    dimensions:
      - name: service.name
      - name: openinference.span.kind
      - name: gen_ai.system
      - name: llm.provider
      - name: llm.model_name
      - name: gen_ai.request.model
      - name: runledger.feature_tag
      - name: runledger.deployment_version
      - name: runledger.workspace_name

processors:
  resource/runledger:
    attributes:
      - key: runledger.collector.name
        value: runledger-otel-collector
        action: upsert
      - key: runledger.workspace_name
        value: "${RUNLEDGER_OTEL_WORKSPACE_NAME}"
        action: upsert
      - key: runledger.organization_name
        value: "${RUNLEDGER_OTEL_ORGANIZATION_NAME}"
        action: upsert
  batch:
    timeout: 5s
    send_batch_size: 512
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
  filter/ai_only:
    error_mode: ignore
    traces:
      span:
        - 'attributes["openinference.span.kind"] == nil and attributes["gen_ai.system"] == nil and not IsMatch(name, "^(llm|chat|agent|tool|retriev).*")'

exporters:
  otlphttp/runledger:
    endpoint: https://api.runledger.io
    headers:
      Authorization: "Bearer ${RUNLEDGER_API_KEY}"
    encoding: json
    compression: gzip
  prometheus/spanmetrics:
    endpoint: 0.0.0.0:8889

service:
  extensions: [health_check, bearertokenauth, zpages]
  telemetry:
    metrics:
      address: 0.0.0.0:8888
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource/runledger, filter/ai_only, batch]
      exporters: [spanmetrics, otlphttp/runledger]
    metrics:
      receivers: [otlp, spanmetrics]
      processors: [memory_limiter, resource/runledger, batch]
      exporters: [otlphttp/runledger, prometheus/spanmetrics]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource/runledger, batch]
      exporters: [otlphttp/runledger]
```

### 3. Set your API key

```bash
export RUNLEDGER_API_KEY=rl_live_...
export RUNLEDGER_OTEL_WORKSPACE_NAME="Support Workspace"
export RUNLEDGER_OTEL_ORGANIZATION_NAME="Acme"
```

### 4. Point your instrumentation at the Collector

```python
# Python with OpenTelemetry SDK
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

exporter = OTLPSpanExporter(
    endpoint="http://localhost:4318/v1/traces",
    headers={"Authorization": "Bearer rl_live_..."},
)
```

```typescript
// TypeScript / Node.js
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http'

const exporter = new OTLPTraceExporter({
  url: 'http://localhost:4318/v1/traces',
  headers: { Authorization: 'Bearer rl_live_...' },
})
```

---

## Direct Ingest (No Collector)

For local development or simple deployments, send directly to RunLedger:

```python
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

exporter = OTLPSpanExporter(
    endpoint="https://api.runledger.io",
    headers={"Authorization": "Bearer rl_live_..."},
)
```

---

## Enriching Traces with RunLedger Attributes

The Collector `resource` processor can inject RunLedger helper attributes across all spans
without modifying application code:

```yaml
processors:
  resource:
    attributes:
      - key: runledger.feature_tag
        value: "support-chat"
        action: upsert
      - key: runledger.deployment_version
        value: "v2.1.0"
        action: upsert
```

Full list of RunLedger attributes: see [openinference.md#runledger-helper-attributes](./openinference.md#runledger-helper-attributes).

Recommended resource attributes for correlation:

- `service.name`
- `service.version`
- `deployment.environment`
- `runledger.session_id`
- `runledger.end_user_id`
- `runledger.feature_tag`
- `runledger.deployment_version`
- `runledger.workspace_name`
- `runledger.organization_name`

---

## Filtering Noisy Spans

Use the `filter` processor to drop spans you don't want in RunLedger:

```yaml
processors:
  filter/ai_only:
    error_mode: ignore
    traces:
      span:
        - 'attributes["openinference.span.kind"] == nil and
           attributes["gen_ai.system"] == nil and
           not IsMatch(name, "^(llm|chat|agent|tool|retriev).*")'
```

This keeps only AI-relevant spans and drops infra/HTTP spans.

---

## Redacting PII Before Export

Use the `transform` processor to redact sensitive content before it leaves your network:

```yaml
processors:
  transform/redact:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          # Remove message content entirely
          - delete_key(attributes, "llm.input_messages.0.message.content")
          - delete_key(attributes, "llm.output_messages.0.message.content")
          - delete_key(attributes, "input.value")
          - delete_key(attributes, "output.value")
```

Note: RunLedger also applies server-side privacy enforcement based on the workspace
capture policy — so even without Collector redaction, `METADATA_ONLY` mode will
not persist payload content. The Collector redaction adds a network-level guarantee.

---

## Fan-out: RunLedger + Existing Backend

Send traces to both RunLedger and your existing backend (e.g. Jaeger, Tempo):

```yaml
exporters:
  otlphttp/runledger:
    endpoint: https://api.runledger.io
    headers:
      Authorization: "Bearer ${RUNLEDGER_API_KEY}"
    compression: gzip

  otlphttp/jaeger:
    endpoint: http://jaeger:4318

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp/runledger, otlphttp/jaeger]
```

---

## Docker Compose (Local Stack)

The RunLedger repo includes a pre-configured Collector for local development:

```bash
# Start full stack including the OTel Collector
docker compose --profile observability up

# Collector endpoints:
#   gRPC:  localhost:4317
#   HTTP:  localhost:4318
# Forwards to: http://runledger-api:8000 (local RunLedger API)
```

Configuration: `infra/otel-collector-config.yaml`

---

## Verifying Ingest

After sending telemetry, check **Observe -> Monitoring -> Telemetry** in the RunLedger dashboard for:

- Batch count (last 24h / 7d)
- Trace, span, metric, and log totals
- 24h OTEL-derived trend charts
- top `service.name` values
- semantic attribution coverage
- Any ingest errors

Or query the management API:

```bash
curl -H "Authorization: Bearer $RL_KEY" \
  https://api.runledger.io/v1/traces/stats
```

```json
{
  "last_24h": {"batches": 42, "traces": 310, "spans": 2847},
  "last_7d":  {"batches": 218, "traces": 1740, "spans": 15203}
}
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `401` from RunLedger | Invalid API key | Check `RUNLEDGER_API_KEY` |
| `401` from Collector | Missing OTLP auth header | Send `Authorization: Bearer <workspace-api-key>` to `localhost:4318` / `4317` |
| `413` from RunLedger | Payload too large | Reduce `send_batch_size` or enable `compression: gzip` |
| `415` from RunLedger | Wrong content type | Use `otlphttp` exporter, not `otlp/grpc` |
| Spans appear but no runs | Trace has no root span | Ensure at least one span has no parent |
| Runs missing token counts | Wrong attribute convention | See [openinference.md](./openinference.md) for supported attrs |
| No cost in analytics | Missing token attrs or model not in pricing table | Add `llm.cost.total` or check pricing config |
