"""OTLP metrics → daily rollups.

Every OTLP metric data point is folded into one row per (series, UTC day) in
``otlp_metric_rollups``. A series is metric name + service + a bounded set of
low-cardinality point attributes, so a misbehaving exporter can't explode the table.

Value semantics per metric kind:

* Sum, delta temporality      → ``total`` adds each point.
* Sum, cumulative temporality → ``total`` adds the increase since the previous point of
  the same series (a drop is treated as a counter reset). The last cumulative value is
  carried across days, so a day's total is that day's increase.
* Histogram / exponential histogram / summary → ``total`` is the sum of observed values
  and ``observations`` their count (same delta / cumulative handling).
* Gauge → ``total`` is not meaningful; ``last`` / ``min`` / ``max`` are kept.

GenAI usage metrics (``gen_ai.client.token.usage``, Claude Code's
``claude_code.token.usage`` / ``claude_code.cost.usage``) are summarised by
``metric_usage_summary`` and compared with the usage RunLedger recorded from traces,
logs and the ingest API.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.otlp import OtlpMetricRollup
from runledger_api.services.otlp_parse import _flatten_attrs

MAX_SERIES_PER_BATCH = 2000
MAX_SERIES_ATTRS = 8
MAX_ATTR_VALUE_LEN = 128
# Attributes that identify one request / process rather than a dimension worth grouping by.
_HIGH_CARDINALITY_SUFFIXES = (
    ".id",
    "_id",
    ".uuid",
    "trace_id",
    "span_id",
    ".timestamp",
    "prompt",
    "session",
)
_KEEP_ALWAYS = {"gen_ai.token.type", "type", "model", "gen_ai.request.model", "gen_ai.system"}

_TEMPORALITY = {
    1: "delta",
    2: "cumulative",
    "AGGREGATION_TEMPORALITY_DELTA": "delta",
    "AGGREGATION_TEMPORALITY_CUMULATIVE": "cumulative",
}


@dataclass
class _Point:
    value: float | None
    count: int | None
    at: datetime


@dataclass
class _Series:
    key: str
    name: str
    unit: str | None
    kind: str
    temporality: str | None
    service_name: str | None
    attributes: dict[str, Any]
    points: list[_Point] = field(default_factory=list)


def _series_attrs(attrs: dict[str, Any]) -> dict[str, Any]:
    kept: dict[str, Any] = {}
    # Grouping keys the usage summary relies on go first, then the rest alphabetically.
    for key in sorted(attrs, key=lambda k: (k not in _KEEP_ALWAYS, k)):
        if len(kept) >= MAX_SERIES_ATTRS:
            break
        val = attrs[key]
        if not isinstance(val, str | int | float | bool):
            continue
        lowered = key.lower()
        if key not in _KEEP_ALWAYS and lowered.endswith(_HIGH_CARDINALITY_SUFFIXES):
            continue
        if isinstance(val, str):
            val = val[:MAX_ATTR_VALUE_LEN]
        kept[key] = val
    return kept


def _series_key(name: str, service: str | None, attrs: dict[str, Any]) -> str:
    raw = json.dumps([name, service or "", attrs], sort_keys=True, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()  # noqa: S324 - identity hash, not security


def _num(dp: dict[str, Any]) -> float | None:
    for key in ("asDouble", "asInt"):
        if key in dp and dp[key] is not None:
            try:
                return float(dp[key])
            except (TypeError, ValueError):
                return None
    return None


def _ts(dp: dict[str, Any]) -> datetime:
    raw = dp.get("timeUnixNano") or dp.get("startTimeUnixNano")
    try:
        ns = int(raw)
        if ns > 0:
            return datetime.fromtimestamp(ns / 1e9, tz=UTC)
    except (TypeError, ValueError):
        pass
    return datetime.now(UTC)


def parse_metric_series(payload: dict[str, Any]) -> list[_Series]:
    """Group every data point in an OTLP metrics payload by series."""
    series: dict[str, _Series] = {}
    for resource_metric in payload.get("resourceMetrics", []) or []:
        resource_attrs = _flatten_attrs(
            (resource_metric.get("resource") or {}).get("attributes", []) or []
        )
        service = resource_attrs.get("service.name")
        service = str(service)[:MAX_ATTR_VALUE_LEN] if service else None
        for scope_metric in resource_metric.get("scopeMetrics", []) or []:
            for metric in scope_metric.get("metrics", []) or []:
                name = str(metric.get("name") or "")[:255]
                if not name:
                    continue
                unit = (metric.get("unit") or None) and str(metric["unit"])[:64]
                for kind in ("sum", "gauge", "histogram", "exponentialHistogram", "summary"):
                    body = metric.get(kind)
                    if not isinstance(body, dict):
                        continue
                    temporality = _TEMPORALITY.get(body.get("aggregationTemporality"))
                    if kind == "summary":
                        temporality = "cumulative"
                    for dp in body.get("dataPoints", []) or []:
                        attrs = _series_attrs(_flatten_attrs(dp.get("attributes", []) or []))
                        key = _series_key(name, service, attrs)
                        if key not in series:
                            if len(series) >= MAX_SERIES_PER_BATCH:
                                continue
                            series[key] = _Series(
                                key=key,
                                name=name,
                                unit=unit,
                                kind=kind,
                                temporality=None if kind == "gauge" else temporality,
                                service_name=service,
                                attributes=attrs,
                            )
                        if kind in ("sum", "gauge"):
                            point = _Point(value=_num(dp), count=None, at=_ts(dp))
                        else:
                            try:
                                count = int(dp.get("count") or 0)
                            except (TypeError, ValueError):
                                count = 0
                            total = dp.get("sum")
                            point = _Point(
                                value=float(total) if total is not None else None,
                                count=count,
                                at=_ts(dp),
                            )
                        series[key].points.append(point)
                    break
    return list(series.values())


async def record_metric_rollups(
    db: AsyncSession, workspace_id: uuid.UUID, payload: dict[str, Any]
) -> int:
    """Fold an OTLP metrics payload into daily rollups. Returns the number of series."""
    parsed = parse_metric_series(payload)
    if not parsed:
        return 0

    # Last cumulative value per series, possibly from an earlier day.
    cumulative_keys = [s.key for s in parsed if s.temporality == "cumulative"]
    prior: dict[str, tuple[float | None, int | None]] = {}
    if cumulative_keys:
        rows = await db.execute(
            select(
                OtlpMetricRollup.series_key,
                OtlpMetricRollup.cumulative_value,
                OtlpMetricRollup.cumulative_count,
            )
            .where(
                OtlpMetricRollup.workspace_id == workspace_id,
                OtlpMetricRollup.series_key.in_(cumulative_keys),
            )
            .distinct(OtlpMetricRollup.series_key)
            .order_by(OtlpMetricRollup.series_key, OtlpMetricRollup.day.desc())
        )
        prior = {r.series_key: (r.cumulative_value, r.cumulative_count) for r in rows}

    for s in parsed:
        by_day: dict[date, dict[str, Any]] = {}
        last_v, last_c = prior.get(s.key, (None, None))
        for p in sorted(s.points, key=lambda x: x.at):
            day = p.at.date()
            agg = by_day.setdefault(
                day,
                {
                    "points": 0,
                    "total": 0.0,
                    "observations": 0,
                    "min": None,
                    "max": None,
                    "last": None,
                    "last_seen": p.at,
                },
            )
            agg["points"] += 1
            agg["last_seen"] = max(agg["last_seen"], p.at)
            if s.kind == "gauge":
                if p.value is not None:
                    agg["last"] = p.value
                    agg["min"] = p.value if agg["min"] is None else min(agg["min"], p.value)
                    agg["max"] = p.value if agg["max"] is None else max(agg["max"], p.value)
                continue
            value = p.value or 0.0
            count = p.count or 0
            if s.temporality == "cumulative":
                inc_v = value - last_v if last_v is not None and value >= last_v else value
                inc_c = count - last_c if last_c is not None and count >= last_c else count
                last_v, last_c = value, count
            else:
                inc_v, inc_c = value, count
            agg["total"] += inc_v
            agg["observations"] += inc_c
            agg["last"] = value

        for day, agg in by_day.items():
            stmt = pg_insert(OtlpMetricRollup).values(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                day=day,
                series_key=s.key,
                name=s.name,
                unit=s.unit,
                kind=s.kind,
                temporality=s.temporality,
                service_name=s.service_name,
                attributes=s.attributes,
                points=agg["points"],
                total=agg["total"] if s.kind != "gauge" else None,
                observations=agg["observations"] if s.kind != "gauge" else None,
                min_value=agg["min"],
                max_value=agg["max"],
                last_value=agg["last"],
                cumulative_value=last_v if s.temporality == "cumulative" else None,
                cumulative_count=last_c if s.temporality == "cumulative" else None,
                last_seen=agg["last_seen"],
            )
            ex = stmt.excluded
            t = OtlpMetricRollup.__table__.c
            stmt = stmt.on_conflict_do_update(
                index_elements=["workspace_id", "series_key", "day"],
                set_={
                    "points": t.points + ex.points,
                    "total": func.coalesce(t.total, 0) + ex.total if s.kind != "gauge" else None,
                    "observations": func.coalesce(t.observations, 0) + ex.observations
                    if s.kind != "gauge"
                    else None,
                    "min_value": func.least(t.min_value, ex.min_value),
                    "max_value": func.greatest(t.max_value, ex.max_value),
                    "last_value": func.coalesce(ex.last_value, t.last_value),
                    "cumulative_value": ex.cumulative_value,
                    "cumulative_count": ex.cumulative_count,
                    "last_seen": func.greatest(t.last_seen, ex.last_seen),
                },
            )
            await db.execute(stmt)
    return len(parsed)


# ── GenAI usage reported by metrics ────────────────────────────────────────────

_TOKEN_METRICS = {"gen_ai.client.token.usage", "claude_code.token.usage"}
_COST_METRICS = {"claude_code.cost.usage"}
_INPUT_TYPES = {"input", "prompt"}
_OUTPUT_TYPES = {"output", "completion"}
_CACHED_TYPES = {"cacheread", "cache_read", "cached_input"}


def classify_token_type(attrs: dict[str, Any]) -> str | None:
    raw = attrs.get("gen_ai.token.type") or attrs.get("type")
    if not raw:
        return None
    kind = str(raw).lower()
    if kind in _INPUT_TYPES:
        return "input"
    if kind in _OUTPUT_TYPES:
        return "output"
    if kind in _CACHED_TYPES:
        return "cached_input"
    return None


async def metric_usage_summary(
    db: AsyncSession, workspace_id: uuid.UUID, since: date
) -> dict[str, Any]:
    """Token and cost totals that exporters reported as metrics since ``since``."""
    rows = await db.execute(
        select(
            OtlpMetricRollup.name,
            OtlpMetricRollup.attributes,
            func.sum(OtlpMetricRollup.total).label("total"),
        )
        .where(
            OtlpMetricRollup.workspace_id == workspace_id,
            OtlpMetricRollup.day >= since,
            OtlpMetricRollup.name.in_(_TOKEN_METRICS | _COST_METRICS),
        )
        .group_by(OtlpMetricRollup.name, OtlpMetricRollup.attributes)
    )
    tokens = {"input": 0, "output": 0, "cached_input": 0}
    cost = 0.0
    seen = False
    for r in rows:
        seen = True
        total = float(r.total or 0)
        if r.name in _COST_METRICS:
            cost += total
            continue
        kind = classify_token_type(r.attributes or {})
        if kind:
            tokens[kind] += int(total)
    return {
        "reported": seen,
        "input_tokens": tokens["input"],
        "output_tokens": tokens["output"],
        "cached_input_tokens": tokens["cached_input"],
        "cost_usd": round(cost, 6),
    }
