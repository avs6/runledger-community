"""
examples/101_data_protection_gateway_observe.py

Demonstrates data protection gateway & observe integration:

1. Fetch the data protection gateway posture (providers, guardrails, runs, alerts)
2. List recent security events for investigation context
3. List active capture policies to correlate with gateway activity
4. Print a summary of gateway-scoped data protection

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
        client.get("/analytics/data-protection-gateway-posture"),
        "Data protection gateway posture",
    )
    print("=== Data Protection Gateway & Observe Posture ===")
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

    events = check(
        client.get("/security/events", params={"limit": 5}),
        "Security events",
    )
    items = events.get("items", [])
    print(f"\n=== Recent Security Events ({len(items)}) ===")
    for e in items[:5]:
        print(f"  [{e.get('event_type', '—')}] {e.get('description', '—')[:60]}")

    policies = check(client.get("/capture-policy/scopes"), "Capture policy scopes")
    p_items = policies.get("items", [])
    print(f"\n=== Capture Policy Scopes ({len(p_items)}) ===")
    for p in p_items[:10]:
        print(f"  [{p.get('scope_type', '—')}] {p.get('scope_id', '—')} — "
              f"mode={p.get('privacy_mode', '—')}")

    print("\nDone.")


if __name__ == "__main__":
    main()
