"""
examples/108_security_runtime_scope.py

Demonstrates security runtime scope and evidence across
identity context, gateway posture, monitoring, and FinOps
accountability:

1. Fetch the security runtime posture
2. List security settings and IP ACL rules
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
        posture = client.get("/analytics/security-runtime-posture").json()
        print("=== Security Runtime Scope ===")
        print(f"  Identity: {posture['identity_context']['workspace_users']} users, "
              f"{posture['identity_context']['active_api_keys']} API keys, "
              f"{posture['identity_context']['security_events_30d']} security events 30d")
        print(f"  Gateway: {posture['gateway_posture']['model_routes']} routes, "
              f"{posture['gateway_posture']['guardrail_rules']} guardrail rules, "
              f"{posture['gateway_posture']['guardrail_events_30d']} events 30d")
        print(f"  Observe: {posture['observe_evidence']['runs_30d']} runs, "
              f"{posture['observe_evidence']['provider_calls_30d']} provider calls 30d")
        print(f"  Monitoring: {posture['monitoring_context']['active_alert_rules']} rules, "
              f"{posture['monitoring_context']['alert_firings_30d']} firings 30d")
        print(f"  FinOps: {posture['finops_context']['chargeback_rules']} chargeback rules, "
              f"{posture['finops_context']['ledger_snapshots']} ledger snapshots")

        settings = client.get("/security/settings").json()
        print(f"\n  Metadata mode: {settings.get('required_metadata_mode', 'N/A')}")
        print(f"  Required fields: {', '.join(settings.get('required_metadata_fields', []))}")


if __name__ == "__main__":
    main()
