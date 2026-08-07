# High-Availability Deployment Guide

This guide covers running RunLedger in a production-grade HA configuration — multiple API replicas behind a load balancer, autoscaling workers, and Redis/Postgres failover.

## Architecture overview

```
                  ┌─────────────────────────────┐
                  │     Load Balancer / Ingress   │
                  └──────────────┬───────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
         ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
         │  API #1  │        │  API #2  │        │  API #3  │
         │  :8000   │        │  :8000   │        │  :8000   │
         └────┬────┘        └────┬────┘        └────┬────┘
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
   ┌──────▼──────┐      ┌────────▼────────┐     ┌──────▼──────┐
   │   Redis      │      │   PostgreSQL    │     │   Celery     │
   │ (Sentinel /  │      │  (Primary +     │     │  Workers    │
   │  Cluster)    │      │   Replica)      │     │  (N pods)   │
   └─────────────┘      └────────────────┘     └─────────────┘
                                                       │
                                               ┌───────▼───────┐
                                               │  Celery Beat  │
                                               │   (1 pod)     │
                                               └───────────────┘
```

## API replicas

The FastAPI app is fully stateless — all state lives in PostgreSQL and Redis. You can run as many replicas as needed.

### Kubernetes (Helm)

```yaml
api:
  replicaCount: 3

autoscaling:
  api:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
```

### Docker Compose (manual scale)

```bash
docker compose up --scale api=3
```

### Session stickiness

RunLedger does **not** require sticky sessions. All auth state is in JWT tokens validated per-request. Load balancers can use round-robin.

## Celery workers

Workers are also stateless and scale horizontally. They use `NullPool` for database connections (one connection per task), so more workers = more DB connections.

```yaml
worker:
  replicaCount: 4

autoscaling:
  worker:
    enabled: true
    minReplicas: 2
    maxReplicas: 20
    targetCPUUtilizationPercentage: 70
```

**Queue routing:** Tasks land in three queues: `celery` (default), `priority` (budget checks, gateway health), `low` (rollups, exports). Workers consume all three queues by default.

To dedicate workers to high-priority tasks:

```yaml
# values.yaml — two worker deployments with different queue assignments
# (requires separate Deployment templates or a Helm subchart)
worker:
  command:
    - celery
    - -A
    - runledger_api.core.celery_app
    - worker
    - -Q
    - priority,celery
    - --concurrency=8
```

**Beat scheduler:** Always run exactly **one** beat replica. The `beat-deployment.yaml` uses `strategy: Recreate` to enforce this during rolling updates.

```yaml
beat:
  replicaCount: 1   # Do not change — duplicate beat = duplicate scheduled tasks
```

## Optimization layer services

The optimization layer (semantic cache, context compiler, reranker, embedding, compression, router,
memory, flywheel, MCP gateway) is a set of **stateless** microservices. Each gets a Deployment, Service,
CPU HorizontalPodAutoscaler, PodDisruptionBudget, and soft anti-affinity so replicas spread across nodes.
They scale on demand exactly like the API:

```yaml
optimizationServices:
  semantic-cache:
    autoscaling: { enabled: true, minReplicas: 2, maxReplicas: 10, targetCPUUtilizationPercentage: 70 }
  context-compiler:
    autoscaling: { enabled: true, minReplicas: 2, maxReplicas: 10, targetCPUUtilizationPercentage: 70 }
  # …one entry per service
```

The **stateful** stores (Qdrant, memory-db, Letta, Kùzu, skills) are pluggable — run them in-cluster as
StatefulSets with PVCs for self-hosting, or point at managed services for production HA:

```yaml
stores:
  qdrant:   { external: true, url: "http://qdrant.internal:6333" }
  memoryDb: { external: true, url: "postgresql://user:pass@pg:5432/memory" }
  letta:    { external: true, url: "http://letta.internal:8283" }
```

`kg` and `skill-registry` embed their store on a PVC, so they run as single-replica StatefulSets rather
than autoscaling. Availability comes from standard Kubernetes primitives — replicas, HPA, PDB, and
anti-affinity — there is no bespoke HA component. See [helm.md](./helm.md) for the full values reference.

## Redis HA

### Redis Sentinel (recommended for self-hosted)

Redis Sentinel provides automatic failover with 3 Sentinel nodes monitoring a primary + replica pair.

```yaml
# redis-sentinel.yaml (example using Bitnami chart)
helm install redis bitnami/redis \
  --set architecture=replication \
  --set sentinel.enabled=true \
  --set sentinel.quorum=2
```

Set the Sentinel URL in RunLedger:

```
REDIS_URL=redis+sentinel://sentinel1:26379,sentinel2:26379,sentinel3:26379/mymaster/0
```

### Redis Cluster

For horizontal scaling of Redis itself (>10k events/second), use Redis Cluster. The `redis-py` client used by RunLedger supports cluster mode transparently.

### Managed Redis (recommended)

- **AWS ElastiCache** (Redis 7, Multi-AZ with automatic failover)
- **Upstash** (serverless, good for Railway/Fly.io)
- **Redis Cloud** (Enterprise, supports Sentinel + Cluster)

