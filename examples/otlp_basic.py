"""
OTLP Basic — minimal quickstart for sending a trace to RunLedger.

What this shows
───────────────
Send a single LLM span directly to RunLedger's OTLP/HTTP endpoint using plain
HTTP — no RunLedger SDK, no OTel SDK, no Collector required.

This is the fastest way to verify your OTLP connection works and to understand
exactly what RunLedger expects in an OTLP payload.

For a comprehensive example covering multi-span traces, AGENT/CHAIN/TOOL span
kinds, retrieval spans, OTel GenAI conventions, and Collector usage, see:
    examples/22_otlp_ingest.py

Install
───────
    pip install httpx

Usage
─────
    python otlp_basic.py

Environment
───────────
    RUNLEDGER_API_KEY   — your RunLedger workspace API key
    RUNLEDGER_BASE_URL  — defaults to http://localhost:8000

What happens after this runs
────────────────────────────
1. RunLedger authenticates via Bearer token → resolves your workspace.
2. The trace is stored in `otlp_ingest_batches` + `otlp_spans_raw`.
3. A Celery worker normalises the LLM span into an AgentRun + ProviderCall.
4. The pricing engine enriches cost_usd within 60 seconds.
5. The run appears in the Run Explorer at http://localhost:3000/runs.
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid

import httpx

API_KEY = os.environ.get("RUNLEDGER_API_KEY", "rl_dev_changeme")
BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000").rstrip("/")


def _b64(b: bytes) -> str:
    """Encode bytes to unpadded base64 as required by OTLP JSON format."""
    return base64.b64encode(b).decode()


def build_trace_payload() -> dict:
    """
    Build a minimal OTLP ExportTraceServiceRequest in JSON format.

    One trace containing one LLM span using OpenInference attributes.
    The span represents a single chat.completions call to gpt-4o-mini.
    """
    trace_id = _b64(uuid.uuid4().bytes)   # 16 bytes → base64
    span_id = _b64(uuid.uuid4().bytes[:8])  # 8 bytes → base64

    now_ns = time.time_ns()
    duration_ns = 1_400_000_000  # 1.4 seconds

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        # service.name identifies the application in RunLedger
                        {"key": "service.name", "value": {"stringValue": "my-agent"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name": "openinference.instrumentation.openai",
                            "version": "0.1.0",
                        },
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": span_id,
                                "name": "chat.completions",
                                "kind": 3,  # CLIENT
                                "startTimeUnixNano": str(now_ns),
                                "endTimeUnixNano": str(now_ns + duration_ns),
                                "status": {"code": 1},  # OK
                                "attributes": [
                                    # OpenInference span kind — tells RunLedger this is an LLM call.
                                    # RunLedger uses this to synthesise a provider_call record.
                                    {
                                        "key": "openinference.span.kind",
                                        "value": {"stringValue": "LLM"},
                                    },
                                    # Model identity
                                    {
                                        "key": "llm.model_name",
                                        "value": {"stringValue": "gpt-4o-mini"},
                                    },
                                    {
                                        "key": "llm.provider",
                                        "value": {"stringValue": "openai"},
                                    },
                                    # Token counts — used by the pricing engine to compute cost_usd
                                    {
                                        "key": "llm.token_count.prompt",
                                        "value": {"intValue": 128},
                                    },
                                    {
                                        "key": "llm.token_count.completion",
                                        "value": {"intValue": 64},
                                    },
                                    # Optional: attach RunLedger context attributes to the root span.
                                    # These link the trace to a session and end-user in RunLedger.
                                    {
                                        "key": "runledger.end_user_id",
                                        "value": {"stringValue": "user-demo-001"},
                                    },
                                    {
                                        "key": "runledger.feature_tag",
                                        "value": {"stringValue": "otlp-quickstart"},
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }


def main() -> None:
    payload = build_trace_payload()

    print(f"Sending OTLP trace to {BASE_URL}/v1/traces")
    print(f"  trace_id (first span): {payload['resourceSpans'][0]['scopeSpans'][0]['spans'][0]['traceId']}")
    print()

    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            f"{BASE_URL}/v1/traces",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            content=json.dumps(payload),
        )

    print(f"Status:   {response.status_code}")
    print(f"Response: {response.text}")
    print()

    if response.status_code == 200:
        print("Success — trace accepted.")
        print()
        print("What happens next:")
        print("  1. A Celery worker normalises the LLM span into an AgentRun + ProviderCall.")
        print("  2. The pricing engine enriches cost_usd within ~60 seconds.")
        print("  3. The run appears at http://localhost:3000/runs")
        print("     (filter by feature_tag='otlp-quickstart' or end_user_id='user-demo-001')")
    elif response.status_code == 401:
        print("Auth failed — check your RUNLEDGER_API_KEY.")
    elif response.status_code == 415:
        print("Content-Type not accepted — must be application/json or application/x-protobuf.")
    else:
        print(f"Unexpected response ({response.status_code}). See RunLedger API logs.")


if __name__ == "__main__":
    main()
