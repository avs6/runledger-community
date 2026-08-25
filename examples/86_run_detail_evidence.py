"""
Example 86 — Run Detail Runtime Evidence

Demonstrates the WU-014 enriched runtime evidence on the Run detail page:
org identity posture (workspace, MCP registry), scope posture (approvals,
data capture), and investigation gateway/finops posture together.

Usage:
    export RUNLEDGER_API_KEY="rl_test_..."
    python examples/86_run_detail_evidence.py
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        print("=== Org Identity Posture ===")
        r = c.get("/analytics/investigation-org-identity-posture")
        r.raise_for_status()
        org = r.json()
        print(f"  Workspace: {org['org_context']['workspace_name']}")
        print(f"  Workspace users: {org['org_context']['workspace_users']}")
        print(f"  MCP servers: {org['mcp_context']['servers']}")
        print(f"  MCP tool calls (30d): {org['mcp_context']['tool_calls_30d']}")
        print(f"  Telemetry batches (30d): {org['telemetry_context']['batches_30d']}")

        print("\n=== Overview Scope Posture ===")
        r = c.get("/analytics/overview-scope-posture")
        r.raise_for_status()
        scope = r.json()
        print(f"  Pending approvals: {scope['tool_context']['pending_approvals']}")
        print(f"  Capture policies: {scope['tool_context']['capture_policies']}")
        print(f"  Active tool policies: {scope['tool_context']['active_tool_policies']}")

        print("\n=== Investigation FinOps Budget Posture ===")
        r = c.get("/analytics/investigation-finops-budget-posture")
        r.raise_for_status()
        fin = r.json()
        print(f"  Active budgets: {fin['budget_context']['active_budgets']}")
        print(f"  Breach count: {fin['budget_context']['breach_count']}")
        print(f"  30d spend: ${fin['spend_context']['total_spend_30d']:.4f}")

        print("\n=== Investigation Gateway Runtime Posture ===")
        r = c.get("/analytics/investigation-gateway-runtime-posture")
        r.raise_for_status()
        gw = r.json()
        print(f"  Active guardrail rules: {gw['guardrail_context']['active_rules']}")
        print(f"  Guardrail events (30d): {gw['guardrail_context']['events_30d']}")
        print(f"  Guardrail blocks (30d): {gw['guardrail_context']['blocks_30d']}")
        print(f"  Cache configs: {gw['cache_context']['enabled_configs']}")

        print("\nRun detail page combines all four posture feeds into a single")
        print("investigation surface at /runs/{run_id}.")


if __name__ == "__main__":
    main()
