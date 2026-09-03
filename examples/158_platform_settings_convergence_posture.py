"""Fetch platform settings convergence posture (platform admin only): telemetry, audit, compliance, and ops summaries."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/platform-settings-convergence-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"OTLP batches (7d): {data['telemetry_context']['otlp_batches_7d']}")
print(f"OTLP spans (7d): {data['telemetry_context']['otlp_spans_7d']}")
print(f"Capture policies: {data['telemetry_context']['capture_policies']}")
print(f"Audit events (7d): {data['audit_context']['audit_events_7d']}")
print(f"Security events (7d): {data['audit_context']['security_events_7d']}")
print(f"Ledger snapshots: {data['compliance_context']['ledger_snapshots']}")
print(f"Ledger closures: {data['compliance_context']['ledger_closures']}")
print(f"Alert rules: {data['ops_context']['alert_rules']}")
print(f"Alert firings (7d): {data['ops_context']['alert_firings_7d']}")
