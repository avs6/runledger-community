"""
RunLedger transport layer.

Buffers events in-memory and flushes them to the ingest API in batches.
Works in both async contexts (via asyncio) and sync contexts (via a background
thread that owns its own event loop).

Design:
- In-memory queue (max 500 events)
- Flush every 2 s or when queue hits 100 events (whichever comes first)
- 3 retries with exponential backoff (1 s, 2 s, 4 s), then drop + warn
- Local mode: pretty-print events to console instead of sending to API
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

_FLUSH_INTERVAL = 2.0  # seconds between auto-flushes
_FLUSH_THRESHOLD = 100  # flush early when queue reaches this size
_MAX_QUEUE_SIZE = 500  # drop oldest events when exceeded
_MAX_RETRIES = 3
_RETRY_BASE = 1.0  # seconds; doubles on each retry


class Transport:
    """
    Async-first transport.  Call ``enqueue()`` from anywhere; the internal
    flush loop (driven by ``start()`` / ``stop()``) handles batching.

    For sync SDK usage a ``SyncTransport`` wraps this in a background thread.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        local: bool = False,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._local = local or api_key is None

        self._queue: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task[None] | None = None
        self._stopped = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Schedule the background flush loop. Must be called from an async context."""
        if self._flush_task is None or self._flush_task.done():
            self._stopped = False
            self._flush_task = asyncio.ensure_future(self._flush_loop())

    async def stop(self, drain: bool = True) -> None:
        """Stop the flush loop. If drain=True, flush remaining events first."""
        self._stopped = True
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._flush_task
        if drain:
            await self._flush_all()

    # ── Enqueue ───────────────────────────────────────────────────────────────

    async def enqueue(self, event: dict[str, Any]) -> None:
        """Add an event to the buffer. Non-blocking."""
        async with self._lock:
            if len(self._queue) >= _MAX_QUEUE_SIZE:
                self._queue.pop(0)  # drop oldest
                log.warning("transport_queue_full_dropping_oldest")
            self._queue.append(event)

        if len(self._queue) >= _FLUSH_THRESHOLD:
            await self._flush_all()

    # ── Flush ─────────────────────────────────────────────────────────────────

    async def _flush_loop(self) -> None:
        while not self._stopped:
            await asyncio.sleep(_FLUSH_INTERVAL)
            await self._flush_all()

    async def _flush_all(self) -> None:
        async with self._lock:
            if not self._queue:
                return
            batch = self._queue[:]
            self._queue.clear()

        if self._local:
            _log_local(batch)
            return

        await self._send_with_retry(batch)

    async def _send_with_retry(self, batch: list[dict[str, Any]]) -> None:
        delay = _RETRY_BASE
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                await self._send(batch)
                return
            except Exception as exc:
                if attempt == _MAX_RETRIES:
                    log.warning(
                        "transport_batch_dropped",
                        events=len(batch),
                        error=str(exc),
                    )
                    return
                log.debug(
                    "transport_retry",
                    attempt=attempt,
                    delay=delay,
                    error=str(exc),
                )
                await asyncio.sleep(delay)
                delay *= 2

    async def _send(self, batch: list[dict[str, Any]]) -> None:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/ingest/v1/batch"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={"events": batch}, headers=headers)
            resp.raise_for_status()


# ── Local mode ────────────────────────────────────────────────────────────────


def _log_local(batch: list[dict[str, Any]]) -> None:
    for event in batch:
        print(json.dumps(event, default=str))  # noqa: T201


# ── Sync wrapper ──────────────────────────────────────────────────────────────


class SyncTransport:
    """
    Wraps ``Transport`` for use from synchronous code.

    Runs its own asyncio event loop in a background daemon thread.
    The thread is started lazily on first ``enqueue()`` call.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        local: bool = False,
        budget_check: bool = False,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._local = local
        self.budget_check = budget_check

        self._loop: asyncio.AbstractEventLoop | None = None
        self._transport: Transport | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._lock = threading.Lock()

    def _ensure_started(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._ready.clear()
            self._thread = threading.Thread(
                target=self._run_loop, daemon=True, name="rl-transport"
            )
            self._thread.start()
        self._ready.wait(timeout=5.0)

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._transport = Transport(
            api_key=self._api_key,
            base_url=self._base_url,
            local=self._local,
        )
        self._transport.start()
        self._ready.set()
        try:
            self._loop.run_forever()
        finally:
            if self._transport:
                self._loop.run_until_complete(self._transport.stop(drain=True))

    def enqueue(self, event: dict[str, Any]) -> None:
        self._ensure_started()
        assert self._loop is not None and self._transport is not None
        asyncio.run_coroutine_threadsafe(self._transport.enqueue(event), self._loop)

    def flush(self) -> None:
        """Block until all buffered events are sent."""
        self._ensure_started()
        assert self._loop is not None and self._transport is not None
        future = asyncio.run_coroutine_threadsafe(
            self._transport._flush_all(), self._loop
        )
        future.result(timeout=30.0)

    def shutdown(self) -> None:
        """Flush remaining events and stop the background thread."""
        if self._loop is None or self._transport is None:
            return
        future = asyncio.run_coroutine_threadsafe(
            self._transport.stop(drain=True),
            self._loop,
        )
        future.result(timeout=30.0)
        self._loop.call_soon_threadsafe(self._loop.stop)
