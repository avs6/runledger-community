#!/usr/bin/env python3
"""End-to-end verification of the Observe surfaces against a running API (review O-26).

Replays a small workflow and asserts what Runs, Request Explorer, Request Flow,
Sessions, Outcomes and Analytics report for it:

  1. Signs in, mints a throwaway workspace key and a read-only key.
  2. Ingests three runs for a unique workflow (feature tag) in one session:
     two succeeded, one failed; records two SDK outcomes on the first run.
  3. Runs: unknown status → 422; the (started_at, id) cursor walks every run once;
     /runs/stats reports a 2/3 success rate; export carries the same filters.
  4. Explorer: status=failed matches the error call, status=succeeded the two others,
     and the workflow filter is a real feature_tag filter.
  5. Sessions: the session lists three turns; detail and cost-over-turns agree.
  6. Outcomes: SDK outcomes are visible in /outcomes (one table) and the run's cost is
     counted once even with two outcomes on it.
  7. Flow: savings are recorded savings only (zero here); the outcome comes from outcomes.
  8. Summary: success_rate comes from the API.
  9. Payloads: the read-only key gets no captured prompts; span metadata never repeats them.
 10. Compare two runs, saved views CRUD, the live SSE stream, and a monitoring feed.

Everything created is removed at the end (pass --keep to inspect it in the UI).
Needs the API, Redis and the Celery pipeline worker running.

Usage:
    python scripts/run_demo.py verify-observe
    python scripts/core/verify_observe.py --base-url http://localhost:8201
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CALL_COST = Decimal("0.02")


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
        self,
        method: str,
        path: str,
        key: str | None = None,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        return self.http.request(method, path, headers=headers, json=body, params=params)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _run_events(
    *, feature: str, session: str, user: str, ok: bool, offset_s: int
) -> tuple[str, list[dict[str, Any]]]:
    run_id, span_id = str(uuid.uuid4()), str(uuid.uuid4())
    start = datetime.now(UTC) - timedelta(seconds=offset_s)
    end = start + timedelta(milliseconds=900)
    status = "succeeded" if ok else "failed"
    return run_id, [
        {
            "event_type": "run_start",
            "run_id": run_id,
            "started_at": _iso(start),
            "end_user_id": user,
            "session_id": session,
            "feature_tag": feature,
        },
        {
            "event_type": "span_start",
            "span_id": span_id,
            "run_id": run_id,
            "span_type": "llm",
            "name": "answer",
            "started_at": _iso(start),
        },
        {
            "event_type": "provider_call",
            "run_id": run_id,
            "span_id": span_id,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "input_tokens": 800,
            "output_tokens": 200,
            "latency_ms": 900,
            "cost_usd": str(CALL_COST),
            "status": "success" if ok else "error",
            **({} if ok else {"error_type": "rate_limited"}),
        },
        {
            "event_type": "span_end",
            "span_id": span_id,
            "run_id": run_id,
            "status": status,
            "ended_at": _iso(end),
            "cost_usd": str(CALL_COST),
        },
        {
            "event_type": "run_end",
            "run_id": run_id,
            "status": status,
            "ended_at": _iso(end),
            "total_cost_usd": str(CALL_COST),
        },
    ]


def _wait(predicate: Any, timeout: float) -> Any:
    deadline = time.monotonic() + timeout
    value = None
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(1)
    return value


def run(args: argparse.Namespace) -> int:  # noqa: PLR0915
    api = Api(args.base_url)
    check = Check()
    suffix = uuid.uuid4().hex[:8]
    feature, session_id, user = f"verify-observe-{suffix}", f"sess-{suffix}", f"user-{suffix}"
    window = {"from": _iso(datetime.now(UTC) - timedelta(hours=1))}

    login = api.call("POST", "/auth/login", body={"email": args.email, "password": args.password})
    if login.status_code != 200:
        print(f"Sign-in failed ({login.status_code}): {login.text}")
        return 2
    sk = login.json()["api_key"]

    key_ids: list[str] = []
    view_id: str | None = None

    def _mint(name: str, scopes: list[str] | None = None) -> str:
        body: dict[str, Any] = {"name": name}
        if scopes:
            body["scopes"] = scopes
        resp = api.call("POST", "/settings/api-keys", sk, body)
        resp.raise_for_status()
        key_ids.append(resp.json()["id"])
        return str(resp.json()["key"])

    try:
        key = _mint(f"verify-observe-{suffix}")
        read_key = _mint(f"verify-observe-ro-{suffix}", ["read"])

        print("\n→ ingesting three runs and two outcomes")
        r1, e1 = _run_events(feature=feature, session=session_id, user=user, ok=True, offset_s=30)
        r2, e2 = _run_events(feature=feature, session=session_id, user=user, ok=True, offset_s=20)
        r3, e3 = _run_events(feature=feature, session=session_id, user=user, ok=False, offset_s=10)
        outcomes = [
            {
                "event_type": "outcome",
                "run_id": r1,
                "outcome_type": f"resolved-{suffix}",
                "success": True,
            },
            {
                "event_type": "outcome",
                "run_id": r1,
                "outcome_type": f"resolved-{suffix}",
                "success": True,
                "labels": {"n": 2},
            },
        ]
        sent = api.call("POST", "/ingest/v1/batch", key, {"events": e1 + e2 + e3})
        check(sent.status_code == 202, "runs accepted", sent.text)
        time.sleep(1)
        sent = api.call("POST", "/ingest/v1/batch", key, {"events": outcomes})
        check(sent.status_code == 202, "outcomes accepted", sent.text)

        def _runs_ready() -> list[dict[str, Any]] | None:
            resp = api.call("GET", "/runs", sk, params={"feature_tag": feature, **window})
            items = resp.json().get("items", []) if resp.status_code == 200 else []
            done = [i for i in items if i["status"] in ("succeeded", "failed")]
            return items if len(done) == 3 else None

        runs = _wait(_runs_ready, args.timeout) or []
        check(len(runs) == 3, "three finished runs listed", len(runs))

        print("\n→ runs: validation, cursor, stats, export")
        bad = api.call("GET", "/runs", sk, params={"status": "exploded"})
        check(bad.status_code == 422, "unknown status is a 422, not a 500", bad.status_code)
        bad_cursor = api.call("GET", "/runs", sk, params={"cursor": "%%%"})
        check(bad_cursor.status_code == 422, "malformed cursor is a 422", bad_cursor.status_code)

        seen: list[str] = []
        cursor: str | None = None
        for _ in range(5):
            params: dict[str, Any] = {
                "feature_tag": feature,
                "limit": 1,
                "include_total": "false",
                **window,
            }
            if cursor:
                params["cursor"] = cursor
            page = api.call("GET", "/runs", sk, params=params).json()
            seen += [i["id"] for i in page["items"]]
            cursor = page.get("next_cursor")
            if not cursor:
                break
        check(sorted(seen) == sorted([r1, r2, r3]), "cursor walks every run exactly once", seen)

        stats = api.call("GET", "/runs/stats", sk, params={"feature_tag": feature, **window}).json()
        check(stats.get("total") == 3 and stats.get("failed") == 1, "stats count every run", stats)
        check(
            stats.get("success_rate") == "0.6667",
            "stats success rate is 2/3",
            stats.get("success_rate"),
        )

        export = api.call(
            "GET", "/runs/export", sk, params={"feature_tag": feature, "status": "failed", **window}
        )
        rows = list(csv.DictReader(io.StringIO(export.text))) if export.status_code == 200 else []
        check([r["run_id"] for r in rows] == [r3], "export honours the list filters", rows)

        facets = api.call("GET", "/runs/facets", sk).json()
        check(
            "gpt-4o-mini" in facets.get("models", []),
            "model facets come from data",
            facets.get("models"),
        )

        print("\n→ request explorer")
        failed = api.call(
            "GET",
            "/analytics/request-explorer",
            sk,
            params={"feature_tag": feature, "status": "failed", **window},
        ).json()
        check(
            [i["run_id"] for i in failed.get("items", [])] == [r3],
            "status=failed matches the error call (O-01)",
            failed.get("items"),
        )
        ok = api.call(
            "GET",
            "/analytics/request-explorer",
            sk,
            params={"feature_tag": feature, "status": "succeeded", **window},
        ).json()
        check(ok.get("total") == 2, "status=succeeded matches the two successes", ok.get("total"))
        check(
            all(i.get("feature_tag") == feature for i in ok.get("items", [])),
            "workflow filter is a feature_tag filter (O-02)",
        )

        print("\n→ sessions")
        listing = api.call("GET", "/sessions", sk, params={"q": session_id}).json()
        match = [s for s in listing.get("items", []) if s["session_id"] == session_id]
        check(bool(match) and match[0]["run_count"] == 3, "session lists three turns", match)
        detail = api.call("GET", f"/sessions/{session_id}", sk).json()
        turns = api.call("GET", f"/sessions/{session_id}/cost-over-turns", sk).json()
        check(len(detail.get("runs", [])) == 3, "session detail has three runs")
        check(
            Decimal(turns["turns"][-1]["cumulative_cost_usd"]) == CALL_COST * 3,
            "cumulative cost over turns adds up",
            turns.get("turns"),
        )

        print("\n→ outcomes (one table) and ROI cost per run")

        def _outcomes() -> list[dict[str, Any]] | None:
            items = api.call("GET", "/outcomes", sk, params={"run_id": r1}).json().get("items", [])
            return items if len(items) == 2 else None

        got = _wait(_outcomes, args.timeout) or []
        check(len(got) == 2, "SDK outcomes are visible in /outcomes (O-03)", len(got))
        summary = api.call("GET", "/outcomes/summary", sk).json()
        row = next(
            (i for i in summary.get("items", []) if i["outcome_type"] == f"resolved-{suffix}"), None
        )
        check(
            row is not None and Decimal(row["total_cost_usd"]) == CALL_COST,
            "run cost counted once despite two outcomes (O-04)",
            row,
        )

        print("\n→ request flow")
        flow = api.call("GET", "/runs/flow", sk, params={"limit": 200, **window}).json()
        mine = [i for i in flow.get("items", []) if i["feature_tag"] == feature]
        check(len(mine) == 3, "flow includes the workflow's runs", len(mine))
        check(all(Decimal(i["savings_usd"]) == 0 for i in mine), "no fabricated savings (O-13)")
        r1_flow = next((i for i in mine if i["id"] == r1), None)
        check(
            r1_flow is not None and r1_flow["outcome"].startswith(f"resolved-{suffix}"),
            "flow outcome comes from the outcomes table",
            r1_flow and r1_flow["outcome"],
        )

        print("\n→ analytics summary")
        kpi = api.call("GET", "/analytics/summary", sk, params=window).json()
        check(kpi.get("success_rate") is not None, "summary returns success_rate (O-22)", kpi)
        scoped = api.call("GET", "/analytics/scoped-summary", sk, params=window).json()
        check(
            kpi.get("total_cost_usd") == scoped.get("total_cost_usd"),
            "summary and scoped summary agree (O-06)",
        )

        print("\n→ payload access")
        ro = api.call("GET", f"/runs/{r1}", read_key)
        check(ro.status_code == 200, "read-only key can read run metadata", ro.status_code)
        body = ro.json() if ro.status_code == 200 else {}
        check(
            body.get("input_payload") is None and body.get("span_payloads") is None,
            "read-only key gets no payloads (O-05)",
        )
        full = api.call("GET", f"/runs/{r1}", sk).json()
        check(
            all("messages" not in (s.get("metadata") or {}) for s in full.get("spans", [])),
            "span metadata never repeats payloads",
        )

        print("\n→ compare, saved views, stream, monitoring")
        cmp = api.call("GET", "/runs/compare", sk, params={"a": r1, "b": r3}).json()
        check(
            cmp.get("b", {}).get("error_count") == 1 and cmp.get("a", {}).get("error_count") == 0,
            "compare shows the failed call",
        )

        query = f"feature_tag={feature}&status=failed"
        created = api.call(
            "POST",
            "/runs/saved-views",
            sk,
            {"page": "runs", "name": f"failed {suffix}", "query": query},
        )
        check(created.status_code == 201, "saved view created", created.text)
        view_id = created.json().get("id") if created.status_code == 201 else None
        listed = (
            api.call("GET", "/runs/saved-views", sk, params={"page": "runs"})
            .json()
            .get("items", [])
        )
        check(
            any(v["id"] == view_id and v["query"] == query for v in listed),
            "saved view listed with its query",
        )
        renamed = api.call(
            "PUT",
            f"/runs/saved-views/{view_id}",
            sk,
            {"page": "runs", "name": f"errors {suffix}", "query": query},
        )
        check(
            renamed.status_code == 200 and renamed.json()["name"] == f"errors {suffix}",
            "saved view renamed",
        )
        wrong = api.call("GET", "/runs/saved-views", key, params={"page": "runs"})
        check(
            wrong.status_code in (401, 403), "saved views need a dashboard user", wrong.status_code
        )

        events = 0
        with api.http.stream(
            "GET",
            "/runs/stream",
            headers={"Authorization": f"Bearer {sk}"},
            params={"feature_tag": feature, "since": window["from"], "max_seconds": 3},
            timeout=15,
        ) as stream:
            for line in stream.iter_lines():
                if line == "event: run":
                    events += 1
        check(events >= 3, "live stream emits the workflow's runs (O-07)", events)

        mon = api.call(
            "GET", "/analytics/monitoring/security-events", sk, params={"limit": 5, **window}
        )
        check(
            mon.status_code == 200 and "x-total-count" in mon.headers,
            "monitoring pages on the server (O-18)",
            mon.status_code,
        )
    finally:
        if not args.keep:
            if view_id:
                api.call("DELETE", f"/runs/saved-views/{view_id}", sk)
            for item in (
                api.call("GET", "/outcomes", sk, params={"outcome_type": f"resolved-{suffix}"})
                .json()
                .get("items", [])
            ):
                api.call("DELETE", f"/outcomes/{item['id']}", sk)
            for key_id in key_ids:
                api.call("DELETE", f"/settings/api-keys/{key_id}", sk)

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
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="Seconds to wait for the pipeline worker."
    )
    parser.add_argument(
        "--keep", action="store_true", help="Keep the saved view, outcomes and keys afterwards."
    )
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
