"""Generate incident-style runbooks for agent runs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import AgentRun, ProviderCall, RunbookEntry, Span, ToolCall


async def generate_runbook(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    run_id: uuid.UUID,
) -> RunbookEntry:
    run = (
        await db.execute(
            select(AgentRun).where(AgentRun.id == run_id, AgentRun.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()
    if run is None:
        raise ValueError(f"Run {run_id} not found")

    spans = (await db.execute(select(Span).where(Span.run_id == run_id))).scalars().all()
    provider_calls = (
        (await db.execute(select(ProviderCall).where(ProviderCall.run_id == run_id)))
        .scalars()
        .all()
    )
    tool_calls = (
        (await db.execute(select(ToolCall).where(ToolCall.run_id == run_id))).scalars().all()
    )

    avg_cost_result = await db.execute(
        select(func.avg(AgentRun.total_cost_usd)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.total_cost_usd.isnot(None),
        )
    )
    avg_cost = avg_cost_result.scalar() or Decimal("0")

    duration_ms = None
    if run.started_at and run.ended_at:
        duration_ms = int((run.ended_at - run.started_at).total_seconds() * 1000)

    cost = run.total_cost_usd or Decimal("0")
    cost_ratio = float(cost / avg_cost) if avg_cost > 0 else 0.0

    failed_spans = [s for s in spans if s.status == "failed"]
    failed_calls = [c for c in provider_calls if c.status == "failed"]
    errors = []
    for c in failed_calls:
        errors.append(
            {
                "model": c.model,
                "provider": c.provider,
                "error_type": c.error_type,
            }
        )

    models_used = list({c.model for c in provider_calls})
    providers_used = list({c.provider for c in provider_calls})
    tools_used = list({t.tool_name for t in tool_calls})

    if run.status == "failed" or cost_ratio > 3.0:
        severity = "critical"
    elif cost_ratio > 2.0 or len(failed_calls) > 0:
        severity = "warning"
    else:
        severity = "info"

    summary = {
        "run_id": str(run_id),
        "status": run.status.value if hasattr(run.status, "value") else str(run.status),
        "duration_ms": duration_ms,
        "cost_usd": float(cost),
        "avg_workspace_cost_usd": float(avg_cost),
        "cost_ratio": round(cost_ratio, 2),
        "input_tokens": run.total_input_tokens,
        "output_tokens": run.total_output_tokens,
        "models_used": models_used,
        "providers_used": providers_used,
        "tools_used": tools_used,
        "span_count": len(spans),
        "provider_call_count": len(provider_calls),
        "tool_call_count": len(tool_calls),
        "failed_span_count": len(failed_spans),
        "failed_call_count": len(failed_calls),
        "errors": errors,
        "end_user_id": run.end_user_id,
        "feature_tag": run.feature_tag,
        "intent": run.intent,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
    }

    what_happened = f"Run {str(run_id)[:8]} {run.status}"
    if run.status == "failed":
        what_happened += f" with {len(failed_calls)} provider error(s)"
    elif cost_ratio > 2.0:
        what_happened += f" at {cost_ratio:.1f}x average cost"

    recommendations = []
    if cost_ratio > 2.0:
        recommendations.append("Investigate high cost — consider model downgrade or caching")
    if len(failed_calls) > 0:
        recommendations.append("Review provider errors — consider adding fallback routes")
    if len(tool_calls) > 5:
        recommendations.append("High tool usage — consider tool filtering policies")
    if duration_ms and duration_ms > 30000:
        recommendations.append("Long duration — consider timeout policies")

    summary["what_happened"] = what_happened
    summary["recommendations"] = recommendations

    entry = RunbookEntry(
        workspace_id=workspace_id,
        run_id=run_id,
        severity=severity,
        summary=summary,
        generated_at=datetime.now(UTC),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
