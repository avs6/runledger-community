# Part 7 - Control Plane and Platform Settings

*Prerequisite: Part 1 completed.*

This part covers the remaining control-plane pages plus the platform-level settings pages.

## 7.1 - Telemetry

Open **Observe -> Telemetry** and confirm the endpoint guidance, ingest trends,
and recent batches match the `LocalAIAgentStack / Langgraph` traffic from Lab 02.

## 7.2 - MCP

Open **Control Plane -> MCP** and connect a client with the
`LocalAIAgentStack / LiteLLM Gateway` key.

Try these tools:

- `select_tools`
- `compile_context`
- `flywheel_analyze`
- `memory_store`
- `memory_recall`

Store and recall an example fact such as:

`LocalAIAgentStack uses Qdrant for semantic cache`

Then work through [Part 7B - MCP Registry](./part7_mcp_registry.md) to validate the full MCP server lifecycle surface.

## 7.3 - Integrations

Wire a Slack webhook and send a test message.

## 7.4 - AI Hub

Work through [Part 7A - AI Hub Model Catalog](./part7_ai_hub_model_catalog.md).

## 7.5 - Data capture

Review metadata-only, sampled, errors-only, and full capture modes.

## 7.6 - Compliance

Open **Settings -> Compliance** as the platform admin.

## 7.7 - Data retention

Open **Settings -> Data Retention** and review policy plus purge flows.

## 7.8 - Email

Open **Settings -> Email** and review notification and report settings.
