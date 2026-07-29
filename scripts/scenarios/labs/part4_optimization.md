# Part 4 · Optimization layer

*Prerequisite: Part 1 done. Use the **AI Test Team** key for this part — it's the natural
owner of gateway/routing experiments.*

RunLedger's optimization features mostly live as **routing policies on a Gateway route**.
The pattern is identical every time:

1. Add / edit a route policy in the **Gateway** GUI (configs in
   [`samples/routing_policies.md`](./samples/routing_policies.md)).
2. Drive traffic **through that alias** with the reusable agent:
   ```bash
   LAB_GATEWAY_ALIAS=<alias> LAB_RUNS=30 LAB_FEATURE_TAG=policy-test python traffic_gen.py
   ```
3. Read the effect on the **Gateway** request log / route stats.

> Base URL for any Ollama target must be `http://host.docker.internal:11434/v1`.

---

## 4.1 · Semantic cache

Apply **Policy 2** (semantic cache ON) on alias `cached-chat`, then run traffic through it.

🔎 Re-worded but equivalent prompts return instantly with
`decision_reason = semantic_cache_hit` — no model round-trip, near-zero latency and cost.

---

## 4.2 · Context compiler (+ prompt compression)

Apply **Policy 4** (context compiler ON) on a route. The compiler shrinks oversized
`messages` in stages: dedup → tool-output compression → rerank/prune → compaction → token
budget. **Prompt compression (LLMLingua-2)** is the optional final lossy stage — enable it in
the compiler config with `"stages": { ..., "compress": true }`.

🔎 The request log shows a **token-saved report** per stage. Bloated prompts cost less
without you touching the agent.

---

## 4.3 · Intelligent routing

Apply **Policy 3** (intelligent routing ON with the tier matrix) on a route. Each request is
classified on complexity × risk and sent to the matching tier's model.

🔎 Simple/low-risk prompts resolve to the **cheap** tier; hard/high-risk ones to **frontier** —
visible per request. You spend frontier money only where it's warranted.

---

## 4.4 · Flywheel (cost × quality SLA)

**Goal:** let RunLedger recommend the cheapest config that still holds your quality bar.

1. Generate traffic **with outcomes and scores** so the flywheel has something to learn from:
   ```bash
   LAB_FEATURE_TAG=support-chat LAB_RUNS=60 LAB_SCORE=true LAB_OUTCOME=true python traffic_gen.py
   ```
2. Open **Flywheel**. Configure the SLA (e.g. min quality `0.85`), segment by outcome type,
   mode = *approval* (propose, don't auto-apply).
3. **Run** the loop. Review the **recommendations** — e.g. "segment X can move to a cheaper
   model at −70% cost, quality still ≥ SLA." Apply or dismiss.

🔎 This closes the loop: observe → recommend → (approve) → cheaper traffic that still meets
quality. It needs traffic **plus** outcomes/scores, which is why step 1 enables both.

---

## 4.5 · Cognitive layer *(advanced, optional)*

Persistent **memory**, a **knowledge graph**, and a **skill registry** — workspace-scoped and
exposed over MCP so multiple agents share them. These are service/MCP-driven rather than
GUI + traffic-gen, so they're out of the main flow. To explore them, see the repo example
[`examples/37_cognitive_layer.py`](../../../../examples/37_cognitive_layer.py).

---

✅ **End of Part 4.** You've cached near-duplicates, compressed context, routed by
complexity, and let the flywheel recommend cheaper configs. Next:
**[Part 5 · Governance & Control](./part5_governance.md)**.
