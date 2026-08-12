# Part 4 - Optimization Layer

*Prerequisite: configure gateway routes as an org admin, then use the `LocalAIAgentStack / LiteLLM Gateway` key for traffic.*

The pattern stays the same for each optimization exercise:

1. Configure the route in the dashboard.
2. Put the `LiteLLM Gateway` key in `agents/.env`.
3. Drive traffic through the alias.
4. Inspect the effect in the gateway views.

## 4.1 - Exact cache

```bash
LAB_GATEWAY_ALIAS=exact-cache-chat LAB_RUNS=2 LAB_FEATURE_TAG=exact-cache python traffic_gen.py
```

Verify the second request is a cache hit.

## 4.2 - Semantic cache

```bash
LAB_GATEWAY_ALIAS=cached-chat LAB_RUNS=30 LAB_FEATURE_TAG=semantic-cache python traffic_gen.py
```

Verify semantically similar prompts hit the cache.

## 4.3 - Context compiler

```bash
LAB_GATEWAY_ALIAS=compiled-chat LAB_RUNS=20 LAB_FEATURE_TAG=context-compiler python traffic_gen.py
```

Verify the request detail includes token savings.

## 4.4 - Prompt compression

```bash
LAB_GATEWAY_ALIAS=compiled-chat LAB_RUNS=10 LAB_FEATURE_TAG=prompt-compression python traffic_gen.py
```

Verify compression savings appear in the token report.

## 4.5 - Intelligent routing

```bash
LAB_GATEWAY_ALIAS=auto-chat LAB_RUNS=30 LAB_FEATURE_TAG=intelligent-routing python traffic_gen.py
```

Verify the selected route tier or routing reason appears in gateway request detail.

## 4.6 - Dynamic tool filtering

Use the sample tool catalog and confirm only relevant tools remain for the request.

## 4.7 - MCP optimization tools

Connect an MCP client using the `LocalAIAgentStack / LiteLLM Gateway` key and try:

- `select_tools`
- `compile_context`
- `flywheel_analyze`
- `memory_store`
- `memory_recall`

## 4.8 - Optimization flywheel

Generate richer traffic first:

```bash
LAB_FEATURE_TAG=support-chat LAB_RUNS=60 LAB_SCORE=true LAB_OUTCOME=true python traffic_gen.py
```

Then inspect recommendations in the flywheel area.

## 4.9 - Cost and savings

Open **FinOps -> Cost & Savings** and verify realized savings from cache, routing,
or prompt optimization.

Next: [Part 5 - Governance and Control](./part5_governance.md)
