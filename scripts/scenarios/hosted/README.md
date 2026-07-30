# Hosted-provider scenarios

These scenarios exercise hosted model providers such as OpenAI, Anthropic, and Google through RunLedger's REST API.

They are auto-discovered by `scripts/full_simulate.py` and each scenario creates its own organization and workspace:

- `01_saas_support.py` - high-volume support, cache, budgets, ticket outcomes, CSAT, alert rules.
- `02_ml_research.py` - frontier-vs-local research workloads with dense evaluation scores, compiler/compression/tool filtering, and intelligent routing.
- `03_ecommerce_agents.py` - multi-provider fallback, conversion ROI, fraud review, feature budgets.

RBAC alignment:

- The simulator creates organizations through `/org/tenants` as the platform admin.
- It logs in as each seeded org admin for management actions such as Gateway routes, Alert Rules, Budgets, and API-key minting.
- It uses a minted workspace API key for data-plane traffic such as ingest, outcomes, scores, and gateway completions.
