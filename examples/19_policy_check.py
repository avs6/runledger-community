"""
Example 19 - Unified policy decision checks.

Demonstrates:
1. POST /policies/check with no constraints (allow)
2. POST /policies/check with tool policy and model alias checks
3. POST /policies/check with an evaluation score gate

Environment:
  RUNLEDGER_API_KEY   required
  RUNLEDGER_BASE_URL  optional (default: http://localhost:8000)
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
    print("ERROR: RUNLEDGER_API_KEY is required", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def call_policy_check(payload: dict) -> None:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=20) as client:
        resp = client.post("/policies/check", json=payload)

    print(f"Request: {payload}")
    print(f"Status : {resp.status_code}")
    if resp.status_code != 200:
        print(resp.text)
        return

    data = resp.json()
    print(
        "Decision: allowed={allowed} decision={decision} downgrade_model={model}".format(
            allowed=data.get("allowed"),
            decision=data.get("decision"),
            model=data.get("downgrade_model"),
        )
    )
    if data.get("reasons"):
        print("Reasons :")
        for reason in data["reasons"]:
            print(f"  - {reason}")
    print("Raw     :", data)


if __name__ == "__main__":
    section("1) Base check (no constraints)")
    call_policy_check({})

    section("2) Tool + gateway checks")
    call_policy_check(
        {
            "tool_name": "search",
            "model_alias": "gpt-4o-mini",
            "end_user_id": "user-demo",
            "feature_tag": "support-chat",
        }
    )

    section("3) Evaluation score gate")
    call_policy_check(
        {
            "score_gate": {
                "name": "helpfulness",
                "min_value": 80,
                "source": "human",
            }
        }
    )
