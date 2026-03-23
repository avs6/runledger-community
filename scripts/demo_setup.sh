#!/usr/bin/env bash
# =============================================================================
# RunLedger Demo Setup Script
# Creates orgs, users, budgets, gateway aliases, runs, outcomes, and reports
# =============================================================================
set -uo pipefail

API="http://localhost:8000"
ADMIN_EMAIL="admin@runledger.local"
ADMIN_PASSWORD="runledger"
ADMIN_SECRET="${ADMIN_SECRET:-runledger-admin}"

sep()  { echo; echo "──────────────────────────────────────────────────────"; echo "  $*"; echo "──────────────────────────────────────────────────────"; }
ok()   { echo "  ✓ $*"; }
info() { echo "  → $*"; }
warn() { echo "  ⚠ $*"; }

# Post with idempotency: returns response body; doesn't exit on 4xx
post() {
  local url="$1"; shift
  curl -s -X POST "$url" "$@"
}

extract_id() {
  grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4
}

# ── 0. Login as Platform Admin ────────────────────────────────────────────────
sep "Step 0 — Login as Platform Admin"
LOGIN=$(curl -s "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")
ADMIN_KEY=$(echo "$LOGIN" | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)
DEFAULT_WS=$(echo "$LOGIN" | grep -o '"workspace_id":"[^"]*"' | cut -d'"' -f4)
ok "Logged in as Platform Admin"
ok "Default workspace: $DEFAULT_WS"
ok "API key: ${ADMIN_KEY:0:24}..."

# ── 1. Create two tenants (orgs) ──────────────────────────────────────────────
sep "Step 1 — Create Orgs (Tenants)"

