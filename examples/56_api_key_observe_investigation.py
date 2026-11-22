"""
Example: API-key-scoped observe investigation and workspace posture.

Demonstrates querying the API key observe footprint and workspace observe
posture endpoints, plus filtering runs and analytics by api_key_id.

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


def api(method: str, path: str, payload: dict | None = None):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload) if payload is not None else None,
        timeout=30,
    )
    response.raise_for_status()
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


def main() -> None:
    if not API_KEY:
        raise SystemExit("Set RUNLEDGER_API_KEY before running this example.")

    keys = api("GET", "/settings/api-keys")
    if not keys["items"]:
        print("No API keys found — create one first.")
        return
    key_id = keys["items"][0]["id"]
    key_name = keys["items"][0].get("name", "unnamed")
    print(f"Investigating API key: {key_name} ({key_id})")

    footprint = api("GET", f"/analytics/api-key-footprint/{key_id}")
    print(f"  30d run count: {footprint['run_count']}")
    print(f"  30d total cost: ${footprint['total_cost_usd']:.4f}")
    print(f"  30d total tokens: {footprint['total_tokens']}")
    print(f"  Models used: {footprint['models_used']}")
    print(f"  Recent runs: {len(footprint['recent_runs'])}")

    runs = api("GET", f"/runs?api_key_id={key_id}&limit=5")
    print(f"  Runs scoped to key: {len(runs['items'])}")

    sessions = api("GET", f"/sessions?api_key_id={key_id}&page_size=5")
    print(f"  Sessions scoped to key: {sessions['total']}")

    summary = api("GET", f"/analytics/summary?api_key_id={key_id}")
    print(f"  Analytics summary cost: ${summary['total_cost_usd']:.4f}")

    print("\n--- Workspace Observe Posture ---")
    ctx = api("GET", f"/context?entity=api_key&id={key_id}")
    print("  Related: " + ", ".join(f"{i['label']}={i['value']}" for i in ctx["items"]))


if __name__ == "__main__":
    main()
