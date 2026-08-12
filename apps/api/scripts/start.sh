#!/bin/bash
set -e

LOG=/app/logs/startup.log
mkdir -p /app/logs

# ── Migrations ────────────────────────────────────────────────────────────────

echo "── RunLedger startup $(date -u '+%Y-%m-%d %H:%M:%S UTC') ──────────────────────" | tee "$LOG"
echo "" | tee -a "$LOG"

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "→ Running database migrations..." | tee -a "$LOG"
  alembic upgrade head 2>&1 | tee -a "$LOG"
else
  echo "→ Skipping migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS})" | tee -a "$LOG"
fi
echo "" | tee -a "$LOG"

# ── Seed (capture output so we can extract the API key) ───────────────────────

echo "→ Seeding database (idempotent — safe on every start)..." | tee -a "$LOG"
SEED_OUTPUT=$(python /app/scripts/seed.py 2>&1)
printf '%s\n' "$SEED_OUTPUT" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Extract the API key — only present on first run when the key is created
API_KEY=$(printf '%s\n' "$SEED_OUTPUT" | grep "^API Key:" | awk '{print $NF}' || true)
if [ -z "$API_KEY" ]; then
  API_KEY="(already created — check logs/startup.log from first run)"
fi

# ── Ready banner ──────────────────────────────────────────────────────────────

{
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RunLedger is ready"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Dashboard   →  http://localhost:3000"
echo "  API docs    →  http://localhost:8000/docs"
echo "  Health      →  http://localhost:8000/health"
echo ""
echo "  Login       →  admin@runledger.local  /  runledger"
echo "  API Key     →  $API_KEY"
echo ""
echo "  Logs        →  docker compose logs -f runledger-api"
echo "  Log file    →  logs/startup.log  (at repo root)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
} | tee -a "$LOG"

# ── Start API ─────────────────────────────────────────────────────────────────

echo "→ Starting API..." | tee -a "$LOG"
exec uvicorn runledger_api.main:app --host 0.0.0.0 --port 8000
