#!/usr/bin/env bash
# RunLedger Codespace setup — runs once after container creation
set -euo pipefail

echo "==> Waiting for Postgres to be ready..."
until pg_isready -h localhost -p 5432 -U runledger 2>/dev/null; do
  sleep 1
done

echo "==> Running Alembic migrations..."
cd /app/apps/api
uv run alembic upgrade head

echo "==> Bootstrapping platform admin..."
curl -s -X POST http://localhost:8000/admin/bootstrap \
  -H "X-Admin-Secret: runledger-admin" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin123!","full_name":"Admin","org_name":"Demo"}' \
  || echo "(bootstrap already done or API not ready yet — run manually)"

echo ""
echo "==> RunLedger is ready!"
echo "    Dashboard: http://localhost:3000"
echo "    API docs:  http://localhost:8000/docs"
echo "    Login:     admin@example.com / Admin123!"
