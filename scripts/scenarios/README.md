# Simulation scenarios

Each scenario module (`NAME` + `run(sim)`) populates a RunLedger workspace through
the public REST API. The simulator mirrors the real product path: platform admin
creates an org, the seeded org admin creates routes/API keys/budgets, and agent
traffic lands through `/ingest/v1/batch`.

## Default demo mode

`scripts/full_simulate.py` now defaults to local-only Ollama scenarios and a 3x
traffic multiplier:

```bash
uv run python scripts/full_simulate.py
```

That creates four org/workspace pairs and roughly 1,770 synthetic local-model runs.
It imports `scripts/pricing.yaml`, which is intentionally Ollama-only, so the demo
does not need OpenAI, Anthropic, Gemini, or any other hosted-provider key.

Default simulator logins:

| Account | Password | Notes |
|---|---|---|
| `admin@runledger.local` | `runledger` | Platform admin created by `full_simulate.py`. |
| `admin@<scenario-slug>.example.com` | `Sim-Passw0rd!` | Org admin for each scenario org. Example: `admin@helpdesk-local.example.com`. |

Use these only when you intentionally want broader coverage:

```bash
uv run python scripts/full_simulate.py --traffic-multiplier 5
uv run python scripts/full_simulate.py --scenario-set all
uv run python scripts/full_simulate.py --scenario-set hosted
```

## Bundled local scenarios

| Scenario | Org / Workspace | Models | Demonstrates |
|---|---|---|---|
| `ollama/01_coding_assistant` | Acme Dev Tools / Coding Assistant | `qwen2.5-coder:14b`, `deepseek-r1:14b`, `deepseek-r1:8b` | Priced local coding/reasoning, semantic cache, compiler, tool filtering, intelligent routing, budgets, alerts |
| `ollama/02_local_rag` | DataCo / Knowledge Base | `llama3.1:8b`, `nomic-embed-text` | RAG generation vs embedding cost, relevance and faithfulness scores, helpful-answer outcomes |
| `ollama/03_reasoning_agent` | ThinkLocal / Reasoning | `deepseek-r1:14b`, `deepseek-r1:8b` | Output-heavy reasoning spend, cost vs quality comparisons, decision-supported outcomes |
| `ollama/04_chat_support` | HelpDesk Local / Support Bot | `llama3.2`, `gemma3:latest` | High-volume support traffic, local ticket outcomes, daily and monthly spend controls |

## Hosted scenarios

The `hosted/` folder is kept as optional reference material for mixed-provider demos.
Those scenarios are no longer part of the default run because the current local demo
uses only `scripts/pricing.yaml`, and that catalog is Ollama-only.

## LocalAI Agent Stack integration scenarios

The LocalAI integration is separate from the default scenario library because it is
meant to connect to another local repo and keep its generated API keys private.

Use these helpers from the repo root:

```powershell
python scripts\localai\bootstrap_runledger_org.py
python scripts\localai\inject_mcp_configs.py
python scripts\localai\localai_s3_backup.py backup
python scripts\localai\generate_agent_traffic.py --workspace "Python Console" --source python-console
python scripts\localai\generate_otlp_traffic.py --workspace "Open WebUI" --source open-webui-otel
```

That creates the `LocalAI Agent Stack` org and separate workspaces for LiteLLM,
Open WebUI, OpenHands, LangGraph, Hermes Agent, Claude Desktop, OpenAI Codex,
Python Console, and Backup Restore Lab. See [`../README.md`](../README.md) for the
full runbook, including S3 backup/restore, SDK-style traffic, OTLP trace ingestion,
and why Claude/Codex use MCP or wrappers for out-of-band telemetry unless a spawned
tool can be routed through the Gateway.

## Writing a scenario

Create a file in any folder, usually under `scripts/scenarios/ollama/`:

```python
from scenarios._base import Sim

NAME = "my-local-scenario"
DESCRIPTION = "One line describing what this simulates."

def run(sim: Sim) -> None:
    ws = sim.workspace("My Org", "My Workspace")
    ws.add_route("chat", "llama3.2", base_url="http://host.docker.internal:11434/v1")
    runs = ws.ingest_runs(
        100,
        models=["llama3.2"],
        features=["chat"],
        users=["u_1", "u_2"],
        days=30,
        success_rate=0.94,
        sessions=10,
    )
    ws.add_budget("workspace", 50, period_type="monthly", action="notify")
    for r in ws.sample(runs, 20):
        ws.record_outcome(r, "resolved", value_usd=6.0)
        ws.score(r, "quality", 0.9)
```

## Helper API

Defined in `_base.py`; every method maps to a real API call and is best-effort.

| Method | Populates |
|---|---|
| `ingest_runs(n, models=, features=, users=, days=, success_rate=, sessions=)` | Runs, spans, and provider calls via `/ingest/v1/batch`; run count is multiplied by `--traffic-multiplier` |
| `add_route(alias, model, priority=, **flags)` | Gateway routes, including Ollama `base_url`, cache, compiler, routing, and policy flags |
| `add_budget(scope_type, limit_usd, period_type=, action=, scope_id=)` | Workspace, feature, or user budgets |
| `record_outcome(run, outcome_type, success=, value_usd=, labels=)` | Business outcomes for ROI dashboards |
| `score(run, metric_name, value, label=)` | Evaluation score events |
| `add_alert(name, metric, operator, threshold)` | Alert rules |
