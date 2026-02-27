"""Tests for runledger_sdk.transport"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from runledger_sdk.transport import (
    _MAX_QUEUE_SIZE,
    SyncTransport,
    Transport,
)

# ── Transport (async) ─────────────────────────────────────────────────────────


async def test_transport_local_mode_logs_to_console() -> None:
    transport = Transport(api_key=None, base_url="http://test", local=True)
    with patch("runledger_sdk.transport._log_local") as mock_log:
        await transport.enqueue({"event_type": "run_start", "run_id": "abc"})
        await transport._flush_all()
        mock_log.assert_called_once()
        events = mock_log.call_args[0][0]
        assert len(events) == 1
        assert events[0]["event_type"] == "run_start"


async def test_transport_queue_drains_on_flush() -> None:
    transport = Transport(api_key=None, base_url="http://test", local=True)
    with patch("runledger_sdk.transport._log_local"):
        await transport.enqueue({"event_type": "e1"})
        await transport.enqueue({"event_type": "e2"})
        assert len(transport._queue) == 2
        await transport._flush_all()
        assert len(transport._queue) == 0


async def test_transport_drops_oldest_when_full() -> None:
    transport = Transport(api_key=None, base_url="http://test", local=True)
    # Fill the queue to max
    for i in range(_MAX_QUEUE_SIZE):
        transport._queue.append({"i": i})
    # Patch _flush_all to prevent auto-flush from clearing the queue before we inspect it
    with patch.object(transport, "_flush_all", AsyncMock()):
        await transport.enqueue({"i": "new"})
    assert len(transport._queue) == _MAX_QUEUE_SIZE
    assert transport._queue[-1] == {"i": "new"}
    assert transport._queue[0] == {"i": 1}  # oldest ({"i": 0}) was dropped


async def test_transport_sends_batch_to_api() -> None:
    transport = Transport(
        api_key="rl_test_key", base_url="http://api.test", local=False
    )
    await transport.enqueue({"event_type": "run_start", "run_id": "x"})

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await transport._flush_all()

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.kwargs["json"] == {
        "events": [{"event_type": "run_start", "run_id": "x"}]
    }
    assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer rl_test_key"


async def test_transport_retries_on_failure() -> None:
    transport = Transport(
        api_key="rl_test_key", base_url="http://api.test", local=False
    )
    await transport.enqueue({"event_type": "run_start"})

    call_count = 0

    async def failing_post(*args: Any, **kwargs: Any) -> None:
        nonlocal call_count
        call_count += 1
        raise ConnectionError("network error")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = failing_post

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("asyncio.sleep"),  # skip actual waiting
    ):
        await transport._send_with_retry([{"event_type": "run_start"}])

    assert call_count == 3  # max retries


async def test_transport_start_stop_lifecycle() -> None:
    transport = Transport(api_key=None, base_url="http://test", local=True)
    transport.start()
    assert transport._flush_task is not None
    assert not transport._flush_task.done()
    await transport.stop(drain=False)
    # After stop, task should be done
    assert transport._flush_task.done()


# ── SyncTransport ─────────────────────────────────────────────────────────────


def test_sync_transport_enqueue_starts_thread() -> None:
    transport = SyncTransport(api_key=None, base_url="http://test", local=True)
    with patch("runledger_sdk.transport._log_local"):
        transport.enqueue({"event_type": "run_start"})
        assert transport._thread is not None
        assert transport._thread.is_alive()
        transport.flush()
        transport.shutdown()


def test_sync_transport_local_mode() -> None:
    transport = SyncTransport(api_key=None, base_url="http://test", local=True)
    captured: list[list[dict[str, Any]]] = []

    def capture_log(batch: list[dict[str, Any]]) -> None:
        captured.append(batch)

    with patch("runledger_sdk.transport._log_local", side_effect=capture_log):
        transport.enqueue({"event_type": "run_start", "run_id": "sync-1"})
        transport.flush()

    assert len(captured) == 1
    assert captured[0][0]["run_id"] == "sync-1"
    transport.shutdown()
