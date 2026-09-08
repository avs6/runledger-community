# Gateway Performance & Scale

Validate gateway benchmarking, pass-through analytics, and multi-region routing.

## Goals

- Measure gateway p50, p95, and p99 overhead
- Compare gateway latency to a direct provider call
- Verify pass-through endpoint testing and per-call cost assignment
- Verify preferred-region routing and cross-region fallback

## Prerequisites

- RunLedger running locally with at least one gateway alias configured
- A workspace API key
- Optional: direct provider credentials for comparison mode

## Drive Benchmark Traffic

```bash
python scripts/bench/run_benchmark.py \
  --base-url http://localhost:8201 \
  --api-key rl_... \
  --alias chat \
  --repeat 30 \
  --concurrency 5
```

Optional direct-provider comparison (e.g. against Ollama directly):

```bash
python scripts/bench/run_benchmark.py \
  --base-url http://localhost:8201 \
  --api-key rl_... \
  --alias chat \
  --repeat 30 \
  --concurrency 5 \
  --provider-url http://localhost:11434/v1/chat/completions \
  --provider-model llama3.2
```

## Inspect Benchmark Results

```bash
python scripts/bench/report.py \
  --base-url http://localhost:8201 \
  --api-key rl_... \
  --days 7
```

Open the Gateway dashboard and review the **Performance & Benchmarking** section.

## Pass-Through Analytics

1. Create or open a pass-through endpoint in the Gateway dashboard.
2. Use the **Test** action to verify connectivity.
3. Send requests through `/gateway/passthrough/{slug}`.
4. Confirm the dashboard shows: total requests, p95 latency, estimated 24h cost, rate-limit utilization.

## Multi-Region Routing

1. Configure two routes for the same alias with different `region` values.
2. Send requests with `X-RunLedger-Region` set to the preferred region.
3. Disable the preferred-region route.
4. Confirm traffic succeeds via cross-region fallback in the routing log.
