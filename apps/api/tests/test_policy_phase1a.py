from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from runledger_api.schemas.policies import FinopsSimulationRequest
from runledger_api.services.policies import get_tool_cost_accounting, simulate_finops_policy


def _result(rows):
    result = MagicMock()
    result.one.return_value = rows
    result.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_simulate_finops_policy_returns_savings() -> None:
    db = AsyncMock()
    redis = AsyncMock()
    workspace_id = uuid.uuid4()

    db.execute = AsyncMock(
        side_effect=[
            _result(SimpleNamespace(mcp_cost=Decimal("4.00"), mcp_calls=10)),
            _result(
                SimpleNamespace(tool_calls=20, search_cost=Decimal("2.00"), avg_duration=250.0)
            ),
        ]
    )

    with patch(
        "runledger_api.services.policies.evaluate_policy_check",
        new=AsyncMock(return_value=SimpleNamespace(allowed=True, decision="allow", reasons=[])),
    ):
        result = await simulate_finops_policy(
            db=db,
            redis=redis,
            workspace_id=workspace_id,
            body=FinopsSimulationRequest(
                current_model="gpt-4o",
                proposed_model="gpt-4o-mini",
                enable_cache=True,
            ),
        )

    assert result.affected_requests == 30
    assert result.current_cost_usd == Decimal("6.00")
    assert result.projected_savings_usd > Decimal("0")
    assert result.policy.decision == "allow"


@pytest.mark.asyncio
async def test_get_tool_cost_accounting_groups_sources() -> None:
    db = AsyncMock()
    workspace_id = uuid.uuid4()
    now = datetime.now(UTC)

    db.execute = AsyncMock(
        side_effect=[
            _result(
                [
                    SimpleNamespace(
                        tool_name="browser.search", call_count=3, total_cost=Decimal("1.50")
                    ),
                ]
            ),
            _result(
                [
                    SimpleNamespace(
                        tool_name="web_search",
                        tool_type="read",
                        call_count=4,
                        unit_cost=Decimal("0.20"),
                    ),
                ]
            ),
            _result(
                [
                    SimpleNamespace(
                        tool_name="shell_command", tool_type="privileged", call_count=2
                    ),
                ]
            ),
        ]
    )

    result = await get_tool_cost_accounting(
        db=db,
        workspace_id=workspace_id,
        from_dt=now - timedelta(days=7),
        to_dt=now,
    )

    assert result.total_calls == 9
    assert result.tracked_calls == 3
    assert result.estimated_calls == 6
    assert result.total_cost_usd == Decimal("2.30")
    assert any(item.source == "mcp_tracked" for item in result.items)
    assert any(item.source == "search_tool_estimated" for item in result.items)
    assert any(item.source == "unpriced_tool_activity" for item in result.items)
