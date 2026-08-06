"""
Tests for the runledger CLI.

Uses typer's CliRunner and httpx mocking so no live API is required.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

try:
    from typer.testing import CliRunner

    from runledger_sdk.cli import app

    _TYPER_AVAILABLE = True
except ImportError:
    _TYPER_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _TYPER_AVAILABLE, reason="typer not installed")

runner = CliRunner()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _mock_response(status_code: int = 200, json_data: Any = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_data or {})
    resp.text = str(json_data or "")
    return resp


# ── validate ──────────────────────────────────────────────────────────────────


def test_validate_success() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.post = MagicMock(return_value=_mock_response(202, {"accepted": 1}))

    with patch("runledger_sdk.cli.httpx.Client", return_value=mock_client):
        result = runner.invoke(app, ["validate", "--api-key", "rl_test_abc"])

    assert result.exit_code == 0
    assert "Accepted" in result.output


def test_validate_api_error() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.post = MagicMock(
        return_value=_mock_response(401, {"detail": "unauthorized"})
    )

    with patch("runledger_sdk.cli.httpx.Client", return_value=mock_client):
        result = runner.invoke(app, ["validate", "--api-key", "rl_test_bad"])

    assert result.exit_code == 1


def test_validate_requires_api_key() -> None:
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUNLEDGER_API_KEY", "rl_test_env_key")

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.post = MagicMock(return_value=_mock_response(202))

    with patch("runledger_sdk.cli.httpx.Client", return_value=mock_client):
        result = runner.invoke(app, ["validate"])

    assert result.exit_code == 0


# ── status ────────────────────────────────────────────────────────────────────


def test_status_all_ok() -> None:
    health_data = {"status": "ok", "db": "ok", "redis": "ok"}

    with patch(
        "runledger_sdk.cli.httpx.get", return_value=_mock_response(200, health_data)
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "ok" in result.output


def test_status_degraded() -> None:
    health_data = {"status": "ok", "db": "ok", "redis": "error"}

    with patch(
        "runledger_sdk.cli.httpx.get", return_value=_mock_response(200, health_data)
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 1


def test_status_api_down() -> None:
    import httpx

    with patch(
        "runledger_sdk.cli.httpx.get", side_effect=httpx.ConnectError("refused")
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 1


# ── runs ──────────────────────────────────────────────────────────────────────


def test_runs_shows_table() -> None:
    import uuid
    from datetime import UTC, datetime

    runs_data = [
        {
            "id": str(uuid.uuid4()),
            "status": "succeeded",
            "feature_tag": "support-chat",
            "total_cost_usd": "0.0042",
            "total_input_tokens": 512,
            "total_output_tokens": 128,
            "started_at": datetime.now(UTC).isoformat(),
        }
    ]

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.get = MagicMock(return_value=_mock_response(200, runs_data))

    with patch("runledger_sdk.cli.httpx.Client", return_value=mock_client):
        result = runner.invoke(app, ["runs", "--api-key", "rl_test_abc"])

    assert result.exit_code == 0
    # Rich may truncate long values in narrow columns; check the prefix
    assert "support" in result.output


def test_runs_empty_workspace() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.get = MagicMock(return_value=_mock_response(200, []))

    with patch("runledger_sdk.cli.httpx.Client", return_value=mock_client):
        result = runner.invoke(app, ["runs", "--api-key", "rl_test_abc"])

    assert result.exit_code == 0
    assert "No runs" in result.output


def test_task_start_returns_run_id() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.post = MagicMock(return_value=_mock_response(202, {"accepted": 1}))

    with patch("runledger_sdk.cli.httpx.Client", return_value=mock_client):
        result = runner.invoke(
            app,
            ["task", "start", "--api-key", "rl_test_abc", "--task", "Fix failing tests"],
        )

    assert result.exit_code == 0
    assert '"run_id"' in result.output


def test_task_outcome_posts_batch() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.post = MagicMock(return_value=_mock_response(202, {"accepted": 2}))

    with patch("runledger_sdk.cli.httpx.Client", return_value=mock_client):
        result = runner.invoke(
            app,
            [
                "task",
                "outcome",
                "--api-key",
                "rl_test_abc",
                "--run-id",
                "11111111-1111-1111-1111-111111111111",
                "--result",
                "completed",
            ],
        )

    assert result.exit_code == 0
    body = mock_client.post.call_args.kwargs["json"]
    assert len(body["events"]) == 2


# ── client.py propagation helpers ─────────────────────────────────────────────


def test_propagation_headers_and_from_headers() -> None:
    from runledger_sdk.client import RunLedger
    from runledger_sdk.context import RunLedgerContext, _run_id

    _run_id.set(None)
    rl = RunLedger(api_key="rl_test_abc")

    with RunLedgerContext(end_user_id="u_42", feature_tag="chat") as run_id:
        headers = rl.propagation_headers()

    assert headers["X-RunLedger-Run-Id"] == run_id
    assert headers["X-RunLedger-End-User-Id"] == "u_42"
    assert headers["X-RunLedger-Feature-Tag"] == "chat"

    # Restore from headers
    ctx = RunLedger.from_headers(headers)
    with ctx as restored_run_id:
        from runledger_sdk.context import get_end_user_id, get_feature_tag

        assert restored_run_id == run_id
        assert get_end_user_id() == "u_42"
        assert get_feature_tag() == "chat"


def test_from_headers_case_insensitive() -> None:
    from runledger_sdk.client import RunLedger

    headers = {
        "x-runledger-run-id": "some-run-id",
        "x-runledger-feature-tag": "my-feature",
    }
    ctx = RunLedger.from_headers(headers)
    with ctx as run_id:
        from runledger_sdk.context import get_feature_tag

        assert run_id == "some-run-id"
        assert get_feature_tag() == "my-feature"
