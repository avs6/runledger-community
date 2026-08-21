"""
Example: onboarding setup readiness check.

Demonstrates the expanded 19-step onboarding readiness model
covering Foundation, FinOps, Gateway, Observe, and Safety.

Uses a workspace-level API key.
"""

from __future__ import annotations

import json
import os
import urllib.request


BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ["RUNLEDGER_API_KEY"]


def api_get(path: str) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


SECTIONS = {
    "Foundation": [
        "has_org", "has_workspace", "has_api_key", "has_first_run",
        "has_gateway_route", "has_budget", "has_alert_rule",
    ],
    "FinOps": ["has_budget_notification", "has_billing_period"],
    "Gateway": ["has_provider_profile", "has_guardrail", "has_rate_limit"],
    "Safety": [
        "has_mcp_server", "has_search_tool", "has_tool_policy",
        "has_approval_config", "has_data_capture", "has_security_config",
        "has_tag",
    ],
}


def main() -> None:
    status = api_get("/settings/onboarding-status")

    print(f"Overall: {status['completed']}/{status['total']} steps ({status['pct']}%)\n")

    for section, keys in SECTIONS.items():
        done = sum(1 for k in keys if status.get(k))
        print(f"  {section}: {done}/{len(keys)}")
        for k in keys:
            mark = "x" if status.get(k) else " "
            print(f"    [{mark}] {k}")
        print()

    if status["pct"] < 100:
        missing = [k for section_keys in SECTIONS.values() for k in section_keys if not status.get(k)]
        print(f"Next steps: complete {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")
    else:
        print("All setup steps complete!")


if __name__ == "__main__":
    main()
