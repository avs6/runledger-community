# Backup and Restore

## Backup strategy

The **control-plane PostgreSQL** is RunLedger's system of record and the primary thing to back up.
The optimization layer adds a few more **durable** stores that also hold state worth keeping:

| Store | Contents | Back up? |
|-------|----------|----------|
| control-plane Postgres | routes, ledger, flywheel, everything | **Always** |
| memory-db (Letta) | facts / preferences / decisions / episodes | **Yes** |
| Kùzu graph | knowledge graph | **Yes** |
| skill-registry | skill files | **Yes** |
| Qdrant | semantic cache + episode vectors | Optional — largely regenerable |

Everything else is **regenerable** and is *not* backed up:
- **Redis** — Celery queues + rate-limit counters (ephemeral) and budget counters (rebuilt from Postgres).
- **Embedding / reranker / compression model caches** — re-downloaded on pod start.

The Helm chart's backup CronJob covers every durable store in one job (see below); `scripts/restore.sh`
is the companion restore tool.

## Automated backups

### Via Helm chart (K8s)

Enable the nightly multi-store backup CronJob in your values and pick which durable stores to include:

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"          # 02:00 UTC daily
  s3Bucket: "s3://my-bucket/runledger-backups"
  awsRegion: us-east-1
  retainDays: 30
  stores:
    memoryDb: { enabled: true }  # pg_dump the Letta memory Postgres
    qdrant:   { enabled: false } # snapshot (semantic cache is regenerable; episodes are not)
    kuzu:     { enabled: true }  # tar the knowledge-graph PVC
    skills:   { enabled: true }  # tar the skill-registry PVC
```

One job backs up every enabled store to S3 (`STANDARD_IA`) under per-store prefixes, pruning objects
older than `retainDays`:

| Store | Method |
|-------|--------|
| control-plane Postgres | `pg_dump --format=custom` (always) |
| memory-db | `pg_dump --format=custom` |
| Qdrant | snapshot API |
| Kùzu / skills | `tar` the StatefulSet PVC |

> **PVC access:** the Kùzu and skills backups mount their `ReadWriteOnce` PVCs, which single-attach — so
> the backup Job must land on the same node as the owning pod, or the PVC must use a `ReadWriteMany`
> storage class. For managed production, prefer external stores with the provider's own snapshots.

The backup pod needs S3 write access. On EKS, use IRSA:

```yaml
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789:role/runledger-backup
```

Required IAM policy:
```json
{
  "Effect": "Allow",
  "Action": ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
  "Resource": [
    "arn:aws:s3:::my-bucket",
    "arn:aws:s3:::my-bucket/runledger-backups/*"
  ]
}
```

### Via Docker Compose (standalone backup script)

```bash
#!/bin/bash
TIMESTAMP=$(date +%Y%m%dT%H%M%SZ)
FILENAME="runledger-${TIMESTAMP}.dump"

docker run --rm \
  --network runledger_default \
  -e PGPASSWORD="${DB_PASSWORD}" \
  postgres:16-alpine \
  pg_dump \
    --host=postgres \
    --port=5432 \
    --username="${DB_USER}" \
    --dbname=runledger \
    --format=custom \
    --no-acl \
    --no-owner \
    > "/backups/${FILENAME}"

# Upload to S3
aws s3 cp "/backups/${FILENAME}" "s3://my-bucket/runledger-backups/${FILENAME}"
```

Schedule with system cron:
```
0 2 * * * /opt/runledger/backup.sh >> /var/log/runledger-backup.log 2>&1
```

### Managed database backups

If you use a managed Postgres service, prefer the built-in backup:

| Provider | Backup | PITR |
|----------|--------|------|
| AWS RDS | Automated daily snapshots + transaction logs | Up to 35 days |
| Google Cloud SQL | Automated backups + binary logging | Up to 7 days |
| Neon | Continuous branching / point-in-time | Up to 7 days |
| Supabase | Daily backups (Pro+) | Available on Pro+ |

Enable PITR in addition to daily snapshots — it lets you restore to within seconds of any event.

## Restore procedures

### All stores — `scripts/restore.sh`

[`scripts/restore.sh`](https://github.com/avs6/runledger-community/blob/master/scripts/restore.sh) restores
any subset of stores from S3 — the latest object per prefix, or a specific `--timestamp`:

```bash
S3_BUCKET=s3://my-bucket/runledger-backups \
DATABASE_URL=postgresql://user:pass@host:5432/runledger \
MEMORY_DB_URL=postgresql://user:pass@host:5432/memory \
QDRANT_URL=http://qdrant:6333 \
./scripts/restore.sh --control-plane --memory-db --qdrant \
    --kuzu-dir /data --skills-dir /data/skills
