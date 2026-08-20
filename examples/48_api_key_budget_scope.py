"""
Example: API key budget ownership.

This example creates a workspace API key, assigns a budget directly to that key,
and then queries the API-key-scoped budget and chargeback views.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import json
import os
from datetime import date

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

    created_key = api(
        "POST",
        "/settings/api-keys",
        {"name": "Budget owner example", "ownership_type": "service_account", "scopes": []},
    )
    key_id = created_key["id"]
    print(f"Created API key owner: {key_id}")

    budget = api(
        "POST",
        "/budgets",
        {
            "scope_type": "api_key",
            "scope_id": key_id,
            "period_type": "monthly",
            "limit_usd": "25.00",
            "action": "notify",
        },
    )
    print(f"Created API-key budget: {budget['id']}")

    scoped_budgets = api("GET", f"/budgets?scope_type=api_key&scope_id={key_id}")
    print(f"Scoped budgets: {len(scoped_budgets['items'])}")

    period = date.today().strftime("%Y-%m")
    report = api(
        "GET",
        f"/billing/chargeback-report?period={period}&dimension=api_key&api_key_id={key_id}",
    )
    first = report["items"][0]
    print("Chargeback dimension:", first["dimension"])
    print("Chargeback rows:", len(first["breakdown"]))

    api("DELETE", f"/settings/api-keys/{key_id}")
    print("Revoked example API key owner")


if __name__ == "__main__":
    main()
