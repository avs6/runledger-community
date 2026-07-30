# RunLedger Agent Telemetry Contract

Every agent connector should capture the same minimum shape so dashboards can group traffic consistently.

## Required Environment

- `RUNLEDGER_BASE_URL`: RunLedger API base URL, for example `http://localhost:8201`.
- `RUNLEDGER_API_KEY`: Workspace-scoped RunLedger API key.
- `RUNLEDGER_WORKSPACE`: Human-readable workspace label for local instructions.

## Recommended Metadata

- `agent_client`: `claude`, `codex`, `cursor`, `devin`, or another integration name.
- `agent_session_id`: Client session/thread/task identifier.
- `task_id`: Stable task identifier when available.
- `repo`: Repository name or path.
- `branch`: Git branch.
- `intent`: Task category such as coding, research, planning, review, summarize, support, or search.
- `model`: Model used by the agent.
- `tool`: Tool or MCP tool used.
- `route`: RunLedger Gateway route when inline control is used.
- `outcome`: completed, failed, blocked, cancelled, or needs_review.

## Event Pattern

1. Record `run_start` when the agent begins a task.
2. Record `span_start` and `span_end` for major task phases when the client supports it.
3. Record `tool_call` for shell, browser, code edit, MCP, and external service actions.
4. Record `provider_call` for model calls with provider, model, token, latency, cache, and cost fields when known.
5. Record `outcome` with business or engineering result.
6. Record `run_end` with status, final cost, and token totals when known.

## Inline Control Pattern

Use RunLedger before expensive or risky actions:

- Check budget before long-running tasks.
- Check policy before sensitive tool calls.
- Ask for route recommendations before choosing a model.
- Use Gateway where the client supports OpenAI-compatible base URLs.

## Out-Of-Band Pattern

If a tool cannot route through RunLedger Gateway, keep the model provider path unchanged and send telemetry through SDK, OTLP, MCP, hooks, or webhook wrappers.
