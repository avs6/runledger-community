# Claude Desktop Integration

## Goal

Use RunLedger with Claude Desktop and Claude Code so Claude-driven work can be observed, budgeted, and governed alongside the rest of the Local AI Lab.

Recommended workspace:

- RunLedger workspace: `Claude Desktop`
- API key: `RUNLEDGER_KEY_CLAUDE_DESKTOP`

## Best Integration Paths

| Path | Use It For | Notes |
|---|---|---|
| MCP | Give Claude access to RunLedger tools for budget checks, analytics, policy, memory, and outcome logging | Best first integration |
| Claude Code MCP | Add RunLedger as an HTTP or stdio MCP server for local coding workflows | Good for CLI/IDE-like Claude usage |
| Stdio bridge | Connect Claude Desktop to RunLedger MCP when local stdio config is required | Bridge can inject the RunLedger key safely |
| Wrapper | Capture task lifecycle and command outcomes around Claude-launched repo workflows | Useful for consistent cross-agent telemetry |
| Gateway | Inline token/cost control only if the Claude workflow can route model calls through RunLedger Gateway | Do not assume Claude Desktop native model calls are proxyable |

## Claude Desktop MCP Setup

Claude Desktop commonly connects to local MCP servers through a JSON config. Use a local bridge if the client expects a stdio server:

```json
{
  "mcpServers": {
    "runledger": {
      "command": "node",
      "args": [
        "C:\\Users\\Abi\\Desktop\\github\\runledger-community\\scripts\\Integration\\runledger-mcp-bridge.js"
      ],
      "env": {
        "RUNLEDGER_BASE_URL": "http://localhost:8201",
        "RUNLEDGER_MCP_URL": "http://localhost:8206/mcp",
        "RUNLEDGER_API_KEY": "rl_..."
      }
    }
  }
}
```

If Claude Code HTTP MCP is used, add the RunLedger MCP endpoint directly:

```powershell
claude mcp add --transport http runledger http://localhost:8206/mcp
```

Then verify:

```powershell
claude mcp list
```

## RunLedger MCP Tools To Expose

- `runledger.budget_check`: check remaining daily/monthly budget.
- `runledger.policy_check`: decide whether a tool/command/task is allowed.
- `runledger.query_runs`: inspect recent runs for the current repo/workspace.
- `runledger.query_costs`: inspect cost by model, route, and agent.
- `runledger.record_outcome`: attach final outcome to a task.
- `runledger.recommend_model_route`: suggest cheaper/faster/higher-quality route.
- `runledger.filter_mcp_tool`: approve or block downstream MCP tools.

## FinOps And Observability

RunLedger should show:

- Claude-assisted tasks by repo, user, session, and task type.
- MCP tool usage and policy decisions.
- Outcomes such as docs completed, code changed, test passed, or blocked.
- Estimated cost when Claude Desktop native model usage cannot be routed through RunLedger.
- Exact token/cost only for calls that pass through RunLedger Gateway or are imported later.

## Control Points

- Ask Claude to call `runledger.budget_check` before expensive tasks.
- Use `runledger.policy_check` before commands that modify files, install packages, touch secrets, or run migrations.
- Use wrapper scripts for command execution so RunLedger sees exit status and duration.
- Use Gateway only for Claude-compatible workflows that can target an OpenAI-compatible endpoint.

## Demo Scenario

Ask Claude:

```text
Before editing, check RunLedger budget for the Claude Desktop workspace. Then summarize the safest model route for this repo task and record the final outcome.
```

Expected RunLedger story:

- MCP budget check appears.
- Policy checks appear before sensitive steps.
- Outcome is recorded even if native Claude token usage is estimated.

## Official Docs Consulted

- MCP local server guide: https://modelcontextprotocol.io/docs/2026-07-28/develop/connect-local-servers
- Claude Code MCP quickstart: https://code.claude.com/docs/en/mcp-quickstart
