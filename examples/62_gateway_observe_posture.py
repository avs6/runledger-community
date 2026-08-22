"""
Example: Gateway observe posture — workspace-wide traffic, caching, throttling, and cost.

Demonstrates querying the gateway-observe-posture endpoint that surfaces 30-day
traffic breakdown (requests, cache hits/misses, throttled, errors), route context,
run and user counts, cost and savings, token totals, and average latency.

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
    print("--- Gateway Observe Posture ---")
    posture = api("GET", "/analytics/gateway-observe-posture")
    print(json.dumps(posture, indent=2))

    routes = posture.get("routes", {})
    print(f"\nActive routes: {routes.get('active_routes', 0)}")
    print(f"Cache-enabled: {routes.get('cache_enabled', 0)}")
    print(f"Rate-limited: {routes.get('rate_limited', 0)}")

    traffic = posture.get("traffic", {})
    print(f"\nRequests (30d): {traffic.get('total_requests', 0):,}")
    print(f"Cache hits: {traffic.get('cache_hits', 0):,}")
    print(f"Cache misses: {traffic.get('cache_misses', 0):,}")
    print(f"Cache hit rate: {traffic.get('cache_hit_rate', 0) * 100:.1f}%")
    print(f"Throttled: {traffic.get('throttled_requests', 0):,}")
    print(f"Errors: {traffic.get('errors', 0):,}")

    runs = posture.get("runs", {})
    print(f"\nRuns: {runs.get('run_count', 0):,}")
    print(f"Distinct users: {runs.get('distinct_users', 0)}")
    print(f"Distinct models: {runs.get('distinct_models', 0)}")

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
