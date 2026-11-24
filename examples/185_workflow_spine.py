"""
examples/185_workflow_spine.py

A workflow end to end: define it, send its traffic, read its health.

  1. Create a workflow linked to a feature tag (409 if another live workflow owns it).
  2. Register an agent with a monthly budget envelope.
  3. Run a function as the workflow with the SDK decorator. Every call is one run,
     attributed to the workflow and the agent at ingest; failures are recorded too.
     Model calls are recorded here with task.model_call so the example needs no
     provider key; with rl.instrument(openai_client) they are captured automatically.
  4. Read the Workflow page data: health card (cost per success, p95 latency, eval
     score), runs, and cost by step rolled up from the model calls.

The same attribution works without the SDK: the X-RunLedger-Workflow header on
/ingest/v1/*, the OTLP attribute runledger.workflow, or a feature_tag on gateway requests.

Required env vars:
  RUNLEDGER_API_KEY     a workspace API key
  RUNLEDGER_BASE_URL    control plane (default http://localhost:8201)
"""

from __future__ import annotations

import os
import sys
import time
import uuid

import httpx
from runledger_sdk import RunLedger, RunLedgerBudgetExceededError, get_run_id

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def api(method: str, path: str, body: dict | None = None) -> httpx.Response:
    return httpx.request(
        method,
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json=body,
        timeout=30,
    )


def main() -> int:
    if not API_KEY:
        print("Set RUNLEDGER_API_KEY")
        return 2
    suffix = uuid.uuid4().hex[:6]
    tag = f"support-triage-{suffix}"

    wf = api("POST", "/workflows", {"name": f"Support triage {suffix}", "feature_tag": tag})
    wf.raise_for_status()
    wf_id = wf.json()["id"]
    print(f"workflow {wf_id} linked to tag {tag}")

    agent = api("POST", "/agents", {"name": f"triage-bot-{suffix}", "budget_envelope": "5.00"})
    agent.raise_for_status()
    agent_id = agent.json()["id"]

    rl = RunLedger(api_key=API_KEY, base_url=BASE_URL)

    @rl.workflow(tag, agent_id=agent_id)
    def triage(ticket: str) -> str:
        # The decorator opened the run; get_run_id() is its id inside the function.
        helper = rl.agent_helper()
        span = helper.record_span(run_id=get_run_id(), name="classify", span_type="llm")
        helper.record_model_call(
            run_id=get_run_id(),
            span_id=span,
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=420,
            output_tokens=60,
            latency_ms=700,
            cost_usd="0.0009",
        )
        if "refund" in ticket:
            raise ValueError("needs a human")
        return "billing"

    for ticket in ["card declined", "invoice copy", "refund please"]:
        try:
            print(f"{ticket!r} -> {triage(ticket)}")
        except ValueError as exc:
            print(f"{ticket!r} -> failed ({exc})")
        except RunLedgerBudgetExceededError as exc:
            print(f"refused by the agent envelope: {exc}")
    rl.flush()

    time.sleep(5)  # let the pipeline worker attribute the runs
    ov = api("GET", f"/workflows/{wf_id}/overview").json()
    h = ov["health"]
    print(
        f"\nhealth: {h['runs']} runs, success {h['success_rate']}, "
        f"cost/success {h['cost_per_success']}, p95 {h['p95_latency_ms']} ms"
    )
    cost = api("GET", f"/workflows/{wf_id}/cost").json()
    for step in cost["cost_by_step"]:
        print(
            f"  step {step['step_name']}: ${step['total_cost']} over {step['invocation_count']} calls"
        )
    print(f"\nopen it: http://localhost:3201/workflows/{wf_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
