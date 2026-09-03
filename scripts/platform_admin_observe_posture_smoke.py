"""Smoke test: platform admin observe posture endpoint returns expected structure."""

import os
import sys
import urllib.request
import json

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
if not KEY:
    print("RUNLEDGER_API_KEY not set")
    sys.exit(1)

req = urllib.request.Request(
    f"{BASE}/analytics/platform-admin-observe-posture",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

errors = []
for section in ("monitoring_context", "telemetry_context", "governance_context", "build_context"):
    if section not in data:
        errors.append(f"missing {section}")

if "period_days" not in data:
    errors.append("missing period_days")

if data.get("monitoring_context"):
    for k in ("alert_rules", "alert_firings_7d", "guardrail_events_7d"):
        if k not in data["monitoring_context"]:
            errors.append(f"monitoring_context missing {k}")

if data.get("telemetry_context"):
    for k in ("otlp_batches_7d", "otlp_spans_7d"):
        if k not in data["telemetry_context"]:
            errors.append(f"telemetry_context missing {k}")

if data.get("governance_context"):
    for k in ("guardrail_rules", "tool_policies", "capture_policies"):
        if k not in data["governance_context"]:
            errors.append(f"governance_context missing {k}")

if data.get("build_context"):
    for k in ("eval_experiments", "eval_datasets", "agents", "workflow_runs_7d"):
        if k not in data["build_context"]:
            errors.append(f"build_context missing {k}")

if errors:
    print("FAIL:", "; ".join(errors))
    sys.exit(1)

print("PASS: platform-admin-observe-posture structure valid")
print(f"  period_days={data['period_days']}")
print(f"  alert_rules={data['monitoring_context']['alert_rules']}")
print(f"  otlp_batches={data['telemetry_context']['otlp_batches_7d']}")
print(f"  guardrail_rules={data['governance_context']['guardrail_rules']}")
print(f"  eval_experiments={data['build_context']['eval_experiments']}")
