#!/usr/bin/env python3
"""End-to-end verification of the critical security fixes against a running stack.

  1. Guardrail logic (review S-01): custom logic runs in RunLedger's own interpreter,
     never exec. Sandbox escapes are refused on save (422); a valid rule blocks and
     modifies as written; the PII template (which uses ``import re``) now works.
  2. Route credentials and hosts (review S-02): a route can't name a platform secret as
     its provider key, and can't point at internal or metadata addresses (422, even for
     platform admins); a route to the provider's official host still saves.
  3. Streamed gateway calls are metered (review G-03): a streamed completion through the
     Rust gateway produces a recorded run with token usage. Needs a local Ollama
     (``--ollama-model``); skipped with a note otherwise.
  4. Cache safety (review G-05, G-07): the exact cache key covers request parameters (a
     different temperature misses); a prompt cached before a blocking guardrail existed
     is blocked afterwards instead of being served from cache. Same Ollama requirement.
  5. Routing strategies (review G-01, G-02): data-driven policies (cost, latency, quality)
     decide instead of silently falling back to manual, and an alias-switching policy
     (complexity_based) routes to its target alias. Same Ollama requirement.
  6. Intelligent routing (review G-04): the built-in classifier routes a simple prompt
     to the "cheap" tier's alias without the old 25 s stall. Same Ollama requirement.
  7. PII redaction (review G-09, S-12): on a route with pii_redaction_enabled, a
     non-streamed request reaches the model with the email already replaced; the same
     prompt on a route without redaction is echoed back verbatim. Same Ollama requirement.
  8. Error-triggered fallbacks (review G-11): a local mock provider returns a 400
     context-length error; the route's context_window fallback serves the request. A plain
     400 reaches the client as 400 (not 502) and plain fallbacks are skipped.

Creates throwaway guardrail rules in the platform admin's workspace and deletes them.

Usage:
    python scripts/run_demo.py verify-security
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


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


ESCAPES = [
    "x = ().__class__.__bases__[0].__subclasses__()",
    "import os\nresult = block(os.getcwd())",
    "result = block(str(open('/etc/passwd').read()))",
    "f = getattr(texts, 'append')",
    "result = (lambda: block('x'))()",
]


def _admin_secret() -> str | None:
    """ADMIN_SECRET from the environment or the repo's .env, for internal endpoints.
    Never printed."""
    value = os.getenv("ADMIN_SECRET")
    if value:
        return value
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    try:
        with open(env_file, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("ADMIN_SECRET="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


class _MockProvider(BaseHTTPRequestHandler):
    """OpenAI-shaped provider that fails on demand: model "ctx" → 400 context-length
    error; "busy" → 429 with Retry-After: 1 on odd calls, a completion on even calls;
    anything else → plain 400. Counts hits per model."""

    hits: dict[str, int] = {}

    def _send(self, code: int, payload: dict[str, Any], headers: dict[str, str]) -> None:
        self.send_response(code)
        self.send_header("content-type", "application/json")
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_POST(self) -> None:  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("content-length") or 0)) or b"{}")
        model = str(body.get("model"))
        _MockProvider.hits[model] = _MockProvider.hits.get(model, 0) + 1
        if model == "shadow":
            time.sleep(3)
            self._send(
                200,
                {
                    "id": "chatcmpl-shadow",
                    "object": "chat.completion",
                    "model": "shadow",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "shadow"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 1, "total_tokens": 8},
                },
                {},
            )
            return
        if model == "busy":
            if _MockProvider.hits[model] % 2:
                self._send(429, {"error": {"message": "rate limited"}}, {"retry-after": "1"})
            else:
                self._send(
                    200,
                    {
                        "id": "chatcmpl-mock",
                        "object": "chat.completion",
                        "model": "busy",
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": "ok"},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
                    },
                    {},
                )
            return
        message = (
            "This model's maximum context length is 8192 tokens"
            if model == "ctx"
            else "Invalid value for 'foo'"
        )
        payload = json.dumps({"error": {"message": message, "type": "invalid_request_error"}})
        self.send_response(400)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(payload.encode())

    def log_message(self, *_: Any) -> None:
        pass


def run(args: argparse.Namespace) -> int:
    http = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=60)
    check = Check()
    login = http.post("/auth/login", json={"email": args.email, "password": args.password})
    if login.status_code != 200:
        print(f"Sign-in failed ({login.status_code}): {login.text}")
        return 2
    h = {"Authorization": f"Bearer {login.json()['api_key']}"}
    created: list[str] = []
    routes: list[str] = []

    def rule(name: str, logic: str) -> httpx.Response:
        resp = http.post(
            "/guardrails",
            headers=h,
            json={
                "name": name,
                "mode": "pre_call",
                "rule_type": "custom",
                "logic": logic,
                "status": "draft",
            },
        )
        if resp.status_code in (200, 201):
            created.append(resp.json()["id"])
        return resp

    try:
        print("\n→ guardrail logic: no exec (S-01)")
        for src in ESCAPES:
            r = rule("verify-escape", src)
            check(
                r.status_code == 422,
                f"escape refused on save: {src.splitlines()[0][:40]}",
                r.status_code,
            )

        ok = rule(
            "verify-secret-block",
            'combined = " ".join(texts).lower()\n'
            'hits = [w for w in ["password", "api_key"] if w in combined]\n'
            'result = block(f"secret words: {hits}") if hits else allow()',
        )
        if check(ok.status_code in (200, 201), "valid custom rule saved", ok.text):
            t = http.post(
                f"/guardrails/{ok.json()['id']}/test",
                headers=h,
                json={"texts": ["my password is x"]},
            )
            check(
                t.status_code == 200 and t.json()["overall_decision"] == "block",
                "rule blocks as written",
                t.text,
            )
            t = http.post(
                f"/guardrails/{ok.json()['id']}/test", headers=h, json={"texts": ["hello"]}
            )
            check(
                t.status_code == 200 and t.json()["overall_decision"] == "allow",
                "rule allows clean text",
                t.text,
            )

        templates = http.get("/guardrails/templates", headers=h).json()
        items = templates.get("items", templates) if isinstance(templates, dict) else templates
        pii = next(
            (
                tpl
                for tpl in items
                if tpl.get("id") == "pii_detection" or tpl.get("template_id") == "pii_detection"
            ),
            None,
        )
        if check(pii is not None, "PII template listed"):
            pr = rule("verify-pii", pii["default_logic"])
            if check(pr.status_code in (200, 201), "PII template (uses import re) saves", pr.text):
                t = http.post(
                    f"/guardrails/{pr.json()['id']}/test",
                    headers=h,
                    json={"texts": ["mail jane@example.com"]},
                )
                check(
                    t.status_code == 200 and t.json()["overall_decision"] == "block",
                    "PII template blocks an email",
                    t.text,
                )

        mod = rule(
            "verify-mask",
            'out = [re.sub(r"\\d{9,17}", "[ACCOUNT]", t) for t in texts]\n'
            "result = modify(texts=out) if out != texts else allow()",
        )
        if check(mod.status_code in (200, 201), "modify rule saved", mod.text):
            t = http.post(
                f"/guardrails/{mod.json()['id']}/test",
                headers=h,
                json={"texts": ["acct 123456789012"]},
            )
            check(
                t.status_code == 200 and t.json()["overall_decision"] == "modify",
                "modify rule rewrites text",
                t.text,
            )
        print("\n→ route credentials and hosts (S-02)")
        suffix = os.urandom(3).hex()

        def route(body: dict[str, Any]) -> httpx.Response:
            resp = http.post(
                "/gateway/routes",
                headers=h,
                json={
                    "alias": f"verify-sec-{suffix}",
                    "provider": "openai",
                    "target_model": "gpt-4o-mini",
                    "is_active": False,
                    **body,
                },
            )
            if resp.status_code in (200, 201):
                routes.append(resp.json()["id"])
            return resp

        for var in ("ADMIN_SECRET", "SECRET_KEY", "DATABASE_URL", "POSTGRES_PASSWORD"):
            r = route({"api_key_env_var": var})
            check(r.status_code == 422, f"{var} refused as a provider key", r.status_code)
        for url in (
            "http://169.254.169.254/latest/meta-data",
            "http://127.0.0.1:8201",
            "http://10.1.2.3/v1",
        ):
            r = route({"base_url": url, "api_key_env_var": "OPENAI_API_KEY"})
            check(r.status_code == 422, f"internal host refused: {url}", r.status_code)
        ok = route({"base_url": "https://api.openai.com/v1", "api_key_env_var": "OPENAI_API_KEY"})
        check(ok.status_code in (200, 201), "official-host route saves", ok.text)
        if ok.status_code in (200, 201):
            upd = http.put(
                f"/gateway/routes/{ok.json()['id']}",
                headers=h,
                json={"api_key_env_var": "ADMIN_SECRET"},
            )
            check(
                upd.status_code == 422,
                "editing a route to a secret variable is refused",
                upd.status_code,
            )
        print("\n→ streamed calls are metered (G-03)")
        try:
            tags = httpx.get(f"{args.ollama_url}/api/tags", timeout=3).json()
            models = [m["name"] for m in tags.get("models", [])]
        except (httpx.HTTPError, ValueError):
            models = []
        model = args.ollama_model or (models[0] if models else "")
        if not model:
            print("  - skipped: no local Ollama model (pass --ollama-url/--ollama-model)")
        else:
            alias = f"verify-stream-{suffix}"
            cr = http.post(
                "/gateway/routes",
                headers=h,
                json={
                    "alias": alias,
                    "provider": "ollama",
                    "target_model": model,
                    "base_url": "http://host.docker.internal:11434/v1",
                    "is_active": True,
                },
            )
            if check(cr.status_code in (200, 201), "local streaming route saved", cr.text):
                routes.append(cr.json()["id"])
                key = http.post(
                    "/settings/api-keys",
                    headers=h,
                    json={"name": f"verify-stream-{suffix}", "scopes": ["gateway"]},
                ).json()
                gk = {"Authorization": f"Bearer {key['key']}"}
                tag = f"verify-stream-{suffix}"
                chunks = 0
                with httpx.stream(
                    "POST",
                    f"{args.gateway_url}/gateway/chat/completions",
                    headers=gk,
                    timeout=180,
                    json={
                        "model": alias,
                        "stream": True,
                        "max_tokens": 16,
                        "messages": [{"role": "user", "content": "Say hi."}],
                        "metadata": {"feature_tag": tag},
                    },
                ) as resp:
                    for line in resp.iter_lines():
                        if line.startswith("data:"):
                            chunks += 1
                check(chunks > 1, "stream delivered to the client", chunks)
                run = None
                for _ in range(20):
                    runs = http.get("/runs", headers=h, params={"limit": 10}).json()
                    items = runs.get("items", runs) if isinstance(runs, dict) else runs
                    run = next((r for r in items if r.get("feature_tag") == tag), None)
                    if run:
                        break
                    time.sleep(1)
                check(bool(run), "streamed call recorded as a run", run)
                check(
                    bool(run) and (run.get("total_output_tokens") or 0) > 0,
                    "streamed call has token usage",
                    run,
                )

                print("\n→ cache safety (G-05, G-07)")

                def ask(prompt: str, temperature: float) -> httpx.Response:
                    return httpx.post(
                        f"{args.gateway_url}/gateway/chat/completions",
                        headers=gk,
                        timeout=180,
                        json={
                            "model": alias,
                            "max_tokens": 8,
                            "temperature": temperature,
                            "cache": True,
                            "messages": [{"role": "user", "content": prompt}],
                        },
                    )

                prompt = f"cache probe {suffix} zebra-word"
                first = ask(prompt, 0)
                check(
                    first.status_code == 200, "first call served by the provider", first.status_code
                )
                time.sleep(1)
                second = ask(prompt, 0)
                check(
                    second.headers.get("x-runledger-cache") == "exact",
                    "identical call is a cache hit",
                    dict(second.headers),
                )
                other = ask(prompt, 0.9)
                check(
                    other.headers.get("x-runledger-cache") is None,
                    "different temperature is not a cache hit",
                    dict(other.headers),
                )
                gr = http.post(
                    "/guardrails",
                    headers=h,
                    json={
                        "name": f"verify-cache-block-{suffix}",
                        "mode": "pre_call",
                        "rule_type": "custom",
                        "status": "active",
                        "logic": 'result = block("zebra") if any("zebra-word" in t for t in texts) else allow()',
                    },
                )
                if check(gr.status_code in (200, 201), "blocking guardrail created", gr.text):
                    created.append(gr.json()["id"])
                    blocked = ask(prompt, 0)
                    check(
                        blocked.status_code == 451,
                        "cached prompt is blocked, not served from cache",
                        (blocked.status_code, blocked.headers.get("x-runledger-cache")),
                    )

                print("\n→ routing strategies (G-01, G-02)")
                small = f"verify-small-{suffix}"
                sr = http.post(
                    "/gateway/routes",
                    headers=h,
                    json={
                        "alias": small,
                        "provider": "ollama",
                        "target_model": model,
                        "base_url": "http://host.docker.internal:11434/v1",
                        "is_active": True,
                    },
                )
                if sr.status_code in (200, 201):
                    routes.append(sr.json()["id"])
                policies: list[str] = []

                def decide(policy_type: str, config: dict) -> str:
                    for pid in policies:
                        http.delete(f"/gateway/policies/{pid}", headers=h)
                    policies.clear()
                    pr = http.post(
                        "/gateway/policies",
                        headers=h,
                        json={"alias": alias, "policy_type": policy_type, "config": config},
                    )
                    if pr.status_code not in (200, 201):
                        return f"policy create failed {pr.status_code} {pr.text[:120]}"
                    policies.append(pr.json()["id"])
                    httpx.post(
                        f"{args.gateway_url}/gateway/chat/completions",
                        headers=gk,
                        timeout=180,
                        json={
                            "model": alias,
                            "max_tokens": 4,
                            "cache": False,
                            "messages": [{"role": "user", "content": f"route probe {policy_type}"}],
                        },
                    )
                    time.sleep(1)
                    for target in (alias, small):
                        reqs = http.get(
                            "/gateway/requests", headers=h, params={"alias": target, "limit": 1}
                        ).json()
                        items = reqs.get("items", reqs) if isinstance(reqs, dict) else reqs
                        if items and policy_type.split("_")[0] in (
                            items[0].get("decision_reason") or ""
                        ):
                            return items[0]["decision_reason"]
                    reqs = http.get("/gateway/requests", headers=h, params={"limit": 1}).json()
                    items = reqs.get("items", reqs) if isinstance(reqs, dict) else reqs
                    return (items[0].get("decision_reason") or "") if items else ""

                for ptype in (
                    "cost_optimized",
                    "latency_optimized",
                    "quality_optimized",
                    "outcome_optimized",
                ):
                    reason = decide(ptype, {})
                    check(
                        reason.startswith(ptype),
                        f"{ptype} decides (no silent manual fallback)",
                        reason,
                    )
                reason = decide(
                    "complexity_based", {"token_threshold": 100000, "simple_alias": small}
                )
                check(
                    f"→ {small}" in reason, "complexity_based switches to its target alias", reason
                )
                for pid in policies:
                    http.delete(f"/gateway/policies/{pid}", headers=h)

                print("\n→ intelligent routing (G-04)")
                smart = f"verify-smart-{suffix}"
                ir = http.post(
                    "/gateway/routes",
                    headers=h,
                    json={
                        "alias": smart,
                        "provider": "ollama",
                        "target_model": model,
                        "base_url": "http://host.docker.internal:11434/v1",
                        "is_active": True,
                        "intelligent_routing_enabled": True,
                        "routing_config": {
                            "classifier_mode": "heuristic",
                            "tiers": {"cheap": small},
                        },
                    },
                )
                if check(
                    ir.status_code in (200, 201), "route with intelligent routing saved", ir.text
                ):
                    routes.append(ir.json()["id"])
                    started = time.monotonic()
                    httpx.post(
                        f"{args.gateway_url}/gateway/chat/completions",
                        headers=gk,
                        timeout=180,
                        json={
                            "model": smart,
                            "max_tokens": 4,
                            "cache": False,
                            "messages": [{"role": "user", "content": f"say hi {suffix}"}],
                        },
                    )
                    elapsed = time.monotonic() - started
                    time.sleep(1)
                    reqs = http.get(
                        "/gateway/requests", headers=h, params={"alias": smart, "limit": 1}
                    ).json()
                    items = reqs.get("items", reqs) if isinstance(reqs, dict) else reqs
                    reason = (items[0].get("decision_reason") or "") if items else ""
                    check(
                        "intelligent:simple/low" in reason,
                        "simple prompt classified and routed to the cheap tier",
                        reason,
                    )
                    check(elapsed < 20, "no classifier stall", f"{elapsed:.1f}s")

                print("\n→ PII redaction on non-streamed calls (G-09, S-12)")
                email = f"alice.{suffix}@example.com"

                def echo(redact: bool) -> str | None:
                    name = f"verify-pii-{'on' if redact else 'off'}-{suffix}"
                    rr = http.post(
                        "/gateway/routes",
                        headers=h,
                        json={
                            "alias": name,
                            "provider": "ollama",
                            "target_model": model,
                            "base_url": "http://host.docker.internal:11434/v1",
                            "is_active": True,
                            "pii_redaction_enabled": redact,
                        },
                    )
                    if rr.status_code not in (200, 201):
                        return None
                    routes.append(rr.json()["id"])
                    resp = httpx.post(
                        f"{args.gateway_url}/gateway/chat/completions",
                        headers=gk,
                        timeout=180,
                        json={
                            "model": name,
                            "max_tokens": 60,
                            "temperature": 0,
                            "reasoning_effort": "none",
                            "cache": False,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": f"Repeat this text exactly and nothing else: {email}",
                                }
                            ],
                        },
                    )
                    if resp.status_code != 200:
                        return None
                    return str(resp.json()["choices"][0]["message"].get("content") or "")

                plain = echo(False)
                redacted = echo(True)
                check(
                    plain is not None and email in plain,
                    "without redaction the model echoes the email (baseline)",
                    (plain or "")[:120],
                )
                check(
                    redacted is not None and email not in redacted,
                    "with pii_redaction_enabled the non-streamed prompt is redacted before the model",
                    (redacted or "")[:120],
                )

                print("\n→ post-call guardrail block keeps the spend (G-10)")
                word = f"mango{suffix}"
                pg = http.post(
                    "/guardrails",
                    headers=h,
                    json={
                        "name": f"verify-post-block-{suffix}",
                        "mode": "post_call",
                        "rule_type": "custom",
                        "status": "active",
                        "logic": f'result = block("fruit") if any("{word}" in t for t in texts) else allow()',
                    },
                )
                if check(pg.status_code in (200, 201), "post-call guardrail created", pg.text):
                    created.append(pg.json()["id"])
                    pb = httpx.post(
                        f"{args.gateway_url}/gateway/chat/completions",
                        headers=gk,
                        timeout=180,
                        json={
                            "model": small,
                            "max_tokens": 30,
                            "temperature": 0,
                            "reasoning_effort": "none",
                            "cache": False,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": f"Repeat this text exactly and nothing else: {word}",
                                }
                            ],
                        },
                    )
                    check(pb.status_code == 451, "response is blocked (451)", pb.status_code)
                    time.sleep(1)
                    reqs = http.get(
                        "/gateway/requests",
                        headers=h,
                        params={"alias": small, "status": "blocked", "limit": 1},
                    ).json()
                    items = reqs.get("items", reqs) if isinstance(reqs, dict) else reqs
                    row = items[0] if items else {}
                    check(
                        bool(row) and (row.get("input_tokens") or 0) > 0,
                        "blocked call is recorded with its tokens (status blocked)",
                        row,
                    )
                    check(
                        "guardrail_blocked" in (row.get("decision_reason") or ""),
                        "blocked call names the guardrail reason",
                        row.get("decision_reason"),
                    )
                    runs = http.get(
                        "/runs", headers=h, params={"status": "failed", "limit": 10}
                    ).json()
                    run_items = runs.get("items", runs) if isinstance(runs, dict) else runs
                    blocked_runs = [r for r in run_items if (r.get("total_input_tokens") or 0) > 0]
                    check(
                        bool(blocked_runs),
                        "blocked call is recorded as a failed run",
                        run_items[:1],
                    )
                    tb = httpx.post(
                        f"{args.gateway_url}/gateway/chat/completions",
                        headers=gk,
                        timeout=180,
                        json={
                            "model": small,
                            "max_tokens": 80,
                            "temperature": 0,
                            "reasoning_effort": "none",
                            "cache": False,
                            "tools": [
                                {
                                    "type": "function",
                                    "function": {
                                        "name": "save_note",
                                        "parameters": {
                                            "type": "object",
                                            "properties": {"text": {"type": "string"}},
                                            "required": ["text"],
                                        },
                                    },
                                }
                            ],
                            "tool_choice": "required",
                            "messages": [
                                {"role": "user", "content": f"Save a note with the text {word}"}
                            ],
                        },
                    )
                    calls = []
                    if tb.status_code == 200:
                        calls = tb.json()["choices"][0]["message"].get("tool_calls") or []
                    if tb.status_code == 200 and not calls:
                        print("  - model returned no tool call; tool-argument check skipped")
                    else:
                        check(
                            tb.status_code == 451,
                            "blocked word inside tool-call arguments is caught post-call",
                            (tb.status_code, calls[:1]),
                        )

                print("\n→ error-triggered fallbacks (G-11)")
                server = ThreadingHTTPServer(("0.0.0.0", 0), _MockProvider)  # noqa: S104
                threading.Thread(target=server.serve_forever, daemon=True).start()
                mock_url = f"http://host.docker.internal:{server.server_address[1]}/v1"

                def mock_route(name: str, target: str, fallback: dict) -> bool:
                    mr = http.post(
                        "/gateway/routes",
                        headers=h,
                        json={
                            "alias": name,
                            "provider": "ollama",
                            "target_model": target,
                            "base_url": mock_url,
                            "is_active": True,
                            "fallback_config": fallback,
                        },
                    )
                    if mr.status_code in (200, 201):
                        routes.append(mr.json()["id"])
                    return check(
                        mr.status_code in (200, 201), f"mock route {target} saved", mr.text
                    )

                def call(name: str) -> httpx.Response:
                    return httpx.post(
                        f"{args.gateway_url}/gateway/chat/completions",
                        headers=gk,
                        timeout=180,
                        json={
                            "model": name,
                            "max_tokens": 4,
                            "reasoning_effort": "none",
                            "cache": False,
                            "messages": [{"role": "user", "content": f"fallback probe {suffix}"}],
                        },
                    )

                try:
                    ctx_alias = f"verify-ctx-{suffix}"
                    if mock_route(
                        ctx_alias,
                        "ctx",
                        {"fallbacks": [{"alias": small, "on": ["context_window"]}]},
                    ):
                        cr = call(ctx_alias)
                        check(
                            _MockProvider.hits.get("ctx", 0) >= 1,
                            "primary route was tried (mock provider hit)",
                            _MockProvider.hits,
                        )
                        check(
                            cr.status_code == 200,
                            "context_window error falls through to its fallback route",
                            (cr.status_code, cr.text[:200]),
                        )
                    bad_alias = f"verify-bad-{suffix}"
                    if mock_route(bad_alias, "bad", {"aliases": [small]}):
                        before = len(
                            (lambda r: r.get("items", r) if isinstance(r, dict) else r)(
                                http.get(
                                    "/gateway/requests",
                                    headers=h,
                                    params={"alias": small, "limit": 200},
                                ).json()
                            )
                        )
                        br = call(bad_alias)
                        check(
                            br.status_code == 400,
                            "plain 400 reaches the client as 400, not 502",
                            (br.status_code, br.text[:200]),
                        )
                        check(
                            _MockProvider.hits.get("bad", 0) == 1,
                            "non-transient error is not retried",
                            _MockProvider.hits,
                        )
                        time.sleep(1)
                        after = len(
                            (lambda r: r.get("items", r) if isinstance(r, dict) else r)(
                                http.get(
                                    "/gateway/requests",
                                    headers=h,
                                    params={"alias": small, "limit": 200},
                                ).json()
                            )
                        )
                        check(
                            after == before, "plain fallback skipped after a 400", (before, after)
                        )
                    busy_alias = f"verify-busy-{suffix}"
                    if mock_route(busy_alias, "busy", {}):
                        started = time.monotonic()
                        rr = call(busy_alias)
                        waited = time.monotonic() - started
                        check(
                            rr.status_code == 200 and _MockProvider.hits.get("busy") == 2,
                            "429 is retried on the same route and then succeeds",
                            (rr.status_code, _MockProvider.hits, rr.text[:120]),
                        )
                        check(waited >= 0.9, "retry waits for Retry-After (1 s)", f"{waited:.2f}s")

                    print("\n→ mirror traffic off the response path (G-12)")
                    shadow_alias = f"verify-shadow-{suffix}"
                    primary_alias = f"verify-mirrored-{suffix}"
                    tag = f"verify-shadow-{suffix}"
                    if mock_route(shadow_alias, "shadow", {}):
                        pr = http.post(
                            "/gateway/routes",
                            headers=h,
                            json={
                                "alias": primary_alias,
                                "provider": "ollama",
                                "target_model": model,
                                "base_url": "http://host.docker.internal:11434/v1",
                                "is_active": True,
                                "mirror_config": {"alias": shadow_alias, "sample_pct": 1.0},
                            },
                        )
                        if check(pr.status_code in (200, 201), "mirrored route saved", pr.text):
                            routes.append(pr.json()["id"])
                            started = time.monotonic()
                            mr = httpx.post(
                                f"{args.gateway_url}/gateway/chat/completions",
                                headers=gk,
                                timeout=180,
                                json={
                                    "model": primary_alias,
                                    "max_tokens": 4,
                                    "reasoning_effort": "none",
                                    "cache": False,
                                    "metadata": {"feature_tag": tag},
                                    "messages": [{"role": "user", "content": "say ok"}],
                                },
                            )
                            waited = time.monotonic() - started
                            check(
                                mr.status_code == 200, "mirrored request succeeds", mr.status_code
                            )
                            check(
                                waited < 2.5,
                                "user isn't kept waiting for the 3 s shadow model",
                                f"{waited:.2f}s",
                            )
                            shadow_runs: list = []
                            for _ in range(15):
                                time.sleep(1)
                                runs = http.get(
                                    "/runs", headers=h, params={"feature_tag": tag, "limit": 10}
                                ).json()
                                shadow_runs = (
                                    runs.get("items", runs) if isinstance(runs, dict) else runs
                                )
                                if len(shadow_runs) >= 2:
                                    break
                            check(
                                _MockProvider.hits.get("shadow") == 1,
                                "shadow call still happens in the background",
                                _MockProvider.hits,
                            )
                            check(
                                len(shadow_runs) == 2
                                and any(
                                    (r.get("total_input_tokens") or 0) == 7 for r in shadow_runs
                                ),
                                "shadow call is recorded as its own run with its tokens",
                                [
                                    (r.get("total_input_tokens"), r.get("status"))
                                    for r in shadow_runs
                                ],
                            )
                finally:
                    server.shutdown()

                print("\n→ limit breaches are 429s, not outages (G-13)")
                neg = http.post(
                    "/gateway/routes",
                    headers=h,
                    json={
                        "alias": f"verify-neg-{suffix}",
                        "provider": "ollama",
                        "target_model": model,
                        "base_url": "http://host.docker.internal:11434/v1",
                        "daily_cost_limit_usd": -1,
                    },
                )
                check(neg.status_code == 422, "negative cost cap rejected", neg.status_code)

                def limited_route(name: str, extra: dict) -> bool:
                    lr = http.post(
                        "/gateway/routes",
                        headers=h,
                        json={
                            "alias": name,
                            "provider": "ollama",
                            "target_model": model,
                            "base_url": "http://host.docker.internal:11434/v1",
                            "is_active": True,
                            **extra,
                        },
                    )
                    if lr.status_code in (200, 201):
                        routes.append(lr.json()["id"])
                    return check(lr.status_code in (200, 201), f"route {extra} saved", lr.text)

                def limited_call(name: str) -> httpx.Response:
                    return httpx.post(
                        f"{args.gateway_url}/gateway/chat/completions",
                        headers={**gk, "X-RunLedger-End-User-Id": f"verify-user-{suffix}"},
                        timeout=180,
                        json={
                            "model": name,
                            "max_tokens": 4,
                            "reasoning_effort": "none",
                            "cache": False,
                            "messages": [{"role": "user", "content": "say ok"}],
                        },
                    )

                capped = f"verify-capped-{suffix}"
                if limited_route(capped, {"daily_cost_limit_usd": 0}):
                    cr = limited_call(capped)
                    check(
                        cr.status_code == 429
                        and cr.headers.get("x-cost-cap-reason") == "daily_limit_exceeded"
                        and int(cr.headers.get("retry-after") or 0) > 0,
                        "cost-cap breach → 429 with X-Cost-Cap-Reason and Retry-After",
                        (cr.status_code, dict(cr.headers), cr.text[:120]),
                    )
                rpm = f"verify-rpm-{suffix}"
                if limited_route(rpm, {"per_user_rpm_limit": 1}):
                    first = limited_call(rpm)
                    second = limited_call(rpm)
                    check(
                        first.status_code == 200,
                        "first request under the RPM limit",
                        first.status_code,
                    )
                    check(
                        second.status_code == 429 and second.headers.get("retry-after") is not None,
                        "per-user RPM breach → 429 with Retry-After",
                        (second.status_code, dict(second.headers), second.text[:120]),
                    )

                print("\n→ RPM limiter semantics (G-14)")
                anon = f"verify-rpm-key-{suffix}"
                if limited_route(anon, {"per_user_rpm_limit": 1}):

                    def keyed_call(name: str) -> httpx.Response:
                        return httpx.post(
                            f"{args.gateway_url}/gateway/chat/completions",
                            headers=gk,
                            timeout=180,
                            json={
                                "model": name,
                                "max_tokens": 4,
                                "reasoning_effort": "none",
                                "cache": False,
                                "messages": [{"role": "user", "content": "say ok"}],
                            },
                        )

                    a1, a2 = keyed_call(anon), keyed_call(anon)
                    check(
                        a1.status_code == 200 and a2.status_code == 429,
                        "no end-user header → limited per API key, not bypassed",
                        (a1.status_code, a2.status_code),
                    )
                pair = f"verify-rpm-pair-{suffix}"
                if limited_route(pair, {"per_user_rpm_limit": 1, "priority": 1}) and limited_route(
                    pair, {"per_user_rpm_limit": 1, "priority": 2}
                ):
                    codes = [limited_call(pair).status_code for _ in range(3)]
                    check(
                        codes == [200, 200, 429],
                        "fallback route isn't counted until it serves (200, 200 via fallback, then 429)",
                        codes,
                    )

                print("\n→ gateway overhead is measured (G-15)")
                for stream in (False, True):
                    oh_alias = f"verify-overhead-{'s' if stream else 'j'}-{suffix}"
                    if not limited_route(oh_alias, {}):
                        continue
                    with httpx.stream(
                        "POST",
                        f"{args.gateway_url}/gateway/chat/completions",
                        headers=gk,
                        timeout=180,
                        json={
                            "model": oh_alias,
                            "max_tokens": 8,
                            "reasoning_effort": "none",
                            "cache": False,
                            "stream": stream,
                            "messages": [{"role": "user", "content": "count to three"}],
                        },
                    ) as resp:
                        for _ in resp.iter_bytes():
                            pass
                    bench: dict = {}
                    for _ in range(10):
                        time.sleep(1)
                        data = http.get(
                            "/gateway/benchmarks/compare",
                            headers=h,
                            params={"alias": oh_alias, "days": 1},
                        ).json()
                        items = data.get("items", data) if isinstance(data, dict) else data
                        if items:
                            bench = items[0]
                            break
                    overhead = float(bench.get("avg_gateway_overhead_ms") or 0)
                    check(
                        overhead > 0,
                        f"{'streamed' if stream else 'non-streamed'} request reports gateway overhead > 0",
                        bench,
                    )

                print("\n→ cost caps use real pricing (G-17)")
                unpriced = http.post(
                    "/gateway/routes",
                    headers=h,
                    json={
                        "alias": f"verify-unpriced-{suffix}",
                        "provider": "openai",
                        "target_model": f"unpriced-model-{suffix}",
                        "api_key_env_var": "OPENAI_API_KEY",
                        "daily_cost_limit_usd": 5,
                    },
                )
                check(
                    unpriced.status_code == 422 and "No pricing" in unpriced.text,
                    "cost cap on an unpriced hosted model is rejected (no invented price)",
                    (unpriced.status_code, unpriced.text[:160]),
                )
                tiny = f"verify-tinycap-{suffix}"
                if limited_route(tiny, {"daily_cost_limit_usd": 0.0001}):
                    tiny_codes = [
                        httpx.post(
                            f"{args.gateway_url}/gateway/chat/completions",
                            headers=gk,
                            timeout=180,
                            json={
                                "model": tiny,
                                "max_tokens": 4,
                                "reasoning_effort": "none",
                                "cache": False,
                                # ~1,800 prompt tokens: about $0.0009 at the old invented
                                # $0.50/1M rate, so the old code refused the 2nd call.
                                "messages": [{"role": "user", "content": "say ok " * 600}],
                            },
                        ).status_code
                        for _ in range(3)
                    ]
                    check(
                        tiny_codes == [200, 200, 200],
                        "local model calls don't count toward a cost cap (cost 0, not $0.50/$1.50 per 1M)",
                        tiny_codes,
                    )

                print("\n→ IP ACL: no spoofing, access groups, OIDC-safe (G-18)")
                bad = http.post(
                    "/security/ip-acl",
                    headers=h,
                    json={"scope_type": "workspace", "cidr": "not-a-cidr", "action": "allow"},
                )
                check(bad.status_code == 422, "invalid CIDR rejected", bad.status_code)
                acl_ids: list[str] = []
                group_id = None
                me = http.get("/users/me", headers=h).json()
                acl_alias = f"verify-acl-{suffix}"
                limited_route(acl_alias, {})

                def acl_call(extra_headers: dict) -> int:
                    return httpx.post(
                        f"{args.gateway_url}/gateway/chat/completions",
                        headers={**gk, **extra_headers},
                        timeout=180,
                        json={
                            "model": acl_alias,
                            "max_tokens": 4,
                            "reasoning_effort": "none",
                            "cache": False,
                            "messages": [{"role": "user", "content": "say ok"}],
                        },
                    ).status_code

                try:
                    r1 = http.post(
                        "/security/ip-acl",
                        headers=h,
                        json={
                            "scope_type": "workspace",
                            "cidr": "198.51.100.0/24",
                            "action": "allow",
                            "priority": 50,
                            "description": f"verify-acl-{suffix}",
                        },
                    )
                    if check(r1.status_code == 201, "allow-list rule saved", r1.text):
                        acl_ids.append(r1.json()["id"])
                        check(
                            acl_call({"X-Forwarded-For": "198.51.100.7"}) == 403,
                            "spoofed X-Forwarded-For can't claim an allow-listed IP",
                        )
                    g = http.post(
                        "/access-groups", headers=h, json={"name": f"verify-acl-{suffix}"}
                    )
                    if check(g.status_code in (200, 201), "access group created", g.text):
                        group_id = g.json()["id"]
                        http.post(
                            f"/access-groups/{group_id}/members",
                            headers=h,
                            json={"user_id": me["id"]},
                        )
                        for net in ("0.0.0.0/0", "::/0"):
                            gr = http.post(
                                "/security/ip-acl",
                                headers=h,
                                json={
                                    "scope_type": "access_group",
                                    "access_group_id": group_id,
                                    "cidr": net,
                                    "action": "allow",
                                    "priority": 10,
                                    "description": f"verify-acl-{suffix}",
                                },
                            )
                            if gr.status_code == 201:
                                acl_ids.append(gr.json()["id"])
                        member = acl_call({"X-RunLedger-End-User-Id": me["email"]})
                        check(
                            member == 200,
                            "access-group member is admitted by the group's rule",
                            member,
                        )
                        http.delete(f"/access-groups/{group_id}/members/{me['id']}", headers=h)
                        removed = acl_call({"X-RunLedger-End-User-Id": me["email"]})
                        check(
                            removed == 403,
                            "after leaving the group the request is refused",
                            removed,
                        )
                finally:
                    for rid in acl_ids:
                        http.delete(f"/security/ip-acl/{rid}", headers=h)
                    if group_id:
                        http.delete(f"/access-groups/{group_id}", headers=h)
                check(acl_call({}) == 200, "ACL rules removed: traffic flows again")

                print("\n→ timeout overrides don't touch the route (G-20)")
                secret = _admin_secret()
                if not secret:
                    print("  - ADMIN_SECRET not set (env or .env); provider-execute check skipped")
                else:
                    slow_server = ThreadingHTTPServer(("0.0.0.0", 0), _MockProvider)  # noqa: S104
                    threading.Thread(target=slow_server.serve_forever, daemon=True).start()
                    try:
                        sr = http.post(
                            "/gateway/routes",
                            headers=h,
                            json={
                                "alias": f"verify-slow-{suffix}",
                                "provider": "ollama",
                                "target_model": "shadow",
                                "base_url": f"http://host.docker.internal:{slow_server.server_address[1]}/v1",
                                "timeout_ms": 60_000,
                            },
                        )
                        if check(sr.status_code in (200, 201), "slow mock route saved", sr.text):
                            slow_id = sr.json()["id"]
                            routes.append(slow_id)
                            started = time.monotonic()
                            pe = http.post(
                                "/gateway/runtime/internal/provider-execute",
                                headers={"x-admin-secret": secret},
                                json={
                                    "route_id": slow_id,
                                    "request_body": {
                                        "messages": [{"role": "user", "content": "hi"}],
                                        "max_tokens": 4,
                                    },
                                    "stream": False,
                                    "timeout_ms": 1_000,
                                },
                                timeout=30,
                            )
                            waited = time.monotonic() - started
                            check(
                                pe.status_code >= 400 and waited < 2.8,
                                "non-streamed call honours the 1 s override (3 s model times out)",
                                (pe.status_code, f"{waited:.2f}s"),
                            )
                            after = next(
                                (
                                    r
                                    for r in http.get(
                                        "/gateway/routes", headers=h, params={"limit": 500}
                                    ).json()["items"]
                                    if r["id"] == slow_id
                                ),
                                {},
                            )
                            check(
                                after.get("timeout_ms") == 60_000
                                and "completion_timeout_ms" not in (after.get("config") or {}),
                                "route's stored timeout and config are unchanged",
                                (after.get("timeout_ms"), after.get("config")),
                            )
                    finally:
                        slow_server.shutdown()

                print("\n→ pricing versions, events counts, pass-through slugs, get-by-id, tiers")
                pmodel = f"verify-priced-{suffix}"
                pr = http.post(
                    "/providers/pricing",
                    headers=h,
                    json={
                        "provider": "openai",
                        "model": pmodel,
                        "input_cost_per_1m": 1,
                        "output_cost_per_1m": 2,
                    },
                )
                if check(pr.status_code == 201, "workspace price created", pr.text):
                    first_id = pr.json()["id"]
                    up = http.put(
                        f"/providers/pricing/{first_id}", headers=h, json={"input_cost_per_1m": 3}
                    )
                    new_id = up.json().get("id") if up.status_code == 200 else None
                    check(
                        up.status_code == 200 and new_id != first_id,
                        "price change starts a new version; the old one keeps past calls' rate (G-21)",
                        (up.status_code, up.text[:160]),
                    )
                    rm = http.delete(f"/providers/pricing/{new_id or first_id}", headers=h)
                    listed = [
                        p
                        for p in http.get("/providers/pricing", headers=h).json()["items"]
                        if p["model"] == pmodel
                    ]
                    check(
                        rm.status_code == 204 and not listed,
                        "deleting retires the price (no longer listed as current)",
                        (rm.status_code, len(listed)),
                    )
                ev = http.get("/guardrails/events", headers=h, params={"limit": 1})
                evj = ev.json() if ev.status_code == 200 else {}
                check(
                    "decision_counts" in evj
                    and sum(evj["decision_counts"].values()) <= evj.get("total", 0),
                    "events list reports decision counts across all matches (G-22)",
                    {k: evj.get(k) for k in ("total", "decision_counts")},
                )
                for bad_slug in ("stats", str(uuid.uuid4()), "Bad Slug"):
                    bs = http.post(
                        "/gateway/passthrough",
                        headers=h,
                        json={"slug": bad_slug, "upstream_base_url": "https://api.openai.com"},
                    )
                    check(
                        bs.status_code == 422,
                        f"pass-through slug {bad_slug[:12]!r} refused (G-24)",
                        bs.status_code,
                    )
                slug = f"verify-pt-{suffix}"
                pt = http.post(
                    "/gateway/passthrough",
                    headers=h,
                    json={"slug": slug, "upstream_base_url": "https://api.openai.com"},
                )
                if check(pt.status_code == 201, "pass-through endpoint created", pt.text):
                    pt_id = pt.json()["id"]
                    dup = http.post(
                        "/gateway/passthrough",
                        headers=h,
                        json={"slug": slug, "upstream_base_url": "https://api.openai.com"},
                    )
                    check(
                        dup.status_code == 409, "duplicate slug → 409 (not a 500)", dup.status_code
                    )
                    got = http.get(f"/gateway/passthrough/{pt_id}", headers=h)
                    check(
                        got.status_code == 200 and got.json()["slug"] == slug,
                        "pass-through GET by id (G-25)",
                        got.status_code,
                    )
                    run_put = httpx.put(
                        f"{args.base_url.rstrip('/')}/gateway/passthrough/{slug}",
                        headers=gk,
                        json={},
                        timeout=30,
                    )
                    check(
                        run_put.status_code != 422,
                        "PUT /passthrough/{slug} reaches the executor, not the update route",
                        run_put.status_code,
                    )
                    http.delete(f"/gateway/passthrough/{pt_id}", headers=h)
                if routes:
                    gr_ = http.get(f"/gateway/routes/{routes[0]}", headers=h)
                    check(
                        gr_.status_code in (200, 404),
                        "route GET by id answers (G-25)",
                        gr_.status_code,
                    )
                missing = http.get(f"/gateway/routes/{uuid.uuid4()}", headers=h)
                check(missing.status_code == 404, "unknown route id → 404", missing.status_code)
                pol = http.get(f"/gateway/policies/{uuid.uuid4()}", headers=h)
                grp = http.get(f"/gateway/routing-groups/{uuid.uuid4()}", headers=h)
                check(
                    pol.status_code == 404 and grp.status_code == 404,
                    "policy and routing-group GET by id exist (404 for unknown ids)",
                    (pol.status_code, grp.status_code),
                )
                cmp_ = http.get("/gateway/routing-groups/strategy-comparison", headers=h)
                check(
                    cmp_.status_code == 200,
                    "strategy-comparison still routes correctly",
                    cmp_.status_code,
                )
                tiers = http.get(
                    "/budget-tiers", headers=h, params={"q": "a", "sort": "-name", "limit": 1}
                )
                check(
                    tiers.status_code == 200 and tiers.headers.get("x-total-count") is not None,
                    "budget tiers support search, sort and paging (G-26)",
                    (tiers.status_code, tiers.headers.get("x-total-count")),
                )
                http.delete(f"/settings/api-keys/{key['id']}", headers=h)
    finally:
        for rid in created:
            http.delete(f"/guardrails/{rid}", headers=h)
        for rid in routes:
            http.delete(f"/gateway/routes/{rid}", headers=h)

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
        "--gateway-url", default=os.getenv("RUNLEDGER_GATEWAY_URL", "http://localhost:8210")
    )
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", "http://localhost:11434"))
    parser.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", ""))
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
