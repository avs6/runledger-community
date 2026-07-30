# Ollama scenarios

These scenarios show local-model FinOps: Ollama traffic is assigned internal pricing from `scripts/pricing.yaml`, so local inference still appears in cost, budget, and ROI views.

They are auto-discovered by `scripts/full_simulate.py`:

- `01_coding_assistant.py` - local coding assistant with GPU-spend budgets, compiler/tool filtering/skill injection, intelligent routing, and bug-resolved outcomes.
- `02_local_rag.py` - local RAG with generation-vs-embedding cost split.
- `03_reasoning_agent.py` - output-heavy reasoning workloads comparing 14B and 8B models.
- `04_chat_support.py` - local support bot comparable to the hosted support scenario.

Requirements:

- Ollama should be reachable from Docker at `http://host.docker.internal:11434/v1` for live gateway tests.
- Local models should exist in the pricing catalog, otherwise runs ingest but cost remains zero.

RBAC alignment:

- Scenario setup uses a dashboard org-admin session for management actions.
- Agent/data-plane traffic uses the workspace API key minted by that session.
