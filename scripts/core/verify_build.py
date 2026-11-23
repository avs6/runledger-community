#!/usr/bin/env python3
"""End-to-end verification of the Build area (prompts, experiments, Playground, judge,
runbooks, vector search, agent memory) against a running API and gateway.

Replays what a builder does and asserts every step:

  1. Prompt governance (review B-02, B-03): a new version lands in dev; writing to
     production without an approval is 403; a promotion request goes through the
     approvals queue; promoting with the approved request works once, and reusing
     that approval is 409. The diff and score endpoints answer.
  2. Playground (B-10): models come from gateway route aliases; a send goes through
     gateway-rs and records either a real reply with a run id or the gateway's
     refusal, never a placeholder.
  3. Experiments (B-07, B-08): a two-item dataset runs through the gateway against
     one alias with ``?wait=true``; the result says ``via=gateway`` and counts the
     calls. Replay datasets are curated from the Playground run when it has a
     captured conversation.
  4. LLM judge (B-09): a judge config carrying a provider key or base_url is 422.
  5. Runbooks (B-12): generate for a run, export Markdown, delete.
  6. Vector search (B-19): search-test either returns hits or an explicit 503, and a
     503 leaves the query counter unchanged.
  7. Agent memory (B-16): a duplicate key is 409, ``upsert`` overwrites, a PII value
     round-trips.

Steps that need a gateway route are skipped (and reported) when the workspace has
no active alias. Everything created is deleted at the end unless --keep is passed.

Usage:
    python scripts/run_demo.py verify-build
    python scripts/core/verify_build.py --base-url http://localhost:8201 --alias smart
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
        self.skipped: list[str] = []
        self.passed = 0

    def __call__(self, ok: bool, label: str, detail: Any = "") -> bool:
        if ok:
            self.passed += 1
            print(f"  ✓ {label}")
        else:
            self.failures.append(label)
            print(f"  ✗ {label} {detail}")
        return ok

    def skip(self, label: str, why: str) -> None:
        self.skipped.append(label)
        print(f"  - {label} (skipped: {why})")


class Api:
    def __init__(self, base_url: str, key: str | None = None) -> None:
        self.http = httpx.Client(base_url=base_url.rstrip("/"), timeout=180)
        self.key = key

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        return self.http.request(method, path, headers=headers, json=body)


def verify_prompts(api: Api, check: Check, suffix: str, cleanup: list[tuple[str, str]]) -> None:
    print("\n1. Prompt governance")
    name = f"verify-build-{suffix}"
    r = api.call("POST", "/prompts", {"name": name, "description": "verify_build"})
    if not check(r.status_code == 201, "create prompt", r.text):
        return
    cleanup.append(("DELETE", f"/prompts/{name}"))
    check(r.json()["default_environment"] == "dev", "prompt defaults to dev")

    r = api.call(
        "POST", f"/prompts/{name}/versions", {"content": "You are terse.\nAnswer briefly."}
    )
    check(
        r.status_code == 201 and r.json()["environment"] == "dev",
        "new version lands in dev",
        r.text,
    )
    r = api.call(
        "POST", f"/prompts/{name}/versions", {"content": "Bypass", "environment": "production"}
    )
    check(r.status_code == 403, "production version without approval is 403", r.status_code)

    r = api.call(
        "POST",
        f"/prompts/{name}/versions",
        {"content": "You are terse.\nAnswer in one line.", "environment": "staging"},
    )
    check(r.status_code == 201 and r.json()["environment"] == "staging", "staging version", r.text)
    staging_version = r.json().get("version")

    r = api.call("GET", f"/prompts/{name}/diff?from=1&to={staging_version}")
    check(
        r.status_code == 200 and r.json()["added"] >= 1 and r.json()["removed"] >= 1,
        "diff reports added and removed lines",
        r.text,
    )
    r = api.call("GET", f"/prompts/{name}/versions/{staging_version}/score")
    check(r.status_code == 200 and "passes_gate" in r.json(), "version score endpoint", r.text)

    r = api.call(
        "POST",
        f"/prompts/{name}/promotion-requests",
        {"source_environment": "staging", "reason": "verify_build"},
    )
    if not check(r.status_code == 201, "promotion request creates an approval", r.text):
        return
    approval = r.json()
    check(approval["version"] == staging_version, "approval pins the staging version")
    if approval["status"] == "pending":
        d = api.call("POST", f"/approvals/{approval['id']}/approve", {"note": "verify_build"})
        if d.status_code != 200:
            check.skip(
                "promote with approval",
                f"could not approve as this user ({d.status_code}); separation of duties?",
            )
            api.call("POST", f"/approvals/{approval['id']}/cancel")
            return
    r = api.call(
        "POST",
        f"/prompts/{name}/promote",
        {
            "source_environment": "staging",
            "target_environment": "production",
            "approval_id": approval["id"],
        },
    )
    check(
        r.status_code == 201 and r.json()["environment"] == "production",
        "promote with an approved request",
        r.text,
    )
    r = api.call(
        "POST",
        f"/prompts/{name}/promote",
        {
            "source_environment": "staging",
            "target_environment": "production",
            "approval_id": approval["id"],
        },
    )
    check(r.status_code == 409, "an approval authorises one production version", r.status_code)
    r = api.call("GET", f"/prompts/{name}/promotion-requests")
    used = [a for a in r.json().get("items", []) if a["id"] == approval["id"]]
    check(
        bool(used) and used[0]["used_by_version"] is not None,
        "request shows the version it was used for",
    )


def pick_alias(api: Api, check: Check, wanted: str | None) -> str | None:
    r = api.call("GET", "/playground/models")
    check(r.status_code == 200, "playground models come from route aliases", r.text)
    aliases = [m["alias"] for m in r.json().get("items", [])] if r.status_code == 200 else []
    if wanted:
        return wanted if wanted in aliases else None
    return aliases[0] if aliases else None


def verify_playground(api: Api, check: Check, alias: str | None) -> str | None:
    print("\n2. Playground through the gateway")
    if alias is None:
        check.skip("playground send", "no active gateway route alias")
        return None
    r = api.call(
        "POST",
        "/playground/send",
        {
            "model": alias,
            "user_prompt": "Reply with the single word: pong",
            "parameters": {"max_tokens": 16},
        },
    )
    if not check(r.status_code == 201, "playground send accepted", r.text):
        return None
    body = r.json()
    check("integration pending" not in (body.get("response_text") or ""), "no placeholder response")
    if body["status"] == "completed":
        check(bool(body.get("run_id")), "completed send links the recorded run", body)
        return body.get("run_id")
    check(bool(body.get("error")), "a refused send records the gateway's reason", body)
    return None


def verify_experiments(
    api: Api, check: Check, alias: str | None, run_id: str | None, cleanup: list[tuple[str, str]]
) -> None:
    print("\n3. Experiments through the gateway")
    r = api.call(
        "POST",
        "/datasets",
        {
            "name": "verify-build",
            "items": [
                {"input": "What is 2+2? Answer with a number.", "expected_output": "4"},
                {"input": "Capital of France? One word.", "expected_output": "Paris"},
            ],
        },
    )
    if not check(r.status_code == 201, "create eval dataset", r.text):
        return
    ds_id = r.json()["id"]
    cleanup.append(("DELETE", f"/datasets/{ds_id}"))
    if alias is None:
        check.skip("run experiment", "no active gateway route alias")
        return
    r = api.call(
        "POST",
        "/experiments",
        {"name": "verify-build", "mode": "eval", "dataset_id": ds_id, "models": [{"model": alias}]},
    )
    if not check(r.status_code == 201 and r.json()["mode"] == "eval", "create experiment", r.text):
        return
    exp_id = r.json()["id"]
    cleanup.append(("DELETE", f"/experiments/{exp_id}"))
    r = api.call("POST", f"/experiments/{exp_id}/run?wait=true")
    ok = r.status_code == 200 and r.json()["status"] == "completed"
    check(ok, "experiment completes", r.text[:300])
    if ok:
        summary = r.json()["results"]["summary"]
        check(summary["via"] == "gateway", "results come from the gateway")
        check(summary["calls"] == 2, "one gateway call per item", summary)
        check(r.json()["run_count"] == 2, "run_count matches calls")

    if run_id:
        r = api.call("POST", "/datasets/from-runs", {"name": "verify-replay", "run_ids": [run_id]})
        if r.status_code == 201:
            cleanup.append(("DELETE", f"/datasets/{r.json()['id']}"))
            check(r.json()["source"] == "runs", "replay dataset curated from a run")
        else:
            check(r.status_code == 422, "uncaptured run is refused honestly", r.text)


def verify_judge(api: Api, check: Check, alias: str | None) -> None:
    print("\n4. Gateway-backed LLM judge")
    r = api.call(
        "POST",
        "/evaluations/evaluators",
        {
            "name": "verify-bad-judge",
            "type": "llm_judge",
            "config": {
                "model": alias or "any",
                "api_key": "sk-x",
                "base_url": "http://169.254.169.254",
            },
        },
    )
    check(r.status_code in (403, 422), "judge with provider key/base_url is refused", r.status_code)


def verify_runbooks(api: Api, check: Check, run_id: str | None) -> None:
    print("\n5. Runbooks")
    if run_id is None:
        check.skip("runbook export/delete", "no recorded run from the Playground step")
        return
    r = api.call("POST", f"/runs/{run_id}/runbook")
    if not check(r.status_code == 201, "generate runbook", r.text):
        return
    rb_id = r.json()["id"]
    r = api.call("GET", f"/runbooks/{rb_id}/export?format=md")
    check(r.status_code == 200 and r.text.startswith("# Runbook"), "export Markdown")
    r = api.call("GET", f"/runbooks/{rb_id}")
    check(r.status_code == 200, "get runbook")
    r = api.call("DELETE", f"/runbooks/{rb_id}")
    check(r.status_code == 204, "delete runbook", r.status_code)
    r = api.call("GET", f"/runbooks/{rb_id}")
    check(r.status_code == 404, "deleted runbook is gone")


def verify_vector(api: Api, check: Check, suffix: str, cleanup: list[tuple[str, str]]) -> None:
    print("\n6. Vector search")
    r = api.call(
        "POST",
        "/vector-stores",
        {"name": f"verify-{suffix}", "qdrant_collection": f"verify_build_{suffix}"},
    )
    if not check(r.status_code == 201, "register collection", r.text):
        return
    cid = r.json()["id"]
    cleanup.append(("DELETE", f"/vector-stores/{cid}"))
    before = r.json()["total_queries"]
    r = api.call("POST", f"/vector-stores/{cid}/search-test", {"query": "hello", "top_k": 3})
    after = api.call("GET", f"/vector-stores/{cid}").json()["total_queries"]
    if r.status_code == 503:
        check(after == before, "an unavailable search records nothing", (before, after))
    else:
        check(r.status_code == 200 and after == before + 1, "search runs and is counted", r.text)


def verify_memory(api: Api, check: Check, suffix: str, cleanup: list[tuple[str, str]]) -> None:
    print("\n7. Agent memory")
    r = api.call("POST", "/agents", {"name": f"verify-build-{suffix}"})
    if not check(r.status_code == 201, "create agent", r.text):
        return
    agent_id = r.json()["id"]
    cleanup.append(("DELETE", f"/agents/{agent_id}"))
    path = f"/agents/{agent_id}/memory"
    r = api.call("POST", path, {"key": "contact", "value": "email me at verify@example.com"})
    check(r.status_code == 201 and r.json()["has_pii"], "PII memory stored and flagged", r.text)
    check(r.json().get("value") == "email me at verify@example.com", "PII value round-trips")
    r = api.call("POST", path, {"key": "contact", "value": "again"})
    check(r.status_code == 409, "duplicate key is 409", r.status_code)
    r = api.call("POST", path, {"key": "contact", "value": "updated", "upsert": True})
    check(r.status_code == 201 and r.json()["value"] == "updated", "upsert overwrites", r.text)


def run(args: argparse.Namespace) -> int:
    api = Api(args.base_url)
    check = Check()
    suffix = uuid.uuid4().hex[:8]
    login = api.call("POST", "/auth/login", {"email": args.email, "password": args.password})
    if login.status_code != 200:
        print(f"Sign-in failed ({login.status_code}): {login.text}")
        return 2
    api.key = login.json()["api_key"]
    cleanup: list[tuple[str, str]] = []
    try:
        verify_prompts(api, check, suffix, cleanup)
        alias = pick_alias(api, check, args.alias)
        run_id = verify_playground(api, check, alias)
        verify_experiments(api, check, alias, run_id, cleanup)
        verify_judge(api, check, alias)
        verify_runbooks(api, check, run_id)
        verify_vector(api, check, suffix, cleanup)
        verify_memory(api, check, suffix, cleanup)
    finally:
        if not args.keep:
            for method, path in reversed(cleanup):
                api.call(method, path)
    print(f"\n{check.passed} passed, {len(check.failures)} failed, {len(check.skipped)} skipped")
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
    parser.add_argument("--alias", default=os.getenv("RUNLEDGER_GATEWAY_ALIAS"))
    parser.add_argument("--keep", action="store_true", help="Keep what the run created.")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
