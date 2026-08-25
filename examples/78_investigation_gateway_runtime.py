"""
Example: Investigation gateway runtime posture.

Demonstrates querying the investigation-gateway-runtime-posture endpoint that
surfaces provider routing, guardrail evaluation, response cache, and rate
limit context for investigation scope.

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
    print("--- Investigation Gateway Runtime Posture ---")
    posture = api("GET", "/analytics/investigation-gateway-runtime-posture")
    print(json.dumps(posture, indent=2))

    prov = posture.get("provider_context", {})
    print(f"\nProviders: {prov.get('distinct_providers', 0)}")
    print(f"Active routes: {prov.get('active_routes', 0)} / {prov.get('total_routes', 0)}")
    print(f"Routing policies: {prov.get('routing_policies', 0)}")

    route = posture.get("route_context", {})
    print(f"Gateway requests (30d): {route.get('gateway_requests_30d', 0)}")
    print(f"Cache hits (30d): {route.get('cache_hits_30d', 0)}")

    guard = posture.get("guardrail_context", {})
    print(f"Guardrail rules: {guard.get('active_rules', 0)}")
    print(f"Guardrail events (30d): {guard.get('events_30d', 0)}, blocks: {guard.get('blocks_30d', 0)}")

    cache = posture.get("cache_context", {})
    print(f"Cache configs: {cache.get('enabled_configs', 0)}, entries: {cache.get('cache_entries', 0)}")
    print(f"Total cache hits: {cache.get('total_hits', 0)}, savings: ${cache.get('savings_usd', 0):.2f}")

    rl = posture.get("rate_limit_context", {})
    print(f"Routes with RPM limits: {rl.get('routes_with_rpm_limits', 0)}")
    print(f"Routes with cost limits: {rl.get('routes_with_cost_limits', 0)}")


if __name__ == "__main__":
    main()
