"""
Example: Performance controls org & platform posture — cache and throttle scope.

Demonstrates querying the performance-controls-org-posture endpoint that surfaces
cache profiles (total, enabled, cache-enabled routes, API keys), rate-limit context
(routes with RPM, pass-through with RPM, active routes, access groups), and platform
context (workspace-scoped flag, configuration status).

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
    print("--- Performance Controls Org & Platform Posture ---")
    posture = api("GET", "/analytics/performance-controls-org-posture")
    print(json.dumps(posture, indent=2))

    cache = posture.get("cache_context", {})
    print(f"\nCache profiles: {cache.get('profiles', 0)}")
    print(f"Enabled profiles: {cache.get('enabled_profiles', 0)}")
    print(f"Cache-enabled routes: {cache.get('cache_enabled_routes', 0)}")
    print(f"API keys: {cache.get('api_keys', 0)}")

    rl = posture.get("rate_limit_context", {})
    print(f"\nRoutes with RPM: {rl.get('routes_with_rpm', 0)}")
    print(f"Pass-through with RPM: {rl.get('passthrough_with_rpm', 0)}")
    print(f"Active routes: {rl.get('active_routes', 0)}")
    print(f"Access groups: {rl.get('access_groups', 0)}")

    platform = posture.get("platform_context", {})
    print(f"\nWorkspace scoped: {platform.get('workspace_scoped', False)}")
    print(f"Cache configured: {platform.get('cache_profiles_configured', False)}")
    print(f"Throttle configured: {platform.get('throttle_configured', False)}")


if __name__ == "__main__":
    main()
