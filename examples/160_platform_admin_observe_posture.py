"""Fetch platform admin observe posture (platform admin only): monitoring, telemetry, governance, and build summaries."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/platform-admin-observe-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Alert rules: {data['monitoring_context']['alert_rules']}")
print(f"Alert firings (7d): {data['monitoring_context']['alert_firings_7d']}")
print(f"Guardrail events (7d): {data['monitoring_context']['guardrail_events_7d']}")
print(f"OTLP batches (7d): {data['telemetry_context']['otlp_batches_7d']}")
print(f"OTLP spans (7d): {data['telemetry_context']['otlp_spans_7d']}")
print(f"Guardrail rules: {data['governance_context']['guardrail_rules']}")
print(f"Tool policies: {data['governance_context']['tool_policies']}")
print(f"Capture policies: {data['governance_context']['capture_policies']}")
print(f"Eval experiments: {data['build_context']['eval_experiments']}")
print(f"Eval datasets: {data['build_context']['eval_datasets']}")
print(f"Agents: {data['build_context']['agents']}")
print(f"Workflow runs (7d): {data['build_context']['workflow_runs_7d']}")
