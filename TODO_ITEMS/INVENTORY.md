# RunLedger Asset Inventory

Last updated: 2026-08-14

Reference catalog of docs, examples, scripts, Postman, and infrastructure assets. Use this to locate existing coverage when auditing delivery surfaces.

---

## Docs (`docs/`)

| File | Covers |
|------|--------|
| `architecture.md` | System architecture overview |
| `deployment.md` | Production deployment guide |
| `backup-restore.md` | Backup and restore procedures |
| `collector.md` | OTEL collector setup |
| `otlp.md` | OTLP ingest guide |
| `openinference.md` | OpenInference integration |
| `litellm.md` | LiteLLM integration |
| `helm.md` | Helm chart deployment |
| `ha.md` | High availability setup |
| `infra-hardening.md` | Infrastructure hardening |
| `upgrade.md` | Version upgrade guide |
| `versioning-policy.md` | Versioning policy |
| `release-checklist.md` | Release checklist |
| `integration-options-mcp.md` | MCP integration options |
| `product-data-alignment.md` | Product/data alignment |
| `demo-script.md` | Demo script |
| `demo-runbook.md` | Demo runbook |
| `demo-asset-bundle.md` | Demo assets |
| `demo-visual-regression.md` | Visual regression testing |
| `administration/email-delivery.md` | Email delivery admin guide |
| `integrations/desktop-agent-setup.md` | Desktop agent integration |

## Examples (`examples/`)

| File | Covers |
|------|--------|
| `01_openai_basic.py` | Basic OpenAI SDK integration |
| `02_openai_multi_turn.py` | Multi-turn conversations |
| `03_langchain_chain.py` | LangChain integration |
| `04_langgraph_agent.py` | LangGraph agent |
| `05_fastapi_service.py` | FastAPI service integration |
| `06_ollama_local.py` | Local Ollama usage |
| `07_analytics_query.py` | Analytics API queries |
| `08_budget_enforcement.py` | Budget enforcement demo |
| `09_economics_query.py` | Economics API queries |
| `10_replay_experiment.py` | Replay experiments |
| `11_ledger_verify.py` | Ledger verification |
| `12_settings.py` | Settings API |
| `13_integrations.py` | Integration examples |
| `14_evaluations.py` | Evaluation API |
| `15_prompts.py` | Prompt management |
| `16_sessions.py` | Session tracking |
| `17_alerts.py` | Alert rules |
| `18_gateway.py` | Gateway usage |
| `19_policy_check.py` | Policy checking |
| `20_anthropic_basic.py` | Anthropic SDK integration |
| `20_tool_registry_ollama.py` | Tool registry with Ollama |
| `21_mcp_example.py` | MCP usage |
| `22_otlp_ingest.py` | OTLP ingest |
| `24_openinference_otel.py` | OpenInference + OTEL |
| `25_outcomes_roi.py` | Outcomes and ROI |
| `27_approvals_workflow.py` | Approval workflows |
| `30_langchain_gateway_otel.py` | LangChain + Gateway + OTEL |
| `31_litellm_basic.py` | LiteLLM basic |
| `32_litellm_proxy.py` | LiteLLM proxy |
| `33_semantic_cache.py` | Semantic cache |
| `34_context_compiler.py` | Context compiler |
| `35_prompt_compression.py` | Prompt compression |
| `36_intelligent_routing.py` | Intelligent routing |
| `37_cognitive_layer.py` | Cognitive layer |
| `38_tool_filtering_skills.py` | Tool filtering |
| `39_flywheel.py` | Optimization flywheel |
| `ts/01_openai_basic.ts` | TypeScript OpenAI |
| `ts/02_multi_turn.ts` | TypeScript multi-turn |
| `ts/03_vercel_ai.ts` | TypeScript Vercel AI |

## Postman (`postman/`)

| File | Notes |
|------|-------|
| `RunLedger.postman_collection.json` | Full API collection |
| `RunLedger.postman_environment.json` | Environment variables |

## Scripts (`scripts/`)

| Path | Covers |
|------|--------|
| `full_simulate.py` | Full platform simulation |
| `generate_postman.py` | Postman collection generator |
| `cleanup.py` | Data cleanup |
| `bench/run_benchmark.py` | Gateway benchmarking |
| `bench/report.py` | Benchmark reporting |
| `streaming/kafka_consumer.py` | Kafka consumer demo |
| `scenarios/hosted/01_saas_support.py` | SaaS support scenario |
| `scenarios/hosted/02_ml_research.py` | ML research scenario |
| `scenarios/hosted/03_ecommerce_agents.py` | E-commerce agents scenario |
| `scenarios/ollama/01-07_*.py` | 7 Ollama-based scenarios |
| `scenarios/labs/agents/lab_01-05_*.py` | 5 agent lab scenarios |
| `localai/bootstrap_runledger_org.py` | LocalAI org bootstrap |
| `localai/generate_agent_traffic.py` | Agent traffic generation |
| `localai/generate_otlp_traffic.py` | OTLP traffic generation |
| `localai/register_all_gateway_routes.py` | Gateway route registration |
| `localai/seed_gateway_routes_all_workspaces.py` | Multi-workspace gateway seed |
| `localai/inject_mcp_configs.py` | MCP config injection |
| `localai/localai_s3_backup.py` | S3 backup script |
| `localai/runledger_auto_init.py` | Auto-initialization |
| `runledger/validate_mcp_connection.py` | MCP connection validation |
| `runledger/mcp_stdio_bridge.py` | MCP stdio bridge |

## Infrastructure (`docker-compose.yml`)

| Service | Profile | Purpose |
|---------|---------|---------|
| `runledger-postgres` | core | Primary database |
| `runledger-redis` | core | Cache, rate limits, budget counters |
| `runledger-api` | core | FastAPI application |
| `runledger-worker` | core | Celery worker |
| `runledger-beat` | core | Celery beat scheduler |
| `runledger-web` | core | Next.js dashboard |
| `runledger-qdrant` | infra | Vector store |
| `runledger-minio` | backup | S3-compatible object storage |
| `runledger-redpanda` | streaming | Kafka-compatible event streaming |
| `runledger-redpanda-console` | streaming | Redpanda management UI |
| `runledger-otel-collector` | observability | OpenTelemetry collector |
| `runledger-embedding-svc` | aux | Text embedding service |
| `runledger-semantic-cache-svc` | aux | Semantic cache service |
| `runledger-mcp-gateway` | aux | MCP gateway |
| `runledger-memory-db` | infra | Letta memory database (pgvector) |
| `runledger-letta` | infra | Letta memory service |
| `runledger-memory-svc` | aux | Memory abstraction layer |
| `runledger-kg-svc` | aux | Knowledge graph (Kuzu) |
| `runledger-skill-registry` | aux | Skill registry |
| `runledger-reranker` | aux | Reranker service |
| `runledger-compression` | aux | Prompt compression |
| `runledger-router` | aux | Intelligent routing |
| `runledger-context-compiler` | aux | Context compilation |
| `runledger-flywheel` | aux | Optimization flywheel |
| `runledger-caddy` | tls-demo | TLS termination proxy |
