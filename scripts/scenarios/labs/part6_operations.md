# Part 6 - Operations, Backup, Restore, and Snapshots

*Prerequisite: Part 1 done.*

Day-2 operator tasks: growing the deployment, protecting the data, and proving that restore works.

---

## 6.1 - Add a Workspace

**Goal:** onboard a fourth team without disrupting the others.

1. As an org admin, open **Workspace** and add `AI Data Team` under Acme Corp.
2. As an org admin, open **Users** and invite/assign a workspace admin for it.
3. As that workspace admin or an org admin, switch to `AI Data Team`, open **Control Plane -> API Keys**, and mint a key.
4. Point the reusable agent at the new team by swapping the key in `.env`:
   ```bash
   RUNLEDGER_API_KEY=<new-key> LAB_FEATURE_TAG=data-agent LAB_RUNS=20 python traffic_gen.py
   ```

Verify: the new team has isolated runs, key, budgets, and data, while the org admin can still see it
alongside the other teams.

---

## 6.2 - Backup Matrix

**Goal:** know which store is authoritative and which stores are rebuildable.

| Store | Contains | Backup type | Priority |
|---|---|---|---|
| Control-plane Postgres | orgs, users, workspaces, runs, routes, pricing, budgets, outcomes, audit, ledger | `pg_dump -Fc` | Always |
| Memory Postgres | Letta memory state | `pg_dump -Fc` | If cognitive layer is used |
| Qdrant | semantic cache vectors, memory/episode vectors | Qdrant snapshot API | Optional for cache, important for memory |
| Kuzu directory | knowledge graph files | tar archive | If cognitive layer is used |
| Skill registry directory | skill bodies and metadata | tar archive | If skill injection/MCP skills are used |
| Redis | queues/cache | usually no restore | Rebuildable |
| Embedding/reranker/compression model cache | downloaded models | no restore | Re-downloadable |

The control-plane Postgres dump is the one you must never skip.

---

## 6.3 - Local Control-Plane Backup

**Goal:** create a portable dump from the Docker Compose stack.

From the repo root:

```bash
mkdir -p backup
docker compose exec -T runledger-postgres pg_dump -U runledger -Fc runledger > backup/control-plane.dump
```

Verify the dump exists:

```bash
ls -lh backup/control-plane.dump
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force backup | Out-Null
docker compose exec -T runledger-postgres pg_dump -U runledger -Fc runledger > backup/control-plane.dump
Get-Item backup/control-plane.dump
```

---

## 6.4 - Optional Durable Store Snapshots

**Goal:** snapshot the optimization/cognitive stores when they contain state you care about.

Memory DB:

```bash
docker compose exec -T runledger-memory-db pg_dump -U letta -Fc letta > backup/memory.dump
```

Qdrant collections:

```bash
curl -s http://localhost:8202/collections
curl -s -X POST http://localhost:8202/collections/<collection-name>/snapshots
curl -s http://localhost:8202/collections/<collection-name>/snapshots
```

Kuzu and skills directories are volume-backed in Compose. For a local drill, archive them from the
containers or volumes you use in your environment; in Kubernetes the Helm backup CronJob tars those PVCs
for you.

Verify: you should have a Postgres dump for each enabled DB and at least one Qdrant snapshot listed for
any collection you care about.

---

## 6.5 - Restore Drill: Backup -> Change -> Restore

**Goal:** prove the backup actually restores the product state.

1. Record a baseline:
   - Dashboard **Runs** count.
   - Dashboard **Gateway** route count.
   - Dashboard **Budgets** count.
2. Create a visible change after the backup:
   - Add a temporary Gateway route named `restore-drill-temp`.
   - Generate a few runs.
3. Simulate data loss while preserving schema/admin/pricing:
   ```bash
   uv run python scripts/cleanup.py
   ```
4. Confirm the dashboard is mostly empty.
5. Restore the control-plane dump:
   ```bash
   docker compose exec -T runledger-postgres pg_restore -U runledger -d runledger --clean --if-exists --no-owner < backup/control-plane.dump
   ```
6. Restart API/worker processes so every connection sees restored state:
   ```bash
   docker compose restart runledger-api runledger-worker runledger-beat
   ```

Verify: the baseline routes, budgets, users, workspaces, runs, outcomes, and audit records are back.
The temporary data created after the backup should be gone.

---

## 6.6 - Qdrant Snapshot Restore Drill

**Goal:** practice vector-store recovery separately from Postgres.

