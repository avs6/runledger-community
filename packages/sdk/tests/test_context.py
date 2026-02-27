"""Tests for runledger_sdk.context"""

from __future__ import annotations

import asyncio
import uuid

from runledger_sdk.context import (
    RunLedgerContext,
    _run_id,
    get_context_snapshot,
    get_end_user_id,
    get_feature_tag,
    get_run_id,
    get_session_id,
)

# ── Basic get_run_id ──────────────────────────────────────────────────────────


def test_get_run_id_generates_uuid_when_none() -> None:
    _run_id.set(None)
    run_id = get_run_id()
    assert uuid.UUID(run_id)  # valid UUID


def test_get_run_id_returns_same_value_within_scope() -> None:
    _run_id.set(None)
    first = get_run_id()
    second = get_run_id()
    assert first == second


# ── Sync context manager ──────────────────────────────────────────────────────


def test_sync_context_sets_and_resets_vars() -> None:
    _run_id.set(None)
    ctx = RunLedgerContext(end_user_id="u_123", feature_tag="chat")
    with ctx as run_id:
        assert uuid.UUID(run_id)
        assert get_end_user_id() == "u_123"
        assert get_feature_tag() == "chat"
    # After exit, values should be reset to None
    assert get_end_user_id() is None
    assert get_feature_tag() is None


def test_sync_context_explicit_run_id() -> None:
    fixed = str(uuid.uuid4())
    ctx = RunLedgerContext(run_id=fixed)
    with ctx as run_id:
        assert run_id == fixed
        assert get_run_id() == fixed


def test_sync_context_nested_override() -> None:
    outer_ctx = RunLedgerContext(end_user_id="outer", feature_tag="outer-tag")
    with outer_ctx:
        assert get_end_user_id() == "outer"
        inner_ctx = RunLedgerContext(end_user_id="inner")
        with inner_ctx:
            assert get_end_user_id() == "inner"
            assert get_feature_tag() == "outer-tag"  # inherited from outer
        assert get_end_user_id() == "outer"
    assert get_end_user_id() is None


def test_sync_context_resets_on_exception() -> None:
    ctx = RunLedgerContext(end_user_id="u_exc")
    try:
        with ctx:
            assert get_end_user_id() == "u_exc"
            raise ValueError("boom")
    except ValueError:
        pass
    assert get_end_user_id() is None


# ── Async context manager ─────────────────────────────────────────────────────


async def test_async_context_sets_and_resets_vars() -> None:
    ctx = RunLedgerContext(end_user_id="async_user", session_id="s_1")
    async with ctx as run_id:
        assert uuid.UUID(run_id)
        assert get_end_user_id() == "async_user"
        assert get_session_id() == "s_1"
    assert get_end_user_id() is None
    assert get_session_id() is None


async def test_async_context_resets_on_exception() -> None:
    ctx = RunLedgerContext(end_user_id="async_exc")
    try:
        async with ctx:
            assert get_end_user_id() == "async_exc"
            raise RuntimeError("async boom")
    except RuntimeError:
        pass
    assert get_end_user_id() is None


async def test_async_contexts_are_task_isolated() -> None:
    """Two concurrent tasks should have independent contexts."""
    results: dict[str, str | None] = {}

    async def task_a() -> None:
        async with RunLedgerContext(end_user_id="alice"):
            await asyncio.sleep(0.01)
            results["a"] = get_end_user_id()

    async def task_b() -> None:
        async with RunLedgerContext(end_user_id="bob"):
            await asyncio.sleep(0.01)
            results["b"] = get_end_user_id()

    await asyncio.gather(task_a(), task_b())
    assert results["a"] == "alice"
    assert results["b"] == "bob"


# ── Snapshot ──────────────────────────────────────────────────────────────────


def test_snapshot_returns_all_fields() -> None:
    ctx = RunLedgerContext(end_user_id="snap", feature_tag="ft")
    with ctx as run_id:
        snap = get_context_snapshot()
        assert snap["run_id"] == run_id
        assert snap["end_user_id"] == "snap"
        assert snap["feature_tag"] == "ft"
        assert snap["session_id"] is None
        assert snap["deployment_version"] is None
