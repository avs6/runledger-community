"""Smoke test: platform lifecycle posture endpoint returns expected structure."""

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
    f"{BASE}/analytics/platform-lifecycle-posture",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

errors = []
for section in ("finops_context", "gateway_context", "governance_context", "org_access_context"):
    if section not in data:
        errors.append(f"missing {section}")

if "period_days" not in data:
    errors.append("missing period_days")

if data.get("finops_context"):
    for k in ("billing_periods", "active_billing_periods", "chargeback_rules", "ledger_snapshots"):
        if k not in data["finops_context"]:
            errors.append(f"finops_context missing {k}")

if data.get("gateway_context"):
    for k in ("gateway_routes", "distinct_providers", "guardrail_rules"):
        if k not in data["gateway_context"]:
            errors.append(f"gateway_context missing {k}")

if data.get("governance_context"):
    for k in ("audit_events_30d", "tool_policies", "alert_rules"):
        if k not in data["governance_context"]:
            errors.append(f"governance_context missing {k}")

if data.get("org_access_context"):
    for k in ("total_workspaces", "total_api_keys", "total_users"):
        if k not in data["org_access_context"]:
            errors.append(f"org_access_context missing {k}")

if errors:
    print("FAIL:", "; ".join(errors))
    sys.exit(1)

print("PASS: platform-lifecycle-posture structure valid")
print(f"  period_days={data['period_days']}")
print(f"  billing_periods={data['finops_context']['billing_periods']}")
print(f"  gateway_routes={data['gateway_context']['gateway_routes']}")
print(f"  audit_events={data['governance_context']['audit_events_30d']}")
print(f"  workspaces={data['org_access_context']['total_workspaces']}")
