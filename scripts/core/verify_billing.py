#!/usr/bin/env python3
"""End-to-end verification of Billing & Chargeback against a running stack.

Creates a throwaway org with two admins, sends priced usage for three workflows, and
asserts every control:

  1. Periods: create; overlapping dates → 409; end before start → 422.
  2. Cost centers: create, nest, cycle refused (422), tree.
  3. Chargeback rules map a workflow tag to cost centers by weight: weights over 1 →
     409; a second dimension → 409; direct with weight < 1 → 422.
  4. Separation of duties: an approval-gated rule can't be activated with PUT (409),
     its requester can't approve it (403), another admin can (rule becomes active).
  5. Billable cost is one definition: a failed-but-charged call counts in the
     chargeback report and the cost-center report.
  6. Cost-center report applies the rules: direct cost per center, nothing unassigned
     for mapped tags, the unmapped tag reported as unassigned.
  7. Shared costs: weights must sum to 1 (422); applying a pool persists the split and
     re-applying replaces it; the report shows it.
  8. CSV exports escape formulas; the chargeback export honours end_user_id.
  9. Adjustments record who made them. Close freezes the period: a second close →
     409, adjustments locked (409), late usage leaves the closed bill unchanged and
     reconciliation flags the drift; the signed export verifies with the workspace key
     (and a tampered copy doesn't).
 10. Reopen (reason required) and close again include the late usage; rotating the
     signing key keeps the old snapshot verifiable.

The org is deleted at the end (pass --keep to inspect it in the UI).

Usage:
    python scripts/run_demo.py verify-billing
"""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import hmac
import io
import json
import os
import sys
import time
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSWORD = "verify-billing-Pass-1"


class Check:
    def __init__(self) -> None:
        self.passed = 0
        self.failures: list[str] = []

    def __call__(self, ok: bool, label: str, detail: Any = "") -> bool:
        if ok:
            self.passed += 1
            print(f"  ✓ {label}")
        else:
            self.failures.append(label)
            print(f"  ✗ {label} {str(detail)[:300]}")
        return ok


