"""
Lab 02 - Out-of-band OTLP instrumentation.

This simulates a traced app in LocalAIAgentStack / Langgraph sending OTel spans to
RunLedger without using inline SDK patching.
"""

from __future__ import annotations

import time

from _config import OLLAMA_MODEL, RUNLEDGER_BASE_URL, banner, dashboard_url, require_key
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from runledger_sdk.otel_exporter import RunLedgerOTLPExporter


def main() -> None:
    banner("Lab 02 - Out-of-band OTLP - LocalAIAgentStack / Langgraph")
    key = require_key()

    exporter = RunLedgerOTLPExporter(api_key=key, base_url=RUNLEDGER_BASE_URL)
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("local-ai-agent-stack.langgraph.prototype-agent")

    with tracer.start_as_current_span("agent.run") as agent:
        agent.set_attribute("openinference.span.kind", "AGENT")
        agent.set_attribute("user.id", "dev_tester_1")
        agent.set_attribute("session.id", "sess_lab02")

        with tracer.start_as_current_span("search_docs") as tool:
            tool.set_attribute("openinference.span.kind", "TOOL")
            tool.set_attribute("tool.name", "search_docs")
            tool.set_attribute("tool.description", "Searches internal documentation")
            time.sleep(0.05)

        with tracer.start_as_current_span("chat") as llm:
            llm.set_attribute("openinference.span.kind", "LLM")
            llm.set_attribute("llm.provider", "ollama")
            llm.set_attribute("llm.model_name", OLLAMA_MODEL)
            llm.set_attribute("llm.token_count.prompt", 120)
            llm.set_attribute("llm.token_count.completion", 60)
            llm.set_attribute("llm.token_count.total", 180)
            time.sleep(0.05)

    provider.force_flush()
    provider.shutdown()

    print(f"\nTraces exported to {RUNLEDGER_BASE_URL}/v1/traces")
    print(f"Open {dashboard_url()}/runs and look for the 'agent.run' trace.")


if __name__ == "__main__":
    main()
