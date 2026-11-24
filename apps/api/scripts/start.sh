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

# The seed creates a demo admin and dev key, so it only runs in development (P-01).
echo "→ Seeding database (development only; idempotent)..." | tee -a "$LOG"
SEED_OUTPUT=$(python /app/scripts/seed.py 2>&1)
# Full output (including a newly created API key) goes to the console only; the
# bind-mounted log gets the key redacted (review P-23).
printf '%s\n' "$SEED_OUTPUT"
printf '%s\n' "$SEED_OUTPUT" | sed -E 's/^(API Key: *rl_[A-Za-z0-9]{0,8})[A-Za-z0-9_-]*/\1...(redacted)/' >> "$LOG"
echo "" | tee -a "$LOG"

# Extract the API key — only present on first run when the key is created
API_KEY=$(printf '%s\n' "$SEED_OUTPUT" | grep "^API Key:" | awk '{print $NF}' || true)
if [ -z "$API_KEY" ]; then
  API_KEY="(already created; create a new key in Settings > API Keys if lost)"
fi

# ── Ready banner ──────────────────────────────────────────────────────────────

{
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RunLedger is ready"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Dashboard   →  http://localhost:3201"
echo "  API docs    →  http://localhost:8201/docs"
echo "  Health      →  http://localhost:8201/health"
echo ""
if [ "${ENVIRONMENT:-production}" = "development" ]; then
echo "  Login       →  admin@runledger.local  /  runledger   (development only)"
echo "  API Key     →  ${API_KEY:0:11}... (full key shown once above, on first start)"
else
echo "  First run   →  open the dashboard at /setup (needs ADMIN_SECRET) or call"
echo "                 POST /admin/bootstrap; no default account exists in production"
fi
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
