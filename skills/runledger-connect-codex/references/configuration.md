# Codex Configuration Notes

RunLedger support for Codex starts with repo-level instructions and an optional lifecycle-hook template.

## Generate Instructions

```bash
python skills/shared/scripts/install_agent_instructions.py --client codex --repo /path/to/repo
```

This writes:

- `AGENTS.md`
- `.codex/runledger-hooks.template.json`

## Hook Intent

When local hook support is finalized, capture:

- SessionStart
- SubagentStart
- PreToolUse
- PermissionRequest
- PostToolUse
- Stop
- SessionEnd

Hooks should call a local trusted wrapper that reads `RUNLEDGER_API_KEY` from the environment and sends events to RunLedger.

## Validation

```bash
python skills/shared/scripts/runledger_smoke.py --client codex --task "codex setup smoke"
```
