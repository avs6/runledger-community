#!/usr/bin/env python3
"""
Example 11 - Ledger compliance closure.

Demonstrates the current Bundle D operator flow:
1. GET  /ledger/closure-summary
2. POST /ledger/snapshots/generate
3. GET  /ledger/snapshots
4. GET  /ledger/verify/{snapshot_date}

Install:
    pip install httpx python-dotenv

Run:
    python examples/11_ledger_verify.py

Environment:
    RUNLEDGER_BASE_URL=http://localhost:8201
    RUNLEDGER_API_KEY=<platform-admin bearer token or compatible admin key>
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("Set RUNLEDGER_API_KEY before running this example.")
    sys.exit(1)


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def separator(title: str) -> None:
    print(f"\n{'=' * 64}")
    print(title)
    print("=" * 64)


def main() -> None:
    with httpx.Client(base_url=API_URL, headers=headers(), timeout=30) as client:
        separator("1. Fetch closure summary")
        response = client.get("/ledger/closure-summary")
        response.raise_for_status()
        summary = response.json()
        print(f"readiness_status   : {summary['readiness_status']}")
        print(f"evidence_score     : {summary['evidence_score']}/5")
        print(f"missing_evidence   : {', '.join(summary['missing_evidence']) or 'none'}")
        print(f"recent_audit_events: {summary['recent_audit_event_count']}")

        if summary.get("latest_closed_period"):
            period = summary["latest_closed_period"]
            print(
                "latest_closed_period: "
                f"{period['period_start']} -> {period['period_end']} "
                f"net={period['net_cost_usd']}"
            )
        else:
            print("latest_closed_period: none")

        separator("2. Generate snapshot")
        response = client.post("/ledger/snapshots/generate")
        response.raise_for_status()
        snapshot = response.json()
        print(f"snapshot_date      : {snapshot['snapshot_date']}")
        print(f"total_cost_usd     : {snapshot['total_cost_usd']}")
        print(f"call_count         : {snapshot['call_count']}")
        print(f"hash_prefix        : {snapshot['hash'][:16]}")

        separator("3. List snapshots")
        response = client.get("/ledger/snapshots")
        response.raise_for_status()
        snapshots = response.json()["items"]
        print(f"snapshot_count     : {len(snapshots)}")
        for item in snapshots[:5]:
            print(
                f"  {item['snapshot_date']} "
                f"cost={item['total_cost_usd']} calls={item['call_count']}"
            )

        separator("4. Verify latest snapshot")
        response = client.get(f"/ledger/verify/{snapshot['snapshot_date']}")
        response.raise_for_status()
        verification = response.json()
        print(f"status             : {verification['status']}")
        print(f"match              : {verification['match']}")
        print(f"stored_hash        : {(verification['stored_hash'] or '')[:16]}")
        print(f"computed_hash      : {(verification['computed_hash'] or '')[:16]}")

        separator("5. Refresh closure summary")
        response = client.get("/ledger/closure-summary")
        response.raise_for_status()
        refreshed = response.json()
        print(f"readiness_status   : {refreshed['readiness_status']}")
        print(f"evidence_score     : {refreshed['evidence_score']}/5")
        print(f"missing_evidence   : {', '.join(refreshed['missing_evidence']) or 'none'}")


if __name__ == "__main__":
    main()
