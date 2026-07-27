#!/usr/bin/env python3
"""
Phase 0 benchmark report.

Pulls recent gateway requests for an alias from RunLedger and renders the Baseline-vs-Optimized
table (input/cached/output tokens, agent calls, cache-hit rate, latency). Cost-per-task is a
TODO pending the analytics/ledger endpoint wiring.

Usage:
    python scripts/bench/report.py \
        --base-url http://localhost:8000 --api-key $RUNLEDGER_API_KEY \
        --alias gpt-frontier --since 2026-07-27T00:00:00+00:00 --limit 200
"""

from __future__ import annotations

import argparse
from datetime import datetime

import httpx


def fetch(base_url: str, api_key: str, alias: str, limit: int) -> list[dict]:
    url = f"{base_url.rstrip('/')}/gateway/requests"
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=60.0) as client:
        r = client.get(url, headers=headers, params={"alias": alias, "limit": limit})
        r.raise_for_status()
        return r.json().get("items", [])


def summarize(items: list[dict], since: datetime | None) -> dict:
    n = cache_hits = in_tok = out_tok = lat_sum = lat_n = 0
    for it in items:
        if since is not None:
            created = it.get("created_at")
            if created and datetime.fromisoformat(created) < since:
                continue
        n += 1
        cache_hits += 1 if it.get("cache_hit") else 0
        in_tok += it.get("input_tokens") or 0
        out_tok += it.get("output_tokens") or 0
        if it.get("latency_ms") is not None:
            lat_sum += it["latency_ms"]
            lat_n += 1
    return {
        "requests": n,
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / n, 3) if n else 0.0,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "avg_latency_ms": round(lat_sum / lat_n, 1) if lat_n else None,
        "cost_usd": "TODO (analytics endpoint)",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--alias", required=True)
    ap.add_argument("--since", default=None, help="ISO timestamp; ignore requests before it")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    since = datetime.fromisoformat(args.since) if args.since else None
    items = fetch(args.base_url, args.api_key, args.alias, args.limit)
    s = summarize(items, since)

    print(f"\nBenchmark summary · alias={args.alias}")
    print("-" * 48)
    for k, v in s.items():
        print(f"{k:>18}: {v}")


if __name__ == "__main__":
    main()
