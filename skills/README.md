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

## Add A Skill To A Repo

Use the shared installer from the RunLedger repo root. It writes only safe instruction/config templates and never writes API keys into generated markdown.

```bash
python skills/shared/scripts/install_agent_instructions.py --client claude --repo /path/to/target-repo
python skills/shared/scripts/install_agent_instructions.py --client codex --repo /path/to/target-repo
python skills/shared/scripts/install_agent_instructions.py --client cursor --repo /path/to/target-repo
python skills/shared/scripts/install_agent_instructions.py --client devin --repo /path/to/target-repo
```

Generated files:

| Client | Generated file(s) | Purpose |
|---|---|---|
| Claude | `CLAUDE.md` | Persistent Claude Desktop / Claude Code repo instructions. |
| Codex | `AGENTS.md`, `.codex/runledger-hooks.template.json` | Codex and subagent instructions, plus disabled hook template. |
| Cursor | `.cursor/rules/runledger.mdc` | Cursor agent rules for RunLedger budget/policy/outcome behavior. |
| Devin | `RUNLEDGER_AGENT.md` | Devin wrapper/session instructions and telemetry contract. |

After generating instructions, configure MCP or Gateway where the client supports it. Client-specific setup notes live in each skill's `references/configuration.md`.

## Validate Skills

Run the structural validator first. It creates a temporary repo, invokes every skill installer, and confirms the expected files are generated.

```bash
python skills/shared/scripts/validate_skills.py
```

Run the full validation when a local RunLedger workspace API key is available:

```bash
export RUNLEDGER_BASE_URL=http://localhost:8201
export RUNLEDGER_API_KEY=rl_live_or_test_key
export RUNLEDGER_WORKSPACE=default
python skills/shared/scripts/validate_skills.py --smoke
```

On Windows PowerShell:

```powershell
$env:RUNLEDGER_BASE_URL = "http://localhost:8201"
$env:RUNLEDGER_API_KEY = "rl_live_or_test_key"
$env:RUNLEDGER_WORKSPACE = "default"
python skills\shared\scripts\validate_skills.py --smoke
```

Current local validation status:

| Check | Status |
|---|---|
| Skill package folders exist for Claude, Codex, Cursor, and Devin | Validated |
| Instruction generation for all four clients | Validated |
| Shared smoke telemetry into RunLedger for all four clients | Validated |
| No generated markdown writes API-key secrets | Validated |
| Live client UI verification of MCP visibility | Manual follow-up |

The skills are therefore usable as publishable onboarding packages for repo-level instructions and smoke telemetry. Final MCP visibility still needs to be confirmed inside each live desktop app after its config is reloaded.

## Publishing Shape

Each publishable skill should keep this structure:

```text
skills/
  runledger-connect-<client>/
    SKILL.md
    references/
      configuration.md
  shared/
    telemetry-contract.md
    scripts/
      install_agent_instructions.py
      runledger_smoke.py
      validate_skills.py
```

Before publishing or copying a skill into another skill registry:

1. Run `python skills/shared/scripts/validate_skills.py`.
2. Run `python skills/shared/scripts/validate_skills.py --smoke` against a test workspace.
3. Confirm the target client can load its generated instruction file.
4. Confirm MCP/Gateway setup manually where the client supports it.
5. Keep all API keys in environment variables, local ignored files, or the client secret store.
