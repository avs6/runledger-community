"""
Example: Prompt detail observe posture — version analytics, model usage, cost, and requests.

Demonstrates querying the prompt-detail-observe-posture endpoint that surfaces
prompt version count, workspace runs, distinct models, total/average cost, and
request context for prompt performance analysis.

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
    prompt_name = "my-prompt"
    resp = requests.get(
        f"{BASE}/analytics/prompt-detail-observe-posture",
        headers=HEADERS,
        params={"prompt_name": prompt_name},
    )
    resp.raise_for_status()
    data = resp.json()

    print("=== Prompt Detail Observe Posture ===")
    print(f"Workspace: {data['workspace_id']}")
    print(f"Prompt: {data['prompt_name']}")
    print(f"Period: {data['period_days']}d\n")

    ac = data["analytics_context"]
    print(f"Total prompts: {ac['total_prompts']}  |  Versions: {ac['prompt_versions']}  |  Runs (30d): {ac['runs_30d']}")

    mu = data["model_usage_context"]
    print(f"Distinct models (30d): {mu['distinct_models_30d']}  |  Provider calls: {mu['provider_calls_30d']}")

    cc = data["cost_context"]
    print(f"Total cost (30d): ${cc['total_cost_30d']:.4f}  |  Avg/call: ${cc['avg_cost_per_call']:.6f}")

    print(f"\nFull response:\n{json.dumps(data, indent=2)}")


if __name__ == "__main__":
    main()
