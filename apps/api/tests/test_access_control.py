"""
Access control across the API surface.

- Route inventory guard: every route is authenticated, and every write route
  enforces a role, unless it is on an explicit, reviewed allowlist. New endpoints
  that forget auth fail this test.
- ``require_workspace_writer``: workload keys write; viewers and read-only org roles
  get 403.
- Gateway credentials pass the same checks as the API (suspended org/workspace,
  stale dashboard sessions).
- Secrets stored by features (prompt GitHub token) are encrypted at rest.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from runledger_api.core import deps
from runledger_api.main import app
from runledger_api.models.tenant import (
    TenantRoleEnum,
    WorkspaceRoleEnum,
    WorkspaceStatusEnum,
)

# ── Route inventory ───────────────────────────────────────────────────────────

_AUTH_DEPS = {
    "get_current_workspace",
    "get_current_api_key",
    "require_user",
    "require_admin",
}
_ROLE_DEPS = {
    "require_workspace_writer",
    "require_workspace_admin",
    "require_org_admin",
    "require_platform_admin",
    "require_member",
    "require_admin",
    "require_user",
    "_dep",  # require_billing_access / require_audit_access
}

# Routes that authenticate inside the handler or are intentionally public.
_PUBLIC = {
    "/health",
    "/health/live",
    "/health/ready",
    "/metrics",  # bearer METRICS_TOKEN checked in the handler
    "/reference",
    "/ingest/v1/signed",  # HMAC signature
    "/gateway/runtime/events/signed",  # HMAC signature
    "/gateway/chat/completions",  # legacy, returns 410
    "/gateway/passthrough/{slug}",  # API key checked in the handler
    "/gateway/passthrough/{slug}/{upstream_path:path}",
    "/auth/login",
    "/auth/verify-email",
    "/auth/resend-verification",
    "/auth/password-reset/request",
    "/auth/password-reset/confirm",
    "/auth/providers",
    "/auth/oidc/{provider_id}/authorize",
    "/auth/oidc/callback",
    "/auth/oauth2/{provider_id}/authorize",
    "/auth/oauth2/callback",
    "/auth/ldap/login",
    "/auth/unsubscribe",
}

# Write routes any workspace credential may call: read-only computations
# (simulations, searches, policy checks), sign-out, and approval requests.
_OPEN_WRITES = {
    ("POST", "/auth/logout"),
    ("POST", "/approvals"),
    ("POST", "/policies/check"),
    ("POST", "/policies/simulate-finops"),
    ("POST", "/analytics/simulate-optimization"),
    ("POST", "/tags/auto-rules/simulate"),
    ("POST", "/tool-policies/simulate"),
    ("POST", "/agents/{agent_id}/memory/search"),
    ("POST", "/vector-stores/{collection_id}/search-test"),
}


def _dep_names(dependant: Any, acc: set[str]) -> set[str]:
    for sub in dependant.dependencies:
        if sub.call is not None:
            acc.add(getattr(sub.call, "__name__", ""))
        _dep_names(sub, acc)
    return acc


def _routes() -> list[tuple[APIRoute, set[str]]]:
    return [(r, _dep_names(r.dependant, set())) for r in app.routes if isinstance(r, APIRoute)]


def test_every_route_is_authenticated_or_explicitly_public() -> None:
    missing = [
        f"{sorted(r.methods)} {r.path}"
        for r, names in _routes()
        if not names & (_AUTH_DEPS | _ROLE_DEPS) and r.path not in _PUBLIC
    ]
    assert missing == [], f"Routes without authentication: {missing}"


def test_every_write_route_enforces_a_role() -> None:
    missing = []
    for r, names in _routes():
        if r.path in _PUBLIC:
            continue
        for method in r.methods & {"POST", "PUT", "PATCH", "DELETE"}:
            if (method, r.path) in _OPEN_WRITES:
                continue
            if not names & _ROLE_DEPS:
                missing.append(f"{method} {r.path}")
    assert missing == [], f"Write routes without a role check: {missing}"


def test_unsigned_ingest_webhook_is_gone() -> None:
    assert not any(r.path == "/ingest/v1/webhook" for r, _ in _routes())


def test_no_duplicated_analytics_prefix() -> None:
    assert not [r.path for r, _ in _routes() if r.path.startswith("/analytics/analytics/")]


def test_governance_config_writes_need_workspace_admin() -> None:
    admin_only = {
        ("POST", "/guardrails"),
        ("POST", "/gateway/flywheel/run"),
        ("POST", "/gateway/flywheel/recommendations/{rec_id}/dismiss"),
        ("POST", "/prompts/github-config"),
        ("PUT", "/prompts/github-config"),
        ("POST", "/intelligence/alerts/{rule_id}/enable-adaptive"),
    }
    found = set()
    for r, names in _routes():
        for method in r.methods:
            if (method, r.path) in admin_only:
                assert "require_workspace_admin" in names, (method, r.path)
                found.add((method, r.path))
    assert found == admin_only


def test_flywheel_route_rewrites_need_org_admin() -> None:
    """Apply, rollback and settings rewrite routes: org admin only (review G-03)."""
    org_only = {
        ("PUT", "/gateway/flywheel/settings"),
        ("POST", "/gateway/flywheel/recommendations/{rec_id}/apply"),
        ("POST", "/gateway/flywheel/recommendations/{rec_id}/rollback"),
    }
    found = set()
    for r, names in _routes():
        for method in r.methods:
            if (method, r.path) in org_only:
                assert "require_org_admin" in names, (method, r.path)
                found.add((method, r.path))
    assert found == org_only


# ── require_workspace_writer ──────────────────────────────────────────────────

WS = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())


def _request(api_key: Any, user: Any = None) -> Any:
    return SimpleNamespace(state=SimpleNamespace(api_key=api_key, session_user=user))


def _user(**kw: Any) -> Any:
    return SimpleNamespace(id=uuid.uuid4(), is_platform_admin=False, is_active=True, **kw)


async def _writer(api_key: Any, user: Any, tenant_role: Any = None, ws_role: Any = None) -> Any:
    tu = SimpleNamespace(role=tenant_role) if tenant_role else None
    wu = SimpleNamespace(role=ws_role) if ws_role else None
    with (
        patch.object(deps, "_get_tenant_user", AsyncMock(return_value=tu)),
        patch.object(deps, "_get_workspace_user", AsyncMock(return_value=wu)),
    ):
        return await deps.require_workspace_writer(_request(api_key, user), WS, AsyncMock())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_workload_key_may_write() -> None:
    assert await _writer(SimpleNamespace(is_session=False), None) is WS


@pytest.mark.asyncio
async def test_oidc_workload_token_may_write() -> None:
    assert await _writer(None, None) is WS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ws_role",
    [
        WorkspaceRoleEnum.workspace_admin,
        WorkspaceRoleEnum.workspace_editor,
        WorkspaceRoleEnum.workspace_contributor,
        WorkspaceRoleEnum.member,
    ],
)
async def test_writable_workspace_roles_may_write(ws_role: WorkspaceRoleEnum) -> None:
    session = SimpleNamespace(is_session=True)
    assert await _writer(session, _user(), TenantRoleEnum.org_member, ws_role) is WS


@pytest.mark.asyncio
async def test_viewer_is_read_only() -> None:
    with pytest.raises(HTTPException) as exc:
        await _writer(
            SimpleNamespace(is_session=True),
            _user(),
            TenantRoleEnum.org_member,
            WorkspaceRoleEnum.viewer,
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [TenantRoleEnum.org_auditor, TenantRoleEnum.org_billing_admin])
async def test_read_only_org_roles_cannot_write(role: TenantRoleEnum) -> None:
    with pytest.raises(HTTPException) as exc:
        await _writer(SimpleNamespace(is_session=True), _user(), role, None)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [TenantRoleEnum.org_admin, TenantRoleEnum.org_manager])
async def test_org_admins_may_write_without_workspace_role(role: TenantRoleEnum) -> None:
    assert await _writer(SimpleNamespace(is_session=True), _user(), role, None) is WS


@pytest.mark.asyncio
async def test_platform_admin_may_write() -> None:
    admin = _user()
    admin.is_platform_admin = True
    assert await _writer(SimpleNamespace(is_session=True), admin) is WS


# ── authorize_api_key (API + gateway) ─────────────────────────────────────────


def _db_returning(workspace: Any) -> Any:
    db = AsyncMock()
    result = SimpleNamespace(scalar_one_or_none=lambda: workspace)
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_authorize_api_key_rejects_suspended_workspace() -> None:
    workspace = SimpleNamespace(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), status=WorkspaceStatusEnum.suspended
    )
    key = SimpleNamespace(workspace_id=workspace.id, is_session=False)
    with pytest.raises(HTTPException) as exc:
        await deps.authorize_api_key(key, _db_returning(workspace))  # type: ignore[arg-type]
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_authorize_api_key_rejects_stale_session() -> None:
    workspace = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4(), status="active")
    key = SimpleNamespace(workspace_id=workspace.id, is_session=True)
    owner = _user()
    with (
        patch.object(deps, "_session_owner", AsyncMock(return_value=owner)),
        patch.object(deps, "has_workspace_access", AsyncMock(return_value=False)),
        pytest.raises(HTTPException) as exc,
    ):
        await deps.authorize_api_key(key, _db_returning(workspace))  # type: ignore[arg-type]
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_gateway_resolver_applies_api_rules() -> None:
    from runledger_api.routers import gateway_shared

    key = SimpleNamespace(workspace_id=uuid.uuid4(), is_session=False)
    with (
        patch.object(gateway_shared, "verify_api_key", AsyncMock(return_value=key)),
        patch.object(
            deps,
            "authorize_api_key",
            AsyncMock(side_effect=HTTPException(403, "This organization is suspended")),
        ),
        pytest.raises(HTTPException) as exc,
    ):
        await gateway_shared._resolve_gateway_bearer_token("rl_live_x", AsyncMock())
    assert exc.value.status_code == 403


# ── Secrets at rest ───────────────────────────────────────────────────────────


def test_prompt_github_token_is_encrypted_and_legacy_values_still_read() -> None:
    import base64

    from runledger_api.routers.prompts import _decrypt_token
    from runledger_api.services.kafka_export import encrypt_secret_value

    stored = encrypt_secret_value("ghp_secret")
    assert stored.startswith("enc::") and "ghp_secret" not in stored
    assert _decrypt_token(stored) == "ghp_secret"
    legacy = "b64:" + base64.b64encode(b"ghp_old").decode()
    assert _decrypt_token(legacy) == "ghp_old"


# ── Internal service token ────────────────────────────────────────────────────


def test_internal_service_headers_fall_back_to_admin_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from runledger_api.core.config import settings

    monkeypatch.setattr(settings, "internal_service_token", "")
    monkeypatch.setattr(settings, "admin_secret", "adm")
    assert settings.internal_service_headers == {"x-internal-token": "adm"}
    monkeypatch.setattr(settings, "internal_service_token", "svc")
    assert settings.internal_service_headers == {"x-internal-token": "svc"}


def test_api_clients_of_internal_services_send_the_token() -> None:
    import inspect

    from runledger_api.services import (
        context_compiler,
        flywheel,
        intelligent_router,
        semantic_cache,
    )
    from runledger_api.workers import consolidation

    for module in (semantic_cache, context_compiler, flywheel, intelligent_router, consolidation):
        assert "internal_service_headers" in inspect.getsource(module), module.__name__


# ── Audit review follow-ups (I-02, I-03/P-02, I-04, G-04, A-12) ───────────────


@pytest.mark.asyncio
async def test_pipeline_drops_events_for_another_workspaces_run() -> None:
    from runledger_api.workers.pipeline import _event_run_in_workspace

    mine, theirs = str(uuid.uuid4()), str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    def _session(owner: Any) -> Any:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: owner))
        return session

    cache: dict[str, bool] = {}
    event = {"event_type": "run_end", "run_id": run_id}
    assert await _event_run_in_workspace(_session(uuid.UUID(theirs)), mine, event, cache) is False
    cache.clear()
    assert await _event_run_in_workspace(_session(uuid.UUID(mine)), mine, event, cache) is True
    cache.clear()
    assert await _event_run_in_workspace(_session(None), mine, event, cache) is False
    # run_start creates the run; ON CONFLICT DO NOTHING protects existing runs.
    start = {"event_type": "run_start", "run_id": run_id}
    assert await _event_run_in_workspace(_session(uuid.UUID(theirs)), mine, start, {}) is True


def _route_deps(path: str, method: str) -> set[str]:
    for r, names in _routes():
        if r.path == path and method in r.methods:
            return names
    raise AssertionError(f"route not found: {method} {path}")


def test_backups_and_global_pricing_are_platform_admin_only() -> None:
    for method, path in [
        ("GET", "/settings/backups/config"),
        ("PUT", "/settings/backups/config"),
        ("POST", "/settings/backups/run"),
        ("POST", "/settings/backups/restore-drill"),
        ("GET", "/settings/backups/history"),
        ("POST", "/providers/pricing/import"),
    ]:
        names = _route_deps(path, method)
        assert "require_platform_admin" in names, (method, path)


def test_billing_and_audit_reads_admit_billing_and_auditor_roles() -> None:
    # require_billing_access / require_audit_access are both built by
    # _org_role_or_workspace_admin, whose dependency function is named _dep.
    for path in ("/billing/periods", "/billing/chargeback-report", "/audit/events"):
        names = _route_deps(path, "GET")
        assert "_dep" in names and "require_workspace_admin" not in names, path


@pytest.mark.asyncio
async def test_billing_access_allows_billing_admin_and_audit_access_allows_auditor() -> None:
    async def _check(dep: Any, role: Any) -> bool:
        with (
            patch.object(
                deps, "_get_tenant_user", AsyncMock(return_value=SimpleNamespace(role=role))
            ),
            patch.object(deps, "_get_workspace_user", AsyncMock(return_value=None)),
        ):
            try:
                await dep((WS, _user()), AsyncMock())
                return True
            except HTTPException:
                return False

    assert await _check(deps.require_billing_access, TenantRoleEnum.org_billing_admin)
    assert not await _check(deps.require_billing_access, TenantRoleEnum.org_auditor)
    assert await _check(deps.require_audit_access, TenantRoleEnum.org_auditor)
    assert not await _check(deps.require_audit_access, TenantRoleEnum.org_billing_admin)


@pytest.mark.asyncio
async def test_backup_secret_is_encrypted_and_never_returned() -> None:
    from runledger_api.routers.settings import _backup_config_response
    from runledger_api.services import backup_ops

    stored: dict[str, Any] = {}

    class _Cfg(SimpleNamespace):
        pass

    db = AsyncMock()
    with patch.object(backup_ops, "get_backup_config", AsyncMock(return_value=None)):
        db.add = lambda obj: stored.setdefault("obj", obj)
        config = await backup_ops.upsert_backup_config(
            db, uuid.uuid4(), {"bucket": "b", "secret_access_key": "s3cr3t"}
        )
    assert config.secret_access_key.startswith("enc::")
    assert "s3cr3t" not in config.secret_access_key
    env = backup_ops._command_env(config)
    assert env["RUNLEDGER_BACKUP_SECRET_ACCESS_KEY"] == "s3cr3t"

    from datetime import UTC, datetime

    now = datetime.now(UTC)
    row = _Cfg(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        provider="s3",
        bucket="b",
        prefix=None,
        region=None,
        endpoint_url=None,
        access_key_id="a",
        secret_access_key=config.secret_access_key,
        force_path_style=True,
        schedule_enabled=False,
        cadence="daily",
        run_hour_utc=2,
        retention_days=30,
        include_memory_db=True,
        include_qdrant=False,
        include_kuzu=True,
        include_skills=True,
        encryption_mode="server_side",
        last_verified_at=None,
        created_at=now,
        updated_at=now,
    )
    response = _backup_config_response(row)
    assert response.secret_access_key is None
    assert response.has_secret_access_key is True

    # Blank secret on update keeps the stored one.
    existing = SimpleNamespace(secret_access_key=config.secret_access_key, bucket="b")
    with patch.object(backup_ops, "get_backup_config", AsyncMock(return_value=existing)):
        await backup_ops.upsert_backup_config(
            db, uuid.uuid4(), {"bucket": "c", "secret_access_key": ""}
        )
    assert existing.secret_access_key == config.secret_access_key
    assert existing.bucket == "c"
