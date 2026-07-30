# RunLedger Publishable Skills

This folder contains publishable connector skill scaffolds for agent tools that should send usage, cost, routing, tool, and outcome telemetry to RunLedger.

The first target skills are:

- `runledger-connect-claude`
- `runledger-connect-codex`
- `runledger-connect-cursor`
- `runledger-connect-devin`

Each skill follows the same pattern:

- `SKILL.md` gives the short instructions an agent reads when the skill is invoked.
- `references/` contains setup notes and client-specific details.
- `scripts/` contains deterministic setup or validation helpers where the client supports it.
- Shared contracts and smoke-test helpers live in `skills/shared`.

Secrets must stay in environment variables or local ignored files. Do not commit API keys into generated markdown.

## Shared Environment

Set these before running validation:

```bash
export RUNLEDGER_BASE_URL=http://localhost:8201
export RUNLEDGER_API_KEY=rl_live_or_test_key
export RUNLEDGER_WORKSPACE=default
```

On Windows PowerShell:

```powershell
$env:RUNLEDGER_BASE_URL = "http://localhost:8201"
$env:RUNLEDGER_API_KEY = "rl_live_or_test_key"
$env:RUNLEDGER_WORKSPACE = "default"
```

## Smoke Test

```bash
python skills/shared/scripts/runledger_smoke.py --client codex --task "connector smoke test"
```

The smoke test sends a run start, provider call, outcome, and run end through `/ingest/v1/batch`.
