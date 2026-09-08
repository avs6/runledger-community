# Operations

Backup, restore, and operational drills.

## Add a Workspace

Add `Backup Restore Lab` under `LocalAIAgentStack`, mint a key, and send traffic:

```bash
RUNLEDGER_API_KEY=<new-key> LAB_FEATURE_TAG=data-agent LAB_RUNS=20 python traffic_gen.py
```

Verify the new workspace stays isolated while still visible to the org admin.

## Backup Matrix

Review which stores are authoritative and which are rebuildable:

| Store | Type | Authoritative? |
|---|---|---|
| Control-plane Postgres | RDBMS | Yes |
| Memory Postgres | RDBMS | Yes |
| Qdrant | Vector | Rebuildable |
| Kuzu | Graph | Rebuildable |
| Skills directory | Files | Yes |
| Redis | Cache | Rebuildable |

## Local Control-Plane Backup

```bash
mkdir -p backup
docker compose exec -T runledger-postgres pg_dump -U runledger -Fc runledger > backup/control-plane.dump
```

## Restore Drill

1. Record counts for runs, routes, and budgets.
2. Create a visible change.
3. Run `python scripts/run_demo.py cleanup`.
4. Restore the dump.
5. Restart API and workers.

Verify the pre-backup state returns.

## Qdrant Restore

Practice a vector-store recovery separately from the control plane.

## Ledger Integrity

Verify the latest ledger snapshot chain is intact after restore.

## Production Backups (S3)

Use the backup flow for S3-backed production snapshots. For local MinIO:

```bash
python scripts/localai/localai_s3_backup.py ensure-bucket
python scripts/localai/localai_s3_backup.py backup
python scripts/localai/localai_s3_backup.py list
```

## Production Restore

Use `scripts/restore.sh` when restoring one or more stores from backup artifacts.

---

Next: [Platform Settings](./platform-settings.md)
