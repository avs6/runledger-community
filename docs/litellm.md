# LiteLLM Integration

RunLedger integrates with [LiteLLM](https://github.com/BerriAI/litellm) in three
complementary patterns.  Choose the one that matches your architecture, or
combine them.

| Pattern | Use case |
|---------|----------|
| [A — SDK instrumentation](#pattern-a--litellm-sdk-instrumentation) | You call `litellm.completion()` directly |
| [B — OpenAI client → LiteLLM Proxy](#pattern-b--openai-client--litellm-proxy) | LiteLLM Proxy is already in your stack |
| [C — RunLedger Gateway → LiteLLM Proxy](#pattern-c--runledger-gateway--litellm-proxy) | Production: RunLedger in front of LiteLLM Proxy |

---

## Prerequisites

```bash
pip install litellm runledger-sdk
```

---

## Pattern A — LiteLLM SDK Instrumentation

One line instruments every provider that LiteLLM supports — OpenAI,
Anthropic, Gemini, Mistral, Groq, Ollama, Bedrock, Azure, Vertex AI,
Together AI, and 100+ more.

```python
from runledger_sdk import RunLedger

rl = RunLedger(api_key="rl_live_...")
rl.instrument_litellm()          # patches litellm.completion + litellm.acompletion

import litellm

# All calls are now tracked — provider is auto-detected from the model name
response = litellm.completion(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)

response = litellm.completion(
    model="claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": "Hello!"}],
)

response = litellm.completion(
    model="gemini/gemini-1.5-pro",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

### Async

```python
response = await litellm.acompletion(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

### Context propagation

```python
with rl.context(end_user_id="u_123", feature_tag="support-chat"):
    response = litellm.completion(model="gpt-4o", messages=[...])
    # All events are tagged with end_user_id and feature_tag
```

### Budget enforcement

```python
rl = RunLedger(api_key="rl_live_...", budget_check=True)
rl.instrument_litellm()
# RunLedger checks spend guardrails before each call.
# Raises RunLedgerBudgetExceededError if the budget is blocked.
# Mutates model= in-place if the budget action is "downgrade".
```

---

## Pattern B — OpenAI client → LiteLLM Proxy

If you already run a LiteLLM Proxy, point an OpenAI client at the proxy
URL and use `rl.instrument()`.  The SDK intercepts every
`chat.completions.create` call before it reaches the proxy.

```
your app
  └── openai.chat.completions.create()
        └── RunLedger SDK  (intercepts here)
              └── LiteLLM Proxy :4000
                    └── OpenAI / Anthropic / Bedrock / …
```

```bash
# Start the LiteLLM Proxy
litellm --model gpt-4o --model claude-3-5-sonnet-20241022 --port 4000
```

```python
import openai
from runledger_sdk import RunLedger

rl = RunLedger(api_key="rl_live_...")
rl.instrument()  # patches openai.chat.completions.create

client = openai.OpenAI(
    base_url="http://localhost:4000/v1",
    api_key="sk-litellm-proxy",   # your LiteLLM master key (or any string)
)

with rl.context(end_user_id="u_456", feature_tag="chat"):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello!"}],
    )
```

> **Provider detection:** When requests pass through LiteLLM Proxy, the
> `model` field in the OpenAI response reflects the LiteLLM model alias.
> RunLedger records whatever model name is returned.  For accurate
> per-provider attribution, use model names that include the provider prefix
> (e.g. `anthropic/claude-3-5-sonnet-20241022`) in your LiteLLM config.

### LiteLLM Proxy config (litellm_config.yaml)

```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-3-5-sonnet
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20241022
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: gemini-flash
    litellm_params:
      model: gemini/gemini-1.5-flash
      api_key: os.environ/GOOGLE_API_KEY
```

```bash
litellm --config litellm_config.yaml --port 4000
```

---

## Pattern C — RunLedger Gateway → LiteLLM Proxy

For production deployments, place the RunLedger Gateway in front of the
LiteLLM Proxy.  RunLedger adds:

- **Prompt caching** (SHA-256, 24 h TTL) — saves provider costs
- **Cost-cap enforcement** — hard-stop at daily or monthly spend limits
- **PII redaction** — strip emails, phone numbers, SSNs before forwarding
- **Routing policies** — cost-optimised, latency-optimised, canary, weighted
- **Per-user rate limiting** — protect against runaway agents
- **Audit log** — every proxied call recorded in the Routing Log

```
your app
  └── openai.OpenAI(base_url="http://api:8000/gateway/v1")
        └── RunLedger Gateway :8000
              ├── prompt cache  (cache hit → return immediately)
              ├── cost-cap check
              ├── PII redaction
              └── LiteLLM Proxy :4000
                    └── OpenAI / Anthropic / Bedrock / …
```

### 1. Register LiteLLM Proxy as a gateway route

```bash
curl -X POST http://localhost:8000/gateway/routes \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "litellm-proxy",
    "provider": "openai",
    "target_model": "gpt-4o",
    "base_url": "http://localhost:4000/v1",
    "api_key_env_var": "LITELLM_PROXY_KEY",
    "priority": 1,
    "is_active": true,
    "daily_cost_limit_usd": 50.0,
    "pii_redaction_enabled": true
  }'
```

Set `LITELLM_PROXY_KEY` in the RunLedger API server's environment (e.g.
`apps/api/.env`).

### 2. Send completions through the RunLedger Gateway

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/gateway/v1",
    api_key="rl_live_...",    # your RunLedger workspace API key
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

### 3. Add a routing policy (optional)

```bash
# Cost-optimised routing across multiple LiteLLM routes
curl -X POST http://localhost:8000/gateway/policies \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cost-optimised",
    "strategy": "cost_optimized",
    "config": {}
  }'
```

See the [Gateway documentation](./deployment.md#model-gateway) for the full
list of routing strategies: `manual`, `cost_optimized`, `latency_optimized`,
`quality_optimized`, `weighted`, `canary`, `budget_aware`, `complexity_based`.

---

## Provider detection table

RunLedger infers the provider from the LiteLLM model name:

| LiteLLM model name | Detected provider |
|--------------------|-------------------|
| `gpt-4o`, `gpt-3.5-turbo`, `o1-preview` | `openai` |
| `claude-3-5-sonnet-20241022` | `anthropic` |
| `anthropic/claude-3-5-sonnet-20241022` | `anthropic` |
| `gemini/gemini-1.5-pro` | `google` |
| `vertex_ai/gemini-1.5-pro` | `google` |
| `azure/gpt-4` | `azure` |
| `mistral/mistral-large-latest` | `mistral` |
| `groq/llama3-70b-8192` | `groq` |
| `ollama/llama3`, `ollama_chat/llama3` | `ollama` |
| `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0` | `bedrock` |
| `together_ai/meta-llama/Llama-3-70b-chat-hf` | `together` |
| `cohere/command-r-plus` | `cohere` |
| `fireworks_ai/llama-v3-70b-instruct` | `fireworks` |
| `perplexity/llama-3.1-sonar-huge-128k-online` | `perplexity` |

---

## LiteLLM cost estimates

LiteLLM computes its own cost estimate on every response, available via:

```python
hidden = getattr(response, "_hidden_params", {})
cost_estimate = hidden.get("response_cost")  # float, USD
```

RunLedger captures this as `reported_cost_usd` (with `cost_source="litellm"`)
alongside its own pricing-engine calculation.  You can compare both in the
**Provider Invoice Reconciliation** page.

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `RUNLEDGER_API_KEY` | Your RunLedger workspace API key |
| `RUNLEDGER_BASE_URL` | RunLedger API base URL (default: `https://api.runledger.io`) |
| `LITELLM_PROXY_KEY` | Master key for your LiteLLM Proxy (set on the API server) |

---

## Examples

| File | Description |
|------|-------------|
| [`examples/31_litellm_basic.py`](../examples/31_litellm_basic.py) | SDK instrumentation, multi-model calls, async, cost comparison |
| [`examples/32_litellm_proxy.py`](../examples/32_litellm_proxy.py) | All three patterns side-by-side with a live LiteLLM Proxy |

---

## Troubleshooting

**`litellm` not installed**

```
ImportError: litellm package is required for LiteLLM instrumentation.
Install it with: pip install litellm
```

**LiteLLM Proxy returns 401**

Set `LITELLM_PROXY_KEY` in your RunLedger API server environment to match the
`master_key` in your LiteLLM Proxy config.

**Provider shows as `unknown`**

The model name doesn't match any known prefix.  Pass the provider explicitly
using the `provider/model` format, e.g. `openrouter/meta-llama/llama-3.1-8b-instruct`.

**Double-counted events**

If you call both `rl.instrument_litellm()` and `rl.instrument()` while also
pointing OpenAI at a LiteLLM Proxy, each completion will be tracked twice.
Use exactly one instrumentation method per call path.
