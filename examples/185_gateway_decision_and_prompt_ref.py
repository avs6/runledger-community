"""
examples/185_gateway_decision_and_prompt_ref.py

Call the gateway with a managed prompt ref and read why it routed the way it did.

  1. Send a chat completion through gateway-rs with "prompt": "<name>@prod" and
     prompt_variables; the gateway renders the prompt as the system message.
  2. Print the X-RunLedger-Decision response header (route, cache, budget, guardrail).
  3. Find the gateway request by workflow and read the run's full decision record
     (GET /gateway/runs/{run_id}/decision) — the same data as the run page's
     "Why this route" panel.

Required env vars:
  RUNLEDGER_API_KEY        a workspace API key (also sent to the gateway)
  RUNLEDGER_BASE_URL       control plane   (default http://localhost:8201)
  RUNLEDGER_GATEWAY_URL    gateway-rs      (default http://localhost:8210)
  RUNLEDGER_GATEWAY_ALIAS  a route alias   (default "default")
  RUNLEDGER_PROMPT_REF     e.g. "support-triage@prod" (create it under Prompts first)
"""

from __future__ import annotations

import json
import os

import httpx

API_KEY = os.environ["RUNLEDGER_API_KEY"]
BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201").rstrip("/")
GATEWAY_URL = os.getenv("RUNLEDGER_GATEWAY_URL", "http://localhost:8210").rstrip("/")
ALIAS = os.getenv("RUNLEDGER_GATEWAY_ALIAS", "default")
PROMPT_REF = os.getenv("RUNLEDGER_PROMPT_REF", "support-triage@prod")
WORKFLOW = "example-185"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def main() -> None:
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{GATEWAY_URL}/gateway/chat/completions",
            headers=HEADERS,
            json={
                "model": ALIAS,
                "prompt": PROMPT_REF,
                "prompt_variables": {"product": "RunLedger"},
                "messages": [{"role": "user", "content": "Ticket 42: can I get a refund?"}],
                "metadata": {"workflow": WORKFLOW},
            },
        )
        print("status:", resp.status_code)
        print("X-RunLedger-Decision:", resp.headers.get("x-runledger-decision"))
        resp.raise_for_status()

        # The gateway request row persists run_id + workflow: no time-window matching.
        requests = client.get(
            f"{BASE_URL}/gateway/requests",
            headers=HEADERS,
            params={"workflow": WORKFLOW, "limit": 1},
        )
        requests.raise_for_status()
        items = requests.json()["items"]
        if not items or not items[0].get("run_id"):
            print("no run recorded yet (streamed calls finalize when the stream ends)")
            return
        run_id = items[0]["run_id"]
        decision = client.get(f"{BASE_URL}/gateway/runs/{run_id}/decision", headers=HEADERS)
        decision.raise_for_status()
        print(json.dumps(decision.json(), indent=2)[:2000])


if __name__ == "__main__":
    main()
