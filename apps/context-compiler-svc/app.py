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

import json
import os
import re
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

RERANKER_SVC_URL = os.getenv("RERANKER_SVC_URL", "http://runledger-reranker:8102").rstrip("/")
COMPRESSION_SVC_URL = os.getenv("COMPRESSION_SVC_URL", "http://runledger-compression:8104").rstrip("/")
MEMORY_SVC_URL = os.getenv("MEMORY_SVC_URL", "http://runledger-memory-svc:8107").rstrip("/")
SKILL_REGISTRY_URL = os.getenv("SKILL_REGISTRY_URL", "http://runledger-skill-registry:8108").rstrip("/")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1").rstrip("/")
DEFAULT_LLM_MODEL = os.getenv("COMPILER_LLM_MODEL", "llama3.1:8b")
DEFAULT_RERANKER = os.getenv("RERANKER_MODEL", "flashrank")
DEFAULT_COMPRESSION_MODEL = os.getenv("COMPRESSION_MODEL", "bert-base-multilingual")
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
    keep_recent: int = 4  # recent messages kept verbatim by compaction/compression
    # Prompt compression (Phase 3) — opt-in, lossy.
    compression_model: str = DEFAULT_COMPRESSION_MODEL
    compression_rate: float = 0.5  # fraction of tokens to keep (lower = more aggressive)
    compress_when: str = "over_budget"  # always | over_budget | over_pct
    compress_budget_pct: float = 0.8  # used when compress_when == "over_pct"
    memory_k: int = 5  # top-k memories injected by the (opt-in) memory stage
    # Skill injection (Phase 6) — opt-in, inject-body-on-match.
    skill_k: int = 2  # max skills whose body is injected
    # Cross-encoder logit floor for a skill to be injected. Relevant matches are typically > -8,
    # clearly-irrelevant ones well below; tune per route.
    skill_min_score: float = -8.0
    # Tool filtering (Phase 6).
    tool_k: int = 8  # keep the top-k most relevant tools
    tool_filter_threshold: int = 12  # only filter when the request carries more tools than this
    tool_min_score: float | None = None  # optional absolute score floor
    always_tools: list[str] = Field(default_factory=list)  # tool names never dropped
    stages: dict[str, bool] = Field(
        default_factory=lambda: {
            "memory": False,  # opt-in: augment with recalled facts (adds context)
            "skills": False,  # opt-in: inject matched skill bodies (adds context)
            "tools": True,  # filter the tool schemas to the relevant subset
            "dedup": True,
            "tool_output": True,
            "rerank": True,
            "compaction": True,
            "compress": False,  # opt-in: prompt compression is lossy
        }
    )


class CompileRequest(BaseModel):
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None  # OpenAI-style tool definitions
    query: str | None = None
    workspace: str | None = None  # required for the memory/skills stages
    config: CompileConfig = Field(default_factory=CompileConfig)


class CompileResponse(BaseModel):
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None  # filtered tool set (None if unchanged)
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


async def _recall_memory(workspace: str, query: str, k: int) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(
                f"{MEMORY_SVC_URL}/recall",
                json={"workspace": workspace, "query": query, "k": k},
            )
            r.raise_for_status()
            return r.json().get("memories", [])
    except Exception:
        return []


async def _list_skills(workspace: str) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(f"{SKILL_REGISTRY_URL}/skills", params={"workspace": workspace})
            r.raise_for_status()
            return r.json().get("skills", [])
    except Exception:
        return []


async def _get_skill(workspace: str, name: str) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(f"{SKILL_REGISTRY_URL}/skills/{name}", params={"workspace": workspace})
            r.raise_for_status()
            return r.json()
    except Exception:
        return None


def _tool_text(tool: dict[str, Any]) -> str:
    fn = tool.get("function", tool)
    return f"{fn.get('name', '')}: {fn.get('description', '')}".strip()


def _tool_name(tool: dict[str, Any]) -> str:
    return tool.get("function", tool).get("name", "")


