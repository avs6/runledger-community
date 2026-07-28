# Phase 2 — Context Compiler v1 (Implementation Plan)

> Status: **DRAFT for discussion** · Parent spec: [`SPEC-AND-ROADMAP.md`](./SPEC-AND-ROADMAP.md) · Builds on [`PHASE-0-1-IMPLEMENTATION.md`](./PHASE-0-1-IMPLEMENTATION.md) · Last updated: 2026-07-27
>
> The PDF calls the Context Compiler *"the #1 feature I'd add."* It's the biggest single token
> win: intercept an 80K-token request and forward ~25K effective tokens, without changing the
> reasoning model. This plan covers a **v1** that is safe (fail-open, quality-gated, default-off)
> and fits the product exactly like the semantic-cache toggle shipped in Phase 1.
>
> **Decisions locked (2026-07-27):**
> 1. **Ship all five stages** in v1 (dedup, tool-output compression, rerank+prune, compaction, token budget).
> 2. **Dedicated `reranker-svc`** container (not folded into embedding-svc).
> 3. **Compiler LLM model is a GUI-selectable, per-route field** — a dropdown of the workspace's local models (Ollama/vLLM/local rows from `provider_pricing`), not a hardcoded default.
> 4. **Generic RAG handling** — rerank all content blocks against the current question; no client tagging required.

---

## 1. What we already have (Phase 1 foundations we build on)

- **embedding-svc** (fastembed / ONNX, CPU) — the shared embedding model of record.
- **Qdrant** + **semantic-cache-svc** — scope-isolated near-duplicate cache, wired into the gateway (default-off, fail-open) with a **per-route GUI toggle** (`semantic_cache_enabled`).
- **External local LLMs** (Ollama on the host / vLLM) reachable via `OLLAMA_BASE_URL` / `VLLM_BASE_URL`, routable as gateway providers. Your Ollama catalog is already in `provider_pricing`.
- The gateway pipeline: exact cache → **semantic cache** → route → forward → meter. Phase 2 inserts the compiler **after the semantic-cache miss, before routing**.

---

## 2. What the Context Compiler does (v1)

Input to the gateway is an OpenAI-compatible `messages` array. The compiler transforms it into a
smaller, equivalent `messages` array **only when the request exceeds a size threshold**, running
these stages in order — each individually toggleable, each fail-open:

| # | Stage | What it does | Engine |
|---|-------|--------------|--------|
| 1 | **Dedup** | Remove exact / near-duplicate content blocks repeated across messages (common in agent loops that resend context). | hashing + embedding-svc |
| 2 | **Tool-output compression** | Collapse `role: tool` (and oversized) messages — dedupe log lines, head+tail truncation, aggregate; optionally summarize very large outputs. | rules + local LLM |
| 3 | **Rerank + prune** | Rerank content blocks against the current user question with a cross-encoder; drop blocks below a relevance threshold, keep within a per-stage token budget. Handles RAG/context bloat generically. | reranker (FlashRank/BGE) |
| 4 | **Conversation compaction** | When history exceeds a token budget, summarize older turns into a compact checkpoint (goal / decisions / facts / artifacts / pending), keep recent turns verbatim. | local LLM |
| 5 | **Token budgeting** | Enforce an overall input-token ceiling and emit a `token_report` (before/after per stage). | — |

**Prompt/context compression (LLMLingua-2) is deliberately deferred to Phase 3** — it's the heaviest
stage and deserves its own quality gating.

```
84K-token request
   │  (semantic-cache miss)
   ▼
Context Compiler
   ├─ dedup                 -4K
   ├─ tool-output compress  -13K
   ├─ rerank + prune        -14K
   ├─ compaction            -19K
   └─ token budget check
   ▼
~34K effective tokens  →  route → provider
        │
        ▼  token_report {before, after, per-stage} → GatewayRequest + OTel
```

---

## 3. Architecture

### 3.1 New service — `context-compiler-svc`
- FastAPI, CPU-only, container `runledger-context-compiler` (host port **8207**).
- `POST /compile { messages, query?, config, scope }` → `{ messages, token_report, dropped[] }`.
- `GET /health`.
- Orchestrates the five stages; calls **embedding-svc** (dedup/similarity), the **reranker**, and the **local LLM** (Ollama) for compaction / tool summaries.
- **Stateless** and horizontally scalable. Fail-open: any error → return the original messages untouched with a `degraded` flag.

### 3.2 Reranker — dedicated `reranker-svc`, model GUI-selectable (decisions #2, #5)
A cross-encoder served by its own container `runledger-reranker` (host port **8208**), CPU-only.
`POST /rerank { query, passages, model? }` → scored/ordered passages. It **loads multiple reranker
backends** and picks per request:
- **FlashRank** (Apache-2.0, tiny, fastest) — the default.
- A **BGE reranker** (e.g. `BAAI/bge-reranker-base`/`-v2-m3`, MIT) — higher quality, heavier.

The active model is a **per-route GUI dropdown** (`context_compiler_config.reranker_model`), env
fallback `RERANKER_MODEL`. Independently scalable and separated from the embedding model of record.

### 3.3 Local model for summarization / compaction — GUI-selectable per route (decision #3)
Stages 2 and 4 call your **external Ollama** (`OLLAMA_BASE_URL`) — no new runtime. **The model is not
hardcoded**: it's a per-route setting chosen from a dashboard dropdown populated with the workspace's
local models (the `provider_pricing` rows where `provider ∈ {ollama, vllm, local}` — the same catalog
that now lists your installed Ollama models). Stored in `context_compiler_config.model`; falls back to
`COMPILER_LLM_MODEL` env if unset. This reuses the pricing catalog wired in Phase 1.

