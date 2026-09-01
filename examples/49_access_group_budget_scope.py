"""
Example: Access-group budget scope.

This example creates an access group, assigns a budget scoped to that group,
queries the budget and the org-scope posture analytics endpoint, then cleans up.

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

    group = api(
        "POST",
        "/access-groups",
        {"name": "Budget scope demo group", "description": "Temporary group for budget scoping example"},
    )
    group_id = group["id"]
    print(f"Created access group: {group_id} ({group['name']})")

    budget = api(
        "POST",
        "/budgets",
        {
            "scope_type": "access_group",
            "scope_id": group_id,
            "period_type": "monthly",
            "limit_usd": "50.00",
            "action": "block",
        },
    )
    budget_id = budget["id"]
    print(f"Created access-group budget: {budget_id}")
    print(f"  scope_type={budget['scope_type']}  scope_display_name={budget.get('scope_display_name')}")

    scoped = api("GET", f"/budgets?scope_type=access_group&scope_id={group_id}")
    print(f"Budgets scoped to group: {len(scoped['items'])}")

    posture = api("GET", f"/analytics/budget-org-scope-posture/{budget_id}")
    print(f"Org posture — workspace users: {posture['org_context']['workspace_users']}")
    print(f"Org posture — access groups: {posture['org_context']['workspace_access_groups']}")
    print(f"Hub posture — model catalog: {posture['hub_context']['hub_model_count']}")

    api("DELETE", f"/budgets/{budget_id}")
    print(f"Deleted budget {budget_id}")

    api("DELETE", f"/access-groups/{group_id}")
    print(f"Deleted access group {group_id}")


if __name__ == "__main__":
    main()
