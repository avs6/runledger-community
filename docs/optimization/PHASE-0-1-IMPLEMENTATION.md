# Phase 0 + Phase 1 — Implementation Plan

> Status: **IN PROGRESS** · Parent spec: [`SPEC-AND-ROADMAP.md`](./SPEC-AND-ROADMAP.md) · Last updated: 2026-07-27
>
> Scope of this doc: the concrete, buildable baseline for **Phase 0 (measure)** and **Phase 1
> (shared foundations + semantic cache)**, now including **vLLM + local-LLM support** as a
> first-class provider path. Everything here is containerized and follows the locked decisions
> (strict-parallel, Qdrant/Kùzu/Letta, enterprise-first, no HA/backup yet).

---

## 0. What "local LLM + vLLM support" means here

Both **Ollama** and **vLLM** expose an **OpenAI-compatible `/v1/chat/completions`** API. The RunLedger
gateway already routes OpenAI-compatible providers (`services/gateway_providers.py` maps `openai`,
`anthropic`, `ollama`, `groq`, `mistral`, `custom` → `OpenAIAdapter`). So local-LLM support is
**config + one provider alias**, not a new adapter:

- Register a **`vllm`** (and generic **`local`**) provider alias → reuse `OpenAIAdapter`.
- **Local runtimes are external — not shipped in the compose suite.** Ollama runs on the host (e.g. the
  Windows machine); vLLM runs wherever it's hosted. RunLedger only needs their base URL via
  `OLLAMA_BASE_URL` / `VLLM_BASE_URL` (from a container, the host is `http://host.docker.internal:<port>`).
