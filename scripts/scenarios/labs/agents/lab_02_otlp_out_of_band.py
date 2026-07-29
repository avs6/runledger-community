"""
Lab 02 — Out-of-band OTLP instrumentation.

WHAT THIS IS
────────────
The **AI Development Team** is prototyping an agent that's already instrumented
with OpenTelemetry (the industry standard). Instead of the RunLedger SDK patching
calls *inline*, the app emits OTel spans and a **background exporter** ships them
to RunLedger's OTLP endpoint (`POST /v1/traces`) — "out of band", off the request
path, in a batch thread. Nothing in the hot path waits on RunLedger.

This is how you onboard an app you *didn't* write with the RunLedger SDK: point
its existing OTel tracer at RunLedger. We use `RunLedgerOTLPExporter` (a standard
OTel SpanExporter) so any OpenTelemetry codebase works the same way.

We hand-build an AGENT → LLM → TOOL span tree with OpenInference attributes so
RunLedger records a run, a provider_call (with tokens/model), and a tool_call.

PREREQUISITES
─────────────
  • Workspace API key in agents/.env
  • pip install -r requirements.txt   (installs opentelemetry-sdk)

RUN
───
    python lab_02_otlp_out_of_band.py

THEN VERIFY (dashboard → Runs)
──────────────────────────────
  • A run named "agent.run" with a nested LLM call (model=llama3.2, 180 tokens)
    and a tool call "search_docs".
  • No RunLedger SDK instrumentation was used — this came purely from OTel spans.

Alternative: route through the OTel Collector instead of directly to RunLedger.
The stack already runs one on :4318 (HTTP). Point a standard OTLPSpanExporter at
http://localhost:4318 and the collector forwards to RunLedger. Direct is simpler
for the lab, so that's what we do here.
"""

from __future__ import annotations

import time

from _config import OLLAMA_MODEL, RUNLEDGER_BASE_URL, banner, dashboard_url, require_key
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from runledger_sdk.otel_exporter import RunLedgerOTLPExporter


def main() -> None:
    banner("Lab 02 · Out-of-band OTLP · AI Development Team")
    key = require_key()

    # ── 1. Standard OpenTelemetry setup. The only RunLedger-specific line is the
    #      exporter — everything else is vanilla OTel your app may already have.
    exporter = RunLedgerOTLPExporter(api_key=key, base_url=RUNLEDGER_BASE_URL)
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))  # batched → background thread
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("ai-dev-team.prototype-agent")

    # ── 2. Emit an agent trace. Attributes follow OpenInference conventions so
    #      RunLedger classifies each span (AGENT / LLM / TOOL).
    with tracer.start_as_current_span("agent.run") as agent:
        agent.set_attribute("openinference.span.kind", "AGENT")
        agent.set_attribute("user.id", "dev_tester_1")
        agent.set_attribute("session.id", "sess_lab02")

        # A tool call the agent made.
        with tracer.start_as_current_span("search_docs") as tool:
            tool.set_attribute("openinference.span.kind", "TOOL")
            tool.set_attribute("tool.name", "search_docs")
            tool.set_attribute("tool.description", "Searches internal documentation")
            time.sleep(0.05)

        # The LLM call — this becomes a provider_call with tokens + model in RunLedger.
        with tracer.start_as_current_span("chat") as llm:
            llm.set_attribute("openinference.span.kind", "LLM")
            llm.set_attribute("llm.provider", "ollama")
            llm.set_attribute("llm.model_name", OLLAMA_MODEL)
            llm.set_attribute("llm.token_count.prompt", 120)
            llm.set_attribute("llm.token_count.completion", 60)
            llm.set_attribute("llm.token_count.total", 180)
            time.sleep(0.05)

    # ── 3. Flush the batch exporter so the spans are shipped before we exit.
    provider.force_flush()
    provider.shutdown()

    print(f"\n✓ Traces exported out-of-band to {RUNLEDGER_BASE_URL}/v1/traces")
    print(f"  Open {dashboard_url()}/runs — look for the 'agent.run' trace (~5s to process).")


if __name__ == "__main__":
    main()
