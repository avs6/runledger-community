"""
Example 8 — Budget enforcement.

What this demonstrates
──────────────────────
- Creating a per-user daily budget via the RunLedger API
- Enabling the SDK's pre-call budget check (budget_check=True)
- Running LLM calls until the budget is exceeded
- Catching RunLedgerBudgetExceededError on the blocking call
- Listing budgets with live Redis spend counters
- Fetching breach history for the exceeded budget
- Opening the budget detail page for edits, overrides, and breach review

Prerequisites
─────────────
A running RunLedger stack:

    docker compose -f infra/docker-compose.yml up -d

Install
───────
    pip install httpx python-dotenv
    pip install -e "/path/to/runledger/packages/sdk[openai]"

Run it
──────
    # Copy .env.example → .env and fill in your values, then:
    python 08_budget_enforcement.py

    # Use a custom user ID and limit
    python 08_budget_enforcement.py --user alice --limit 0.05

Key .env variables used here:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8000  (local Docker stack)
    OPENAI_API_KEY      — your OpenAI key
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from decimal import Decimal

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


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}"}


def _post(path: str, body: dict) -> dict:
    resp = httpx.post(f"{BASE_URL}{path}", json=body, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()  # type: ignore[return-value]


def _get(path: str, params: dict | None = None) -> dict:
    resp = httpx.get(f"{BASE_URL}{path}", params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()  # type: ignore[return-value]


def _delete(path: str) -> None:
    resp = httpx.delete(f"{BASE_URL}{path}", headers=_headers(), timeout=10)
    resp.raise_for_status()


# ── Formatting ────────────────────────────────────────────────────────────────

def _fmt_usd(value: str | float | Decimal) -> str:
    n = float(value)
    if n >= 1:
        return f"${n:.2f}"
    if n >= 0.001:
        return f"${n:.4f}"
    return f"${n:.6f}"


def _spend_bar(pct: float, width: int = 30) -> str:
    filled = min(width, int(pct / 100 * width))
    empty = width - filled
    color = "\033[92m" if pct < 70 else ("\033[93m" if pct < 100 else "\033[91m")
    reset = "\033[0m"
    return f"{color}{'█' * filled}{'░' * empty}{reset}  {pct:.1f}%"


def _hr(width: int = 60) -> None:
    print("─" * width)


# ── Budget API helpers ─────────────────────────────────────────────────────────


def create_budget(user_id: str, limit_usd: str) -> dict:
    """POST /budgets — create a per-user daily block budget."""
    return _post(
        "/budgets",
        {
            "scope_type": "end_user",
            "scope_id": user_id,
            "period_type": "daily",
            "limit_usd": limit_usd,
            "action": "block",
        },
    )


def list_budgets() -> list[dict]:
    return _get("/budgets")["items"]


def get_breaches(budget_id: str) -> list[dict]:
    return _get(f"/budgets/{budget_id}/breaches")["items"]


def delete_budget(budget_id: str) -> None:
    _delete(f"/budgets/{budget_id}")


# ── SDK calls ─────────────────────────────────────────────────────────────────


def run_llm_calls(user_id: str, max_calls: int = 20) -> tuple[int, str | None]:
    """
    Run LLM calls with budget_check=True until blocked.

    Returns (calls_succeeded, budget_id_that_blocked).
    """
    import openai
    from runledger_sdk import RunLedger, RunLedgerBudgetExceededError

    rl = RunLedger(
        base_url=BASE_URL,
        budget_check=True,  # enable pre-call budget enforcement
    )
    rl.instrument()

    client = openai.OpenAI()

    succeeded = 0
    blocked_by: str | None = None

    for i in range(1, max_calls + 1):
        try:
            with rl.context(end_user_id=user_id, feature_tag="budget-demo"):
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": f"Say 'call {i} ok' and nothing else.",
                        }
                    ],
                    max_tokens=10,
                )
            text = resp.choices[0].message.content or ""
            print(f"  Call {i:>2}: {text.strip()}")
            succeeded += 1

        except RunLedgerBudgetExceededError as exc:
            blocked_by = exc.budget_id
            print(f"\n  Call {i:>2}: BLOCKED — RunLedgerBudgetExceededError (budget {exc.budget_id})")
            break

        except Exception as exc:
            print(f"  Call {i:>2}: ERROR — {exc}", file=sys.stderr)
            break

        # Small delay so the metering worker can write cost_usd between calls
        time.sleep(0.3)

    rl.shutdown()
    return succeeded, blocked_by


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="RunLedger budget enforcement demo")
    parser.add_argument(
        "--user",
        dest="user_id",
        default="demo-user-budget-test",
        help="End-user ID to apply the budget to",
    )
    parser.add_argument(
        "--limit",
        dest="limit_usd",
        default="0.10",
        help="Daily spend limit in USD (default: 0.10)",
    )
    parser.add_argument(
        "--max-calls",
        dest="max_calls",
        type=int,
        default=20,
        help="Maximum LLM calls to attempt (default: 20)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the budget after the demo",
    )
    args = parser.parse_args()

    print("\nRunLedger Budget Enforcement Demo")
    print(f"User: {args.user_id}  |  Daily limit: ${args.limit_usd}  |  API: {BASE_URL}\n")

    # ── Step 1: Create budget ─────────────────────────────────────────────────
    _hr()
    print("  STEP 1 — Create budget")
    _hr()
    budget = create_budget(args.user_id, args.limit_usd)
    budget_id = budget["id"]
    print(f"  Created budget : {budget_id}")
    print(f"  Scope          : {budget['scope_type']} / {budget['scope_id']}")
    print(f"  Period         : {budget['period_type']}")
    print(f"  Limit          : {_fmt_usd(budget['limit_usd'])}")
    print(f"  Action         : {budget['action']}")
    _hr()
    print()

    # ── Step 2: Run calls until blocked ──────────────────────────────────────
    _hr()
    print(f"  STEP 2 — Running up to {args.max_calls} LLM calls (budget_check=True)")
    _hr()
    succeeded, blocked_by = run_llm_calls(args.user_id, args.max_calls)
    print()
    _hr()
    print(f"  Calls succeeded : {succeeded}")
    print(f"  Blocked by      : {blocked_by or '(not blocked — increase --max-calls)'}")
    _hr()
    print()

    # Give the cost enrichment worker a moment to process remaining calls
    if succeeded > 0:
        print("  Waiting 5s for cost enrichment worker to process calls...")
        time.sleep(5)
        print()

    # ── Step 3: Show budget with current spend ────────────────────────────────
    _hr()
    print("  STEP 3 — Budget status (live Redis spend)")
    _hr()
    budgets = list_budgets()
    for b in budgets:
        if b["id"] == budget_id:
            pct = float(b["pct_used"])
            print(f"  Spend : {_fmt_usd(b['current_spend_usd'])} / {_fmt_usd(b['limit_usd'])}")
            print(f"  Usage : {_spend_bar(pct)}")
            break
    _hr()
    print()

    # ── Step 4: Show breach history ───────────────────────────────────────────
    _hr()
    print("  STEP 4 — Breach history")
    _hr()
    breaches = get_breaches(budget_id)
    if not breaches:
        print("  (no breaches recorded yet — metering worker may still be processing)")
    else:
        print(f"  {'Occurred at':<28} {'Spend at breach':>16}  Action")
        print("  " + "-" * 56)
        for br in breaches:
            occurred = br["occurred_at"][:19].replace("T", " ")
            print(
                f"  {occurred:<28} "
                f"{_fmt_usd(br['spend_at_breach_usd']):>16}  "
                f"{br['action_taken']}"
            )
    _hr()
    print()

    # ── Step 5: Cleanup (optional) ────────────────────────────────────────────
    if args.cleanup:
        _hr()
        print("  STEP 5 — Cleanup")
        _hr()
        delete_budget(budget_id)
        print(f"  Deleted budget {budget_id}")
        _hr()
        print()

    print("Demo complete.")
    print(
        f"\nTip: open http://localhost:3000/budgets to see the budget in the dashboard,\n"
        f"     or http://localhost:3000/budgets/{budget_id} for policy detail, overrides, and breach history.\n"
    )


if __name__ == "__main__":
    main()
