"""
examples/104_tool_registry_runtime_scope.py

Demonstrates tool registry runtime scope and evidence across
workspace scope, API key attribution, gateway routing, observe
evidence, and budget linkage:

1. Fetch the tool registry runtime posture
2. List registered tools with enforcement status
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
        posture = client.get("/analytics/tool-registry-runtime-posture").json()
        print("=== Tool Registry Runtime Scope ===")
        print(f"  Workspaces: {posture['workspace_scope']['total_workspaces']} total, "
              f"{posture['workspace_scope']['workspace_scoped_tools']} enforced tools")
        print(f"  API Keys: {posture['api_key_scope']['active_keys']} active, "
              f"{posture['api_key_scope']['keys_with_tool_calls_30d']} with tool calls (30d)")
        print(f"  MCP: {posture['mcp_scope']['active_mcp_servers']} active servers, "
              f"{posture['mcp_scope']['mcp_tool_calls_30d']} tool calls (30d)")

        print("\n=== Gateway Runtime ===")
        gw = posture["gateway_runtime"]
        print(f"  Model Routes: {gw['model_routes']}")
        print(f"  Cache Configs Active: {gw['cache_configs_active']}")
        print(f"  Rate-Limited Routes: {gw['rate_limited_routes']}")

        print("\n=== Observe Evidence (30d) ===")
        obs = posture["observe_evidence"]
        print(f"  Tool Runs: {obs['tool_runs_30d']}")
        print(f"  Tool Requests: {obs['tool_requests_30d']}")

        print("\n=== Budget Linkage ===")
        bl = posture["budget_linkage"]
        print(f"  Tool-Scoped Budgets: {bl['tool_scoped_budgets']}")
        print(f"  Budget Notifications (30d): {bl['budget_notifications_30d']}")

        tools = client.get("/tool-registry").json()
        print(f"\n=== Registered Tools ({len(tools.get('items', []))}) ===")
        for t in tools.get("items", [])[:5]:
            print(f"  {t['tool_name']} — policy={t['policy']}, "
                  f"enforced={t.get('runtime_enforcement', False)}")

        print("\n=== Cross-Suite Scope Links ===")
        links = [
            "Workspaces (/workspaces)",
            "API Keys (/api-keys)",
            "MCP Registry (/mcp-registry)",
            "Model Gateway (/gateway)",
            "Response Cache (/gateway?tab=cache)",
            "Rate Limits (/gateway?tab=rate-limits)",
            "Run Detail (/runs)",
            "Request Flow (/request-explorer)",
            "Budgets (/budgets)",
            "Budget Detail (/budgets?view=detail)",
        ]
        for link in links:
            print(f"  -> {link}")
        print(f"\nAll {len(links)} cross-suite surfaces linked via runtime scope card.")


if __name__ == "__main__":
    main()
