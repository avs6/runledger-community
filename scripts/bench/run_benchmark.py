#!/usr/bin/env python3
"""
Phase 0 benchmark driver.

Runs a named workload N times through the RunLedger gateway under a chosen optimization
profile (which maps to a gateway model alias), and prints a run manifest that report.py
uses to scope its aggregation.

Baseline usage (no optimization):
    python scripts/bench/run_benchmark.py \
        --base-url http://localhost:8000 --api-key $RUNLEDGER_API_KEY \
        --alias gpt-frontier --profile baseline --repeat 5

Later, re-run against a semantic-cache-enabled alias/flag to get the Optimized column.

Note: this drives single-shot completions as a stand-in. Swap `WORKLOADS` for scripted
Codex CLI / Claude Code agent runs to exercise real multi-call agentic token usage.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime

import httpx

# Minimal placeholder workloads — replace with the PDF's harness tasks / real agent runs.
WORKLOADS: dict[str, list[dict[str, str]]] = {
    "smoke": [{"role": "user", "content": "Summarize what an AI FinOps control plane does in 3 bullets."}],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--alias", required=True, help="Gateway model alias / route to target")
    ap.add_argument("--profile", default="baseline", help="Label for this run (baseline|semantic_cache|...)")
    ap.add_argument("--workload", default="smoke", choices=list(WORKLOADS))
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--cache", action="store_true", help="Set body.cache=true (exact prompt cache)")
    ap.add_argument("--semantic-cache", action="store_true", help="Set body.semantic_cache=true")
    ap.add_argument("--context-compiler", action="store_true", help="Set body.context_compiler=true")
    args = ap.parse_args()

    url = f"{args.base_url.rstrip('/')}/gateway/chat/completions"
    headers = {"Authorization": f"Bearer {args.api_key}", "Content-Type": "application/json"}
    messages = WORKLOADS[args.workload]

    started = datetime.now(UTC).isoformat()
    t0 = time.monotonic()
    ok = 0
    with httpx.Client(timeout=120.0) as client:
        for i in range(args.repeat):
            body = {
                "model": args.alias,
                "messages": messages,
                "cache": args.cache,
                "semantic_cache": args.semantic_cache,
                "context_compiler": args.context_compiler,
            }
            r = client.post(url, headers=headers, json=body)
            ok += 1 if r.status_code == 200 else 0
            print(f"  run {i + 1}/{args.repeat} → {r.status_code}")
    elapsed = time.monotonic() - t0
    ended = datetime.now(UTC).isoformat()

    manifest = {
        "profile": args.profile,
        "alias": args.alias,
        "workload": args.workload,
        "repeat": args.repeat,
        "cache": args.cache,
        "semantic_cache": args.semantic_cache,
        "context_compiler": args.context_compiler,
        "ok": ok,
        "started": started,
        "ended": ended,
        "wall_seconds": round(elapsed, 2),
    }
    print("\nMANIFEST " + json.dumps(manifest))


if __name__ == "__main__":
    main()
