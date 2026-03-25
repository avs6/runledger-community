"""
RunLedger — LangChain / LangGraph + Model Gateway + Observability

Demonstrates two ways to instrument a LangGraph agent and send traces to RunLedger:

  APPROACH A — OTEL Collector (recommended for LangGraph/LangChain)
    LangGraph agent → OpenInference instrumentor → OTEL Collector (localhost:4318)
    → RunLedger /v1/traces (full span tree, token counts, costs)

  APPROACH B — RunLedger SDK (lighter, no collector required)
    LangGraph agent → rl.instrument_graph() + rl.context()
    → RunLedger /ingest/v1/batch (direct HTTP, no extra infra)

Both approaches:
  - Route LLM calls through the RunLedger Model Gateway (/gateway/chat/completions)
    so every call is logged, cost-tracked, PII-scrubbed, and budget-enforced
  - Work with any model the gateway has a route for (GPT-4o, Claude, Gemini, Ollama)

Prerequisites — one-time install:
  pip install runledger-sdk                          # Approach B
  pip install openai langchain langchain-openai langgraph  # both approaches
  pip install openinference-instrumentation-langchain opentelemetry-exporter-otlp-proto-http  # Approach A only

Environment variables:
  RUNLEDGER_API_KEY   — your RunLedger API key (from /admin/bootstrap)
  RUNLEDGER_BASE_URL  — RunLedger API base URL  (default: http://localhost:8000)
  OTEL_ENDPOINT       — OTEL Collector HTTP endpoint (default: http://localhost:4318)

The example does NOT require a real OpenAI key — it calls the RunLedger gateway
which in turn forwards to whichever provider you have configured.  If no gateway
route is active the call will return a 400/404; set OPENAI_API_KEY in .env and
re-run the seed script to create live routes.
"""

from __future__ import annotations

import os
import textwrap
import time
from typing import Annotated, TypedDict

# ── Config ────────────────────────────────────────────────────────────────────

RUNLEDGER_API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")
RUNLEDGER_BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000")
OTEL_ENDPOINT = os.environ.get("OTEL_ENDPOINT", "http://localhost:4318")

# The gateway endpoint is OpenAI-API-compatible — drop it in as the base_url
GATEWAY_BASE_URL = f"{RUNLEDGER_BASE_URL}/gateway"

