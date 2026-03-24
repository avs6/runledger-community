"""
Example 24 — OpenInference + OTel → RunLedger
==============================================
Expected cost: ~$0.0010 per call (instrumented via OTel, not RunLedger SDK)

Demonstrates:
- Using openinference-instrumentation-openai with a standard OTel TracerProvider
- Attaching RunLedgerOTLPExporter as an additional export destination
- Zero-code-change integration: existing OTel pipelines ship traces to RunLedger

Prerequisites:
    pip install opentelemetry-sdk openinference-instrumentation-openai
    export RUNLEDGER_API_KEY=rl_live_...
    export OPENAI_API_KEY=sk-...
"""

from __future__ import annotations

import os

BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")


def main() -> None:
    print("=== RunLedger OpenInference/OTel Export Example ===\n")

    # 1. Set up a standard OTel TracerProvider
    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except ImportError:
        print("ERROR: opentelemetry-sdk not installed.")
        print("  pip install opentelemetry-sdk")
        return

    provider = TracerProvider()

    # Optional: also print spans locally for debugging
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # 2. Attach RunLedger as a second export destination — one line
    from runledger_sdk.otel_exporter import RunLedgerOTLPExporter

    rl_exporter = RunLedgerOTLPExporter(api_key=API_KEY, base_url=BASE_URL)
    provider.add_span_processor(BatchSpanProcessor(rl_exporter))
    print("✓ RunLedger exporter attached to TracerProvider")

    # 3. Instrument OpenAI with OpenInference
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor
        OpenAIInstrumentor().instrument(tracer_provider=provider)
        print("✓ OpenAI instrumented via OpenInference")
    except ImportError:
        print("WARNING: openinference-instrumentation-openai not installed.")
        print("  pip install openinference-instrumentation-openai")
        print("  Falling back to manual span example…")
        _manual_span_example(provider)
        return

    # 4. Make some OpenAI calls — they're automatically traced
    import openai  # type: ignore[import-untyped]

    openai_client = openai.OpenAI()

    prompts = [
        "What is the FinOps framework?",
        "Explain token-based billing in one sentence.",
    ]

    print("\nSending instrumented OpenAI calls…")
    for prompt in prompts:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
        )
        content = response.choices[0].message.content or ""
        print(f"  Q: {prompt[:50]}")
        print(f"  A: {content[:80]}…\n")

    # 5. Flush all pending spans to RunLedger
    provider.force_flush(timeout_millis=10_000)
    print("✓ Spans flushed to RunLedger")
    print(f"\nView runs at: {BASE_URL.replace('localhost:8000', 'localhost:3000')}/runs")


def _manual_span_example(provider: object) -> None:
    """Fallback: create a manual span to demonstrate the exporter."""
    try:
        import opentelemetry.trace as trace_api
        from opentelemetry import trace

        trace.set_tracer_provider(provider)  # type: ignore[arg-type]
        tracer = trace.get_tracer("runledger-example")

        with tracer.start_as_current_span("example-llm-call") as span:
            span.set_attribute("openinference.span.kind", "LLM")
            span.set_attribute("llm.model_name", "gpt-4o-mini")
            span.set_attribute("llm.token_count.prompt", 15)
            span.set_attribute("llm.token_count.completion", 42)
            span.set_attribute("llm.token_count.total", 57)
            span.set_attribute("session.id", "example-session-01")
            span.set_attribute("user.id", "example-user-01")

        provider.force_flush(timeout_millis=5_000)  # type: ignore[union-attr]
        print("✓ Manual example span sent to RunLedger")
    except Exception as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
