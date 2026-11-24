"""Postgres-backed checks for stream W1-A (secrets, audit chain, RLS, isolation).

These need a real, migrated Postgres, so they skip unless
``RUNLEDGER_TEST_DATABASE_URL`` points at one (a superuser URL; the tests create a
non-superuser ``rl_app_test`` role, because RLS never applies to superusers)::

    docker run -d --name rl-test-pg -e POSTGRES_USER=rl -e POSTGRES_PASSWORD=rltest \
        -e POSTGRES_DB=rl -p 127.0.0.1:55433:5432 postgres:16-alpine
    DATABASE_URL=postgresql+asyncpg://rl:rltest@127.0.0.1:55433/rl uv run alembic upgrade head
    RUNLEDGER_TEST_DATABASE_URL=postgresql+asyncpg://rl:rltest@127.0.0.1:55433/rl \
        uv run pytest tests/test_security_pg.py
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

PG_URL = os.getenv("RUNLEDGER_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not PG_URL, reason="needs a migrated Postgres (set RUNLEDGER_TEST_DATABASE_URL)"
)

APP_ROLE = "rl_app_test"
APP_PASSWORD = "rl_app_test_pw"
MARKER = "LEAKMARKER"


async def _engines() -> tuple[AsyncEngine, AsyncEngine]:
    admin = create_async_engine(PG_URL)
    async with admin.begin() as conn:
        await conn.execute(
            text(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}')"
                f" THEN CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{APP_PASSWORD}'"
                " NOSUPERUSER NOBYPASSRLS; END IF; END $$"
            )
        )
        await conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}"))
        await conn.execute(
            text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}"
            )
        )
        await conn.execute(text(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}"))
    app_url = make_url(PG_URL).set(username=APP_ROLE, password=APP_PASSWORD)
    return admin, create_async_engine(app_url)


async def _world(admin: AsyncEngine) -> dict[str, Any]:
    """Two orgs; org A has workspaces wa and wa2, org B has wb. Secrets live in wa."""
    from runledger_api.models.approvals import Approval
    from runledger_api.models.budgets import BudgetNotification
    from runledger_api.models.evaluators import Evaluator
    from runledger_api.models.search_tools import SearchTool
    from runledger_api.models.security import OIDCProvider
    from runledger_api.models.tenant import (
        ApiKey,
        Tenant,
        User,
        Workspace,
        WorkspaceRoleEnum,
        WorkspaceUser,
    )
    from runledger_api.services.audit import emit_audit_event
    from runledger_api.services.auth import _hmac_hash

    w: dict[str, Any] = {}
    suffix = uuid.uuid4().hex[:8]
    maker = async_sessionmaker(admin, expire_on_commit=False)
    async with maker() as db:
        ta = Tenant(id=uuid.uuid4(), slug=f"ta-{suffix}", name="Org A")
        tb = Tenant(id=uuid.uuid4(), slug=f"tb-{suffix}", name="Org B")
        db.add_all([ta, tb])
        await db.flush()
        wa = Workspace(id=uuid.uuid4(), tenant_id=ta.id, name=f"wa-{suffix}")
        wa2 = Workspace(id=uuid.uuid4(), tenant_id=ta.id, name=f"wa2-{suffix}")
        wb = Workspace(id=uuid.uuid4(), tenant_id=tb.id, name=f"wb-{suffix}")
        db.add_all([wa, wa2, wb])
        await db.flush()
        for name, ws in (("ua", wa), ("ua2", wa2), ("ub", wb)):
            user = User(id=uuid.uuid4(), email=f"{name}-{suffix}@example.test", password_hash="x")
            db.add(user)
            await db.flush()
            db.add(
                WorkspaceUser(
                    workspace_id=ws.id, user_id=user.id, role=WorkspaceRoleEnum.workspace_admin
                )
            )
            raw = f"rl_test_{name}_{uuid.uuid4().hex}"
            db.add(
                ApiKey(
                    id=uuid.uuid4(),
                    workspace_id=ws.id,
                    key_hash=_hmac_hash(raw),
                    key_prefix=raw[:24],
                    is_session=True,
                    user_id=user.id,
                    created_by=user.email,
                )
            )
            w[f"key_{name}"] = raw
        tool = SearchTool(
            id=uuid.uuid4(),
            workspace_id=wa.id,
            name=f"{MARKER}-search",
            tool_type="web",
            auth_type="bearer",
            auth_config={"token": "search-secret-1", "header_name": "X-Key"},
        )
        evaluator = Evaluator(
            id=uuid.uuid4(),
            workspace_id=wa.id,
            name=f"{MARKER}-judge",
            type="llm_judge",
            config={"model": "m", "api_key": "eval-secret"},
        )
        notification = BudgetNotification(
            workspace_id=wa.id,
            channel="slack",
            destination_url="https://hooks.slack.com/services/T0/B0/notify-secret",
            events=["budget.breach"],
            is_active=True,
        )
        oidc = OIDCProvider(
            id=uuid.uuid4(),
            workspace_id=wa.id,
            tenant_id=ta.id,
            name=f"{MARKER}-okta",
            issuer_url="https://idp.example.test",
            client_secret_encrypted="oidc-secret",
        )
        approval = Approval(
            workspace_id=wa.id, request_type="custom", request={"note": MARKER}, status="pending"
        )
        db.add_all([tool, evaluator, notification, oidc, approval])
        await db.flush()
        await emit_audit_event(db, wa.id, "test.seeded", target_type="test", target_id=MARKER)
        await db.commit()
        w.update(
            ta=ta.id,
            tb=tb.id,
            wa=wa.id,
            wa2=wa2.id,
            wb=wb.id,
            tool=tool.id,
            evaluator=evaluator.id,
            notification=notification.id,
            oidc=oidc.id,
            approval=approval.id,
        )
    return w


@pytest.fixture
async def env() -> AsyncGenerator[tuple[AsyncEngine, AsyncEngine, dict[str, Any]]]:
    admin, app_engine = await _engines()
    world = await _world(admin)
    yield admin, app_engine, world
    await app_engine.dispose()
    await admin.dispose()


async def test_secrets_encrypted_at_rest_and_tracked(env: Any) -> None:
    from runledger_api.models.audit import AuditEvent
    from runledger_api.models.search_tools import SearchTool
    from runledger_api.models.secrets import SecretRecord
    from runledger_api.models.security import OIDCProvider

    admin, _app, w = env
    async with admin.connect() as conn:
        raw_cfg = (
            await conn.execute(
                text("SELECT auth_config->>'token' FROM search_tools WHERE id=:i"), {"i": w["tool"]}
            )
        ).scalar_one()
        raw_oidc = (
            await conn.execute(
                text("SELECT client_secret_encrypted FROM oidc_providers WHERE id=:i"),
                {"i": w["oidc"]},
            )
        ).scalar_one()
        raw_url = (
            await conn.execute(
                text("SELECT destination_url FROM budget_notifications WHERE id=:i"),
                {"i": w["notification"]},
            )
        ).scalar_one()
    for raw in (raw_cfg, raw_oidc, raw_url):
        assert raw.startswith("rlsec:v1:"), raw
        assert "secret" not in raw
    async with AsyncSession(admin) as db:
        tool = await db.get(SearchTool, w["tool"])
        assert tool is not None and tool.auth_config["token"] == "search-secret-1"
        oidc = await db.get(OIDCProvider, w["oidc"])
        assert oidc is not None and oidc.client_secret_encrypted == "oidc-secret"
        kinds = set(
            (
                await db.execute(
                    select(SecretRecord.kind).where(SecretRecord.workspace_id == w["wa"])
                )
            )
            .scalars()
            .all()
        )
        assert {
            "search_provider_auth",
            "evaluator_api_key",
            "notification_webhook",
            "oidc_client_secret",
        } <= kinds
        created = (
            (
                await db.execute(
                    select(AuditEvent).where(
                        AuditEvent.workspace_id == w["wa"], AuditEvent.action == "secret.created"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(created) >= 4
        assert all(e.hash and e.seq for e in created)


async def test_rotate_and_rewrap_update_inventory_and_audit(env: Any) -> None:
    from runledger_api.models.audit import AuditEvent
    from runledger_api.models.search_tools import SearchTool
    from runledger_api.services import secrets_inventory

    admin, _app, w = env
    rid = secrets_inventory.secret_id("search_tools", w["tool"], "auth_config")
    async with AsyncSession(admin, expire_on_commit=False) as db:
        record = await secrets_inventory.get_record(db, w["wa"], rid)
        assert record is not None and record.rotation_count == 0
        old_fp = record.fingerprint
        await secrets_inventory.rotate_secret(db, record, value="search-secret-2", values=None)
        await db.commit()
        assert record.rotation_count == 1 and record.fingerprint != old_fp
        tool = await db.get(SearchTool, w["tool"])
        assert tool is not None and tool.auth_config["token"] == "search-secret-2"
        # Writing the same value back (a masked field kept) is not a rotation.
        tool.auth_config = dict(tool.auth_config)
        await db.commit()
        assert record.rotation_count == 1
        timeline = (
            (
                await db.execute(
                    select(AuditEvent.action).where(
                        AuditEvent.target_type == "secret", AuditEvent.target_id == str(rid)
                    )
                )
            )
            .scalars()
            .all()
        )
        assert sorted(timeline) == ["secret.created", "secret.rotated"]
        # Already on the primary key: re-wrap is a no-op.
        assert await secrets_inventory.rewrap_secret(db, record) is False


async def test_audit_chain_verifies_and_detects_tampering(env: Any) -> None:
    from runledger_api.services.audit import chain_key_for, verify_chain

    admin, _app, w = env
    key = chain_key_for(w["wa"], None)
    async with AsyncSession(admin) as db:
        ok = await verify_chain(db, key)
        assert ok.ok and ok.checked >= 5, ok
    async with admin.begin() as conn:
        await conn.execute(
            text("UPDATE audit_events SET target_id='tampered' WHERE chain_key=:k AND seq=2"),
            {"k": key},
        )
    async with AsyncSession(admin) as db:
        bad = await verify_chain(db, key)
        assert not bad.ok and bad.first_bad_seq == 2 and bad.reason


async def test_rls_isolates_tenants_and_pinned_workspaces(env: Any) -> None:
    from runledger_api.models.search_tools import SearchTool
    from runledger_api.services.security import apply_tenant_context

    _admin, app_engine, w = env
    maker = async_sessionmaker(app_engine, expire_on_commit=False)

    async with maker() as db:  # org B session: A's rows do not exist
        await apply_tenant_context(db, _Ws(w["wb"], w["tb"]), pin_workspace=False)
        assert await db.get(SearchTool, w["tool"]) is None
        rows = (await db.execute(select(SearchTool.workspace_id))).scalars().all()
        assert w["wa"] not in rows
        await db.commit()  # the context survives a commit (re-applied on begin)
        assert (
            await db.execute(select(SearchTool).where(SearchTool.id == w["tool"]))
        ).scalar_one_or_none() is None

    async with maker() as db:  # org B cannot write into org A's workspace
        await apply_tenant_context(db, _Ws(w["wb"], w["tb"]), pin_workspace=False)
        db.add(SearchTool(id=uuid.uuid4(), workspace_id=w["wa"], name="x", tool_type="web"))
        with pytest.raises(Exception, match="row-level security"):
            await db.flush()

    async with maker() as db:  # a workload key pinned to wa2 cannot see wa (same org)
        await apply_tenant_context(db, _Ws(w["wa2"], w["ta"]), pin_workspace=True)
        assert await db.get(SearchTool, w["tool"]) is None

    async with maker() as db:  # org A sees its own row
        await apply_tenant_context(db, _Ws(w["wa"], w["ta"]), pin_workspace=False)
        assert await db.get(SearchTool, w["tool"]) is not None


class _Ws:
    def __init__(self, id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        self.id = id
        self.tenant_id = tenant_id


async def test_cross_workspace_fuzz(env: Any) -> None:
    """Every GET route with one UUID path parameter, called with another workspace's
    key and workspace A's object ids, must not return workspace A's data."""
    from fastapi.routing import APIRoute
    from httpx import ASGITransport, AsyncClient
    from runledger_api.core.db import get_db
    from runledger_api.core.redis import get_redis
    from runledger_api.main import app
    from runledger_api.models.audit import AuditEvent
    from runledger_api.services import secrets_inventory

    admin, app_engine, w = env
    maker = async_sessionmaker(app_engine, expire_on_commit=False)

    async def override_db() -> AsyncGenerator[AsyncSession]:
        async with maker() as session:
            yield session

    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.get = AsyncMock(return_value=None)
    redis.ttl = AsyncMock(return_value=60)

    async def override_redis() -> AsyncMock:
        return redis

    async with AsyncSession(admin) as db:
        audit_id = (
            await db.execute(
                select(AuditEvent.id).where(AuditEvent.workspace_id == w["wa"]).limit(1)
            )
        ).scalar_one()
    foreign_ids = [
        w["tool"],
        w["evaluator"],
        w["notification"],
        w["oidc"],
        w["approval"],
        audit_id,
        secrets_inventory.secret_id("search_tools", w["tool"], "auth_config"),
    ]

    routes = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or "GET" not in route.methods:
            continue
        params = route.dependant.path_params
        if len(params) != 1 or params[0].field_info.annotation is not uuid.UUID:
            continue
        if any(s in route.path for s in ("stream", "/live", "sse", "/events/tail")):
            continue
        routes.append((route.path_format, params[0].name))
    assert len(routes) > 40, routes

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = override_redis
    leaks: list[str] = []
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            # Positive control: the owner can read its own secret record.
            own = await client.get(
                f"/security/secrets/{foreign_ids[-1]}",
                headers={"Authorization": f"Bearer {w['key_ua']}"},
            )
            assert own.status_code == 200, own.text
            for key_name in ("key_ub", "key_ua2"):
                headers = {"Authorization": f"Bearer {w[key_name]}"}
                for path, name in routes:
                    for fid in foreign_ids:
                        url = path.replace("{" + name + "}", str(fid))
                        try:
                            resp = await client.get(url, headers=headers, timeout=10)
                        except Exception:  # noqa: BLE001,S112 — handler errors are not leaks
                            continue
                        body = resp.text
                        if resp.status_code < 300 and (MARKER in body or str(w["wa"]) in body):
                            leaks.append(f"{key_name} GET {url} -> {resp.status_code}")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_redis, None)
    assert not leaks, "\n".join(leaks)
