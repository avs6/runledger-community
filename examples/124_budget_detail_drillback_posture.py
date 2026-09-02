"""
Example: Budget detail drillback posture.

Queries the budget-detail-drillback-posture analytics endpoint and prints
scope context, runtime context, evidence context, workflow context, and spend.

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
    posture = api("GET", "/analytics/budget-detail-drillback-posture")
    print("Budget Detail — Drillback Posture")
    print("=" * 50)

    sc = posture["scope_context"]
    print(f"\nScope Context:")
    print(f"  Users:          {sc['workspace_users']}")
    print(f"  Access groups:  {sc['access_groups']}")
    print(f"  API keys:       {sc['api_keys']}")

    rt = posture["runtime_context"]
    print(f"\nRuntime Context:")
    print(f"  Cache configs:        {rt['cache_configs']}")
    print(f"  Rate-limited routes:  {rt['rate_limited_routes']}")

    ev = posture["evidence_context"]
    print(f"\nEvidence Context:")
    print(f"  Runs 30d:         {ev['runs_30d']}")
    print(f"  Requests 30d:     {ev['requests_30d']}")
    print(f"  Audit events 30d: {ev['audit_events_30d']}")

    wf = posture["workflow_context"]
    print(f"\nWorkflow Context:")
    print(f"  Workflows:        {wf['workflows']}")
    print(f"  Workflow runs 30d: {wf['workflow_runs_30d']}")

    sp = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  30d spend:        ${sp['total_spend_30d']:.2f}")
    print(f"  Distinct models:  {sp['distinct_models_30d']}")


if __name__ == "__main__":
    main()
