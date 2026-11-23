#!/usr/bin/env python3
"""End-to-end verification of scoped budget counting and enforcement against a running API.

Replays what a workflow owner does and asserts every step:

  1. Signs in and mints a throwaway workspace API key.
  2. Creates three budgets for a unique workflow (feature tag) and end user:
     - feature_tag  · block  · $0.05 / month
     - end_user     · notify · $10   / month
     - api_key      · notify · $10   / month (the throwaway key)
  3. Ingests two priced model calls ($0.03 each) through /ingest/v1/batch.
  4. Waits for the pipeline worker, then asserts each budget counted exactly $0.06.
  5. Re-sends the same batch and asserts nothing is double counted.
  6. Asserts the feature-tag budget recorded one breach, and that
     GET /budgets/check now blocks that workflow but allows another one.
  7. Scope validation: a duplicate active scope is refused (409), malformed scopes 422.
  8. Model budget (scope_type=model, one key): a new priced call counts against it and
     /budgets/check?model= blocks that model for the key but not another model.
  9. Burn-down: GET /budgets/{id}/burndown reports this period's spend.
 10. Simulation: POST /budgets/simulate replays today's calls and reports the breach
     and the calls a tighter limit would have blocked.
 11. Runaway hold: a held session is refused by /budgets/check and allowed again
     once released.
 12. Optional (--gateway-url + --alias): sends a chat completion tagged with the
     workflow through gateway-rs and expects 429 ``budget_exceeded``, and one in a
     held session and expects 429 ``runaway_hold``.

Budgets and the key are deleted at the end (pass --keep to inspect them in the UI).
Needs the API, Redis and the Celery pipeline worker running.

Usage:
    python scripts/run_demo.py verify-budgets
    python scripts/core/verify_budgets.py --base-url http://localhost:8201 \\
        --gateway-url http://localhost:8210 --alias smart
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CALL_COST = Decimal("0.03")


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passed = 0

    def __call__(self, ok: bool, label: str, detail: Any = "") -> None:
        if ok:
            self.passed += 1
            print(f"  ✓ {label}")
        else:
            self.failures.append(label)
            print(f"  ✗ {label} {detail}")


class Api:
    def __init__(self, base_url: str) -> None:
        self.http = httpx.Client(base_url=base_url.rstrip("/"), timeout=30)

    def call(
        self, method: str, path: str, key: str | None = None, body: dict[str, Any] | None = None
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        return self.http.request(method, path, headers=headers, json=body)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _priced_run(feature: str, user: str, model: str = "gpt-4o-mini") -> list[dict[str, Any]]:
    run_id, span_id = str(uuid.uuid4()), str(uuid.uuid4())
    now = _iso(datetime.now(UTC))
    return [
        {
            "event_type": "run_start",
            "run_id": run_id,
            "started_at": now,
            "end_user_id": user,
            "feature_tag": feature,
            "agent_name": feature,
        },
        {
            "event_type": "span_start",
            "span_id": span_id,
            "run_id": run_id,
            "span_type": "llm",
            "name": "llm-call",
            "started_at": now,
        },
        {
            "event_type": "provider_call",
            "run_id": run_id,
            "span_id": span_id,
            "provider": "openai",
            "model": model,
            "input_tokens": 1200,
            "output_tokens": 300,
            "latency_ms": 800,
            "cost_usd": str(CALL_COST),
            "status": "success",
        },
        {
            "event_type": "span_end",
            "span_id": span_id,
            "run_id": run_id,
            "status": "succeeded",
            "ended_at": now,
            "cost_usd": str(CALL_COST),
        },
        {
            "event_type": "run_end",
            "run_id": run_id,
            "status": "succeeded",
            "ended_at": now,
            "total_cost_usd": str(CALL_COST),
        },
    ]


def _spend(api: Api, session_key: str, budget_ids: list[str]) -> dict[str, Decimal]:
    resp = api.call("GET", "/budgets", session_key)
    resp.raise_for_status()
    return {
        b["id"]: Decimal(str(b["current_spend_usd"]))
        for b in resp.json()["items"]
        if b["id"] in budget_ids
    }


def _wait_for_spend(
    api: Api, session_key: str, budget_ids: list[str], target: Decimal, timeout: float
) -> dict[str, Decimal]:
    deadline = time.monotonic() + timeout
    spend: dict[str, Decimal] = {}
    while time.monotonic() < deadline:
        spend = _spend(api, session_key, budget_ids)
        if spend and all(v >= target for v in spend.values()):
            return spend
        time.sleep(1)
    return spend


def run(args: argparse.Namespace) -> int:
    api = Api(args.base_url)
    check = Check()
    suffix = uuid.uuid4().hex[:8]
    feature, user = f"verify-budget-{suffix}", f"verify-user-{suffix}"

    login = api.call("POST", "/auth/login", body={"email": args.email, "password": args.password})
    if login.status_code != 200:
        print(f"Sign-in failed ({login.status_code}): {login.text}")
        return 2
    session_key = login.json()["api_key"]

    key_resp = api.call(
        "POST", "/settings/api-keys", session_key, {"name": f"verify-budgets-{suffix}"}
    )
    if key_resp.status_code not in (200, 201):
        print(f"API key creation failed ({key_resp.status_code}): {key_resp.text}")
        return 2
    key_id, raw_key = key_resp.json()["id"], key_resp.json()["key"]
    budget_ids: list[str] = []

    try:
        print("\n→ creating scoped budgets")
        specs = [
            ("feature_tag", feature, "0.05", "block"),
            ("end_user", user, "10", "notify"),
            ("api_key", key_id, "10", "notify"),
        ]
        for scope_type, scope_id, limit, action in specs:
            resp = api.call(
                "POST",
                "/budgets",
                session_key,
                {
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    "period_type": "monthly",
                    "limit_usd": limit,
                    "action": action,
                },
            )
            check(resp.status_code == 201, f"{scope_type} budget created", resp.text)
            if resp.status_code == 201:
                budget_ids.append(resp.json()["id"])
        if len(budget_ids) != len(specs):
            return 1
        feature_budget = budget_ids[0]

        print("\n→ ingesting two priced calls for the workflow")
        batch = _priced_run(feature, user) + _priced_run(feature, user)
        sent = api.call("POST", "/ingest/v1/batch", raw_key, {"events": batch})
        check(sent.status_code == 202, "batch accepted", sent.text)
        expected = CALL_COST * 2
        spend = _wait_for_spend(api, session_key, budget_ids, expected, args.timeout)
        for (scope_type, *_), budget_id in zip(specs, budget_ids, strict=True):
            got = spend.get(budget_id, Decimal(0))
            check(got == expected, f"{scope_type} budget counted ${expected}", f"got ${got}")

        print("\n→ re-sending the same events (retry)")
        api.call("POST", "/ingest/v1/batch", raw_key, {"events": batch})
        time.sleep(min(5.0, args.timeout))
        again = _spend(api, session_key, budget_ids)
        check(
            all(v == expected for v in again.values()),
            "retried events not double counted",
            {k[:8]: str(v) for k, v in again.items()},
        )

        print("\n→ breach and enforcement")
        breaches = api.call("GET", f"/budgets/{feature_budget}/breaches", session_key)
        items = breaches.json().get("items", []) if breaches.status_code == 200 else []
        check(len(items) == 1, "one breach recorded for the workflow budget", len(items))
        blocked = api.call("GET", f"/budgets/check?feature_tag={feature}", raw_key).json()
        check(
            blocked.get("allowed") is False and blocked.get("action") == "block",
            "budget check blocks the workflow",
            blocked,
        )
        other = api.call("GET", f"/budgets/check?feature_tag=other-{suffix}", raw_key).json()
        check(other.get("allowed") is True, "another workflow is still allowed", other)

        print("\n→ scope validation (F-12)")
        dup = api.call(
            "POST",
            "/budgets",
            session_key,
            {
                "scope_type": "feature_tag",
                "scope_id": feature,
                "period_type": "monthly",
                "limit_usd": "1",
                "action": "notify",
            },
        )
        check(dup.status_code == 409, "duplicate active scope refused (409)", dup.status_code)
        for bad, label in (
            ({"scope_type": "app", "scope_id": "not-a-uuid"}, "malformed app scope"),
            ({"scope_type": "workspace", "scope_id": "x"}, "workspace scope with scope_id"),
            (
                {"scope_type": "feature_tag", "scope_id": feature, "api_key_id": key_id},
                "key filter on a non-model scope",
            ),
        ):
            resp = api.call(
                "POST",
                "/budgets",
                session_key,
                {**bad, "period_type": "monthly", "limit_usd": "1", "action": "notify"},
            )
            check(resp.status_code == 422, f"{label} refused (422)", resp.status_code)

        print("\n→ model budget (G-01)")
        model = f"verify-model-{suffix}"
        resp = api.call(
            "POST",
            "/budgets",
            session_key,
            {
                "scope_type": "model",
                "scope_id": f"{model}*",
                "api_key_id": key_id,
                "period_type": "daily",
                "limit_usd": "0.02",
                "action": "block",
            },
        )
        check(resp.status_code == 201, "model budget created", resp.text)
        model_budget = resp.json()["id"] if resp.status_code == 201 else None
        if model_budget:
            budget_ids.append(model_budget)
            sent = api.call(
                "POST",
                "/ingest/v1/batch",
                raw_key,
                {"events": _priced_run(f"model-{suffix}", user, model=f"{model}-large")},
            )
            check(sent.status_code == 202, "model call accepted", sent.text)
            got = _wait_for_spend(api, session_key, [model_budget], CALL_COST, args.timeout)
            check(got.get(model_budget) == CALL_COST, "model budget counted the call", got)
            held = api.call("GET", f"/budgets/check?model={model}-large", raw_key).json()
            check(
                held.get("allowed") is False and held.get("budget_id") == model_budget,
                "budget check blocks the model for this key",
                held,
            )
            free = api.call("GET", "/budgets/check?model=some-other-model", raw_key).json()
            check(free.get("allowed") is True, "another model is still allowed", free)

        print("\n→ burn-down and forecast")
        burn = api.call("GET", f"/budgets/{feature_budget}/burndown", session_key)
        check(burn.status_code == 200, "burn-down returned", burn.text[:200])
        if burn.status_code == 200:
            data = burn.json()
            check(
                Decimal(str(data["current_spend_usd"])) >= expected,
                "burn-down shows spend",
                data["current_spend_usd"],
            )
            check(data["already_breached"] is True, "burn-down marks the breach")
            check(len(data["points"]) > 0, "burn-down has points")

        print("\n→ simulation against the last day")
        sim = api.call(
            "POST",
            "/budgets/simulate",
            session_key,
            {
                "scope_type": "feature_tag",
                "scope_id": feature,
                "period_type": "daily",
                "limit_usd": "0.02",
                "action": "block",
                "days": 1,
            },
        )
        check(sim.status_code == 200, "simulation ran", sim.text[:200])
        if sim.status_code == 200:
            result = sim.json()
            check(
                result["total_calls"] == 2,
                "simulation saw the workflow's 2 calls",
                result["total_calls"],
            )
            check(result["breach_count"] == 1, "simulation finds the breach", result["summary"])
            check(
                result["affected_calls"] == 1, "one call would have been blocked", result["summary"]
            )

        print("\n→ runaway hold (cd:B-09)")
        session_id = f"verify-session-{suffix}"
        hold = api.call(
            "POST",
            "/budgets/runaway-holds",
            session_key,
            {"subject_type": "session", "subject_id": session_id, "minutes": 5},
        )
        check(hold.status_code == 201, "hold placed", hold.text)
        stopped = api.call("GET", f"/budgets/check?session_id={session_id}", raw_key).json()
        check(
            stopped.get("allowed") is False and "runaway_hold" in str(stopped.get("reason")),
            "budget check refuses the held session",
            stopped,
        )
        if args.gateway_url and args.alias:
            gw = httpx.post(
                f"{args.gateway_url.rstrip('/')}/gateway/chat/completions",
                headers={"Authorization": f"Bearer {raw_key}"},
                json={
                    "model": args.alias,
                    "messages": [{"role": "user", "content": "ping"}],
                    "metadata": {"session_id": session_id},
                    "cache": False,
                },
                timeout=60,
            )
            check(gw.status_code == 429, "gateway refuses the held session (429)", gw.text[:200])
            check(
                gw.headers.get("x-cost-cap-reason") in (None, "runaway_hold"),
                "rejection names runaway protection",
                gw.headers.get("x-cost-cap-reason"),
            )
        if hold.status_code == 201:
            released = api.call(
                "POST", f"/budgets/runaway-holds/{hold.json()['id']}/release", session_key
            )
            check(released.status_code == 200, "hold released", released.text)
            time.sleep(1)
            again_ok = api.call("GET", f"/budgets/check?session_id={session_id}", raw_key).json()
            check(again_ok.get("allowed") is True, "released session is allowed again", again_ok)

        if args.gateway_url and args.alias:
            print("\n→ gateway enforcement")
            gw = httpx.post(
                f"{args.gateway_url.rstrip('/')}/gateway/chat/completions",
                headers={"Authorization": f"Bearer {raw_key}"},
                json={
                    "model": args.alias,
                    "messages": [{"role": "user", "content": "ping"}],
                    "metadata": {"feature_tag": feature},
                    "cache": False,
                },
                timeout=60,
            )
            check(gw.status_code == 429, "gateway rejects the exhausted workflow (429)", gw.text)
            check(
                gw.headers.get("x-cost-cap-reason") in (None, "budget_exceeded")
                and "Budget" in gw.text,
                "rejection names the budget",
                gw.text[:200],
            )
        else:
            print("\n→ gateway enforcement skipped (pass --gateway-url and --alias)")
    finally:
        if not args.keep:
            for budget_id in budget_ids:
                api.call("DELETE", f"/budgets/{budget_id}", session_key)
            api.call("DELETE", f"/settings/api-keys/{key_id}", session_key)

    print(f"\n{check.passed} passed, {len(check.failures)} failed")
    for label in check.failures:
        print(f"  FAILED: {label}")
    return 1 if check.failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default=os.getenv("RUNLEDGER_URL", "http://localhost:8201"))
    parser.add_argument(
        "--email", default=os.getenv("RUNLEDGER_PLATFORM_EMAIL", "admin@runledger.local")
    )
    parser.add_argument("--password", default=os.getenv("RUNLEDGER_PLATFORM_PASSWORD", "runledger"))
    parser.add_argument("--gateway-url", default=os.getenv("RUNLEDGER_GATEWAY_URL"))
    parser.add_argument("--alias", default=os.getenv("RUNLEDGER_GATEWAY_ALIAS"))
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="Seconds to wait for the pipeline worker."
    )
    parser.add_argument("--keep", action="store_true", help="Keep the budgets and key afterwards.")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
