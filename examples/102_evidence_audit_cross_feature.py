"""
examples/102_evidence_audit_cross_feature.py

Demonstrates evidence & audit cross-feature linkage:

1. Fetch the evidence audit cross posture (FinOps, Org, Gateway, Observe)
2. List recent audit events to show source-feature provenance
3. Generate a governance audit pack for compliance evidence
4. Print a summary of cross-feature evidence coverage

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


def check(resp: httpx.Response, label: str) -> dict:
    if resp.status_code not in (200, 201, 204):
        print(f"{label} failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 204:
        return {}
    return resp.json()


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=30)

    posture = check(
        client.get("/analytics/evidence-audit-cross-posture"),
        "Evidence audit cross posture",
    )
    print("=== Evidence & Audit Cross-Feature Posture ===")
    fc = posture.get("finops_context", {})
    oc = posture.get("org_context", {})
    gc = posture.get("gateway_context", {})
    rc = posture.get("observe_context", {})
    print(f"  FinOps:")
    print(f"    Active budgets:     {fc.get('active_budgets', 0)}")
    print(f"    Billing periods:    {fc.get('billing_periods', 0)}")
    print(f"    Chargeback rules:   {fc.get('chargeback_rules', 0)}")
    print(f"    Ledger snapshots:   {fc.get('ledger_snapshots', 0)}")
    print(f"  Org & Access:")
    print(f"    Organization:       {oc.get('org_name', '—')}")
    print(f"    Workspace users:    {oc.get('workspace_users', 0)}")
    print(f"    Active API keys:    {oc.get('active_api_keys', 0)}")
    print(f"  Gateway:")
    print(f"    Providers:          {gc.get('total_providers', 0)}")
    print(f"    Routes:             {gc.get('total_routes', 0)}")
    print(f"    Rate-limited:       {gc.get('rate_limited_routes', 0)}")
    print(f"  Observe:")
    print(f"    Audit events (30d): {rc.get('audit_events_30d', 0)}")
    print(f"    Agent runs (30d):   {rc.get('total_runs_30d', 0)}")
    print(f"    Alert rules:        {rc.get('total_alert_rules', 0)}")
    print(f"    Alert firings (30d):{rc.get('alert_firings_30d', 0)}")

    events = check(
        client.get("/audit/events", params={"limit": 5}),
        "Audit events",
    )
    items = events.get("items", [])
    print(f"\n=== Recent Audit Events ({len(items)}) ===")
    for e in items[:5]:
        target = e.get("target_type", "—")
        action = e.get("action", "—")
        print(f"  [{action}] target={target}")

    pack = check(
        client.get("/governance/audit-pack", params={"from": "2026-01-01", "to": "2026-12-31"}),
        "Governance audit pack",
    )
    summary = pack.get("summary", {})
    print(f"\n=== Governance Pack Summary ===")
    print(f"  Total requests:      {summary.get('total_requests', 0)}")
    print(f"  Policies enforced:   {summary.get('policies_enforced', 0)}")
    print(f"  Approvals processed: {summary.get('approvals_processed', 0)}")
    print(f"  Alerts fired:        {summary.get('alerts_fired', 0)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
