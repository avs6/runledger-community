"""
RunLedger SDK client.

OpenAI instrumentation: Phase 2.
LangChain/LangGraph instrumentation: Phase 3.
"""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Any

import structlog

from runledger_sdk.context import RunLedgerContext, get_context_snapshot
from runledger_sdk.transport import SyncTransport, Transport

log = structlog.get_logger()

# Propagation header names
_HEADER_RUN_ID = "X-RunLedger-Run-Id"
_HEADER_END_USER_ID = "X-RunLedger-End-User-Id"
_HEADER_SESSION_ID = "X-RunLedger-Session-Id"
_HEADER_FEATURE_TAG = "X-RunLedger-Feature-Tag"
_HEADER_DEPLOYMENT_VERSION = "X-RunLedger-Deployment-Version"


class PrivacyMode:
    """Controls how much payload data is captured and transmitted."""

    METADATA_ONLY = "metadata_only"  # default: tokens, model, latency only
    ERRORS_ONLY = "errors_only"  # metadata + payload captured on errors
    SAMPLED = "sampled"  # metadata + payload on N% of calls
    FULL = "full"  # capture everything (explicit opt-in)


class RunLedger:
    """
    Main RunLedger client.

    Sync usage (OpenAI patch)::

        from runledger_sdk import RunLedger

        rl = RunLedger(api_key="rl_live_...")
        rl.instrument()

        import openai
        client = openai.OpenAI()

        with rl.context(end_user_id="u_123", feature_tag="support-chat"):
            resp = client.chat.completions.create(model="gpt-4o", messages=[...])

    LangChain usage::

        handler = rl.callback_handler()
        chain.invoke({...}, config={"callbacks": [handler]})

    LangGraph usage::

        from runledger_sdk.langgraph import instrument_graph
        graph = instrument_graph(graph, rl._get_sync_transport())

    Async usage::

        rl = RunLedger(api_key="rl_live_...")
        rl.instrument()

        async with rl.context(end_user_id="u_123"):
            resp = await async_client.chat.completions.create(...)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.runledger.io",
        privacy_mode: str = PrivacyMode.METADATA_ONLY,
        local: bool = False,
        budget_check: bool = False,
        tool_enforcement: bool = False,
    ) -> None:
        # Resolve base_url + api_key from env if not provided
        self.base_url = os.getenv("RUNLEDGER_BASE_URL", base_url)

        if api_key is None:
            api_key = os.getenv("RUNLEDGER_API_KEY")

        self.api_key = api_key

        # local means "print only" — ONLY when explicitly requested
        env_local = os.getenv("RUNLEDGER_LOCAL", "").lower() in ("1", "true", "yes")
        self.local = bool(local or env_local)

        self.privacy_mode = privacy_mode
        self.budget_check = budget_check
        self.tool_enforcement = tool_enforcement

        # If not local, require a key
        if not self.local and not self.api_key:
            raise ValueError("RUNLEDGER_API_KEY is required unless local=True")

        self._sync_transport: SyncTransport | None = None
        self._async_transport: Transport | None = None
        self._instrumented = False

    # ── Transport helpers ─────────────────────────────────────────────────────

    def _get_sync_transport(self) -> SyncTransport:
        if self._sync_transport is None:
            self._sync_transport = SyncTransport(
                api_key=self.api_key,
                base_url=self.base_url,
                local=self.local,
                budget_check=self.budget_check,
                tool_enforcement=self.tool_enforcement,
            )
        return self._sync_transport

    def _get_async_transport(self) -> Transport:
        if self._async_transport is None:
            self._async_transport = Transport(
                api_key=self.api_key,
                base_url=self.base_url,
                local=self.local,
            )
            self._async_transport.start()
        return self._async_transport

    # ── Public API ────────────────────────────────────────────────────────────

    def instrument(self) -> None:
        """
        Monkey-patches OpenAI clients so every ``chat.completions.create``
        call is automatically captured.

        Uses a background-thread transport that works from both sync and async
        call sites.  Safe to call multiple times (idempotent).
        """
        if self._instrumented:
            return

        from runledger_sdk.openai import instrument_openai  # noqa: PLC0415

        instrument_openai(self._get_sync_transport())
        self._instrumented = True

    def instrument_anthropic(self) -> None:
        """
        Monkey-patches Anthropic clients so every ``messages.create`` call is
        automatically captured. Requires ``anthropic`` package installed.

        Safe to call multiple times (idempotent).
        """
        from runledger_sdk.anthropic import instrument_anthropic  # noqa: PLC0415

        instrument_anthropic(self._get_sync_transport())

    def instrument_gemini(self) -> None:
        """
        Monkey-patches Google Gemini ``client.models.generate_content`` (sync + async).
        Requires ``google-genai`` package installed (``pip install google-genai``).

        Safe to call multiple times (idempotent).
        """
        from runledger_sdk.gemini import instrument_gemini  # noqa: PLC0415

        instrument_gemini(self._get_sync_transport())

    def instrument_mistral(self) -> None:
        """
        Monkey-patches Mistral ``client.chat.complete`` (sync + async).
        Requires ``mistralai`` package installed (``pip install mistralai``).

        Safe to call multiple times (idempotent).
        """
        from runledger_sdk.mistral import instrument_mistral  # noqa: PLC0415

        instrument_mistral(self._get_sync_transport())

    def instrument_cohere(self) -> None:
        """
        Monkey-patches Cohere ``ClientV2.chat`` (sync + async).
        Requires ``cohere`` package installed (``pip install cohere``).

        Safe to call multiple times (idempotent).
        """
        from runledger_sdk.cohere import instrument_cohere  # noqa: PLC0415

        instrument_cohere(self._get_sync_transport())

    def instrument_mcp(self, session: object) -> None:
        """
        Patch an ``mcp.ClientSession`` so every ``call_tool`` invocation is
        captured as a ``tool_call`` event.

        Parameters
        ----------
        session:
            An initialised ``mcp.ClientSession`` instance.
        """
        from runledger_sdk.mcp import instrument_mcp_session  # noqa: PLC0415

        instrument_mcp_session(session, self._get_sync_transport())

    def instrument_otel(self, tracer_provider: object) -> None:
        """
        Attach a :class:`~runledger_sdk.otel_exporter.RunLedgerOTLPExporter` to
        an existing ``opentelemetry.sdk.trace.TracerProvider``.

        This is the recommended integration for codebases already using
        ``openinference-instrumentation-*`` or other OTel instrumentors —
        add RunLedger as an additional export destination without changing
        anything else.

        Parameters
        ----------
        tracer_provider:
            An initialised ``opentelemetry.sdk.trace.TracerProvider``.

        Example::

            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from openinference.instrumentation.openai import OpenAIInstrumentor

            provider = TracerProvider()
            OpenAIInstrumentor().instrument(tracer_provider=provider)

            rl = RunLedger(api_key="rl_live_...")
            rl.instrument_otel(provider)   # RunLedger now receives all OTel spans
        """
        from runledger_sdk.otel_exporter import RunLedgerOTLPExporter  # noqa: PLC0415

        try:
            from opentelemetry.sdk.trace.export import (
                BatchSpanProcessor,  # noqa: PLC0415
            )
        except ImportError as exc:
            raise ImportError(
                "opentelemetry-sdk is required. Install with: pip install opentelemetry-sdk"
            ) from exc

        exporter = RunLedgerOTLPExporter(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))  # type: ignore[attr-defined]

    def callback_handler(self, *, track_llm_cost: bool = True) -> object:
        """
        Return a ``RunLedgerCallbackHandler`` for use with LangChain chains
        and LangGraph graphs.

        Parameters
        ----------
        track_llm_cost:
            If False, skip ``provider_call`` events from ``on_llm_end``
            (use when ``rl.instrument()`` is also active to avoid duplicates).

        Example::

            handler = rl.callback_handler()
            chain.invoke({...}, config={"callbacks": [handler]})
        """
        from runledger_sdk.langchain import RunLedgerCallbackHandler  # noqa: PLC0415

        return RunLedgerCallbackHandler(
            self._get_sync_transport(),
            track_llm_cost=track_llm_cost,
        )

    def context(
        self,
        *,
        run_id: str | None = None,
        end_user_id: str | None = None,
        session_id: str | None = None,
        feature_tag: str | None = None,
        deployment_version: str | None = None,
    ) -> RunLedgerContext:
        """
        Context manager that attaches user/session metadata to all runs
        within scope.  Supports both ``with`` and ``async with``.

        Returns the effective ``run_id`` on enter::

            with rl.context(end_user_id="u_123") as run_id:
                ...  # run_id is the UUID for this run

        Nested contexts inherit and can selectively override parent values.
        """
        return RunLedgerContext(
            run_id=run_id,
            end_user_id=end_user_id,
            session_id=session_id,
            feature_tag=feature_tag,
            deployment_version=deployment_version,
        )

    # ── Context propagation ───────────────────────────────────────────────────

    def propagation_headers(self) -> dict[str, str]:
        """
        Return HTTP headers that carry the current RunLedger context.

        Use this to propagate run context across service boundaries::

            headers = rl.propagation_headers()
            httpx.get("http://other-service/...", headers=headers)

        On the receiving service, restore context with ``from_headers()``.
        """
        ctx = get_context_snapshot()
        headers: dict[str, str] = {}

        if ctx.get("run_id"):
            headers[_HEADER_RUN_ID] = ctx["run_id"]  # type: ignore[assignment]
        if ctx.get("end_user_id"):
            headers[_HEADER_END_USER_ID] = ctx["end_user_id"]  # type: ignore[assignment]
        if ctx.get("session_id"):
            headers[_HEADER_SESSION_ID] = ctx["session_id"]  # type: ignore[assignment]
        if ctx.get("feature_tag"):
            headers[_HEADER_FEATURE_TAG] = ctx["feature_tag"]  # type: ignore[assignment]
        if ctx.get("deployment_version"):
            headers[_HEADER_DEPLOYMENT_VERSION] = ctx["deployment_version"]  # type: ignore[assignment]

        return headers

    @staticmethod
    def from_headers(headers: dict[str, str]) -> RunLedgerContext:
        """
        Restore RunLedger context from incoming HTTP headers.

        Use on the receiving end of a cross-service call::

            ctx = RunLedger.from_headers(dict(request.headers))
            with ctx:
                # context is now set; all instrumentation will use the
                # propagated run_id and metadata
                ...
        """
        # httpx / starlette headers are case-insensitive; normalise to lower
        lowered = {k.lower(): v for k, v in headers.items()}

        return RunLedgerContext(
            run_id=lowered.get(_HEADER_RUN_ID.lower()),
            end_user_id=lowered.get(_HEADER_END_USER_ID.lower()),
            session_id=lowered.get(_HEADER_SESSION_ID.lower()),
            feature_tag=lowered.get(_HEADER_FEATURE_TAG.lower()),
            deployment_version=lowered.get(_HEADER_DEPLOYMENT_VERSION.lower()),
        )

    # ── Quality scores ────────────────────────────────────────────────────────

    def score(
        self,
        name: str,
        value: float,
        *,
        run_id: str | None = None,
        span_id: str | None = None,
        label: str | None = None,
        source: str = "human",
        confidence: float | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        """
        Submit a quality score for a run or span.

        Scores are posted synchronously and directly (not via the event queue).
        Failures are logged as warnings — scoring must never break application flow.

        Parameters
        ----------
        name:
            Score dimension name (e.g. "relevance", "accuracy", "helpfulness").
        value:
            Numeric score, 0–100 scale.
        run_id:
            Optional UUID of the run being scored. Defaults to current context run_id.
        span_id:
            Optional UUID of the span being scored.
        label:
            Human-readable label (e.g. "good", "bad", "pass", "fail").
        source:
            Scorer type: "human", "llm", "rule", or "telemetry".
        confidence:
            Confidence in the score, 0–1. Optional.
        evidence:
            Arbitrary JSON evidence dict.
        """
        if self.local:
            log.info("score_local", name=name, value=value, run_id=run_id)
            return

        # Fall back to current context run_id if not explicitly provided
        if run_id is None:
            ctx = get_context_snapshot()
            run_id = ctx.get("run_id")

        payload: dict[str, Any] = {
            "name": name,
            "value": value,
            "source": source,
        }
        if run_id is not None:
            payload["run_id"] = str(run_id)
        if span_id is not None:
            payload["span_id"] = str(span_id)
        if label is not None:
            payload["label"] = label
        if confidence is not None:
            payload["confidence"] = confidence
        if evidence is not None:
            payload["evidence"] = evidence

        try:
            import httpx  # noqa: PLC0415

            resp = httpx.post(
                f"{self.base_url}/evaluations/scores",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5.0,
            )
            resp.raise_for_status()
        except Exception as exc:
            log.warning("score_post_failed", name=name, error=str(exc))

    # ── Business outcomes ─────────────────────────────────────────────────────

    def outcome(
        self,
        outcome_type: str,
        success: bool,
        *,
        run_id: str | None = None,
        session_id: str | None = None,
        end_user_id: str | None = None,
        value_usd: float | None = None,
        labels: dict[str, Any] | None = None,
    ) -> None:
        """
        Record a business outcome linked to an agent run or session.

        Outcomes are posted synchronously and directly (not via the event queue).
        Failures are logged as warnings — outcome tracking must never break flow.

        Parameters
        ----------
        outcome_type:
            Business outcome category (e.g. "checkout_completed", "lead_qualified").
        success:
            Whether the outcome was achieved successfully.
        run_id:
            Optional UUID of the run being evaluated. Defaults to current context.
        session_id:
            Optional session identifier.
        end_user_id:
            Optional end-user identifier.
        value_usd:
            Optional business value of the outcome in USD.
        labels:
            Arbitrary JSON labels for grouping / filtering.
        """
        if self.local:
            log.info(
                "outcome_local",
                outcome_type=outcome_type,
                success=success,
                run_id=run_id,
            )
            return

        # Fall back to current context run_id if not explicitly provided
        if run_id is None:
            ctx = get_context_snapshot()
            run_id = ctx.get("run_id")
        if session_id is None:
            ctx = get_context_snapshot()
            session_id = ctx.get("session_id")
        if end_user_id is None:
            ctx = get_context_snapshot()
            end_user_id = ctx.get("end_user_id")

        payload: dict[str, Any] = {
            "outcome_type": outcome_type,
            "success": success,
        }
        if run_id is not None:
            payload["run_id"] = str(run_id)
        if session_id is not None:
            payload["session_id"] = str(session_id)
        if end_user_id is not None:
            payload["end_user_id"] = str(end_user_id)
        if value_usd is not None:
            payload["value_usd"] = value_usd
        if labels is not None:
            payload["labels"] = labels

        try:
            import httpx  # noqa: PLC0415

            resp = httpx.post(
                f"{self.base_url}/outcomes",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5.0,
            )
            resp.raise_for_status()
        except Exception as exc:
            log.warning(
                "outcome_post_failed", outcome_type=outcome_type, error=str(exc)
            )

    # ── Prompt management ─────────────────────────────────────────────────────

    # In-memory cache: key → (data_dict, expires_at_monotonic)
    _prompt_cache: dict[str, tuple[dict[str, Any], float]] = {}
    _prompt_cache_lock: threading.Lock = threading.Lock()
    _PROMPT_CACHE_TTL: float = 60.0

    def get_prompt(
        self,
        name: str,
        environment: str = "production",
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Fetch the latest prompt version for the given environment and render it.

        Caches results for 60 seconds to avoid repeated API calls per request.

        The deployment_version convention for linking prompts to runs is:
        ``f"{name}:{version_number}"``

        Parameters
        ----------
        name:
            Prompt name (slug-style, e.g. "support-agent").
        environment:
            Environment to fetch ("production", "staging", "dev").
        variables:
            Dict of ``{{variable}}`` substitution values.

        Returns
        -------
        dict with keys:
            content: str — rendered prompt string
            version: int — version number fetched
            environment: str
            model_hint: str | None
            variables: list — variable schema from the registry
        """
        cache_key = f"{name}:{environment}"
        now = time.monotonic()

        with self._prompt_cache_lock:
            cached = self._prompt_cache.get(cache_key)
            if cached is not None:
                data, expires_at = cached
                if now < expires_at:
                    return self._render_prompt(data, variables)

        if self.local:
            log.info("get_prompt_local", name=name, environment=environment)
            return {
                "content": f"[local] prompt:{name}:{environment}",
                "version": 0,
                "environment": environment,
                "model_hint": None,
                "variables": [],
            }

        try:
            import httpx  # noqa: PLC0415

            resp = httpx.get(
                f"{self.base_url}/prompts/{name}/latest",
                params={"environment": environment},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.warning("get_prompt_failed", name=name, error=str(exc))
            raise

        with self._prompt_cache_lock:
            self._prompt_cache[cache_key] = (data, now + self._PROMPT_CACHE_TTL)

        return self._render_prompt(data, variables)

    @staticmethod
    def _render_prompt(
        data: dict[str, Any],
        variables: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Apply ``{{variable}}`` substitution and return a render result dict."""
        content: str = data.get("content", "")
        if variables:
            for key, value in variables.items():
                content = re.sub(
                    r"\{\{" + re.escape(key) + r"\}\}", str(value), content
                )
        return {
            "content": content,
            "version": data.get("version"),
            "environment": data.get("environment"),
            "model_hint": data.get("model_hint"),
            "variables": data.get("variables", []),
        }

    # ── Flush / shutdown ──────────────────────────────────────────────────────

    def flush(self) -> None:
        """Block until all buffered events have been sent (sync)."""
        if self._sync_transport:
            self._sync_transport.flush()

    async def aflush(self) -> None:
        """Flush all buffered events (async)."""
        if self._async_transport:
            await self._async_transport._flush_all()
        if self._sync_transport:
            self._sync_transport.flush()

    def shutdown(self) -> None:
        """Flush and shut down the background transport thread."""
        if self._sync_transport:
            self._sync_transport.shutdown()