1. Pick a collection:
   ```bash
   curl -s http://localhost:8202/collections
   ```
2. Create a snapshot:
   ```bash
   curl -s -X POST http://localhost:8202/collections/<collection-name>/snapshots
   ```
3. Download the snapshot from Qdrant's snapshot endpoint or copy it from the Qdrant volume if you are
   doing a deeper local drill.
4. Restore it to a scratch Qdrant instance or collection first. Do not test destructive Qdrant restore
   on your only local stack unless you are comfortable recreating vectors.

Production restore uses the Qdrant upload/recover API through `scripts/restore.sh`:

```bash
S3_BUCKET=s3://my-org-runledger-backups \
QDRANT_URL=http://qdrant:6333 \
./scripts/restore.sh --qdrant --timestamp 20260728T020000Z
```

Verify: semantic-cache or memory-vector lookups still work after restore. If only semantic cache was lost,
it is acceptable for hit rate to rebuild over time.

---

## 6.7 - Ledger Snapshot Integrity After Restore

**Goal:** confirm finance/audit snapshots remain tamper-evident after a restore.

1. After restoring, open **Ledger** or call the API:
   ```bash
   curl -H "Authorization: Bearer <dashboard-session-key>" \
     "http://localhost:8201/ledger/snapshots?limit=5"
   ```
2. Record the latest `snapshot_hash` and `prev_snapshot_hash`.
3. Compare the sequence before and after a restore drill.

Verify: restored snapshots are present and the hash chain is intact. If a snapshot hash no longer
matches, treat it as possible data tampering or a bad restore source.

---

## 6.8 - Production Backups to S3

**Goal:** enable the Kubernetes multi-store backup CronJob.

1. Create a bucket:
   ```bash
   aws s3 mb s3://my-org-runledger-backups --region us-east-1
   ```
2. Create a least-privilege IAM policy. The backup job writes; `restore.sh` reads:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket", "s3:DeleteObject"],
         "Resource": [
           "arn:aws:s3:::my-org-runledger-backups",
           "arn:aws:s3:::my-org-runledger-backups/*"
         ]
       }
     ]
   }
   ```
3. On EKS, grant it to the backup pod via IRSA:
   ```yaml
   serviceAccount:
     create: true
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/runledger-backup
   ```
4. Enable backups in `infra/helm/runledger/values.yaml`:
   ```yaml
   backup:
     enabled: true
     schedule: "0 2 * * *"
     s3Bucket: "s3://my-org-runledger-backups"
     awsRegion: us-east-1
     retainDays: 30
     stores:
       memoryDb: { enabled: true }
       qdrant:   { enabled: false }
       kuzu:     { enabled: true }
       skills:   { enabled: true }
   ```
5. Upgrade:
   ```bash
   helm upgrade runledger infra/helm/runledger -f infra/helm/runledger/values.yaml
   ```
6. Trigger a manual backup and confirm objects landed:
   ```bash
   kubectl create job --from=cronjob/runledger-backup runledger-backup-manual
   kubectl logs -f job/runledger-backup-manual
   aws s3 ls s3://my-org-runledger-backups/control-plane/
   ```

---

## 6.9 - Production Restore With `scripts/restore.sh`

**Goal:** restore one or more stores from S3.

```bash
S3_BUCKET=s3://my-org-runledger-backups \
DATABASE_URL=postgresql://runledger:pass@pg:5432/runledger \
MEMORY_DB_URL=postgresql://letta:letta@memory-db:5432/letta \
QDRANT_URL=http://qdrant:6333 \
./scripts/restore.sh --control-plane --memory-db --qdrant --timestamp 20260728T020000Z
```

With no `--timestamp`, the latest object under each prefix is used. Each store is independent, so you
can restore only the control plane, only Qdrant, or only memory DB during an incident.

After restore:

1. Run pending migrations if the dump is older than the deployed app.
2. Restart API, worker, beat, and any cognitive services whose stores were restored.
3. Re-run the ledger snapshot integrity check in 6.7.
4. Confirm Gateway routes, API keys, budgets, runs, and dashboards load.

Full runbook: [`docs/backup-restore.md`](../../../docs/backup-restore.md).

---

End of Part 6. You added a workspace, backed up the control plane, practiced snapshots, restored from
backup, verified ledger integrity, and mapped the production S3 restore path. Next:
**[Part 7 - Control Plane & Platform Settings](./part7_settings.md)**.
