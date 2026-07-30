# OpenAI Codex IDE Integration

## Goal

Use RunLedger with OpenAI Codex IDE so Codex tasks, spawned subagents, shell/tool usage, repo outcomes, token usage, and FinOps signals can be observed and governed.

Recommended workspace:

- RunLedger workspace: `OpenAI Codex`
- API key: `RUNLEDGER_KEY_CODEX`

## Best Integration Paths

| Path | Use It For | Notes |
|---|---|---|
| Codex hooks | Record session/subagent lifecycle, tool use, permission requests, and outcomes | Strongest Codex-specific integration path |
| MCP | Give Codex direct RunLedger tools for budget checks, analytics, route recommendations, and policy checks | Codex settings support MCP configuration |
| Gateway | Inline model/token/cost control if the active Codex surface can be configured to use a compatible provider/base URL | Verify per surface before promising exact control |
| Wrapper/OTLP | Capture shell commands and local task spans | Useful across CLI, IDE, and spawned-agent workflows |

## Codex Hooks

Codex supports lifecycle hooks through `hooks.json` or inline hook tables in `config.toml`. Use hooks to send task events into RunLedger.

High-value hook events:

- `SessionStart`: create or resume a RunLedger run.
- `SubagentStart`: record spawned agent usage and parent task linkage.
- `PreToolUse`: budget/policy check before shell commands or sensitive tools.
- `PermissionRequest`: record requested escalations and approval decisions.
- `PostToolUse`: record command/tool spans and exit status.
- `Stop`: record the final assistant turn status.
- `SessionEnd`: close the RunLedger run with duration and outcome.

Example user-level hook location:

```text
C:\Users\Abi\.codex\hooks.json
```

Example project-level hook location:

```text
C:\Users\Abi\Desktop\github\runledger-community\.codex\hooks.json
```

Example hook shape:

```json
{
  "description": "Send Codex lifecycle events to RunLedger.",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/runledger/codex_hook.py --event SessionStart",
            "statusMessage": "Starting RunLedger task"
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/runledger/codex_hook.py --event SubagentStart",
            "statusMessage": "Linking subagent to RunLedger"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash|Shell",
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/runledger/codex_hook.py --event PreToolUse",
            "statusMessage": "Checking RunLedger policy"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/runledger/codex_hook.py --event SessionEnd",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

## MCP Setup

Configure RunLedger MCP in Codex settings or `config.toml`.

Preferred endpoint:

```text
http://localhost:8206/mcp
```

Use:

```env
RUNLEDGER_BASE_URL=http://localhost:8201
RUNLEDGER_API_KEY=rl_...
```

Recommended tools:

- `runledger.budget_check`
- `runledger.policy_check`
- `runledger.query_runs`
- `runledger.query_costs`
- `runledger.record_outcome`
- `runledger.recommend_model_route`
- `runledger.filter_mcp_tool`

## IDE Extension Notes

The OpenAI Codex IDE extension works through Codex settings shared with Codex CLI, including model, permissions, sandbox behavior, MCP servers, and personalization. The editor layer uses `chatgpt.*` settings for UI behavior.

For RunLedger:

- Put governance and MCP configuration in Codex settings/config, not editor UI settings.
- Use hooks for telemetry and enforcement.
- Use MCP tools when Codex needs to query RunLedger.
- Use Gateway only when the active Codex model/provider path supports it.

## FinOps And Observability

RunLedger should show:

- Codex sessions by repo, branch, task type, and user.
- Spawned subagents linked to parent tasks.
- Shell/tool spans, approvals, denials, and failures.
- Token and cost when routed through Gateway or imported from available usage data.
- Outcome per task: merged, committed, tests passed, blocked, reverted, or docs-only.

## Control Points

- `PreToolUse` policy check before high-risk shell commands.
- `PermissionRequest` logging for approvals.
- `SubagentStart` budget checks before spawning multi-agent work.
- Workspace budgets and alert rules for `OpenAI Codex`.
- Gateway routes for model/provider control where available.

## Demo Scenario

Run a Codex task:

```text
Review scripts/scenarios, patch one scenario, run validation, and record outcome in RunLedger.
```

Expected RunLedger story:

- Session start creates a run.
- Subagent starts are visible if any are spawned.
- Tool calls become spans.
- Final outcome includes files touched, tests run, and success/failure.

## Official Docs Consulted

- OpenAI Codex IDE extension docs: https://learn.chatgpt.com/docs/codex/ide
- OpenAI Codex CLI repository: https://github.com/openai/codex
- Codex local manual used for hooks, MCP, and IDE settings: generated from the official Codex docs cache.
