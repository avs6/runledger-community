"""
Example 7 — Analytics API query.

What this demonstrates
──────────────────────
- Querying all analytics endpoints (summary, spend-over-time, spend-by-model,
  spend-by-feature, spend-by-user, user profile)
- Period-over-period delta from /analytics/summary
- Printing spend breakdowns as formatted tables

Prerequisites
─────────────
A running RunLedger stack with some data:

    docker compose -f infra/docker-compose.yml up -d

Then run a few example agents first so there's data to query:

    export OPENAI_API_KEY=sk-...
    python examples/01_openai_basic.py
    python examples/02_openai_multi_turn.py

Install the SDK (not on PyPI yet — install from source)
────────────────────────────────────────────────────────
Option A — local path (recommended if you have the repo):
    pip install -e "/path/to/runledger/packages/sdk"

Option B — directly from GitHub (no clone needed):
    pip install "runledger-sdk @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"

Run it
──────
    export RUNLEDGER_API_KEY=rl_dev_...   # from docker compose logs api
    python examples/07_analytics_query.py

    # Custom time window (ISO-8601)
    python examples/07_analytics_query.py --from 2026-01-01T00:00:00Z --to 2026-01-31T23:59:59Z
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = os.environ.get("RUNLEDGER_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print(
        "Error: RUNLEDGER_API_KEY is not set.\n"
        "Run: docker compose -f infra/docker-compose.yml logs api | grep 'API Key'",
        file=sys.stderr,
    )
    sys.exit(1)


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get(path: str, params: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    resp = httpx.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()  # type: ignore[return-value]


# ── Formatting ────────────────────────────────────────────────────────────────

def _fmt_usd(value: str | Decimal) -> str:
    n = float(value)
    if n >= 1:
        return f"${n:.2f}"
    if n >= 0.001:
        return f"${n:.4f}"
    return f"${n:.6f}"


def _fmt_delta(pct: str | None) -> str:
    if pct is None:
        return "n/a (no prior data)"
    n = float(pct)
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:.1f}%"


def _hr(width: int = 60) -> None:
    print("─" * width)


# ── Query functions ───────────────────────────────────────────────────────────

def print_summary(params: dict) -> None:
    data = _get("/analytics/summary", params)
    _hr()
    print("  SUMMARY")
    _hr()
    print(f"  Total spend (current period) : {_fmt_usd(data['total_cost_usd'])}")
    print(f"  Prior period spend           : {_fmt_usd(data['prev_cost_usd'])}")
    print(f"  Period-over-period delta     : {_fmt_delta(data['cost_delta_pct'])}")
    print(f"  Agent runs                   : {data['run_count']:,}")
    print(f"  Provider calls               : {data['call_count']:,}")
    print(f"  Input tokens                 : {data['total_input_tokens']:,}")
    print(f"  Output tokens                : {data['total_output_tokens']:,}")
    _hr()
    print()


def print_spend_over_time(params: dict, granularity: str = "daily") -> None:
    data = _get("/analytics/spend-over-time", {**params, "granularity": granularity})
    points = data["points"]
    _hr()
    print(f"  SPEND OVER TIME  ({granularity})")
    _hr()
    if not points:
        print("  (no data)")
    else:
        for p in points:
            period = p["period"][:10] if granularity == "daily" else p["period"][:16]
            bar_len = max(1, int(float(p["cost_usd"]) * 400))
            bar = "█" * min(bar_len, 40)
            print(f"  {period}  {bar}  {_fmt_usd(p['cost_usd'])}")
    _hr()
    print()


def print_spend_by_model(params: dict) -> None:
    data = _get("/analytics/spend-by-model", params)
    items = data["items"]
    _hr()
    print("  SPEND BY MODEL")
    _hr()
    if not items:
        print("  (no data)")
    else:
        for m in items:
            tokens = m["input_tokens"] + m["output_tokens"]
            print(
                f"  {m['provider']}/{m['model']:<30} "
                f"{_fmt_usd(m['cost_usd']):<12}  "
                f"{tokens:>10,} tokens  "
                f"{m['call_count']:>5} calls"
            )
    _hr()
    print()


def print_spend_by_feature(params: dict) -> None:
    data = _get("/analytics/spend-by-feature", params)
    items = data["items"]
    _hr()
    print("  SPEND BY FEATURE TAG")
    _hr()
    if not items:
        print("  (no data)")
    else:
        total = sum(float(i["cost_usd"]) for i in items) or 1
        for f in items:
            tag = f["feature_tag"] or "(untagged)"
            pct = float(f["cost_usd"]) / total * 100
            bar = "█" * max(1, int(pct / 2))
            print(
                f"  {tag:<28}  {_fmt_usd(f['cost_usd']):<12}  "
                f"{pct:5.1f}%  {bar}"
            )
    _hr()
    print()


def print_top_spenders(params: dict, limit: int = 10) -> None:
    data = _get("/analytics/spend-by-user", {**params, "limit": limit})
    items = data["items"]
    _hr()
    print("  TOP SPENDERS")
    _hr()
    if not items:
        print("  (no data)")
    else:
        header = f"  {'User':<30} {'Spend':>10}  {'Runs':>6}  {'Avg/run':>10}  Last active"
        print(header)
        print("  " + "-" * 72)
        for u in items:
            last = u["last_active"][:10] if u["last_active"] else "—"
            print(
                f"  {u['end_user_id']:<30} "
                f"{_fmt_usd(u['cost_usd']):>10}  "
                f"{u['run_count']:>6,}  "
                f"{_fmt_usd(u['avg_cost_per_run']):>10}  "
                f"{last}"
            )
    _hr()
    print()


def print_user_profile(user_id: str, params: dict) -> None:
    try:
        data = _get(f"/analytics/users/{user_id}", params)
    except httpx.HTTPStatusError as e:
        print(f"  Error fetching profile for {user_id!r}: {e.response.status_code}")
        return
    _hr()
    print(f"  USER PROFILE — {data['end_user_id']}")
    _hr()
    print(f"  Total spend     : {_fmt_usd(data['cost_usd'])}")
    print(f"  Runs            : {data['run_count']:,}")
    print(f"  Calls           : {data['call_count']:,}")
    print(f"  Avg cost / run  : {_fmt_usd(data['avg_cost_per_run'])}")
    print(f"  Last active     : {data['last_active'] or '—'}")
    if data["models_used"]:
        print("\n  Models used:")
        for m in data["models_used"]:
            print(f"    {m['provider']}/{m['model']:<28}  {_fmt_usd(m['cost_usd'])}")
    if data["features_used"]:
        print("\n  Features used:")
        for f in data["features_used"]:
            tag = f["feature_tag"] or "(untagged)"
            print(f"    {tag:<30}  {_fmt_usd(f['cost_usd'])}")
    _hr()
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Query the RunLedger analytics API")
    parser.add_argument(
        "--from",
        dest="from_dt",
        default=None,
        help="Start datetime ISO-8601 (default: 7 days ago)",
    )
    parser.add_argument(
        "--to",
        dest="to_dt",
        default=None,
        help="End datetime ISO-8601 (default: now)",
    )
    parser.add_argument(
        "--user",
        dest="user_id",
        default=None,
        help="Print a detailed profile for this end_user_id",
    )
    args = parser.parse_args()

    now = datetime.now(UTC)
    params: dict = {
        "from": args.from_dt or (now - timedelta(days=7)).isoformat(),
        "to": args.to_dt or now.isoformat(),
    }

    print(f"\nRunLedger Analytics — {params['from'][:10]} → {params['to'][:10]}")
    print(f"API: {BASE_URL}\n")

    print_summary(params)
    print_spend_over_time(params)
    print_spend_by_model(params)
    print_spend_by_feature(params)
    print_top_spenders(params)

    if args.user_id:
        print_user_profile(args.user_id, params)


if __name__ == "__main__":
    main()
