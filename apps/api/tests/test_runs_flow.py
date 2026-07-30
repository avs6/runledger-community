from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from runledger_api.core.deps import get_current_user
from runledger_api.main import app


def _scalar_one_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one = MagicMock(return_value=value)
    return result


def _row_result(rows: list[object]) -> MagicMock:
    result = MagicMock()
    result.all = MagicMock(return_value=rows)
    return result


@pytest.mark.asyncio
async def test_run_flow_empty_workspace_scope(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    async def override_get_current_user() -> None:
        return None

    app.dependency_overrides[get_current_user] = override_get_current_user
    mock_db_session.execute = AsyncMock(
        side_effect=[
            _scalar_one_result(0),
            _row_result([]),
        ]
    )

    resp = await authed_client.get("/runs/flow")

    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "workspace"
    assert body["sampled_runs"] == 0
    assert body["total_runs"] == 0
    assert body["workspace_count"] == 1
    assert body["items"] == []