For ElastiCache with TLS:
```
REDIS_URL=rediss://your-cluster.abc123.cache.amazonaws.com:6380/0
```

## PostgreSQL HA

### Patroni + etcd (self-hosted)

Patroni manages leader election and automatic failover for a Postgres primary/replica pair.

```bash
# Example Patroni config snippet
bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576   # 1 MB
```

Point `DATABASE_URL` at a VIP or HAProxy fronting the primary. RunLedger uses async SQLAlchemy — connection errors cause retries at the application level.

### Managed Postgres (recommended)

- **AWS RDS Multi-AZ** — synchronous standby, automatic failover in ~60s
- **Google Cloud SQL HA** — automatic failover
- **Neon** (serverless, branching for dev/staging, good for Railway)
- **Supabase** — Postgres with built-in connection pooling (PgBouncer)

### Connection pooling

For high concurrency, place PgBouncer in front of Postgres. RunLedger uses SQLAlchemy `asyncpg` with a connection pool:

```
DATABASE_URL=postgresql+asyncpg://user:pass@pgbouncer-host:5432/runledger
```

Recommended PgBouncer settings:
```ini
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
```

### Read replicas and lag monitoring

RunLedger can keep Postgres as the write primary while moving read-heavy operator
paths to replicas. Good candidates include:

- gateway request history
- benchmark comparison queries
- analytics-heavy dashboards

Monitor at minimum:

- replica lag in seconds
- replay delay trend
- connection saturation
- query latency split between primary and replicas

If lag exceeds your audit or routing tolerance, keep those reads pinned to primary
 until the replica recovers.

## Health checks

RunLedger exposes two health endpoints used by Kubernetes probes:

- `GET /health/live` — always 200 while the process is running (liveness)
- `GET /health/ready` — 200 when DB + Redis are reachable; 503 when degraded (readiness)

The readiness probe prevents traffic from being routed to a pod while its DB/Redis connections are warming up or failing.

The API exposes the full `health/live` plus `health/ready` pair. The stateless optimization
sidecars expose `GET /health/ready` as well, so local Compose and Kubernetes-style checks can
use a consistent readiness path across the stack.

### Graceful draining

Gateway nodes are intended to be drained before termination:

1. mark the pod unready
2. stop accepting new requests
3. allow in-flight streaming requests to finish or hit timeout
4. terminate after the drain window

This preserves the stateless horizontal-scaling model without dropping active
gateway sessions during rollouts.

## Prometheus / Grafana monitoring

RunLedger intentionally prefers OSS infrastructure monitoring rather than re-implementing a full
infra-monitoring product surface in-app. The supported pattern is:

- use Prometheus to scrape `/metrics`
- use Grafana or your existing dashboards for infrastructure views
- use the bundled OTel Collector for trace fan-in and fan-out
- use RunLedger's own UI for agent, FinOps, governance, and operator workflows such as queue visibility

This keeps generic host, container, and infra telemetry in standard OSS tooling while RunLedger
focuses on AI-specific control-plane data.

Enable the metrics endpoint and protect it with a token:

```yaml
secrets:
  metricsToken: "your-scrape-token"

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/path: /metrics
  prometheus.io/port: "8000"
```

Available metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `runledger_uptime_seconds` | gauge | Seconds since API process started |
| `runledger_active_runs` | gauge | Agent runs in `running` state |
| `runledger_pipeline_lag_seconds` | gauge | Seconds since last ingest event |
| `runledger_ingest_rate_per_minute` | gauge | Runs/minute (5-min window) |
| `runledger_provider_calls_last_hour` | gauge | Provider calls in last hour |
| `runledger_gateway_requests_last_hour` | gauge | Gateway forwards in last hour |
| `runledger_gateway_cache_hit_rate` | gauge | Prompt cache hit fraction (0–1) |
| `runledger_uncosted_provider_calls` | gauge | Cost enrichment backlog |
| `runledger_celery_queue_depth{queue}` | gauge | Tasks waiting per queue |

Platform admins can also inspect the same queue-depth summary in the dashboard under
`Settings -> Backup & Restore -> Worker Queue Visibility`.

Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: runledger
    static_configs:
      - targets: ["api.runledger.svc.cluster.local:8000"]
    authorization:
      type: Bearer
      credentials: <METRICS_TOKEN>
```

### Recommended alert rules

```yaml
groups:
  - name: runledger
    rules:
      - alert: RunLedgerPipelineLag
        expr: runledger_pipeline_lag_seconds > 300
        for: 5m
        annotations:
          summary: "Pipeline lag > 5 minutes — workers may be stuck"

      - alert: RunLedgerQueueDepth
        expr: runledger_celery_queue_depth > 1000
        for: 2m
        annotations:
          summary: "Celery queue {{ $labels.queue }} depth > 1000"

      - alert: RunLedgerCostingBacklog
        expr: runledger_uncosted_provider_calls > 500
        for: 10m
        annotations:
          summary: "Cost enrichment backlog > 500 — check cost-enrichment worker"
```
