# Windsurf IDE Integration

## Goal

Use RunLedger with Windsurf IDE / Devin Desktop Cascade to monitor coding-agent activity, enforce governance policies, track agentic usage, and feed optimization decisions back into RunLedger.

Recommended workspace:

- RunLedger workspace: `Windsurf`
- API key: `RUNLEDGER_KEY_WINDSURF`

## Best Integration Paths

| Path | Use It For | Notes |
|---|---|---|
| Cascade hooks | Log prompts, file reads/writes, commands, MCP tool calls, responses, and transcripts | Strongest Windsurf integration path |
| MCP | Expose RunLedger budget, analytics, tool-filtering, and optimization helpers to Cascade | Supported by Cascade's MCP server configuration |
| Gateway | Inline model routing and token control if the selected model/provider path can be configured to RunLedger Gateway | Optional; depends on current Windsurf model/provider support |
| Wrapper/OTLP | Extra run/session spans for repo-level demos | Useful for consistent cross-agent reporting |

## Hook-Based Observability

Cascade hooks can run shell commands before and after agent actions. Use them to post events to RunLedger.

High-value hook events:

- `pre_user_prompt`: classify task type and optionally block policy-violating prompts.
- `pre_run_command`: enforce command policy before terminal execution.
- `post_run_command`: record command spans and exit status.
- `pre_write_code`: block protected files or require a higher budget tier.
- `post_write_code`: record code-change spans.
- `pre_mcp_tool_use`: filter expensive or sensitive MCP tool calls.
- `post_mcp_tool_use`: record tool usage and results.
- `post_cascade_response_with_transcript`: ingest a complete conversation transcript for audit and outcome extraction.

Example workspace-level `.windsurf/hooks.json`:

```json
{
  "hooks": {
    "pre_run_command": [
      {
        "powershell": "python scripts/runledger/windsurf_hook.py --event pre_run_command",
        "command": "python3 scripts/runledger/windsurf_hook.py --event pre_run_command",
        "show_output": true
      }
    ],
    "post_run_command": [
      {
        "powershell": "python scripts/runledger/windsurf_hook.py --event post_run_command",
        "command": "python3 scripts/runledger/windsurf_hook.py --event post_run_command",
        "show_output": false
      }
    ],
    "pre_mcp_tool_use": [
      {
        "powershell": "python scripts/runledger/windsurf_hook.py --event pre_mcp_tool_use",
        "command": "python3 scripts/runledger/windsurf_hook.py --event pre_mcp_tool_use",
        "show_output": true
      }
    ],
    "post_cascade_response_with_transcript": [
      {
        "powershell": "python scripts/runledger/windsurf_hook.py --event post_cascade_response_with_transcript",
        "command": "python3 scripts/runledger/windsurf_hook.py --event post_cascade_response_with_transcript",
        "show_output": false
      }
    ]
  }
}
```

The hook script should read JSON from `stdin`, add RunLedger metadata, and emit an event to the `Windsurf` workspace. For blocking hooks, exit with the vendor-supported blocking exit code when RunLedger returns `deny`.

## MCP Setup

Add RunLedger MCP as a Cascade MCP server.

Preferred target:

```text
http://localhost:8206/mcp
```

If the client needs a local stdio bridge instead of HTTP, run a tiny `runledger-mcp-bridge` process that forwards MCP messages to the RunLedger MCP endpoint and injects:

```env
RUNLEDGER_BASE_URL=http://localhost:8201
RUNLEDGER_API_KEY=rl_...
```

Expose these RunLedger MCP tools first:

- `runledger.budget_check`
- `runledger.policy_check`
- `runledger.record_outcome`
- `runledger.query_runs`
- `runledger.recommend_model_route`
- `runledger.filter_mcp_tool`

## FinOps And Observability

RunLedger should show:

- Cascade task count by repo and user.
- Commands executed, blocked, and failed.
- MCP tool calls by server/tool name.
- Code-write volume and risky-file access.
- Estimated agentic cost per task.
- Outcome per task: completed, blocked, failed tests, reverted, or follow-up required.

## Control Points

- Block dangerous terminal commands through `pre_run_command`.
- Block sensitive file access through `pre_read_code` or `pre_write_code`.
- Block or approve MCP tools through `pre_mcp_tool_use`.
- Use RunLedger budgets before allowing large refactors, dependency changes, or long-running commands.
- Use Gateway routes if Windsurf can be configured to use an OpenAI-compatible model endpoint.

## Demo Scenario

Ask Cascade to:

```text
Refactor one simulation scenario, run tests, and summarize the cost and outcome in RunLedger.
```

Expected RunLedger story:

- Hook events appear as spans.
- MCP tool filtering is visible.
- Budget checks approve or block commands.
- The final outcome is attached to the run.

## Official Docs Consulted

- Windsurf/Cascade MCP: https://docs.windsurf.com/windsurf/cascade/mcp
- Windsurf/Cascade hooks: https://docs.windsurf.com/windsurf/cascade/hooks
- Windsurf terminal docs: https://docs.codeium.com/windsurf/terminal