if not RUNLEDGER_API_KEY:
    raise SystemExit(
        "Set RUNLEDGER_API_KEY before running this example.\n"
        "  export RUNLEDGER_API_KEY=rl_live_...\n"
        "Get your key from: POST http://localhost:8000/admin/bootstrap"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# APPROACH A — OpenInference + OTEL Collector
# ═══════════════════════════════════════════════════════════════════════════════

def run_with_otel_collector(query: str) -> str:
    """
    Run a LangGraph ReAct agent with full OpenTelemetry tracing.

    Traces flow:  LangChain/LangGraph → OpenInference instrumentor
                  → OTEL Collector (localhost:4318)
                  → RunLedger /v1/traces

    This approach captures the full span tree: agent loop, LLM calls, tool calls,
    retriever calls — all with token counts, latency, and model metadata.

    Install deps:
        pip install openinference-instrumentation-langchain \\
                    opentelemetry-sdk \\
                    opentelemetry-exporter-otlp-proto-http \\
                    langchain langchain-openai langgraph
    """
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as e:
        print(f"\n[APPROACH A] Missing dependency: {e}")
        print("Install: pip install openinference-instrumentation-langchain "
              "opentelemetry-sdk opentelemetry-exporter-otlp-proto-http")
        return ""

    try:
        from langchain_core.tools import tool
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent
    except ImportError as e:
        print(f"\n[APPROACH A] Missing dependency: {e}")
        print("Install: pip install langchain langchain-openai langgraph")
        return ""

    print("\n" + "═" * 60)
    print("APPROACH A — OpenInference → OTEL Collector → RunLedger")
    print("═" * 60)

    # ── 1. Configure OpenTelemetry SDK ────────────────────────────────────────
    resource = Resource.create({
        "service.name": "runledger-demo-agent",
        "service.version": "1.0.0",
        "deployment.environment": "demo",
    })

    # Export to the local OTEL Collector which forwards to RunLedger
    exporter = OTLPSpanExporter(
        endpoint=f"{OTEL_ENDPOINT}/v1/traces",
        headers={"Authorization": f"Bearer {RUNLEDGER_API_KEY}"},
    )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # ── 2. Instrument LangChain / LangGraph ───────────────────────────────────
    # One call — instruments LangChain chains, LLMs, tools, and LangGraph nodes
    LangChainInstrumentor().instrument()
    print(f"  ✓ LangChain instrumented → traces → {OTEL_ENDPOINT}")

    # ── 3. Build the LangGraph agent ──────────────────────────────────────────
    # Point the LLM at the RunLedger Model Gateway.
    # The gateway is OpenAI-API-compatible, so ChatOpenAI works unchanged.
    # The gateway will:
    #   - Route to the best available model (cost-optimized, quality-first, etc.)
    #   - Log every request with token counts + cost
    #   - Enforce budgets and per-user rate limits
    #   - Scrub PII from prompts if the route has pii_redaction_enabled=True
    llm = ChatOpenAI(
        model="gpt-4o-mini",          # gateway resolves this to the active route
        base_url=GATEWAY_BASE_URL,
        api_key=RUNLEDGER_API_KEY,    # RunLedger API key is used as the gateway auth
        temperature=0,
    )

    @tool
    def calculate_cost(tokens: int, model: str = "gpt-4o-mini") -> str:
        """Calculate the estimated USD cost for a given token count and model."""
        rates = {
            "gpt-4o": (2.50, 10.00),
            "gpt-4o-mini": (0.15, 0.60),
            "claude-sonnet-4-6": (3.00, 15.00),
            "claude-haiku-4-5": (0.80, 4.00),
        }
        in_r, out_r = rates.get(model, (1.00, 3.00))
        # Assume 80/20 input/output split
        cost = (tokens * 0.8 / 1_000_000 * in_r) + (tokens * 0.2 / 1_000_000 * out_r)
        return f"Estimated cost for {tokens:,} tokens on {model}: ${cost:.4f}"

    @tool
    def get_model_info(model: str) -> str:
        """Get information about a model's capabilities and pricing tier."""
        info = {
            "gpt-4o": "OpenAI flagship — best quality, $2.50/$10.00 per 1M tokens",
            "gpt-4o-mini": "OpenAI fast + cheap — $0.15/$0.60 per 1M tokens",
            "claude-sonnet-4-6": "Anthropic Sonnet — great coding + reasoning, $3/$15 per 1M",
            "claude-haiku-4-5": "Anthropic budget — fastest Anthropic model, $0.80/$4 per 1M",
            "gemini-2.0-flash": "Google Gemini Flash — multimodal, $0.075/$0.30 per 1M",
        }
        return info.get(model, f"Unknown model: {model}. Available: {', '.join(info)}")

    agent = create_react_agent(llm, tools=[calculate_cost, get_model_info])
    print(f"  ✓ LangGraph ReAct agent ready → gateway: {GATEWAY_BASE_URL}")

    # ── 4. Run the agent ──────────────────────────────────────────────────────
    print(f"\n  Query: {query}\n")
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    answer = result["messages"][-1].content

    print(f"\n  Answer: {textwrap.fill(answer, 70, subsequent_indent='  ')}")

    # ── 5. Flush spans to the collector ───────────────────────────────────────
    provider.force_flush(timeout_millis=5000)
    print(f"\n  ✓ Spans flushed → OTEL Collector → RunLedger")
    print(f"  View traces: {RUNLEDGER_BASE_URL.replace(':8000', ':3000')}/runs")

    return answer


# ═══════════════════════════════════════════════════════════════════════════════
# APPROACH B — RunLedger SDK (no OTEL collector needed)
# ═══════════════════════════════════════════════════════════════════════════════

def run_with_runledger_sdk(query: str) -> str:
    """
    Run a LangGraph agent instrumented directly with the RunLedger SDK.

    Traces flow:  LangGraph → rl.instrument_graph() hooks
                  → RunLedger /ingest/v1/batch (direct HTTP)

    This approach requires no extra infrastructure — just the SDK and your
    RunLedger API key.  It captures: run start/end, span tree, LLM calls,
    tool calls, scores, and outcome signals.

    Install deps:
        pip install runledger-sdk langchain langchain-openai langgraph
    """
    try:
        import runledger as rl
    except ImportError:
        print("\n[APPROACH B] runledger-sdk not installed.")
        print("Install: pip install runledger-sdk")
        return ""

    try:
        from langchain_core.tools import tool
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent
    except ImportError as e:
        print(f"\n[APPROACH B] Missing dependency: {e}")
        print("Install: pip install langchain langchain-openai langgraph")
        return ""

    print("\n" + "═" * 60)
    print("APPROACH B — RunLedger SDK (direct, no OTEL collector)")
    print("═" * 60)

    # ── 1. Initialise RunLedger ───────────────────────────────────────────────
    client = rl.RunLedger(
        api_key=RUNLEDGER_API_KEY,
        base_url=RUNLEDGER_BASE_URL,
        # Enforce budgets before each LLM call (adds ~5ms via Redis)
        budget_check=True,
    )

    # ── 2. Build the LangGraph agent (gateway-backed) ─────────────────────────
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        base_url=GATEWAY_BASE_URL,
        api_key=RUNLEDGER_API_KEY,
        temperature=0,
    )

    @tool
    def estimate_monthly_spend(daily_tokens: int, model: str = "gpt-4o-mini") -> str:
        """Estimate monthly spend given average daily token usage."""
        rates = {"gpt-4o-mini": 0.375, "gpt-4o": 6.25, "claude-sonnet-4-6": 9.0}
        rate = rates.get(model, 2.0)
        monthly = daily_tokens / 1_000_000 * rate * 30
        return f"~${monthly:.2f}/month for {daily_tokens:,} tokens/day on {model}"

    @tool
    def get_cost_saving_tips() -> str:
        """Return a list of FinOps tips for reducing LLM costs."""
        return (
            "1. Use prompt caching for repeated system prompts (saves 50-90% on cached tokens)\n"
            "2. Route to gpt-4o-mini / claude-haiku for classification/extraction tasks\n"
            "3. Set daily_cost_limit_usd on gateway routes to prevent runaway spend\n"
            "4. Use budget_aware routing policy to auto-fallback when budget is low\n"
            "5. Review /analytics/economics to find your highest cost agent workflows"
        )

    agent = create_react_agent(llm, tools=[estimate_monthly_spend, get_cost_saving_tips])

    # ── 3. Instrument the graph ───────────────────────────────────────────────
    # instrument_graph wraps the agent's invoke/stream methods and automatically
    # creates RunLedger run + span events for every node execution.
    instrumented_agent = client.instrument_graph(agent)
    print(f"  ✓ RunLedger SDK instrumented → {RUNLEDGER_BASE_URL}")
    print(f"  ✓ LangGraph agent ready → gateway: {GATEWAY_BASE_URL}")

    # ── 4. Run inside a RunLedger context ────────────────────────────────────
    # rl.context() tags all events with session_id, user_id, and custom metadata
    with client.context(
        session_id="demo-session-001",
        user_id="demo-user",
        metadata={"demo": True, "approach": "sdk", "query_topic": "finops"},
    ):
        print(f"\n  Query: {query}\n")
        result = instrumented_agent.invoke({"messages": [{"role": "user", "content": query}]})
        answer = result["messages"][-1].content

    print(f"\n  Answer: {textwrap.fill(answer, 70, subsequent_indent='  ')}")

    # ── 5. Flush buffered events ──────────────────────────────────────────────
    client.flush()
    print(f"\n  ✓ Events flushed → RunLedger")
    print(f"  View runs:    {RUNLEDGER_BASE_URL.replace(':8000', ':3000')}/runs")
    print(f"  View session: {RUNLEDGER_BASE_URL.replace(':8000', ':3000')}/sessions/demo-session-001")

    return answer


