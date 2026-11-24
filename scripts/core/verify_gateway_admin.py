#!/usr/bin/env python3
"""End-to-end verification of gateway administration against a running API (stream W1-C).

Replays what a gateway admin does and asserts every step:

  1. Signs in and mints a throwaway workload API key.
  2. Role matrix: the session sees its capabilities; the workload key reads but can't change.
  3. Routes: creates a routing group and a route in it for a unique alias, then asserts
     - renaming the grouped route's alias is refused (400) and renaming the group is refused (409);
     - a merge-mode edit of fallback_config keeps the keys it didn't send;
     - preview-change returns the diff without saving;
     - the test-request dry run selects the route and reports cost and latency fields.
  4. Policies: a policy naming a route of another alias is refused (422); an unknown
     policy_type on update is refused (422).
  5. Budget tiers: creates a tier with allowed_models and rpm_limit, assigns it to the key,
     clears rpm_limit with null, then deletes it and asserts it is inactive and not default.
     Optional (--gateway-url): a request for a model outside allowed_models gets 403.
  6. Pricing sync: dry run returns the catalog summary (platform admins; skipped otherwise).
  7. Audit: the route, policy-free and tier changes above appear in /audit/events.

Everything created is deleted at the end (pass --keep to inspect it in the UI).

Usage:
    python scripts/run_demo.py verify-gateway-admin
    python scripts/core/verify_gateway_admin.py --base-url http://localhost:8201 \\
        --gateway-url http://localhost:8210
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passed = 0

    def __call__(self, ok: bool, label: str, detail: Any = "") -> bool:
        if ok:
            self.passed += 1
            print(f"  ✓ {label}")
        else:
            self.failures.append(label)
            print(f"  ✗ {label} {detail}")
        return ok


class Api:
    def __init__(self, base_url: str) -> None:
        self.http = httpx.Client(base_url=base_url.rstrip("/"), timeout=30)

    def call(
        self, method: str, path: str, key: str | None = None, body: dict[str, Any] | None = None
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        return self.http.request(method, path, headers=headers, json=body)


def run(args: argparse.Namespace) -> int:
    api = Api(args.base_url)
    check = Check()
    suffix = uuid.uuid4().hex[:8]
    alias = f"verify-gw-{suffix}"
    other_alias = f"verify-gw-other-{suffix}"

    login = api.call("POST", "/auth/login", body={"email": args.email, "password": args.password})
    if login.status_code != 200:
        print(f"Sign-in failed ({login.status_code}): {login.text}")
        return 2
    session = login.json()["api_key"]
    key_resp = api.call("POST", "/settings/api-keys", session, {"name": f"verify-gw-{suffix}"})
    if key_resp.status_code not in (200, 201):
        print(f"API key creation failed ({key_resp.status_code}): {key_resp.text}")
        return 2
    key_id, raw_key = key_resp.json()["id"], key_resp.json()["key"]

    created: dict[str, list[str]] = {"routes": [], "groups": [], "policies": [], "tiers": []}
    try:
        print("\n→ role matrix")
        rm = api.call("GET", "/gateway/role-matrix", session)
        check(rm.status_code == 200, "session reads the role matrix", rm.text)
        body = rm.json() if rm.status_code == 200 else {}
        check(
            body.get("matrix", {}).get("flywheel", {}).get("apply") == "org_admin",
            "flywheel apply needs an org admin",
        )
        wl = api.call("GET", "/gateway/role-matrix", raw_key).json()
        check(wl.get("caller_level") == "workload", "workload key is reported as workload", wl)
        check(
            wl.get("capabilities", {}).get("routes", {}).get("write") is False,
            "workload key can't change routes",
        )
        denied = api.call(
            "POST",
            "/gateway/routes",
            raw_key,
            {"alias": alias, "provider": "ollama", "target_model": "llama3"},
        )
        check(
            denied.status_code in (401, 403),
            "workload key is refused on route create",
            denied.status_code,
        )

        print("\n→ routes, groups and invariants")
        group = api.call(
            "POST",
            "/gateway/routing-groups",
            session,
            {"alias": alias, "name": f"verify group {suffix}"},
        )
        check(group.status_code == 201, "routing group created", group.text)
        group_id = group.json()["id"]
        created["groups"].append(group_id)
        route = api.call(
            "POST",
            "/gateway/routes",
            session,
            {
                "alias": alias,
                "provider": "ollama",
                "target_model": "llama3.1:8b",
                "routing_group_id": group_id,
                "fallback_config": {
                    "aliases": ["a"],
                    "fallbacks": [{"alias": "big", "on": ["context_window"]}],
                },
            },
        )
        check(route.status_code == 201, "route created in the group", route.text)
        route_id = route.json()["id"]
        created["routes"].append(route_id)
        other = api.call(
            "POST",
            "/gateway/routes",
            session,
            {"alias": other_alias, "provider": "ollama", "target_model": "llama3.1:8b"},
        )
        check(other.status_code == 201, "second route for another alias", other.text)
        other_id = other.json()["id"]
        created["routes"].append(other_id)

        r = api.call("PUT", f"/gateway/routes/{route_id}", session, {"alias": f"{alias}-x"})
        check(
            r.status_code == 400, "renaming a grouped route's alias is refused (400)", r.status_code
        )
        r = api.call("PUT", f"/gateway/routing-groups/{group_id}", session, {"alias": f"{alias}-x"})
        check(r.status_code == 409, "renaming a group with routes is refused (409)", r.status_code)

        r = api.call(
            "PUT",
            f"/gateway/routes/{route_id}",
            session,
            {"merge_configs": True, "fallback_config": {"aliases": ["b"]}},
        )
        cfg = r.json().get("fallback_config") or {} if r.status_code == 200 else {}
        check(
            r.status_code == 200 and cfg.get("aliases") == ["b"],
            "merge edit replaced aliases",
            r.text,
        )
        check(
            cfg.get("fallbacks") == [{"alias": "big", "on": ["context_window"]}],
            "merge edit kept the fallback rules it didn't send",
            cfg,
        )

        pv = api.call(
            "POST",
            f"/gateway/routes/{route_id}/preview-change",
            session,
            {"target_model": "llama3.2:3b", "is_active": False},
        )
        fields = (
            {c["field"] for c in pv.json().get("changes", [])} if pv.status_code == 200 else set()
        )
        check(fields == {"target_model", "is_active"}, "preview-change lists the diff", pv.text)
        check(
            bool(pv.json().get("warnings")) if pv.status_code == 200 else False,
            "preview-change warns that the route stops serving",
        )
        still = api.call("GET", f"/gateway/routes/{route_id}", session).json()
        check(
            still.get("target_model") == "llama3.1:8b" and still.get("is_active") is True,
            "preview-change saved nothing",
        )

        test = api.call(
            "POST", "/gateway/routes/preview", session, {"model": alias, "prompt": "hi"}
        )
        tb = test.json() if test.status_code == 200 else {}
        check(
            test.status_code == 200 and tb.get("selected_route_id") == route_id,
            "test request selects the route",
            test.text,
        )
        check(
            "est_cost_usd" in tb and "p50_latency_ms" in tb, "test request reports cost and latency"
        )

        print("\n→ routing policies")
        r = api.call(
            "POST",
            "/gateway/policies",
            session,
            {"alias": alias, "policy_type": "weighted", "config": {"weights": {other_id: 1}}},
        )
        check(
            r.status_code == 422,
            "policy naming another alias's route is refused (422)",
            r.status_code,
        )
        pol = api.call(
            "POST",
            "/gateway/policies",
            session,
            {"alias": alias, "policy_type": "weighted", "config": {"weights": {route_id: 1}}},
        )
        check(pol.status_code == 201, "policy with its own route is accepted", pol.text)
        if pol.status_code == 201:
            created["policies"].append(pol.json()["id"])
            r = api.call(
                "PUT",
                f"/gateway/policies/{pol.json()['id']}",
                session,
                {"policy_type": "random_pick"},
            )
            check(
                r.status_code == 422,
                "unknown policy_type on update is refused (422)",
                r.status_code,
            )

        print("\n→ budget tiers")
        tier = api.call(
            "POST",
            "/budget-tiers",
            session,
            {
                "name": f"verify-tier-{suffix}",
                "rpm_limit": 1000,
                "allowed_models": [alias],
            },
        )
        check(tier.status_code == 201, "tier created", tier.text)
        tier_id = tier.json()["id"]
        created["tiers"].append(tier_id)
        r = api.call("PUT", f"/budget-tiers/assign/{key_id}?tier_id={tier_id}", session)
        check(r.status_code == 200, "tier assigned to the key", r.text)
        r = api.call("PUT", f"/budget-tiers/{tier_id}", session, {"rpm_limit": None})
        check(
            r.status_code == 200 and r.json().get("rpm_limit") is None,
            "null clears rpm_limit",
            r.text,
        )
        if args.gateway_url:
            gw = httpx.post(
                f"{args.gateway_url.rstrip('/')}/v1/chat/completions",
                headers={"Authorization": f"Bearer {raw_key}"},
                json={"model": other_alias, "messages": [{"role": "user", "content": "hi"}]},
                timeout=30,
            )
            check(
                gw.status_code == 403,
                "gateway refuses a model outside allowed_models (403)",
                f"{gw.status_code} {gw.text[:200]}",
            )
        r = api.call("DELETE", f"/budget-tiers/{tier_id}", session)
        check(r.status_code == 204, "tier deleted", r.status_code)
        gone = api.call("GET", f"/budget-tiers/{tier_id}", session).json()
        check(
            gone.get("is_active") is False and gone.get("is_default") is False,
            "deleted tier is inactive and not default",
            gone,
        )

        print("\n→ pricing sync")
        sync = api.call("POST", "/providers/pricing/sync", session, {"dry_run": True})
        if sync.status_code == 403:
            print("  · skipped (needs a platform admin)")
        else:
            check(
                sync.status_code == 200 and sync.json().get("total", 0) > 0,
                "dry-run sync parses the deployment catalog",
                sync.text[:200],
            )

        print("\n→ audit trail")
        for action in (
            "gateway_route.updated",
            "gateway_routing_group.created",
            "budget_tier.deleted",
            "budget_tier.assigned",
            "gateway_policy.created",
        ):
            ev = api.call("GET", f"/audit/events?action={action}&limit=50", session)
            items = ev.json().get("items", []) if ev.status_code == 200 else []
            check(
                any(i.get("action") == action for i in items), f"audit has {action}", ev.status_code
            )
    finally:
        if not args.keep:
            for pid in created["policies"]:
                api.call("DELETE", f"/gateway/policies/{pid}", session)
            for rid in created["routes"]:
                api.call("DELETE", f"/gateway/routes/{rid}", session)
            for gid in created["groups"]:
                api.call("DELETE", f"/gateway/routing-groups/{gid}", session)
            for tid in created["tiers"]:
                api.call("DELETE", f"/budget-tiers/{tid}", session)
            api.call("DELETE", f"/settings/api-keys/{key_id}", session)

    print(f"\n{check.passed} passed, {len(check.failures)} failed")
    return 1 if check.failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--base-url", default=os.getenv("RUNLEDGER_API_URL", "http://localhost:8201")
    )
    parser.add_argument("--gateway-url", default=os.getenv("RUNLEDGER_GATEWAY_URL"))
    parser.add_argument(
        "--email", default=os.getenv("RUNLEDGER_PLATFORM_EMAIL", "admin@runledger.local")
    )
    parser.add_argument("--password", default=os.getenv("RUNLEDGER_PLATFORM_PASSWORD", "runledger"))
    parser.add_argument("--keep", action="store_true", help="Keep what was created")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
