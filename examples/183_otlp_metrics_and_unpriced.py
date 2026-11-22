"""
examples/183_otlp_metrics_and_unpriced.py

Two checks that keep cost numbers honest:

  1. Send GenAI token metrics over OTLP (what Claude Code or an OpenTelemetry-instrumented
     client exports), then compare the tokens they report with what RunLedger recorded.
     Low coverage means calls are not reaching RunLedger as traces, logs or events.
  2. List model calls that have no price, so their cost is missing from spend and
     budgets, and add pricing so they are counted.

Required env vars:
  RUNLEDGER_BASE_URL       (default http://localhost:8201)
  RUNLEDGER_API_KEY        a key with the ingest scope (step 1, sending)
  RUNLEDGER_SESSION_KEY    an org admin's dashboard session key (reading, adding pricing)
"""

from __future__ import annotations

import os
import sys
import time

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201").rstrip("/")
INGEST_KEY = os.getenv("RUNLEDGER_API_KEY", "")
ADMIN_KEY = os.getenv("RUNLEDGER_SESSION_KEY", "")


def token_metrics(input_tokens: int, output_tokens: int) -> dict:
    """One OTLP/JSON metrics request: delta token counts by type."""
    now = str(time.time_ns())

    def point(value: int, kind: str) -> dict:
        return {
            "asInt": str(value),
            "timeUnixNano": now,
            "attributes": [{"key": "gen_ai.token.type", "value": {"stringValue": kind}}],
        }

    return {
        "resourceMetrics": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "support-bot"}},
                        {"key": "runledger.feature_tag", "value": {"stringValue": "support-triage"}},
                    ]
                },
                "scopeMetrics": [
                    {
                        "metrics": [
                            {
                                "name": "gen_ai.client.token.usage",
                                "unit": "{token}",
                                "sum": {
                                    "aggregationTemporality": 1,  # delta
                                    "isMonotonic": True,
                                    "dataPoints": [
                                        point(input_tokens, "input"),
                                        point(output_tokens, "output"),
                                    ],
                                },
                            }
                        ]
                    }
                ],
            }
        ]
    }


def main() -> None:
    if not INGEST_KEY or not ADMIN_KEY:
        print("Error: set RUNLEDGER_API_KEY and RUNLEDGER_SESSION_KEY", file=sys.stderr)
        raise SystemExit(1)
    ingest = {"Authorization": f"Bearer {INGEST_KEY}"}
    admin = {"Authorization": f"Bearer {ADMIN_KEY}"}

    # 1. Metrics in, then reported vs recorded usage.
    resp = httpx.post(f"{BASE_URL}/v1/metrics", headers=ingest, json=token_metrics(1200, 300))
    print(f"[ok] metrics accepted: {resp.status_code}")

    series = httpx.get(
        f"{BASE_URL}/v1/metrics/series",
        headers=admin,
        params={"days": 1, "name": "gen_ai.client.token.usage"},
    ).json()
    for item in series["items"]:
        print(f"     {item['name']} {item['attributes']} total={item['total']}")

    usage = httpx.get(f"{BASE_URL}/v1/metrics/usage", headers=admin, params={"days": 1}).json()
    print(
        f"[ok] tokens reported by metrics: "
        f"{usage['reported']['input_tokens'] + usage['reported']['output_tokens']}, "
        f"recorded: {usage['recorded']['input_tokens'] + usage['recorded']['output_tokens']}, "
        f"coverage: {usage['token_coverage_pct']}%"
    )

    # 2. Calls with no price, and how to fix them.
    unpriced = httpx.get(
        f"{BASE_URL}/providers/pricing/unpriced", headers=admin, params={"days": 30}
    ).json()
    print(
        f"[ok] {unpriced['unpriced_calls']} unpriced calls "
        f"({unpriced['unpriced_pct']}% of calls, {unpriced['unpriced_tokens']} tokens)"
    )
    for model in unpriced["items"][:5]:
        print(f"     {model['provider']}/{model['model']}: {model['calls']} calls")
    # Adding pricing prices existing calls on the next enrichment run (every 60 s):
    # httpx.post(f"{BASE_URL}/providers/pricing", headers=admin, json={
    #     "provider": "openai", "model": "my-model",
    #     "input_cost_per_1m": "0.50", "output_cost_per_1m": "1.50"})


if __name__ == "__main__":
    main()