- A gateway **route** with `provider: vllm|ollama|local` + `base_url` pointing at that endpoint makes any
  local OSS model a routable **model tier** (the router's future "cheap/local" tier) and the **worker model**
  for optimizer roles (compaction, compression judging, classification, consolidation).

This gives us three model classes from day one, all measurable by RunLedger:

| Class | Backend | Where it runs | Role |
|---|---|---|---|
| Frontier / mid / cheap (hosted) | OpenAI / Anthropic / Gemini | provider APIs | primary reasoning |
| Local CPU | **Ollama** (external, e.g. Windows host) | `OLLAMA_BASE_URL` | optimizer worker + cheap tier |
| Local high-throughput | **vLLM** (external server) | `VLLM_BASE_URL` | cheap tier at scale where hosted |

---

## 1. Phase 0 — Baseline & benchmark harness

**Goal:** make token/cost savings measurable *before* optimizing anything. No optimization logic ships in P0.

### 1.1 Tasks
- **T0.1** Standard benchmark task set — encode the PDF's harness workloads (e.g. "analyze this repo → find security issues → write report") as reproducible scripted agent runs (Codex CLI profile + a Claude Code run).
- **T0.2** Route clients through RunLedger:
  - Codex CLI → `model_providers.runledger` `base_url = http://localhost:8201/gateway`, `wire_api = responses`.
  - Claude Code → **assume proxy route** (per decision #6; real spike is P8).
  - Add a **local** route (`provider: ollama`, model `llama3.2:3b`) so we can baseline local vs hosted in the same harness.
- **T0.3** Metrics capture — from the existing `GatewayRequest` + `AgentRun → Span → ProviderCall/ToolCall` model, emit the baseline table: input / cached / output tokens, agent calls, cost, task success, latency.
- **T0.4** Baseline vs Optimized comparison view — a script/notebook (`scripts/bench/`) that renders the §9 table from stored runs, tagged by `harness_run_id` and `optimization_profile` (`baseline` for now).

### 1.2 Deliverables
- `scripts/bench/run_benchmark.py` — driver that executes a named workload N times against a chosen gateway profile and tags the runs.
- `scripts/bench/report.py` — pulls the runs back out of RunLedger and prints/writes the comparison table (Markdown + JSON).
- `docs/optimization/benchmark.md` — how to run it + the current baseline numbers.

### 1.3 Acceptance criteria
- One command produces a reproducible Baseline table from real runs.
- A `baseline` and a (future) `optimized` profile can be compared side-by-side by `harness_run_id`.
- Local (Ollama) and hosted routes both appear in the baseline.

---

## 2. Phase 1 — Shared foundations + semantic cache

**Goal:** stand up the substrate both lanes need, and land the first standalone token win (semantic cache).

### 2.1 New infrastructure (containers)
Added via `docker-compose.yml` (an overlay composed alongside the base stack):

| Service | Image / build | Port | Notes |
|---|---|---|---|
| `qdrant` | `qdrant/qdrant` | 6333/6334 | Vectors: semantic cache, episodes, RAG. Local volume, **no backup/HA yet**. |
| `embedding-svc` | build `apps/embedding-svc` | 8100 | fastembed ONNX (`BAAI/bge-small-en-v1.5`, 384-dim), CPU. Shared embedding model of record. |
| `semantic-cache-svc` | build `apps/semantic-cache-svc` | 8101 | Qdrant-backed, scope-aware keys. |
| `mcp-gateway` | build `apps/mcp-gateway` | 8200 | FastMCP scaffold — Lane B kickoff; empty tool registry for now. |

**Local LLM runtimes are external**, not in the suite: Ollama on the host and/or a remote vLLM server,
reached via `OLLAMA_BASE_URL` / `VLLM_BASE_URL`. Kùzu and Letta land in **Phase 5**; not stood up in P1.

### 2.2 Services

#### Embedding svc (`apps/embedding-svc`)
- `POST /embed {texts: [str], model?: str}` → `{model, dim, embeddings: [[float]]}`
- `GET /health`
- fastembed, CPU-only, model configurable via `EMBEDDING_MODEL`. This is the **one** place the embedding
  model version is pinned so cache/episodes/RAG stay comparable.

#### Semantic Cache svc (`apps/semantic-cache-svc`)
- `POST /lookup {text, scope, threshold?}` → `{hit, score, payload}`
- `POST /store {text, scope, response, prompt_tokens, completion_tokens, ttl_seconds?}` → `{stored, id}`
- `GET /health`
- **Scope key (mandatory)** = `{tenant, model, system_prompt_hash, knowledge_version, security_scope}`,
  enforced as an exact-match Qdrant filter so a hit can never cross a permission/version boundary
  (the PDF's explicit leakage warning). TTL stored as `expires_at` epoch in payload + filtered on lookup.
- Similarity threshold default **0.95** (configurable per request).
- Calls `embedding-svc` for vectors (no local embedding model — single source of truth).

#### MCP gateway (`apps/mcp-gateway`)
- FastMCP server, reachable from Claude Desktop/Code. P1 ships an empty-but-wired tool registry +
  `health` tool; real cognitive tools attach in P5.

### 2.3 Gateway integration (semantic cache in the inline pipeline — Lane A)
The current `routers/gateway.py` flow is: exact cache → route → forward → store exact cache. We insert a
**semantic-cache stage after the exact-cache miss and before routing**, gated by a per-request /
per-route flag (`body.semantic_cache` or route config), **fail-open** (svc down ⇒ skip, never error):

```
exact cache miss
   │
   ▼
semantic-cache-svc /lookup {text=canonical(messages), scope}
   │ hit (score ≥ threshold) → record GatewayRequest(cache_hit=semantic) + return payload
   │ miss → continue to route + forward
   ▼
after successful forward → semantic-cache-svc /store {...}
```

`decision_reason` gains a `semantic_cache_hit` value; metering records it distinctly from exact hits so the
benchmark can attribute the lift. **No change to correctness path** — if the cache svc is unreachable the
request proceeds exactly as today.

### 2.4 Provider changes (local LLM + vLLM)
- Register `"vllm"` and `"local"` in `_ADAPTER_MAP` (`services/gateway_providers.py`) → `OpenAIAdapter`.
- `.env.example`: add `OLLAMA_BASE_URL`, `VLLM_BASE_URL`, `LOCAL_LLM_PROVIDER`, `LOCAL_LLM_MODEL`,
  `EMBEDDING_SVC_URL`, `SEMANTIC_CACHE_SVC_URL`, `QDRANT_URL`.
- Optimizer worker model (compaction/compression/consolidation) defaults to `LOCAL_LLM_*` (Ollama), so the
  whole optimizer path can run with **zero external API dependency** and **no GPU**.

### 2.5 Deliverables
- `docker-compose.yml` (Qdrant, Ollama, vLLM[gpu], embedding-svc, semantic-cache-svc, mcp-gateway).
- `apps/embedding-svc/`, `apps/semantic-cache-svc/`, `apps/mcp-gateway/` (each: app + Dockerfile + deps).
- `services/gateway_providers.py` — `vllm`/`local` aliases.
- `routers/gateway.py` + `services/gateway.py` — semantic-cache stage (fail-open, flag-gated).
- `.env.example` additions.

### 2.6 Acceptance criteria
- `docker compose up` brings up all P1 services green (no local-LLM container in the suite).
- Semantic cache measurably lifts hit-rate over exact cache on the benchmark, with **success rate held** and cross-scope isolation verified.
- A `provider: ollama|vllm|local` route pointed at an external `OLLAMA_BASE_URL`/`VLLM_BASE_URL` serves a local model through the gateway and is metered.
- `mcp-gateway` is reachable from Claude Desktop and lists its health tool.
- Cache svc outage ⇒ requests still succeed (fail-open proven).

---

## 3. Repo layout (decision #9 — proceeding monorepo)

```
apps/
  api/                 # existing RunLedger control plane
  web/                 # existing dashboard
  embedding-svc/       # NEW — fastembed CPU
  semantic-cache-svc/  # NEW — Qdrant-backed
  mcp-gateway/         # NEW — FastMCP scaffold
infra/
  docker-compose.yml               # existing base stack
  docker-compose.optimization.yml  # NEW — optimization overlay
scripts/
  bench/               # NEW — Phase 0 harness
docs/optimization/     # spec + this plan + benchmark notes
```

New services are **standalone** (own Dockerfile + deps) rather than uv-workspace members, keeping them
independently buildable/scalable per the microservices decision. Easy to split to their own repos later.

## 4. Sequencing within P0/P1
1. P0 harness (T0.1–T0.4) → baseline numbers recorded.
2. P1 infra overlay (Qdrant, Ollama, vLLM profile) up.
3. embedding-svc → semantic-cache-svc → gateway semantic-cache stage.
4. vLLM/local provider aliases + `.env`.
5. mcp-gateway scaffold (parallel, Lane B).
6. Re-run harness with `optimization_profile=semantic_cache` → first Baseline-vs-Optimized delta.

## 5. Out of scope for P0/P1 (explicit)
- Context Compiler / compression / routing intelligence (P2–P4).
- Kùzu / Letta / episodes / skills (P5).
- HA, backup/restore, the Claude-proxy verification spike (P8).
- gRPC transport (HTTP+JSON for now; decision #10 open).
