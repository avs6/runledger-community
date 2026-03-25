# Zero-Downtime Upgrade Guide

RunLedger uses Alembic for database migrations and supports zero-downtime upgrades for most schema changes. This guide explains the strategy, constraints, and step-by-step procedure.

## Upgrade philosophy

> **All migrations must be backwards-compatible with the previous application version.**

This means the N+1 version of the code must run safely against the N schema (before migration) AND the N+1 schema (after migration). This allows a rolling deployment where some pods run the old code and some run the new code simultaneously.

### What this means in practice

| Change | Safe for zero-downtime? | Notes |
|--------|------------------------|-------|
| Add nullable column | ✅ Yes | Old code ignores it; new code reads `None` |
| Add column with default | ✅ Yes | Old code still inserts successfully |
| Add new table | ✅ Yes | Old code never reads it |
| Add index | ✅ Yes (with `CONCURRENTLY`) | Use `op.create_index(..., postgresql_concurrently=True)` |
| Rename column | ⚠️ Two-phase | Add new column → deploy → backfill → drop old column |
| Drop column | ⚠️ Two-phase | Deploy code without the column first → then drop |
| Add NOT NULL without default | ❌ Requires maintenance | Old code can't insert; must backfill first |
| Change column type | ⚠️ Two-phase | Add new column → backfill → switch reads → drop old |

## Standard upgrade procedure (Kubernetes / Helm)

### 1. Migrations run automatically

The Helm chart runs `alembic upgrade head` as a `pre-upgrade` Job before any pods restart:

```yaml
migrations:
  enabled: true
  backoffLimit: 3
```

The migration Job runs to completion before Helm proceeds to update the Deployments.

### 2. Rolling pod replacement

After migrations succeed, Kubernetes performs a rolling update:

```
Old: [API v1] [API v1] [API v1]
         ↓
Mid: [API v1] [API v1] [API v2]   ← new schema, both versions running
         ↓
New: [API v2] [API v2] [API v2]
```

During the transition, both v1 and v2 pods are live. The migration must be compatible with both versions.

### 3. Upgrade command

```bash
# Update image tags in your values file, then:
helm upgrade runledger ./infra/helm/runledger \
  --namespace runledger \
  --values my-values.yaml \
  --atomic \            # Rollback automatically if upgrade fails
  --timeout 5m
```

`--atomic` ensures that if the migration Job fails or the new pods don't become ready within the timeout, Helm rolls back the Deployment to the previous version. The migration itself is not automatically rolled back — see rollback section below.

## Manual upgrade (Docker Compose)

```bash
# 1. Pull the new image
docker compose pull

# 2. Run migrations (against live database, with app still running)
docker compose run --rm api alembic upgrade head

# 3. Rolling restart (one replica at a time if using multiple)
docker compose up -d --no-deps api worker beat web
```

## Rollback

### Application rollback (no schema change)

If the new image has a bug unrelated to schema:

```bash
# Helm — rollback to previous release
helm rollback runledger --namespace runledger

# Or Docker Compose — pin to previous tag
docker compose up -d --no-deps api   # with old image tag in compose.yml
```

### Schema rollback (Alembic downgrade)

Alembic supports `downgrade` but RunLedger migrations are generally **not written as reversible** because:
1. Dropping data (removed columns/tables) is permanent.
2. The risk of downgrade is usually higher than the risk of forward fix.

For reversible migrations, the `downgrade()` function is implemented. For destructive ones, it's a `pass`.

To check if a downgrade is available:

```bash
# Check migration history
docker compose run --rm api alembic history

# Attempt downgrade (read the migration carefully first!)
docker compose run --rm api alembic downgrade -1
```

### Emergency: last-resort rollback with data loss risk

If a migration added a NOT NULL column with a default and you need to roll back:

```sql
-- Manually remove the column added by the migration
ALTER TABLE my_table DROP COLUMN IF EXISTS new_column;

-- Update the alembic_version table to reflect the prior revision
UPDATE alembic_version SET version_num = '035';
```

Then redeploy the old application image.

## Multi-phase migration pattern

For breaking changes (column rename, type change, NOT NULL addition), use a two-phase approach:

### Phase 1: Add (deploy with N+1 code that writes both old + new)

```python
# Migration 042_add_new_column.py
def upgrade():
    op.add_column('my_table', sa.Column('new_col', sa.Text(), nullable=True))
    # Backfill existing rows
    op.execute("UPDATE my_table SET new_col = old_col WHERE new_col IS NULL")
```

Deploy application code that writes to both `old_col` and `new_col`.

### Phase 2: Remove (after all pods run the new code)

```python
# Migration 043_drop_old_column.py (next release)
def upgrade():
    op.drop_column('my_table', 'old_col')
```

Deploy application code that only reads `new_col`.

## Index migrations

Always create indexes concurrently to avoid table locks:

```python
def upgrade():
    op.create_index(
        'ix_agent_runs_workspace_started',
        'agent_runs',
        ['workspace_id', 'started_at'],
        postgresql_concurrently=True,
    )
```

Note: `CONCURRENTLY` cannot run inside a transaction. Alembic handles this by detecting `postgresql_concurrently=True` and running outside the implicit transaction.

## Checking migration status

```bash
# What version is the database at?
docker compose run --rm api alembic current

# What migrations are pending?
docker compose run --rm api alembic heads
docker compose run --rm api alembic history --verbose

# Kubernetes
kubectl exec -n runledger deployment/runledger-api -- alembic current
```

## Health check during upgrade

Monitor the readiness endpoint during upgrades:

```bash
watch -n 2 'kubectl get pods -n runledger -l app.kubernetes.io/name=runledger'
```

A pod in `Running` state but failing readiness probes will be temporarily removed from the Service's endpoint list and receive no traffic until it passes both `/health/live` and `/health/ready`.
