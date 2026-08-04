# Part 4 - Optimization Layer

*Prerequisite: Part 1 done. Configure Gateway routes as an **org admin**, then use the
**AI Test Team** workspace key for traffic.*

RunLedger's optimization features mostly live as **routing policies on a Gateway route**.
The pattern is identical every time:

1. As an org admin, add or edit a route policy in the **Gateway** GUI. Use the examples in
   [`samples/routing_policies.md`](./samples/routing_policies.md).
2. Switch `agents/.env` to the AI Test Team workspace key and drive traffic through that alias:
   ```bash
   LAB_GATEWAY_ALIAS=<alias> LAB_RUNS=30 LAB_FEATURE_TAG=policy-test python traffic_gen.py
   ```
3. Read the effect on the **Gateway** request log / route stats.

> Base URL for any Ollama target must be `http://host.docker.internal:11434/v1`.

---

## 4.1 - Exact Prompt Cache

**Goal:** prove the cheapest cache path: byte-for-byte identical prompts.

1. Create or edit an alias `exact-cache-chat` with the same Ollama target from Lab 03.
2. Enable exact cache on the route, or send requests with `cache=true`.
3. Run the same prompt twice:
   ```bash
   LAB_GATEWAY_ALIAS=exact-cache-chat LAB_RUNS=2 LAB_FEATURE_TAG=exact-cache python traffic_gen.py
   ```

Verify on **Gateway -> Requests**: the second request should show a cache hit / cache decision.

---

## 4.2 - Semantic Cache

**Goal:** catch paraphrases, not just identical text.

Apply **Policy 2** (semantic cache ON) on alias `cached-chat`, then run traffic through it:

```bash
LAB_GATEWAY_ALIAS=cached-chat LAB_RUNS=30 LAB_FEATURE_TAG=semantic-cache python traffic_gen.py
```

Verify on **Gateway -> Requests**: reworded but equivalent prompts should return with
`decision_reason = semantic_cache_hit`, lower latency, and near-zero model cost.

---

## 4.3 - Context Compiler

**Goal:** shrink oversized prompts before the model sees them.

Apply **Policy 4** (context compiler ON) on alias `compiled-chat`. Enable these stages:

```json
{
  "stages": {
    "dedup": true,
    "tool_output": true,
    "rerank": true,
    "compaction": true,
    "compress": false,
    "tools": false,
    "skills": false
  },
  "token_threshold": 0,
  "token_budget": 32000,
  "keep_recent": 4
}
```

Then run:

```bash
LAB_GATEWAY_ALIAS=compiled-chat LAB_RUNS=20 LAB_FEATURE_TAG=context-compiler python traffic_gen.py
```

Verify on **Gateway -> Requests**: compiled requests should include a `token_report` showing
before/after token counts and savings by stage.

---

## 4.4 - Prompt Compression

**Goal:** test the aggressive, opt-in LLMLingua-2 stage.

Edit `compiled-chat` and turn on prompt compression:

```json
{
  "stages": {
    "dedup": true,
    "tool_output": true,
    "rerank": true,
    "compaction": true,
    "compress": true
  },
  "compression_rate": 0.55,
  "compression_model": "bert-base-multilingual"
}
```

Run a small batch:

```bash
LAB_GATEWAY_ALIAS=compiled-chat LAB_RUNS=10 LAB_FEATURE_TAG=prompt-compression python traffic_gen.py
```

Verify: the `token_report` includes compression savings. If quality drops in Part 3 evaluation,
raise the keep rate or turn compression off for that route.

---

## 4.5 - Intelligent Routing

**Goal:** spend frontier-model money only on hard or risky requests.

Apply **Policy 3** (intelligent routing ON with the tier matrix) on alias `auto-chat`. Each
request is classified by complexity and business risk, then sent to the configured tier.

```bash
LAB_GATEWAY_ALIAS=auto-chat LAB_RUNS=30 LAB_FEATURE_TAG=intelligent-routing python traffic_gen.py
```

Verify on **Gateway -> Requests**: simple/low-risk prompts resolve to the cheap tier; hard/high-risk
ones resolve to the frontier tier. The route decision should name the selected tier or routing reason.

---

## 4.6 - Dynamic Tool Filtering

**Goal:** keep only the tools relevant to this request instead of sending a huge MCP/tool catalog.

1. On a route alias `tool-filter-chat`, enable **Context Compiler** and turn on **Tool filtering**:
   ```json
   {
     "stages": { "tools": true, "skills": false },
     "tool_k": 4,
     "tool_filter_threshold": 8,
     "always_tools": ["send_slack"]
   }
   ```