ACME=$(post "$API/admin/tenants" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Corp","plan":"starter","admin_email":"alice@acme.com","admin_password":"acme-secret-123","admin_full_name":"Alice Chen"}')
ACME_ID=$(echo "$ACME" | extract_id)
if [ -z "$ACME_ID" ]; then
  # May already exist — look it up from tenant list
  ACME_ID=$(curl -s "$API/admin/tenants" -H "X-Admin-Secret: $ADMIN_SECRET" -H "Authorization: Bearer $ADMIN_KEY" | \
    grep -o '"id":"[^"]*","name":"Acme Corp"' | grep -o '"id":"[^"]*"' | cut -d'"' -f4 || true)
  warn "Acme Corp already exists (id: $ACME_ID)"
else
  ok "Tenant: Acme Corp ($ACME_ID)"
fi

NOVA=$(post "$API/admin/tenants" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"Nova AI","plan":"growth","admin_email":"carol@nova.ai","admin_password":"nova-secret-456","admin_full_name":"Carol Davis"}')
NOVA_ID=$(echo "$NOVA" | extract_id)
if [ -z "$NOVA_ID" ]; then
  NOVA_ID=$(curl -s "$API/admin/tenants" -H "X-Admin-Secret: $ADMIN_SECRET" -H "Authorization: Bearer $ADMIN_KEY" | \
    grep -o '"id":"[^"]*","name":"Nova AI"' | grep -o '"id":"[^"]*"' | cut -d'"' -f4 || true)
  warn "Nova AI already exists (id: $NOVA_ID)"
else
  ok "Tenant: Nova AI ($NOVA_ID)"
fi

# ── 2. Get/create workspaces for each org (admin creates via bootstrap) ────────
sep "Step 2 — Verify Workspaces"

ACME_WS_LIST=$(curl -s "$API/admin/tenants/$ACME_ID/workspaces" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -H "Authorization: Bearer $ADMIN_KEY")
ACME_WS=$(echo "$ACME_WS_LIST" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
ok "Acme workspace: $ACME_WS"

NOVA_WS_LIST=$(curl -s "$API/admin/tenants/$NOVA_ID/workspaces" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -H "Authorization: Bearer $ADMIN_KEY")
NOVA_WS=$(echo "$NOVA_WS_LIST" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
ok "Nova workspace: $NOVA_WS"

# ── 3. Create additional workspace via org API ─────────────────────────────────
sep "Step 3 — Create extra workspace for default org"
WS2=$(curl -s -X POST "$API/org/workspaces" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"staging"}')
WS2_ID=$(echo "$WS2" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
ok "Created workspace: staging ($WS2_ID)"

# ── 4. Create Budgets ─────────────────────────────────────────────────────────
sep "Step 4 — Create Budgets"

BUDGET1=$(curl -s -X POST "$API/budgets" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "scope_type": "workspace",
    "period_type": "monthly",
    "limit_usd": 500,
    "action": "notify"
  }')
BUDGET1_ID=$(echo "$BUDGET1" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
ok "Budget: workspace monthly \$500 notify (id: $BUDGET1_ID)"

BUDGET2=$(curl -s -X POST "$API/budgets" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "scope_type": "workspace",
    "period_type": "daily",
    "limit_usd": 25,
    "action": "block"
  }')
BUDGET2_ID=$(echo "$BUDGET2" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
ok "Budget: workspace daily \$25 hard block (id: $BUDGET2_ID)"

BUDGET3=$(curl -s -X POST "$API/budgets" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "scope_type": "end_user",
    "scope_id": "user-alice",
    "period_type": "daily",
    "limit_usd": 5,
    "action": "notify"
  }')
BUDGET3_ID=$(echo "$BUDGET3" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
ok "Budget: user-alice daily \$5 notify (id: $BUDGET3_ID)"

# ── 5. Create Gateway Aliases (Routes) ────────────────────────────────────────
sep "Step 5 — Create Gateway Aliases"

R1=$(curl -s -X POST "$API/gateway/routes" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "default-gpt4o",
    "provider": "openai",
    "target_model": "gpt-4o",
    "base_url": "https://api.openai.com/v1",
    "priority": 10
  }')
ok "Alias: default-gpt4o → openai/gpt-4o (id: $(echo $R1 | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4))"

R2=$(curl -s -X POST "$API/gateway/routes" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "cheap-mini",
    "provider": "openai",
    "target_model": "gpt-4o-mini",
    "base_url": "https://api.openai.com/v1",
    "priority": 5
  }')
ok "Alias: cheap-mini → openai/gpt-4o-mini (id: $(echo $R2 | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4))"

R3=$(curl -s -X POST "$API/gateway/routes" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "claude-sonnet",
    "provider": "anthropic",
    "target_model": "claude-sonnet-4-6",
    "priority": 8
  }')
ok "Alias: claude-sonnet → anthropic/claude-sonnet-4-6 (id: $(echo $R3 | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4))"

# ── 6. Simulate Agent Runs ─────────────────────────────────────────────────────
sep "Step 6 — Simulate Agent Runs (15 runs)"

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
KEY="$ADMIN_KEY"

simulate_run() {
  local workflow="$1" model="$2" provider="$3" in_t="$4" out_t="$5" status="$6" user="$7"

  # Cost calculation using awk (no bc dependency)
  local cost end_status
  cost=$(awk -v model="$model" -v in_t="$in_t" -v out_t="$out_t" 'BEGIN {
    if (model == "gpt-4o")            { c = in_t*2.50/1000000 + out_t*10.00/1000000 }
    else if (model == "gpt-4o-mini")  { c = in_t*0.15/1000000 + out_t*0.60/1000000 }
    else if (model ~ /claude/)        { c = in_t*3.00/1000000 + out_t*15.00/1000000 }
    else                              { c = 0.001 }
    printf "%.6f", c
  }')

  # Map provider_call status: API uses success/error; span/run use succeeded/failed/cancelled
  if [ "$status" = "error" ]; then end_status="failed"; else end_status="succeeded"; fi

  # Generate UUIDs — use PowerShell on Windows if /proc not available
  run_id=$(cat /proc/sys/kernel/random/uuid 2>/dev/null \
    || powershell.exe -NoProfile -Command "[guid]::NewGuid().ToString()" 2>/dev/null \
    || awk 'BEGIN{srand();printf"%08x-%04x-%04x-%04x-%012x\n",int(rand()*2^32),int(rand()*2^16),int(rand()*2^16),int(rand()*2^16),int(rand()*2^48)}')
  span_id=$(cat /proc/sys/kernel/random/uuid 2>/dev/null \
    || powershell.exe -NoProfile -Command "[guid]::NewGuid().ToString()" 2>/dev/null \
    || awk 'BEGIN{srand();printf"%08x-%04x-%04x-%04x-%012x\n",int(rand()*2^32),int(rand()*2^16),int(rand()*2^16),int(rand()*2^16),int(rand()*2^48)}')
  latency=$((RANDOM % 2000 + 200))

  curl -s -X POST "$API/ingest/v1/batch" \
    -H "Authorization: Bearer $KEY" \
    -H "Content-Type: application/json" \
    -d "{\"events\":[
      {\"event_type\":\"run_start\",\"run_id\":\"$run_id\",\"started_at\":\"$NOW\",\"end_user_id\":\"$user\",\"feature_tag\":\"$workflow\"},
      {\"event_type\":\"span_start\",\"span_id\":\"$span_id\",\"run_id\":\"$run_id\",\"span_type\":\"llm\",\"name\":\"llm-call\",\"started_at\":\"$NOW\"},
      {\"event_type\":\"provider_call\",\"run_id\":\"$run_id\",\"span_id\":\"$span_id\",\"provider\":\"$provider\",\"model\":\"$model\",\"input_tokens\":$in_t,\"output_tokens\":$out_t,\"latency_ms\":$latency,\"cost_usd\":$cost,\"status\":\"$status\"},
      {\"event_type\":\"span_end\",\"span_id\":\"$span_id\",\"run_id\":\"$run_id\",\"status\":\"$end_status\",\"ended_at\":\"$NOW\",\"cost_usd\":$cost},
      {\"event_type\":\"run_end\",\"run_id\":\"$run_id\",\"status\":\"$end_status\",\"ended_at\":\"$NOW\",\"total_cost_usd\":$cost,\"total_input_tokens\":$in_t,\"total_output_tokens\":$out_t}
    ]}" > /dev/null

  echo "  ✓ $workflow | $provider/$model | in=${in_t} out=${out_t} | \$$(printf '%8.6f' $cost) | $status | $user" >&2
  echo "$run_id"
}

# Simulate 15 runs (capture first 3 run_ids for outcomes)
RUN1_ID=$(simulate_run "customer-support-chat"  "gpt-4o"           "openai"    1200  450  "success" "user-alice")
RUN2_ID=$(simulate_run "document-summarizer"    "gpt-4o"           "openai"    4500  800  "success" "user-bob")
RUN3_ID=$(simulate_run "code-review-agent"      "gpt-4o"           "openai"    3200  1200 "success" "user-carol")
simulate_run "email-drafter"          "gpt-4o-mini"      "openai"    800   300  "success" "user-alice"   > /dev/null
simulate_run "data-extractor"         "gpt-4o-mini"      "openai"    2100  400  "success" "user-dave"    > /dev/null
simulate_run "sql-generator"          "gpt-4o-mini"      "openai"    1500  600  "success" "user-bob"     > /dev/null
simulate_run "claude-researcher"      "claude-sonnet-4-6" "anthropic" 2800  900  "success" "user-carol"  > /dev/null
simulate_run "content-writer"         "claude-sonnet-4-6" "anthropic" 3500  1400 "success" "user-alice"  > /dev/null
simulate_run "sentiment-analyzer"     "gpt-4o-mini"      "openai"    600   200  "success" "user-eve"     > /dev/null
simulate_run "rag-pipeline"           "gpt-4o"           "openai"    5800  1100 "success" "user-dave"    > /dev/null
simulate_run "translation-agent"      "gpt-4o-mini"      "openai"    1900  700  "success" "user-bob"     > /dev/null
simulate_run "report-generator"       "gpt-4o"           "openai"    6200  2100 "success" "user-carol"   > /dev/null
simulate_run "chatbot-error-test"     "gpt-4o-mini"      "openai"    1100  0    "error"   "user-alice"   > /dev/null
simulate_run "image-description"      "gpt-4o"           "openai"    2300  850  "success" "user-dave"    > /dev/null
simulate_run "policy-checker"         "claude-sonnet-4-6" "anthropic" 1800  600  "success" "user-eve"    > /dev/null

# ── 7. Record Outcomes ────────────────────────────────────────────────────────
sep "Step 7 — Record Outcomes & ROI"

curl -s -X POST "$API/outcomes" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"outcome_type\":\"conversion\",\"success\":true,\"run_id\":\"$RUN1_ID\",\"value_usd\":45.00,\"end_user_id\":\"user-alice\",\"labels\":{\"tier\":\"premium\"}}" > /dev/null
ok "Outcome: customer-support-chat → +\$45 conversion"

curl -s -X POST "$API/outcomes" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"outcome_type\":\"time_saved\",\"success\":true,\"run_id\":\"$RUN2_ID\",\"value_usd\":12.50,\"end_user_id\":\"user-bob\",\"labels\":{\"minutes_saved\":30}}" > /dev/null
ok "Outcome: document-summarizer → +\$12.50 time saved"

curl -s -X POST "$API/outcomes" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"outcome_type\":\"error_prevented\",\"success\":true,\"run_id\":\"$RUN3_ID\",\"value_usd\":200.00,\"end_user_id\":\"user-carol\",\"labels\":{\"severity\":\"high\"}}" > /dev/null
ok "Outcome: code-review-agent → +\$200 error prevented"

# ── 8. Record Evaluation Scores ───────────────────────────────────────────────
sep "Step 8 — Evaluation Scores"

curl -s -X POST "$API/evaluations/scores" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"run_id\":\"$RUN1_ID\",\"metric_name\":\"quality\",\"score\":0.92,\"label\":\"excellent\"}" > /dev/null
ok "Score: customer-support-chat quality=0.92 (excellent)"

curl -s -X POST "$API/evaluations/scores" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"run_id\":\"$RUN2_ID\",\"metric_name\":\"quality\",\"score\":0.78,\"label\":\"good\"}" > /dev/null
ok "Score: document-summarizer quality=0.78 (good)"

curl -s -X POST "$API/evaluations/scores" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"run_id\":\"$RUN3_ID\",\"metric_name\":\"faithfulness\",\"score\":0.88,\"label\":\"good\"}" > /dev/null
ok "Score: code-review-agent faithfulness=0.88 (good)"

# ── 9. Create Alert Rule ──────────────────────────────────────────────────────
sep "Step 9 — Alert Rules"

ALERT=$(curl -s -X POST "$API/alerts/rules" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Error Rate",
    "metric": "error_rate",
    "operator": "gt",
    "threshold": 0.1,
    "window_minutes": 60,
    "email_enabled": false
  }')
ok "Alert: High Error Rate >10% / 60min (id: $(echo $ALERT | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4))"

ALERT2=$(curl -s -X POST "$API/alerts/rules" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Latency P95",
    "metric": "p95_latency",
    "operator": "gt",
    "threshold": 5000,
    "window_minutes": 30,
    "email_enabled": false
  }')
ok "Alert: High Latency P95 >5000ms / 30min (id: $(echo $ALERT2 | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4))"

# ── 10. Reports ───────────────────────────────────────────────────────────────
sep "Step 10 — Reports"

echo
info "Analytics Summary:"
curl -s "$API/analytics/summary" -H "Authorization: Bearer $KEY" | \
  tr ',' '\n' | tr '{}' ' ' | grep -E '"(total|run|cost|error|avg)' | \
  sed 's/^ *//; s/^/    /'

echo
info "Top Workflows by Cost:"
curl -s "$API/analytics/workflows/top?limit=5" -H "Authorization: Bearer $KEY" | \
  grep -o '"workflow_name":"[^"]*"\|"total_cost_usd":[0-9.E-]*\|"run_count":[0-9]*' | \
  paste - - - | sed 's/^/    /'

echo
info "Spend by Model:"
curl -s "$API/analytics/spend-by-model" -H "Authorization: Bearer $KEY" | \
  grep -o '"model":"[^"]*"\|"cost_usd":[0-9.E-]*' | \
  paste - - | sed 's/^/    /'

echo
info "Budget Status:"
curl -s "$API/budgets" -H "Authorization: Bearer $KEY" | \
  grep -o '"scope_type":"[^"]*"\|"period_type":"[^"]*"\|"limit_usd":[0-9.]*\|"spent_usd":[0-9.E-]*' | \
  paste - - - - | sed 's/^/    /'

echo
info "Gateway Stats:"
curl -s "$API/gateway/stats" -H "Authorization: Bearer $KEY" | \
  tr ',' '\n' | tr '{}' ' ' | grep '"' | sed 's/^ *//; s/^/    /'

echo
info "Outcomes Summary:"
curl -s "$API/outcomes/summary" -H "Authorization: Bearer $KEY" | \
  tr ',' '\n' | tr '{}' ' ' | grep '"' | sed 's/^ *//; s/^/    /'

echo
info "Score Summary:"
curl -s "$API/analytics/scores/summary" -H "Authorization: Bearer $KEY" | \
  tr ',' '\n' | tr '{}[]' '    ' | grep '"' | sed 's/^ *//; s/^/    /'

# ── Done ──────────────────────────────────────────────────────────────────────
sep "Complete!"
echo "  Dashboard  →  http://localhost:3000"
echo "  API Docs   →  http://localhost:8000/docs"
echo "  Login      →  admin@runledger.local / runledger"
echo "  API Key    →  $ADMIN_KEY"
echo
echo "  Entities created:"
echo "    • 2 tenant orgs  (Acme Corp, Nova AI)"
echo "    • 2 org admins   (alice@acme.com, carol@nova.ai)"
echo "    • 1 extra workspace (staging)"
echo "    • 3 budgets      (monthly \$500 notify, daily \$25 block, user daily \$5)"
echo "    • 3 gateway aliases (default-gpt4o, cheap-mini, claude-sonnet)"
echo "    • 15 agent runs  (gpt-4o, gpt-4o-mini, claude-sonnet-4-6)"
echo "    • 3 outcome records (\$257.50 total ROI)"
echo "    • 3 evaluation scores"
echo "    • 2 alert rules"
echo
