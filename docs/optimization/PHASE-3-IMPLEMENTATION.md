# Phase 3 — Prompt/Context Compression (Implementation Plan)

> Status: **DRAFT for discussion** · Parent spec: [`SPEC-AND-ROADMAP.md`](./SPEC-AND-ROADMAP.md) · Builds on [`PHASE-2-IMPLEMENTATION.md`](./PHASE-2-IMPLEMENTATION.md) · Last updated: 2026-07-28

Phase 2 shipped the Context Compiler (dedup, tool-output compression, rerank+prune, compaction).
Phase 3 adds the stage we deliberately deferred: **LLMLingua-2 prompt compression** — a small
token-classifier that drops low-information tokens while preserving task performance. It's the most
aggressive (lossy) stage, so it is **opt-in, conservative by default, and quality-gated**.

## 1. What it does
LLMLingua-2 (Microsoft, MIT) scores each token and keeps the most informative ones to hit a target
**compression rate** (e.g. keep 50%). It runs on **CPU** (no GPU) but, unlike the rest of the
optimization layer, needs **PyTorch + transformers** — so it lives in its own opt-in container.

## 2. Architecture — dedicated `compression-svc`
- Own container `runledger-compression` (host port **8209**), CPU. Consistent with `reranker-svc`.
- `POST /compress { text, rate?, target_tokens?, model?, force_tokens? }`
  → `{ compressed_text, original_tokens, compressed_tokens, ratio }`.
- `GET /health`.
- Backed by the `llmlingua` package. Model is selectable:
  - `bert-base-multilingual` (lighter, faster CPU) — **default**.
  - `xlm-roberta-large` (higher quality, heavier).

## 3. Context Compiler integration (stage 6)
- New stage **`compress`** runs **after** compaction, **before** the final token-budget check.
- **Protects** the final user question and the most recent turns verbatim; only compresses the
  bulk context (system context blocks, retained history). Uses LLMLingua's structured/force-token
  support so instructions and key tokens survive.
- `context_compiler_config` gains:
  ```json
  {
    "stages": { "...": true, "compress": false },   // OFF by default even when the compiler is on
    "compression_model": "bert-base-multilingual",
    "compression_rate": 0.5                           // keep 50% of tokens
  }
  ```
- Fail-open: compression-svc down/error ⇒ the text passes through uncompressed.

## 4. Quality gate (hard invariant)
Compression is lossy, so:
- **Default OFF** inside the compiler `stages` even when the compiler is enabled — the operator opts in.
- Conservative default **rate 0.5**; protected spans (question + recent turns) are never compressed.
- Measured on the eval harness; auto-disable per workspace if success-rate drops below the SLA.

## 5. GUI (Gateway page compiler config popover)
Add to the existing Context Compiler config popover:
- **Prompt compression** toggle (the `compress` stage).
- **Compression model** dropdown — `bert-base-multilingual` / `xlm-roberta-large`.
- **Keep rate** field (0.1–1.0; lower = more aggressive).

## 6. Deliverables
1. `compression-svc` (LLMLingua-2, CPU) + container + compose wiring (`COMPRESSION_SVC_URL`).
2. Context Compiler `compress` stage + config fields + protected-span logic.
3. GUI additions (toggle, model dropdown, keep-rate) on the compiler config popover.
4. `examples/35_prompt_compression.py` + Postman "Compression Service" folder (via `generate_postman.py`).
5. `docs/optimization.mdx` updated with the compression stage.
6. README capability + roadmap update.

## 7. Decisions — resolved 2026-07-28
1. ✅ **Compression model:** `bert-base-multilingual` default, **GUI-selectable**; the service uses an extensible alias registry so more models can be added later.
2. ✅ **Engage policy:** fully **user-configurable** via `compress_when` — `always` | `over_budget` | `over_pct` (with `compress_budget_pct`) | off (stage toggle). GUI dropdown + a percent field.
3. ✅ **Keep rate:** **user-configurable** GUI field (`compression_rate`), sensible default 0.5.

Final `context_compiler_config` additions:
```json
{
  "stages": { "compress": false },
  "compression_model": "bert-base-multilingual",
  "compression_rate": 0.5,
  "compress_when": "over_budget",     // always | over_budget | over_pct
  "compress_budget_pct": 0.8          // used when compress_when = "over_pct"
}
```

## 8. Out of scope (later phases)
- Complexity / risk / reasoning-effort routing → Phase 4.
- Cognitive layer (memory / KG / episodes / skills) → Phase 5.
