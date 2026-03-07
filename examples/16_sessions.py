"""
Example 16 — Sessions & Payload Viewer

Demonstrates:
  1. List sessions — multi-turn runs grouped by session_id
  2. GET /sessions/{id} — session detail with ordered turn list
  3. GET /sessions/{id}/cost-over-turns — cumulative cost chart data
  4. GET /runs/{id} — run detail showing captured input/output payload
     (payload fields are non-null only when capture policy is SAMPLED or FULL)

Install
───────
    pip install httpx python-dotenv

Run it
──────
    # Copy .env.example → .env, then:
    python 16_sessions.py

Key .env variables:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8000  (default)

Notes
─────
* Sessions are created automatically when you pass session_id= to rl.context().
  Example 02 (02_openai_multi_turn.py) shows how to generate them.
* To see captured payloads, first set the capture policy to SAMPLED or FULL
  via PUT /privacy/capture-policy (see example 11 or the /ledger page).
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("ERROR: RUNLEDGER_API_KEY env var is required", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def sep(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ── Step 1 — List sessions ─────────────────────────────────────────────────────

sep("Step 1 — GET /sessions (list grouped sessions)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get("/sessions", params={"limit": 10})

if resp.status_code == 200:
    data = resp.json()
    sessions = data.get("items", [])
    total = data.get("total", len(sessions))
    print(f"  {total} session(s) total, showing {len(sessions)}:")
    for s in sessions[:5]:
        cost = f"${float(s['total_cost_usd']):.4f}" if s["total_cost_usd"] else "$—"
        user = s["end_user_id"] or "—"
        print(
            f"    session={s['session_id'][:12]}…  user={user}"
            f"  turns={s['run_count']}  cost={cost}"
        )
    if not sessions:
        print("  No sessions yet. Run 02_openai_multi_turn.py to generate some.")
    first_session_id = sessions[0]["session_id"] if sessions else None
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")
    first_session_id = None


# ── Step 2 — Session detail ────────────────────────────────────────────────────

sep("Step 2 — GET /sessions/{id} (turn-ordered detail)")

if first_session_id:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        resp = client.get(f"/sessions/{first_session_id}")

    if resp.status_code == 200:
        detail = resp.json()
        print(f"  Session:  {detail['session_id']}")
        print(f"  User:     {detail['end_user_id'] or '—'}")
        print(f"  Turns:    {detail['run_count']}")
        total_cost = detail["total_cost_usd"]
        print(f"  Cost:     ${float(total_cost):.6f}" if total_cost else "  Cost:     $—")
        print()
        for run in detail["runs"]:
            cost = f"${float(run['total_cost_usd']):.6f}" if run["total_cost_usd"] else "$—"
            dur = f"{run['duration_ms']}ms" if run["duration_ms"] else "—"
            print(
                f"    Turn {run['turn_number']:>2}  [{run['status']:>9}]"
                f"  cost={cost}  dur={dur}  id={str(run['id'])[:8]}…"
            )
    else:
        print(f"  ERROR {resp.status_code}: {resp.text}")
else:
    print("  (Skipped — no sessions found in Step 1)")


# ── Step 3 — Cost over turns ───────────────────────────────────────────────────

sep("Step 3 — GET /sessions/{id}/cost-over-turns (chart data)")

if first_session_id:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        resp = client.get(f"/sessions/{first_session_id}/cost-over-turns")

    if resp.status_code == 200:
        chart = resp.json()
        print(f"  Session: {chart['session_id']}")
        print(f"  {'Turn':>4}  {'Per-turn cost':>15}  {'Cumulative cost':>16}")
        for t in chart["turns"]:
            per = f"${float(t['cost_usd']):.6f}" if t["cost_usd"] else "$—"
            cum = f"${float(t['cumulative_cost_usd']):.6f}"
            print(f"  {t['turn_number']:>4}  {per:>15}  {cum:>16}")
    else:
        print(f"  ERROR {resp.status_code}: {resp.text}")
else:
    print("  (Skipped — no sessions found in Step 1)")


# ── Step 4 — Run detail with payload ──────────────────────────────────────────

sep("Step 4 — GET /runs/{id} — payload fields (requires SAMPLED or FULL capture)")

# Use the first run from the first session (if available)
first_run_id: str | None = None
if first_session_id:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        r = client.get(f"/sessions/{first_session_id}")
    if r.status_code == 200:
        runs = r.json().get("runs", [])
        if runs:
            first_run_id = str(runs[0]["id"])

if first_run_id:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        resp = client.get(f"/runs/{first_run_id}")

    if resp.status_code == 200:
        run = resp.json()
        input_payload = run.get("input_payload")
        output_payload = run.get("output_payload")
        span_payloads = run.get("span_payloads") or {}

        if input_payload:
            print(f"  Input payload ({len(input_payload)} message(s)):")
            for msg in input_payload[:3]:
                content = str(msg.get("content", ""))[:80]
                print(f"    [{msg.get('role', '?'):>9}]  {content!r}")
            if output_payload:
                out = str(output_payload)[:100]
                print(f"\n  Output payload: {out!r}")
            print(f"\n  Span payloads captured for {len(span_payloads)} span(s)")
        else:
            print(
                "  No payload captured for this run.\n"
                "  To enable: PUT /privacy/capture-policy\n"
                '  body: {"privacy_mode": "SAMPLED", "sampled_rate": "1.0"}'
            )
    else:
        print(f"  ERROR {resp.status_code}: {resp.text}")
else:
    print("  (Skipped — no runs found)")


print("\n✓ Example 16 complete.\n")
