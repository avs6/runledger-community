"""
Smoke script for access-group-scoped observability.

Usage:
  RUNLEDGER_BASE_URL=http://localhost:8201
  RUNLEDGER_API_KEY=...
  RUNLEDGER_ACCESS_GROUP_ID=...
  python scripts/access_group_observe_smoke.py
"""

from __future__ import annotations

import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
ACCESS_GROUP_ID = os.getenv("RUNLEDGER_ACCESS_GROUP_ID", "")


def call(path: str):
    response = requests.get(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    )
    response.raise_for_status()
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


def main() -> None:
    if not API_KEY:
        raise SystemExit("RUNLEDGER_API_KEY is required")
    if not ACCESS_GROUP_ID:
        raise SystemExit("RUNLEDGER_ACCESS_GROUP_ID is required")

    query = f"access_group_id={ACCESS_GROUP_ID}"

    runs = call(f"/runs?limit=3&{query}")
    print(f"[access-group-observe] runs={len(runs['items'])}")

    if runs["items"]:
        run_id = runs["items"][0]["id"]
        detail = call(f"/runs/{run_id}?{query}")
        graph = call(f"/runs/{run_id}/graph?{query}")
        print(
            f"[access-group-observe] run_detail={detail['id']} "
            f"graph_nodes={len(graph['nodes'])}"
        )

    flow = call(
        f"/runs/flow?scope=workspace&mode=request-route-provider-outcome&metric=requests&limit=20&{query}"
    )
    print(f"[access-group-observe] flow_sampled={flow['sampled_runs']}")

    explorer = call(f"/analytics/request-explorer?page=1&page_size=10&{query}")
    print(f"[access-group-observe] explorer_total={explorer['total']}")

    overview = call(f"/analytics/scoped-summary?scope=workspace&{query}")
    print(f"[access-group-observe] overview_runs={overview['run_count']}")
    print("[access-group-observe] smoke complete")


if __name__ == "__main__":
    main()
