"""Smoke test: platform settings convergence posture endpoint returns expected structure."""

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
    f"{BASE}/analytics/platform-settings-convergence-posture",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

errors = []
for section in ("telemetry_context", "audit_context", "compliance_context", "ops_context"):
    if section not in data:
        errors.append(f"missing {section}")

if "period_days" not in data:
    errors.append("missing period_days")

if data.get("telemetry_context"):
    for k in ("otlp_batches_7d", "otlp_spans_7d", "capture_policies"):
        if k not in data["telemetry_context"]:
            errors.append(f"telemetry_context missing {k}")

if data.get("audit_context"):
    for k in ("audit_events_7d", "security_events_7d"):
        if k not in data["audit_context"]:
            errors.append(f"audit_context missing {k}")

if data.get("compliance_context"):
    for k in ("ledger_snapshots", "ledger_closures"):
        if k not in data["compliance_context"]:
            errors.append(f"compliance_context missing {k}")

if data.get("ops_context"):
    for k in ("alert_rules", "alert_firings_7d"):
        if k not in data["ops_context"]:
            errors.append(f"ops_context missing {k}")

if errors:
    print("FAIL:", "; ".join(errors))
    sys.exit(1)

print("PASS: platform-settings-convergence-posture structure valid")
print(f"  period_days={data['period_days']}")
print(f"  otlp_batches={data['telemetry_context']['otlp_batches_7d']}")
print(f"  audit_events={data['audit_context']['audit_events_7d']}")
print(f"  ledger_snapshots={data['compliance_context']['ledger_snapshots']}")
print(f"  alert_rules={data['ops_context']['alert_rules']}")
