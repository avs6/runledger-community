"""
Example: identity-scoped Build & Improve queries.

Demonstrates how to filter Build & Improve surfaces by identity primitives:
- Agents list filtered by access group
- Workflows list filtered by API key
- Evaluation scores filtered by access group
- Workflow run creation with identity attribution
- Model scorecards filtered by API key
"""

from __future__ import annotations

import json
import os
import urllib.request


BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ["RUNLEDGER_API_KEY"]
ACCESS_GROUP_ID = os.environ.get("RUNLEDGER_ACCESS_GROUP_ID", "")
TARGET_API_KEY_ID = os.environ.get("RUNLEDGER_TARGET_API_KEY_ID", "")


def api_get(path: str) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def api_post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main() -> None:
    print("=== Identity-scoped Build & Improve ===\n")

    if ACCESS_GROUP_ID:
        print("--- Agents by access group ---")
        agents = api_get(f"/agents?access_group_id={ACCESS_GROUP_ID}")
        print(f"  Found {agents.get('total', 0)} agents for group {ACCESS_GROUP_ID}")
        for a in agents.get("agents", [])[:3]:
            print(f"    {a['name']} ({a['status']})")

        print("\n--- Workflows by access group ---")
        workflows = api_get(f"/workflows?access_group_id={ACCESS_GROUP_ID}")
        print(f"  Found {workflows.get('total', 0)} workflows for group {ACCESS_GROUP_ID}")

        print("\n--- Evaluations by access group ---")
        scores = api_get(f"/evaluations/scores?access_group_id={ACCESS_GROUP_ID}&limit=5")
        print(f"  Found {len(scores.get('items', []))} scores for group {ACCESS_GROUP_ID}")

        print("\n--- Playground sessions by access group ---")
        sessions = api_get(f"/playground/sessions?access_group_id={ACCESS_GROUP_ID}")
        print(f"  Found {sessions.get('total', 0)} sessions for group {ACCESS_GROUP_ID}")

    if TARGET_API_KEY_ID:
        print("\n--- Workflows by API key ---")
        workflows = api_get(f"/workflows?api_key_id={TARGET_API_KEY_ID}")
        print(f"  Found {workflows.get('total', 0)} workflows for key {TARGET_API_KEY_ID}")

        print("\n--- Model scorecards by API key ---")
        scorecards = api_get(f"/analytics/model-scorecards?api_key_id={TARGET_API_KEY_ID}")
        items = scorecards.get("items", [])
        print(f"  Found {len(items)} model scorecards for key {TARGET_API_KEY_ID}")
        for sc in items[:3]:
            print(f"    {sc['model']}: ${float(sc.get('total_cost', 0)):.4f} ({sc.get('call_count', 0)} calls)")

        print("\n--- Optimization by API key ---")
        opps = api_get(f"/gateway/flywheel/recommendations?api_key_id={TARGET_API_KEY_ID}")
        print(f"  Found {opps.get('total', 0)} recommendations for key {TARGET_API_KEY_ID}")

    if not ACCESS_GROUP_ID and not TARGET_API_KEY_ID:
        print("Set RUNLEDGER_ACCESS_GROUP_ID and/or RUNLEDGER_TARGET_API_KEY_ID to see identity-scoped results.")

    print("\nDone.")


if __name__ == "__main__":
    main()
