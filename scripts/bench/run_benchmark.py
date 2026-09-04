#!/usr/bin/env python3
"""
Gateway benchmark driver.

Drives a workload through the RunLedger gateway, optionally compares it to a direct
provider endpoint, and prints a compact summary plus a JSON manifest.

Example:
    python scripts/bench/run_benchmark.py \
        --base-url http://localhost:8210 \
        --api-key rl_... \
        --alias chat \
        --repeat 30 \
        --concurrency 5 \
        --provider-url https://api.openai.com/v1/chat/completions \
        --provider-auth-header Authorization \
        --provider-auth-value "Bearer sk-..." \
        --provider-model gpt-4o-mini
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

WORKLOADS: dict[str, list[dict[str, str]]] = {
    "smoke": [{"role": "user", "content": "Summarize what an AI FinOps control plane does in 3 bullets."}],
    "routing": [{"role": "user", "content": "Explain how fallback routing and latency-based selection work in 5 bullets."}],
    "passthrough": [{"role": "user", "content": "Return a short checklist for testing a gateway pass-through endpoint."}],
}


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return round(ordered[index], 2)


def _summarize(latencies_ms: list[float], *, ok: int, started: str, ended: str) -> dict[str, Any]:
    wall_seconds = (
        datetime.fromisoformat(ended).timestamp() - datetime.fromisoformat(started).timestamp()
    )
    throughput_rps = round(ok / wall_seconds, 3) if wall_seconds > 0 else 0.0
    return {
        "ok": ok,
        "request_count": len(latencies_ms),
        "wall_seconds": round(wall_seconds, 2),
        "throughput_rps": throughput_rps,
        "throughput_rpm": round(throughput_rps * 60, 3),
        "p50_latency_ms": _percentile(latencies_ms, 0.50),
        "p95_latency_ms": _percentile(latencies_ms, 0.95),
        "p99_latency_ms": _percentile(latencies_ms, 0.99),
        "avg_latency_ms": round(statistics.fmean(latencies_ms), 2) if latencies_ms else None,
    }


async def _run_requests(
    *,
    url: str,
    headers: dict[str, str],
    body_factory,
    repeat: int,
    concurrency: int,
    timeout_seconds: float,
) -> tuple[list[float], int]:
    latencies_ms: list[float] = []
    ok = 0
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def once(index: int) -> tuple[float, bool]:
        del index
        async with semaphore:
            started = time.perf_counter()
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=body_factory())
            latency_ms = (time.perf_counter() - started) * 1000
            return latency_ms, response.status_code < 400

    results = await asyncio.gather(*(once(i) for i in range(repeat)))
    for latency_ms, success in results:
        latencies_ms.append(round(latency_ms, 2))
        ok += 1 if success else 0
    return latencies_ms, ok


async def main_async() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8210")
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--alias", required=True, help="Gateway alias to target")
    ap.add_argument("--profile", default="baseline")
    ap.add_argument("--workload", default="smoke", choices=list(WORKLOADS))
    ap.add_argument("--repeat", type=int, default=10)
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--cache", action="store_true")
    ap.add_argument("--semantic-cache", action="store_true")
    ap.add_argument("--context-compiler", action="store_true")
    ap.add_argument("--timeout-seconds", type=float, default=120.0)
    ap.add_argument("--provider-url", default=None, help="Optional direct provider comparison URL")
    ap.add_argument("--provider-auth-header", default="Authorization")
    ap.add_argument("--provider-auth-value", default=None)
    ap.add_argument("--provider-model", default=None, help="Provider model name for direct comparison")
    ap.add_argument("--out", default=None, help="Optional path to write JSON manifest")
    args = ap.parse_args()

    gateway_url = f"{args.base_url.rstrip('/')}/gateway/chat/completions"
    gateway_headers = {"Authorization": f"Bearer {args.api_key}", "Content-Type": "application/json"}
    messages = WORKLOADS[args.workload]

    def gateway_body() -> dict[str, Any]:
        return {
            "model": args.alias,
            "messages": messages,
            "cache": args.cache,
            "semantic_cache": args.semantic_cache,
            "context_compiler": args.context_compiler,
        }

    started = datetime.now(UTC).isoformat()
    gateway_latencies, gateway_ok = await _run_requests(
        url=gateway_url,
        headers=gateway_headers,
        body_factory=gateway_body,
        repeat=args.repeat,
        concurrency=args.concurrency,
        timeout_seconds=args.timeout_seconds,
    )
    ended = datetime.now(UTC).isoformat()

    manifest: dict[str, Any] = {
        "profile": args.profile,
        "alias": args.alias,
        "workload": args.workload,
        "repeat": args.repeat,
        "concurrency": args.concurrency,
        "cache": args.cache,
        "semantic_cache": args.semantic_cache,
        "context_compiler": args.context_compiler,
        "started": started,
        "ended": ended,
        "gateway": _summarize(gateway_latencies, ok=gateway_ok, started=started, ended=ended),
    }

    if args.provider_url and args.provider_model:
        if not args.provider_auth_value:
            raise SystemExit("--provider-auth-value is required when --provider-url is set")
        provider_headers = {
            args.provider_auth_header: args.provider_auth_value,
            "Content-Type": "application/json",
        }

        def provider_body() -> dict[str, Any]:
            return {"model": args.provider_model, "messages": messages}

        provider_started = datetime.now(UTC).isoformat()
        provider_latencies, provider_ok = await _run_requests(
            url=args.provider_url,
            headers=provider_headers,
            body_factory=provider_body,
            repeat=args.repeat,
            concurrency=args.concurrency,
            timeout_seconds=args.timeout_seconds,
        )
        provider_ended = datetime.now(UTC).isoformat()
        provider_summary = _summarize(
            provider_latencies,
            ok=provider_ok,
            started=provider_started,
            ended=provider_ended,
        )
        manifest["provider"] = provider_summary
        gateway_p95 = manifest["gateway"].get("p95_latency_ms")
        provider_p95 = provider_summary.get("p95_latency_ms")
        if gateway_p95 is not None and provider_p95 is not None and provider_p95 > 0:
            manifest["gateway_vs_provider"] = {
                "p95_overhead_ms": round(gateway_p95 - provider_p95, 2),
                "p95_overhead_pct": round((gateway_p95 - provider_p95) / provider_p95, 4),
            }

    print("\nGateway benchmark summary")
    print("-" * 60)
    for section in ("gateway", "provider", "gateway_vs_provider"):
        if section not in manifest:
            continue
        print(section)
        for key, value in manifest[section].items():
            print(f"  {key:>20}: {value}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nWrote manifest to {out_path}")

    print("\nMANIFEST " + json.dumps(manifest))


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
