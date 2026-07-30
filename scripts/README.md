# RunLedger scripts

Utilities for running, resetting, and populating a RunLedger stack.

| Script | What it does |
|---|---|
| [`full_simulate.py`](./full_simulate.py) | Reset the cluster, then populate it with realistic data by running every scenario **through the REST API**. |
| [`cleanup.py`](./cleanup.py) | Reset to a blank slate - truncate data (default) or wipe every volume (`--hard`). |
| [`pricing.yaml`](./pricing.yaml) | The simulation pricing catalog - **local Ollama models are priced** so their cost is tracked. |
| [`scenarios/`](./scenarios) | The scenario library, organized in folders (`hosted/`, `ollama/`). |
| [`generate_postman.py`](./generate_postman.py) | Regenerate the Postman collection from the live OpenAPI spec. |
| [`restore.sh`](./restore.sh) | Restore stores from an S3 backup (companion to the Helm backup CronJob). |
| [`bench/`](./bench) | Optimization benchmark harness (baseline vs optimized). |

## What `full_simulate.py` does

One command turns an empty stack into a fully-populated demo:

```bash
uv run python scripts/full_simulate.py            # reset (truncate) -> bootstrap -> import pricing -> run all scenarios
uv run python scripts/full_simulate.py --hard-clean  # wipe every volume first (Qdrant, memory, ...)
uv run python scripts/full_simulate.py --no-clean    # add on top of existing data
```

Step by step:

1. **Reset** - truncates all data by default (preserves admin + provider pricing), or `--hard-clean` wipes every volume.
2. **Bootstrap** - creates / promotes the platform admin (`admin@runledger.local` / `runledger`).
3. **Import pricing** - uploads [`pricing.yaml`](./pricing.yaml) to the provider-pricing catalog, so cost is tracked - including for local Ollama models.
4. **Run every scenario** - discovers every scenario under [`scenarios/`](./scenarios) (recursively, across folders) and runs each. Each scenario creates its own org via `/org/tenants`, logs in as the seeded org admin for management actions, mints a workspace API key from `/settings/api-keys`, and fills the workspace via the API: gateway routes, runs (`/ingest/v1/batch`), budgets, outcomes, scores, and alerts.
5. **Summary** - prints each workspace, its API key, and run count.

Everything goes through the **public REST API** exactly as a real client would - no direct database writes - so it exercises the real ingest / metering / budgets / outcomes paths. Cost enrichment and rollups run on Celery, so give analytics ~60s to populate.

## Pricing local models

By default RunLedger prices local models at `$0` (see `config/pricing.yml`). For the simulator,
[`scripts/pricing.yaml`](./pricing.yaml) instead assigns a **small per-1M-token cost to Ollama models**
(representing GPU / electricity / infra spend), so local inference accrues real, trackable spend —
budgets bite, and you can compare cost-per-outcome of local vs hosted. It's the single source of truth:
`full_simulate` imports it into the catalog **and** uses it to compute each ingested run's cost. Tune the
numbers to your hardware.

## Adding scenarios

Scenarios live in folders under [`scenarios/`](./scenarios) - see [`scenarios/README.md`](./scenarios/README.md).
Create a folder (with an `__init__.py`), drop in a module exposing `NAME` + `run(sim)`, and it's picked up
automatically:

```python
# scripts/scenarios/ollama/05_my_scenario.py
from scenarios._base import Sim

NAME = "my-scenario"
DESCRIPTION = "One line describing it."

def run(sim: Sim) -> None:
    ws = sim.workspace("My Org", "My Workspace")
    ws.add_route("chat", "llama3.1:8b", base_url="http://host.docker.internal:11434/v1")
    runs = ws.ingest_runs(100, models=["llama3.1:8b"], features=["chat"], users=["u_1"])
    for r in runs:
        ws.record_outcome(r, "resolved", value_usd=6.0)
        ws.score(r, "quality", 0.9)
```
