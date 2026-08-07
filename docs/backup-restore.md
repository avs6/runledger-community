# Backup and Restore

RunLedger now has two practical backup stories:

- **platform-managed backup operations** exposed in Settings for manual runs, history, connectivity checks, and restore drills
- **infrastructure-level scheduled backups** for Helm, MinIO/S3, and restore automation

This document covers both.

## What should be backed up

The control-plane PostgreSQL database is the system of record and should always be backed up. Depending on your deployment, you may also want to include:

| Store | Purpose | Recommendation |
|---|---|---|
| Control-plane Postgres | routes, runs, ledger, prompts, approvals, policies, budgets, analytics inputs | Always back up |
| Memory DB | long-lived memory / agent state | Back up if enabled |
| Kuzu graph | knowledge-graph state | Back up if you use it |
| Skill registry storage | durable skill content | Back up if you use it |
| Qdrant | semantic cache and vector artifacts | Optional, depending on recovery goals |

Redis and model caches are generally treated as rebuildable.

## Product-managed backup operations

The Settings page includes backup operations for platform admins:

- saved S3-compatible target configuration
- scheduled backup cadence, hour, and retention settings
- manual **Run backup now**
- backup run history
- snapshot inventory with checksum and artifact metadata
- **Test backup connectivity**
- **Run restore drill**
- checksum and artifact metadata capture for LocalAI/MinIO helper runs

These flows are backed by the `backup_runs` table and the backup operations service in the API.

### Local helper path

For local development and demos, RunLedger ships a generic S3-compatible helper:

```bash
python scripts/localai/localai_s3_backup.py ensure-bucket
python scripts/localai/localai_s3_backup.py backup
python scripts/localai/localai_s3_backup.py list
python scripts/localai/localai_s3_backup.py restore --confirm-restore
```

The backup helper emits structured summary metadata, including:

- per-artifact name
- artifact size in bytes
- per-artifact checksum
- total size
- aggregate checksum

That metadata is recorded into backup history when the RunLedger backup service invokes the helper.

## Local Docker Compose backup profile

RunLedger now includes a local `backup` profile with MinIO:

```bash
docker compose --profile backup up -d runledger-minio
```

Default local ports:

- S3 API: `http://localhost:9010`
- MinIO console: `http://localhost:9011`

Default local credentials are driven from `.env`:

- `RUNLEDGER_BACKUP_ACCESS_KEY_ID`
- `RUNLEDGER_BACKUP_SECRET_ACCESS_KEY`
- `RUNLEDGER_BACKUP_ENDPOINT_URL`
- `RUNLEDGER_LOCALAI_S3_BUCKET`

## Bring your own S3-compatible storage

Use the Settings page to configure:

- bucket
- region
- endpoint URL
- access key
- secret key
- path-style vs virtual-host behavior
- schedule cadence
- retention days
- encryption mode

This works for:

- AWS S3
- MinIO
- Ceph RGW
- other S3-compatible object stores

For MinIO and many local object stores, keep path-style URLs enabled.

## Helm and infrastructure-managed backups

For Kubernetes deployments, use the Helm backup CronJob and object storage.

Example values:

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"
  s3Bucket: "s3://my-bucket/runledger-backups"
  awsRegion: us-east-1
  retainDays: 30
  stores:
    memoryDb: { enabled: true }
    qdrant: { enabled: false }
    kuzu: { enabled: true }
    skills: { enabled: true }
```

Recommended methods by store:

| Store | Method |
|---|---|
| Control-plane Postgres | `pg_dump --format=custom` |
| Memory DB | `pg_dump --format=custom` |
| Qdrant | snapshot API |
| Kuzu / skill storage | archive the mounted data volume |

## Restore procedures

### Product restore drill

The dashboard restore drill is intended to validate that backup inventory is reachable and that operators can rehearse recovery safely. It is not a full destructive restore in-place.

Use it as a regular validation step before relying on any backup schedule.

### Local restore helper

For local restore using the bundled helper:

```bash
python scripts/localai/localai_s3_backup.py restore --confirm-restore
```

Restart API, worker, and beat after restore so all processes reload state.

### Full Postgres restore

Restore from a `pg_dump` archive:

```bash
pg_restore \
  --host=<host> \
  --port=5432 \
  --username=<user> \
  --dbname=runledger \
  --no-owner \
  --no-acl \
  --verbose \
  runledger-20260324T020000Z.dump
```

When restoring into a live environment:

1. stop API and worker writes
2. restore the target database
3. run pending migrations if needed
4. restart the services

## Connectivity checks and restore drills

Before enabling scheduled backup workflows in any serious environment:

1. verify the target bucket or object store is reachable
2. run at least one successful backup
3. verify checksum and artifact metadata are being recorded
4. run a restore drill against a safe environment
5. confirm operators know the recovery path

## Encryption

RunLedger currently supports a product-managed server-side encryption mode for S3-compatible uploads using AES256 headers where the target accepts them.

Use `Server-side AES256` in the Settings page for the default path.

## Recovery guidance

Use managed database PITR where available. Scheduled dumps are useful, but point-in-time recovery is still the better option for tighter recovery objectives.

| Scenario | Typical guidance |
|---|---|
| Single service restart | restart the service |
| DB failover with managed Postgres | prefer provider failover / PITR |
| Local demo reset | use `scripts/cleanup.py` or demo-mode reset |
| Full environment recovery | restore Postgres first, then durable auxiliary stores |

## Related docs

- [scripts/README.md](../scripts/README.md)
- [Demo runbook](./demo-runbook.md)
- [Helm](./helm.md)
