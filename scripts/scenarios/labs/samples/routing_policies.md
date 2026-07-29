# Model Gateway — routing policies to add in the GUI

Each policy below is a route (or pair of routes) you create on the **Gateway** page.
After adding one, drive traffic through its alias to watch it act:

```bash
LAB_GATEWAY_ALIAS=<alias> LAB_RUNS=30 LAB_FEATURE_TAG=policy-test python traffic_gen.py
```

> ⚠️ For any Ollama target, **Base URL must be** `http://host.docker.internal:11434/v1`
> (the gateway runs in Docker; `localhost` would be the container itself).

---

## Policy 1 — Fallback / priority

Two routes, **same alias**, different priority. Traffic uses the lowest-priority
number first; if it's unhealthy the next takes over.

| Route | Alias | Provider | Target model | Base URL | Priority |
|---|---|---|---|---|---|
| primary | `chat` | ollama | `llama3.2` | host.docker.internal | **1** |
| fallback | `chat` | ollama | `gemma3:latest` | host.docker.internal | **2** |

🔎 Observe: on the Gateway page the primary carries the traffic; stop that model in
Ollama and re-run — the fallback picks up (see `decision_reason` in the request log).

---

## Policy 2 — Semantic cache

One route, **Semantic cache = ON**.

| Alias | Provider | Target model | Base URL | Semantic cache |
|---|---|---|---|---|
| `cached-chat` | ollama | `llama3.2` | host.docker.internal | **ON** |

🔎 Observe: re-worded but equivalent prompts return instantly with
`decision_reason = semantic_cache_hit` — no model round-trip. (The generator sends a
varied prompt pool, so you'll see a mix of misses and near-duplicate hits.)

---

## Policy 3 — Intelligent routing (complexity × risk → tier)

One route with **Intelligent routing = ON** and this `routing_config`:

```json
{
  "classifier_mode": "hybrid",
  "tiers": { "cheap": "llama3.2", "mid": "qwen2.5-coder:14b", "frontier": "deepseek-r1:14b" },
  "matrix": {
    "simple":  { "low": "cheap",    "high": "mid" },
    "medium":  { "low": "mid",      "high": "frontier" },
    "complex": { "low": "frontier", "high": "frontier" }
  },
  "reasoning_effort": true,
  "on_failure": "passthrough"
}
```

🔎 Observe: simple/low-risk prompts resolve to the cheap tier, hard/high-risk ones to
frontier — visible per request. (Make sure the tier aliases also exist as routes, or
point tiers at models you've pulled.)

---

## Policy 4 — Context compiler (shrink oversized context)

One route with **Context compiler = ON** and:

```json
{
  "token_budget": 400,
  "stages": { "dedup": true, "tool_output": true, "rerank": true, "compaction": true }
}
```

🔎 Observe: bloated requests are trimmed before the model; the request log shows a
token-saved report per stage.

---

## Policy 5 — Per-route cost cap

Add a hard ceiling on a route: **Daily cost limit** `0.05` (and/or Monthly).

🔎 Observe: once the day's spend on that route crosses the cap, further calls are
refused at the gateway — a spend guardrail independent of workspace budgets.

---

## Policy 6 — Per-user rate limit + PII redaction

On any route, set **Per-user RPM limit** `20` and **PII redaction = ON**.

🔎 Observe: bursts from a single `end_user_id` get throttled; prompts with emails /
phone numbers are redacted before leaving the gateway.

---

### Cleanup

Delete routes you're done with from the Gateway page so later policies start clean
(especially the two `chat` fallback routes before reusing that alias).