# ═══════════════════════════════════════════════════════════════════════════════
# APPROACH C — Both simultaneously (LangSmith + RunLedger side-by-side)
# ═══════════════════════════════════════════════════════════════════════════════

def run_with_both_collectors(query: str) -> str:
    """
    Run with both LangSmith and RunLedger receiving the same traces.

    Useful during migration: keep LangSmith running while evaluating RunLedger.
    Both receive the identical OpenInference span tree — no code duplication.

    Install deps:
        pip install openinference-instrumentation-langchain \\
                    opentelemetry-sdk \\
                    opentelemetry-exporter-otlp-proto-http \\
                    langchain langchain-openai langgraph

    Additional env:
        LANGCHAIN_API_KEY  — your LangSmith API key
        LANGCHAIN_ENDPOINT — your LangSmith OTEL endpoint
    """
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as e:
        print(f"\n[APPROACH C] Missing dependency: {e}")
        return ""

    try:
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent
    except ImportError as e:
        print(f"\n[APPROACH C] Missing dependency: {e}")
        return ""

    print("\n" + "═" * 60)
    print("APPROACH C — Dual export: LangSmith + RunLedger simultaneously")
    print("═" * 60)

    resource = Resource.create({"service.name": "runledger-dual-export-demo"})
    provider = TracerProvider(resource=resource)

    # Export 1 → RunLedger (via local OTEL Collector)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
        endpoint=f"{OTEL_ENDPOINT}/v1/traces",
        headers={"Authorization": f"Bearer {RUNLEDGER_API_KEY}"},
    )))

    # Export 2 → LangSmith (if configured)
    langsmith_key = os.environ.get("LANGCHAIN_API_KEY", "")
    langsmith_endpoint = os.environ.get(
        "LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com/otel"
    )
    if langsmith_key:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
            endpoint=f"{langsmith_endpoint}/v1/traces",
            headers={"x-api-key": langsmith_key},
        )))
        print(f"  ✓ LangSmith export enabled → {langsmith_endpoint}")
    else:
        print("  ℹ  LANGCHAIN_API_KEY not set — LangSmith export skipped")

    trace.set_tracer_provider(provider)
    LangChainInstrumentor().instrument()

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        base_url=GATEWAY_BASE_URL,
        api_key=RUNLEDGER_API_KEY,
        temperature=0,
    )

    from langchain_core.tools import tool  # noqa: PLC0415

    @tool
    def compare_providers(task: str) -> str:
        """Compare which AI provider is best for a given task type."""
        recommendations = {
            "classification": "gpt-4o-mini or claude-haiku-4-5 — fast and cheap",
            "coding": "claude-sonnet-4-6 — best code quality",
            "summarization": "gpt-4o-mini — great quality/cost ratio",
            "reasoning": "gpt-4o or claude-sonnet-4-6 — both excellent",
            "extraction": "gpt-4o-mini with structured outputs",
        }
        for key, rec in recommendations.items():
            if key in task.lower():
                return f"For {task}: {rec}"
        return f"For {task}: evaluate with RunLedger A/B routing (canary policy)"

    agent = create_react_agent(llm, tools=[compare_providers])
    print(f"  ✓ Dual-export agent ready")

    print(f"\n  Query: {query}\n")
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    answer = result["messages"][-1].content

    print(f"\n  Answer: {textwrap.fill(answer, 70, subsequent_indent='  ')}")

    provider.force_flush(timeout_millis=5000)
    print(f"\n  ✓ Traces flushed to all configured exporters")
    return answer


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LangGraph + RunLedger gateway + observability demo")
    parser.add_argument(
        "--approach",
        choices=["otel", "sdk", "both", "all"],
        default="sdk",
        help=(
            "otel  — OTEL Collector approach (requires collector running on localhost:4318)\n"
            "sdk   — RunLedger SDK approach (no collector needed)\n"
            "both  — dual export to LangSmith + RunLedger\n"
            "all   — run all three approaches in sequence"
        ),
    )
    parser.add_argument(
        "--query",
        default="I'm running 500,000 tokens per day on gpt-4o. What would my monthly cost be, and what are the best ways to reduce it?",
        help="Question to ask the agent",
    )
    args = parser.parse_args()

    print(f"\nRunLedger Demo — LangGraph + Model Gateway + Observability")
    print(f"  RunLedger base: {RUNLEDGER_BASE_URL}")
    print(f"  Gateway:        {GATEWAY_BASE_URL}")
    print(f"  OTEL endpoint:  {OTEL_ENDPOINT}")

    if args.approach in ("sdk", "all"):
        run_with_runledger_sdk(args.query)
        time.sleep(1)

    if args.approach in ("otel", "all"):
        run_with_otel_collector(args.query)
        time.sleep(1)

    if args.approach in ("both", "all"):
        run_with_both_collectors(
            "Which AI provider should I use for document classification tasks?"
        )

    print("\n" + "═" * 60)
    print("Done! Check your RunLedger dashboard:")
    print(f"  Runs:     {RUNLEDGER_BASE_URL.replace(':8000', ':3000')}/runs")
    print(f"  Sessions: {RUNLEDGER_BASE_URL.replace(':8000', ':3000')}/sessions")
    print(f"  Gateway:  {RUNLEDGER_BASE_URL.replace(':8000', ':3000')}/settings  (Model Gateway tab)")
    print(f"  API docs: {RUNLEDGER_BASE_URL}/reference")
    print("═" * 60)
