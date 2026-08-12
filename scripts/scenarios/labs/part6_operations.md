# Part 6 - Operations, Backup, Restore, and Snapshots

*Prerequisite: Part 1 completed.*

## 6.1 - Add a workspace

Add `Backup Restore Lab` under `LocalAIAgentStack`, mint a key, and send a little
traffic with it.

```bash
RUNLEDGER_API_KEY=<new-key> LAB_FEATURE_TAG=data-agent LAB_RUNS=20 python traffic_gen.py
```

Verify the new workspace stays isolated while still visible to the org admin.

## 6.2 - Backup matrix

Review which stores are authoritative and which are rebuildable:

- Control-plane Postgres
- Memory Postgres
- Qdrant
- Kuzu
- Skills directory
- Redis

## 6.3 - Local control-plane backup

```bash
mkdir -p backup
docker compose exec -T runledger-postgres pg_dump -U runledger -Fc runledger > backup/control-plane.dump
```

## 6.4 - Optional store snapshots

Take memory or Qdrant snapshots if those stores contain state you care about.

## 6.5 - Restore drill

1. Record counts for runs, routes, and budgets.
2. Create a visible change.
3. Run `uv run python scripts/cleanup.py`.
4. Restore the dump.
5. Restart API and workers.

Verify the pre-backup state returns.

## 6.6 - Qdrant restore drill

Practice a vector-store recovery separately from the control plane.

## 6.7 - Ledger integrity

Verify the latest ledger snapshot chain is intact after restore.

## 6.8 - Production backups to S3

Use the repo backup flow for S3-backed production snapshots.

## 6.9 - Production restore

Use `scripts/restore.sh` when restoring one or more stores from backup artifacts.

Next: [Part 7 - Control Plane and Platform Settings](./part7_settings.md)
