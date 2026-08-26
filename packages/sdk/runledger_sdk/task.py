"""High-level task wrapper for manual agent lifecycle instrumentation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


class RunLedgerTask:
    """Context manager that wraps a single task run with helper methods."""

    def __init__(
        self,
        client: Any,
        name: str,
        *,
        intent: str | None = None,
        metadata: dict[str, Any] | None = None,
        end_user_id: str | None = None,
        session_id: str | None = None,
        feature_tag: str | None = None,
        deployment_version: str | None = None,
    ) -> None:
        self._client = client
        self.name = name
        self.intent = intent
        self.metadata = metadata or {}
        self.end_user_id = end_user_id
        self.session_id = session_id
        self.feature_tag = feature_tag
        self.deployment_version = deployment_version
        self.run_id: str | None = None
        self._ctx: Any | None = None
        self._outcome_recorded = False
        self._total_cost_usd = Decimal("0")
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def __enter__(self) -> RunLedgerTask:
        default_metadata = getattr(self._client, "_default_task_metadata", {})
        merged_metadata = {**default_metadata, **self.metadata, "task": self.name}
        self.run_id = self._client.record_run_start(
            end_user_id=self.end_user_id,
            session_id=self.session_id,
            feature_tag=self.feature_tag,
            deployment_version=self.deployment_version,
            metadata=merged_metadata,
            intent=self.intent,
        )
        self._ctx = self._client.context(
            run_id=self.run_id,
            end_user_id=self.end_user_id,
            session_id=self.session_id,
            feature_tag=self.feature_tag,
            deployment_version=self.deployment_version,
        )
        self._ctx.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc: BaseException | None, tb: Any) -> None:
        if self._ctx is not None:
            self._ctx.__exit__(exc_type, exc, tb)
        if self._outcome_recorded or self.run_id is None:
            return
        if exc is not None:
            self.outcome(
                "failed",
                success=False,
                final_status="failed",
                labels={"error_type": exc.__class__.__name__, "task": self.name},
            )
            return
        self.outcome(
            "completed",
            success=True,
            labels={"task": self.name},
        )

    def span(
        self,
        name: str,
        *,
        span_type: str = "agent",
        status: str = "succeeded",
        cost_usd: Decimal | float | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return self._client.record_span(
            run_id=self._require_run_id(),
            name=name,
            span_type=span_type,
            status=status,
            cost_usd=cost_usd,
            metadata=metadata,
        )

    def tool_call(
        self,
        tool_name: str,
        *,
        span_id: str | None = None,
        tool_type: str = "read",
        risk_score: int | None = None,
        duration_ms: int | None = None,
        status: str = "success",
    ) -> None:
        self._client.record_tool_call(
            run_id=self._require_run_id(),
            span_id=span_id,
            tool_name=tool_name,
            tool_type=tool_type,
            risk_score=risk_score,
            duration_ms=duration_ms,
            status=status,
        )

    def model_call(
        self,
        *,
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
        self._client.record_model_call(
            run_id=self._require_run_id(),
            provider=provider,
            model=model,
            span_id=span_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            status=status,
            error_type=error_type,
        )
        if cost_usd is not None:
            self._total_cost_usd += Decimal(str(cost_usd))
        self._total_input_tokens += int(input_tokens or 0)
        self._total_output_tokens += int(output_tokens or 0)

    def outcome(
        self,
        outcome_type: str,
        *,
        success: bool = True,
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
        self._client.record_outcome(
            run_id=self._require_run_id(),
            outcome_type=outcome_type,
            success=success,
            labels=merged_labels or None,
            final_status=final_status,
            total_cost_usd=total_cost_usd
            if total_cost_usd is not None
            else str(self._total_cost_usd),
            total_input_tokens=total_input_tokens
            if total_input_tokens is not None
            else self._total_input_tokens,
            total_output_tokens=total_output_tokens
            if total_output_tokens is not None
            else self._total_output_tokens,
        )
        self._outcome_recorded = True

    def check_budget(self, **kwargs: Any) -> dict[str, Any]:
        return self._client.check_budget(**kwargs)

    def check_policy(self, **kwargs: Any) -> dict[str, Any]:
        return self._client.check_policy(**kwargs)

    def _require_run_id(self) -> str:
        if self.run_id is None:
            raise RuntimeError("RunLedgerTask has not been entered yet")
        return self.run_id
