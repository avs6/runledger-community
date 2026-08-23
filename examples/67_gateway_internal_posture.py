"""
Example: Gateway internal & platform cohesion posture.

Demonstrates querying the gateway-internal-posture endpoint that surfaces
the gateway family's internal cohesion: providers, guardrails, cache profiles,
throttled routes, routing policies, and platform visibility.

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
    print("--- Gateway Internal & Platform Cohesion Posture ---")
    posture = api("GET", "/analytics/gateway-internal-posture")
    print(json.dumps(posture, indent=2))

    gw = posture.get("gateway_family", {})
    print(f"\nActive routes: {gw.get('active_routes', 0)}")
    print(f"Providers: {gw.get('providers', 0)}")
    print(f"Routing policies: {gw.get('routing_policies', 0)}")
    print(f"Pass-through endpoints: {gw.get('passthrough_endpoints', 0)}")

    gr = posture.get("guardrail_context", {})
    print(f"\nGuardrail rules: {gr.get('rules', 0)}")
    print(f"Active guardrails: {gr.get('active', 0)}")

    cache = posture.get("cache_context", {})
    print(f"\nCache profiles: {cache.get('profiles', 0)}")
    print(f"Cache-enabled routes: {cache.get('cache_enabled_routes', 0)}")

    throttle = posture.get("throttle_context", {})
    print(f"\nRate-limited routes: {throttle.get('rate_limited_routes', 0)}")

    pv = posture.get("platform_visibility", {})
    print(f"\nWorkspace scoped: {pv.get('workspace_scoped', False)}")
    print(f"Provider count: {pv.get('provider_count', 0)}")
    print(f"Guardrails active: {pv.get('guardrails_active', False)}")
    print(f"Cache configured: {pv.get('cache_configured', False)}")
    print(f"Throttle configured: {pv.get('throttle_configured', False)}")


if __name__ == "__main__":
    main()
