"""One role matrix for gateway administration (review G-17).

Every gateway admin router takes its dependency from this table, and
``GET /gateway/role-matrix`` returns the same table plus the caller's effective
capabilities, so the UI shows exactly the controls the API will accept.

Levels, lowest first:

  viewer < member < workspace_admin < org_admin < platform_admin

``member`` reads also accept workload API keys (SDK, automation). Anything at
``workspace_admin`` or above needs a dashboard user session.

Why the split:
  * Routes, routing groups, policies, pass-through endpoints and flywheel apply change
    where traffic goes and which credentials it uses, so they need an org admin.
  * Budget tiers, response cache profiles and guardrails are workspace-scoped controls,
    so a workspace admin manages them.
  * Workspace pricing rows need an org admin; the global catalog needs a platform admin.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core import deps
from runledger_api.models.tenant import WorkspaceRoleEnum

Level = Literal["viewer", "member", "workspace_admin", "org_admin", "platform_admin"]

LEVELS: tuple[Level, ...] = ("viewer", "member", "workspace_admin", "org_admin", "platform_admin")

GATEWAY_ROLE_MATRIX: dict[str, dict[str, Level]] = {
    # Routes, routing groups and routing policies (incl. promote / rollout / rollback).
    "routes": {"read": "workspace_admin", "write": "org_admin"},
    "pass_through": {"read": "org_admin", "write": "org_admin"},
    # Flywheel: run analysis and dismiss are workspace-admin; applying a recommendation,
    # rolling one back and changing settings (which can turn on auto-apply) rewrite routes.
    "flywheel": {"read": "member", "write": "workspace_admin", "apply": "org_admin"},
    "budget_tiers": {"read": "member", "write": "workspace_admin"},
    "response_cache": {"read": "member", "write": "workspace_admin"},
    "pricing": {"read": "member", "write": "org_admin", "global": "platform_admin"},
    "guardrails": {"read": "member", "write": "workspace_admin"},
}

_DEPENDENCY_FOR_LEVEL: dict[Level, Callable[..., Any]] = {
    "viewer": deps.get_current_workspace,
    "member": deps.get_current_workspace,
    "workspace_admin": deps.require_workspace_admin,
    "org_admin": deps.require_org_admin,
    "platform_admin": deps.require_platform_admin,
}


def gateway_role(resource: str, action: str) -> Callable[..., Any]:
    """The FastAPI dependency that enforces ``GATEWAY_ROLE_MATRIX[resource][action]``."""
    return _DEPENDENCY_FOR_LEVEL[GATEWAY_ROLE_MATRIX[resource][action]]


def level_allows(have: Level | Literal["workload"], need: Level) -> bool:
    """Whether a caller at ``have`` passes a check for ``need``."""
    if have == "workload":
        return need in ("viewer", "member")
    return LEVELS.index(have) >= LEVELS.index(need)


async def caller_level(
    request: Request, workspace: Any, db: AsyncSession
) -> Level | Literal["workload"]:
    """The caller's effective level in ``workspace`` (``workload`` for non-session keys)."""
    api_key = getattr(request.state, "api_key", None)
    if api_key is None or not getattr(api_key, "is_session", False):
        return "workload"
    user = getattr(request.state, "session_user", None) or await deps._session_owner(api_key, db)
    if user is None:
        return "viewer"
    if user.is_platform_admin:
        return "platform_admin"
    tu = await deps._get_tenant_user(user.id, workspace.tenant_id, db)
    if tu is not None and tu.role in deps._ORG_ADMIN_ROLES:
        return "org_admin"
    wu = await deps._get_workspace_user(user.id, workspace.id, db)
    if wu is None:
        return "viewer"
    if wu.role == WorkspaceRoleEnum.workspace_admin:
        return "workspace_admin"
    if wu.role == WorkspaceRoleEnum.viewer:
        return "viewer"
    return "member"


def capabilities(level: Level | Literal["workload"]) -> dict[str, dict[str, bool]]:
    """``{resource: {action: allowed}}`` for a caller at ``level``."""
    return {
        resource: {action: level_allows(level, need) for action, need in actions.items()}
        for resource, actions in GATEWAY_ROLE_MATRIX.items()
    }
