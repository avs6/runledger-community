#!/bin/sh
set -e

echo "→ Running database migrations..."
alembic upgrade head

echo "→ Seeding database (idempotent — safe to run on every start)..."
python /app/scripts/seed.py

echo ""
echo "┌─────────────────────────────────────────────────┐"
echo "│              RunLedger is ready                  │"
echo "├─────────────────────────────────────────────────┤"
echo "│  Dashboard    http://localhost:3000              │"
echo "│  API docs     http://localhost:8000/docs         │"
echo "│  Health       http://localhost:8000/health       │"
echo "├─────────────────────────────────────────────────┤"
echo "│  Login        admin@runledger.local              │"
echo "│  Password     runledger                          │"
echo "├─────────────────────────────────────────────────┤"
echo "│  API key printed above (shown once on first run) │"
echo "├─────────────────────────────────────────────────┤"
echo "│  Logs  docker compose -f infra/docker-compose   │"
echo "│              .yml logs -f [api|web|worker]       │"
echo "└─────────────────────────────────────────────────┘"
echo ""

echo "→ Starting API..."
exec uvicorn runledger_api.main:app --host 0.0.0.0 --port 8000
