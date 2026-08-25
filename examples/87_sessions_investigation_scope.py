"""
Example 87 — Sessions Investigation Scope

Demonstrates the WU-015 session-led investigation walkthrough: listing
sessions with filters, fetching session detail with cost-over-turns,
and showing the identity and FinOps context available for attribution.

Usage:
    export RUNLEDGER_API_KEY="rl_test_..."
    python examples/87_sessions_investigation_scope.py
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        print("=== Sessions (30d, min 2 turns) ===")
        r = c.get("/sessions", params={"min_turns": 2, "page_size": 5})
        r.raise_for_status()
        data = r.json()
        print(f"  Total: {data['total']} sessions")
        for s in data["items"][:3]:
            print(f"  {s['session_id'][:16]}… user={s.get('end_user_id', '—')} "
                  f"turns={s['run_count']} cost=${s.get('total_cost_usd', '0')}")

        if data["items"]:
            sid = data["items"][0]["session_id"]
            print(f"\n=== Session Detail: {sid[:16]}… ===")
            r = c.get(f"/sessions/{sid}")
            r.raise_for_status()
            detail = r.json()
            print(f"  User: {detail.get('end_user_id', 'Not captured')}")
            print(f"  Turns: {detail['run_count']}")
            print(f"  Total cost: ${detail.get('total_cost_usd', '0')}")
            print(f"  Runs: {len(detail['runs'])}")
            for run in detail["runs"][:3]:
                print(f"    Turn {run['turn_number']}: {run['status']} "
                      f"cost=${run.get('total_cost_usd', '0')}")

            print(f"\n=== Cost Over Turns ===")
            r = c.get(f"/sessions/{sid}/cost-over-turns")
            r.raise_for_status()
            turns = r.json()
            for t in turns["turns"][:5]:
                print(f"  Turn {t['turn_number']}: "
                      f"${t.get('cost_usd', '0')} "
                      f"(cumulative: ${t['cumulative_cost_usd']})")

        print("\nSession detail page links to Users, API Keys, Budgets,")
        print("Budget Detail, and Chargeback for identity and cost attribution.")


if __name__ == "__main__":
    main()