async def _compress(text: str, rate: float, model: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(
                f"{COMPRESSION_SVC_URL}/compress",
                json={"text": text, "rate": rate, "model": model},
            )
            r.raise_for_status()
            return r.json().get("compressed_text")
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


# ── Skill injection (opt-in, inject-body-on-match) ───────────────────────────
async def stage_skills(
    messages: list[dict[str, Any]], workspace: str | None, query: str, cfg: CompileConfig,
    dropped: list[str],
) -> list[dict[str, Any]]:
    if not workspace:
        return messages
    skills = await _list_skills(workspace)
    if not skills:
        return messages
    descriptions = [f"{s.get('name', '')}: {s.get('description', '')}" for s in skills]
    scores = await _rerank(query, descriptions, cfg.reranker_model)
    if scores is None:
        return messages
    ranked = sorted(range(len(skills)), key=lambda k: scores[k], reverse=True)
    injected = []
    for k in ranked[: cfg.skill_k]:
        if scores[k] < cfg.skill_min_score:
            break
        full = await _get_skill(workspace, skills[k]["name"])
        if full and full.get("content"):
            injected.append(f"Relevant skill — {full['name']}:\n{full['content']}")
    if not injected:
        return messages
    dropped.append(f"skills: injected {len(injected)} matched skill(s)")
    return [{"role": "system", "content": "\n\n".join(injected)}, *messages]


# ── Tool filtering (keep the top-k relevant tools) ───────────────────────────
async def stage_tools(
    tools: list[dict[str, Any]] | None, query: str, cfg: CompileConfig, dropped: list[str]
) -> tuple[list[dict[str, Any]] | None, int]:
    if not tools or len(tools) <= cfg.tool_filter_threshold:
        return tools, 0
    always = set(cfg.always_tools)
    candidates = [(i, t) for i, t in enumerate(tools) if _tool_name(t) not in always]
    scores = await _rerank(query, [_tool_text(t) for _, t in candidates], cfg.reranker_model)
    if scores is None:
        return tools, 0
    order = sorted(range(len(candidates)), key=lambda j: scores[j], reverse=True)
    keep_idx = set()
    for j in order[: cfg.tool_k]:
        if cfg.tool_min_score is not None and scores[j] < cfg.tool_min_score:
            break
        keep_idx.add(candidates[j][0])
    keep = [i for i in range(len(tools)) if _tool_name(tools[i]) in always or i in keep_idx]
    kept = [tools[i] for i in keep]
    saved = sum(est(json.dumps(tools[i])) for i in range(len(tools)) if i not in set(keep))
    if len(kept) < len(tools):
        dropped.append(f"tools: kept {len(kept)}/{len(tools)} tools by relevance")
    return kept, saved


# ── Stage 0: memory recall (opt-in, augments context) ────────────────────────
async def stage_memory(
    messages: list[dict[str, Any]], workspace: str | None, query: str, cfg: CompileConfig,
    dropped: list[str],
) -> list[dict[str, Any]]:
    if not workspace:
        return messages
    mems = await _recall_memory(workspace, query, cfg.memory_k)
    if not mems:
        return messages
    block = "Relevant memory (recalled facts/decisions):\n" + "\n".join(
        f"- [{m.get('kind', 'fact')}] {m.get('text', '')}" for m in mems
    )
    dropped.append(f"memory: injected {len(mems)} recalled item(s)")
    return [{"role": "system", "content": block}, *messages]


# ── Stage 6: prompt compression (LLMLingua-2, opt-in, lossy) ──────────────────
async def stage_compress(
    messages: list[dict[str, Any]], cfg: CompileConfig, dropped: list[str]
) -> list[dict[str, Any]]:
    total = total_tokens(messages)
    when = cfg.compress_when
    if when == "over_budget" and total <= cfg.token_budget:
        return messages
    if when == "over_pct" and total <= cfg.token_budget * cfg.compress_budget_pct:
        return messages
    # else "always" (or over-threshold met) → engage
    protected = _protected_indices(messages, cfg.keep_recent)
    out: list[dict[str, Any]] = []
    compressed_any = False
    for i, m in enumerate(messages):
        content = str(m.get("content", ""))
        if i in protected or est(content) < 100:
            out.append(m)
            continue
        c = await _compress(content, cfg.compression_rate, cfg.compression_model)
        if c is not None and c != content:
            compressed_any = True
            nm = dict(m)
            nm["content"] = c
            out.append(nm)
        else:
            out.append(m)
    if compressed_any:
        dropped.append(f"compress: LLMLingua-2 compressed context (rate={cfg.compression_rate})")
    return out


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "reranker": RERANKER_SVC_URL, "llm": OLLAMA_BASE_URL}


@app.get("/health/ready")
def readiness() -> dict[str, object]:
    return health()


class SelectToolsRequest(BaseModel):
    query: str
    tools: list[dict[str, Any]]
    config: CompileConfig = Field(default_factory=CompileConfig)


@app.post("/select-tools")
async def select_tools(req: SelectToolsRequest) -> dict[str, Any]:
    """Return the subset of tools relevant to the query (same reranker path as the compiler)."""
    dropped: list[str] = []
    tools, saved = await stage_tools(req.tools, req.query, req.config, dropped)
    return {"tools": tools, "saved_tokens": saved, "note": dropped}


@app.post("/compile", response_model=CompileResponse)
async def compile_context(req: CompileRequest) -> CompileResponse:
    messages = req.messages
    cfg = req.config
    before = total_tokens(messages)
    query = req.query or _last_user(messages)
    dropped: list[str] = []
    per_stage: dict[str, int] = {}
    degraded = False
    tools = req.tools

    # Tool filtering engages on tool COUNT (independent of the message token threshold).
    if cfg.stages.get("tools", True) and tools:
        try:
            tools, tool_saved = await stage_tools(tools, query, cfg, dropped)
            if tool_saved:
                per_stage["tools"] = tool_saved
        except Exception:
            degraded = True

    # Below the engage threshold (and threshold != 0) → skip the message stages.
    if cfg.token_threshold and before <= cfg.token_threshold:
        return CompileResponse(
            messages=messages,
            tools=tools if tools is not req.tools else None,
            token_report={"before": before, "after": before, "saved": 0, "per_stage": per_stage},
            dropped=dropped,
        )

    import inspect

    async def run(name: str, fn):
        nonlocal messages, degraded
        # All stages default on, except memory + skills + compress (opt-in).
        if not cfg.stages.get(name, name not in ("compress", "memory", "skills")):
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

    await run("memory", lambda: stage_memory(messages, req.workspace, query, cfg, dropped))
    await run("skills", lambda: stage_skills(messages, req.workspace, query, cfg, dropped))
    await run("dedup", lambda: stage_dedup(messages, dropped))
    await run("tool_output", lambda: stage_tool_output(messages, cfg))
    await run("rerank", lambda: stage_rerank(messages, query, cfg, dropped))
    await run("compaction", lambda: stage_compaction(messages, cfg, dropped))
    await run("compress", lambda: stage_compress(messages, cfg, dropped))

    after = total_tokens(messages)
    return CompileResponse(
        messages=messages,
        tools=tools if tools is not req.tools else None,
        token_report={"before": before, "after": after, "saved": before - after, "per_stage": per_stage},
        dropped=dropped,
        degraded=degraded,
    )


def _last_user(messages: list[dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content", ""))
    return str(messages[-1].get("content", "")) if messages else ""
