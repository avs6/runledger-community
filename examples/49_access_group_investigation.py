"""
Example: access-group-scoped observability investigation.

Required env vars:
  RUNLEDGER_API_KEY
  RUNLEDGER_ACCESS_GROUP_ID

Optional env vars:
  RUNLEDGER_BASE_URL
"""

from __future__ import annotations

import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
ACCESS_GROUP_ID = os.getenv("RUNLEDGER_ACCESS_GROUP_ID", "")


def api_get(path: str):
    response = requests.get(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    if not API_KEY:
        raise SystemExit("Set RUNLEDGER_API_KEY before running this example.")
    if not ACCESS_GROUP_ID:
        raise SystemExit("Set RUNLEDGER_ACCESS_GROUP_ID before running this example.")

    query = f"access_group_id={ACCESS_GROUP_ID}"

    overview = api_get(f"/analytics/scoped-summary?scope=workspace&{query}")
    print("[overview] runs:", overview["run_count"])
    print("[overview] spend:", overview["total_cost_usd"])

    runs = api_get(f"/runs?limit=5&{query}")
    print("[runs] loaded:", len(runs["items"]))
    if runs["items"]:
        run_id = runs["items"][0]["id"]
        detail = api_get(f"/runs/{run_id}?{query}")
        print("[run detail] id:", detail["id"])
        print("[run detail] status:", detail["status"])

    flow = api_get(
        f"/runs/flow?scope=workspace&mode=request-route-provider-outcome&metric=requests&limit=25&{query}"
    )
    print("[flow] sampled runs:", flow["sampled_runs"])

    explorer = api_get(f"/analytics/request-explorer?page=1&page_size=10&{query}")
    print("[explorer] total requests:", explorer["total"])


if __name__ == "__main__":
    main()
