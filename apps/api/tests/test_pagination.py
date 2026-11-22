"""One pagination standard for list endpoints (review: pagination audit)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Response
from runledger_api.core.pagination import MAX_LIMIT, PageParams, paginate, paginate_list
from runledger_api.main import app
from runledger_api.models.prompts import Prompt
from sqlalchemy import select

LISTED = [
    "/settings/email/log",
    "/settings/email/history",
    "/settings/api-keys",
    "/tools/security-events",
    "/users",
    "/users/all",
    "/org/members",
    "/prompts",
    "/gateway/routes",
    "/billing/chargeback-report",
    "/analytics/annotations",
    "/analytics/regressions",
    "/alerts/rules",
    "/budgets",
    "/budgets/notifications",
    "/billing/periods",
    "/replay/datasets",
    "/replay/experiments",
    "/evaluations/evaluators",
    "/mcp-registry",
    "/mcp-registry/tools",
    "/ledger/snapshots",
    "/hub/models",
]


@pytest.mark.parametrize("path", LISTED)
def test_listed_endpoints_take_limit_and_offset(path: str) -> None:
    params = {p["name"]: p for p in app.openapi()["paths"][path]["get"].get("parameters", [])}
    assert "limit" in params and "offset" in params, path
    assert params["limit"]["schema"].get("maximum", 0) <= MAX_LIMIT


def test_paginate_list_headers() -> None:
    resp = Response()
    chunk = paginate_list(list(range(10)), PageParams(limit=3, offset=6), resp)
    assert chunk == [6, 7, 8]
    assert resp.headers["X-Total-Count"] == "10"
    assert resp.headers["X-Has-More"] == "true"
    resp = Response()
    assert paginate_list(list(range(10)), PageParams(limit=5, offset=8), resp) == [8, 9]
    assert resp.headers["X-Has-More"] == "false"


@pytest.mark.asyncio
async def test_paginate_counts_then_pages() -> None:
    count = MagicMock()
    count.scalar_one = MagicMock(return_value=42)
    rows = MagicMock()
    rows.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=["a", "b"])))
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[count, rows])
    resp = Response()
    out = await paginate(
        db, select(Prompt).order_by(Prompt.id), PageParams(limit=2, offset=0), resp
    )
    assert out == ["a", "b"]
    assert resp.headers["X-Total-Count"] == "42"
    assert resp.headers["X-Has-More"] == "true"
    sql = str(db.execute.await_args_list[1].args[0])
    assert "LIMIT" in sql and "OFFSET" in sql
