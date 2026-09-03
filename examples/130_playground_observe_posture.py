"""
Example: Playground observe posture — runs, request flow, model usage, and cost context.

Demonstrates querying the playground-observe-posture endpoint that surfaces
runs (30d/total), provider calls, input/output tokens, distinct models, and
cost/savings context for playground experimentation.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import json
import os

import requests

BASE = os.environ["RUNLEDGER_BASE_URL"]
KEY = os.environ["RUNLEDGER_API_KEY"]
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def main() -> None:
    resp = requests.get(f"{BASE}/analytics/playground-observe-posture", headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    print("=== Playground Observe Posture ===")
    print(f"Workspace: {data['workspace_id']}")
    print(f"Period: {data['period_days']}d\n")

    rc = data["runs_context"]
    print(f"Runs (30d): {rc['runs_30d']}  |  Total: {rc['total_runs']}")

    rf = data["request_flow_context"]
    print(f"Provider calls (30d): {rf['provider_calls_30d']}")
    print(f"Tokens — input: {rf['total_input_tokens']:,}  output: {rf['total_output_tokens']:,}")

    mu = data["model_usage_context"]
    print(f"Distinct models (30d): {mu['distinct_models_30d']}")

    cs = data["cost_savings_context"]
    print(f"Total cost (30d): ${cs['total_cost_30d']:.4f}")
    print(f"Cache configs: {cs['cache_configs']}  |  Est. savings: ${cs['estimated_savings']:.4f}")

    print(f"\nFull response:\n{json.dumps(data, indent=2)}")


if __name__ == "__main__":
    main()
