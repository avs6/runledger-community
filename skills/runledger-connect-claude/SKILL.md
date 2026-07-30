# RunLedger Connect Claude

Use this skill when a user wants Claude Desktop or Claude Code to connect to RunLedger.

## What This Skill Does

- Adds RunLedger instructions to `CLAUDE.md`.
- Guides Claude MCP setup for the RunLedger MCP gateway.
- Validates RunLedger ingest with the shared smoke test.
- Keeps API keys in environment variables, never committed files.

## Required Inputs

- RunLedger base URL, usually `http://localhost:8201`.
- RunLedger MCP URL, usually `http://localhost:8206/mcp`.
- Workspace-scoped RunLedger API key.
- Target repo path.

## Steps

1. Confirm `RUNLEDGER_BASE_URL` and `RUNLEDGER_API_KEY` are set locally.
2. Run:

```bash
python skills/shared/scripts/install_agent_instructions.py --client claude --repo .
```

3. Add the RunLedger MCP server to Claude Desktop or Claude Code config using the guidance in `references/configuration.md`.
4. Run:

```bash
python skills/shared/scripts/runledger_smoke.py --client claude --task "claude connector validation"
```

5. Ask Claude to use RunLedger for budget checks, policy checks, and outcome logging on every spawned agent task.

## Success Criteria

- `CLAUDE.md` exists in the target repo.
- Claude can see RunLedger MCP tools.
- A smoke run appears in RunLedger.
- No API key is written to committed markdown.
