# RunLedger Connect Cursor

Use this skill when a user wants Cursor IDE agent tasks to connect to RunLedger.

## What This Skill Does

- Adds `.cursor/rules/runledger.mdc`.
- Guides Cursor MCP configuration.
- Supports Gateway use where Cursor can target a custom OpenAI-compatible endpoint.
- Validates telemetry with the shared smoke test.

## Steps

```bash
python skills/shared/scripts/install_agent_instructions.py --client cursor --repo .
python skills/shared/scripts/runledger_smoke.py --client cursor --task "cursor connector validation"
```

## Agent Rules

Cursor agents should:

- Use RunLedger MCP budget and policy checks before expensive work.
- Record task outcome and verification status.
- Prefer RunLedger-recommended model routes where configurable.
- Log tool usage and high-risk actions.

## Success Criteria

- `.cursor/rules/runledger.mdc` exists.
- Cursor can see RunLedger MCP where configured.
- One smoke event appears in RunLedger.
