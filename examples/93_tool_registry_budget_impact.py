"""
examples/93_tool_registry_budget_impact.py

Demonstrates the tool-registry-to-FinOps budget bridge:

1. List registered tools
2. Fetch the tool-registry FinOps posture (budget impact, chargeback, spend)
3. Fetch the chargeback report filtered to the feature_tag dimension
4. Print a summary of tool cost attribution

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

    registry = check(client.get("/tools/registry"), "List tool registry")
    tools = registry.get("items", [])
    print(f"Registered tools: {len(tools)}")
    for t in tools:
        print(f"  - {t['tool_name']}  policy={t['policy']}  enforced={t['runtime_enforcement']}")

    posture = check(
        client.get("/analytics/tool-registry-finops-posture"),
        "Tool registry FinOps posture",
    )
    bc = posture.get("budget_context", {})
    cc = posture.get("chargeback_context", {})
    sc = posture.get("spend_context", {})
    print(f"\nFinOps Budget Impact (30d):")
    print(f"  Active budgets:       {bc.get('total_budgets', 0)}")
    print(f"  Tool-scoped budgets:  {bc.get('tool_scoped_budgets', 0)}")
    print(f"  Total budget limit:   ${bc.get('total_budget_limit_usd', 0):.2f}")
    print(f"  Tool spend:           ${sc.get('tool_spend_30d', 0):.2f}")
    print(f"  Tool calls:           {sc.get('tool_call_count_30d', 0)}")
    print(f"  Total spend:          ${sc.get('total_spend_30d', 0):.2f}")
    total = sc.get("total_spend_30d", 0)
    tool = sc.get("tool_spend_30d", 0)
    pct = (tool / total * 100) if total > 0 else 0
    print(f"  Tool share:           {pct:.1f}%")
    print(f"  Chargeback rules:     {cc.get('chargeback_rules', 0)}")
    print(f"  Tool-dim rules:       {cc.get('tool_dimension_rules', 0)}")

    report = check(
        client.get("/billing/chargeback-report", params={"dimension": "feature_tag"}),
        "Chargeback report (feature_tag)",
    )
    breakdown = report.get("breakdown", [])
    if breakdown:
        print(f"\nChargeback by tool/feature_tag:")
        for item in breakdown[:10]:
            print(
                f"  {item['dimension_value']:30s}  "
                f"${item['cost_usd']:>10.2f}  "
                f"{item['pct_of_total']:>5.1f}%  "
                f"{item['allocation_status']}"
            )
    else:
        print("\nNo chargeback breakdown data for feature_tag dimension yet.")

    print("\nDone.")


if __name__ == "__main__":
    main()
