# Desktop Agent Integration Overview

## Goal

Use RunLedger as the control plane, observability layer, and FinOps system for desktop and hosted coding agents while keeping each agent vendor and repo separate.

Target clients:

- Devin
- Windsurf IDE / Devin Desktop Cascade
- Cursor IDE
- Claude Desktop / Claude Code
- OpenAI Codex IDE

These tools do not all expose the same integration points. The integration should use the strongest available path per tool and normalize the result inside RunLedger.

## RunLedger Workspace Model

Start with a single RunLedger org:

- Org: `Local AI Lab`

Create these workspaces:

- `Desktop Agents` for shared early testing.
- `Devin` once Devin traffic needs separate reporting.
- `Windsurf` once Cascade hooks are active.
- `Cursor` once Cursor MCP/wrapper traffic is active.
- `Claude Desktop` once Claude MCP/tool usage is active.
- `OpenAI Codex` once Codex hooks and MCP are active.

Create one API key per workspace from **Control Plane -> API Keys**. Do not reuse the same key across all tools unless the test is intentionally measuring aggregate desktop usage.

## Common Environment Contract

Use these variables in wrappers, MCP bridges, and local tool config:

```env
RUNLEDGER_BASE_URL=http://localhost:8201
RUNLEDGER_GATEWAY_BASE_URL=http://localhost:8201/gateway
RUNLEDGER_MCP_URL=http://localhost:8206/mcp
RUNLEDGER_OTLP_HTTP=http://localhost:4318/v1/traces

RUNLEDGER_KEY_DESKTOP_AGENTS=rl_...
RUNLEDGER_KEY_DEVIN=rl_...
RUNLEDGER_KEY_WINDSURF=rl_...
RUNLEDGER_KEY_CURSOR=rl_...
RUNLEDGER_KEY_CLAUDE_DESKTOP=rl_...
RUNLEDGER_KEY_CODEX=rl_...
```

When integrating with Docker-based LocalAIAgentStack services, use `host.docker.internal` instead of `localhost` from inside containers.

## Capture Paths

Use these paths in priority order:

| Path | What It Gives RunLedger | Best Fit |
|---|---|---|
| RunLedger Gateway | Inline token/cost tracking, model routing, budget enforcement, caching, compiler/optimization, provider comparison | Any tool that can use an OpenAI-compatible base URL |
| RunLedger SDK or wrapper | Task/run lifecycle, repo metadata, command spans, status, outcome, branch/commit, business labels | Desktop agents and hosted automation |
| MCP | Agent-accessible RunLedger tools, budget checks, policy checks, analytics lookup, memory/context retrieval, optimization recommendations | Claude, Cursor, Windsurf, Codex |
| Hooks | Pre/post tool logging, policy blocks, command auditing, MCP tool filtering, transcript ingestion | Windsurf/Cascade and Codex |
| OTLP | Out-of-band spans/metrics without changing model path | Local services and custom wrappers |

## Standard Metadata

Every desktop-agent event should carry:

```json
{
  "agent_client": "cursor|windsurf|claude_desktop|claude_code|codex|devin",
  "workspace": "Desktop Agents",
  "repo": "runledger-community",
  "task_id": "vendor-or-wrapper-task-id",
  "session_id": "vendor-session-or-chat-id",
  "spawned_by": "human|agent|automation",
  "task_type": "code_change|review|debug|docs|migration|simulation",
  "branch": "feature/runledger-demo",
  "commit_sha": "optional",
  "model_alias": "optional",
  "control_path": "gateway|sdk|mcp|hook|otlp",
  "result": "success|failure|blocked|cancelled"
}
```

This keeps analytics useful even when a vendor does not expose exact token accounting.

## Control Model

RunLedger should control desktop agents at three levels:

- Budget level: workspace budgets, per-agent caps, alert rules, and kill-switch guidance.
- Route level: when an agent can use RunLedger Gateway, route requests through approved models and provider profiles.
- Tool level: MCP tool filtering and hook-based policy checks for risky commands, sensitive files, and expensive actions.

The honest boundary: if a vendor-hosted product does not let us route model calls through RunLedger Gateway or export raw usage, RunLedger cannot enforce exact per-token budgets inline. In that case, it should enforce task/session budgets before launch, capture out-of-band telemetry, record outcomes, and show estimated or imported cost.

## Documentation Files

- [Devin Integration](Devin%20Integration.md)
- [Windsurf IDE Integration](Windsurf%20IDE%20Integration.md)
- [Cursor IDE Integration](Cursor%20IDE%20Integration.md)
- [Claude Desktop Integration](Claude%20Desktop%20Integration.md)
- [OpenAI Codex IDE Integration](OpenAI%20Codex%20IDE%20Integration.md)

## Official Docs Consulted

- Model Context Protocol local server guide: https://modelcontextprotocol.io/docs/2026-07-28/develop/connect-local-servers
- Devin API overview: https://docs.devin.ai/api-reference/overview
- Windsurf/Cascade MCP: https://docs.windsurf.com/windsurf/cascade/mcp
- Windsurf/Cascade hooks: https://docs.windsurf.com/windsurf/cascade/hooks
- Cursor MCP: https://cursor.com/docs/mcp
- Cursor permissions reference: https://cursor.com/docs/reference/permissions
- Claude Code MCP quickstart: https://code.claude.com/docs/en/mcp-quickstart
- OpenAI Codex IDE extension docs: https://learn.chatgpt.com/docs/codex/ide
