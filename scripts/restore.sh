#!/usr/bin/env bash
#
# RunLedger restore — companion to the multi-store backup CronJob
# (infra/helm/runledger/templates/backup-cronjob.yaml).
#
# Restores any subset of the durable stores from S3. Each store is independent;
# pass only the flags you need. Runbook: docs/optimization/ha-and-backup.mdx.
#
# Prerequisites: awscli, pg_restore (postgresql-client), curl, tar.
#
# Usage:
#   S3_BUCKET=s3://my-bucket/runledger-backups \
#   DATABASE_URL=postgresql://user:pass@host:5432/runledger \
#   MEMORY_DB_URL=postgresql://user:pass@host:5432/memory \
#   QDRANT_URL=http://qdrant:6333 \
#   ./scripts/restore.sh --control-plane --memory-db --qdrant \
#       --kuzu-dir /data --skills-dir /data/skills [--timestamp 20260728T020000Z]
#
# With no --timestamp, the latest object under each prefix is used.
set -euo pipefail

: "${S3_BUCKET:?set S3_BUCKET (e.g. s3://my-bucket/runledger-backups)}"

TS=""; DO_CP=0; DO_MEM=0; DO_QDRANT=0; KUZU_DIR=""; SKILLS_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --control-plane) DO_CP=1 ;;
    --memory-db)     DO_MEM=1 ;;
    --qdrant)        DO_QDRANT=1 ;;
    --kuzu-dir)      KUZU_DIR="$2"; shift ;;
    --skills-dir)    SKILLS_DIR="$2"; shift ;;
    --timestamp)     TS="$2"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

# Resolve the newest object under a prefix (or the one matching $TS).
latest() {  # $1 = prefix
  if [ -n "$TS" ]; then
    aws s3 ls "${S3_BUCKET}/$1/" | awk '{print $4}' | grep "$TS" | head -1
  else
    aws s3 ls "${S3_BUCKET}/$1/" | sort | awk '{print $4}' | tail -1
  fi
}

fetch() {  # $1 = prefix -> echoes local path
  local f; f=$(latest "$1")
  [ -n "$f" ] || { echo "no backup found under ${S3_BUCKET}/$1/" >&2; return 1; }
  aws s3 cp "${S3_BUCKET}/$1/${f}" "/tmp/${f}" >&2
  echo "/tmp/${f}"
}

if [ "$DO_CP" = 1 ]; then
  : "${DATABASE_URL:?set DATABASE_URL for --control-plane}"
  echo "[control-plane] restoring…"
  f=$(fetch control-plane)
  pg_restore --clean --if-exists --no-owner --no-acl \
    -d "${DATABASE_URL/postgresql+asyncpg:/postgresql:}" "$f"
  echo "[control-plane] done"
fi

if [ "$DO_MEM" = 1 ]; then
  : "${MEMORY_DB_URL:?set MEMORY_DB_URL for --memory-db}"
  echo "[memory-db] restoring…"
  f=$(fetch memory-db)
  pg_restore --clean --if-exists --no-owner --no-acl -d "$MEMORY_DB_URL" "$f"
  echo "[memory-db] done"
fi

if [ "$DO_QDRANT" = 1 ]; then
  : "${QDRANT_URL:?set QDRANT_URL for --qdrant}"
  echo "[qdrant] restoring…"
  f=$(fetch qdrant)
  curl -sf -X POST "${QDRANT_URL}/snapshots/upload?priority=snapshot" \
    -H "Content-Type: multipart/form-data" -F "snapshot=@${f}"
  echo "[qdrant] done"
fi

if [ -n "$KUZU_DIR" ]; then
  echo "[kuzu] restoring into ${KUZU_DIR}…"
  f=$(fetch kuzu)
  mkdir -p "$KUZU_DIR"; tar xzf "$f" -C "$KUZU_DIR"
  echo "[kuzu] done — restart runledger-kg to reload"
fi

if [ -n "$SKILLS_DIR" ]; then
  echo "[skills] restoring into ${SKILLS_DIR}…"
  f=$(fetch skills)
  mkdir -p "$SKILLS_DIR"; tar xzf "$f" -C "$SKILLS_DIR"
  echo "[skills] done — restart runledger-skill-registry to reload"
fi

echo "Restore complete."
