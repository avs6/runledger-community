# Platform Settings

Control-plane configuration and platform-level settings.

## Telemetry

Open **Observe → Telemetry** and confirm the endpoint guidance, ingest trends,
and recent batches match the `LocalAIAgentStack / Langgraph` traffic from the
OTLP lab.

## MCP

Open **Control Plane → MCP** and connect a client with the
`LocalAIAgentStack / LiteLLM Gateway` key.

Try these tools:

- `select_tools`
- `compile_context`
- `flywheel_analyze`
- `memory_store`
- `memory_recall`

Store and recall an example fact such as:

`LocalAIAgentStack uses Qdrant for semantic cache`

Then work through the [MCP Registry](./mcp-registry.md) guide.

## Integrations

Wire a Slack webhook and send a test message.

## AI Hub

Work through the [AI Hub Catalog](./ai-hub-catalog.md) guide.

## Data Capture

Review metadata-only, sampled, errors-only, and full capture modes.

## Compliance

Open **Settings → Compliance** as the platform admin.

## Data Retention

Open **Settings → Data Retention** and review policy plus purge flows.

## Email

Open **Settings → Email** and review notification and report settings.
