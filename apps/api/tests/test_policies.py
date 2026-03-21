"""Tests for unified policy checks."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_policy_check_allows_when_no_constraints(
    authed_client: AsyncClient,
) -> None:
    with patch(
        "runledger_api.services.policies.check_budgets",
        new=AsyncMock(return_value=type("Budget", (), {"allowed": True})()),
    ):
        resp = await authed_client.post("/policies/check", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True
    assert data["decision"] == "allow"
    assert data["reasons"] == []


@pytest.mark.asyncio
async def test_policy_check_blocks_on_budget_block(
    authed_client: AsyncClient,
) -> None:
    budget_result = type(
        "Budget",
        (),
        {
            "allowed": False,
            "action": "block",
            "budget_id": "b_1",
            "downgrade_model": None,
        },
    )()

    with patch(
        "runledger_api.services.policies.check_budgets",
        new=AsyncMock(return_value=budget_result),
    ):
        resp = await authed_client.post("/policies/check", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert data["decision"] == "block"
    assert data["budget_action"] == "block"


@pytest.mark.asyncio
async def test_policy_check_downgrades_when_budget_requires_downgrade(
    authed_client: AsyncClient,
) -> None:
    budget_result = type(
        "Budget",
        (),
        {
            "allowed": False,
            "action": "downgrade",
            "budget_id": "b_2",
            "downgrade_model": "gpt-4o-mini",
        },
    )()

    with patch(
        "runledger_api.services.policies.check_budgets",
        new=AsyncMock(return_value=budget_result),
    ):
        resp = await authed_client.post("/policies/check", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True
    assert data["decision"] == "downgrade"
    assert data["downgrade_model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_policy_check_blocks_on_tool_policy(
    authed_client: AsyncClient,
) -> None:
    with (
        patch(
            "runledger_api.services.policies.check_budgets",
            new=AsyncMock(return_value=type("Budget", (), {"allowed": True})()),
        ),
        patch(
            "runledger_api.services.policies._get_tool_policy",
            new=AsyncMock(return_value="block"),
        ),
    ):
        resp = await authed_client.post(
            "/policies/check",
            json={"tool_name": "dangerous_tool"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert data["decision"] == "block"
    assert data["tool_policy"] == "block"


@pytest.mark.asyncio
async def test_policy_check_blocks_when_gateway_route_missing(
    authed_client: AsyncClient,
) -> None:
    with (
        patch(
            "runledger_api.services.policies.check_budgets",
            new=AsyncMock(return_value=type("Budget", (), {"allowed": True})()),
        ),
        patch(
            "runledger_api.services.policies._has_active_gateway_route",
            new=AsyncMock(return_value=False),
        ),
    ):
        resp = await authed_client.post(
            "/policies/check",
            json={"model_alias": "gpt-4o"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert data["decision"] == "block"
    assert data["gateway_route_available"] is False


@pytest.mark.asyncio
async def test_policy_check_blocks_on_failed_score_gate(
    authed_client: AsyncClient,
) -> None:
    with (
        patch(
            "runledger_api.services.policies.check_budgets",
            new=AsyncMock(return_value=type("Budget", (), {"allowed": True})()),
        ),
        patch(
            "runledger_api.services.policies._passes_score_gate",
            new=AsyncMock(return_value=False),
        ),
    ):
        resp = await authed_client.post(
            "/policies/check",
            json={
                "score_gate": {"name": "accuracy", "min_value": 90},
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert data["decision"] == "block"
    assert data["score_gate_passed"] is False
