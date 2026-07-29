# Part 6 · Operations

*Prerequisite: Part 1 done.*

Day-2 operator tasks: growing the deployment, and protecting the data.

---

## 6.1 · Add a workspace (a new team) — live

**Goal:** onboard a fourth team without disrupting the others.

1. Open **Workspace** → add `AI Data Team` under Acme Corp.
2. Open **Users** → invite/assign a workspace admin for it.
3. Open **Settings → API Keys** (with that workspace active) → mint a key.
4. Point the reusable agent at the new team — just swap the key in `.env`:
   ```bash
   RUNLEDGER_API_KEY=<new-key> LAB_FEATURE_TAG=data-agent LAB_RUNS=20 python traffic_gen.py
   ```

🔎 The new team is fully isolated — its own key, data, budgets, routes — yet the org admin
sees it alongside the others. Adding capacity is a GUI action, not a redeploy.

---

## 6.2 · Backup & Restore

RunLedger's durable stores are the **control-plane Postgres** (all runs, config, pricing,
budgets…), the **memory Postgres** (Letta), **Qdrant** (vectors), and the Kùzu/skills dirs. In
production a Helm **CronJob** dumps them all to S3 and [`scripts/restore.sh`](../../restore.sh)
restores them (runbook: `docs/optimization/ha-and-backup.mdx`). Locally you can do the same
thing by hand — the control-plane dump is the one that matters most.

### Back up (local docker stack)

```bash
mkdir -p backup
docker compose exec -T runledger-postgres pg_dump -U runledger -Fc runledger > backup/control-plane.dump
```

Optional, if you're using the cognitive layer:

```bash
docker compose exec -T runledger-memory-db pg_dump -U letta -Fc letta > backup/memory.dump
# Qdrant HTTP is on host port 8202 — trigger a snapshot per collection:
curl -s -X POST http://localhost:8202/collections/{collection}/snapshots
```

### Prove it works (backup → change → restore)

1. Note your current run count (dashboard → Runs, or the Analytics page).
2. Simulate data loss — truncate everything but keep the schema:
   ```bash
   uv run python scripts/cleanup.py      # wipes data, preserves admin + pricing
   ```
   Confirm the dashboard is now empty.
3. Restore from the dump:
   ```bash
   docker compose exec -T runledger-postgres pg_restore -U runledger -d runledger --clean --if-exists --no-owner < backup/control-plane.dump
   ```
4. Refresh the dashboard — your runs, budgets, and config are back.

🔎 The restore is `pg_restore` of a custom-format dump — the same format the production
CronJob and `restore.sh` use, so what you practice here matches production.

### Production path — scheduled backups to S3 (Kubernetes)

The local `pg_dump` above is fine for a laptop; in production the Helm chart runs a
**CronJob** ([`backup-cronjob.yaml`](../../../infra/helm/runledger/templates/backup-cronjob.yaml))
that dumps every store to S3 on a schedule. Set it up once:

**1. Create the bucket**

```bash
aws s3 mb s3://my-org-runledger-backups --region us-east-1
```

**2. Create a least-privilege IAM policy** (the backup job writes; `restore.sh` reads):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket", "s3:DeleteObject"],
      "Resource": [
        "arn:aws:s3:::my-org-runledger-backups",
        "arn:aws:s3:::my-org-runledger-backups/*"
      ] }
  ]
}
```

**3. Grant it to the backup pod via IRSA** — the CronJob authenticates through its
**service account**, not static keys. On EKS, create an IAM role for the service account
with the policy above, then annotate the chart's service account with the role ARN in
`values.yaml`:

```yaml
serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/runledger-backup
```

(Not on EKS? Attach the policy to the node instance profile, or add static AWS keys to the
pod another way — but IRSA is the intended path and avoids long-lived keys.)

**4. Turn on backups in Helm values** (`infra/helm/runledger/values.yaml`) and upgrade:

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"        # 02:00 UTC daily
  s3Bucket: "s3://my-org-runledger-backups"
  awsRegion: us-east-1
  retainDays: 30
  stores:
    memoryDb: { enabled: true }
    qdrant:   { enabled: false }   # semantic cache is regenerable; episodic memory isn't
    kuzu:     { enabled: true }
    skills:   { enabled: true }
```

```bash
helm upgrade runledger infra/helm/runledger -f infra/helm/runledger/values.yaml
```

**5. Verify** — trigger a one-off run and confirm objects land:

```bash
kubectl create job --from=cronjob/runledger-backup runledger-backup-manual
kubectl logs -f job/runledger-backup-manual
aws s3 ls s3://my-org-runledger-backups/control-plane/
```

**6. Restore from S3** with the companion script — each store is independent:

```bash
S3_BUCKET=s3://my-org-runledger-backups \
DATABASE_URL=postgresql://runledger:pass@pg:5432/runledger \
MEMORY_DB_URL=postgresql://letta:letta@memory-db:5432/letta \
QDRANT_URL=http://qdrant:6333 \
AWS_ACCESS_KEY_ID=AKIA... AWS_SECRET_ACCESS_KEY=... \
./scripts/restore.sh --control-plane --memory-db [--timestamp 20260728T020000Z]
```

With no `--timestamp`, the latest object under each prefix is used. Full runbook:
`docs/optimization/ha-and-backup.mdx`.

---

✅ **End of Part 6 — and the workbook.** You've provisioned teams, instrumented agents three
ways, observed and alerted, run evaluations/experiments/replays, applied optimization and
governance policies, and proven backup/restore. That's the full RunLedger surface, end to end.