```

- **Postgres stores** → `pg_restore --clean --if-exists` (idempotent).
- **Qdrant** → snapshot upload/recover API.
- **Kùzu / skills** → `tar` extract into the PVC; restart `runledger-kg` / `runledger-skill-registry` to reload.

Run a restore drill on a scratch namespace periodically — that is the only way to know your backups work.
The manual per-store procedures below cover the control-plane Postgres in detail.

### From pg_dump file (control-plane)

```bash
# 1. Create an empty database (if restoring to a new instance)
createdb -h <host> -U <user> runledger_restored

# 2. Restore
pg_restore \
  --host=<host> \
  --port=5432 \
  --username=<user> \
  --dbname=runledger_restored \
  --no-owner \
  --no-acl \
  --verbose \
  runledger-20260324T020000Z.dump
```

### Full replace (same database)

```bash
# 1. Stop the API and workers to prevent writes during restore
kubectl scale deployment runledger-api runledger-worker runledger-beat --replicas=0

# 2. Drop and recreate the database
psql -h <host> -U <adminuser> -c "DROP DATABASE runledger;"
psql -h <host> -U <adminuser> -c "CREATE DATABASE runledger OWNER runledger;"

# 3. Restore
pg_restore \
  --host=<host> \
  --username=runledger \
  --dbname=runledger \
  --no-owner \
  --no-acl \
  --verbose \
  runledger-20260324T020000Z.dump

# 4. Run any pending migrations (in case the dump is behind HEAD)
kubectl run --rm -it migrations --image=ghcr.io/avs6/runledger-api:latest \
  --env DATABASE_URL="$DATABASE_URL" \
  --env SECRET_KEY="$SECRET_KEY" \
  -- alembic upgrade head

# 5. Restart all pods
kubectl scale deployment runledger-api runledger-worker runledger-beat \
  --replicas=$(kubectl get deployment runledger-api -o jsonpath='{.spec.replicas}')
```

### Point-in-time recovery (AWS RDS)

```bash
# Via AWS CLI — restore to a new DB instance
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier runledger-prod \
  --target-db-instance-identifier runledger-restored \
  --restore-time "2026-03-24T03:00:00Z"

# Wait for it to become available, then update DATABASE_URL in your secret
kubectl patch secret runledger-secrets \
  -p '{"stringData":{"DATABASE_URL":"postgresql+asyncpg://user:pass@runledger-restored.xxx.rds.amazonaws.com:5432/runledger"}}'

# Rolling restart to pick up new DB URL
kubectl rollout restart deployment/runledger-api deployment/runledger-worker deployment/runledger-beat
```

## Verify restore integrity

After restoring, verify the tamper-evident ledger snapshots are intact:

```bash
curl -H "Authorization: Bearer $ADMIN_SECRET" \
  https://api.example.com/ledger/snapshots?limit=5
```

Each snapshot contains a `snapshot_hash` that can be re-verified against the raw data. A mismatch indicates the data was modified after the snapshot was signed.

## Recovery time objectives

| Scenario | RTO | RPO |
|----------|-----|-----|
| Single pod failure | ~30s (K8s restart) | 0 |
| Primary DB failover (RDS Multi-AZ) | ~60s | ~0 (synchronous standby) |
| Full DB restore from pg_dump | 15–60 min (size-dependent) | Up to 24h (daily backup) |
| PITR | 15–30 min provisioning | ~5 min (transaction log lag) |

For RPO < 5 min, use managed PITR (RDS / Cloud SQL) rather than scheduled pg_dump.
