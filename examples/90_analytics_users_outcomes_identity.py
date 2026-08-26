"""
Example 90 — Analytics Users Outcomes and Identity Refresh

Demonstrates the posture endpoints used by the Analytics Users and Outcomes
pages to surface gateway, workspace, and identity context alongside user
spend analysis and outcome ROI tracking.
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_API_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "rl_test_key")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        # Analytics users — org posture (already present, shown for context)
        org = c.get("/analytics/user-analytics-org-posture").json()
        print("=== User Analytics Org Posture ===")
        print(f"  Org: {org['org_context']['org_name']}")
        print(f"  Workspaces: {org['org_context']['workspace_count']}")
        print(f"  API Keys: {org['user_context']['active_api_keys']}/{org['user_context']['api_keys']}")

        # Analytics users — gateway posture (WU-018 addition)
        gw = c.get("/analytics/model-usage-gateway-posture").json()
        print("\n=== Model Usage Gateway Posture (for Analytics Users) ===")
        print(f"  Active routes: {gw['gateway_context']['active_routes']}/{gw['gateway_context']['total_routes']}")
        print(f"  Distinct models: {gw['gateway_context']['distinct_models']}")
        print(f"  Routing policies: {gw['gateway_context']['routing_policies']}")
        print(f"  Gateway requests (30d): {gw['investigation_context']['gateway_requests_30d']}")

        # Outcomes — finops posture (already present, shown for context)
        fin = c.get("/analytics/outcomes-finops-posture").json()
        print("\n=== Outcomes FinOps Posture ===")
        print(f"  Active budgets: {fin['budget_context']['active_budgets']}/{fin['budget_context']['budgets']}")
        print(f"  Breaches: {fin['budget_context']['breach_count']}")

        # Outcomes — org identity posture (WU-018 addition)
        oid = c.get("/analytics/investigation-org-identity-posture").json()
        print("\n=== Investigation Org Identity Posture (for Outcomes) ===")
        print(f"  Workspace: {oid['org_context']['workspace_name']}")
        print(f"  Workspace users: {oid['org_context']['workspace_users']}")
        print(f"  End users (30d): {oid['user_context']['distinct_end_users_30d']}")
        print(f"  API keys: {oid['api_key_context']['active_keys']}/{oid['api_key_context']['total_keys']}")


if __name__ == "__main__":
    main()
