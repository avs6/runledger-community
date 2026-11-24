#!/usr/bin/env python3
"""
Verify the gateway runtime (stream W1-B) end to end, in process, and benchmark it.

Runs the real FastAPI app over an ASGI transport against a Postgres + Redis you point
it at (a throwaway database: it seeds a tenant and flushes the Redis DB). It does not
need the Docker stack, gateway-rs or any provider: preflight and finalize are the
control-plane half of every gateway call, and are exactly what gateway-rs calls.

    cd apps/api
    DATABASE_URL=postgresql+asyncpg://runledger:runledger@127.0.0.1:5432/runledger \\
    REDIS_URL=redis://127.0.0.1:6379/0 \\
      uv run alembic upgrade head
    DATABASE_URL=... REDIS_URL=... uv run python ../../scripts/run_demo.py verify-gateway-runtime
    # benchmark only (CI): --bench --iterations 300

Checks (review IDs in brackets):
  * preflight mints a request_id and returns a decision trace + header      [ENH]
  * prompt refs resolve: name@prod / name@<n>, {{vars}} rendered            [B-23]
  * finalize persists run_id / api_key_id / workflow on the request row,
    links guardrail events to the run, keys the run to the prompt version   [G-19, O-12]
  * GET /gateway/runs/{id}/decision returns the "why this route" record     [ENH]
  * one cache profile: unique per workspace, real hit/miss/savings counters,
    scope_models enforced, max_entries evicts                               [G-09]
  * pass-through: governance preflight (guardrails 451, budgets 429) and
    upstream redirects are returned, never followed                         [G-15]
  * hot path: SQL statements per preflight stay within budget and the route
    lookup runs once per alias per request; p50 / p99 overhead reported     [cd:gw-perf]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import sys
import threading
import time
import uuid
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ADMIN_SECRET = os.environ.setdefault("ADMIN_SECRET", "verify-gateway-runtime-admin-secret")
os.environ.setdefault("SECRET_KEY", "verify-gateway-runtime-secret-key-0123456789")
os.environ.setdefault("RUNLEDGER_GATEWAY_HOTPATH_TTL_S", "0")  # correctness first

API_DIR = Path(__file__).resolve().parents[2] / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

import logging  # noqa: E402

import httpx  # noqa: E402
from runledger_api.core.db import AsyncSessionLocal, engine  # noqa: E402
from runledger_api.core.redis import get_redis  # noqa: E402
from runledger_api.main import app  # noqa: E402
from runledger_api.models.budgets import Budget  # noqa: E402
from runledger_api.models.cache_config import ResponseCacheConfig  # noqa: E402
from runledger_api.models.events import AgentRun  # noqa: E402
from runledger_api.models.gateway import (  # noqa: E402
    GatewayPassThroughEndpoint,
    GatewayRequest,
    GatewayRoute,
    PromptCache,
)
from runledger_api.models.guardrails import GuardrailEvent, GuardrailRule  # noqa: E402
from runledger_api.models.prompts import Prompt, PromptVersion  # noqa: E402
from runledger_api.models.tenant import ApiKey, Tenant, Workspace  # noqa: E402
from runledger_api.services.auth import generate_api_key  # noqa: E402
from runledger_api.services.budgets import set_budget_spend  # noqa: E402
from runledger_api.services.gateway_cache import invalidate_cache_profile  # noqa: E402
from runledger_api.services.gateway_hotpath import count_queries, ttl_cache  # noqa: E402
from sqlalchemy import func, select, text  # noqa: E402

logging.getLogger("httpx").setLevel(logging.WARNING)
engine.sync_engine.echo = False  # development mode echoes SQL; keep the report readable
PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, condition: bool, detail: Any = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {detail}")


# ── Upstream for pass-through ──────────────────────────────────────────────────


class _Upstream(BaseHTTPRequestHandler):
    def _reply(self) -> None:
        if self.path.startswith("/redirect"):
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
            self.end_headers()
            return
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = _reply  # noqa: N815
    do_POST = _reply  # noqa: N815

    def log_message(self, *args: Any) -> None:  # silence
        return


def start_upstream() -> str:
    server = HTTPServer(("127.0.0.1", 0), _Upstream)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"


# ── Seed ───────────────────────────────────────────────────────────────────────


async def seed(upstream: str) -> dict[str, Any]:
    from runledger_api.models.tenant import EnvironmentEnum  # noqa: PLC0415

    suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        tenant = Tenant(slug=f"w1b-{suffix}", name="W1-B verify")
        db.add(tenant)
        await db.flush()
        workspace = Workspace(tenant_id=tenant.id, name=f"w1b-{suffix}")
        db.add(workspace)
        await db.flush()
        raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
        api_key = ApiKey(
            workspace_id=workspace.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="w1b-verify",
            scopes=["gateway", "read", "write"],
        )
        db.add(api_key)
        for alias, priority, model in (
            ("chat", 1, "gpt-4o-mini"),
            ("chat", 2, "gpt-4o"),
            ("chat-fallback", 1, "claude-3-5-haiku"),
        ):
            db.add(
                GatewayRoute(
                    workspace_id=workspace.id,
                    alias=alias,
                    provider="openai" if model.startswith("gpt") else "anthropic",
                    target_model=model,
                    base_url=None,  # provider default; preflight never calls it
                    priority=priority,
                    fallback_config={"aliases": ["chat-fallback"]} if alias == "chat" else None,
                )
            )
        prompt = Prompt(workspace_id=workspace.id, name="triage", default_environment="production")
        db.add(prompt)
        await db.flush()
        for version, env, content in (
            (1, "production", "You are v1."),
            (2, "production", "You triage tickets for {{product}}. Tone: {{tone}}."),
            (3, "staging", "Staging prompt for {{product}}."),
        ):
            db.add(
                PromptVersion(
                    prompt_id=prompt.id, version=version, content=content, environment=env
                )
            )
        db.add(
            GuardrailRule(
                workspace_id=workspace.id,
                name="Denied Financial Advice",
                mode="pre_call",
                rule_type="builtin_filter",
                template_id="denied_financial_advice",
                severity="medium",
            )
        )
        db.add(
            GatewayPassThroughEndpoint(
                workspace_id=workspace.id,
                slug="upstream",
                upstream_base_url=upstream,
                cost_per_call_usd=Decimal("0.01"),
            )
        )
        blocked_budget = Budget(
            workspace_id=workspace.id,
            scope_type="feature_tag",
            scope_id="blocked-wf",
            period_type="monthly",
            limit_usd=Decimal("1"),
            action="block",
        )
        db.add(blocked_budget)
        await db.commit()
        return {
            "workspace_id": workspace.id,
            "api_key_id": api_key.id,
            "raw_key": raw_key,
            "blocked_budget_id": blocked_budget.id,
        }


# ── Helpers ────────────────────────────────────────────────────────────────────


def preflight_body(raw_key: str, **body: Any) -> dict[str, Any]:
    payload = {
        "model": "chat",
        "messages": [{"role": "user", "content": "Summarise ticket 42"}],
        "metadata": {"workflow": "support-triage"},
    }
    payload.update(body)
    return {"raw_key": raw_key, "body": payload, "client_ip": "127.0.0.1"}


ADMIN = {"X-Admin-Secret": ADMIN_SECRET}


async def verify(client: httpx.AsyncClient, ctx: dict[str, Any]) -> None:
    raw_key = ctx["raw_key"]
    ws_id = ctx["workspace_id"]

    print("\n[ENH / B-23] preflight decision trace + prompt ref")
    resp = await client.post(
        "/gateway/runtime/internal/preflight",
        headers=ADMIN,
        json=preflight_body(
            raw_key,
            prompt="triage@prod",
            prompt_variables={"product": "RunLedger", "tone": "calm"},
        ),
    )
    check("preflight 200", resp.status_code == 200, resp.text[:300])
    pre = resp.json()
    decision = pre.get("decision") or {}
    check("request_id minted", bool(pre.get("request_id")))
    check("decision.route.alias", (decision.get("route") or {}).get("alias") == "chat", decision)
    check(
        "fallback candidate listed",
        any(c.get("alias") == "chat-fallback" for c in decision.get("candidates", [])),
        decision.get("candidates"),
    )
    check(
        "prompt@prod → latest production version (2)",
        decision.get("prompt", {}).get("prompt_version") == 2,
    )
    system = (pre.get("prepared_messages") or [{}])[0]
    check(
        "prompt rendered as system message",
        system.get("role") == "system"
        and system.get("content") == "You triage tickets for RunLedger. Tone: calm.",
        system,
    )
    header = pre.get("decision_header") or ""
    check(
        "decision header cache/budget/guardrail",
        all(p in header for p in ("cache=miss", "budget=ok", "guardrail=pass")),
        header,
    )
    check("decision header names the prompt", "prompt=triage@2" in header, header)

    resp_v3 = await client.post(
        "/gateway/runtime/internal/preflight",
        headers=ADMIN,
        json=preflight_body(
            raw_key, prompt="triage@3", prompt_variables={"product": "X"}, cache=False
        ),
    )
    check(
        "prompt@3 resolves the staging version by number",
        (resp_v3.json().get("decision") or {}).get("prompt", {}).get("prompt_version") == 3,
    )
    resp_missing = await client.post(
        "/gateway/runtime/internal/preflight",
        headers=ADMIN,
        json=preflight_body(raw_key, prompt="nope@prod", cache=False),
    )
    check("unknown prompt → 404", resp_missing.status_code == 404, resp_missing.status_code)

    print("\n[G-19 / O-12] finalize persists attribution")
    step = pre["execution_steps"][0]
    fin = await client.post(
        "/gateway/runtime/internal/finalize",
        headers=ADMIN,
        json={
            "workspace_id": str(ws_id),
            "route_id": str(step["route_id"]),
            "api_key_id": str(ctx["api_key_id"]),
            "model_requested": "chat",
            "prepared_messages": pre["prepared_messages"],
            "response_json": {
                "id": "resp-1",
                "choices": [
                    {"message": {"role": "assistant", "content": "Ticket 42 is about billing."}}
                ],
                "usage": {"prompt_tokens": 40, "completion_tokens": 12},
            },
            "request_metadata": {"workflow": "support-triage"},
            "request_tags": pre.get("request_tags", []),
            "latency_ms": 120,
            "total_wall_ms": 131,
            "decision_reason": step.get("decision_reason"),
            "cache": True,
            "guardrails_enabled": True,
            "cache_key": pre.get("cache_key"),
            "request_id": pre["request_id"],
            "decision": decision,
        },
    )
    check("finalize 200", fin.status_code == 200, fin.text[:300])
    async with AsyncSessionLocal() as db:
        row = await db.get(GatewayRequest, uuid.UUID(pre["request_id"]))
        check("request row keyed by preflight request_id", row is not None)
        if row is not None:
            check("request.run_id persisted", row.run_id is not None)
            check("request.api_key_id persisted", row.api_key_id == ctx["api_key_id"])
            check("request.workflow persisted", row.workflow == "support-triage", row.workflow)
            run = await db.get(AgentRun, row.run_id) if row.run_id else None
            check(
                "run.deployment_version = prompt name:version",
                run is not None and run.deployment_version == "triage:2",
                run and run.deployment_version,
            )
            served = (
                (((run.run_metadata or {}).get("gateway_decision") or {}).get("route") or {}).get(
                    "served"
                )
                if run
                else None
            )
            check(
                "run stores the served route",
                bool(served) and served.get("route_id") == str(step["route_id"]),
                served,
            )
            linked = (
                await db.execute(
                    select(func.count(GuardrailEvent.id)).where(
                        GuardrailEvent.gateway_request_id == row.id,
                        GuardrailEvent.run_id == row.run_id,
                        GuardrailEvent.api_key_id == ctx["api_key_id"],
                        GuardrailEvent.workflow == "support-triage",
                    )
                )
            ).scalar_one()
            check("guardrail events linked to request, run, key and workflow", linked >= 1, linked)
            ctx["run_id"] = row.run_id

    print("\n[ENH] run decision endpoint")
    dec = await client.get(
        f"/gateway/runs/{ctx['run_id']}/decision", headers={"Authorization": f"Bearer {raw_key}"}
    )
    check("GET /gateway/runs/{id}/decision 200", dec.status_code == 200, dec.text[:300])
    body = dec.json() if dec.status_code == 200 else {}
    check(
        "decision header names the served route",
        (body.get("decision_header") or "").startswith("route=chat/openai:gpt-4o-mini"),
        body.get("decision_header"),
    )
    check(
        "decision endpoint reports gateway overhead",
        body.get("gateway_overhead_ms") == 11,
        body.get("gateway_overhead_ms"),
    )

    print("\n[G-09] one cache profile, real counters")
    hit = await client.post(
        "/gateway/runtime/internal/preflight",
        headers=ADMIN,
        json=preflight_body(
            raw_key, prompt="triage@prod", prompt_variables={"product": "RunLedger", "tone": "calm"}
        ),
    )
    hit_body = hit.json()
    check(
        "identical request → exact cache hit",
        hit_body.get("cache_hit_kind") == "exact",
        hit_body.get("cache_hit_kind"),
    )
    check(
        "cache-hit header",
        (hit_body.get("decision_header") or "").startswith("route=cache; cache=exact"),
        hit_body.get("decision_header"),
    )
    async with AsyncSessionLocal() as db:
        profile = (
            await db.execute(
                select(ResponseCacheConfig).where(ResponseCacheConfig.workspace_id == ws_id)
            )
        ).scalar_one_or_none()
        check("profile auto-created on first counted request", profile is not None)
        if profile is not None:
            check("hit counter", (profile.total_hits or 0) >= 1, profile.total_hits)
            check("miss counter", (profile.total_misses or 0) >= 1, profile.total_misses)
        hit_row = await db.get(GatewayRequest, uuid.UUID(hit_body["request_id"]))
        check(
            "cache-hit row carries key + workflow",
            hit_row is not None
            and hit_row.api_key_id == ctx["api_key_id"]
            and hit_row.workflow == "support-triage",
        )
        db.add(ResponseCacheConfig(workspace_id=ws_id, name="second"))
        try:
            await db.commit()
            unique_ok = False
        except Exception:  # noqa: BLE001
            await db.rollback()
            unique_ok = True
        check("second profile per workspace refused (unique index)", unique_ok)
        await db.execute(
            text(
                "UPDATE response_cache_configs SET scope_models = '[\"other-alias\"]', max_entries = 1 WHERE workspace_id = :ws"
            ),
            {"ws": ws_id},
        )
        await db.commit()
    invalidate_cache_profile(ws_id)
    scoped = await client.post(
        "/gateway/runtime/internal/preflight",
        headers=ADMIN,
        json=preflight_body(
            raw_key, prompt="triage@prod", prompt_variables={"product": "RunLedger", "tone": "calm"}
        ),
    )
    check(
        "scope_models excludes alias → no cache",
        scoped.json().get("cache_hit_kind") is None
        and (scoped.json().get("decision") or {}).get("cache", {}).get("exact") == "off",
    )
    async with AsyncSessionLocal() as db:
        for i in range(3):
            db.add(
                PromptCache(workspace_id=ws_id, cache_key=f"{i:064d}", model="m", response_json={})
            )
        await db.commit()
        await db.execute(
            text("UPDATE response_cache_configs SET scope_models = NULL WHERE workspace_id = :ws"),
            {"ws": ws_id},
        )
        await db.commit()
        invalidate_cache_profile(ws_id)
        from runledger_api.services.gateway import store_cache  # noqa: PLC0415

        await store_cache(db, ws_id, "f" * 64, "m", {}, 1, 1)
        left = (
            await db.execute(
                select(func.count(PromptCache.id)).where(PromptCache.workspace_id == ws_id)
            )
        ).scalar_one()
        check("max_entries=1 evicts the overflow", left == 1, left)
        await db.execute(
            text("UPDATE response_cache_configs SET max_entries = 10000 WHERE workspace_id = :ws"),
            {"ws": ws_id},
        )
        await db.commit()
        invalidate_cache_profile(ws_id)

    print("\n[G-15] pass-through governance + no redirects")
    bearer = {"Authorization": f"Bearer {raw_key}"}
    ok = await client.post(
        "/gateway/passthrough/upstream/ok",
        headers={**bearer, "X-RunLedger-Workflow": "support-triage"},
        json={"q": "hello"},
    )
    check("pass-through allowed request 200", ok.status_code == 200, ok.text[:200])
    redirect = await client.get("/gateway/passthrough/upstream/redirect", headers=bearer)
    check("upstream 302 returned, not followed", redirect.status_code == 302, redirect.status_code)
    check("Location header not forwarded", "location" not in {k.lower() for k in redirect.headers})
    blocked = await client.post(
        "/gateway/passthrough/upstream/ok",
        headers=bearer,
        content=b"I recommend you invest in crypto; this is financial advice to buy stock",
    )
    check("guardrail block → 451", blocked.status_code == 451, blocked.status_code)
    redis = await get_redis()
    # Budget spend is durable in Postgres with Redis as a cache (W1-D, cd:B-05).
    async with AsyncSessionLocal() as db:
        await set_budget_spend(db, redis, ctx["blocked_budget_id"], "monthly", Decimal("5"), 1)
        await db.commit()
    over = await client.post(
        "/gateway/passthrough/upstream/ok",
        headers={**bearer, "X-RunLedger-Workflow": "blocked-wf"},
        json={},
    )
    check("exhausted workflow budget → 429", over.status_code == 429, over.text[:200])
    async with AsyncSessionLocal() as db:
        pt = (
            (
                await db.execute(
                    select(GatewayRequest).where(
                        GatewayRequest.workspace_id == ws_id,
                        GatewayRequest.model_requested == "passthrough:upstream",
                        GatewayRequest.status == "success",
                    )
                )
            )
            .scalars()
            .first()
        )
        check(
            "pass-through row carries key + workflow",
            pt is not None
            and pt.api_key_id == ctx["api_key_id"]
            and pt.workflow == "support-triage",
        )


async def bench(client: httpx.AsyncClient, ctx: dict[str, Any], iterations: int) -> None:
    print(f"\n[cd:gw-perf] preflight hot path ({iterations} iterations, cache off)")
    body = preflight_body(ctx["raw_key"], cache=False)
    # Warm up (imports, pools).
    for _ in range(5):
        await client.post("/gateway/runtime/internal/preflight", headers=ADMIN, json=body)
    with count_queries(engine) as statements:
        resp = await client.post("/gateway/runtime/internal/preflight", headers=ADMIN, json=body)
    check("bench preflight 200", resp.status_code == 200, resp.text[:200])
    route_lookups = sum(
        1
        for s in statements
        if "FROM gateway_routes" in s
        and "gateway_routes.alias =" in s
        and "chat" not in s.split("WHERE")[0]
    )
    by_alias = sum(
        1
        for s in statements
        if s.lstrip().startswith("SELECT gateway_routes.id") and "gateway_routes.alias" in s
    )
    max_sql = int(os.getenv("GATEWAY_BENCH_MAX_SQL", "20"))
    print(
        f"  SQL statements per preflight: {len(statements)} (budget {max_sql}); route-row selects: {by_alias}"
    )
    if os.getenv("GATEWAY_BENCH_DUMP_SQL"):
        for stmt in statements:
            print("   ", " ".join(stmt.split())[:160])
    check(f"SQL per preflight ≤ {max_sql}", len(statements) <= max_sql, len(statements))
    # 2 aliases (chat + chat-fallback) → at most one route select each thanks to the memo.
    check("route rows loaded once per alias per request", by_alias <= 2, by_alias)
    _ = route_lookups

    for ttl_label, ttl in (("ttl=0 (no process cache)", "0"), ("ttl=5s (default)", "5")):
        os.environ["RUNLEDGER_GATEWAY_HOTPATH_TTL_S"] = ttl
        ttl_cache.clear()
        samples: list[float] = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            r = await client.post("/gateway/runtime/internal/preflight", headers=ADMIN, json=body)
            samples.append((time.perf_counter() - t0) * 1000)
            if r.status_code != 200:
                check("bench request ok", False, r.text[:200])
                return
        samples.sort()
        p50 = statistics.median(samples)
        p99 = samples[min(len(samples) - 1, int(len(samples) * 0.99))]
        print(f"  {ttl_label}: p50 {p50:.1f} ms  p99 {p99:.1f} ms")
        if ttl == "5":
            max_p99 = float(os.getenv("GATEWAY_BENCH_MAX_P99_MS", "400"))
            check(f"p99 preflight overhead ≤ {max_p99:.0f} ms", p99 <= max_p99, f"{p99:.1f}")
            summary = os.getenv("GITHUB_STEP_SUMMARY")
            if summary:
                with open(summary, "a", encoding="utf-8") as fh:
                    fh.write(
                        "### Gateway preflight overhead\n\n"
                        f"| iterations | p50 ms | p99 ms | SQL / request |\n|---|---|---|---|\n"
                        f"| {iterations} | {p50:.1f} | {p99:.1f} | {len(statements)} |\n"
                    )


async def main_async(args: argparse.Namespace) -> int:
    redis = await get_redis()
    await redis.flushdb()
    upstream = start_upstream()
    ctx = await seed(upstream)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://verify") as client:
        if not args.bench_only:
            await verify(client, ctx)
        if args.bench or args.bench_only:
            await bench(client, ctx, args.iterations)
    await engine.dispose()
    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for name in FAILED:
        print(f"  - {name}")
    return 1 if FAILED else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--bench", action="store_true", help="also run the p50/p99 benchmark")
    parser.add_argument("--bench-only", action="store_true", help="only run the benchmark")
    parser.add_argument("--iterations", type=int, default=200)
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
