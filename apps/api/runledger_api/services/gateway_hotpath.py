"""
Hot-path helpers for the gateway preflight (review cd:gw-perf).

Two layers, both opt-in and both safe to ignore:

* **Request memo** (``request_memo()``): a per-request dict held in a ContextVar.
  Route and routing-group lookups for an alias run once per request instead of once
  per caller (semantic decision, primary choice, step loop, policy switch). Nothing
  leaks across requests; outside a memo block every lookup hits the database.
* **Process TTL cache** (``ttl_cache``): a few seconds of reuse for read-mostly
  aggregates that are expensive and tolerate staleness — the 24 h region-latency
  ranking, latency-optimized group stats, cost-cap passes and the cache profile.
  ``RUNLEDGER_GATEWAY_HOTPATH_TTL_S`` sets the TTL (0 disables it).

A query counter (``count_queries``) lets tests and the CI benchmark assert how much
SQL one preflight issues.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

_MEMO: ContextVar[dict[Any, Any] | None] = ContextVar("gateway_request_memo", default=None)
_MISSING = object()


@contextmanager
def request_memo() -> Iterator[dict[Any, Any]]:
    """Scope a request memo; nested calls reuse the outer one."""
    current = _MEMO.get()
    if current is not None:
        yield current
        return
    memo: dict[Any, Any] = {}
    token = _MEMO.set(memo)
    try:
        yield memo
    finally:
        _MEMO.reset(token)


def memo_get(key: Any) -> Any:
    memo = _MEMO.get()
    if memo is None:
        return _MISSING
    return memo.get(key, _MISSING)


def memo_put(key: Any, value: Any) -> None:
    memo = _MEMO.get()
    if memo is not None:
        memo[key] = value


def is_missing(value: Any) -> bool:
    return value is _MISSING


def hotpath_ttl_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("RUNLEDGER_GATEWAY_HOTPATH_TTL_S", "5")))
    except ValueError:
        return 5.0


class TTLCache:
    """A tiny bounded TTL map (per process). Values must be plain data, never ORM rows."""

    def __init__(self, max_items: int = 4096) -> None:
        self._items: dict[Any, tuple[float, Any]] = {}
        self._max = max_items

    def get(self, key: Any) -> Any:
        hit = self._items.get(key)
        if hit is None:
            return _MISSING
        expires, value = hit
        if expires < time.monotonic():
            self._items.pop(key, None)
            return _MISSING
        return value

    def put(self, key: Any, value: Any, ttl: float | None = None) -> None:
        ttl = hotpath_ttl_seconds() if ttl is None else ttl
        if ttl <= 0:
            return
        if len(self._items) >= self._max:
            # Drop expired entries first, then the oldest half.
            now = time.monotonic()
            self._items = {k: v for k, v in self._items.items() if v[0] >= now}
            if len(self._items) >= self._max:
                for k in list(self._items)[: self._max // 2]:
                    self._items.pop(k, None)
        self._items[key] = (time.monotonic() + ttl, value)

    def pop(self, key: Any) -> None:
        self._items.pop(key, None)

    def clear(self) -> None:
        self._items.clear()


ttl_cache = TTLCache()


# ── Query counting (tests / benchmark) ─────────────────────────────────────────


@contextmanager
def count_queries(engine: Any) -> Iterator[list[str]]:
    """Collect every SQL statement executed on ``engine`` (a sync or async engine)."""
    from sqlalchemy import event  # noqa: PLC0415

    target = getattr(engine, "sync_engine", engine)
    statements: list[str] = []

    def _on_execute(*args: Any) -> None:
        statements.append(str(args[2]))

    event.listen(target, "before_cursor_execute", _on_execute)
    try:
        yield statements
    finally:
        event.remove(target, "before_cursor_execute", _on_execute)
