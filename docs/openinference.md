# OpenInference Attribute Mapping

RunLedger uses [OpenInference](https://github.com/Arize-ai/openinference) as its first-class OTLP mapping target.
This document lists every OpenInference attribute that RunLedger extracts and explains where each value lands.

---

## Span Kind

RunLedger reads the `openinference.span.kind` attribute to determine span type.

| OpenInference kind | RunLedger span type |
|--------------------|---------------------|
| `AGENT`            | `agent`             |
| `CHAIN`            | `chain`             |
| `LLM`              | `llm`               |
| `TOOL`             | `tool`              |
| `RETRIEVER`        | `retrieval`         |
| `EMBEDDING`        | `retrieval`         |
| `PROMPT`           | `chain`             |
| `EVALUATOR`        | `chain`             |
| `GUARDRAIL`        | `chain`             |

If `openinference.span.kind` is absent, RunLedger falls back to OTel GenAI conventions,
then to span name heuristics.

---

## Run-level Context

These attributes are extracted from the root span or resource attributes and stored as
top-level fields on the `agent_runs` row.

| Attribute                       | Fallback(s)                                     | RunLedger field        |
|---------------------------------|-------------------------------------------------|------------------------|
| `session.id`                    | `runledger.session_id`, `openinference.session_id` | `session_id`        |
| `user.id`                       | `runledger.end_user_id`, `openinference.user_id`, `enduser.id` | `end_user_id` |
| `tag.feature` / `feature_tag`   | `runledger.feature_tag`                         | `feature_tag`          |
| `service.version` (resource)    | `runledger.deployment_version`                  | `deployment_version`   |

---

## LLM Span Fields

All extracted from `llm`-typed spans and persisted to `provider_calls`.

### Model and Provider

| Attribute                  | Notes                                 | RunLedger field  |
|----------------------------|---------------------------------------|------------------|
| `llm.model_name`           | Primary model name                    | `model`          |
| `llm.provider`             | e.g. `openai`, `anthropic`            | `provider`       |
| `llm.hosting_provider`     | e.g. `azure` for Azure-hosted OpenAI  | `model_provider` |
| `gen_ai.openai.api_type`   | `azure` sets `model_provider="azure"` | `model_provider` |

### Token Counts

| Attribute                                     | RunLedger field     |
|-----------------------------------------------|---------------------|
| `llm.token_count.prompt`                      | `input_tokens`      |
| `llm.token_count.completion`                  | `output_tokens`     |
| `llm.token_count.prompt_details.cached_tokens` | `input_tokens_details.cached_tokens` |
| `llm.token_count.prompt_details.audio_tokens`  | `input_tokens_details.audio_tokens`  |
| `llm.token_count.completion_details.reasoning_tokens` | `output_tokens_details.reasoning_tokens` |
| `llm.token_count.completion_details.audio_tokens`     | `output_tokens_details.audio_tokens`     |

### Cost

| Attribute                      | Priority | RunLedger field       |
|-------------------------------|----------|-----------------------|
| `llm.cost.total`              | 1 (preferred) | `reported_cost_usd` |
| `llm.token_count.total_cost`  | 2 (fallback)  | `reported_cost_usd` |

When `reported_cost_usd` is present, `cost_source` is set to `"reported"`.
Otherwise `cost_source` is `"pricing_engine"` and RunLedger derives cost from token counts.

### Provider Request ID

Used for invoice reconciliation — maps to `provider_calls.provider_request_id`.

| Attribute                      | Notes                                      |
|--------------------------------|--------------------------------------------|
| `llm.openai.response.id`       | OpenInference OpenAI instrumentation       |
| `anthropic.request_id`         | OpenInference Anthropic instrumentation    |
| `gen_ai.response.id`           | OTel GenAI generic                         |
| `gen_ai.openai.api.id`         | OTel GenAI Azure variant                   |
| `llm.request_id`               | Generic OpenInference fallback             |
| `x_request_id`                 | Header-forwarded request ID                |

Priority is top-to-bottom; first non-null value wins.

---

## Message Payloads

Stored in `span_end.metadata.messages` / `.response` and subject to the workspace
[privacy capture policy](./otlp.md#privacy-and-payload-capture).

### Input messages

| Attribute pattern                             | Notes                           |
|-----------------------------------------------|---------------------------------|
| `llm.input_messages.{N}.message.role`         | Message role                    |
| `llm.input_messages.{N}.message.content`      | Message text                    |
| `input.value`                                 | Generic fallback (single turn)  |

### Output messages

| Attribute                                     | Notes                           |
|-----------------------------------------------|---------------------------------|
| `llm.output_messages.0.message.content`       | First output message            |
| `output.value`                                | Generic fallback                |

---

## Tool Span Fields

Extracted from `tool`-typed spans and persisted to `tool_calls`.

| Attribute                            | RunLedger field    |
|--------------------------------------|--------------------|
| `tool.name`                          | `tool_name`        |
| `openinference.tool.name`            | `tool_name` (fallback) |
| `gen_ai.tool.name`                   | `tool_name` (fallback) |
| `tool.parameters`                    | `metadata.tool_arguments` |
| `gen_ai.tool.call.function.arguments`| `metadata.tool_arguments` (fallback) |
| `tool_call.function.arguments`       | `metadata.tool_arguments` (fallback) |

---

## Retrieval Span Fields

Extracted from `retrieval`-typed spans and stored in `span_end.metadata`.

| Attribute pattern                           | Notes                            |
|---------------------------------------------|----------------------------------|
| `retrieval.documents.{N}.document.id`       | Document identifier              |
| `retrieval.documents.{N}.document.score`    | Relevance score (float)          |
| `retrieval.documents.{N}.document.content`  | Document text (privacy-gated)    |

The `span_end.metadata` receives:
```json
{
  "document_count": 3,
  "documents": [
    {"id": "doc-1", "score": 0.92, "content": "..."},
    ...
  ]
}
```

Document content is subject to the workspace privacy capture policy.

---

## RunLedger Helper Attributes

These optional attributes can be added via an OTel Collector `resource` processor
or directly in your instrumentation to enrich runs without adopting the RunLedger SDK.

| Attribute                        | Description                               |
|----------------------------------|-------------------------------------------|
| `runledger.session_id`           | Group runs into sessions                  |
| `runledger.end_user_id`          | Associate run with an end user            |
| `runledger.feature_tag`          | Tag runs by product feature               |
| `runledger.deployment_version`   | Track model/prompt version deployments    |
| `runledger.application_id`       | Identify the application (metadata only)  |
| `runledger.capture_hint`         | Hint for payload capture: `full`, `none`  |

These attributes are **metadata only** — they never override workspace tenancy.

---

## OTel GenAI Fallback Mapping

When OpenInference attributes are absent, RunLedger reads OTel GenAI semantic conventions.

| OTel GenAI attribute           | RunLedger field      |
|-------------------------------|----------------------|
| `gen_ai.system`               | `provider`           |
| `gen_ai.request.model`        | `model`              |
| `gen_ai.response.model`       | `model` (fallback)   |
| `gen_ai.usage.input_tokens`   | `input_tokens`       |
| `gen_ai.usage.output_tokens`  | `output_tokens`      |
| `gen_ai.response.id`          | `provider_request_id`|

### OTel GenAI span events (message payloads)

OTel GenAI emits message content as span events rather than span attributes:

| Span event name              | Mapped to                  |
|------------------------------|----------------------------|
| `gen_ai.system.message`      | `messages[role=system]`    |
| `gen_ai.user.message`        | `messages[role=user]`      |
| `gen_ai.assistant.message`   | `response`                 |
| `gen_ai.tool.message`        | `messages[role=tool]`      |

Event content is read from `gen_ai.event.content` attribute on each span event.

---

## Convention Version Tracking

RunLedger stores OTel SDK metadata in `run_start.metadata.instrumentation` for observability:

| Resource attribute           | Stored as                                  |
|------------------------------|--------------------------------------------|
| `telemetry.sdk.name`         | `instrumentation.sdk_name`                 |
| `telemetry.sdk.version`      | `instrumentation.sdk_version`              |
| `telemetry.sdk.language`     | `instrumentation.sdk_language`             |
| Scope `name`                 | `instrumentation.instrumentation_scope`    |
| Scope `version`              | `instrumentation.instrumentation_scope_version` |

This allows future filtering of runs by instrumentation library.
