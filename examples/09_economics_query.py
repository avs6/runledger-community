"""
Example 9 — Unit economics + change impact queries.

What this demonstrates
──────────────────────
- Per-run cost breakdown by span type (llm/tool/retrieval) and by model
- Top workflows ranked by average cost
- Version-to-version cost/token/latency comparison
- Cost regression detection (workflows where cost jumped >20% vs prior week)
- Creating and listing team annotations anchored to a date or version

All calls go directly to the RunLedger HTTP API — no SDK needed for analytics.

Prerequisites
─────────────
A running RunLedger stack with some instrumented runs:

    docker compose -f infra/docker-compose.yml up -d

Then send some runs with deployment_version tags:

    # Tag some runs as v1
    python -c "
    import os; from runledger_sdk import RunLedger; rl = RunLedger()
    rl.instrument()
    import openai; client = openai.OpenAI()
    for _ in range(3):
        with rl.context(deployment_version='v1', feature_tag='chat'):
            client.chat.completions.create(model='gpt-4o-mini',
                messages=[{'role':'user','content':'Hello'}], max_tokens=5)
    rl.shutdown()
    "

    # Tag some runs as v2
    python -c "
    import os; from runledger_sdk import RunLedger; rl = RunLedger()
    rl.instrument()
    import openai; client = openai.OpenAI()
    for _ in range(3):
        with rl.context(deployment_version='v2', feature_tag='chat'):
            client.chat.completions.create(model='gpt-4o',
                messages=[{'role':'user','content':'Hello, can you help?'}], max_tokens=20)
    rl.shutdown()
    "

Install
───────
    pip install httpx python-dotenv

Run it
──────
    # Copy .env.example → .env and fill in your values, then:
    python 09_economics_query.py

    # With specific run ID and versions
    python 09_economics_query.py --run-id <run_uuid> --baseline v1 --comparison v2

Key .env variables used here:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8000  (local Docker stack)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, date, datetime, timedelta

import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print(
        "Error: RUNLEDGER_API_KEY is not set.\n"
        "Copy .env.example → .env and set RUNLEDGER_API_KEY.",
        file=sys.stderr,
    )
    sys.exit(1)


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}"}


def _get(path: str, params: dict | None = None) -> dict:
    resp = httpx.get(f"{BASE_URL}{path}", params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()  # type: ignore[return-value]


def _post(path: str, body: dict) -> dict:
    resp = httpx.post(f"{BASE_URL}{path}", json=body, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()  # type: ignore[return-value]


# ── Formatting ─────────────────────────────────────────────────────────────────

def _fmt_usd(value: str | float | None) -> str:
    if value is None:
        return "—"
    n = float(value)
    if n == 0:
        return "$0.00"
    if n >= 1:
        return f"${n:.4f}"
    if n >= 0.0001:
        return f"${n:.6f}"
    return f"${n:.8f}"


def _fmt_pct(value: str | float | None, *, sign: bool = True) -> str:
    if value is None:
        return "—"
    n = float(value)
    prefix = ("+" if n > 0 else "") if sign else ""
    colour = "\033[91m" if n > 0 else ("\033[92m" if n < 0 else "")
    reset = "\033[0m"
    return f"{colour}{prefix}{n:.2f}%{reset}"


def _hr(width: int = 64) -> None:
    print("─" * width)


# ── API helpers ────────────────────────────────────────────────────────────────

def get_recent_run_id() -> str | None:
    """Return the most recent run_id from the workspace, or None."""
    try:
        data = _get("/runs", {"limit": 1})
        items = data.get("items", [])
        return items[0]["id"] if items else None
    except httpx.HTTPError:
        return None


def get_run_economics(run_id: str) -> dict:
    return _get(f"/analytics/economics/{run_id}")


def get_top_workflows(metric: str = "cost", limit: int = 10) -> dict:
    return _get("/analytics/workflows/top", {"metric": metric, "limit": limit})


def get_version_compare(baseline: str, comparison: str) -> dict:
    return _get(
        "/analytics/compare",
        {"baseline_version": baseline, "comparison_version": comparison},
    )


def get_regressions() -> dict:
    return _get("/analytics/regressions")


def create_annotation(note: str, annotation_date: str, version: str | None = None) -> dict:
    body: dict = {"note": note, "annotation_date": annotation_date}
    if version:
        body["version"] = version
    return _post("/analytics/annotations", body)


def list_annotations() -> dict:
    return _get("/analytics/annotations")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="RunLedger economics + change impact demo")
    parser.add_argument("--run-id", dest="run_id", default=None, help="Run UUID to inspect")
    parser.add_argument("--baseline", default="v1", help="Baseline deployment version")
    parser.add_argument("--comparison", default="v2", help="Comparison deployment version")
    parser.add_argument("--skip-annotation", action="store_true", help="Skip annotation creation")
    args = parser.parse_args()

    print(f"\nRunLedger Economics + Change Impact")
    print(f"API: {BASE_URL}\n")

    # ── Section 1: Per-run economics ──────────────────────────────────────────
    _hr()
    print("  SECTION 1 — Per-run economics (cost by span type + model)")
    _hr()

    run_id = args.run_id or get_recent_run_id()
    if not run_id:
        print("  No runs found. Instrument some agent calls first (see file docstring).")
    else:
        print(f"  Run: {run_id}")
        try:
            econ = get_run_economics(run_id)
            print(f"  Total cost : {_fmt_usd(econ['total_cost_usd'])}")
            print(f"  Retry cost : {_fmt_usd(econ['retry_cost'])}")

            print()
            if econ["cost_by_span_type"]:
                print(f"  {'Span type':<14} {'Cost':>12}")
                print(f"  {'─'*14} {'─'*12}")
                for s in econ["cost_by_span_type"]:
                    print(f"  {s['span_type']:<14} {_fmt_usd(s['cost_usd']):>12}")
            else:
                print("  (no span cost data — cost enrichment worker may still be processing)")

            print()
            if econ["cost_by_model"]:
                print(f"  {'Model':<30} {'Provider':<10} {'Calls':>6} {'Cost':>12}")
                print(f"  {'─'*30} {'─'*10} {'─'*6} {'─'*12}")
                for m in econ["cost_by_model"]:
                    print(
                        f"  {m['model']:<30} {m['provider']:<10} "
                        f"{m['call_count']:>6} {_fmt_usd(m['cost_usd']):>12}"
                    )
            else:
                print("  (no model cost data yet)")

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                print(f"  Run {run_id} not found in this workspace.")
            else:
                raise

    print()
    _hr()
    print("  SECTION 2 — Top workflows by cost")
    _hr()

    workflows = get_top_workflows(metric="cost", limit=5)
    items = workflows.get("items", [])
    if not items:
        print("  No workflow data yet. Run some agents with feature_tag set.")
    else:
        print(f"  {'Feature tag':<20} {'Runs':>6} {'Avg cost':>12} {'p95 cost':>12} {'Calls':>7}")
        print(f"  {'─'*20} {'─'*6} {'─'*12} {'─'*12} {'─'*7}")
        for w in items:
            tag = (w["feature_tag"] or "—")[:20]
            print(
                f"  {tag:<20} {w['run_count']:>6} "
                f"{_fmt_usd(w['avg_cost_usd']):>12} "
                f"{_fmt_usd(w['p95_cost_usd']):>12} "
                f"{w['call_count']:>7}"
            )

    print()
    _hr()
    print(f"  SECTION 3 — Version compare: {args.baseline} vs {args.comparison}")
    _hr()

    try:
        cmp = get_version_compare(args.baseline, args.comparison)
        base = cmp["baseline"]
        comp = cmp["comparison"]

        print(f"  {'Metric':<24} {'Baseline (' + args.baseline + ')':>18} {'Compare (' + args.comparison + ')':>18} {'Delta':>10}")
        print(f"  {'─'*24} {'─'*18} {'─'*18} {'─'*10}")
        print(
            f"  {'Avg cost / run':<24} "
            f"{_fmt_usd(base['avg_cost_usd']):>18} "
            f"{_fmt_usd(comp['avg_cost_usd']):>18} "
            f"{_fmt_pct(cmp['cost_delta_pct']):>10}"
        )
        print(
            f"  {'Avg input tokens':<24} "
            f"{float(base['avg_input_tokens']):>18.0f} "
            f"{float(comp['avg_input_tokens']):>18.0f} "
            f"{_fmt_pct(cmp['token_delta_pct']):>10}"
        )
        if base["avg_latency_ms"] is not None:
            print(
                f"  {'Avg latency (ms)':<24} "
                f"{float(base['avg_latency_ms']):>18.0f} "
                f"{float(comp['avg_latency_ms'] or 0):>18.0f} "
                f"{_fmt_pct(cmp['latency_delta_pct']):>10}"
            )
        print(
            f"  {'Run count':<24} "
            f"{base['run_count']:>18} "
            f"{comp['run_count']:>18}"
        )

        if cmp["by_span_type"]:
            print()
            print(f"  Cost delta by span type:")
            print(f"  {'Span type':<14} {'Baseline':>12} {'Comparison':>12} {'Δ%':>10}")
            print(f"  {'─'*14} {'─'*12} {'─'*12} {'─'*10}")
            for row in cmp["by_span_type"]:
                print(
                    f"  {row['span_type']:<14} "
                    f"{_fmt_usd(row['baseline_cost']):>12} "
                    f"{_fmt_usd(row['comparison_cost']):>12} "
                    f"{_fmt_pct(row['delta_pct']):>10}"
                )

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 422:
            print(
                f"  Versions '{args.baseline}' and/or '{args.comparison}' not found.\n"
                f"  Tag runs with deployment_version in rl.context() then retry."
            )
        else:
            raise

    print()
    _hr()
    print("  SECTION 4 — Cost regressions (last 7 days vs prior 7 days)")
    _hr()

    reg = get_regressions()
    items_reg = reg.get("items", [])
    if not items_reg:
        print("  No cost regressions detected (>20% increase with ≥3 runs required).")
    else:
        print(f"  {'Feature tag':<20} {'Current avg':>12} {'Prior avg':>12} {'Change %':>10} {'Runs':>6}")
        print(f"  {'─'*20} {'─'*12} {'─'*12} {'─'*10} {'─'*6}")
        for item in items_reg:
            tag = (item["feature_tag"] or "—")[:20]
            print(
                f"  {tag:<20} "
                f"{_fmt_usd(item['current_avg_cost']):>12} "
                f"{_fmt_usd(item['prior_avg_cost']):>12} "
                f"{_fmt_pct(item['change_pct']):>10} "
                f"{item['run_count']:>6}"
            )

    print()
    _hr()
    print("  SECTION 5 — Annotations")
    _hr()

    if not args.skip_annotation:
        today = date.today().isoformat()
        note = f"economics example run — baseline={args.baseline} vs comparison={args.comparison}"
        annotation = create_annotation(note=note, annotation_date=today, version=args.comparison)
        print(f"  Created annotation : {annotation['id']}")
        print(f"  Date               : {annotation['annotation_date']}")
        print(f"  Version            : {annotation.get('version') or '—'}")
        print(f"  Note               : {annotation['note']}")
        print()

    annotations = list_annotations()
    all_items = annotations.get("items", [])
    if not all_items:
        print("  No annotations yet.")
    else:
        print(f"  {'Date':<12} {'Version':<10} Note")
        print(f"  {'─'*12} {'─'*10} {'─'*40}")
        for a in all_items[:10]:
            ver = (a.get("version") or "—")[:10]
            note_text = a["note"][:60]
            print(f"  {a['annotation_date']:<12} {ver:<10} {note_text}")
        if len(all_items) > 10:
            print(f"  ... and {len(all_items) - 10} more")

    print()
    print(
        "Tip: open http://localhost:3000/analytics/economics to see the full\n"
        "     economics dashboard with version comparison and regression table."
    )
    print()


if __name__ == "__main__":
    main()
