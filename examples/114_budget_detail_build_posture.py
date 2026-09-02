"""
Example: Budget detail build posture.

Queries the budget-detail-build-posture analytics endpoint and prints
budget context, build counts, experiment activity, and spend context
across the workspace.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import json
import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def api(method: str, path: str, payload: dict | None = None):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload) if payload is not None else None,
        timeout=30,
    )
    response.raise_for_status()
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


def main() -> None:
    posture = api("GET", "/analytics/budget-detail-build-posture")
    print("Budget Detail Build Posture")
    print("=" * 50)

    bc = posture["budget_context"]
    print(f"\nBudget Context:")
    print(f"  Active budgets:    {bc['active_budgets']}")
    print(f"  Total limit (USD): {bc['total_limit_usd']}")
    print(f"  Breach count:      {bc['breach_count']}")
    print(f"  Feature budgets:   {bc['feature_budgets']}")

    bl = posture["build_context"]
    print(f"\nBuild Context:")
    print(f"  Prompts:           {bl['prompts']}")
    print(f"  Agents:            {bl['agents']}")
    print(f"  Workflows:         {bl['workflows']}")
    print(f"  Workflow runs (30d): {bl['workflow_runs_30d']}")

    ex = posture["experiment_context"]
    print(f"\nExperiment Context:")
    print(f"  Eval experiments:       {ex['eval_experiments']}")
    print(f"  Eval experiments (30d): {ex['eval_experiments_30d']}")
    print(f"  Replay experiments:     {ex['replay_experiments']}")
    print(f"  Replay experiments (30d): {ex['replay_experiments_30d']}")
    print(f"  Score events (30d):     {ex['score_events_30d']}")

    sc = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  Total spend (30d):   ${sc['total_spend_30d']:.2f}")
    print(f"  Distinct models (30d): {sc['distinct_models_30d']}")


if __name__ == "__main__":
    main()
