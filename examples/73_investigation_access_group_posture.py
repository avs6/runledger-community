"""
Example: Investigation access-group scope posture.

Demonstrates querying the investigation-access-group-posture endpoint that
surfaces access group context (groups, members) and investigation context
(30-day runs, requests, active users, active routes).

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
    print("--- Investigation Access Group Posture ---")
    posture = api("GET", "/analytics/investigation-access-group-posture")
    print(json.dumps(posture, indent=2))

    ag = posture.get("access_group_context", {})
    print(f"\nAccess groups: {ag.get('access_groups', 0)}")
    print(f"Total members: {ag.get('total_members', 0)}")

    ic = posture.get("investigation_context", {})
    print(f"\nRuns (30d): {ic.get('runs_30d', 0)}")
    print(f"Requests (30d): {ic.get('requests_30d', 0)}")
    print(f"Active users: {ic.get('active_users', 0)}")
    print(f"Active routes: {ic.get('active_routes', 0)}")


if __name__ == "__main__":
    main()
