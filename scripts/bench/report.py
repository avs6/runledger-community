#!/usr/bin/env python3
"""
Gateway benchmark report.

Reads the gateway's benchmark comparison endpoint and prints per-alias overhead,
throughput, and provider-comparison metrics.

Example:
    python scripts/bench/report.py \
        --base-url http://localhost:8201 \
        --api-key rl_... \
        --days 7
"""

from __future__ import annotations

import argparse

import httpx


def fetch(base_url: str, api_key: str, days: int, alias: str | None) -> list[dict]:
    url = f"{base_url.rstrip('/')}/gateway/benchmarks/compare"
    headers = {"Authorization": f"Bearer {api_key}"}
    params: dict[str, str | int] = {"days": days}
    if alias:
        params["alias"] = alias
    with httpx.Client(timeout=60.0) as client:
        response = client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("items", [])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8201")
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--alias", default=None)
    args = ap.parse_args()

    items = fetch(args.base_url, args.api_key, args.days, args.alias)
    if not items:
        print("No benchmark comparison data found.")
        return

    print(f"\nGateway benchmark comparison - last {args.days} day(s)")
    print("-" * 120)
    header = (
        f"{'alias':<22} {'req':>6} {'rpm':>9} {'p50':>8} {'p95':>8} "
        f"{'p99':>8} {'provider':>10} {'end2end':>10} {'ovh%':>8}"
    )
    print(header)
    print("-" * len(header))
    for item in items:
        overhead_pct = item.get("overhead_vs_provider_pct")
        print(
            f"{item['alias']:<22} "
            f"{item['request_count']:>6} "
            f"{float(item.get('throughput_rpm') or 0):>9.2f} "
            f"{float(item.get('p50_gateway_overhead_ms') or 0):>8.1f} "
            f"{float(item.get('p95_gateway_overhead_ms') or 0):>8.1f} "
            f"{float(item.get('p99_gateway_overhead_ms') or 0):>8.1f} "
            f"{float(item.get('avg_provider_latency_ms') or 0):>10.1f} "
            f"{float(item.get('avg_end_to_end_latency_ms') or 0):>10.1f} "
            f"{(float(overhead_pct) * 100 if overhead_pct is not None else 0):>7.1f}%"
        )


if __name__ == "__main__":
    main()
