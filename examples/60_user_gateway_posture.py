"""
Example: User gateway posture — per-user gateway, guardrail, and identity context.

Demonstrates querying the user-gateway-posture endpoint that surfaces
active routes, rate-limited routes, routing policies, 30-day request count,
active guardrail rules, and API keys for a given user's workspace.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
  RUNLEDGER_USER_ID
"""

from __future__ import annotations

import json
import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
USER_ID = os.getenv("RUNLEDGER_USER_ID", "")


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
    print("--- User Gateway Posture ---")
    posture = api("GET", "/analytics/user-gateway-posture", {"user_id": USER_ID})
    print(json.dumps(posture, indent=2))

    gw = posture.get("gateway", {})
    print(f"\nActive routes: {gw.get('active_routes', 0)}")
    print(f"Rate-limited routes: {gw.get('rate_limited_routes', 0)}")
    print(f"Routing policies: {gw.get('routing_policies', 0)}")
    print(f"Requests (30d): {gw.get('requests_30d', 0)}")

    guardrails = posture.get("guardrails", {})
    print(f"\nActive guardrail rules: {guardrails.get('active_rules', 0)}")

    identity = posture.get("identity", {})
    print(f"API keys: {identity.get('api_keys', 0)}")


if __name__ == "__main__":
    main()
