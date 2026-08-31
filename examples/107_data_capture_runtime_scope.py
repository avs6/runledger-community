"""
examples/107_data_capture_runtime_scope.py

Demonstrates data capture runtime scope and evidence across
gateway evidence, observability, budget context, and ledger
integration:

1. Fetch the data capture runtime posture
2. List active capture policies
3. Print a cross-suite scope summary

Requires RUNLEDGER_API_KEY.
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("Error: RUNLEDGER_API_KEY not set", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def main() -> None:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=30) as client:
        posture = client.get("/analytics/data-capture-runtime-posture").json()
        print("=== Data Capture Runtime Scope ===")
        print(f"  Scope: {posture['capture_scope']['total_workspaces']} workspaces, "
              f"{posture['capture_scope']['capture_policies']} policies, "
              f"{posture['capture_scope']['active_api_keys']} API keys")
        print(f"  Gateway: {posture['gateway_evidence']['provider_calls_30d']} provider calls, "
              f"{posture['gateway_evidence']['model_routes']} routes, "
              f"{posture['gateway_evidence']['cache_configs_active']} cache configs")
        print(f"  Observe: {posture['observe_evidence']['runs_30d']} runs, "
              f"{posture['observe_evidence']['audit_events_30d']} audit events 30d")
        print(f"  Budgets: {posture['budget_context']['total_budgets']} active, "
              f"{posture['budget_context']['budget_notifications_30d']} notifications 30d")
        print(f"  Ledger: {posture['ledger_context']['ledger_snapshots']} snapshots, "
              f"{posture['ledger_context']['ledger_entries_30d']} entries 30d")

        policy = client.get("/capture-policy").json()
        print(f"\n  Global policy: privacy_mode={policy.get('privacy_mode', 'N/A')}")


if __name__ == "__main__":
    main()
