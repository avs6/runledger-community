# Infrastructure Hardening

RunLedger now ships a practical infra-hardening posture for local, demo, and
self-hosted environments. The application exposes the settings and policy
signals; storage, lifecycle, durability, and TLS remain infrastructure choices.

## Redis durability plan

The default `core` profile treats Redis as an **ephemeral** queue/cache layer.
That is appropriate when Redis only backs:

- Celery broker state
- sliding-window rate limits
- cache entries

If you ever store non-ephemeral state in Redis, enable append-only persistence:

```bash
RUNLEDGER_REDIS_APPENDONLY=yes \
RUNLEDGER_REDIS_APPENDFSYNC=everysec \
docker compose up -d
```

Supported settings:

- `RUNLEDGER_REDIS_APPENDONLY`
- `RUNLEDGER_REDIS_APPENDFSYNC`
- `RUNLEDGER_REDIS_SAVE`

The Settings operator surface now shows whether Redis is still ephemeral or
running in a durable mode.

## ClickHouse evaluation

RunLedger does **not** enable ClickHouse by default.

Decision:

- Keep Postgres as the system of record.
- Keep Redis for queue/cache state only.
- Revisit ClickHouse only when event volume or dashboard/export pressure makes
  Postgres analytics a bottleneck.

Recommended trigger for reevaluation:

- sustained high-cardinality analytics
- tens of millions of provider/tool/request records per month
- material dashboard or export contention on Postgres

## Object lifecycle rules

Backup and compliance buckets should be lifecycle-managed outside the app.
RunLedger now exposes lifecycle intent through config and policy evaluation:

- `OBJECT_LIFECYCLE_ENABLED`
- `OBJECT_LIFECYCLE_DAYS`
- `OBJECT_LIFECYCLE_NONCURRENT_DAYS`

Suggested baseline:

- current objects: 90 days
- non-current versions: 30 days
- compliance exports: 365 days

## Compliance export storage

Compliance artifacts can be pointed at dedicated object storage with:

- `COMPLIANCE_EXPORT_ENABLED`
- `COMPLIANCE_EXPORT_BUCKET`
- `COMPLIANCE_EXPORT_PREFIX`
- `COMPLIANCE_EXPORT_STORAGE_CLASS`
- `COMPLIANCE_EXPORT_RETENTION_DAYS`

The app owns destination awareness; bucket policy, KMS policy, lifecycle, and
replication remain infrastructure concerns.

## Feature flags

Deployment-scoped feature flags are now supported through:

```bash
FEATURE_FLAGS=backup_operations,kafka_exports,policy_dry_run
```

The Settings operator surface and ops API expose the enabled set.

## Abuse and rate protection

RunLedger now has a dedicated **system** rate-limit tier alongside ingest,
analytics, and management tiers.

Settings:

- `ABUSE_PROTECTION_ENABLED`
- `INGEST_RATE_LIMIT_PER_MINUTE`
- `ANALYTICS_RATE_LIMIT_PER_MINUTE`
- `MANAGEMENT_RATE_LIMIT_PER_MINUTE`
- `SYSTEM_RATE_LIMIT_PER_MINUTE`

The `/admin/*` surface now uses the system tier, so bootstrap and admin-secret
operations are not left unthrottled.

## Infra policy evaluation

The Settings operator surface now includes bring-up policy evaluation via:

- `GET /settings/ops/policy-evaluation`

It evaluates:

- Redis durability mode
- object lifecycle configuration
- compliance export storage readiness
- abuse protection status
- metrics-token isolation
- local TLS posture
- current deployment profile

Mode is controlled through `INFRA_POLICY_ENFORCEMENT_MODE` and defaults to
`advisory`.

## Local TLS demo story

For realistic customer demos, RunLedger now ships a `tls-demo` profile using
Caddy with internal certificates.

```bash
docker compose --profile tls-demo up -d runledger-caddy
```

Endpoints:

- `https://runledger.localhost:3443`
- `https://api.runledger.localhost:8443`

Config: [infra/Caddyfile](../infra/Caddyfile)

This is for local HTTPS demos, not production certificate management.

## Deployment profiles

RunLedger now has a clearer local profile split:

- `core`: plain `docker compose up -d`
- `aux`: optimization and agentic sidecars
- `observability`: OTEL collector
- `backup`: MinIO
- `tls-demo`: local HTTPS proxy
- `full-demo`: all optional services together

Examples:

```bash
docker compose up -d
docker compose --profile aux up -d
docker compose --profile full-demo up -d
docker compose --profile full-demo --profile tls-demo up -d
```
