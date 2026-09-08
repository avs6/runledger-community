# Optimization

*Use the `LocalAIAgentStack / LiteLLM Gateway` workspace key for traffic.*

The pattern for each exercise:

1. Configure the route in the dashboard (as an org admin).
2. Put the `LiteLLM Gateway` key in `agents/.env`.
3. Drive traffic through the alias.
4. Inspect the effect in the gateway views.

## Exact Cache

```bash
LAB_GATEWAY_ALIAS=exact-cache-chat LAB_RUNS=2 LAB_FEATURE_TAG=exact-cache python traffic_gen.py
```

Verify the second request is a cache hit.

## Semantic Cache

```bash
LAB_GATEWAY_ALIAS=cached-chat LAB_RUNS=30 LAB_FEATURE_TAG=semantic-cache python traffic_gen.py
```

Verify semantically similar prompts hit the cache.

## Context Compiler

```bash
LAB_GATEWAY_ALIAS=compiled-chat LAB_RUNS=20 LAB_FEATURE_TAG=context-compiler python traffic_gen.py
```

Verify the request detail includes token savings.

## Prompt Compression

```bash
LAB_GATEWAY_ALIAS=compiled-chat LAB_RUNS=10 LAB_FEATURE_TAG=prompt-compression python traffic_gen.py
```

Verify compression savings appear in the token report.

## Intelligent Routing

```bash
LAB_GATEWAY_ALIAS=auto-chat LAB_RUNS=30 LAB_FEATURE_TAG=intelligent-routing python traffic_gen.py
```

Verify the selected route tier or routing reason appears in gateway request detail.

## Dynamic Tool Filtering

Use the sample tool catalog and confirm only relevant tools remain for the request.

## MCP Optimization Tools

Connect an MCP client using the `LocalAIAgentStack / LiteLLM Gateway` key and try:

- `select_tools`
- `compile_context`
- `flywheel_analyze`
- `memory_store`
- `memory_recall`

## Optimization Flywheel

Generate richer traffic first:

```bash
LAB_FEATURE_TAG=support-chat LAB_RUNS=60 LAB_SCORE=true LAB_OUTCOME=true python traffic_gen.py
```

Then inspect recommendations in the flywheel area.

## Cost & Savings

Open **FinOps → Cost & Savings** and verify realized savings from cache, routing,
or prompt optimization.

---

Next: [Governance](./governance.md)
