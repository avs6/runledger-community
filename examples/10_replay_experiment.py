"""
Example 10 — Experiments through the gateway: eval a dataset, replay recorded runs,
turn the winner into a route recommendation.

What this demonstrates
──────────────────────
- Listing the gateway route aliases you can test (GET /playground/models)
- An eval experiment: a small dataset with expected outputs, run against two
  route aliases with POST /experiments/{id}/run?wait=true. Every item is a real
  gateway call (budgets, guardrails and routing apply) recorded as a run, and is
  scored by expected-output match plus any evaluators you attach.
- A replay experiment: curate a dataset from recorded runs (their captured
  conversations) with POST /datasets/from-runs and replay it against an alias.
- POST /experiments/{id}/recommend-route: turn the result into a Flywheel
  recommendation, then apply it from Optimization (audited, with rollback).

The old Replay Lab (/replay, cost projection only) was merged into experiments as
mode="replay" (review B-07).

Prerequisites
─────────────
A running RunLedger stack with at least one active gateway route alias, and a
workspace API key in .env.

Run it
──────
    pip install httpx python-dotenv
    python 10_replay_experiment.py

Key .env variables used here:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8201  (local Docker stack)
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
if not API_KEY:
    raise SystemExit("Set RUNLEDGER_API_KEY in .env before running this example.")

client = httpx.Client(base_url=API_URL, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=180)


def show(title: str) -> None:
    print(f"\n── {title} " + "─" * max(0, 60 - len(title)))


show("1 · Route aliases you can test")
aliases = [m["alias"] for m in client.get("/playground/models").raise_for_status().json()["items"]]
print("  ", aliases or "none — add a gateway route first")
if not aliases:
    raise SystemExit(0)
models = [{"model": a} for a in aliases[:2]]

show("2 · Eval dataset")
dataset = (
    client.post(
        "/datasets",
        json={
            "name": "example-10-eval",
            "items": [
                {"input": "What is 2+2? Answer with a number.", "expected_output": "4"},
                {"input": "What is the capital of France? One word.", "expected_output": "Paris"},
                {"input": "Spell 'cat' backwards.", "expected_output": "tac"},
            ],
        },
    )
    .raise_for_status()
    .json()
)
print(f"   dataset {dataset['id'][:8]}… with {dataset['item_count']} items")

show("3 · Eval experiment through the gateway")
exp = (
    client.post(
        "/experiments",
        json={
            "name": "example-10-eval",
            "mode": "eval",
            "dataset_id": dataset["id"],
            "models": models,
        },
    )
    .raise_for_status()
    .json()
)
exp = (
    client.post(f"/experiments/{exp['id']}/run", params={"wait": "true"}).raise_for_status().json()
)
summary = exp["results"]["summary"]
print(
    f"   status={exp['status']}  calls={summary['calls']}  errors={summary['errors']}  via={summary['via']}"
)
for row in exp["results"]["models"]:
    print(
        f"   {row['label']:<20} score={row['avg_score']}  match={row['expected_match_rate']}  "
        f"latency={row['avg_latency_ms']}ms  avg_cost={row['avg_cost_usd']}"
    )
for d in exp["results"]["deltas"]:
    print(
        f"   {d['candidate']} vs {d['baseline']}: score {d['score_delta']}, cost {d['cost_delta_pct']}%"
    )

show("4 · Route recommendation from the result")
rec = client.post(f"/experiments/{exp['id']}/recommend-route", json={"max_score_drop": 0.05})
if rec.status_code == 201:
    r = rec.json()
    print(
        f"   pending recommendation {r['recommendation_id'][:8]}…: {r['alias']} → {r['proposed_model']}"
    )
    print(
        "   review and apply it under Optimization (POST /gateway/flywheel/recommendations/{id}/apply)"
    )
else:
    print(f"   no recommendation: {rec.json().get('detail')}")

show("5 · Replay recorded runs")
runs = [o["run_id"] for item in exp["results"]["items"] for o in item["outputs"] if o["run_id"]][:3]
replay_ds = client.post("/datasets/from-runs", json={"name": "example-10-replay", "run_ids": runs})
if replay_ds.status_code == 201:
    rd = replay_ds.json()
    rexp = (
        client.post(
            "/experiments",
            json={
                "name": "example-10-replay",
                "mode": "replay",
                "dataset_id": rd["id"],
                "models": models[-1:],
            },
        )
        .raise_for_status()
        .json()
    )
    rexp = (
        client.post(f"/experiments/{rexp['id']}/run", params={"wait": "true"})
        .raise_for_status()
        .json()
    )
    print(f"   replayed {rd['item_count']} runs: {rexp['results']['summary']}")
else:
    # Replays need captured conversations; enable payload capture to use them.
    print(f"   {replay_ds.status_code}: {replay_ds.json().get('detail')}")

print("\nOpen /experiments in the dashboard to browse results, items and the recorded runs.")
