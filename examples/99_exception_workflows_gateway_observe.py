"""
examples/99_exception_workflows_gateway_observe.py

Demonstrates exception workflows gateway & observe integration:

1. Fetch the exception workflows gateway posture (providers, guardrails, runs, alerts)
2. List recent alert firings to identify investigation targets
3. Pivot from alert to request investigation context
4. Print a summary of gateway-triggered exception workflows

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
        client.get("/analytics/exception-workflows-gateway-posture"),
        "Exception workflows gateway posture",
    )
    print("=== Exception Workflows Gateway & Observe Posture ===")
    pc = posture.get("provider_context", {})
    gc = posture.get("guardrail_context", {})
    cc = posture.get("cache_context", {})
    rlc = posture.get("rate_limit_context", {})
    rc = posture.get("run_context", {})
    mc = posture.get("monitoring_context", {})
    print(f"  Providers:            {pc.get('total_providers', 0)}")
    print(f"  Gateway routes:       {pc.get('total_routes', 0)}")
    print(f"    Rate-limited:       {rlc.get('rate_limited_routes', 0)}")
    print(f"  Guardrail rules:      {gc.get('total_guardrails', 0)}")
    print(f"    Events (30d):       {gc.get('guardrail_events_30d', 0)}")
    print(f"  Cache configs:        {cc.get('cache_configs', 0)}")
    print(f"  Tool calls (30d):     {rc.get('tool_runs_30d', 0)}")
    print(f"  Agent runs (30d):     {rc.get('total_runs_30d', 0)}")
    print(f"  Active alert rules:   {mc.get('total_alert_rules', 0)}")
    print(f"  Alert firings (30d):  {mc.get('alert_firings_30d', 0)}")

    history = check(client.get("/alert-history", params={"limit": 5}), "Alert history")
    items = history.get("items", [])
    print(f"\n=== Recent Alert Firings ({len(items)}) ===")
    for f in items[:5]:
        print(f"  {f.get('alert_rule_name', '—')} — {f.get('metric', '—')} "
              f"{f.get('operator', '—')} {f.get('threshold', '—')} "
              f"(actual: {f.get('actual_value', '—')})")

    pending = check(
        client.get("/approvals", params={"status": "pending", "limit": 5}),
        "Pending approvals",
    )
    p_items = pending.get("items", [])
    print(f"\n=== Pending Approvals ({len(p_items)}) ===")
    for a in p_items[:5]:
        print(f"  {a.get('request_type', '—')} — {a.get('reason', '—')[:60]}")

    print("\nDone.")


if __name__ == "__main__":
    main()
