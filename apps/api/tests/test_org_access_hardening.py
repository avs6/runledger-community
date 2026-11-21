"""
Org & Access hardening tests.

Covers:
  * password policy, temporary passwords, one-time token hashing, timing-safe verify
  * tenant role hierarchy (can_assign_tenant_role)
  * tenant-managed identity rule (is_tenant_managed_user)
  * workspace access resolution (has_workspace_access)
  * login brute-force guard (service + /auth/login 429)
  * password reset endpoints (no enumeration, invalid token)
  * SSO state single-use semantics
  * external identity linking rules (resolve_external_user)
  * LDAP empty-credential rejection
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from runledger_api.core.config import settings
from runledger_api.models.tenant import MemberStatusEnum, TenantRoleEnum
from runledger_api.services import login_guard
from runledger_api.services.passwords import (
    generate_temporary_password,
    hash_password,
    hash_token,
    new_token,
    password_policy_errors,
    validate_password_policy,
    verify_password,
)
from runledger_api.services.security import (
    authenticate_ldap,
    consume_auth_state,
    create_auth_state,
    resolve_external_user,
)
from runledger_api.services.sessions import (
    can_assign_tenant_role,
    has_workspace_access,
    is_tenant_managed_user,
    revoke_user_sessions,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _result(*, scalar: Any = None, rows: list[Any] | None = None) -> MagicMock:
    m = MagicMock()
    m.scalar_one_or_none.return_value = scalar
    m.scalars.return_value.all.return_value = rows or []
    return m


def _db(*results: MagicMock) -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.add = MagicMock()
    return db


def _user(**kw: Any) -> SimpleNamespace:
    base = {"id": uuid.uuid4(), "email": "u@example.com", "is_platform_admin": False}
    base.update(kw)
    return SimpleNamespace(**base)


def _tu(tenant_id: uuid.UUID, status: MemberStatusEnum, role: TenantRoleEnum) -> SimpleNamespace:
    return SimpleNamespace(tenant_id=tenant_id, status=status, role=role)


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def getdel(self, key: str) -> str | None:
        return self.store.pop(key, None)


# ── Passwords ─────────────────────────────────────────────────────────────────


def test_password_policy_rejects_weak_passwords() -> None:
    assert password_policy_errors("short1")
    assert any("digit" in e for e in password_policy_errors("onlylettersssss"))
    assert any("letter" in e for e in password_policy_errors("123456789012345"))
    assert any("common" in e for e in password_policy_errors("ChangeMe123!"))
    assert password_policy_errors("correct horse 42 battery") == []


def test_validate_password_policy_raises_422() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_password_policy("abc")
    assert exc.value.status_code == 422


def test_generated_temporary_password_meets_policy() -> None:
    for _ in range(20):
        pw = generate_temporary_password()
        assert len(pw) >= settings.password_min_length
        assert password_policy_errors(pw) == []


def test_new_token_stores_only_hash() -> None:
    raw, digest = new_token()
    assert raw != digest
    assert hash_token(raw) == digest
    assert len(digest) == 64


@pytest.mark.asyncio
async def test_verify_password_handles_missing_hash() -> None:
    hashed = hash_password("a-good-password-1")
    assert await verify_password("a-good-password-1", hashed) is True
    assert await verify_password("wrong-password-1", hashed) is False
    # Unknown user path: still runs bcrypt against a dummy hash, never succeeds.
    assert await verify_password("anything-1234", None) is False


# ── Role hierarchy ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("actor_role", "target_role", "new_role", "allowed"),
    [
        (TenantRoleEnum.org_admin, TenantRoleEnum.org_member, TenantRoleEnum.org_admin, True),
        (TenantRoleEnum.org_manager, TenantRoleEnum.org_member, TenantRoleEnum.org_auditor, True),
        (TenantRoleEnum.org_manager, TenantRoleEnum.org_member, TenantRoleEnum.org_admin, False),
        (TenantRoleEnum.org_manager, TenantRoleEnum.org_admin, TenantRoleEnum.org_member, False),
        (TenantRoleEnum.org_manager, TenantRoleEnum.org_admin, None, False),
        (TenantRoleEnum.org_member, TenantRoleEnum.org_member, TenantRoleEnum.org_auditor, False),
        (None, None, TenantRoleEnum.org_member, False),
    ],
)
def test_can_assign_tenant_role(
    actor_role: TenantRoleEnum | None,
    target_role: TenantRoleEnum | None,
    new_role: TenantRoleEnum | None,
    allowed: bool,
) -> None:
    assert (
        can_assign_tenant_role(
            actor_is_platform_admin=False,
            actor_role=actor_role,
            target_current_role=target_role,
            new_role=new_role,
        )
        is allowed
    )


def test_platform_admin_can_assign_any_role() -> None:
    assert can_assign_tenant_role(
        actor_is_platform_admin=True,
        actor_role=None,
        target_current_role=TenantRoleEnum.org_admin,
        new_role=TenantRoleEnum.org_admin,
    )


# ── Tenant-managed identity ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_platform_admin_is_never_tenant_managed() -> None:
    db = _db()
    assert await is_tenant_managed_user(db, _user(is_platform_admin=True), uuid.uuid4()) is False
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_sole_active_member_is_tenant_managed() -> None:
    tid = uuid.uuid4()
    db = _db(
        _result(rows=[_tu(tid, MemberStatusEnum.active, TenantRoleEnum.org_member)]),
        _result(scalar=None),  # no workspace memberships in other orgs
    )
    assert await is_tenant_managed_user(db, _user(), tid) is True


@pytest.mark.asyncio
async def test_invited_member_is_not_tenant_managed() -> None:
    tid = uuid.uuid4()
    db = _db(_result(rows=[_tu(tid, MemberStatusEnum.invited, TenantRoleEnum.org_member)]))
    assert await is_tenant_managed_user(db, _user(), tid) is False


@pytest.mark.asyncio
async def test_member_of_another_org_is_not_tenant_managed() -> None:
    tid = uuid.uuid4()
    db = _db(
        _result(
            rows=[
                _tu(tid, MemberStatusEnum.active, TenantRoleEnum.org_member),
                _tu(uuid.uuid4(), MemberStatusEnum.active, TenantRoleEnum.org_admin),
            ]
        )
    )
    assert await is_tenant_managed_user(db, _user(), tid) is False


@pytest.mark.asyncio
async def test_foreign_workspace_member_is_not_tenant_managed() -> None:
    tid = uuid.uuid4()
    db = _db(
        _result(rows=[_tu(tid, MemberStatusEnum.active, TenantRoleEnum.org_member)]),
        _result(scalar=uuid.uuid4()),
    )
    assert await is_tenant_managed_user(db, _user(), tid) is False


# ── Workspace access ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_suspended_org_membership_blocks_workspace_access() -> None:
    ws = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
    db = _db(
        _result(scalar=_tu(ws.tenant_id, MemberStatusEnum.suspended, TenantRoleEnum.org_admin))
    )
    assert await has_workspace_access(db, _user(), ws) is False


@pytest.mark.asyncio
async def test_active_org_level_role_grants_every_workspace() -> None:
    ws = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
    db = _db(_result(scalar=_tu(ws.tenant_id, MemberStatusEnum.active, TenantRoleEnum.org_auditor)))
    assert await has_workspace_access(db, _user(), ws) is True


@pytest.mark.asyncio
async def test_org_member_needs_active_workspace_membership() -> None:
    ws = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
    tu = _tu(ws.tenant_id, MemberStatusEnum.active, TenantRoleEnum.org_member)
    assert (
        await has_workspace_access(_db(_result(scalar=tu), _result(scalar=None)), _user(), ws)
        is False
    )
    member = SimpleNamespace(id=uuid.uuid4())
    assert (
        await has_workspace_access(_db(_result(scalar=tu), _result(scalar=member)), _user(), ws)
        is True
    )


@pytest.mark.asyncio
async def test_revoke_sessions_with_empty_workspace_list_is_noop() -> None:
    db = AsyncMock()
    db.get = AsyncMock(return_value=_user())
    assert await revoke_user_sessions(db, uuid.uuid4(), workspace_ids=[]) == 0
    db.execute.assert_not_called()


# ── Login guard ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_guard_blocks_after_account_limit() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=[str(settings.login_max_failures_per_account), "0"])
    with pytest.raises(HTTPException) as exc:
        await login_guard.assert_login_allowed(redis, "a@example.com", "10.0.0.1")
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_login_guard_fails_open_when_redis_down() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=ConnectionError("redis down"))
    await login_guard.assert_login_allowed(redis, "a@example.com", "10.0.0.1")


@pytest.mark.asyncio
async def test_record_failure_sets_window_on_first_failure() -> None:
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    await login_guard.record_login_failure(redis, "A@Example.com ", "10.0.0.1")
    keys = [c.args[0] for c in redis.expire.await_args_list]
    assert "rl:login:fail:acct:a@example.com" in keys
    assert "rl:login:fail:ip:10.0.0.1" in keys


@pytest.mark.asyncio
async def test_login_endpoint_returns_429_when_locked(
    client: AsyncClient, mock_redis_client: AsyncMock, mock_db_session: AsyncMock
) -> None:
    mock_redis_client.get = AsyncMock(return_value=str(settings.login_max_failures_per_account))
    resp = await client.post(
        "/auth/login", json={"email": "victim@example.com", "password": "whatever-123"}
    )
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
    mock_db_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_login_unknown_user_is_401_and_counted(
    client: AsyncClient, mock_redis_client: AsyncMock
) -> None:
    mock_redis_client.get = AsyncMock(return_value=None)
    resp = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever-123"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"
    assert mock_redis_client.incr.await_count >= 1


# ── Password reset ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_password_reset_request_does_not_enumerate(
    client: AsyncClient, mock_redis_client: AsyncMock
) -> None:
    mock_redis_client.get = AsyncMock(return_value=None)
    resp = await client.post("/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert resp.status_code == 202
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_password_reset_confirm_rejects_unknown_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": "brand-new-password-9"},
    )
    assert resp.status_code == 400


# ── SSO state ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sso_state_is_single_use() -> None:
    redis = _FakeRedis()
    provider_id = uuid.uuid4()
    flow = await create_auth_state(redis, "oidc", provider_id)
    stored = json.loads(next(iter(redis.store.values())))
    assert stored["nonce"] == flow.nonce

    consumed = await consume_auth_state(redis, "oidc", flow.state)
    assert consumed.provider_id == provider_id
    assert consumed.code_verifier == flow.code_verifier
    assert flow.code_challenge and flow.code_challenge != flow.code_verifier

    with pytest.raises(HTTPException) as exc:
        await consume_auth_state(redis, "oidc", flow.state)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_sso_state_kind_mismatch_is_rejected() -> None:
    redis = _FakeRedis()
    flow = await create_auth_state(redis, "oidc", uuid.uuid4())
    with pytest.raises(HTTPException):
        await consume_auth_state(redis, "oauth2", flow.state)


# ── External identity linking ─────────────────────────────────────────────────


def _provider(**kw: Any) -> SimpleNamespace:
    base = {"id": uuid.uuid4(), "tenant_id": uuid.uuid4(), "auto_provision": True}
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_existing_account_not_linked_without_verified_email() -> None:
    existing = _user(email="ceo@victim.com")
    db = _db(_result(scalar=None), _result(scalar=existing))
    with pytest.raises(HTTPException) as exc:
        await resolve_external_user(
            db,
            provider_type="oauth2",
            provider=_provider(),
            subject="attacker-sub",
            email="ceo@victim.com",
            full_name=None,
            email_trusted=False,
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_existing_account_outside_org_not_linked_even_if_verified() -> None:
    existing = _user(email="ceo@victim.com")
    provider = _provider()
    db = _db(
        _result(scalar=None),  # no linked identity
        _result(scalar=existing),  # email match
        _result(rows=[]),  # is_tenant_managed_user: no membership in provider org
    )
    with pytest.raises(HTTPException) as exc:
        await resolve_external_user(
            db,
            provider_type="oidc",
            provider=provider,
            subject="sub-1",
            email="ceo@victim.com",
            full_name=None,
            email_trusted=True,
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_linked_identity_signs_in_as_its_user() -> None:
    user = _user()
    ext = SimpleNamespace(user_id=user.id, last_login_at=None, external_email=None)
    db = _db(_result(scalar=ext))
    db.get = AsyncMock(return_value=user)
    got, ext_out = await resolve_external_user(
        db,
        provider_type="oidc",
        provider=_provider(),
        subject="sub-1",
        email="new@example.com",
        full_name=None,
        email_trusted=True,
    )
    assert got is user
    assert ext_out.external_email == "new@example.com"
    assert ext_out.last_login_at is not None


@pytest.mark.asyncio
async def test_unknown_identity_without_auto_provision_is_refused() -> None:
    db = _db(_result(scalar=None), _result(scalar=None))
    with pytest.raises(HTTPException) as exc:
        await resolve_external_user(
            db,
            provider_type="oidc",
            provider=_provider(auto_provision=False),
            subject="sub-2",
            email="fresh@example.com",
            full_name=None,
            email_trusted=True,
        )
    assert exc.value.status_code == 403


# ── LDAP ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(("username", "password"), [("alice", ""), ("", "secret")])
async def test_ldap_rejects_empty_credentials(username: str, password: str) -> None:
    with pytest.raises(HTTPException) as exc:
        await authenticate_ldap(SimpleNamespace(), username, password)  # type: ignore[arg-type]
    assert exc.value.status_code == 401
