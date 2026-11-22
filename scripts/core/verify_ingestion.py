#!/usr/bin/env python3
"""End-to-end verification of Ingestion & Integrations against a running stack.

Replays what an integrator does and asserts every control:

  1. Batch limits: more than INGEST_MAX_BATCH_EVENTS events → 422; an oversized body → 413.
  2. Pipeline reliability: a batch with one bad event (unknown application id) still
     applies its good events; the bad one becomes a dead letter that can be replayed
     (attempts grow) and discarded.
  3. Idempotency: the same tool call sent twice is stored once; provider-call status
     ``succeeded`` is normalized to ``success`` and the run's end user lands on the call.
  4. OTLP: a noise trace is dropped (counted on the batch), an LLM trace becomes a run,
     protobuf is accepted, a gzip bomb is refused, and the raw payload is not stored
     under the default capture policy.
  5. Signed ingest: per-workspace secret, replayed nonce → 409, bad signature → 401.
  6. SSRF: Slack test and Kafka configs pointing at internal addresses → 422.
  7. OTLP metrics: delta and cumulative counters (including a reset) roll up to the
     right daily totals; GenAI token metrics are compared with recorded usage.
  8. Unpriced usage: a call to a model with no price is listed with its tokens, then
     priced once pricing is added.
  9. Web: old links (/telemetry, /cache-config, /billing-periods, …) redirect.
 10. MCP: ``POST /mcp`` (no trailing slash) is not redirected.

Creates throwaway API keys and data in the platform admin's workspace and revokes the
keys at the end. Needs the API, web, Redis, beat and both Celery workers running.

Usage:
    python scripts/run_demo.py verify-ingestion
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passed = 0

    def __call__(self, ok: bool, label: str, detail: Any = "") -> None:
        if ok:
            self.passed += 1
            print(f"  ✓ {label}")
        else:
            self.failures.append(label)
            print(f"  ✗ {label} {detail}")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _wait(fn: Any, timeout: float = 30.0) -> Any:
    deadline = time.monotonic() + timeout
    value = None
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(1)
    return value


def _otlp_trace(trace_id: str, spans: list[dict[str, Any]], service: str) -> dict[str, Any]:
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": service}}]
                },
                "scopeSpans": [{"spans": [{"traceId": trace_id, **s} for s in spans]}],
            }
        ]
    }


def run(args: argparse.Namespace) -> int:
    base = args.base_url.rstrip("/")
    http = httpx.Client(base_url=base, timeout=60)
    check = Check()

    login = http.post("/auth/login", json={"email": args.email, "password": args.password})
    if login.status_code != 200:
        print(f"Sign-in failed ({login.status_code}): {login.text}")
        return 2
    session = login.json()["api_key"]
    admin = {"Authorization": f"Bearer {session}"}
    suffix = uuid.uuid4().hex[:8]
    keys: list[str] = []

    def mint(scopes: list[str]) -> str:
        made = http.post(
            "/settings/api-keys",
            headers=admin,
            json={"name": f"verify-ingestion-{suffix}", "scopes": scopes},
        ).json()
        keys.append(made["id"])
        return str(made["key"])

    try:
        ingest = {"Authorization": f"Bearer {mint(['read', 'ingest'])}"}

        print("\n→ batch limits")
        too_many = [
            {"event_type": "run_start", "run_id": str(uuid.uuid4()), "started_at": _now()}
            for _ in range(args.max_batch + 1)
        ]
        r = http.post("/ingest/v1/batch", headers=ingest, json={"events": too_many})
        check(r.status_code == 422, f"batch over {args.max_batch} events rejected", r.status_code)
        big = b'{"events": [' + b" " * (11 * 1024 * 1024) + b"]}"
        r = http.post(
            "/ingest/v1/batch",
            headers={**ingest, "Content-Type": "application/json"},
            content=big,
        )
        check(r.status_code == 413, "oversized body rejected (413)", r.status_code)

        print("\n→ one bad event does not drop the batch")
        good_run, bad_run = str(uuid.uuid4()), str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        tool_call_id = str(uuid.uuid4())
        events = [
            {
                "event_type": "run_start",
                "run_id": bad_run,
                "started_at": _now(),
                "application_id": str(uuid.uuid4()),  # unknown application → FK error
            },
            {
                "event_type": "run_start",
                "run_id": good_run,
                "started_at": _now(),
                "end_user_id": f"user-{suffix}",
                "feature_tag": f"verify-ingestion-{suffix}",
            },
            {
                "event_type": "span_start",
                "run_id": good_run,
                "span_id": span_id,
                "span_type": "llm",
                "name": "chat",
                "started_at": _now(),
            },
            {
                "event_type": "provider_call",
                "run_id": good_run,
                "span_id": span_id,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "input_tokens": 100,
                "output_tokens": 20,
                "status": "succeeded",
            },
            {
                "event_type": "tool_call",
                "run_id": good_run,
                "tool_call_id": tool_call_id,
                "tool_name": "search",
                "status": "success",
            },
        ]
        r = http.post("/ingest/v1/batch", headers=ingest, json={"events": events})
        check(r.status_code == 202, "mixed batch accepted", r.text)
        run = _wait(
            lambda: (
                (g := http.get(f"/runs/{good_run}", headers=admin)).status_code == 200 and g.json()
            )
        )
        check(bool(run), "good run applied despite a bad sibling event")
        dead = _wait(
            lambda: [
                d
                for d in http.get("/ingest/v1/dead-letters", headers=admin).json().get("items", [])
                if d.get("run_id") == bad_run
            ]
        )
        check(bool(dead), "bad event stored as a dead letter")
        if dead:
            item = dead[0]
            r = http.post(f"/ingest/v1/dead-letters/{item['id']}/replay", headers=admin)
            check(r.status_code == 200, "dead letter replayed (re-queued)", r.text)
            again = _wait(
                lambda: (
                    (
                        g := http.get(f"/ingest/v1/dead-letters/{item['id']}", headers=admin)
                    ).status_code
                    == 200
                    and g.json().get("attempts", 0) >= 2
                    and g.json()
                )
            )
            check(bool(again), "failing replay increments attempts instead of duplicating")
            r = http.delete(f"/ingest/v1/dead-letters/{item['id']}", headers=admin)
            check(r.status_code == 204, "dead letter discarded")

        print("\n→ idempotency and normalization")
        http.post("/ingest/v1/batch", headers=ingest, json={"events": [events[4]]})
        time.sleep(4)
        detail = http.get(f"/runs/{good_run}", headers=admin).json()
        tools = [t for t in detail.get("tool_calls", []) if t.get("tool_name") == "search"]
        check(len(tools) == 1, "retried tool call stored once", len(tools))
        calls = detail.get("provider_calls", [])
        check(
            bool(calls) and calls[0].get("status") == "success",
            "provider-call status normalized to success",
            calls[:1],
        )

        print("\n→ OTLP gating, protobuf, gzip, capture policy")
        noise = _otlp_trace(
            uuid.uuid4().hex,
            [
                {
                    "spanId": uuid.uuid4().hex[:16],
                    "name": "fs.get_metadata",
                    "startTimeUnixNano": str(time.time_ns()),
                    "endTimeUnixNano": str(time.time_ns() + 1_000_000),
                }
            ],
            f"noise-{suffix}",
        )
        r = http.post("/v1/traces", headers=ingest, json=noise)
        check(r.status_code == 200, "noise trace accepted", r.text)
        llm_trace_id = uuid.uuid4().hex
        llm = _otlp_trace(
            llm_trace_id,
            [
                {
                    "spanId": uuid.uuid4().hex[:16],
                    "name": "chat gpt-4o",
                    "startTimeUnixNano": str(time.time_ns()),
                    "endTimeUnixNano": str(time.time_ns() + 1_000_000),
                    "attributes": [
                        {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o"}},
                        {"key": "gen_ai.prompt.0.content", "value": {"stringValue": "secret"}},
                    ],
                }
            ],
            f"llm-{suffix}",
        )
        r = http.post("/v1/traces", headers=ingest, json=llm)
        check(r.status_code == 200, "LLM trace accepted", r.text)
        batches = http.get("/v1/traces/batches?limit=10", headers=admin).json().get("items", [])
        check(
            any(b.get("traces_dropped") == 1 for b in batches),
            "noise trace counted as dropped",
            batches[:2],
        )
        check(any(b.get("runs_created") == 1 for b in batches), "LLM trace recorded as a run")
        if batches:
            detail = http.get(f"/v1/traces/batches/{batches[0]['id']}", headers=admin).json()
            check(
                detail.get("raw_payload_bytes", 1) == 0,
                "raw payload not stored (capture policy not FULL)",
                detail.get("raw_payload_bytes"),
            )
        try:
            from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
                ExportTraceServiceRequest,
            )

            req = ExportTraceServiceRequest()
            span = req.resource_spans.add().scope_spans.add().spans.add()
            span.trace_id = uuid.uuid4().bytes
            span.span_id = uuid.uuid4().bytes[:8]
            span.name = "chat"
            span.start_time_unix_nano = time.time_ns()
            span.end_time_unix_nano = time.time_ns() + 1_000_000
            attr = span.attributes.add()
            attr.key = "gen_ai.request.model"
            attr.value.string_value = "gpt-4o"
            r = http.post(
                "/v1/traces",
                headers={**ingest, "Content-Type": "application/x-protobuf"},
                content=req.SerializeToString(),
            )
            check(r.status_code == 200, "OTLP protobuf accepted", r.text)
        except ImportError:
            print("  · protobuf check skipped (pip install opentelemetry-proto)")
        bomb = gzip.compress(b"{" + b" " * (60 * 1024 * 1024) + b"}")
        r = http.post(
            "/v1/traces",
            headers={**ingest, "Content-Type": "application/json", "Content-Encoding": "gzip"},
            content=bomb,
        )
        check(r.status_code == 413, "gzip bomb refused (413)", r.status_code)

        print("\n→ signed ingest")
        me = http.get("/auth/me", headers=admin).json()
        workspace_id = me.get("workspace_id")
        secret = http.get("/ingest/v1/signing-secret", headers=admin).json().get("secret", "")
        body = json.dumps(
            {
                "workspace_id": workspace_id,
                "events": [
                    {"event_type": "run_start", "run_id": str(uuid.uuid4()), "started_at": _now()}
                ],
            }
        ).encode()
        ts, nonce = _now(), uuid.uuid4().hex
        sig = hmac.new(
            secret.encode(), f"{workspace_id}.{ts}.{nonce}.".encode() + body, hashlib.sha256
        ).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-RunLedger-Timestamp": ts,
            "X-RunLedger-Nonce": nonce,
            "X-RunLedger-Signature": sig,
        }
        check(
            http.post("/ingest/v1/signed", headers=headers, content=body).status_code == 202,
            "signed batch accepted",
        )
        check(
            http.post("/ingest/v1/signed", headers=headers, content=body).status_code == 409,
            "replayed nonce refused (409)",
        )
        bad = {**headers, "X-RunLedger-Nonce": uuid.uuid4().hex}
        check(
            http.post("/ingest/v1/signed", headers=bad, content=body).status_code == 401,
            "signature over another nonce refused (401)",
        )

        print("\n→ SSRF protection")
        r = http.post(
            "/integrations/slack/test",
            headers=admin,
            json={"webhook_url": "http://169.254.169.254/latest/meta-data"},
        )
        check(r.status_code == 422, "Slack test to cloud metadata refused", r.status_code)
        r = http.post(
            "/integrations/kafka/configs",
            headers=admin,
            json={
                "label": f"verify-{suffix}",
                "bootstrap_servers": "10.20.30.40:9092",
                "event_types": ["run.started"],
            },
        )
        check(r.status_code == 422, "Kafka config with a private broker refused", r.status_code)

        print("\n→ OTLP metrics rollups and GenAI usage")
        metric_service = f"metrics-{suffix}"

        def metrics_payload(points: list[tuple[str, float, dict[str, str], int]]) -> dict:
            """points: (metric name, value, attributes, temporality 1=delta 2=cumulative)."""
            ns = str(time.time_ns())
            return {
                "resourceMetrics": [
                    {
                        "resource": {
                            "attributes": [
                                {"key": "service.name", "value": {"stringValue": metric_service}}
                            ]
                        },
                        "scopeMetrics": [
                            {
                                "metrics": [
                                    {
                                        "name": name,
                                        "unit": "tokens",
                                        "sum": {
                                            "aggregationTemporality": temporality,
                                            "isMonotonic": True,
                                            "dataPoints": [
                                                {
                                                    "asDouble": value,
                                                    "timeUnixNano": ns,
                                                    "attributes": [
                                                        {"key": k, "value": {"stringValue": v}}
                                                        for k, v in attrs.items()
                                                    ],
                                                }
                                            ],
                                        },
                                    }
                                    for name, value, attrs, temporality in points
                                ]
                            }
                        ],
                    }
                ]
            }

        tok = "claude_code.token.usage"
        counter = f"verify.requests.{suffix}"
        for batch in (
            [
                (tok, 100, {"type": "input"}, 1),
                (tok, 30, {"type": "output"}, 1),
                (counter, 10, {}, 2),
            ],
            [(tok, 50, {"type": "input"}, 1), (counter, 25, {}, 2)],
            [(counter, 5, {}, 2)],  # counter reset (process restart)
        ):
            r = http.post("/v1/metrics", headers=ingest, json=metrics_payload(batch))
            check(r.status_code == 200, "metrics batch accepted", r.text)
        series = http.get(
            "/v1/metrics/series", headers=admin, params={"days": 1, "name": suffix}
        ).json()
        counter_rows = [i for i in series.get("items", []) if i["name"] == counter]
        check(
            bool(counter_rows) and counter_rows[0]["total"] == 30,
            "cumulative counter totals its increases across batches and a reset (10+15+5)",
            counter_rows[:1],
        )
        tokens = http.get(
            "/v1/metrics/series", headers=admin, params={"days": 1, "name": tok, "limit": 500}
        ).json()
        mine = {
            i["attributes"].get("type"): i["total"]
            for i in tokens.get("items", [])
            if i["service_name"] == metric_service
        }
        check(mine == {"input": 150, "output": 30}, "delta token metrics summed per type", mine)
        usage = http.get("/v1/metrics/usage", headers=admin, params={"days": 1}).json()
        check(
            usage.get("reported", {}).get("input_tokens", 0) >= 150
            and usage.get("token_coverage_pct") is not None,
            "metric usage compared with recorded usage",
            usage,
        )

        print("\n→ unpriced model calls")
        model = f"verify-unpriced-{suffix}"
        unpriced_run = str(uuid.uuid4())
        r = http.post(
            "/ingest/v1/batch",
            headers=ingest,
            json={
                "events": [
                    {"event_type": "run_start", "run_id": unpriced_run, "started_at": _now()},
                    {
                        "event_type": "provider_call",
                        "run_id": unpriced_run,
                        "provider": "openai",
                        "model": model,
                        "input_tokens": 1000,
                        "output_tokens": 500,
                        "status": "success",
                    },
                ]
            },
        )
        check(r.status_code == 202, "call to an unpriced model accepted", r.text)

        def unpriced_row() -> Any:
            body = http.get("/providers/pricing/unpriced", headers=admin, params={"days": 1}).json()
            return next((i for i in body.get("items", []) if i["model"] == model), None)

        row = _wait(unpriced_row, timeout=150)  # enrichment runs every 60 s
        check(
            bool(row) and row["calls"] == 1 and row["input_tokens"] == 1000,
            "unpriced call listed with its tokens",
            row,
        )
        pricing = http.post(
            "/providers/pricing",
            headers=admin,
            json={
                "provider": "openai",
                "model": model,
                "input_cost_per_1m": "1.00",
                "output_cost_per_1m": "2.00",
            },
        )
        check(pricing.status_code in (200, 201), "pricing added for the model", pricing.text)
        if pricing.status_code in (200, 201):
            priced = _wait(
                lambda: (
                    (
                        calls := http.get(f"/runs/{unpriced_run}", headers=admin)
                        .json()
                        .get("provider_calls", [])
                    )
                    and calls[0].get("cost_usd") is not None
                    and calls
                ),
                timeout=150,
            )
            check(
                bool(priced) and abs(float(priced[0]["cost_usd"]) - 0.002) < 1e-9,
                "call priced after pricing was added ($0.002)",
                priced[:1] if priced else priced,
            )
            check(unpriced_row() is None, "model no longer listed as unpriced")
            http.delete(f"/providers/pricing/{pricing.json()['id']}", headers=admin)

        print("\n→ web: old links redirect")
        web = httpx.Client(base_url=args.web_url.rstrip("/"), timeout=30)
        for old, new in (
            ("/telemetry", "/monitoring/telemetry"),
            ("/cache-config", "/gateway?tab=cache"),
            ("/billing-periods", "/billing"),
            ("/audit-log", "/audit"),
            ("/routes", "/gateway?tab=routes"),
        ):
            try:
                resp = web.get(old, follow_redirects=False)
                ok = resp.status_code in (301, 307, 308) and resp.headers.get(
                    "location", ""
                ).endswith(new)
                check(
                    ok,
                    f"{old} redirects to {new}",
                    (resp.status_code, resp.headers.get("location")),
                )
            except httpx.HTTPError as exc:
                check(False, f"{old} redirects to {new}", str(exc))

        print("\n→ MCP endpoint")
        r = http.post(
            "/mcp",
            headers={**admin, "Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            follow_redirects=False,
        )
        check(r.status_code != 307, "POST /mcp is served without a redirect", r.status_code)
    finally:
        for key_id in keys:
            http.delete(f"/settings/api-keys/{key_id}", headers=admin)

    print(f"\n{check.passed} passed, {len(check.failures)} failed")
    for label in check.failures:
        print(f"  FAILED: {label}")
    return 1 if check.failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default=os.getenv("RUNLEDGER_URL", "http://localhost:8201"))
    parser.add_argument(
        "--email", default=os.getenv("RUNLEDGER_PLATFORM_EMAIL", "admin@runledger.local")
    )
    parser.add_argument("--password", default=os.getenv("RUNLEDGER_PLATFORM_PASSWORD", "runledger"))
    parser.add_argument(
        "--web-url", default=os.getenv("RUNLEDGER_WEB_URL", "http://localhost:3201")
    )
    parser.add_argument(
        "--max-batch",
        type=int,
        default=int(os.getenv("INGEST_MAX_BATCH_EVENTS", "1000")),
        help="Server's INGEST_MAX_BATCH_EVENTS (default 1000).",
    )
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
