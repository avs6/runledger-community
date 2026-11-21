"""
examples/180_workflow_budget_gateway.py

A spend limit on one workflow, enforced by the gateway:

  1. Create a monthly budget on a workflow (scope_type=feature_tag).
     Use action "downgrade" to reroute to a cheaper model once the limit is hit,
     "throttle" to slow traffic down, or "block" to stop it.
  2. Send chat completions through gateway-rs tagged with that workflow
     (metadata.feature_tag). Every priced call is counted against the budget.
  3. Once the limit is reached the gateway applies the action. A blocked request
     gets 429 with "Budget limit reached" and the X-Budget-Id header.
  4. Read the budget's spend and breach history, then clean up.

Access-group, end-user and API-key budgets work the same way. The gateway picks
them up from the calling key, its owner and the request's end user.

Required env vars:
  RUNLEDGER_API_KEY        a workspace API key (also sent to the gateway)
  RUNLEDGER_BASE_URL       control plane   (default http://localhost:8201)
  RUNLEDGER_GATEWAY_URL    gateway-rs      (default http://localhost:8210)
  RUNLEDGER_GATEWAY_ALIAS  a route alias   (default "default")
Optional:
  BUDGET_ACTION            block | downgrade | throttle (default block)
  DOWNGRADE_TO             alias or model for downgrade (required for downgrade)
"""

from __future__ import annotations

import os
import sys
import uuid

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
GATEWAY_URL = os.getenv("RUNLEDGER_GATEWAY_URL", "http://localhost:8210")
ALIAS = os.getenv("RUNLEDGER_GATEWAY_ALIAS", "default")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
ACTION = os.getenv("BUDGET_ACTION", "block")
DOWNGRADE_TO = os.getenv("DOWNGRADE_TO")


def api(method: str, path: str, body: dict | None = None) -> httpx.Response:
    return httpx.request(
        method,
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json=body,
        timeout=30,
    )


def main() -> None:
    if not API_KEY:
        print("Error: RUNLEDGER_API_KEY not set", file=sys.stderr)
        raise SystemExit(1)

    workflow = f"support-triage-{uuid.uuid4().hex[:6]}"
    budget = api(
        "POST",
        "/budgets",
        {
            "scope_type": "feature_tag",
            "scope_id": workflow,
            "period_type": "monthly",
            "limit_usd": "0.001",  # tiny, so the first call or two exhausts it
            "action": ACTION,
            "downgrade_to_model": DOWNGRADE_TO,
        },
    )
    budget.raise_for_status()
    budget_id = budget.json()["id"]
    print(f"[ok] {ACTION} budget {budget_id[:8]} on workflow '{workflow}'")

    try:
        for attempt in range(1, 6):
            resp = httpx.post(
                f"{GATEWAY_URL}/gateway/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": ALIAS,
                    "messages": [{"role": "user", "content": "Summarise ticket #42 in one line."}],
                    "metadata": {"feature_tag": workflow},
                    "cache": False,
                },
                timeout=60,
            )
            if resp.status_code == 429:
                print(f"  call {attempt}: 429 {resp.json().get('detail')}")
                break
            resp.raise_for_status()
            print(f"  call {attempt}: 200 via {resp.json().get('model')}")

        # Spend is counted when the gateway finalizes each call.
        for item in api("GET", "/budgets").json()["items"]:
            if item["id"] == budget_id:
                print(f"[ok] spend ${item['current_spend_usd']} of ${item['limit_usd']}")
        breaches = api("GET", f"/budgets/{budget_id}/breaches").json()["items"]
        print(f"[ok] {len(breaches)} breach(es) recorded")
    finally:
        api("DELETE", f"/budgets/{budget_id}")
        print("[ok] budget deleted")


if __name__ == "__main__":
    main()
