# Backup and Restore

## Backup strategy

RunLedger uses PostgreSQL as its system of record. All Redis state is either:
- **Ephemeral** (Celery queues, rate-limit counters) — lost on Redis restart, safe to discard
- **Derived** (budget counters) — rebuilt from Postgres on next request

This means **only PostgreSQL requires backup**. Redis does not.

## Automated backups

### Via Helm chart (K8s)

Enable the nightly backup CronJob in your values:

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"          # 02:00 UTC daily
  s3Bucket: "s3://my-bucket/runledger-backups"
  awsRegion: us-east-1
  retainDays: 30
```

The job uses `pg_dump --format=custom` and uploads a `.dump` file to S3. Files older than `retainDays` are pruned automatically.

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

### From pg_dump file

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
