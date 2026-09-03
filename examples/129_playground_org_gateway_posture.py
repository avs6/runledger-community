"""
Example: Playground org & gateway posture — workspace, API key, AI hub, and gateway context.

Demonstrates querying the playground-org-gateway-posture endpoint that surfaces
workspace identity (name, users), API key context, AI hub model catalog, provider
profiles, guardrail rules, cache configs, and rate limit posture for playground
experimentation.

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
    print("--- Playground Org & Gateway Posture ---")
    posture = api("GET", "/analytics/playground-org-gateway-posture")
    print(json.dumps(posture, indent=2))

    ws = posture.get("workspace_context", {})
    print(f"\nWorkspace: {ws.get('workspace_name', '')}")
    print(f"Users: {ws.get('workspace_users', 0)}")

    ak = posture.get("api_key_context", {})
    print(f"\nAPI keys: {ak.get('total_api_keys', 0)}")
    print(f"Active key: {ak.get('active_key_name', '')} ({ak.get('active_key_prefix', '')})")

    hub = posture.get("ai_hub_context", {})
    print(f"\nHub models: {hub.get('hub_active_models', 0)}/{hub.get('hub_models', 0)} active")

    prov = posture.get("provider_context", {})
    print(f"\nProviders: {prov.get('distinct_providers', 0)}")
    print(f"Active routes: {prov.get('active_routes', 0)}")

    gr = posture.get("guardrail_context", {})
    print(f"\nGuardrails: {gr.get('active_guardrails', 0)}/{gr.get('guardrail_rules', 0)} active")

    cache = posture.get("cache_context", {})
    print(f"\nCache configs: {cache.get('cache_enabled', 0)}/{cache.get('cache_configs', 0)} enabled")
    print(f"Cache savings 30d: ${cache.get('cache_savings_30d', 0):.2f}")

    rl = posture.get("rate_limit_context", {})
    print(f"\nRate-limited routes: {rl.get('rate_limited_routes', 0)}")
    print(f"Passthrough endpoints: {rl.get('passthrough_endpoints', 0)}")


if __name__ == "__main__":
    main()
