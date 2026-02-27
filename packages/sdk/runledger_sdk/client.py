"""
RunLedger SDK client — skeleton for Phase 0.

Full implementation built across Phases 2 (OpenAI) and 3 (LangChain/LangGraph).
"""

from __future__ import annotations

from enum import StrEnum


class PrivacyMode(StrEnum):
    """Controls how much payload data is captured and transmitted."""

    METADATA_ONLY = "metadata_only"  # default: tokens, model, latency only
    ERRORS_ONLY = "errors_only"  # metadata + payload captured on errors
    SAMPLED = "sampled"  # metadata + payload on N% of calls
    FULL = "full"  # capture everything (explicit opt-in)


class RunLedger:
    """
    Main RunLedger client.

    Usage::

        from runledger_sdk import RunLedger

        rl = RunLedger(api_key="rl_live_...")
        rl.instrument()  # patches OpenAI + LangChain/LangGraph automatically
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.runledger.io",
        privacy_mode: PrivacyMode = PrivacyMode.METADATA_ONLY,
        local: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.privacy_mode = privacy_mode
        # local=True → log events to console instead of sending to API
        self.local = local or api_key is None

    def instrument(self) -> None:
        """
        One-line enablement: patches OpenAI and LangChain clients.

        Implemented in Phase 2 (OpenAI) and Phase 3 (LangChain/LangGraph).
        """
        raise NotImplementedError(
            "instrument() is implemented in Phase 2. "
            "Use RunLedgerCallbackHandler for LangChain in the meantime."
        )

    def context(
        self,
        *,
        end_user_id: str | None = None,
        session_id: str | None = None,
        feature_tag: str | None = None,
        deployment_version: str | None = None,
    ) -> object:
        """
        Context manager to attach user/session metadata to all runs within scope.

        Implemented in Phase 2.
        """
        raise NotImplementedError("context() is implemented in Phase 2.")
