# RunLedger Connect Codex

Use this skill when a user wants OpenAI Codex tasks and subagents to report telemetry to RunLedger.

## What This Skill Does

- Adds RunLedger repo instructions to `AGENTS.md`.
- Creates a `.codex/runledger-hooks.template.json` placeholder for lifecycle hook wiring.
- Provides a smoke test that records a Codex connector run.
- Establishes the default rule that spawned agents inherit RunLedger telemetry and FinOps policy.

## Required Inputs

- RunLedger base URL.
- Workspace-scoped RunLedger API key.
- Target repo path.

## Steps

1. Confirm environment variables:

```bash
export RUNLEDGER_BASE_URL=http://localhost:8201
export RUNLEDGER_API_KEY=rl_live_or_test_key
export RUNLEDGER_WORKSPACE=default
```

2. Generate repo instructions:

```bash
python skills/shared/scripts/install_agent_instructions.py --client codex --repo .
```

3. Review `.codex/runledger-hooks.template.json` before enabling any lifecycle hooks.
4. Run validation:

```bash
python skills/shared/scripts/runledger_smoke.py --client codex --task "codex connector validation"
```

## Agent Rules

Codex and every subagent should:

- Treat RunLedger as the telemetry and FinOps control plane.
- Log the task, repo, branch, model, tools, verification, and outcome.
- Use budget/policy checks before risky or expensive work.
- Prefer RunLedger Gateway when configured by the workspace.

## Success Criteria

- `AGENTS.md` exists.
- Hook template exists but is disabled until reviewed.
- Smoke telemetry appears in RunLedger.
