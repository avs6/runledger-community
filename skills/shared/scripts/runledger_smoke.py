"""Send a tiny RunLedger telemetry smoke test.

Environment:
  RUNLEDGER_BASE_URL=http://localhost:8201
  RUNLEDGER_API_KEY=rl_live_or_test_key
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import uuid
from datetime import UTC, datetime


def iso_now() -> str:
    return datetime.now(UTC).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", required=True, help="Agent client name, e.g. codex")
    parser.add_argument("--task", default="RunLedger connector smoke test")
    parser.add_argument("--intent", default="integration_test")
    args = parser.parse_args()

    base_url = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8201").rstrip("/")
    api_key = os.environ.get("RUNLEDGER_API_KEY", "")
    if not api_key:
        print("RUNLEDGER_API_KEY is required", file=sys.stderr)
        return 2

    run_id = str(uuid.uuid4())
    events = [
        {
            "event_type": "run_start",
            "run_id": run_id,
            "feature_tag": "agent_connector",
            "deployment_version": "skill-smoke",
            "started_at": iso_now(),
            "metadata": {
                "agent_client": args.client,
                "task": args.task,
                "intent": args.intent,
                "source": "runledger_skill_smoke",
            },
        },
        {
            "event_type": "provider_call",
            "run_id": run_id,
            "provider": "runledger-smoke",
            "model": f"{args.client}-connector",
            "input_tokens": 12,
            "output_tokens": 8,
            "cached_input_tokens": 0,
            "latency_ms": 25,
            "cost_usd": "0.000001",
            "status": "success",
        },
        {
            "event_type": "outcome",
            "run_id": run_id,
            "outcome_type": "connector_smoke",
            "success": True,
            "labels": {"agent_client": args.client, "intent": args.intent},
        },
        {
            "event_type": "run_end",
            "run_id": run_id,
            "status": "succeeded",
            "ended_at": iso_now(),
            "total_cost_usd": "0.000001",
            "total_input_tokens": 12,
            "total_output_tokens": 8,
        },
    ]

    payload = json.dumps({"events": events}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/ingest/v1/batch",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
        print(body)
    print(f"RunLedger smoke run accepted: {run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
