# Simulation scenarios

Each `NN_*.py` file here is a self-contained scenario that populates a RunLedger
workspace **through the REST API**. The driver [`scripts/full_simulate.py`](../full_simulate.py)
resets the cluster, bootstraps an admin, and runs every scenario in filename order.

```bash
# from the repo root, with the stack running
uv run python scripts/full_simulate.py            # reset (truncate) + run all scenarios
uv run python scripts/full_simulate.py --hard-clean  # wipe every volume first
uv run python scripts/cleanup.py [--hard]         # reset only
```

## Writing a scenario

Create `scripts/scenarios/NN_your_scenario.py`:

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
| `add_route(alias, model, priority=, **flags)` | A gateway route (`semantic_cache_enabled`, etc.) |
| `add_budget(scope_type, limit_usd, period_type=, action=, scope_id=)` | A budget |
| `record_outcome(run, outcome_type, success=, value_usd=, labels=)` | A business outcome |
| `score(run, metric_name, value, label=)` | An evaluation score |
| `add_alert(name, metric, operator, threshold)` | An alert rule |

Costs are computed from a small pricing table in `_base.py`, so analytics and budgets
show real numbers even for free local (Ollama) models.
