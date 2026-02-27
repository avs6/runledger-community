"""
RunLedger context propagation using contextvars.

Thread-safe and async-safe. Nested contexts inherit parent values and reset
to previous values on exit.

Usage::

    with rl.context(end_user_id="u_123", feature_tag="support-chat"):
        response = openai_client.chat.completions.create(...)

    async with rl.context(end_user_id="u_123"):
        response = await async_openai_client.chat.completions.create(...)
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar, Token
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

# ── ContextVars ───────────────────────────────────────────────────────────────

_run_id: ContextVar[str | None] = ContextVar("rl_run_id", default=None)
_end_user_id: ContextVar[str | None] = ContextVar("rl_end_user_id", default=None)
_session_id: ContextVar[str | None] = ContextVar("rl_session_id", default=None)
_feature_tag: ContextVar[str | None] = ContextVar("rl_feature_tag", default=None)
_deployment_version: ContextVar[str | None] = ContextVar(
    "rl_deployment_version", default=None
)


# ── Public accessors ──────────────────────────────────────────────────────────


def get_run_id() -> str:
    """Return the current run_id, generating a new UUID if none is set."""
    run_id = _run_id.get()
    if run_id is None:
        run_id = str(uuid.uuid4())
        _run_id.set(run_id)
    return run_id


def get_end_user_id() -> str | None:
    return _end_user_id.get()


def get_session_id() -> str | None:
    return _session_id.get()


def get_feature_tag() -> str | None:
    return _feature_tag.get()


def get_deployment_version() -> str | None:
    return _deployment_version.get()


def get_context_snapshot() -> dict[str, str | None]:
    """Return all current context values as a plain dict."""
    return {
        "run_id": _run_id.get(),
        "end_user_id": _end_user_id.get(),
        "session_id": _session_id.get(),
        "feature_tag": _feature_tag.get(),
        "deployment_version": _deployment_version.get(),
    }


# ── Internals ─────────────────────────────────────────────────────────────────


def _set_vars(
    run_id: str | None,
    end_user_id: str | None,
    session_id: str | None,
    feature_tag: str | None,
    deployment_version: str | None,
) -> tuple[str, list[tuple[ContextVar[str | None], Token[str | None]]]]:
    """Set context vars, returning (effective_run_id, list of (var, token) to reset)."""
    effective_run_id = run_id or str(uuid.uuid4())
    tokens: list[tuple[ContextVar[str | None], Token[str | None]]] = []

    tokens.append((_run_id, _run_id.set(effective_run_id)))
    if end_user_id is not None:
        tokens.append((_end_user_id, _end_user_id.set(end_user_id)))
    if session_id is not None:
        tokens.append((_session_id, _session_id.set(session_id)))
    if feature_tag is not None:
        tokens.append((_feature_tag, _feature_tag.set(feature_tag)))
    if deployment_version is not None:
        tokens.append(
            (_deployment_version, _deployment_version.set(deployment_version))
        )

    return effective_run_id, tokens


def _reset_vars(tokens: list[tuple[ContextVar[str | None], Token[str | None]]]) -> None:
    for var, token in reversed(tokens):
        var.reset(token)


@contextmanager
def _sync_context(
    *,
    run_id: str | None = None,
    end_user_id: str | None = None,
    session_id: str | None = None,
    feature_tag: str | None = None,
    deployment_version: str | None = None,
) -> Generator[str]:
    """Sync context manager. Yields the effective run_id."""
    effective_run_id, tokens = _set_vars(
        run_id, end_user_id, session_id, feature_tag, deployment_version
    )
    try:
        yield effective_run_id
    finally:
        _reset_vars(tokens)


@asynccontextmanager
async def _async_context(
    *,
    run_id: str | None = None,
    end_user_id: str | None = None,
    session_id: str | None = None,
    feature_tag: str | None = None,
    deployment_version: str | None = None,
) -> AsyncGenerator[str]:
    """Async context manager. Yields the effective run_id."""
    effective_run_id, tokens = _set_vars(
        run_id, end_user_id, session_id, feature_tag, deployment_version
    )
    try:
        yield effective_run_id
    finally:
        _reset_vars(tokens)


# ── Public context class ──────────────────────────────────────────────────────


class RunLedgerContext:
    """
    Dual-mode context manager (sync + async) returned by ``rl.context(...)``.

    Supports both ``with`` and ``async with`` usage, yielding the run_id.
    """

    def __init__(
        self,
        *,
        run_id: str | None = None,
        end_user_id: str | None = None,
        session_id: str | None = None,
        feature_tag: str | None = None,
        deployment_version: str | None = None,
    ) -> None:
        self._kwargs: dict[str, str | None] = {
            "run_id": run_id,
            "end_user_id": end_user_id,
            "session_id": session_id,
            "feature_tag": feature_tag,
            "deployment_version": deployment_version,
        }
        self._tokens: list[tuple[ContextVar[str | None], Token[str | None]]] = []
        self._effective_run_id: str | None = None

    def __enter__(self) -> str:
        self._effective_run_id, self._tokens = _set_vars(**self._kwargs)
        return self._effective_run_id

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        _reset_vars(self._tokens)

    async def __aenter__(self) -> str:
        self._effective_run_id, self._tokens = _set_vars(**self._kwargs)
        return self._effective_run_id

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        _reset_vars(self._tokens)
