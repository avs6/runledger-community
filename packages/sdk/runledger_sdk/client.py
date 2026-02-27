"""
RunLedger SDK client.

OpenAI instrumentation is implemented in Phase 2.
LangChain/LangGraph instrumentation is added in Phase 3.
"""

from __future__ import annotations

from runledger_sdk.context import RunLedgerContext
from runledger_sdk.transport import SyncTransport, Transport


class PrivacyMode:
    """Controls how much payload data is captured and transmitted."""

    METADATA_ONLY = "metadata_only"  # default: tokens, model, latency only
    ERRORS_ONLY = "errors_only"  # metadata + payload captured on errors
    SAMPLED = "sampled"  # metadata + payload on N% of calls
    FULL = "full"  # capture everything (explicit opt-in)


class RunLedger:
    """
    Main RunLedger client.

    Sync usage::

        from runledger_sdk import RunLedger

        rl = RunLedger(api_key="rl_live_...")
        rl.instrument()

        import openai
        client = openai.OpenAI()

        with rl.context(end_user_id="u_123", feature_tag="support-chat"):
            resp = client.chat.completions.create(model="gpt-4o", messages=[...])

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
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.privacy_mode = privacy_mode
        # local=True → log events to console instead of sending to API
        self.local = local or api_key is None

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
