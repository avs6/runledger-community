"""
Bundle C smoke script for chargeback.

Usage:
  RUNLEDGER_BASE_URL=http://localhost:8201
  RUNLEDGER_API_KEY=...
  python scripts/chargeback_smoke.py
"""

from __future__ import annotations

import json
import os
from datetime import date

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def call(method: str, path: str, payload: dict | None = None):
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
        raise SystemExit("RUNLEDGER_API_KEY is required")

    today = date.today()
    period = f"{today.year}-{today.month:02d}"

    rule = call(
        "POST",
        "/billing/chargeback-rules",
        {
            "allocation_type": "direct",
            "dimension": "feature_tag",
            "weight": "1.0",
        },
    )
    print(f"[chargeback] created rule {rule['id']}")

    updated = call(
        "PUT",
        f"/billing/chargeback-rules/{rule['id']}",
        {
            "allocation_type": "showback",
            "dimension": "workspace",
            "weight": "0.8",
            "status": "active",
        },
    )
    print(
        "[chargeback] updated rule "
        f"{updated['id']} -> {updated['allocation_type']}:{updated['dimension']}"
    )

    report = call(
        "GET",
        f"/billing/chargeback-report?period={period}&dimension=workspace",
    )
    print(f"[chargeback] report rows={len(report['items'][0]['breakdown'])}")

    exported = call(
        "GET",
        f"/billing/chargeback-report/export?period={period}&dimension=workspace&format=csv",
    )
    print(f"[chargeback] export bytes={len(exported)}")

    call("DELETE", f"/billing/chargeback-rules/{rule['id']}")
    print("[chargeback] deleted rule")
    print("[chargeback] smoke complete")


if __name__ == "__main__":
    main()
