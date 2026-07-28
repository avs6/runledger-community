"""
Context Compiler service (Phase 2).

Shrinks an OpenAI-compatible `messages` array *before* it reaches the model, in five toggleable,
fail-open stages:

  1. dedup            — drop exact-duplicate message blocks (agent loops resend context)
  2. tool_output      — compress role=tool / oversized outputs (line-dedupe, head+tail, LLM summary)
  3. rerank           — rerank context chunks against the question, prune low-relevance overflow
  4. compaction       — summarize older turns into a checkpoint when over the token budget
  5. token_budget     — final hard trim + emit a token_report

Every stage is wrapped so any failure leaves the input for that stage untouched (fail-open).
Only engages when estimated input tokens exceed `config.token_threshold` (0 = always).

Calls out to: reranker-svc (/rerank), an external local LLM (Ollama, OpenAI-compatible) for
compaction / large tool summaries. Token counts are estimates (~4 chars/token).

Endpoints
---------
GET  /health
POST /compile { messages, query?, config } -> { messages, token_report, dropped[] }
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

RERANKER_SVC_URL = os.getenv("RERANKER_SVC_URL", "http://runledger-reranker:8102").rstrip("/")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1").rstrip("/")
DEFAULT_LLM_MODEL = os.getenv("COMPILER_LLM_MODEL", "llama3.1:8b")
DEFAULT_RERANKER = os.getenv("RERANKER_MODEL", "flashrank")
TIMEOUT = float(os.getenv("COMPILER_TIMEOUT_SECONDS", "20"))

app = FastAPI(title="RunLedger Context Compiler", version="0.1.0")


# ── Token estimate ────────────────────────────────────────────────────────────
def est(text: str) -> int:
    return max(1, len(text) // 4)


def total_tokens(messages: list[dict[str, Any]]) -> int:
    return sum(est(str(m.get("content", ""))) for m in messages)


# ── Schemas ───────────────────────────────────────────────────────────────────
class CompileConfig(BaseModel):
    model: str = DEFAULT_LLM_MODEL
    reranker_model: str = DEFAULT_RERANKER
    token_threshold: int = 2000  # 0 = always engage
    token_budget: int = 32000
    keep_recent: int = 4  # recent messages kept verbatim by compaction
    stages: dict[str, bool] = Field(
        default_factory=lambda: {
            "dedup": True,
            "tool_output": True,
            "rerank": True,
            "compaction": True,
        }
    )


class CompileRequest(BaseModel):
    messages: list[dict[str, Any]]
    query: str | None = None
    config: CompileConfig = Field(default_factory=CompileConfig)


class CompileResponse(BaseModel):
    messages: list[dict[str, Any]]
    token_report: dict[str, Any]
    dropped: list[str]
    degraded: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def _split_chunks(text: str, max_chars: int = 1200) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[str] = []
    for p in parts:
        if len(p) <= max_chars:
            out.append(p)
            continue
        buf = ""
        for sent in re.split(r"(?<=[.!?])\s+", p):
            if len(buf) + len(sent) > max_chars and buf:
                out.append(buf.strip())
                buf = ""
            buf += sent + " "
        if buf.strip():
            out.append(buf.strip())
    return out


async def _rerank(query: str, passages: list[str], model: str) -> list[float] | None:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(
                f"{RERANKER_SVC_URL}/rerank",
                json={"query": query, "passages": passages, "model": model},
            )
            r.raise_for_status()
            data = r.json()
        scores = [0.0] * len(passages)
        for item in data.get("results", []):
            scores[item["index"]] = item["score"]
        return scores
    except Exception:
        return None


async def _llm_summarize(text: str, model: str, instruction: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(
                f"{OLLAMA_BASE_URL}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 512,
                    "temperature": 0.1,
                    "stream": False,
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


# ── Stage 1: dedup ────────────────────────────────────────────────────────────
def stage_dedup(messages: list[dict[str, Any]], dropped: list[str]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    last_idx = len(messages) - 1
    for i, m in enumerate(messages):
        key = (str(m.get("role")), _norm(m.get("content", "")))
        # Never drop the final message; only dedup substantial repeated blocks.
        if i != last_idx and key in seen and est(str(m.get("content", ""))) > 20:
            dropped.append(f"dedup: duplicate {m.get('role')} block")
            continue
        seen.add(key)
        out.append(m)
    return out


# ── Stage 2: tool-output compression ──────────────────────────────────────────
async def stage_tool_output(
    messages: list[dict[str, Any]], cfg: CompileConfig
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        content = str(m.get("content", ""))
        is_tool = m.get("role") in ("tool", "function")
        if not (is_tool or len(content) > 4000):
            out.append(m)
            continue
        # 1) collapse consecutive duplicate lines
        lines = content.splitlines()
        deduped: list[str] = []
        for ln in lines:
            if deduped and deduped[-1] == ln:
                continue
            deduped.append(ln)
        compressed = "\n".join(deduped)
        # 2) very large → LLM summary, else head+tail truncation
        if len(compressed) > 12000:
            summary = await _llm_summarize(
                compressed[:16000],
                cfg.model,
                "Summarize this tool/log output. Keep errors, anomalies, key values, and counts. "
                "Be terse; drop repetition and boilerplate.",
            )
            if summary:
                compressed = f"[tool output summarized]\n{summary}"
            else:
                compressed = _head_tail(compressed)
        elif len(compressed) > 4000:
            compressed = _head_tail(compressed)
        nm = dict(m)
        nm["content"] = compressed
        out.append(nm)
    return out


def _head_tail(text: str, head: int = 2000, tail: int = 1000) -> str:
    if len(text) <= head + tail:
        return text
    omitted = len(text) - head - tail
    return f"{text[:head]}\n… [{omitted} chars omitted] …\n{text[-tail:]}"


# ── Stage 3: rerank + prune ───────────────────────────────────────────────────
async def stage_rerank(
    messages: list[dict[str, Any]], query: str, cfg: CompileConfig, dropped: list[str]
) -> list[dict[str, Any]]:
    if total_tokens(messages) <= cfg.token_budget:
        return messages  # nothing to prune
    protected = _protected_indices(messages, cfg.keep_recent)
    out: list[dict[str, Any]] = []
    for i, m in enumerate(messages):
        content = str(m.get("content", ""))
        if i in protected or est(content) < 200:
            out.append(m)
            continue
        chunks = _split_chunks(content)
        if len(chunks) < 2:
            out.append(m)
            continue
        scores = await _rerank(query, chunks, cfg.reranker_model)
        if scores is None:
            out.append(m)  # reranker down → keep as-is
            continue
        ranked = sorted(range(len(chunks)), key=lambda k: scores[k], reverse=True)
        # keep highest-scoring chunks until this message's share of budget is filled
        share = max(400, cfg.token_budget // max(1, len(messages)))
        kept_idx, used = [], 0
        for k in ranked:
            t = est(chunks[k])
            if used + t > share and kept_idx:
                break
            kept_idx.append(k)
            used += t
        dropped_n = len(chunks) - len(kept_idx)
        if dropped_n:
            dropped.append(f"rerank: pruned {dropped_n} low-relevance chunk(s) from {m.get('role')}")
        nm = dict(m)
        nm["content"] = "\n\n".join(chunks[k] for k in sorted(kept_idx))
        out.append(nm)
    return out


def _protected_indices(messages: list[dict[str, Any]], keep_recent: int) -> set[int]:
    n = len(messages)
    prot = set(range(max(0, n - keep_recent), n))  # recent turns
    if messages and messages[0].get("role") == "system":
        prot.add(0)  # first system message (core instructions)
    return prot


# ── Stage 4: conversation compaction ──────────────────────────────────────────
async def stage_compaction(
    messages: list[dict[str, Any]], cfg: CompileConfig, dropped: list[str]
) -> list[dict[str, Any]]:
    if total_tokens(messages) <= cfg.token_budget:
        return messages
    protected = _protected_indices(messages, cfg.keep_recent)
    middle = [(i, m) for i, m in enumerate(messages) if i not in protected]
    if len(middle) < 2:
        return messages
    transcript = "\n".join(f"{m.get('role')}: {str(m.get('content', ''))}" for _, m in middle)
    summary = await _llm_summarize(
        transcript[:20000],
        cfg.model,
        "Compact this earlier conversation into a checkpoint. Capture: goal, decisions made, "
        "important facts, artifacts/paths, and pending tasks. Bullet points, no fluff.",
    )
    if not summary:
        # fail-open: drop oldest middle turns to fit budget
        keep = messages[:]
        for i, _ in middle:
            if total_tokens(keep) <= cfg.token_budget:
                break
            keep[i] = {**messages[i], "content": ""}
        dropped.append("compaction: LLM unavailable — trimmed oldest turns")
        return [m for m in keep if str(m.get("content", "")).strip()]
    checkpoint = {"role": "system", "content": f"[Earlier conversation summary]\n{summary}"}
    dropped.append(f"compaction: summarized {len(middle)} older turn(s) into a checkpoint")
    rebuilt: list[dict[str, Any]] = []
    inserted = False
    for i, m in enumerate(messages):
        if i in protected:
            rebuilt.append(m)
        elif not inserted:
            rebuilt.append(checkpoint)
            inserted = True
    return rebuilt


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "reranker": RERANKER_SVC_URL, "llm": OLLAMA_BASE_URL}


@app.post("/compile", response_model=CompileResponse)
async def compile_context(req: CompileRequest) -> CompileResponse:
    messages = req.messages
    cfg = req.config
    before = total_tokens(messages)

    # Below the engage threshold (and threshold != 0) → pass through untouched.
    if cfg.token_threshold and before <= cfg.token_threshold:
        return CompileResponse(
            messages=messages,
            token_report={"before": before, "after": before, "saved": 0, "per_stage": {}},
            dropped=[],
        )

    query = req.query or _last_user(messages)
    dropped: list[str] = []
    per_stage: dict[str, int] = {}
    degraded = False

    import inspect

    async def run(name: str, fn):
        nonlocal messages, degraded
        if not cfg.stages.get(name, True):
            return
        pre = total_tokens(messages)
        try:
            result = fn()
            if inspect.isawaitable(result):
                result = await result
            messages = result
        except Exception:
            degraded = True
            return
        per_stage[name] = pre - total_tokens(messages)

    await run("dedup", lambda: stage_dedup(messages, dropped))
    await run("tool_output", lambda: stage_tool_output(messages, cfg))
    await run("rerank", lambda: stage_rerank(messages, query, cfg, dropped))
    await run("compaction", lambda: stage_compaction(messages, cfg, dropped))

    after = total_tokens(messages)
    return CompileResponse(
        messages=messages,
        token_report={"before": before, "after": after, "saved": before - after, "per_stage": per_stage},
        dropped=dropped,
        degraded=degraded,
    )


def _last_user(messages: list[dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content", ""))
    return str(messages[-1].get("content", "")) if messages else ""
