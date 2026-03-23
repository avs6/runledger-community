# OTel Collector Integration

This guide shows how to configure an OpenTelemetry Collector to forward traces to RunLedger.

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

Or use the Docker Compose profile included in the RunLedger repo:

```bash
docker compose --profile otel up
```

This starts the Collector at `localhost:4317` (gRPC) and `localhost:4318` (HTTP).

### 2. Configure the Collector

Create `otel-collector-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:
    timeout: 5s
    send_batch_size: 512
  memory_limiter:
    check_interval: 1s
    limit_mib: 512

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
      processors: [memory_limiter, batch]
      exporters: [otlphttp/runledger]
```

### 3. Set your API key

```bash
export RUNLEDGER_API_KEY=rl_live_...
```

### 4. Point your instrumentation at the Collector

```python
# Python with OpenTelemetry SDK
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

exporter = OTLPSpanExporter(endpoint="http://localhost:4318")
```

```typescript
// TypeScript / Node.js
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http'

const exporter = new OTLPTraceExporter({ url: 'http://localhost:4318/v1/traces' })
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
# Start full stack including OTel Collector
docker compose --profile otel up

# Collector endpoints:
#   gRPC:  localhost:4317
#   HTTP:  localhost:4318
# Forwards to: http://api:8000 (local RunLedger API)
```

Configuration: `infra/otel-collector-config.yaml`

---

## Verifying Ingest

After sending traces, check the OTLP Settings tab in the RunLedger dashboard
(`Settings → OTLP`) for:

- Batch count (last 24h / 7d)
- Trace and span totals
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
| `413` from RunLedger | Payload too large | Reduce `send_batch_size` or enable `compression: gzip` |
| `415` from RunLedger | Wrong content type | Use `otlphttp` exporter, not `otlp/grpc` |
| Spans appear but no runs | Trace has no root span | Ensure at least one span has no parent |
| Runs missing token counts | Wrong attribute convention | See [openinference.md](./openinference.md) for supported attrs |
| No cost in analytics | Missing token attrs or model not in pricing table | Add `llm.cost.total` or check pricing config |