### 3.4 Gateway integration (Lane A — inline)
- New per-route control **`context_compiler_enabled`** (+ a small `context_compiler_config` JSON:
  token budget, per-stage on/off, aggressiveness), mirroring `semantic_cache_enabled` exactly
  (model column, migration, create/update/response schema, gateway wiring).
- Effective switch = per-request flag **OR** route toggle. Runs after the semantic-cache miss,
  before `route_and_forward`.
- **Engage threshold is configurable** (`context_compiler_config.token_threshold`, a GUI field):
  the compiler only runs when the estimated input tokens exceed it, so small requests skip the work.
  **`0` means always engage** (no threshold). Default a sensible value (e.g. ~2000 tokens).
- Records the `token_report` on the `GatewayRequest` and as nested OTel spans, so savings are
  attributable per stage — this is what makes the benchmark real.

### 3.5 MCP exposure (Lane B)
Expose the same compiler as an MCP tool on `runledger-mcp-gateway` (`compile_context`) so Claude
Desktop / Code can compact context on demand. Same service, two entry points.

### 3.6 GUI (fits the Phase-1 pattern)
On the dashboard **Gateway page**, next to the "Semantic Cache" / "Cache ON/OFF" controls:
- A **"Context Compiler"** checkbox on the add-route form.
- An inline **"Compiler ON/OFF"** badge on each route that flips it live.
- A config popover with:
  - **Compaction model** dropdown (decision #3) — the workspace's local models from `/providers/pricing` filtered to `ollama` / `vllm` / `local`.
  - **Reranker model** dropdown (decision #5) — `flashrank` (default) or a BGE reranker.
  - **Engage threshold** (number, tokens) — `0` = always engage; requests below it skip the compiler.
  - **Token budget** + per-stage on/off toggles.

`context_compiler_config` (JSON on the route):

```json
{
  "model": "llama3.1:8b",          // compaction / tool-summary LLM (local)
  "reranker_model": "flashrank",   // "flashrank" | "bge-reranker-base" | ...
  "token_threshold": 2000,         // 0 = always engage
  "token_budget": 32000,           // overall input ceiling after compile
  "stages": { "dedup": true, "tool_output": true, "rerank": true, "compaction": true }
}
```

---

## 4. Cross-cutting (unchanged invariants from the spec)

- **Fail-open everywhere** — compiler down/slow/erroring ⇒ forward the original request; never break a good call.
- **Default-off** — opt-in per request or per route, like semantic cache.
- **Quality floor is a hard gate** — every stage is measured on the eval harness; auto-disable per-workspace if success-rate drops below the SLA. "Cost reduction *subject to* a quality floor."
- **Only compress when it pays** — requests under the size threshold pass through untouched (no latency tax on small calls).
- **No GPU** — FlashRank + small BERT + Ollama are all CPU.
- **Observability** — `token_report` (before/after per stage) on every compiled request.

---

## 5. Deliverables & sequencing

1. **`reranker-svc`** container (FlashRank/BGE cross-encoder, CPU) — `POST /rerank`, host port 8208.
2. **context-compiler-svc** (host port 8207) implementing all five stages (dedup → tool-output compression → rerank+prune → compaction → token budget), each individually toggleable and fail-open, emitting `token_report`.
3. **Gateway wiring** — `context_compiler_enabled` + `context_compiler_config` (JSON: `model`, `reranker_model`, `token_threshold`, `token_budget`, per-stage flags) on `gateway_routes` (model column + migration + create/update/response schema), mirroring the semantic-cache toggle. Runs after semantic-cache miss, before routing; engages only when estimated tokens > `token_threshold` (0 = always).
4. **GUI** on the Gateway page — Context Compiler checkbox + inline ON/OFF badge + config popover: **compaction-model dropdown** (from `/providers/pricing`, filtered to ollama/vllm/local), **reranker-model dropdown** (flashrank/BGE), **engage-threshold** field (0 = always), token budget, per-stage toggles.
5. **MCP `compile_context` tool** on runledger-mcp-gateway (Lane B).
6. **Benchmark** — extend `scripts/bench` to compare Baseline vs `semantic_cache` vs `context_compiler` (input/cached/output tokens, cost, task success, latency) proving reduction at held quality.
7. **Example** `examples/34_context_compiler.py` + **Postman** requests, and update the README capability list.

## 6. Decisions — resolved 2026-07-27

1. ✅ **v1 scope:** all five stages.
2. ✅ **Reranker:** dedicated `reranker-svc`.
3. ✅ **Compaction/summarization model:** GUI-selectable per route (dropdown of the workspace's local models); env fallback `COMPILER_LLM_MODEL`.
4. ✅ **RAG handling:** generic rerank against the current question — no client tagging.
5. ✅ **Reranker model:** GUI-selectable per route — `flashrank` (default) or a BGE reranker; env fallback `RERANKER_MODEL`.
6. ✅ **Engage threshold:** GUI-configurable per route (`token_threshold`); **`0` = always engage**; default ~2000 tokens.

## 7. Out of scope for Phase 2 (later phases)
- Prompt/context compression via LLMLingua-2 → **Phase 3**.
- Complexity / risk / reasoning-effort routing → **Phase 4**.
- Cognitive layer (memory / KG / episodes / skills) that the compiler *pulls from* → **Phase 5**.
- Dynamic MCP tool filtering → **Phase 6**.
