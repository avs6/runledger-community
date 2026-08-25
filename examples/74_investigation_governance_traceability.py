"""
Example: Investigation governance traceability.

Demonstrates the end-to-end governance-aware investigation flow:
1. List runs filtered by governance dimensions (tag, tool, security events)
2. Fetch the investigation governance posture for the filtered scope
3. Fetch per-run governance context (tool policy outcomes, security events,
   alert firings, audit log entries, governance pack summary)
4. Correlate a request through tool policy evaluation and audit log

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import json
import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def api(method: str, path: str, params: dict | None = None):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def main():
    # ── Step 1: List runs with governance filters ────────────────────────
    print("=== Step 1: List runs with governance filters ===")
    runs = api("GET", "/runs", params={"limit": 5, "security_event_only": "true"})
    items = runs.get("items", [])
    print(f"Runs with security events: {len(items)}")
    for run in items:
        print(f"  {run['id']} — {run.get('status', '?')} — {run.get('feature_tag', 'untagged')}")

    # ── Step 2: Investigation governance posture ─────────────────────────
    print("\n=== Step 2: Investigation governance posture ===")
    posture = api("GET", "/analytics/investigation-governance-posture")
    print(json.dumps(posture, indent=2))

    tg = posture.get("tool_governance", {})
    print(f"\nActive tool policies: {tg.get('active_policies', 0)}")
    print(f"Total tool calls: {tg.get('total_tool_calls', 0)}")
    print(f"Average risk score: {tg.get('avg_risk_score', 0):.3f}")

    sec = posture.get("security", {})
    print(f"Security events: {sec.get('events', 0)}")

    ar = posture.get("alert_rules", {})
    print(f"Active alert rules: {ar.get('active_rules', 0)}")
    print(f"Recent firings: {ar.get('recent_firings', 0)}")

    al = posture.get("audit_log", {})
    print(f"Governance audit events: {al.get('governance_events', 0)}")

    gp = posture.get("governance_pack", {})
    print(f"Approvals: {gp.get('approvals', 0)}")
    print(f"Tool policies: {gp.get('tool_policies', 0)}")
    print(f"Capture policies: {gp.get('capture_policies', 0)}")
    print(f"Tags: {gp.get('tags', 0)}")

    # ── Step 3: Per-run governance context ────────────────────────────────
    if not items:
        print("\nNo runs to inspect — try without security_event_only filter.")
        runs = api("GET", "/runs", params={"limit": 1})
        items = runs.get("items", [])

    if items:
        run_id = items[0]["id"]
        print(f"\n=== Step 3: Governance context for run {run_id} ===")
        gov = api("GET", f"/runs/{run_id}/governance")
        print(json.dumps(gov, indent=2))

        # ── Step 4: Trace through tool policy and audit log ──────────────
        print(f"\n=== Step 4: Trace tool policy evaluation and audit log ===")
        tools = gov.get("tool_evidence", [])
        print(f"Tool calls with policy context: {len(tools)}")
        for t in tools:
            print(f"  Tool: {t['tool_name']}")
            print(f"    Risk score: {t.get('risk_score', 'n/a')}")
            print(f"    Matched policies: {', '.join(t.get('matched_policy_names', [])) or 'none'}")
            print(f"    Policy actions: {', '.join(t.get('matched_policy_actions', [])) or 'none'}")
            print(f"    Registry enforcement: {t.get('registry_runtime_enforcement', 'n/a')}")

        sec_events = gov.get("security_events", [])
        print(f"\nCorrelated security events: {len(sec_events)}")
        for s in sec_events:
            print(f"  [{s.get('event_type', '?')}] tool={s.get('tool_name', 'n/a')} at {s.get('detected_at', '?')}")

        alerts = gov.get("alert_evidence", [])
        print(f"\nAlert firings: {len(alerts)}")
        for a in alerts:
            print(f"  Rule: {a.get('rule_name', '?')} — metric={a.get('metric_value', '?')} at {a.get('fired_at', '?')}")

        audit = gov.get("audit_events", [])
        print(f"\nAudit log entries: {len(audit)}")
        for e in audit:
            print(f"  [{e.get('action', '?')}] {e.get('target_type', '?')}/{e.get('target_id', '?')} at {e.get('created_at', '?')}")

        tags = gov.get("tags", [])
        print(f"\nRun tags: {', '.join(tags) if tags else 'none'}")
    else:
        print("\nNo runs available to inspect governance context.")

    # ── Step 5: Request flow with governance filters ─────────────────────
    print("\n=== Step 5: Request flow with governance filters ===")
    flow = api("GET", "/runs/flow", params={"limit": 10, "security_event_only": "true"})
    print(f"Flow runs sampled: {flow.get('sampled_runs', 0)}")
    print(f"Total runs: {flow.get('total_runs', 0)}")


if __name__ == "__main__":
    main()
