"""Shared helper for agent telemetry, budget checks, and policy checks."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from runledger_sdk.context import get_context_snapshot


class AgentTelemetryHelper:
    """High-level helper used by publishable skills and local agent wrappers."""

    def __init__(self, client: Any) -> None:
        self._client = client

    @property
    def _transport(self) -> Any:
        return self._client._get_sync_transport()

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._client.api_key}"}

    def _current_run_id(self, run_id: str | None = None) -> str:
        if run_id:
            return run_id
        ctx = get_context_snapshot()
        return str(ctx.get("run_id") or uuid.uuid4())

    def record_run_start(
        self,
        *,
        run_id: str | None = None,
        end_user_id: str | None = None,
        session_id: str | None = None,
        feature_tag: str | None = None,
        deployment_version: str | None = None,
        metadata: dict[str, Any] | None = None,
        intent: str | None = None,
    ) -> str:
        resolved_run_id = self._current_run_id(run_id)
        self._transport.enqueue(
            {
                "event_type": "run_start",
                "run_id": resolved_run_id,
                "end_user_id": end_user_id,
                "session_id": session_id,
                "feature_tag": feature_tag,
                "deployment_version": deployment_version,
                "started_at": datetime.now(UTC).isoformat(),
                "metadata": metadata,
                "intent": intent,
            }
        )
        return resolved_run_id

    def record_span(
        self,
        *,
        run_id: str,
        name: str,
        span_type: str = "agent",
        span_id: str | None = None,
        parent_span_id: str | None = None,
        status: str = "succeeded",
        cost_usd: Decimal | float | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        resolved_span_id = span_id or str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        self._transport.enqueue(
            {
                "event_type": "span_start",
                "span_id": resolved_span_id,
                "run_id": run_id,
                "parent_span_id": parent_span_id,
                "span_type": span_type,
                "name": name,
                "started_at": now,
            }
        )
        self._transport.enqueue(
            {
                "event_type": "span_end",
                "span_id": resolved_span_id,
                "run_id": run_id,
                "status": status,
                "ended_at": now,
                "cost_usd": str(cost_usd) if cost_usd is not None else None,
                "metadata": metadata,
            }
        )
        return resolved_span_id

    def record_tool_call(
        self,
        *,
        run_id: str,
        tool_name: str,
        span_id: str | None = None,
        tool_type: str = "read",
        risk_score: int | None = None,
        duration_ms: int | None = None,
        status: str = "success",
    ) -> None:
        self._transport.enqueue(
            {
                "event_type": "tool_call",
                "run_id": run_id,
                "span_id": span_id,
                "tool_name": tool_name,
                "tool_type": tool_type,
                "risk_score": risk_score,
                "duration_ms": duration_ms,
                "status": status,
            }
        )

    def record_model_call(
        self,
        *,
        run_id: str,
        provider: str,
        model: str,
        span_id: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cached_input_tokens: int | None = None,
        latency_ms: int | None = None,
        cost_usd: Decimal | float | str | None = None,
        status: str = "success",
        error_type: str | None = None,
    ) -> None:
        self._transport.enqueue(
            {
                "event_type": "provider_call",
                "run_id": run_id,
                "span_id": span_id,
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cached_input_tokens": cached_input_tokens,
                "latency_ms": latency_ms,
                "cost_usd": str(cost_usd) if cost_usd is not None else None,
                "status": status,
                "error_type": error_type,
            }
        )

    def record_outcome(
        self,
        *,
        run_id: str,
        outcome_type: str,
        success: bool,
        labels: dict[str, Any] | None = None,
        final_status: str = "succeeded",
        total_cost_usd: Decimal | float | str | None = None,
        total_input_tokens: int | None = None,
        total_output_tokens: int | None = None,
        quality_score: float | None = None,
        verification_status: str | None = None,
    ) -> None:
        merged_labels = dict(labels or {})
        if quality_score is not None:
            merged_labels["quality_score"] = quality_score
        if verification_status is not None:
            merged_labels["verification_status"] = verification_status
        self._transport.enqueue(
            {
                "event_type": "outcome",
                "run_id": run_id,
                "outcome_type": outcome_type,
                "success": success,
                "labels": merged_labels or None,
            }
        )
        self._transport.enqueue(
            {
                "event_type": "run_end",
                "run_id": run_id,
                "status": final_status,
                "ended_at": datetime.now(UTC).isoformat(),
                "total_cost_usd": str(total_cost_usd) if total_cost_usd is not None else None,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
            }
        )

    def check_budget(
        self,
        *,
        end_user_id: str | None = None,
        feature_tag: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if end_user_id:
            params["end_user_id"] = end_user_id
        if feature_tag:
            params["feature_tag"] = feature_tag
        resp = httpx.get(
            f"{self._client.base_url}/budgets/check",
            params=params,
            headers=self._headers,
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json()

    def check_policy(
        self,
        *,
        end_user_id: str | None = None,
        feature_tag: str | None = None,
        tool_name: str | None = None,
        model_alias: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        resp = httpx.post(
            f"{self._client.base_url}/policies/check",
            json={
                "end_user_id": end_user_id,
                "feature_tag": feature_tag,
                "tool_name": tool_name,
                "model_alias": model_alias,
                "dry_run": dry_run,
            },
            headers=self._headers,
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json()
