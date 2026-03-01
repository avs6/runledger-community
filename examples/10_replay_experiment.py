"""
Example 10 — Replay harness + user analytics deepening.

What this demonstrates
──────────────────────
- User cohort classification (P0–P3 spend tiers)
- Anomaly detection list (populated by nightly worker)
- Creating a named dataset from recent run IDs
- Defining a cost-projection experiment (gpt-4o vs gpt-4o-mini)
- Triggering the projection worker
- Polling for results and printing a cost-comparison table

Cost projection uses actual token counts from provider_calls and
ProviderPricing rates — no real LLM calls are made.

Prerequisites
─────────────
A running RunLedger stack with at least one instrumented run:

    docker compose -f infra/docker-compose.yml up -d

Install
───────
    pip install httpx python-dotenv

Run it
──────
    # Copy .env.example → .env and fill in your values, then:
    python 10_replay_experiment.py

Key .env variables used here:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8000  (local Docker stack)
"""

from __future__ import annotations

import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    raise SystemExit("Set RUNLEDGER_API_KEY in .env before running this example.")

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _get(path: str) -> dict:
    r = httpx.get(f"{API_URL}{path}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict) -> dict:
    r = httpx.post(f"{API_URL}{path}", json=body, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


# ── 1. Cohort distribution ─────────────────────────────────────────────────────

print("\n═══════════════════════════════════════")
print("  1 · User cohort distribution (30-day)")
print("═══════════════════════════════════════")

cohorts = _get("/analytics/users/cohorts")
if not cohorts["items"]:
    print("  (no users with spend in the last 30 days)")
else:
    print(f"  Window: {cohorts['window_days']} days")
    print(f"  {'Tier':<6} {'Users':>6} {'Total spend':>14} {'Avg spend':>12}")
    print(f"  {'─'*6} {'─'*6} {'─'*14} {'─'*12}")
    for c in cohorts["items"]:
        print(
            f"  {c['cohort_tier']:<6} {c['user_count']:>6} "
            f"  ${float(c['total_cost_usd']):>12.4f} "
            f"  ${float(c['avg_cost_usd']):>10.4f}"
        )

# ── 2. Anomaly list ────────────────────────────────────────────────────────────

print("\n═══════════════════════════════════════")
print("  2 · User spend anomalies")
print("═══════════════════════════════════════")

anomalies = _get("/analytics/users/anomalies")
count = len(anomalies["items"])
if count == 0:
    print("  No anomalies flagged yet.")
    print("  Tip: run the anomaly_detection Celery worker to populate this table:")
    print("    uv run celery -A runledger_api.core.celery call analytics.anomaly_detection")
else:
    print(f"  {count} anomaly flag(s) found:")
    for a in anomalies["items"][:5]:
        print(f"    {a['end_user_id']:<30} z={float(a['zscore']):.1f}σ  {a['reason'][:60]}")

# ── 3. Get 3 recent run IDs ────────────────────────────────────────────────────

print("\n═══════════════════════════════════════")
print("  3 · Fetch 3 recent run IDs")
print("═══════════════════════════════════════")

runs_resp = _get("/runs?limit=3")
run_ids = [r["id"] for r in runs_resp["items"]]

if not run_ids:
    print("  No runs found. Send some instrumented requests first.")
    raise SystemExit(0)

for rid in run_ids:
    print(f"    {rid}")

# ── 4. Create dataset ──────────────────────────────────────────────────────────

print("\n═══════════════════════════════════════")
print("  4 · Create replay dataset")
print("═══════════════════════════════════════")

dataset = _post("/replay/datasets", {"name": "example-10-dataset", "run_ids": run_ids})
dataset_id = dataset["id"]
print(f"  Created dataset: {dataset['name']} (id={dataset_id})")
print(f"  Run count: {dataset['run_count']}")

# ── 5. Create experiment ───────────────────────────────────────────────────────

print("\n═══════════════════════════════════════")
print("  5 · Create cost-projection experiment")
print("═══════════════════════════════════════")

experiment = _post(
    "/replay/experiments",
    {
        "dataset_id": dataset_id,
        "name": "gpt-4o vs gpt-4o-mini",
        "configs": [
            {"model": "gpt-4o", "label": "GPT-4o"},
            {"model": "gpt-4o-mini", "label": "GPT-4o-mini"},
        ],
    },
)
experiment_id = experiment["id"]
print(f"  Created experiment: {experiment['name']} (id={experiment_id})")
print(f"  Status: {experiment['status']}")

# ── 6. Trigger projection ──────────────────────────────────────────────────────

print("\n═══════════════════════════════════════")
print("  6 · Trigger projection worker")
print("═══════════════════════════════════════")

run_resp = _post(f"/replay/experiments/{experiment_id}/run", {})
print(f"  Status → {run_resp['status']}")

# ── 7. Poll for results ────────────────────────────────────────────────────────

print("\n═══════════════════════════════════════")
print("  7 · Poll for results (up to 30s)")
print("═══════════════════════════════════════")

results = None
for attempt in range(10):
    time.sleep(3)
    r = _get(f"/replay/experiments/{experiment_id}/results")
    if r["status"] == "completed":
        results = r
        break
    print(f"  [{attempt + 1}/10] status={r['status']}…")

if results is None:
    print("  Worker did not complete within 30s.")
    print("  Ensure Celery is running: uv run celery -A runledger_api.core.celery worker --loglevel=info")
    raise SystemExit(1)

# ── 8. Print results ───────────────────────────────────────────────────────────

print(f"\n  Completed at: {results['completed_at']}")
print(f"  Dataset runs used: {results['dataset_run_count']}")
print()
print(f"  {'Model':<25} {'Input tok':>10} {'Output tok':>11} {'Avg cost/run':>14} {'Total cost':>12} Pricing")
print(f"  {'─'*25} {'─'*10} {'─'*11} {'─'*14} {'─'*12} {'─'*7}")
for c in results["configs"]:
    pricing_ok = "✓" if c["pricing_found"] else "⚠ missing"
    print(
        f"  {c['model']:<25} {c['total_input_tokens']:>10,} {c['total_output_tokens']:>11,} "
        f"  ${float(c['avg_cost_per_run']):>12.6f} "
        f"  ${float(c['projected_cost_usd']):>10.4f} {pricing_ok}"
    )

if results["deltas"]:
    print()
    print("  Cost deltas:")
    for d in results["deltas"]:
        delta_str = f"{float(d['cost_delta_pct']):+.1f}%" if d["cost_delta_pct"] is not None else "n/a"
        print(f"    {d['config_a']} → {d['config_b']}: {delta_str}")

print()
print("  ✓ Phase 10 example complete.")
print()
print("  Tips:")
print("  • Run the anomaly detection worker nightly:")
print("      celery beat --app=runledger_api.core.celery (with schedule configured)")
print("  • Open /replay in the dashboard to manage datasets and experiments interactively.")
print("  • Open /analytics/users to see cohort badges and anomaly flags per user.")
