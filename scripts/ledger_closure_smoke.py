"""
Bundle D smoke script for ledger and compliance closure.

Usage:
  RUNLEDGER_BASE_URL=http://localhost:8201
  RUNLEDGER_API_KEY=...
  python scripts/ledger_closure_smoke.py
"""

from __future__ import annotations

import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def call(method: str, path: str):
    response = requests.request(
        method,
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

    summary = call("GET", "/ledger/closure-summary")
    print(
        "[ledger] closure "
        f"status={summary['readiness_status']} score={summary['evidence_score']}/5"
    )

    snapshot = call("POST", "/ledger/snapshots/generate")
    print(f"[ledger] generated snapshot {snapshot['snapshot_date']}")

    verification = call("GET", f"/ledger/verify/{snapshot['snapshot_date']}")
    print(f"[ledger] verify status={verification['status']} match={verification['match']}")

    snapshots = call("GET", "/ledger/snapshots")
    print(f"[ledger] snapshot count={len(snapshots['items'])}")

    refreshed = call("GET", "/ledger/closure-summary")
    print(
        "[ledger] refreshed closure "
        f"status={refreshed['readiness_status']} missing={','.join(refreshed['missing_evidence'])}"
    )

    print("[ledger] smoke complete")


if __name__ == "__main__":
    main()
