"""
RunLedger SDK client.

OpenAI instrumentation: Phase 2.
LangChain/LangGraph instrumentation: Phase 3.
"""

from __future__ import annotations

import os

from runledger_sdk.context import RunLedgerContext, get_context_snapshot
from runledger_sdk.transport import SyncTransport, Transport

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
