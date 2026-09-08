# Ollama scenarios

These scenarios show local-model FinOps: Ollama traffic is assigned internal pricing from `scripts/configs/pricing.yaml`, so local inference still appears in cost, budget, and ROI views.

They are auto-discovered by `run_demo.py full-simulate`:

- `01_coding_assistant.py` — local coding assistant with GPU-spend budgets, compiler/tool filtering/skill injection, intelligent routing, and bug-resolved outcomes.
- `02_local_rag.py` — local RAG with generation-vs-embedding cost split.
- `03_reasoning_agent.py` — output-heavy reasoning workloads comparing 14B and 8B models.
- `04_chat_support.py` — dense HelpDesk Local demo with expanded Ollama model mix, rich agent/tool/outcome metadata, OTLP trace ingestion, prompt versions, eval dataset, and experiment records.
- `05_guardrails.py` — custom guardrails, built-in content filters, PII detection, prompt injection guard, partner integrations, test playground, and regression testing.
- `06_intelligence.py` — anomaly detection, cost/token forecasting, Top-K analysis, pattern recognition, complexity scoring, adaptive alerts, and ML dashboard.
- `07_advanced_budgets.py` — budget tiers, model-specific budgets with wildcards, temporary overrides with auto-expiry, throttle/fallback enforcement, and billing summary.

Requirements:

- Ollama should be reachable from Docker at `http://host.docker.internal:11434/v1` for live gateway tests.
- Local models should exist in the pricing catalog, otherwise runs ingest but cost remains zero.

RBAC alignment:

- Scenario setup uses a dashboard org-admin session for management actions.
- Agent/data-plane traffic uses the workspace API key minted by that session.
