"""Fetch optimization FinOps posture."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/optimization-finops-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Active budgets: {data['budget_context']['active_budgets']} / {data['budget_context']['total_budgets']}")
print(f"  Total limit: ${data['budget_context']['total_limit']:,.2f}")
print(f"  Spend 30d: ${data['budget_context']['spend_30d']:.2f}")
print(f"  Notifications: {data['budget_context']['notifications']}")
print(f"Billing periods: {data['billing_context']['active_billing_periods']} active / {data['billing_context']['total_billing_periods']} total")
print(f"Chargeback rules: {data['chargeback_context']['chargeback_rules']} (active: {data['chargeback_context']['active_chargeback_rules']})")