2. Use the sample catalog in [`samples/tool_filtering_catalog.json`](./samples/tool_filtering_catalog.json).
3. If you want a quick service-level smoke test without an MCP client, call the same filtering path directly:
   ```powershell
   $tools = Get-Content .\samples\tool_filtering_catalog.json -Raw | ConvertFrom-Json
   $body = @{
     query = 'The customer wants a refund for order 123 and asks why their invoice changed.'
     tools = $tools
     config = @{
       stages = @{ tools = $true }
       tool_k = 4
       tool_filter_threshold = 8
       always_tools = @('send_slack')
     }
   } | ConvertTo-Json -Depth 20
   Invoke-RestMethod -Method Post -Uri http://localhost:8207/select-tools -ContentType 'application/json' -Body $body
   ```

Verify: the returned tool list should keep refund/billing/support tools plus `send_slack`, and drop
unrelated deploy/Kubernetes/procurement tools. In real traffic, the Gateway request record shows tool
schema savings in the compiler report.

---

## 4.7 - MCP Optimization Tools

**Goal:** exercise the optimization layer through MCP, the way Claude Desktop/Code would.

Open **Control Plane -> MCP** and connect a client with the AI Test Team workspace key. Then call these
MCP tools:

| MCP tool | What to pass | What to verify |
|---|---|---|
| `select_tools` | The query from 4.6 plus `tool_filtering_catalog.json` | Only relevant tools remain |
| `compile_context` | A duplicated / long `messages` array | `token_report.saved` is positive |
| `flywheel_analyze` | The sample segment payload from 4.8 | Cheapest SLA-safe config is recommended |
| `memory_store` / `memory_recall` | A workspace id and a fact | The fact can be recalled across clients |
| `kg_add_entity` / `kg_neighbors` | Service/entity ids | The knowledge graph returns neighbors |
| `skill_list` / `skill_get` | A workspace id and skill name | Skills are retrievable for injection workflows |

If your MCP client is not available, use the generated Postman collection's direct service folders:
**Context Compiler Service**, **Router Service**, **Flywheel Service**, **Memory Service**,
**Knowledge Graph**, and **Skill Registry**. Those requests hit the same backend services the MCP
gateway wraps.

---

## 4.8 - Optimization Flywheel

**Goal:** let RunLedger recommend the cheapest config that still holds your quality bar.

1. Generate traffic **with outcomes and scores** so the flywheel has something to learn from:
   ```bash
   LAB_FEATURE_TAG=support-chat LAB_RUNS=60 LAB_SCORE=true LAB_OUTCOME=true python traffic_gen.py
   ```
2. As an org admin, open the Gateway/Flywheel optimization area. Configure:
   - `apply_mode = approval`
   - `quality_metric = blend`
   - `min_quality = 0.85`
   - `segment_by = alias`
   - `action_space = model, stages, compression_rate, cache_threshold, routing`
3. Run the loop and review recommendations. Apply or dismiss them manually.

For a pure service smoke test, use the generated Postman **Flywheel Service -> Analyze** request.

Verify: recommendations should propose a cheaper config only when the sample size and quality floor
are satisfied.

---

## 4.9 - What Each Optimization Is For

| Option | Use it when | Main risk to watch |
|---|---|---|
| Exact cache | Identical prompts repeat | Stale responses if scope/version is too broad |
| Semantic cache | Users ask equivalent questions in different words | False positives if threshold is too loose |
| Context compiler | Agent transcripts or retrieved context are bloated | Dropping useful context if budgets are too tight |
| Prompt compression | You need maximum token reduction | Lossy wording changes can hurt quality |
| Tool filtering | Tool catalogs are large | A needed tool can be dropped unless in `always_tools` |
| Skill injection | Reusable procedures should travel with the request | Old skill content can become policy drift |
| Intelligent routing | Work has mixed complexity/risk | Misclassification sends hard work to cheap models |
| Flywheel | You have enough cost + quality history | Under-sampled recommendations should stay approval-only |

---

## 4.10 - Optimization Simulator (what-if analysis)

**Goal:** model the cost/latency impact of optimization changes before applying them.

1. Open **Observability → Optimization Simulator**.
2. Select a workspace and time range with enough traffic.
3. Adjust the sliders:
   - **Cache hit rate** — what if semantic cache caught 40% instead of 20%?
   - **Compression rate** — what if prompt compression saved 30% more tokens?
   - **Model swap** — what if you moved from a $3/M model to a $0.50/M model?
4. The simulator projects cost savings and latency changes based on your real traffic.

🔎 The simulator is the planning tool before you commit to a change. Combine it with
**Policy Dry Run** (Part 5.8) for the full before/after picture.

---

## 4.11 - Cost & Savings Dashboard

**Goal:** see where your savings are coming from.

Open **FinOps → Cost & Savings**. The dashboard shows realized savings by category
(cache hits, compression, routing to cheaper models) with time-series trends.

🔎 This is the ROI proof for your optimization investment — how much you're actually saving.

---

End of Part 4. You've exercised cache, compiler, compression, routing, tool filtering, MCP
optimization tools, the flywheel, the optimization simulator, and the savings dashboard.
Next: **[Part 5 - Governance & Control](./part5_governance.md)**.