class Api:
    def __init__(self, base_url: str) -> None:
        self.http = httpx.Client(base_url=base_url.rstrip("/"), timeout=60)

    def call(
        self,
        method: str,
        path: str,
        key: str | None = None,
        body: Any = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        return self.http.request(method, path, headers=headers, json=body, params=params)


def _sign_in(api: Api, email: str, temp_password: str) -> str:
    login = api.call("POST", "/auth/login", body={"email": email, "password": temp_password})
    login.raise_for_status()
    key = login.json()["api_key"]
    api.call(
        "PUT", "/users/me", key, {"current_password": temp_password, "password": PASSWORD}
    ).raise_for_status()
    return str(key)


def _wait(fn: Any, timeout: float = 45.0) -> Any:
    deadline = time.monotonic() + timeout
    value = None
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(1.5)
    return value


def _usage_events(tag: str, cost: str, *, user: str, status: str = "success") -> list[dict]:
    run_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    return [
        {
            "event_type": "run_start",
            "run_id": run_id,
            "started_at": now,
            "feature_tag": tag,
            "end_user_id": user,
        },
        {
            "event_type": "provider_call",
            "run_id": run_id,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "input_tokens": 100,
            "output_tokens": 20,
            "cost_usd": cost,
            "status": status,
        },
        {"event_type": "run_end", "run_id": run_id, "status": "succeeded", "ended_at": now},
    ]


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def run(args: argparse.Namespace) -> int:
    api = Api(args.base_url)
    check = Check()
    suffix = uuid.uuid4().hex[:8]
    today = datetime.now(UTC).date()
    month = f"{today.year}-{today.month:02d}"
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

    login = api.call("POST", "/auth/login", body={"email": args.email, "password": args.password})
    if login.status_code != 200:
        print(f"Platform sign-in failed ({login.status_code}): {login.text}")
        return 2
    platform = login.json()["api_key"]
    org_name = f"verify-billing-{suffix}"
    org = api.call(
        "POST",
        "/org/tenants",
        platform,
        {
            "name": org_name,
            "admin_email": f"billing-a-{suffix}@verify.test",
            "skip_verification": True,
        },
    )
    if org.status_code != 201:
        print(f"Org creation failed ({org.status_code}): {org.text}")
        return 2
    org_data = org.json()
    try:
        a = _sign_in(api, f"billing-a-{suffix}@verify.test", org_data["temporary_password"])
        email_b = f"billing-b-{suffix}@verify.test"
        invited = api.call(
            "POST",
            "/users/invite",
            a,
            {"email": email_b, "role": "workspace_admin", "skip_verification": True},
        )
        invited.raise_for_status()
        b = _sign_in(api, email_b, invited.json()["temporary_password"])
        ingest_key = api.call(
            "POST",
            "/settings/api-keys",
            a,
            {"name": f"verify-billing-{suffix}", "scopes": ["read", "ingest"]},
        ).json()["key"]
        ingest = {"Authorization": f"Bearer {ingest_key}"}

        print("\n→ usage")
        events: list[dict] = []
        for _ in range(3):
            events += _usage_events("support", "1.00", user="u-1")
        events += _usage_events(
            "support", "0.20", user="u-1", status="error"
        )  # charged though it failed
        for _ in range(2):
            events += _usage_events("search", "0.50", user="u-2")
        events += _usage_events("=evil", "0.10", user="=cmd")
        r = api.http.post("/ingest/v1/batch", headers=ingest, json={"events": events})
        check(r.status_code == 202, "usage accepted", r.text)

        def report(dimension: str = "feature_tag", **params: Any) -> dict:
            resp = api.call(
                "GET",
                "/billing/chargeback-report",
                a,
                params={"period": month, "dimension": dimension, **params},
            )
            return resp.json()["items"][0] if resp.status_code == 200 else {}

        rows = _wait(lambda: (rep := report()) and len(rep.get("breakdown", [])) >= 3 and rep)
        by_tag = {i["dimension_key"]: _d(i["cost_usd"]) for i in (rows or {}).get("breakdown", [])}
        check(
            by_tag.get("support") == Decimal("3.20"),
            "failed-but-charged call counted (support = 3.20)",
            by_tag,
        )
        check(by_tag.get("search") == Decimal("1.00"), "search = 1.00", by_tag)

        print("\n→ periods")
        period = api.call(
            "POST", "/billing/periods", a, {"period_start": str(start), "period_end": str(end)}
        )
        check(period.status_code == 201, "period created", period.text)
        period_id = period.json()["id"]
        overlap = api.call(
            "POST", "/billing/periods", a, {"period_start": str(start), "period_end": str(start)}
        )
        check(overlap.status_code == 409, "overlapping period refused (409)", overlap.status_code)
        bad = api.call(
            "POST", "/billing/periods", a, {"period_start": str(end), "period_end": str(start)}
        )
        check(bad.status_code == 422, "end before start refused (422)", bad.status_code)

        print("\n→ cost centers")
        sup = api.call(
            "POST", "/billing/cost-centers", a, {"name": "Support", "code": "SUP"}
        ).json()
        plat = api.call(
            "POST", "/billing/cost-centers", a, {"name": "Platform", "code": "PLT"}
        ).json()
        child = api.call(
            "POST", "/billing/cost-centers", a, {"name": "Search", "parent_id": plat["id"]}
        )
        check(child.status_code == 201, "nested cost center created", child.text)
        cycle = api.call(
            "PUT", f"/billing/cost-centers/{plat['id']}", a, {"parent_id": child.json()["id"]}
        )
        check(cycle.status_code == 422, "cycle refused (422)", cycle.status_code)
        tree = api.call("GET", "/billing/cost-centers/tree", a).json()
        check(
            any(n["name"] == "Platform" and n["children"] for n in tree),
            "tree nests Search under Platform",
        )

        print("\n→ chargeback rules")

        def rule(body: dict, key: str = a) -> httpx.Response:
            return api.call(
                "POST", "/billing/chargeback-rules", key, {"dimension": "feature_tag", **body}
            )

        r1 = rule({"dimension_value": "support", "cost_center_id": sup["id"], "weight": "0.6"})
        r2 = rule({"dimension_value": "support", "cost_center_id": plat["id"], "weight": "0.4"})
        check(
            r1.status_code == r2.status_code == 201,
            "support split 60/40 across two centers",
            (r1.text, r2.text),
        )
        over = rule({"dimension_value": "support", "cost_center_id": plat["id"], "weight": "0.1"})
        check(over.status_code == 409, "weights over 1 refused (409)", over.status_code)
        other_dim = api.call(
            "POST",
            "/billing/chargeback-rules",
            a,
            {
                "dimension": "end_user",
                "dimension_value": "u-1",
                "cost_center_id": sup["id"],
                "weight": "1",
            },
        )
        check(other_dim.status_code == 409, "second dimension refused (409)", other_dim.status_code)
        direct_half = rule(
            {
                "dimension_value": "search",
                "cost_center_id": plat["id"],
                "weight": "0.5",
                "allocation_type": "direct",
            }
        )
        check(
            direct_half.status_code == 422,
            "direct rule with weight < 1 refused (422)",
            direct_half.status_code,
        )

        print("\n→ separation of duties")
        gated = rule(
            {
                "dimension_value": "search",
                "cost_center_id": plat["id"],
                "weight": "1",
                "allocation_type": "direct",
                "require_approval": True,
            }
        )
        gated_rule = gated.json()
        check(
            gated_rule.get("status") == "pending_approval" and gated_rule.get("approval_id"),
            "approval-gated rule waits in Approvals",
            gated.text,
        )
        forced = api.call(
            "PUT", f"/billing/chargeback-rules/{gated_rule['id']}", a, {"status": "active"}
        )
        check(
            forced.status_code == 409,
            "can't activate a pending rule with PUT (409)",
            forced.status_code,
        )
        self_ok = api.call("PUT", f"/approvals/{gated_rule['approval_id']}/approve", a, {})
        check(
            self_ok.status_code == 403,
            "requester can't approve their own rule (403)",
            self_ok.status_code,
        )
        other_ok = api.call("PUT", f"/approvals/{gated_rule['approval_id']}/approve", b, {})
        check(other_ok.status_code == 200, "another admin approves", other_ok.text)
        active = api.call("GET", f"/billing/chargeback-rules/{gated_rule['id']}", a).json()
        check(active.get("status") == "active", "approved rule is active", active)

        print("\n→ cost-center report")
        cc = api.call(
            "GET", "/billing/chargeback-report/cost-centers", a, params={"period": month}
        ).json()
        by_cc = {row["name"]: _d(row["direct_usd"]) for row in cc.get("rows", [])}
        check(by_cc.get("Support") == Decimal("1.92"), "Support gets 60% of 3.20 = 1.92", by_cc)
        check(
            by_cc.get("Platform") == Decimal("2.28"),
            "Platform gets 40% of 3.20 + search 1.00 = 2.28",
            by_cc,
        )
        check(
            _d(cc.get("unassigned_usd", -1)) == Decimal("0.10"),
            "unmapped tag reported as unassigned (0.10)",
            cc,
        )

        print("\n→ shared costs")
        bad_policy = api.call(
            "POST",
            "/billing/shared-cost-policies",
            a,
            {
                "name": "Platform team",
                "formula_type": "fixed_weight",
                "allocations": [
                    {"label": "Support", "cost_center_id": sup["id"], "weight": "0.7"},
                    {"label": "Platform", "cost_center_id": plat["id"], "weight": "0.2"},
                ],
            },
        )
        check(
            bad_policy.status_code == 422,
            "weights not summing to 1 refused (422)",
            bad_policy.status_code,
        )
        policy = api.call(
            "POST",
            "/billing/shared-cost-policies",
            a,
            {
                "name": "Platform team",
                "formula_type": "fixed_weight",
                "allocations": [
                    {"label": "Support", "cost_center_id": sup["id"], "weight": "0.7"},
                    {"label": "Platform", "cost_center_id": plat["id"], "weight": "0.3"},
                ],
            },
        ).json()
        api.call(
            "POST",
            f"/billing/shared-cost-policies/{policy['id']}/apply",
            a,
            {"period": month, "pool_usd": "100"},
        )
        again = api.call(
            "POST",
            f"/billing/shared-cost-policies/{policy['id']}/apply",
            a,
            {"period": month, "pool_usd": "50"},
        )
        check(
            again.status_code == 200 and _d(again.json()["total_usd"]) == Decimal("50"),
            "re-applying replaces the split",
            again.text,
        )
        allocs = api.call("GET", "/billing/cost-allocations", a, params={"period": month}).json()
        check(
            len(allocs["items"]) == 2 and _d(allocs["total_usd"]) == Decimal("50"),
            "two persisted lines total 50",
            allocs,
        )
        cc = api.call(
            "GET", "/billing/chargeback-report/cost-centers", a, params={"period": month}
        ).json()
        shared = {row["name"]: _d(row["shared_usd"]) for row in cc["rows"]}
        check(
            shared.get("Support") == Decimal("35") and shared.get("Platform") == Decimal("15"),
            "report shows shared 35 / 15",
            shared,
        )

        print("\n→ exports")
        exp = api.call(
            "GET",
            "/billing/chargeback-report/export",
            a,
            params={"period": month, "dimension": "end_user", "end_user_id": "=cmd"},
        )
        rows_csv = list(csv.DictReader(io.StringIO(exp.text)))
        check(len(rows_csv) == 1, "chargeback export honours end_user_id", exp.text[:200])
        check(
            all(not (v or "").startswith("=") for r in rows_csv for v in r.values()),
            "formula cells escaped",
            rows_csv,
        )

        print("\n→ adjustments and close")
        adj = api.call(
            "POST",
            f"/billing/periods/{period_id}/adjustments",
            a,
            {"adjustment_type": "credit", "amount_usd": "0.50", "description": "goodwill"},
        )
        check(
            adj.json().get("created_by") == f"billing-a-{suffix}@verify.test",
            "adjustment records who made it",
            adj.text,
        )
        closed = api.call("POST", f"/billing/periods/{period_id}/close", a)
        check(
            closed.status_code == 200 and closed.json()["signing_key_id"] == "ws-v1",
            "period closed and signed with the workspace key",
            closed.text,
        )
        snapshot_sig = closed.json().get("signature")
        closed_period = api.call("GET", f"/billing/periods/{period_id}", a).json()
        check(
            closed_period.get("closed_by") == f"billing-a-{suffix}@verify.test",
            "period records who closed it",
            closed_period.get("closed_by"),
        )
        check(
            api.call("POST", f"/billing/periods/{period_id}/close", a).status_code == 409,
            "second close refused (409)",
        )
        locked = api.call(
            "POST",
            f"/billing/periods/{period_id}/adjustments",
            a,
            {"adjustment_type": "credit", "amount_usd": "1"},
        )
        check(
            locked.status_code == 409,
            "adjustments locked on a closed period (409)",
            locked.status_code,
        )
        frozen_gross = _d(
            api.call("GET", f"/billing/periods/{period_id}/breakdown", a).json()["gross_cost_usd"]
        )

        api.http.post(
            "/ingest/v1/batch",
            headers=ingest,
            json={"events": _usage_events("support", "5.00", user="u-1")},
        )

        def support_cost() -> Decimal:
            items = report().get("breakdown", [])
            hit = next((i for i in items if i["dimension_key"] == "support"), None)
            return _d(hit["cost_usd"]) if hit else Decimal(0)

        landed = _wait(lambda: support_cost() == Decimal("8.20"))
        check(bool(landed), "late usage ingested into the closed month (support = 8.20)")
        late = api.call("GET", f"/billing/periods/{period_id}/breakdown", a).json()
        check(
            _d(late["gross_cost_usd"]) == frozen_gross and late.get("frozen") is True,
            "late usage leaves the closed bill unchanged",
            (frozen_gross, late.get("gross_cost_usd")),
        )
        recon = api.call("GET", f"/billing/periods/{period_id}/reconciliation", a).json()
        check(
            any("after close" in w for w in recon.get("warnings", [])),
            "reconciliation flags data after close",
            recon,
        )

        signed = api.call(
            "GET", f"/billing/periods/{period_id}/export", a, params={"format": "signed_json"}
        ).json()
        payload = {k: v for k, v in signed.items() if k not in ("signature", "signing_key_id")}
        ok = api.call(
            "POST",
            "/billing/verify",
            a,
            {
                "payload": payload,
                "signature": signed["signature"],
                "signing_key_id": signed["signing_key_id"],
            },
        )
        check(ok.json().get("valid") is True, "signed export verifies", ok.text)
        tampered = api.call(
            "POST",
            "/billing/verify",
            a,
            {
                "payload": {**payload, "total_cost_usd": "0.01"},
                "signature": signed["signature"],
                "signing_key_id": signed["signing_key_id"],
            },
        )
        check(tampered.json().get("valid") is False, "tampered export does not verify")
        key = api.call("GET", "/billing/signing-key", a).json()
        local = hmac.new(
            key["key"].encode(),
            json.dumps(payload, sort_keys=True, default=str).encode(),
            hashlib.sha256,
        ).hexdigest()
        check(local == signed["signature"], "verifiable offline with the workspace key")
        other_ws = api.call(
            "POST",
            "/billing/verify",
            platform,
            {"payload": payload, "signature": signed["signature"], "signing_key_id": "ws-v1"},
        )
        check(
            other_ws.status_code == 200 and other_ws.json().get("valid") is False,
            "another workspace's key does not verify it",
        )

        print("\n→ billing summary")
        summary = api.call("GET", "/budgets/billing-summary", a, params={"months": 1}).json()
        this_month = next((p for p in summary.get("periods", []) if p["period"] == month), {})
        check(
            this_month.get("billable_calls", 0) >= 8
            and _d(this_month.get("billable_cost_usd", 0))
            == _d(this_month.get("total_cost_usd", -1)),
            "summary counts billable calls and cost from usage (not a constant)",
            this_month,
        )

        print("\n→ budget webhook signing")
        hook = api.call(
            "POST",
            "/budgets/notifications",
            a,
            {"channel": "webhook", "destination_url": "https://example.com/runledger-hook"},
        )
        if check(hook.status_code in (200, 201), "webhook destination created", hook.text):
            hook_id = hook.json()["id"]
            s1 = api.call("GET", f"/budgets/notifications/{hook_id}/signing-secret", a).json()
            s2 = api.call(
                "POST", f"/budgets/notifications/{hook_id}/signing-secret/rotate", a
            ).json()
            check(
                bool(s1.get("secret")) and bool(s2.get("secret")) and s1["secret"] != s2["secret"],
                "each destination has its own secret, and rotating changes it",
                (s1, s2),
            )
            check(s1.get("secret") != key["key"], "webhook secret differs from the billing key")

        print("\n→ reopen and rotate")
        no_reason = api.call("POST", f"/billing/periods/{period_id}/reopen", a, {})
        check(no_reason.status_code == 422, "reopen needs a reason (422)", no_reason.status_code)
        reopened = api.call(
            "POST", f"/billing/periods/{period_id}/reopen", a, {"reason": "late usage"}
        )
        check(reopened.json().get("status") == "open", "period reopened", reopened.text)
        api.call("POST", f"/billing/periods/{period_id}/close", a).raise_for_status()
        regross = _d(
            api.call("GET", f"/billing/periods/{period_id}/breakdown", a).json()["gross_cost_usd"]
        )
        check(
            regross == frozen_gross + Decimal("5"),
            "closing again includes the late usage",
            (frozen_gross, regross),
        )
        rotated = api.call("POST", "/billing/signing-key/rotate", a).json()
        check(rotated.get("signing_key_id") == "ws-v2", "signing key rotated to ws-v2", rotated)
        old = api.call(
            "POST",
            "/billing/verify",
            a,
            {"payload": payload, "signature": signed["signature"], "signing_key_id": "ws-v1"},
        )
        check(old.json().get("valid") is True, "old export still verifies after rotation", old.text)
        _ = snapshot_sig
    finally:
        if not args.keep:
            api.call(
                "DELETE", f"/org/tenants/{org_data['id']}", platform, {"confirmation": org_name}
            )

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
        "--keep", action="store_true", help="Keep the throwaway org for inspection."
    )
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
