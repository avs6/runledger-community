"""
Example 22 — OTLP/HTTP trace ingestion.

What this demonstrates
──────────────────────
- Sending traces to RunLedger directly via POST /v1/traces (no RunLedger SDK needed)
- Compatible with any OpenTelemetry-instrumented application
- OpenInference attribute conventions for LLM, TOOL, CHAIN, and AGENT spans
- OTel GenAI attribute conventions as a fallback
- Using an OTel Collector as an intermediate (optional — see below)

Three adoption modes
─────────────────────
1. RunLedger SDK → /ingest/v1/events  (recommended, most features)
2. Your app → OTel SDK → OTel Collector → /v1/traces
3. Your app → OTel SDK → /v1/traces   (direct, no Collector)

This example shows modes 2 and 3 — sending raw OTLP/HTTP JSON to RunLedger.

Install dependencies
─────────────────────
pip install httpx python-dotenv

No OTel SDK is required to run this example — we build the JSON payload manually
to show exactly what RunLedger expects.

Usage
─────
    python 22_otlp_ingest.py

Set environment variables (or create a .env file in examples/):
    RUNLEDGER_API_KEY=rl_dev_xxxx...
    RUNLEDGER_BASE_URL=http://localhost:8000
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")
BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000").rstrip("/")

if not API_KEY:
    print("[WARN] RUNLEDGER_API_KEY not set — will likely get 401")


# ── OTLP helpers ──────────────────────────────────────────────────────────────

def _b64(raw: bytes) -> str:
    """Encode bytes as base64 string (OTLP wire format for IDs)."""
    return base64.b64encode(raw).decode()


def _trace_id() -> str:
    return _b64(uuid.uuid4().bytes + uuid.uuid4().bytes[:0])  # 16 bytes


def _span_id() -> str:
    return _b64(uuid.uuid4().bytes[:8])  # 8 bytes


def _now_ns() -> int:
    return int(time.time() * 1e9)


def _attr(key: str, value: str | int | float | bool) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": value}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    return {"key": key, "value": {"stringValue": str(value)}}


# ── Example 1: simple OpenInference LLM trace ─────────────────────────────────

def build_openinference_trace() -> dict[str, Any]:
    """
    Mimics what openinference-instrumentation-openai would emit for a single
    LLM call inside an agent chain.

    Trace structure:
      agent.run  (AGENT, root)
        ├── chain.invoke  (CHAIN)
        │     └── llm.chat  (LLM) ← token counts + model
        └── tool.execute  (TOOL)
    """
    trace_id = _b64(b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10")
    agent_span_id   = _b64(b"\x01\x02\x03\x04\x05\x06\x07\x08")
    chain_span_id   = _b64(b"\x11\x12\x13\x14\x15\x16\x17\x18")
    llm_span_id     = _b64(b"\x21\x22\x23\x24\x25\x26\x27\x28")
    tool_span_id    = _b64(b"\x31\x32\x33\x34\x35\x36\x37\x38")

    t = _now_ns()

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        _attr("service.name", "support-agent"),
                        _attr("service.version", "1.0.0"),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name": "openinference.instrumentation.openai",
                            "version": "0.1.0",
                        },
                        "spans": [
                            # Root: AGENT span
                            {
                                "traceId": trace_id,
                                "spanId": agent_span_id,
                                "name": "agent.run",
                                "kind": 3,
                                "startTimeUnixNano": str(t),
                                "endTimeUnixNano": str(t + 2_500_000_000),
                                "attributes": [
                                    _attr("openinference.span.kind", "AGENT"),
                                    _attr("session.id", "sess_demo_001"),
                                    _attr("user.id", "u_alice"),
                                ],
                                "status": {"code": 1},
                            },
                            # CHAIN span
                            {
                                "traceId": trace_id,
                                "spanId": chain_span_id,
                                "parentSpanId": agent_span_id,
                                "name": "chain.invoke",
                                "kind": 3,
                                "startTimeUnixNano": str(t + 10_000_000),
                                "endTimeUnixNano": str(t + 1_800_000_000),
                                "attributes": [
                                    _attr("openinference.span.kind", "CHAIN"),
                                ],
                                "status": {"code": 1},
                            },
                            # LLM span — this generates a provider_call in RunLedger
                            {
                                "traceId": trace_id,
                                "spanId": llm_span_id,
                                "parentSpanId": chain_span_id,
                                "name": "ChatOpenAI",
                                "kind": 3,
                                "startTimeUnixNano": str(t + 50_000_000),
                                "endTimeUnixNano": str(t + 1_500_000_000),
                                "attributes": [
                                    _attr("openinference.span.kind", "LLM"),
                                    _attr("llm.model_name", "gpt-4o-mini"),
                                    _attr("llm.provider", "openai"),
                                    _attr("llm.token_count.prompt", 128),
                                    _attr("llm.token_count.completion", 64),
                                    _attr("llm.token_count.total", 192),
                                ],
                                "status": {"code": 1},
                            },
                            # TOOL span — this generates a tool_call in RunLedger
                            {
                                "traceId": trace_id,
                                "spanId": tool_span_id,
                                "parentSpanId": agent_span_id,
                                "name": "search_knowledge_base",
                                "kind": 3,
                                "startTimeUnixNano": str(t + 1_900_000_000),
                                "endTimeUnixNano": str(t + 2_200_000_000),
                                "attributes": [
                                    _attr("openinference.span.kind", "TOOL"),
                                    _attr("tool.name", "search_knowledge_base"),
                                    _attr("tool.description", "Searches the product FAQ"),
                                ],
                                "status": {"code": 1},
                            },
                        ],
                    }
                ],
            }
        ]
    }


# ── Example 2: OTel GenAI conventions ─────────────────────────────────────────

def build_genai_trace() -> dict[str, Any]:
    """
    Mimics what opentelemetry-instrumentation-anthropic might emit using
    the OTel GenAI semantic conventions (gen_ai.*).
    """
    trace_id = _b64(b"\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0")
    root_span_id = _b64(b"\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8")
    llm_span_id  = _b64(b"\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8")

    t = _now_ns()

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        _attr("service.name", "anthropic-chatbot"),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name": "opentelemetry.instrumentation.anthropic",
                            "version": "0.1.0",
                        },
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": root_span_id,
                                "name": "chat_completion",
                                "kind": 3,
                                "startTimeUnixNano": str(t),
                                "endTimeUnixNano": str(t + 1_200_000_000),
                                "attributes": [],
                                "status": {"code": 1},
                            },
                            {
                                "traceId": trace_id,
                                "spanId": llm_span_id,
                                "parentSpanId": root_span_id,
                                "name": "anthropic.chat",
                                "kind": 3,
                                "startTimeUnixNano": str(t + 5_000_000),
                                "endTimeUnixNano": str(t + 1_100_000_000),
                                "attributes": [
                                    _attr("gen_ai.system", "anthropic"),
                                    _attr("gen_ai.request.model", "claude-3-5-sonnet-20241022"),
                                    _attr("gen_ai.usage.input_tokens", 200),
                                    _attr("gen_ai.usage.output_tokens", 85),
                                ],
                                "status": {"code": 1},
                            },
                        ],
                    }
                ],
            }
        ]
    }


# ── Send a trace ───────────────────────────────────────────────────────────────

def send_trace(payload: dict[str, Any], label: str) -> None:
    url = f"{BASE_URL}/v1/traces"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    print(f"\n{'='*60}")
    print(f"Sending: {label}")
    print(f"  → POST {url}")
    spans = sum(
        len(ss.get("spans", []))
        for rs in payload.get("resourceSpans", [])
        for ss in rs.get("scopeSpans", [])
    )
    print(f"  → {len(payload['resourceSpans'])} resource span group(s), {spans} span(s)")

    try:
        resp = httpx.post(url, content=json.dumps(payload), headers=headers, timeout=10)
        print(f"  ← {resp.status_code} {resp.reason_phrase}")
        print(f"  ← {resp.json()}")

        if resp.status_code == 200:
            print("  ✓ Accepted — check the Runs page in ~5s after Celery processes the events")
        elif resp.status_code == 401:
            print("  ✗ Auth failed — check RUNLEDGER_API_KEY")
        elif resp.status_code == 422:
            print("  ✗ Parse error — check the payload format")
        else:
            print(f"  ✗ Unexpected status: {resp.status_code}")
    except httpx.ConnectError:
        print(f"  ✗ Could not connect to {BASE_URL} — is the API running?")


def main() -> None:
    print("RunLedger OTLP Ingestion Example")
    print(f"API: {BASE_URL}")

    # Example 1: OpenInference conventions (LLM + TOOL + CHAIN + AGENT)
    send_trace(
        build_openinference_trace(),
        "OpenInference — agent + chain + LLM + tool",
    )

    # Example 2: OTel GenAI conventions (Anthropic)
    send_trace(
        build_genai_trace(),
        "OTel GenAI — Anthropic claude-3-5-sonnet",
    )

    print("\n" + "="*60)
    print("Done. Check http://localhost:3000/runs to see the ingested traces.")
    print()
    print("OTel Collector (optional):")
    print("  docker compose --profile otel -f infra/docker-compose.yml up otel-collector")
    print("  Then point your OTel SDK exporter at localhost:4318 (HTTP) or localhost:4317 (gRPC).")


if __name__ == "__main__":
    main()
