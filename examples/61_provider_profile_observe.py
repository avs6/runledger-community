"""
Example: Provider profile observe posture — per-provider traffic and cost investigation.

Demonstrates querying the provider-profile-observe-posture endpoint that surfaces
30-day run count, request count, error count, cost, savings, token totals, and
average latency for a specific provider/model pair.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
  RUNLEDGER_PROFILE_ID
"""

from __future__ import annotations

import json
import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
PROFILE_ID = os.getenv("RUNLEDGER_PROFILE_ID", "")


def api(method: str, path: str, params: dict | None = None):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def main():
    print("--- Provider Profile Observe Posture ---")
    posture = api("GET", "/analytics/provider-profile-observe-posture", {"profile_id": PROFILE_ID})
    print(json.dumps(posture, indent=2))

    print(f"\nProvider: {posture.get('provider')}/{posture.get('model')}")

    runs = posture.get("runs", {})
    print(f"\nRuns (30d): {runs.get('run_count', 0)}")
    print(f"Requests (30d): {runs.get('request_count', 0)}")
    print(f"Errors (30d): {runs.get('error_count', 0)}")

    cost = posture.get("cost", {})
    print(f"\nTotal cost: ${cost.get('total_cost_usd', 0):.4f}")
    print(f"Total savings: ${cost.get('total_savings_usd', 0):.4f}")

    tokens = posture.get("tokens", {})
    print(f"\nInput tokens: {tokens.get('input_tokens', 0):,}")
    print(f"Output tokens: {tokens.get('output_tokens', 0):,}")

    perf = posture.get("performance", {})
    avg_latency = perf.get("avg_latency_ms")
    print(f"Avg latency: {avg_latency}ms" if avg_latency else "Avg latency: --")


if __name__ == "__main__":
    main()
