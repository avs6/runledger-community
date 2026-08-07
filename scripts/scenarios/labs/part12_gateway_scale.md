# Part 12: Gateway Performance And Scale Lab

This lab validates the gateway benchmarking, pass-through analytics, and
multi-region routing surfaces added in the platform.

## Goals

- measure gateway p50, p95, and p99 overhead
- compare gateway latency to a direct provider call
- verify pass-through endpoint testing and per-call cost assignment
- verify preferred-region routing and cross-region fallback

## Prerequisites

- RunLedger running locally
- at least one gateway alias configured
- a workspace API key
- optional direct provider credentials for comparison mode

## Step 1: Drive benchmark traffic

```bash
python scripts/bench/run_benchmark.py \
  --base-url http://localhost:8201 \
  --api-key rl_... \
  --alias chat \
  --repeat 30 \
  --concurrency 5
```

Optional direct-provider comparison:

```bash
python scripts/bench/run_benchmark.py \
  --base-url http://localhost:8201 \
  --api-key rl_... \
  --alias chat \
  --repeat 30 \
  --concurrency 5 \
  --provider-url https://api.openai.com/v1/chat/completions \
  --provider-auth-header Authorization \
  --provider-auth-value "Bearer sk-..." \
  --provider-model gpt-4o-mini
```

## Step 2: Inspect benchmark summaries

```bash
python scripts/bench/report.py \
  --base-url http://localhost:8201 \
  --api-key rl_... \
  --days 7
```

Then open the Gateway dashboard and review the **Performance And Benchmarking**
section for the same aliases.

## Step 3: Validate pass-through analytics

1. Create or open a pass-through endpoint in the Gateway dashboard.
2. Use the **Test** action to verify connectivity.
3. Send a few requests through `/gateway/passthrough/{slug}`.
4. Confirm the dashboard shows:
   - total requests
   - p95 latency
   - estimated 24h cost
   - rate-limit utilization

## Step 4: Validate multi-region behavior

1. Configure at least two routes for the same alias with different `region` values.
2. Send requests with `X-RunLedger-Region` set to the preferred region.
3. Temporarily disable or remove the preferred-region route.
4. Confirm traffic still succeeds and the routing log shows cross-region fallback.

## Expected outcome

By the end of the lab you should have:

- benchmark data visible in the API and dashboard
- a measured gateway overhead envelope
- validated pass-through cost and rate analytics
- confirmed regional preference and fallback behavior
