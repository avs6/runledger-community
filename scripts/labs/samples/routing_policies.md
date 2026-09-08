# Model Gateway - Routing Policies To Add In The GUI

Each policy below is a route (or pair of routes) you create on the **Gateway** page.
After adding one, drive traffic through its alias to watch it act:

```bash
LAB_GATEWAY_ALIAS=<alias> LAB_RUNS=30 LAB_FEATURE_TAG=policy-test python traffic_gen.py
```

> For any Ollama target, **Base URL must be** `http://host.docker.internal:11434/v1`.
> The gateway runs in Docker; `localhost` would be the container itself.

---

## Policy 1 - Fallback / Priority

Two routes, **same alias**, different priority. Traffic uses the lowest-priority number first;
if it is unhealthy, the next route takes over.

| Route | Alias | Provider | Target model | Base URL | Priority |
|---|---|---|---|---|---|
| primary | `chat` | ollama | `llama3.2` | `http://host.docker.internal:11434/v1` | `1` |
| fallback | `chat` | ollama | `gemma3:latest` | `http://host.docker.internal:11434/v1` | `2` |

Observe: on the Gateway page the primary carries traffic. Stop that model in Ollama and re-run;
the fallback should pick up and the request log should explain the decision.

---

## Policy 2 - Semantic Cache

One route with **Semantic cache = ON**.

| Alias | Provider | Target model | Base URL | Semantic cache |
|---|---|---|---|---|
| `cached-chat` | ollama | `llama3.2` | `http://host.docker.internal:11434/v1` | ON |

Observe: reworded but equivalent prompts can return with `decision_reason = semantic_cache_hit`.

---

## Policy 3 - Intelligent Routing

One route with **Intelligent routing = ON** and this `routing_config`:

```json
{
  "classifier_mode": "hybrid",
  "tiers": {
    "cheap": "llama3.2",
    "mid": "qwen2.5-coder:14b",
    "frontier": "deepseek-r1:14b"
  },
  "matrix": {
    "simple": { "low": "cheap", "high": "mid" },
    "medium": { "low": "mid", "high": "frontier" },
    "complex": { "low": "frontier", "high": "frontier" }
  },
  "reasoning_effort": true,
  "on_failure": "passthrough"
}
```

Observe: simple/low-risk prompts resolve to the cheap tier, while hard/high-risk prompts resolve
to frontier. Make sure the tier aliases also exist as routes, or point tiers at models you have pulled.

---

## Policy 4 - Context Compiler

One route with **Context compiler = ON** and:

```json
{
  "token_threshold": 0,
  "token_budget": 400,
  "keep_recent": 4,
  "stages": {
    "dedup": true,
    "tool_output": true,
    "rerank": true,
    "compaction": true,
    "compress": false,
    "tools": false,
    "skills": false
  }
}
```

Observe: bloated requests are trimmed before the model; the request log shows savings per stage.

---

## Policy 5 - Prompt Compression

Use the same route as Policy 4, then enable the final lossy compression stage:

```json
{
  "token_threshold": 0,
  "token_budget": 400,
  "compression_rate": 0.55,
  "compression_model": "bert-base-multilingual",
  "stages": {
    "dedup": true,
    "tool_output": true,
    "rerank": true,
    "compaction": true,
    "compress": true,
    "tools": false,
    "skills": false
  }
}
```

Observe: the request log's token report should include a compression stage. If evaluation quality
drops, increase `compression_rate` or disable `compress`.

---

## Policy 6 - Tool Filtering

One route with **Context compiler = ON** and tool filtering enabled:

```json
{
  "token_threshold": 0,
  "token_budget": 400,
  "tool_k": 4,
  "tool_filter_threshold": 8,
  "always_tools": ["send_slack"],
  "stages": {
    "dedup": true,
    "tool_output": true,
    "rerank": true,
    "compaction": true,
    "tools": true,
    "skills": false,
    "compress": false
  }
}
```

Use [`tool_filtering_catalog.json`](./tool_filtering_catalog.json) as a sample large catalog. Observe:
irrelevant tool schemas are dropped before forwarding, while `send_slack` is always kept.

---

## Policy 7 - Skill Injection

One route with **Context compiler = ON** and skill injection enabled:

```json
{
  "token_threshold": 0,
  "token_budget": 400,
  "skill_k": 2,
  "skill_min_score": -8.0,
  "stages": {
    "dedup": true,
    "tool_output": true,
    "rerank": true,
    "compaction": true,
    "tools": false,
    "skills": true,
    "compress": false
  }
}
```

Observe: matched skill bodies are injected as compact system context. Use MCP `skill_list` and
`skill_get` to confirm the source skills.

---

## Policy 8 - Per-Route Cost Cap

Add a hard ceiling on a route: **Daily cost limit** `0.05` and/or a monthly limit.

Observe: once the route's spend crosses the cap, further calls are refused at the gateway. This is a
route guardrail independent of workspace budgets.

---

## Policy 9 - Per-User Rate Limit + PII Redaction

On any route, set **Per-user RPM limit** `20` and **PII redaction = ON**.

Observe: bursts from a single `end_user_id` get throttled, and prompts with emails / phone numbers are
redacted before leaving the gateway.

---

## Cleanup

Delete routes you are done with from the Gateway page so later policies start clean, especially the two
`chat` fallback routes before reusing that alias.
