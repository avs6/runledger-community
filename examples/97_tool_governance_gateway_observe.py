"""
examples/97_tool_governance_gateway_observe.py

Demonstrates tool governance gateway & observe runtime traceability:

1. Fetch the tool governance gateway posture (providers, guardrails, tool calls, alerts)
2. List gateway routes with rate-limit status
3. List recent guardrail events
4. Print a summary of runtime enforcement traceability

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
        client.get("/analytics/tool-governance-gateway-posture"),
        "Tool governance gateway posture",
    )
    print("=== Tool Governance Gateway & Observe Posture ===")
    pc = posture.get("provider_context", {})
    gc = posture.get("guardrail_context", {})
    cc = posture.get("cache_context", {})
    rlc = posture.get("rate_limit_context", {})
    rc = posture.get("run_context", {})
    mc = posture.get("monitoring_context", {})
    print(f"  Providers:            {pc.get('total_providers', 0)}")
    print(f"  Gateway routes:       {pc.get('total_routes', 0)}")
    print(f"    Rate-limited:       {rlc.get('rate_limited_routes', 0)}")
    print(f"  Guardrail rules:      {gc.get('total_rules', 0)}")
    print(f"    Events (30d):       {gc.get('events_30d', 0)}")
    print(f"  Cache configs:        {cc.get('active_configs', 0)}")
    print(f"  Tool calls (30d):     {rc.get('tool_calls_30d', 0)}")
    print(f"  Agent runs (30d):     {rc.get('agent_runs_30d', 0)}")
    print(f"  Active alert rules:   {mc.get('active_alert_rules', 0)}")
    print(f"  Alert firings (30d):  {mc.get('alert_firings_30d', 0)}")

    routes = check(client.get("/gateway/routes"), "Gateway routes list")
    route_items = routes.get("items", routes) if isinstance(routes, dict) else routes
    if isinstance(route_items, list):
        print(f"\n=== Gateway Routes ({len(route_items)}) ===")
        for r in route_items[:10]:
            rl = "rate-limited" if r.get("rate_limit_enabled") else "no limit"
            print(f"  {r.get('name', r.get('id', '—'))} — provider={r.get('provider', '—')} [{rl}]")

    guardrails = check(client.get("/guardrails"), "Guardrails list")
    g_items = guardrails.get("items", [])
    print(f"\n=== Guardrail Rules ({len(g_items)}) ===")
    for g in g_items[:10]:
        status = "active" if g.get("is_active") else "inactive"
        print(f"  {g.get('name', '—')} — type={g.get('rule_type', '—')} [{status}]")

    print("\nDone.")


if __name__ == "__main__":
    main()
