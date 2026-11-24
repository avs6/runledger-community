"""The one tool-policy evaluator (review S-06, S-07, S-08).

Every place that decides whether a tool may run calls :func:`evaluate`:

* ``GET /tools/check/{tool}`` (SDK hot path)
* ``POST /policies/check`` (tool dimension)
* ``POST /tool-policies/simulate`` (dry run) and ``/tool-policies/simulate-impact``
* ``POST /mcp-registry/tools/call`` (governed MCP proxy)
* gateway preflight (``tools[]`` filtering, approval holds) and finalize
  (``tool_calls`` in the model response)

Semantics
---------
Policies are ordered by ``priority`` (ascending) then ``created_at``. The **first
policy that applies decides** (like the IP ACL): a narrow ``allow`` at priority 10
can exempt one tool from a ``block *`` at priority 1000. A policy applies when

1. its ``tool_name`` pattern matches (exact, ``*``, or an ``fnmatch`` glob such as
   ``github_*``; case-insensitive),
2. its scope covers the caller (``workspace``; ``access_group`` the caller's
   principal belongs to; ``api_key``; ``mcp_server``; ``search_tool``), and
3. its condition holds (see :data:`SUPPORTED_CONDITIONS`).

No matching policy means ``allow``. Identity (API key, access groups, end user) always
comes from the authenticated caller, never from the request body (review cd:S-04).

The tool registry (``/tools/registry``) is a catalog; the policy it shows is the
managed ``registry:<tool>`` ToolPolicy row. MCP permissions were folded into
ToolPolicy rows scoped to an ``mcp_server`` (migration ``governance_tool_policy``).
"""

from __future__ import annotations

import fnmatch
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.tool_policies import ToolPolicy

ACTIONS: tuple[str, ...] = ("allow", "audit", "require_approval", "block")
SCOPE_TYPES: tuple[str, ...] = ("workspace", "access_group", "api_key", "mcp_server", "search_tool")
SUPPORTED_CONDITIONS: tuple[str, ...] = (
    "all",
    "risk_score_gte",
    "tool_type",
    "end_user",
    "feature_tag",
    "context_equals",
    "argument_contains",
    "mcp_server",
)
# Prefix of the ToolPolicy rows the tool registry manages for its catalog entries.
REGISTRY_POLICY_PREFIX = "registry:"
REGISTRY_POLICY_PRIORITY = 50

_ACTION_ALIASES = {"deny": "block", "approve": "require_approval", "approval": "require_approval"}
_SCOPE_ALIASES = {"group": "access_group", "global": "workspace", "": "workspace"}


def normalize_action(action: str | None) -> str:
    value = (action or "allow").strip().lower()
    return _ACTION_ALIASES.get(value, value)


def normalize_scope(scope_type: str | None) -> str:
    value = (scope_type or "workspace").strip().lower()
    return _SCOPE_ALIASES.get(value, value)


@dataclass(frozen=True)
class PolicyRule:
    """An immutable snapshot of a ToolPolicy row (safe to cache across sessions)."""

    id: uuid.UUID | None
    name: str
    tool_name: str
    action: str
    condition_type: str
    condition_config: dict[str, Any]
    scope_type: str
    scope_id: uuid.UUID | None
    priority: int
    order: float = 0.0

    @classmethod
    def from_row(cls, row: ToolPolicy) -> PolicyRule:
        created = getattr(row, "created_at", None)
        return cls(
            id=row.id,
            name=row.name,
            tool_name=row.tool_name or "*",
            action=normalize_action(row.action),
            condition_type=row.condition_type or "all",
            condition_config=dict(row.condition_config or {}),
            scope_type=normalize_scope(row.scope_type),
            scope_id=row.scope_id,
            priority=int(row.priority if row.priority is not None else 100),
            order=created.timestamp() if created is not None else 0.0,
        )


