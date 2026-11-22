"""OTLP metrics → daily rollups: parsing, series bounding, token classification.

Rollup arithmetic against Postgres (delta vs cumulative, carry-over across batches) is
exercised end to end by ``scripts/core/verify_ingestion.py``.
"""

from __future__ import annotations

from typing import Any

from runledger_api.services.otlp_metrics import (
    MAX_SERIES_ATTRS,
    MAX_SERIES_PER_BATCH,
    classify_token_type,
    parse_metric_series,
)

NS = 1_763_700_000_000_000_000  # 2025-11-21


def _attr(key: str, value: Any) -> dict[str, Any]:
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    return {"key": key, "value": {"stringValue": value}}


def _payload(metrics: list[dict[str, Any]], service: str = "svc") -> dict[str, Any]:
    return {
        "resourceMetrics": [
            {
                "resource": {"attributes": [_attr("service.name", service)]},
                "scopeMetrics": [{"metrics": metrics}],
            }
        ]
    }


def _sum(name: str, points: list[tuple[float, dict[str, Any]]], temporality: int = 1) -> dict:
    return {
        "name": name,
        "unit": "tokens",
        "sum": {
            "aggregationTemporality": temporality,
            "isMonotonic": True,
            "dataPoints": [
                {
                    "asDouble": v,
                    "timeUnixNano": str(NS + i),
                    "attributes": [_attr(k, a) for k, a in attrs.items()],
                }
                for i, (v, attrs) in enumerate(points)
            ],
        },
    }


def test_sum_points_grouped_by_attributes() -> None:
    series = parse_metric_series(
        _payload(
            [
                _sum(
                    "claude_code.token.usage",
                    [
                        (100, {"type": "input", "model": "claude-x"}),
                        (40, {"type": "output", "model": "claude-x"}),
                        (60, {"type": "input", "model": "claude-x"}),
                    ],
                )
            ]
        )
    )
    assert len(series) == 2
    by_type = {s.attributes["type"]: s for s in series}
    assert [p.value for p in by_type["input"].points] == [100, 60]
    assert by_type["input"].kind == "sum"
    assert by_type["input"].temporality == "delta"
    assert by_type["input"].service_name == "svc"
    assert by_type["input"].unit == "tokens"


def test_cumulative_temporality_enum_names() -> None:
    metric = _sum("requests", [(5, {})], temporality=2)
    assert parse_metric_series(_payload([metric]))[0].temporality == "cumulative"
    metric["sum"]["aggregationTemporality"] = "AGGREGATION_TEMPORALITY_DELTA"
    assert parse_metric_series(_payload([metric]))[0].temporality == "delta"


def test_gauge_has_no_temporality_and_int_values_parse() -> None:
    metric = {
        "name": "queue.depth",
        "gauge": {"dataPoints": [{"asInt": "7", "timeUnixNano": str(NS)}]},
    }
    (s,) = parse_metric_series(_payload([metric]))
    assert s.kind == "gauge"
    assert s.temporality is None
    assert s.points[0].value == 7.0


def test_histogram_keeps_sum_and_count() -> None:
    metric = {
        "name": "gen_ai.client.token.usage",
        "histogram": {
            "aggregationTemporality": 1,
            "dataPoints": [
                {
                    "count": "3",
                    "sum": 900,
                    "timeUnixNano": str(NS),
                    "attributes": [_attr("gen_ai.token.type", "input")],
                }
            ],
        },
    }
    (s,) = parse_metric_series(_payload([metric]))
    assert s.kind == "histogram"
    assert s.points[0].value == 900.0
    assert s.points[0].count == 3


def test_high_cardinality_attributes_dropped_and_capped() -> None:
    attrs = {
        "session.id": "abc",
        "user_id": "u1",
        "gen_ai.request.model": "gpt-4o",
        **{f"dim{i}": "x" for i in range(20)},
    }
    (s,) = parse_metric_series(_payload([_sum("m", [(1, attrs)])]))
    assert "session.id" not in s.attributes
    assert "user_id" not in s.attributes
    assert "gen_ai.request.model" in s.attributes
    assert len(s.attributes) <= MAX_SERIES_ATTRS


def test_series_per_batch_capped() -> None:
    points = [(1, {"dim": f"v{i}"}) for i in range(MAX_SERIES_PER_BATCH + 50)]
    assert len(parse_metric_series(_payload([_sum("m", points)]))) == MAX_SERIES_PER_BATCH


def test_metrics_without_name_or_points_ignored() -> None:
    assert parse_metric_series(_payload([{"name": "", "sum": {"dataPoints": [{}]}}])) == []
    assert parse_metric_series({}) == []


def test_classify_token_type() -> None:
    assert classify_token_type({"gen_ai.token.type": "input"}) == "input"
    assert classify_token_type({"gen_ai.token.type": "completion"}) == "output"
    assert classify_token_type({"type": "cacheRead"}) == "cached_input"
    assert classify_token_type({"type": "cacheCreation"}) is None
    assert classify_token_type({}) is None
