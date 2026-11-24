"""
examples/185_model_budget_simulate_and_holds.py

Plan a budget with real data, then watch it and stop runaways:

  1. Simulate a candidate budget against the last 30 days (POST /budgets/simulate):
     when it would have breached and how many calls it would have blocked.
  2. Create it as a model budget: scope_type=model with a pattern (gpt-4*), narrowed
     to one API key when RUNLEDGER_API_KEY_ID is set. The gateway skips routes whose model is over budget.
  3. Read its burn-down (GET /budgets/{id}/burndown): spend this period, run rate and
     the forecast-to-breach date.
  4. Put a session on hold the way runaway protection does (POST
     /budgets/runaway-holds), see /budgets/check refuse it, then release it.
  5. Clean up.

Required env vars:
  RUNLEDGER_API_KEY   a workspace admin key
Optional:
  RUNLEDGER_BASE_URL  (default http://localhost:8201)
  RUNLEDGER_API_KEY_ID  narrow the model budget to this API key (default: all keys)
  MODEL_PATTERN       (default gpt-4*)
  LIMIT_USD           (default 5)
"""

from __future__ import annotations

import os
import sys
import uuid

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201").rstrip("/")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
PATTERN = os.getenv("MODEL_PATTERN", "gpt-4*")
LIMIT = os.getenv("LIMIT_USD", "5")


def main() -> None:
    if not API_KEY:
        print("Error: set RUNLEDGER_API_KEY", file=sys.stderr)
        raise SystemExit(1)
    http = httpx.Client(
        base_url=BASE_URL, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=60
    )
    key_id = os.getenv("RUNLEDGER_API_KEY_ID") or None

    print(f"1. Simulating a daily ${LIMIT} block budget on {PATTERN} over the last 30 days")
    sim = http.post(
        "/budgets/simulate",
        json={
            "scope_type": "model",
            "scope_id": PATTERN,
            "api_key_id": key_id,
            "period_type": "daily",
            "limit_usd": LIMIT,
            "action": "block",
            "days": 30,
        },
    )
    sim.raise_for_status()
    result = sim.json()
    print(f"   {result['summary']}")
    for period in result["periods"][-5:]:
        print(
            f"   {period['period_key']}: ${float(period['spend_usd']):.4f} over "
            f"{period['call_count']} calls, {period['affected_calls']} would be blocked"
        )

    print("2. Creating the model budget")
    created = http.post(
        "/budgets",
        json={
            "scope_type": "model",
            "scope_id": PATTERN,
            "api_key_id": key_id,
            "period_type": "daily",
            "limit_usd": LIMIT,
            "action": "block",
        },
    )
    if created.status_code == 409:
        print(f"   [skip] {created.json()['detail']}")
        return
    created.raise_for_status()
    budget = created.json()
    print(f"   {budget['id']} · {budget['scope_display_name']}")

    try:
        print("3. Burn-down")
        burn = http.get(f"/budgets/{budget['id']}/burndown").json()
        print(
            f"   spent ${float(burn['current_spend_usd']):.4f} of ${float(burn['limit_usd']):.2f}; "
            f"run rate ${float(burn['daily_run_rate_usd']):.4f}/day; "
            f"forecast breach: {burn['forecast_breach_date'] or 'not this period'}"
        )

        print("4. Holding a session")
        session_id = f"example-session-{uuid.uuid4().hex[:6]}"
        hold = http.post(
            "/budgets/runaway-holds",
            json={"subject_type": "session", "subject_id": session_id, "minutes": 10},
        )
        hold.raise_for_status()
        check = http.get("/budgets/check", params={"session_id": session_id}).json()
        print(f"   check while held: allowed={check['allowed']} reason={check.get('reason')}")
        http.post(f"/budgets/runaway-holds/{hold.json()['id']}/release").raise_for_status()
        check = http.get("/budgets/check", params={"session_id": session_id}).json()
        print(f"   check after release: allowed={check['allowed']}")
    finally:
        print("5. Cleaning up")
        http.delete(f"/budgets/{budget['id']}")


if __name__ == "__main__":
    main()
