# Cursor IDE Integration

## Goal

Use RunLedger with Cursor IDE to monitor coding-agent usage, attribute cost by repo/task/workspace, enforce budget and tool policies, and compare optimization choices across model routes.

Recommended workspace:

- RunLedger workspace: `Cursor`
- API key: `RUNLEDGER_KEY_CURSOR`

## Best Integration Paths

| Path | Use It For | Notes |
|---|---|---|
| MCP | Let Cursor call RunLedger budget, analytics, and policy tools | Cursor documents MCP support for connecting external tools |
| Permissions | Restrict terminal commands and MCP actions where Cursor permissions are available | Useful governance layer around risky actions |
| Gateway | Inline token/cost tracking if Cursor's model/provider configuration can point to RunLedger Gateway | Use when custom OpenAI-compatible provider support is available |
| Wrapper | Record task lifecycle for Cursor-launched commands, scripts, and repo workflows | Best fallback when exact token usage is not exposed |

## MCP Setup

Configure RunLedger MCP in Cursor using Cursor's MCP settings.

Preferred endpoint:

```text
http://localhost:8206/mcp
```

Use the Cursor workspace key:

```env
RUNLEDGER_BASE_URL=http://localhost:8201
RUNLEDGER_API_KEY=rl_...
```

Expose the same RunLedger MCP tools used by other IDEs:

- `runledger.budget_check`
- `runledger.policy_check`
- `runledger.query_runs`
- `runledger.query_costs`
- `runledger.record_outcome`
- `runledger.recommend_model_route`
- `runledger.filter_mcp_tool`

## Gateway Setup

If Cursor supports a custom OpenAI-compatible provider in the active environment, configure:

```env
OPENAI_BASE_URL=http://localhost:8201/gateway
OPENAI_API_KEY=rl_...
```

Use a RunLedger Gateway route alias instead of direct vendor model names:

```text
runledger/cursor-balanced
runledger/cursor-cheap
runledger/cursor-fast
runledger/cursor-premium
```

This lets RunLedger enforce budgets, route selection, provider pricing, and optimization.

## Wrapper Setup

For tasks launched from the terminal, use a wrapper command:

```powershell
scripts\runledger\desktop-agent-wrapper.ps1 `
  -Agent cursor `
  -Workspace Cursor `
  -TaskType code_change `
  -Command "npm test"
```

The wrapper should:

- Start a RunLedger run.
- Attach repo, branch, user, command, and task label.
- Run the command.
- Capture duration and exit code.
- Record outcome.

## FinOps And Observability

RunLedger should show:

- Cursor task volume by repo and user.
- Token and cost details when traffic flows through Gateway.
- Estimated cost and outcome details when Cursor uses vendor-hosted calls outside RunLedger.
- Terminal command spans for wrapped commands.
- MCP usage by tool and server.
- Budget alerts for expensive tasks or long sessions.

## Control Points

- Budget checks before starting long-running Cursor tasks.
- MCP tool filtering for sensitive or expensive tools.
- Terminal allow/deny policy where Cursor permissions are available.
- Gateway model routing where custom provider configuration is available.

## Demo Scenario

Ask Cursor to:

```text
Add a test for workspace-admin API key creation, run the test, and record the result in RunLedger.
```

Expected RunLedger story:

- MCP budget check runs first.
- Wrapped test command appears as a span.
- Outcome is recorded as pass/fail.
- If the model call is Gateway-routed, token/cost is recorded inline.

## Official Docs Consulted

- Cursor MCP docs: https://cursor.com/docs/mcp
- Cursor CLI MCP docs: https://cursor.com/docs/cli/mcp
- Cursor permissions reference: https://cursor.com/docs/reference/permissions
