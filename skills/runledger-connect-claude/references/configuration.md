# Claude Configuration Notes

Claude can connect to RunLedger in two modes.

## MCP Mode

Use the RunLedger MCP gateway when Claude supports MCP configuration.

Recommended environment:

```bash
RUNLEDGER_BASE_URL=http://localhost:8201
RUNLEDGER_API_KEY=rl_live_or_test_key
RUNLEDGER_MCP_URL=http://localhost:8206/mcp
```

The MCP server should expose tools such as budget checks, policy checks, route recommendations, run queries, cost queries, and outcome recording.

## Repo Instruction Mode

Generate `CLAUDE.md`:

```bash
python skills/shared/scripts/install_agent_instructions.py --client claude --repo /path/to/repo
```

Claude should treat `CLAUDE.md` as persistent repo policy:

- Check RunLedger before long or expensive tasks.
- Record task start and task outcome.
- Record tool calls and model calls when wrappers are available.
- Prefer RunLedger Gateway for inline control when the model client can use a custom base URL.

## Validation

```bash
python skills/shared/scripts/runledger_smoke.py --client claude --task "claude setup smoke"
```
