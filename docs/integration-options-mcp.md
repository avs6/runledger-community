# RunLedger Integration Options and MCP Connectivity

RunLedger is designed to be easy to connect to AI apps, desktop agents, frameworks, workflow tools, and OpenAI-compatible gateways.

It supports two primary integration styles:

- **inline control plane**: requests or tool decisions are shaped by RunLedger before work happens
- **out-of-band intelligence layer**: telemetry and outcomes are sent into RunLedger during or after work

MCP is the most direct control-plane path for agent tools.

## What ships today

The current MCP and integration surface includes:

- canonical RunLedger MCP server at `/mcp`
- streamable HTTP MCP transport
- local stdio bridge for MCP clients that cannot connect to HTTP directly
- generated configuration snippets in the product
- publishable skills for Claude, Codex, Cursor, and Devin
- SDK task helpers and webhook-based ingest fallbacks
- signed ingestion support for customer-controlled environments

## MCP tool contract

RunLedger exposes these canonical `runledger.*` MCP tools:

- `runledger.budget_check`
- `runledger.policy_check`
- `runledger.recommend_route`
- `runledger.record_run_start`
- `runledger.record_span`
- `runledger.record_tool_call`
- `runledger.record_model_call`
- `runledger.record_outcome`
- `runledger.query_runs`
- `runledger.query_costs`
- `runledger.query_optimizations`
- `runledger.filter_mcp_tool`

Backward-compatible aliases remain available for older clients.

## MCP resource contract

RunLedger exposes read-oriented resources for agent context, including:

- `runledger://orgs/{org_id}/summary`
- `runledger://workspaces/{workspace_id}/budget`
- `runledger://workspaces/{workspace_id}/routes`
- `runledger://workspaces/{workspace_id}/provider-profiles`
- `runledger://workspaces/{workspace_id}/recent-runs`
- `runledger://workspaces/{workspace_id}/optimization-recommendations`
- `runledger://runs/{run_id}/trace`
- `runledger://policies/{workspace_id}/tool-policy`
- `runledger://docs/agent-instructions`

## MCP prompt contract

RunLedger also ships reusable prompts for consistent behavior:

- `runledger_start_agent_task`
- `runledger_choose_model_route`
- `runledger_record_task_outcome`
- `runledger_optimize_prompt`
- `runledger_debug_expensive_request`

## Connection methods

### Direct HTTP MCP

Use this for Claude Desktop, Claude Code, Cursor, Windsurf, hosted agents, and custom MCP-aware tools.

```text
Endpoint: http://localhost:8201/mcp
Authentication: RUNLEDGER_API_KEY=<workspace-api-key>
Transport: streamable HTTP
```

RunLedger may also expose a separate optimization or cognitive MCP surface in some local setups. Use the canonical API MCP endpoint on `:8201/mcp` when you need budget checks, policy checks, run logging, and cost-aware control-plane tools.

### Local stdio MCP bridge

Use this when a client only supports a launched local stdio server:

```powershell
$env:RUNLEDGER_BASE_URL="http://localhost:8201"
$env:RUNLEDGER_API_KEY="<workspace-api-key>"
python scripts/runledger/mcp_stdio_bridge.py
```

### SSE compatibility

RunLedger uses streamable HTTP at `/mcp`. Some clients still describe this loosely as SSE-style MCP. In practice, they should point at the same endpoint unless they strictly require a different transport implementation.

### Older-client fallback

If an older client cannot use the canonical HTTP MCP endpoint cleanly, the supported fallback is the local stdio bridge:

```powershell
$env:RUNLEDGER_BASE_URL="http://localhost:8201"
$env:RUNLEDGER_API_KEY="<workspace-api-key>"
python scripts\runledger\mcp_stdio_bridge.py
```

For the current product scope, this bridge is the compatibility path for stricter legacy clients. A separate product-managed legacy SSE transport is not required to use RunLedger successfully today.

## Generated config examples

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

## Desktop-agent setup path

For desktop-agent onboarding:

1. generate or install the matching skill
2. configure MCP connectivity
3. install default agent instructions (`AGENTS.md`, `CLAUDE.md`, Cursor rules, or equivalent)
4. run a smoke test
5. confirm the run appears in Runs or Request Explorer

Relevant skill surfaces:

- `skills/runledger-connect-claude`
- `skills/runledger-connect-codex`
- `skills/runledger-connect-cursor`
- `skills/runledger-connect-devin`

For host-side setup, restart expectations, smoke validation, and troubleshooting by client, use [Desktop Agent Setup And Validation](./integrations/desktop-agent-setup.md).

## Frameworks And Workflow Tools

RunLedger's supported integration primitives today are:

- SDKs
- MCP
- OTLP / OpenTelemetry
- webhook ingest
- signed ingest
- OpenAI-compatible gateway routing

That means frameworks and workflow tools do not require dedicated product-side adapters to be usable with RunLedger today. Framework-specific adapters remain optional convenience packaging, not a blocker for the current integration foundation.

## Suggested default instruction

```text
Use RunLedger for every agent task. Before expensive or risky work, call runledger.budget_check and runledger.policy_check. Start each task with runledger.record_run_start. Record model calls, tool calls, and spans as work happens. Finish with runledger.record_outcome so RunLedger can track cost, quality, routing, business impact, and savings.
```

## Smoke test

After connecting an agent:

1. call `runledger.budget_check`
2. call `runledger.record_run_start`
3. call `runledger.record_tool_call`
4. call `runledger.record_model_call`
5. call `runledger.record_outcome`
6. verify the run appears in the dashboard

Validator command:

```powershell
$env:RUNLEDGER_BASE_URL = "http://localhost:8201"
$env:RUNLEDGER_API_KEY = "<workspace-api-key>"
python scripts\runledger\validate_mcp_connection.py
```

## Non-MCP fallbacks

When a tool cannot use MCP directly, RunLedger also supports:

- SDK task wrappers
- webhook ingest
- signed ingest
- OTLP / OpenTelemetry
- gateway-based integration for tools that support a custom OpenAI-compatible `base_url`

## Current follow-up areas

Still-open integration follow-ons include:

- more compatibility help for older MCP clients
