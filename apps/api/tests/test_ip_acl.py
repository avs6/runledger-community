"""IP ACL evaluation and rule management (review G-18)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from runledger_api.routers.security import _require_platform_admin_for_global
from runledger_api.services.security import evaluate_ip_acl


def _rule(cidr: str, action: str = "allow", **kw: object) -> SimpleNamespace:
    return SimpleNamespace(
        cidr=cidr,
        action=action,
        access_group_id=kw.get("access_group_id"),
        team_name=kw.get("team_name"),
    )


def _db(rules: list[SimpleNamespace], members: list[uuid.UUID] | None = None) -> AsyncMock:
    def result(items: list) -> MagicMock:
        res = MagicMock()
        res.scalars.return_value.all.return_value = items
        return res

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[result(rules), result(members or [])])
    return db


async def _allowed(db: AsyncMock, ip: str | None, user: uuid.UUID | None = None) -> bool:
    try:
        await evaluate_ip_acl(
            db, workspace_id=uuid.uuid4(), api_key_id=None, client_ip=ip, principal_user_id=user
        )
        return True
    except HTTPException as exc:
        assert exc.status_code == 403
        return False


@pytest.mark.asyncio
async def test_allow_list_admits_only_listed_ranges() -> None:
    rules = [_rule("198.51.100.0/24")]
    assert await _allowed(_db(rules), "198.51.100.7")
    assert not await _allowed(_db(rules), "203.0.113.9")


@pytest.mark.asyncio
async def test_deny_only_rules_block_just_their_range() -> None:
    rules = [_rule("192.0.2.0/24", "deny")]
    assert not await _allowed(_db(rules), "192.0.2.10")
    assert await _allowed(_db(rules), "203.0.113.9")


@pytest.mark.asyncio
async def test_first_matching_rule_by_priority_wins() -> None:
    rules = [_rule("192.0.2.10/32", "deny"), _rule("192.0.2.0/24", "allow")]
    assert not await _allowed(_db(rules), "192.0.2.10")
    assert await _allowed(_db(rules), "192.0.2.11")


@pytest.mark.asyncio
async def test_access_group_rules_apply_only_to_members() -> None:
    group = uuid.uuid4()
    user = uuid.uuid4()
    rules = [_rule("198.51.100.0/24", access_group_id=group)]
    assert not await _allowed(_db(rules, [group]), "203.0.113.9", user)
    # Not a member: the group's allow list doesn't apply, so nothing applies.
    assert await _allowed(_db(rules, []), "203.0.113.9", user)


@pytest.mark.asyncio
async def test_legacy_team_rules_are_inert_and_bad_ips_are_403() -> None:
    assert await _allowed(_db([_rule("0.0.0.0/0", "deny", team_name="ops")]), "203.0.113.9")
    assert not await _allowed(_db([_rule("0.0.0.0/0")]), "not-an-ip")
    assert not await _allowed(_db([_rule("0.0.0.0/0")]), None)


def test_global_rules_need_a_platform_admin() -> None:
    org_admin = (SimpleNamespace(), SimpleNamespace(is_platform_admin=False))
    platform = (SimpleNamespace(), SimpleNamespace(is_platform_admin=True))
    with pytest.raises(HTTPException) as exc:
        _require_platform_admin_for_global(org_admin, None)
    assert exc.value.status_code == 403
    _require_platform_admin_for_global(platform, None)
    _require_platform_admin_for_global(org_admin, uuid.uuid4())


def test_get_client_ip_trusts_forwarded_for_only_from_proxies(monkeypatch) -> None:
    from runledger_api.core.config import settings
    from runledger_api.services.security import get_client_ip

    monkeypatch.setattr(settings, "trusted_proxies", "172.16.0.0/12")
    # Untrusted peer: header ignored.
    assert get_client_ip("198.51.100.7", "203.0.113.9") == "203.0.113.9"
    # Trusted proxy: right-most untrusted hop, not the client-supplied left one.
    assert get_client_ip("1.2.3.4, 198.51.100.7", "172.18.0.5") == "198.51.100.7"
    assert get_client_ip(None, "172.18.0.5") == "172.18.0.5"
    monkeypatch.setattr(settings, "trusted_proxies", "")
    assert get_client_ip("198.51.100.7", "172.18.0.5") == "172.18.0.5"
