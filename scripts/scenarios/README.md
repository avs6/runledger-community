# Simulation scenarios

Each scenario module (`NAME` + `run(sim)`) populates a RunLedger workspace **through the REST
API**. Scenarios are organized in **folders** and discovered recursively, so add categories
freely:

```
scenarios/
  _base.py          # SimClient helpers (loads costs from scripts/pricing.yaml)
  hosted/           # OpenAI / Anthropic / Google scenarios
    01_saas_support.py …
  ollama/           # local Ollama scenarios (priced → cost is tracked)
    01_coding_assistant.py …
```

The driver [`scripts/full_simulate.py`](../full_simulate.py) resets the cluster, bootstraps an
admin, imports [`scripts/pricing.yaml`](../pricing.yaml), and runs every scenario (sorted by path):

```bash
# from the repo root, with the stack running
uv run python scripts/full_simulate.py            # reset (truncate) + run all scenarios
uv run python scripts/full_simulate.py --hard-clean  # wipe every volume first
uv run python scripts/cleanup.py [--hard]         # reset only
```

## What the bundled scenarios simulate

The seven scenarios below create seven orgs and populate **~940 runs**, plus routes,
budgets, outcomes, scores, and alerts. Every model they use is priced in
[`pricing.yaml`](../pricing.yaml), so cost is attributed for **both** hosted and local runs.

| Scenario | Org / Workspace | Models | Demonstrates |
|---|---|---|---|
| `hosted/01_saas_support` | Acme SaaS / Support Bot | gpt-4o-mini, gpt-4o | High-volume support; semantic cache; monthly-notify + daily-block + per-user budgets; ticket-resolved outcomes with $ value; CSAT scores; spend alert |
| `hosted/02_ml_research` | Nova Labs / Research | o3-mini, claude-sonnet-4-6, gpt-4o, llama3.1:8b, llama3.2 | Frontier-vs-local cost/quality; dense multi-metric eval scoring (accuracy/faithfulness/helpfulness); benchmark-passed outcomes |
| `hosted/03_ecommerce_agents` | Shopwave / Agents | gpt-4o-mini, claude-haiku-4-5, gpt-4o, claude-sonnet-4-6 | Multi-provider fallback routes; conversion ROI outcomes ($ value); fraud-review flagging; feature-scoped hard-block budget |
| `ollama/01_coding_assistant` | Acme Dev Tools / Coding Assistant | qwen2.5-coder:14b, deepseek-r1:14b/8b | **Priced local inference** — bug-resolved outcomes, correctness scores, GPU-spend budgets + alert |
| `ollama/02_local_rag` | DataCo / Knowledge Base | llama3.1:8b, nomic-embed-text | Generation **vs embedding** cost split; relevance/faithfulness scores; answer-helpful outcomes |
| `ollama/03_reasoning_agent` | ThinkLocal / Reasoning | deepseek-r1:14b vs 8b | Output-heavy reasoning cost; 14B-vs-8B cost × quality; decision-supported outcomes with $ value |
| `ollama/04_chat_support` | HelpDesk Local / Support Bot | llama3.2, gemma3:latest | Local mirror of the hosted SaaS-support org — compare cost-per-resolved-ticket local vs hosted |

> **Budgets are the one deliberate gap.** `/budgets` requires a workspace-admin *dashboard
> session*, which an API key can't provide, so `add_budget()` is skipped quietly under the
> simulator. Create budgets from the dashboard. Everything else populates end-to-end.
>
> **TODO:** seed budgets automatically by having the simulator perform a real `/auth/login`
> as the platform admin (which bypasses the role check) and posting `/budgets` with that
> session token instead of the API key — pending a check of how a session request selects
> its workspace context.

## Writing a scenario

Create a file in any folder, e.g. `scripts/scenarios/ollama/05_your_scenario.py`:

```python
from scenarios._base import Sim

NAME = "your-scenario"
DESCRIPTION = "One line describing what this simulates."

def run(sim: Sim) -> None:
    ws = sim.workspace("Your Org", "Your Workspace")

    ws.add_route("chat", "gpt-4o-mini", semantic_cache_enabled=True)
    runs = ws.ingest_runs(
        100,
        models=["gpt-4o-mini", "gpt-4o"],
        features=["support", "summarize"],
        users=["u_1", "u_2", "u_3"],
        days=30,
        success_rate=0.94,
        sessions=15,
    )
    ws.add_budget("workspace", 500, period_type="monthly", action="notify")
    for r in runs:
        if r.success:
            ws.record_outcome(r, "resolved", value_usd=8.0)
            ws.score(r, "quality", 0.9)
```

## The `Workspace` helper API

Defined in [`_base.py`](./_base.py) — every method maps to a real API call and is
best-effort (a failure warns and continues):

| Method | Populates |
|---|---|
| `ingest_runs(n, models=, features=, users=, days=, success_rate=, sessions=)` | Runs + spans + provider calls (via `/ingest/v1/batch`); returns the runs |
| `sample(runs, k=60)` | A random subset — keep per-run scores/outcomes under the 60/min management rate limit |
| `add_route(alias, model, priority=, **flags)` | A gateway route (`semantic_cache_enabled=`, `base_url=` for Ollama, etc.) |
| `add_budget(scope_type, limit_usd, period_type=, action=, scope_id=)` | A budget (skipped under the sim — needs a dashboard session) |
| `record_outcome(run, outcome_type, success=, value_usd=, labels=)` | A business outcome |
| `score(run, metric_name, value, label=)` | An evaluation score |
| `add_alert(name, metric, operator, threshold)` | An alert rule (`metric` ∈ error_rate, p95_latency, avg_score, spend_velocity) |

Costs are computed from a small pricing table in `_base.py`, so analytics and budgets
show real numbers even for free local (Ollama) models.
