# RunLedger Integration Options And MCP Connectivity

RunLedger should be easy to connect to any AI app, IDE, agent framework, workflow tool, or model gateway.

The product supports two integration patterns:

- Inline control plane: agents ask RunLedger before acting, so budgets, policies, routing, and tool filters can shape behavior in real time.
- Out-of-band intelligence layer: agents and gateways send telemetry after or during work, so RunLedger can measure cost, quality, routing, outcomes, savings, and optimization opportunities.

## Phase 1A Scope

Phase 1A creates the base integration surface:

- A RunLedger MCP server mounted at `/mcp`.
- A local stdio bridge for tools that cannot connect to HTTP MCP directly.
- A product setup page at `/mcp` with generated configuration snippets.
- A documented MCP contract for tools, resources, and prompts.
- A smoke-test path that proves a connected agent can record a visible run.

## MCP Tool Contract

RunLedger exposes canonical MCP tools with `runledger.*` names:

- `runledger.budget_check`: Check whether a user, feature, or workspace is inside budget.
- `runledger.policy_check`: Evaluate budget, tool, gateway, and score gates before an action.
- `runledger.recommend_route`: Ask RunLedger whether a model alias should be used, downgraded, or blocked.
- `runledger.record_run_start`: Start a traceable agent run.
- `runledger.record_span`: Record an agent, chain, retrieval, tool, or model span.
- `runledger.record_tool_call`: Record a tool call with risk, duration, and status.
- `runledger.record_model_call`: Record provider, model, token, latency, cost, and error details.
- `runledger.record_outcome`: Record business outcome and close the run.
- `runledger.query_runs`: Query recent runs for the workspace.
- `runledger.query_costs`: Query spend, token, model, and feature-tag cost breakdowns.
- `runledger.query_optimizations`: Query cost regressions and optimization flywheel recommendations.
- `runledger.filter_mcp_tool`: Check whether a downstream tool or MCP server call is allowed.

Backward-compatible aliases such as `list_runs`, `check_budget`, and `get_analytics_summary` remain available for existing clients.

## MCP Resource Contract

RunLedger exposes read-only resources for agent context:

- `runledger://orgs/{org_id}/summary`
- `runledger://workspaces/{workspace_id}/budget`
- `runledger://workspaces/{workspace_id}/routes`
- `runledger://workspaces/{workspace_id}/provider-profiles`
- `runledger://workspaces/{workspace_id}/recent-runs`
- `runledger://workspaces/{workspace_id}/optimization-recommendations`
- `runledger://runs/{run_id}/trace`
- `runledger://policies/{workspace_id}/tool-policy`
- `runledger://docs/agent-instructions`

## MCP Prompt Contract

RunLedger exposes reusable prompts for consistent agent behavior:

- `runledger_start_agent_task`
- `runledger_choose_model_route`
- `runledger_record_task_outcome`
- `runledger_optimize_prompt`
- `runledger_debug_expensive_request`

## Connection Methods

### Direct HTTP MCP

Use this for Claude Desktop, Claude Code, Cursor, Windsurf, hosted agents, and custom MCP-aware clients.

```text
Endpoint: http://localhost:8201/mcp
Authentication: RUNLEDGER_API_KEY=<workspace-api-key>
Transport: streamable HTTP
```

RunLedger also ships a separate optimization/cognitive MCP gateway on `http://localhost:8206/mcp`.
Use `:8206` for context compiler, memory, knowledge graph, skill registry, and flywheel tools.
Use the canonical API endpoint on `:8201/mcp` when you need the Phase 1A control-plane tools
such as budget checks, policy checks, run recording, model-call recording, and cost queries.

### Local stdio MCP Bridge

Use this when a client only supports launching a local stdio MCP server.

```powershell
$env:RUNLEDGER_BASE_URL="http://localhost:8201"
$env:RUNLEDGER_API_KEY="<workspace-api-key>"
python scripts/runledger/mcp_stdio_bridge.py
```

### SSE Compatibility

RunLedger currently uses streamable HTTP at `/mcp`. Clients that describe this as SSE-style MCP should point at the same endpoint unless they require a separate event endpoint.

## Generated Config Examples

### Claude Desktop

```json
{
  "mcpServers": {
    "runledger": {
      "url": "http://localhost:8201/mcp",
      "env": {
        "RUNLEDGER_API_KEY": "<workspace-api-key>"
      }
    }
  }
}
```

### Claude Code

```powershell
$env:RUNLEDGER_API_KEY="<workspace-api-key>"
claude mcp add --transport http runledger http://localhost:8201/mcp
```

### Cursor

```json
{
  "mcpServers": {
    "runledger": {
      "url": "http://localhost:8201/mcp",
      "env": {
        "RUNLEDGER_API_KEY": "<workspace-api-key>"
      }
    }
  }
}
```

### Windsurf

```json
{
  "servers": {
    "runledger": {
      "url": "http://localhost:8201/mcp",
      "headers": {
        "Authorization": "Bearer <workspace-api-key>"
      }
    }
  }
}
```

### OpenAI Codex

```toml
[mcp_servers.runledger]
url = "http://localhost:8201/mcp"
env = { RUNLEDGER_API_KEY = "<workspace-api-key>" }
```

## Agent Default Instruction

Add this instruction to `AGENTS.md`, `CLAUDE.md`, Cursor rules, Windsurf rules, Devin instructions, or a system prompt:

```text
Use RunLedger for every agent task. Before expensive or risky work, call runledger.budget_check and runledger.policy_check. Start each task with runledger.record_run_start. Record model calls, tool calls, and spans as work happens. Finish with runledger.record_outcome so RunLedger can track cost, quality, routing, business impact, and savings.
```

## Smoke Test

After connecting an agent:

1. Ask the agent to call `runledger.budget_check`.
2. Ask the agent to call `runledger.record_run_start`.
3. Ask the agent to call `runledger.record_tool_call` for a harmless read tool.
4. Ask the agent to call `runledger.record_model_call` with sample token and cost values.
5. Ask the agent to call `runledger.record_outcome`.
6. Verify the new run appears in Runs and Request Explorer.

For command-line validation of the canonical MCP endpoint:

```powershell
$env:RUNLEDGER_BASE_URL = "http://localhost:8201"
$env:RUNLEDGER_API_KEY = "<workspace-api-key>"
python scripts\runledger\validate_mcp_connection.py
```

The validator performs the streamable-HTTP handshake, lists tools, and verifies the required Phase 1A
`runledger.*` tools are visible. If you just rebuilt the API image, restart the API container before
running this command.

## Next Enhancements

Phase 1A creates the base integration contract. Follow-up work should add:

- Scoped integration keys for MCP-only, Gateway-only, OTLP-only, SDK ingest-only, and read analytics-only access.
- One-click integration kit generation with config files, `.env`, wrapper scripts, and default agent instructions.
- MCP proxy mode so RunLedger can sit between agents and third-party MCP servers.
- Integration audit events for generated configs, key creation, MCP tool calls, policy denials, and key rotation.
- Webhook ingestion for tools that cannot use SDK, MCP, OTLP, or Gateway.
