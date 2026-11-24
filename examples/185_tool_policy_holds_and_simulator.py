"""
examples/185_tool_policy_holds_and_simulator.py

Govern an agent's tools with one policy system, end to end:

  1. Preview a policy's impact on the last 7 days of real tool calls before saving it.
  2. Save it: `wire_transfer` needs approval, `shell` is blocked.
  3. The agent asks before running a tool (GET /tools/check): blocked → 403,
     approval-required → 403 with a real approval id.
  4. Through the gateway, a request offering `wire_transfer` in tools[] is held (202 +
     approval id) instead of reaching the model; after approval the agent resubmits with
     metadata["runledger.approval_id"].

Required env vars:
  RUNLEDGER_BASE_URL       API, e.g. http://localhost:8201
  RUNLEDGER_SESSION_KEY    a workspace admin's dashboard session key (manages policies)
  RUNLEDGER_API_KEY        the agent's workload key
Optional:
  RUNLEDGER_GATEWAY_URL    gateway-rs, e.g. http://localhost:8210
  RUNLEDGER_GATEWAY_ALIAS  a route alias, e.g. smart
"""

from __future__ import annotations

import os
import sys

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
SESSION_KEY = os.getenv("RUNLEDGER_SESSION_KEY", "")
AGENT_KEY = os.getenv("RUNLEDGER_API_KEY", "")
GATEWAY_URL = os.getenv("RUNLEDGER_GATEWAY_URL")
ALIAS = os.getenv("RUNLEDGER_GATEWAY_ALIAS")

if not SESSION_KEY or not AGENT_KEY:
    print("Error: RUNLEDGER_SESSION_KEY and RUNLEDGER_API_KEY are required", file=sys.stderr)
    raise SystemExit(1)

admin = httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {SESSION_KEY}"}, timeout=30)
agent = httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {AGENT_KEY}"}, timeout=30)

POLICIES = [
    {"name": "wire transfers need approval", "tool_name": "wire_transfer", "action": "require_approval", "priority": 10},
    {"name": "no shell", "tool_name": "shell", "action": "block", "priority": 20},
]


def main() -> None:
    # 1. Impact preview: what would this policy have done to last week's traffic?
    for draft in POLICIES:
        impact = admin.post("/tool-policies/simulate-impact", json={"days": 7, "policy": draft}).json()
        print(
            f"[preview] {draft['name']}: {impact['calls_replayed']} calls replayed, "
            f"{impact['newly_blocked']} newly blocked, {impact['newly_held']} newly held"
        )

    # 2. Save the policies.
    created = [admin.post("/tool-policies", json=p).json() for p in POLICIES]
    print(f"[ok] saved {len(created)} policies")

    try:
        # 3. The SDK-side check (the Python SDK does this for you before each tool call).
        blocked = agent.get("/tools/check/shell")
        print(f"[check] shell → {blocked.status_code} {blocked.json()['detail']}")
        held = agent.get("/tools/check/wire_transfer")
        approval_id = held.headers.get("x-runledger-approval-id")
        print(f"[check] wire_transfer → {held.status_code}, approval {approval_id}")

        # 4. The gateway holds a request that offers the tool to the model.
        if GATEWAY_URL and ALIAS:
            body = {
                "model": ALIAS,
                "messages": [{"role": "user", "content": "Pay invoice 42"}],
                "tools": [
                    {"type": "function", "function": {"name": "wire_transfer", "parameters": {"type": "object"}}},
                    {"type": "function", "function": {"name": "shell", "parameters": {"type": "object"}}},
                ],
            }
            gw = httpx.post(
                f"{GATEWAY_URL}/gateway/chat/completions",
                headers={"Authorization": f"Bearer {AGENT_KEY}"},
                json=body,
                timeout=60,
            )
            hold_id = gw.headers.get("x-runledger-approval-id")
            print(f"[gateway] {gw.status_code}: held for approval {hold_id}")
            print("          approve it on the Approvals page, then resubmit with:")
            print(f'          body["metadata"] = {{"runledger.approval_id": "{hold_id}"}}')
            print("          (`shell` is removed from tools[] because it is blocked)")
    finally:
        for p in created:
            admin.delete(f"/tool-policies/{p['id']}")
        print("[done] policies archived")


if __name__ == "__main__":
    main()