@dataclass
class ToolCallContext:
    """Who is calling which tool, resolved from the authenticated caller."""

    tool_name: str
    tool_type: str | None = None
    risk_score: int | None = None
    end_user_id: str | None = None
    feature_tag: str | None = None
    api_key_id: uuid.UUID | None = None
    access_group_ids: frozenset[uuid.UUID] = frozenset()
    server_id: uuid.UUID | None = None
    search_tool_ids: frozenset[uuid.UUID] = frozenset()
    arguments: dict[str, Any] | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDecision:
    tool_name: str
    action: str = "allow"
    policy_id: uuid.UUID | None = None
    policy_name: str | None = None
    reason: str = "no matching policy"
    scope_type: str | None = None
    evaluated: int = 0
    approval_id: str | None = None

    @property
    def allowed(self) -> bool:
        return self.action in {"allow", "audit"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "action": self.action,
            "policy_id": str(self.policy_id) if self.policy_id else None,
            "policy_name": self.policy_name,
            "reason": self.reason,
            "scope_type": self.scope_type,
        }


def tool_name_matches(pattern: str, tool_name: str) -> bool:
    pat = (pattern or "*").strip().lower()
    name = (tool_name or "").strip().lower()
    if pat in {"*", name}:
        return True
    if any(ch in pat for ch in "*?["):
        return fnmatch.fnmatchcase(name, pat)
    return False


def scope_applies(rule: PolicyRule, ctx: ToolCallContext) -> bool:
    scope = rule.scope_type
    if scope == "workspace" or rule.scope_id is None:
        return True
    if scope == "access_group":
        return rule.scope_id in ctx.access_group_ids
    if scope == "api_key":
        return ctx.api_key_id is not None and rule.scope_id == ctx.api_key_id
    if scope == "mcp_server":
        return ctx.server_id is not None and rule.scope_id == ctx.server_id
    if scope == "search_tool":
        return rule.scope_id in ctx.search_tool_ids
    return False


def condition_holds(rule: PolicyRule, ctx: ToolCallContext) -> tuple[bool, str]:
    condition = rule.condition_type or "all"
    config = rule.condition_config or {}
    if condition == "all":
        return True, "applies to every call"
    if condition == "risk_score_gte":
        threshold = int(config.get("threshold", 0) or 0)
        return (ctx.risk_score or 0) >= threshold, f"risk_score>={threshold}"
    if condition == "tool_type":
        expected = str(config.get("tool_type", ""))
        return (ctx.tool_type or "") == expected, f"tool_type={expected}"
    if condition == "end_user":
        expected = str(config.get("end_user_id", ""))
        return (ctx.end_user_id or "") == expected, f"end_user_id={expected}"
    if condition == "feature_tag":
        expected = str(config.get("feature_tag", ""))
        return (ctx.feature_tag or "") == expected, f"feature_tag={expected}"
    if condition == "context_equals":
        key = str(config.get("key", ""))
        expected = config.get("value")
        return ctx.context.get(key) == expected, f"context.{key}={expected}"
    if condition == "argument_contains":
        needle = str(config.get("value", "")).lower()
        key = config.get("key")
        args = ctx.arguments or {}
        haystack = str(args.get(str(key), "")) if key else str(args)
        return bool(needle) and needle in haystack.lower(), f"arguments contain '{needle}'"
    if condition == "mcp_server":
        expected = str(config.get("server_id", ""))
        return (str(ctx.server_id) if ctx.server_id else "") == expected, f"mcp_server={expected}"
    return False, f"unsupported condition:{condition}"


def sort_rules(rules: list[PolicyRule]) -> list[PolicyRule]:
    return sorted(rules, key=lambda r: (r.priority, r.order, str(r.id or "")))


def evaluate(rules: list[PolicyRule], ctx: ToolCallContext) -> PolicyDecision:
    """First applicable policy (by priority) decides; no match means allow."""
    decision = PolicyDecision(tool_name=ctx.tool_name)
    for rule in sort_rules(rules):
        if not tool_name_matches(rule.tool_name, ctx.tool_name):
            continue
        if not scope_applies(rule, ctx):
            continue
        decision.evaluated += 1
        holds, why = condition_holds(rule, ctx)
        if not holds:
            continue
        decision.action = rule.action if rule.action in ACTIONS else "block"
        decision.policy_id = rule.id
        decision.policy_name = rule.name
        decision.scope_type = rule.scope_type
        decision.reason = f"policy '{rule.name}' ({why})"
        return decision
    return decision


