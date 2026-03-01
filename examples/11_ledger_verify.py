#!/usr/bin/env python3
"""
Example 11 — Tamper-evident Ledger + Tool Registry + Privacy Policy

Demonstrates:
1. POST /ledger/snapshots/generate  — trigger snapshot for yesterday
2. GET  /ledger/snapshots           — list recent snapshots
3. GET  /ledger/verify/{date}       — verify integrity
4. POST /tools/registry             — register a tool with policy=audit
5. GET  /tools/registry             — list tool registry
6. GET  /tools/security-events      — list events (empty unless worker ran)
7. PUT  /privacy/capture-policy     — set privacy mode to METADATA_ONLY

Install
───────
    pip install httpx python-dotenv

Run it
──────
    # Copy .env.example → .env and fill in your values, then:
    python 11_ledger_verify.py

Key .env variables used here:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8000  (local Docker stack)
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("Set RUNLEDGER_API_KEY in .env to a valid workspace API key.")
    sys.exit(1)


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def separator(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


def main() -> None:
    with httpx.Client(base_url=API_URL, headers=headers(), timeout=30) as client:

        # ── 1. Generate snapshot ───────────────────────────────────────────
        separator("1. Generate daily snapshot for yesterday")
        resp = client.post("/ledger/snapshots/generate")
        resp.raise_for_status()
        snap = resp.json()
        print(f"  snapshot_date : {snap['snapshot_date']}")
        print(f"  total_cost_usd: {snap['total_cost_usd']}")
        print(f"  call_count    : {snap['call_count']}")
        print(f"  hash (first 16): {snap['hash'][:16]}…")

        # ── 2. List snapshots ──────────────────────────────────────────────
        separator("2. List recent ledger snapshots")
        resp = client.get("/ledger/snapshots")
        resp.raise_for_status()
        snaps = resp.json()["items"]
        print(f"  Found {len(snaps)} snapshot(s)")
        for s in snaps[:5]:
            print(f"    {s['snapshot_date']}  cost={s['total_cost_usd']}  calls={s['call_count']}")

        # ── 3. Verify snapshot ─────────────────────────────────────────────
        separator("3. Verify snapshot integrity")
        if snaps:
            target_date = snap["snapshot_date"]
            resp = client.get(f"/ledger/verify/{target_date}")
            resp.raise_for_status()
            result = resp.json()
            status_icon = "✓" if result["match"] else "✗"
            print(f"  {status_icon}  status={result['status']}  match={result['match']}")
            print(f"     stored_hash  : {(result['stored_hash'] or '')[:16]}…")
            print(f"     computed_hash: {(result['computed_hash'] or '')[:16]}…")
        else:
            print("  No snapshots to verify.")

        # ── 4. Register a tool ────────────────────────────────────────────
        separator("4. Register tool: search (policy=audit)")
        resp = client.post(
            "/tools/registry",
            json={"tool_name": "search", "policy": "audit", "description": "Web search tool"},
        )
        resp.raise_for_status()
        tool = resp.json()
        print(f"  tool_name : {tool['tool_name']}")
        print(f"  policy    : {tool['policy']}")
        print(f"  description: {tool['description']}")

        # Also register another tool
        client.post(
            "/tools/registry",
            json={"tool_name": "calculator", "policy": "allow"},
        )

        # ── 5. List tool registry ─────────────────────────────────────────
        separator("5. List tool registry")
        resp = client.get("/tools/registry")
        resp.raise_for_status()
        tools = resp.json()["items"]
        print(f"  {'Tool Name':<20} {'Policy':<10} {'Description'}")
        print(f"  {'-'*50}")
        for t in tools:
            print(f"  {t['tool_name']:<20} {t['policy']:<10} {t['description'] or '—'}")

        # ── 6. List security events ───────────────────────────────────────
        separator("6. List security events")
        resp = client.get("/tools/security-events")
        resp.raise_for_status()
        events = resp.json()["items"]
        if events:
            print(f"  Found {len(events)} security event(s):")
            for e in events[:5]:
                print(f"    [{e['event_type']}] tool={e['tool_name']}  user={e['end_user_id']}")
        else:
            print("  No security events (worker hasn't detected any bursts).")

        # ── 7. Set capture policy ─────────────────────────────────────────
        separator("7. Set privacy capture policy → METADATA_ONLY")
        resp = client.put(
            "/privacy/capture-policy",
            json={"privacy_mode": "METADATA_ONLY"},
        )
        resp.raise_for_status()
        policy = resp.json()
        print(f"  privacy_mode: {policy['privacy_mode']}")
        print(f"  sampled_rate: {policy['sampled_rate']}")
        print(f"  updated_at  : {policy['updated_at']}")

        separator("Done")
        print("  All Phase 11 endpoints verified successfully.\n")


if __name__ == "__main__":
    main()
