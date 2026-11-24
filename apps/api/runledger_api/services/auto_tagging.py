"""Auto-tagging rules, applied at ingest and in the gateway (review S-19).

One matcher serves ``POST /tags/auto-rules/simulate``, the ingest pipeline
(``run_start``) and gateway runs (finalize), so a rule that simulates a tag also
writes it. Tags land in ``agent_runs.run_metadata["auto_tags"]`` as ``{key: value}``.

Fields a rule can match: ``feature_tag``, ``end_user_id``, ``session_id``, ``intent``,
``model``, ``source``, ``deployment_version``, ``workflow``, plus ``metadata.<key>``
for any top-level run metadata key. Regex patterns are length-capped, checked for
nested quantifiers on save, and matched against at most 1,000 characters (ReDoS).
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.tags import AutoTaggingRule

MAX_VALUE_LEN = 1000
MAX_PATTERN_LEN = 300
_NESTED_QUANTIFIER = re.compile(r"\([^)]*[+*][^)]*\)\s*[+*{]")
_CACHE_TTL_S = 10.0


@dataclass(frozen=True)
class TagRule:
    id: uuid.UUID
    name: str
    match_type: str
    match_field: str
    match_pattern: str
    tag_key: str
    tag_value: str
    priority: int


def validate_rule_pattern(match_type: str | None, pattern: str | None) -> str | None:
    """Return an error message, or None when the rule is safe to apply at ingest."""
    if match_type != "regex" or pattern is None:
        return None
    if len(pattern) > MAX_PATTERN_LEN:
        return f"regex patterns are limited to {MAX_PATTERN_LEN} characters"
    if _NESTED_QUANTIFIER.search(pattern):
        return "nested quantifiers such as (a+)+ are not allowed (catastrophic backtracking)"
    try:
        re.compile(pattern)
    except re.error as exc:
        return f"invalid regex: {exc}"
    return None


def match_rule(match_type: str, pattern: str, value: str | None) -> bool:
    candidate = (value or "")[:MAX_VALUE_LEN]
    if match_type == "equals":
        return candidate == pattern
    if match_type == "contains":
        return pattern.lower() in candidate.lower()
    if match_type == "prefix":
        return candidate.lower().startswith(pattern.lower())
    if match_type == "suffix":
        return candidate.lower().endswith(pattern.lower())
    if match_type == "regex":
        if validate_rule_pattern("regex", pattern):
            return False
        return bool(re.search(pattern, candidate))
    return False


def field_value(fields: dict[str, Any], match_field: str) -> str | None:
    if match_field.startswith("metadata."):
        meta = fields.get("metadata") or {}
        value = meta.get(match_field.split(".", 1)[1]) if isinstance(meta, dict) else None
    else:
        value = fields.get(match_field)
    return None if value is None else str(value)


def apply_rules(rules: list[TagRule], fields: dict[str, Any]) -> dict[str, str]:
    """Tags from every matching rule; for one key the highest-priority rule wins."""
    tags: dict[str, str] = {}
    for rule in sorted(rules, key=lambda r: (r.priority, str(r.id))):
        if rule.tag_key in tags:
            continue
        if match_rule(rule.match_type, rule.match_pattern, field_value(fields, rule.match_field)):
            tags[rule.tag_key] = rule.tag_value
    return tags


_cache: dict[uuid.UUID, tuple[float, list[TagRule]]] = {}


def invalidate(workspace_id: uuid.UUID) -> None:
    _cache.pop(workspace_id, None)


async def load_rules(
    db: AsyncSession, workspace_id: uuid.UUID, *, use_cache: bool = True
) -> list[TagRule]:
    now = time.monotonic()
    hit = _cache.get(workspace_id)
    if use_cache and hit is not None and now - hit[0] < _CACHE_TTL_S:
        return hit[1]
    rows = (
        (
            await db.execute(
                select(AutoTaggingRule).where(
                    AutoTaggingRule.workspace_id == workspace_id,
                    AutoTaggingRule.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    rules = [
        TagRule(
            id=r.id,
            name=r.name,
            match_type=r.match_type,
            match_field=r.match_field,
            match_pattern=r.match_pattern,
            tag_key=r.tag_key,
            tag_value=r.tag_value,
            priority=int(r.priority if r.priority is not None else 100),
        )
        for r in rows
    ]
    _cache[workspace_id] = (now, rules)
    return rules


async def tags_for(
    db: AsyncSession, workspace_id: uuid.UUID, fields: dict[str, Any]
) -> dict[str, str]:
    """Best effort: a rule lookup failure never breaks ingest or the gateway."""
    try:
        rules = await load_rules(db, workspace_id)
    except Exception:  # noqa: BLE001
        return {}
    return apply_rules(rules, fields)
