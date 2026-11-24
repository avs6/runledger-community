#!/usr/bin/env python3
"""End-to-end verification of tool governance, approvals, capture and auto-tags.

Replays what a governance owner does against a running API and asserts each step
(review S-01, cd:S-04, S-06, S-07, S-08, S-09, S-19, S-21, S-26; approvals as holds; ENH simulator):

  1. Signs in and mints a throwaway workload key.
  2. Refuses an unenforceable policy (422).
  3. Creates ``block`` / ``allow`` / ``require_approval`` policies for unique tool names and
     asserts /tools/check, /policies/check and the dry run all agree (one evaluator).
  4. Priority: a narrow ``allow`` at 10 beats a ``block <prefix>_*`` at 1000.
  5. Approval hold: /tools/check returns 403 + a real approval id; once approved, the
     same check with ?approval_id= passes.
  6. Registry: a registry ``block`` is enforced and appears as the managed policy.
  7. MCP: a blocked MCP call returns 403 and is logged as ``blocked``; an allowed call to
     a stdio server is logged honestly as ``not_executed``; a held call returns 202.
  8. Ingest: tool calls for a unique workflow are ingested, then the policy simulator
     replays them against a draft ``block`` and must report them as newly blocked.
  9. Auto-tag rule applied at ingest: the run carries ``metadata.auto_tags``.
 10. Optional (--gateway-url + --alias): a gateway request whose tools[] include an
     approval-required tool is held with 202 + X-RunLedger-Approval-Id.

Everything it creates is removed at the end (pass --keep to inspect it in the UI).
Needs the API, Redis and the Celery pipeline worker running.

Usage:
    python scripts/run_demo.py verify-governance
    python scripts/core/verify_governance.py --base-url http://localhost:8201 \\
        --gateway-url http://localhost:8210 --alias smart
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passed = 0
        self.skipped: list[str] = []

    def __call__(self, ok: bool, label: str, detail: Any = "") -> None:
        if ok:
            self.passed += 1
            print(f"  ✓ {label}")
        else:
            self.failures.append(label)
            print(f"  ✗ {label} {detail}")

    def skip(self, label: str, why: str) -> None:
        self.skipped.append(label)
        print(f"  - {label} (skipped: {why})")


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


def _iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _run_with_tool_calls(feature: str, tool: str, calls: int) -> tuple[str, list[dict[str, Any]]]:
    run_id = str(uuid.uuid4())
    events: list[dict[str, Any]] = [
        {
            "event_type": "run_start",
            "run_id": run_id,
            "started_at": _iso(),
            "feature_tag": feature,
            "end_user_id": f"{feature}-user",
            "metadata": {"env": "verify"},
        }
    ]
    for _ in range(calls):
        events.append(
            {
                "event_type": "tool_call",
                # Distinct ids: content-identical events without one dedupe on ingest.
                "tool_call_id": str(uuid.uuid4()),
                "run_id": run_id,
                "tool_name": tool,
                "tool_type": "write",
                "status": "success",
                "duration_ms": 12,
            }
        )
    events.append(
        {"event_type": "run_end", "run_id": run_id, "status": "succeeded", "ended_at": _iso()}
    )
    return run_id, events


def run(args: argparse.Namespace) -> int:  # noqa: PLR0915 - a linear scenario reads best
    api = Api(args.base_url)
    check = Check()
    sfx = uuid.uuid4().hex[:8]
    prefix = f"vg{sfx}"
    feature = f"verify-governance-{sfx}"

    login = api.call("POST", "/auth/login", body={"email": args.email, "password": args.password})
    if login.status_code != 200:
        print(f"Sign-in failed ({login.status_code}): {login.text}")
        return 2
    admin = login.json()["api_key"]
    key_resp = api.call("POST", "/settings/api-keys", admin, {"name": f"verify-governance-{sfx}"})
    if key_resp.status_code not in (200, 201):
        print(f"API key creation failed ({key_resp.status_code}): {key_resp.text}")
        return 2
    key_id, key = key_resp.json()["id"], key_resp.json()["key"]

    policy_ids: list[str] = []
    rule_ids: list[str] = []
    registry_tools: list[str] = []
    server_ids: list[str] = []

    def policy(body: dict[str, Any]) -> dict[str, Any]:
        resp = api.call("POST", "/tool-policies", admin, body)
        check(resp.status_code == 201, f"create policy {body['name']}", resp.text[:200])
        data = resp.json() if resp.status_code == 201 else {}
        if data.get("id"):
            policy_ids.append(data["id"])
        return data

    try:
        print("\n→ validation (no decorative policies)")
        bad = api.call(
            "POST",
            "/tool-policies",
            admin,
            {"name": "bad", "tool_name": "x", "action": "block", "scope_type": "access_group"},
        )
        check(bad.status_code == 422, "access_group scope without scope_id is refused", bad.text)

        print("\n→ one evaluator: /tools/check, /policies/check and the dry run agree")
        shell = f"{prefix}_shell"
        policy(
            {
                "name": f"{prefix} deny all",
                "tool_name": f"{prefix}_*",
                "action": "block",
                "priority": 1000,
            }
        )
        policy(
            {
                "name": f"{prefix} allow search",
                "tool_name": f"{prefix}_search",
                "action": "allow",
                "priority": 10,
            }
        )
        r = api.call("GET", f"/tools/check/{shell}", key)
        check(r.status_code == 403, f"/tools/check blocks {shell}", r.status_code)
        r = api.call("POST", "/policies/check", key, {"tool_name": shell})
        check(
            r.status_code == 200
            and r.json()["decision"] == "block"
            and r.json()["tool_policy"] == "block",
            "/policies/check blocks the same tool",
            r.text[:200],
        )
        r = api.call("POST", "/tool-policies/simulate", admin, {"tool_name": shell})
        check(r.json().get("final_action") == "block", "dry run decides block", r.text[:200])
        r = api.call("GET", f"/tools/check/{prefix}_search", key)
        check(r.status_code == 200, "allow at priority 10 beats block * at 1000", r.status_code)

        print("\n→ approval hold")
        wire = f"{prefix}_wire"
        policy(
            {
                "name": f"{prefix} wire approval",
                "tool_name": wire,
                "action": "require_approval",
                "priority": 5,
            }
        )
        r = api.call("GET", f"/tools/check/{wire}", key)
        approval_id = r.headers.get("x-runledger-approval-id")
        check(r.status_code == 403 and bool(approval_id), "held with an approval id", r.status_code)
        if approval_id:
            a = api.call("GET", f"/approvals/{approval_id}", admin)
            check(
                a.status_code == 200 and a.json().get("status") == "pending",
                "the approval is a real pending row",
                a.text[:200],
            )
            ok = api.call("POST", f"/approvals/{approval_id}/approve", admin, {"note": "verify"})
            if ok.status_code == 200:
                r = api.call(
                    "GET", f"/tools/check/{wire}", key, params={"approval_id": approval_id}
                )
                check(
                    r.status_code == 200, "approved call passes with ?approval_id=", r.status_code
                )
            else:
                check.skip(
                    "approved call passes",
                    f"approve returned {ok.status_code} (separation of duties?)",
                )

        print("\n→ registry policy is a managed ToolPolicy")
        reg_tool = f"{prefix}x_registry"
        r = api.call("POST", "/tools/registry", admin, {"tool_name": reg_tool, "policy": "block"})
        check(r.status_code == 201, "register tool with policy block", r.text[:200])
        if r.status_code == 201:
            registry_tools.append(reg_tool)
            check(
                r.json().get("effective_action") == "block", "effective decision is block", r.json()
            )
        r = api.call("GET", f"/tools/check/{reg_tool}", key)
        check(r.status_code == 403, "registry block enforced by /tools/check", r.status_code)
        listed = api.call("GET", "/tool-policies", admin, params={"tool_name": reg_tool}).json()
        check(
            any(p["name"] == f"registry:{reg_tool}" for p in listed.get("items", [])),
            "managed policy registry:<tool> is listed",
        )

        print("\n→ governed MCP calls")
        srv = api.call(
            "POST",
            "/mcp-registry",
            admin,
            {
                "name": f"{prefix}-stdio",
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "x"],
            },
        )
        check(srv.status_code == 201, "register stdio MCP server", srv.text[:200])
        if srv.status_code == 201:
            server_id = srv.json()["id"]
            server_ids.append(server_id)
            r = api.call(
                "POST",
                "/mcp-registry/tools/call",
                key,
                {"server_id": server_id, "tool_name": shell},
            )
            check(r.status_code == 403, "blocked MCP call returns 403", r.status_code)
            r = api.call(
                "POST",
                "/mcp-registry/tools/call",
                key,
                {"server_id": server_id, "tool_name": f"{prefix}_search"},
            )
            check(
                r.status_code == 200 and r.json()["status"] == "not_executed",
                "allowed call to a stdio server is logged honestly as not_executed",
                r.text[:200],
            )
            r = api.call(
                "POST", "/mcp-registry/tools/call", key, {"server_id": server_id, "tool_name": wire}
            )
            check(
                r.status_code == 202
                and r.json()["status"] == "pending_approval"
                and r.json().get("approval_id"),
                "approval-required MCP call is held (202)",
                r.text[:200],
            )
            calls = api.call(
                "GET", "/mcp-registry/tool-calls", admin, params={"server_id": server_id}
            ).json()
            statuses = {c["status"] for c in calls.get("items", [])}
            check(
                {"blocked", "not_executed", "pending_approval"} <= statuses,
                "call log has real statuses",
                statuses,
            )

        print("\n→ auto-tag rule at ingest")
        rr = api.call(
            "POST",
            "/tags/auto-rules",
            admin,
            {
                "name": f"{prefix} team",
                "match_type": "prefix",
                "match_field": "feature_tag",
                "match_pattern": "verify-governance-",
                "tag_key": "team",
                "tag_value": "governance",
                "priority": 1,
            },
        )
        check(rr.status_code == 201, "create auto-tag rule", rr.text[:200])
        if rr.status_code == 201:
            rule_ids.append(rr.json()["id"])

        print("\n→ ingest tool calls, then replay them in the policy simulator")
        replay_tool = f"{prefix}x_replay"
        run_id, events = _run_with_tool_calls(feature, replay_tool, 3)
        ing = api.call("POST", "/ingest/v1/batch", key, {"events": events})
        check(ing.status_code in (200, 202), "ingest batch accepted", ing.text[:200])
        impact: dict[str, Any] = {}
        run_meta: dict[str, Any] = {}
        for _ in range(args.wait):
            time.sleep(1)
            impact = api.call(
                "POST",
                "/tool-policies/simulate-impact",
                admin,
                {
                    "days": 1,
                    "policy": {"name": "draft", "tool_name": replay_tool, "action": "block"},
                },
            ).json()
            run_resp = api.call("GET", f"/runs/{run_id}", admin)
            run_meta = (
                (run_resp.json().get("metadata") or {}) if run_resp.status_code == 200 else {}
            )
            if impact.get("newly_blocked", 0) >= 3 and run_meta:
                break
        check(
            impact.get("newly_blocked", 0) >= 3,
            "simulator reports the 3 calls as newly blocked",
            impact,
        )
        check(
            any(row.get("tool_name") == replay_tool for row in impact.get("by_tool", [])),
            "simulator breaks impact down by tool",
        )
        check(
            (run_meta.get("auto_tags") or {}).get("team") == "governance",
            "run carries auto_tags from the rule",
            run_meta,
        )

        print("\n→ gateway hold (optional)")
        if args.gateway_url and args.alias:
            gw = httpx.post(
                f"{args.gateway_url.rstrip('/')}/gateway/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": args.alias,
                    "messages": [{"role": "user", "content": "send the money"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": wire, "parameters": {"type": "object"}},
                        }
                    ],
                },
                timeout=60,
            )
            check(
                gw.status_code == 202 and bool(gw.headers.get("x-runledger-approval-id")),
                "gateway holds a request with an approval-required tool (202)",
                f"{gw.status_code} {gw.text[:200]}",
            )
        else:
            check.skip("gateway hold", "pass --gateway-url and --alias")
    finally:
        if not args.keep:
            for pid in policy_ids:
                api.call("DELETE", f"/tool-policies/{pid}", admin)
            for rid in rule_ids:
                api.call("DELETE", f"/tags/auto-rules/{rid}", admin)
            for tool in registry_tools:
                api.call("DELETE", f"/tools/registry/{tool}", admin)
            for sid in server_ids:
                api.call("DELETE", f"/mcp-registry/{sid}", admin)
            api.call("DELETE", f"/settings/api-keys/{key_id}", admin)

    print(f"\n{check.passed} passed, {len(check.failures)} failed, {len(check.skipped)} skipped")
    for failure in check.failures:
        print(f"  FAILED: {failure}")
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
    parser.add_argument("--wait", type=int, default=30, help="Seconds to wait for the pipeline.")
    parser.add_argument("--keep", action="store_true", help="Keep what the run created.")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