def validate_policy_fields(
    *,
    action: str | None,
    condition_type: str | None,
    scope_type: str | None,
    scope_id: uuid.UUID | None,
    condition_config: dict[str, Any] | None = None,
) -> list[str]:
    """Return validation errors (empty when the policy can be enforced as written)."""
    errors: list[str] = []
    if action is not None and normalize_action(action) not in ACTIONS:
        errors.append(f"action must be one of {', '.join(ACTIONS)}")
    if condition_type is not None and condition_type not in SUPPORTED_CONDITIONS:
        errors.append(f"condition_type must be one of {', '.join(SUPPORTED_CONDITIONS)}")
    if scope_type is not None:
        scope = normalize_scope(scope_type)
        if scope not in SCOPE_TYPES:
            errors.append(f"scope_type must be one of {', '.join(SCOPE_TYPES)}")
        elif scope != "workspace" and scope_id is None:
            errors.append(f"scope_id is required for scope_type '{scope}'")
    if condition_type == "risk_score_gte":
        try:
            int((condition_config or {}).get("threshold", ""))
        except (TypeError, ValueError):
            errors.append("risk_score_gte needs an integer condition_config.threshold")
    return errors


# ── Loading (with a short in-process cache for the gateway hot path) ─────────

_CACHE_TTL_S = 5.0
_cache: dict[uuid.UUID, tuple[float, list[PolicyRule]]] = {}


def invalidate(workspace_id: uuid.UUID) -> None:
    """Drop the cached policy set after any ToolPolicy write."""
    _cache.pop(workspace_id, None)


async def load_rules(
    db: AsyncSession, workspace_id: uuid.UUID, *, use_cache: bool = True
) -> list[PolicyRule]:
    now = time.monotonic()
    if use_cache:
        hit = _cache.get(workspace_id)
        if hit is not None and now - hit[0] < _CACHE_TTL_S:
            return hit[1]
    rows = (
        (
            await db.execute(
                select(ToolPolicy).where(
                    ToolPolicy.workspace_id == workspace_id,
                    ToolPolicy.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    rules = sort_rules([PolicyRule.from_row(r) for r in rows])
    _cache[workspace_id] = (now, rules)
    return rules


async def caller_access_group_ids(
    db: AsyncSession, principal_user_id: uuid.UUID | None
) -> frozenset[uuid.UUID]:
    """Active access groups the authenticated principal belongs to."""
    if principal_user_id is None:
        return frozenset()
    from runledger_api.models.access_groups import AccessGroup, AccessGroupMember  # noqa: PLC0415

    rows = (
        await db.execute(
            select(AccessGroupMember.group_id)
            .join(AccessGroup, AccessGroup.id == AccessGroupMember.group_id)
            .where(
                AccessGroupMember.user_id == principal_user_id,
                AccessGroup.is_active.is_(True),
            )
        )
    ).scalars()
    return frozenset(rows)


async def search_tool_ids_for(
    db: AsyncSession, workspace_id: uuid.UUID, tool_name: str
) -> frozenset[uuid.UUID]:
    from sqlalchemy import func  # noqa: PLC0415

    from runledger_api.models.search_tools import SearchTool  # noqa: PLC0415

    rows = (
        await db.execute(
            select(SearchTool.id).where(
                SearchTool.workspace_id == workspace_id,
                func.lower(SearchTool.name) == tool_name.lower(),
            )
        )
    ).scalars()
    return frozenset(rows)


def tool_names_from_request(tools: list[dict[str, Any]] | None) -> list[str]:
    """Names of the tools in an OpenAI-style ``tools[]`` request field."""
    names: list[str] = []
    for tool in tools or []:
        if not isinstance(tool, dict):
            continue
        fn = tool.get("function") if isinstance(tool.get("function"), dict) else None
        name = (fn or {}).get("name") or tool.get("name")
        if name:
            names.append(str(name))
    return names


def tool_name_of_call(call: dict[str, Any]) -> str:
    fn = call.get("function") if isinstance(call.get("function"), dict) else {}
    return str((fn or {}).get("name") or call.get("name") or "")
