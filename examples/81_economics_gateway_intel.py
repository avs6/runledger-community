"""
Example 81 — Economics & Model Intelligence Gateway Links

Demonstrates the two WU-009 posture endpoints that connect Model Usage,
Economics, and Cost & Savings to gateway routing context and investigation
surfaces.

Usage:
    export RUNLEDGER_API_KEY="rl_test_..."
    python examples/81_economics_gateway_intel.py
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        print("=== Model Usage Gateway Posture ===")
        r = c.get("/analytics/model-usage-gateway-posture")
        r.raise_for_status()
        mu = r.json()
        gw = mu["gateway_context"]
        inv = mu["investigation_context"]
        tg = mu["tag_context"]
        print(f"  Routes: {gw['active_routes']}/{gw['total_routes']}")
        print(f"  Models: {gw['distinct_models']}  Policies: {gw['routing_policies']}")
        print(f"  Runs 30d: {inv['runs_30d']}  Gateway reqs: {inv['gateway_requests_30d']}  Calls: {inv['provider_calls_30d']}")
        print(f"  Tags: {tg['active_tags']}/{tg['tags']}")

        print("\n=== Economics Gateway Posture ===")
        r = c.get("/analytics/economics-gateway-posture")
        r.raise_for_status()
        eg = r.json()
        prov = eg["provider_context"]
        gw2 = eg["gateway_context"]
        inv2 = eg["investigation_context"]
        print(f"  Providers: {prov['distinct_providers']}  Gateway reqs 30d: {prov['gateway_requests_30d']}")
        print(f"  Routes: {gw2['active_routes']}  Models: {gw2['distinct_models']}  Policies: {gw2['routing_policies']}")
        print(f"  Runs 30d: {inv2['runs_30d']}  Calls: {inv2['provider_calls_30d']}  Alerts: {inv2['monitoring_alerts_30d']}")

    print("\nDone — use these counts to navigate from economics into gateway config and investigation surfaces.")


if __name__ == "__main__":
    main()
