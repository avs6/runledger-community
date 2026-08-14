"""
Guardrails, Content Safety & Policy Engine API.

Prefix: /guardrails
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /guardrails                        Create a guardrail rule
GET    /guardrails                        List guardrail rules
GET    /guardrails/templates              List available templates
GET    /guardrails/filters                List built-in content filters
PUT    /guardrails/filters                Activate/configure content filters
GET    /guardrails/stats                  Monitoring stats
GET    /guardrails/events                 Event log
GET    /guardrails/{id}                   Get single guardrail
PUT    /guardrails/{id}                   Update guardrail
DELETE /guardrails/{id}                   Delete guardrail
POST   /guardrails/{id}/test              Test guardrail against sample input
POST   /guardrails/test                   Test all active guardrails
POST   /guardrails/test/batch             Batch test (CSV rows)

POST   /guardrails/test-cases             Save a test case
GET    /guardrails/test-cases             List test cases
DELETE /guardrails/test-cases/{id}        Delete a test case
POST   /guardrails/{id}/regression        Run regression tests

POST   /guardrails/partners               Add partner guardrail
GET    /guardrails/partners               List partner guardrails
GET    /guardrails/partners/{id}          Get partner guardrail
PUT    /guardrails/partners/{id}          Update partner guardrail
DELETE /guardrails/partners/{id}          Delete partner guardrail
POST   /guardrails/partners/{id}/health   Health check a partner

POST   /guardrails/events/{id}/feedback   Mark event as false positive
GET    /guardrails/alerts                 List guardrail alerts
POST   /guardrails/alerts/evaluate        Trigger alert evaluation
POST   /guardrails/alerts/{id}/acknowledge  Acknowledge an alert
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_api_key,
    get_current_workspace,
    require_workspace_admin,
)
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.guardrails import (
    GuardrailAlert,
    GuardrailEvent,
    GuardrailRule,
    GuardrailTestCase,
    PartnerGuardrail,
)
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.schemas.guardrails import (
    BatchTestResponse,
    BatchTestResult,
    ContentFilterActivation,
    ContentFilterListResponse,
    ContentFilterStatus,
    GuardrailAlertList,
    GuardrailAlertResponse,
    GuardrailEventList,
    GuardrailEventResponse,
    GuardrailFeedbackInput,
    GuardrailRegressionReport,
    GuardrailRegressionResult,
    GuardrailRuleCreate,
    GuardrailRuleList,
    GuardrailRuleResponse,
    GuardrailRuleUpdate,
    GuardrailStats,
    GuardrailTemplate,
    GuardrailTestCaseCreate,
    GuardrailTestCaseList,
    GuardrailTestCaseResponse,
    GuardrailTestInput,
    GuardrailTestResponse,
    GuardrailTestResult,
    PartnerGuardrailCreate,
    PartnerGuardrailList,
    PartnerGuardrailResponse,
    PartnerGuardrailUpdate,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.guardrails import (
    BUILTIN_FILTERS,
    allow,
    evaluate_builtin_filter,
    evaluate_guardrail_alerts,
    evaluate_guardrails,
    execute_custom_logic,
    get_templates,
)

router = APIRouter(prefix="/guardrails", tags=["guardrails"])
log = structlog.get_logger()

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
WorkspaceAdminDep = Annotated[
    tuple[Workspace, object, object | None], Depends(require_workspace_admin)
]
ApiKeyDep = Annotated[ApiKey, Depends(get_current_api_key)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── CRUD — Guardrail Rules ───────────────────────────────────────────────────


@router.post(
    "",
    response_model=GuardrailRuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_guardrail(
    body: GuardrailRuleCreate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> GuardrailRuleResponse:
    rule = GuardrailRule(
        workspace_id=workspace.id,
        name=body.name,
        description=body.description,
        mode=body.mode,
        rule_type=body.rule_type,
        logic=body.logic,
        config=body.config,
        severity=body.severity,
        priority=body.priority,
        status=body.status,
        template_id=body.template_id,
        skip_system_messages=body.skip_system_messages,
    )
    db.add(rule)
    await db.flush()
    await db.commit()
    await db.refresh(rule)

    log.info(
        "guardrail_created",
        workspace_id=str(workspace.id),
        name=body.name,
        rule_type=body.rule_type,
    )
    await emit_audit_event(
        db,
        workspace.id,
        "guardrail.created",
        target_type="guardrail",
        target_id=str(rule.id),
        after={"name": body.name, "rule_type": body.rule_type, "mode": body.mode},
    )
    return GuardrailRuleResponse.model_validate(rule)


@router.get("", response_model=GuardrailRuleList, dependencies=[Depends(analytics_rate_limit)])
async def list_guardrails(
    auth: WorkspaceAdminDep,
    db: DbDep,
    rule_type: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    mode: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GuardrailRuleList:
    workspace = auth[0]
    stmt = select(GuardrailRule).where(GuardrailRule.workspace_id == workspace.id)
    if rule_type:
        stmt = stmt.where(GuardrailRule.rule_type == rule_type)
    if status_filter:
        stmt = stmt.where(GuardrailRule.status == status_filter)
    if mode:
        stmt = stmt.where(GuardrailRule.mode.in_([mode, "both"]))

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = int(count_result.scalar() or 0)

    stmt = (
        stmt.order_by(GuardrailRule.priority.asc(), GuardrailRule.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return GuardrailRuleList(
        items=[GuardrailRuleResponse.model_validate(r) for r in items], total=total
    )


@router.get(
    "/templates",
    response_model=list[GuardrailTemplate],
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_templates(ws: WorkspaceDep) -> list[GuardrailTemplate]:
    return [GuardrailTemplate(**t) for t in get_templates()]


@router.get(
    "/filters",
    response_model=ContentFilterListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_content_filters(
    ws: WorkspaceDep,
    db: DbDep,
) -> ContentFilterListResponse:
    result = await db.execute(
        select(GuardrailRule).where(
            GuardrailRule.workspace_id == ws.id,
            GuardrailRule.rule_type == "builtin_filter",
        )
    )
    active_filters = {r.template_id: r for r in result.scalars().all()}

    filters = []
    for fid, fdef in BUILTIN_FILTERS.items():
        active = active_filters.get(fid)
        filters.append(
            ContentFilterStatus(
                filter_name=fid,
                description=fdef["description"],
                severity=active.severity if active else "off",
                enabled=active is not None and active.status == "active",
                category=fdef["category"],
            )
        )
    return ContentFilterListResponse(filters=filters)


@router.put(
    "/filters",
    response_model=ContentFilterListResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def activate_content_filters(
    body: ContentFilterActivation,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> ContentFilterListResponse:
    workspace = auth[0]
    result = await db.execute(
        select(GuardrailRule).where(
            GuardrailRule.workspace_id == workspace.id,
            GuardrailRule.rule_type == "builtin_filter",
        )
    )
    existing = {r.template_id: r for r in result.scalars().all()}

    for fc in body.filters:
        if fc.filter_name not in BUILTIN_FILTERS:
            continue
        fdef = BUILTIN_FILTERS[fc.filter_name]
        if fc.filter_name in existing:
            rule = existing[fc.filter_name]
            rule.severity = fc.severity
            rule.status = "active" if fc.enabled else "disabled"
            rule.updated_at = datetime.now(UTC)
        elif fc.enabled:
            rule = GuardrailRule(
                workspace_id=workspace.id,
                name=fdef["name"],
                description=fdef["description"],
                mode="both",
                rule_type="builtin_filter",
                severity=fc.severity,
                priority=50,
                status="active",
                template_id=fc.filter_name,
            )
            db.add(rule)

    await db.commit()
    log.info("content_filters_updated", workspace_id=str(workspace.id))
    await emit_audit_event(
        db,
        workspace.id,
        "guardrail.filters_updated",
        target_type="guardrail_filters",
        target_id="bulk",
        after={"filters": [f.model_dump() for f in body.filters]},
    )
    return await list_content_filters(auth, db)


@router.get("/stats", response_model=GuardrailStats, dependencies=[Depends(analytics_rate_limit)])
async def guardrail_stats(
    auth: WorkspaceAdminDep,
    db: DbDep,
    hours: Annotated[int, Query(ge=1, le=720)] = 24,
) -> GuardrailStats:
    workspace = auth[0]
    from datetime import timedelta  # noqa: PLC0415

    since = datetime.now(UTC) - timedelta(hours=hours)

    base = select(GuardrailEvent).where(
        GuardrailEvent.workspace_id == workspace.id,
        GuardrailEvent.created_at >= since,
    )

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = int(count_result.scalar() or 0)

    by_decision_result = await db.execute(
        select(GuardrailEvent.decision, func.count(GuardrailEvent.id))
        .where(GuardrailEvent.workspace_id == workspace.id, GuardrailEvent.created_at >= since)
        .group_by(GuardrailEvent.decision)
    )
    by_decision = {row[0]: int(row[1]) for row in by_decision_result.all()}

    avg_lat_result = await db.execute(
        select(func.avg(GuardrailEvent.latency_ms)).where(
            GuardrailEvent.workspace_id == workspace.id, GuardrailEvent.created_at >= since
        )
    )
    avg_latency = float(avg_lat_result.scalar() or 0)

    top_result = await db.execute(
        select(GuardrailEvent.guardrail_name, func.count(GuardrailEvent.id).label("cnt"))
        .where(GuardrailEvent.workspace_id == workspace.id, GuardrailEvent.created_at >= since)
        .group_by(GuardrailEvent.guardrail_name)
        .order_by(func.count(GuardrailEvent.id).desc())
        .limit(10)
    )
    top_triggered = [{"name": row[0], "count": int(row[1])} for row in top_result.all()]

    # Error count
    error_count_result = await db.execute(
        select(func.count(GuardrailEvent.id)).where(
            GuardrailEvent.workspace_id == workspace.id,
            GuardrailEvent.created_at >= since,
            GuardrailEvent.error.isnot(None),
        )
    )
    total_errors = int(error_count_result.scalar() or 0)

    # False positive count
    fp_count_result = await db.execute(
        select(func.count(GuardrailEvent.id)).where(
            GuardrailEvent.workspace_id == workspace.id,
            GuardrailEvent.created_at >= since,
            GuardrailEvent.is_false_positive.is_(True),
        )
    )
    total_fp = int(fp_count_result.scalar() or 0)

    # Total latency overhead
    total_latency_result = await db.execute(
        select(func.sum(GuardrailEvent.latency_ms)).where(
            GuardrailEvent.workspace_id == workspace.id, GuardrailEvent.created_at >= since
        )
    )
    total_latency_overhead = float(total_latency_result.scalar() or 0)

    # Block rate by model
    by_model_result = await db.execute(
        select(
            GuardrailEvent.model,
            func.count(GuardrailEvent.id).label("total"),
            func.count(GuardrailEvent.id)
            .filter(GuardrailEvent.decision == "block")
            .label("blocks"),
        )
        .where(
            GuardrailEvent.workspace_id == workspace.id,
            GuardrailEvent.created_at >= since,
            GuardrailEvent.model.isnot(None),
        )
        .group_by(GuardrailEvent.model)
        .order_by(func.count(GuardrailEvent.id).desc())
        .limit(10)
    )
    by_model = [
        {
            "model": row[0],
            "total": int(row[1]),
            "blocks": int(row[2]),
            "block_rate": round(int(row[2]) / int(row[1]), 4) if int(row[1]) else 0,
        }
        for row in by_model_result.all()
    ]

    # Block rate by user
    by_user_result = await db.execute(
        select(
            GuardrailEvent.user_id,
            func.count(GuardrailEvent.id).label("total"),
            func.count(GuardrailEvent.id)
            .filter(GuardrailEvent.decision == "block")
            .label("blocks"),
        )
        .where(
            GuardrailEvent.workspace_id == workspace.id,
            GuardrailEvent.created_at >= since,
            GuardrailEvent.user_id.isnot(None),
        )
        .group_by(GuardrailEvent.user_id)
        .order_by(func.count(GuardrailEvent.id).desc())
        .limit(10)
    )
    by_user = [
        {
            "user_id": row[0],
            "total": int(row[1]),
            "blocks": int(row[2]),
            "block_rate": round(int(row[2]) / int(row[1]), 4) if int(row[1]) else 0,
        }
        for row in by_user_result.all()
    ]

    # Per-guardrail breakdown
    by_guardrail_result = await db.execute(
        select(
            GuardrailEvent.guardrail_name,
            func.count(GuardrailEvent.id).label("total"),
            func.count(GuardrailEvent.id)
            .filter(GuardrailEvent.decision == "block")
            .label("blocks"),
            func.avg(GuardrailEvent.latency_ms).label("avg_latency"),
        )
        .where(GuardrailEvent.workspace_id == workspace.id, GuardrailEvent.created_at >= since)
        .group_by(GuardrailEvent.guardrail_name)
        .order_by(func.count(GuardrailEvent.id).desc())
        .limit(20)
    )
    by_guardrail = [
        {
            "name": row[0],
            "total": int(row[1]),
            "blocks": int(row[2]),
            "avg_latency_ms": round(float(row[3] or 0), 2),
        }
        for row in by_guardrail_result.all()
    ]

    blocks = by_decision.get("block", 0)
    return GuardrailStats(
        total_evaluations=total,
        total_blocks=blocks,
        total_modifications=by_decision.get("modify", 0),
        total_allows=by_decision.get("allow", 0),
        total_errors=total_errors,
        block_rate=round(blocks / total, 4) if total else 0,
        false_positive_rate=round(total_fp / blocks, 4) if blocks else 0,
        avg_latency_ms=round(avg_latency, 2),
        total_latency_overhead_ms=round(total_latency_overhead, 2),
        top_triggered=top_triggered,
        by_decision=by_decision,
        by_model=by_model,
        by_user=by_user,
        by_guardrail=by_guardrail,
    )


@router.get(
    "/events", response_model=GuardrailEventList, dependencies=[Depends(analytics_rate_limit)]
)
async def list_events(
    auth: WorkspaceAdminDep,
    db: DbDep,
    decision: Annotated[str | None, Query()] = None,
    guardrail_name: Annotated[str | None, Query()] = None,
    mode: Annotated[str | None, Query()] = None,
    violations_only: Annotated[bool, Query()] = False,
    false_positive: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GuardrailEventList:
    workspace = auth[0]
    stmt = select(GuardrailEvent).where(GuardrailEvent.workspace_id == workspace.id)
    if decision:
        stmt = stmt.where(GuardrailEvent.decision == decision)
    if guardrail_name:
        stmt = stmt.where(GuardrailEvent.guardrail_name.ilike(f"%{guardrail_name}%"))
    if mode:
        stmt = stmt.where(GuardrailEvent.mode == mode)
    if violations_only:
        stmt = stmt.where(GuardrailEvent.decision.in_(["block", "modify"]))
    if false_positive is not None:
        stmt = stmt.where(GuardrailEvent.is_false_positive.is_(false_positive))

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = int(count_result.scalar() or 0)

    stmt = stmt.order_by(GuardrailEvent.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return GuardrailEventList(
        items=[GuardrailEventResponse.model_validate(e) for e in items], total=total
    )
# ── Test endpoints ───────────────────────────────────────────────────────────


@router.post(
    "/{guardrail_id}/test",
    response_model=GuardrailTestResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def test_single_guardrail(
    guardrail_id: uuid.UUID,
    body: GuardrailTestInput,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> GuardrailTestResponse:
    workspace = auth[0]
    result = await db.execute(
        select(GuardrailRule).where(
            GuardrailRule.id == guardrail_id, GuardrailRule.workspace_id == workspace.id
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardrail not found")

    start = time.monotonic()
    if rule.rule_type == "builtin_filter":
        gr = evaluate_builtin_filter(
            rule.template_id or rule.name.lower().replace(" ", "_"), body.texts, rule.severity
        )
    elif rule.logic:
        gr = execute_custom_logic(
            rule.logic,
            body.texts,
            body.images,
            body.tools,
            body.tool_calls,
            body.structured_messages,
            body.model,
            body.user_id,
            body.team_id,
            body.end_user_id,
            {**body.metadata, **rule.config},
        )
    else:
        gr = allow()
    elapsed = (time.monotonic() - start) * 1000

    test_result = GuardrailTestResult(
        guardrail_id=rule.id,
        guardrail_name=rule.name,
        decision=gr.decision,
        reason=gr.reason,
        latency_ms=round(elapsed, 2),
        modified_texts=gr.modified_texts,
        modified_images=gr.modified_images,
        modified_tool_calls=gr.modified_tool_calls,
    )
    return GuardrailTestResponse(
        results=[test_result], overall_decision=gr.decision, total_latency_ms=round(elapsed, 2)
    )


@router.post(
    "/test", response_model=GuardrailTestResponse, dependencies=[Depends(management_rate_limit)]
)
async def test_all_guardrails(
    body: GuardrailTestInput,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> GuardrailTestResponse:
    workspace = auth[0]
    overall_decision, results, total_latency = await evaluate_guardrails(
        db,
        workspace.id,
        "pre_call",
        texts=body.texts,
        images=body.images,
        tools=body.tools,
        tool_calls=body.tool_calls,
        structured_messages=body.structured_messages,
        model=body.model,
        user_id=body.user_id,
        team_id=body.team_id,
        end_user_id=body.end_user_id,
        metadata=body.metadata,
    )
    await db.commit()
    return GuardrailTestResponse(
        results=[GuardrailTestResult(**r) for r in results],
        overall_decision=overall_decision,
        total_latency_ms=total_latency,
    )


@router.post(
    "/test/batch", response_model=BatchTestResponse, dependencies=[Depends(management_rate_limit)]
)
async def batch_test_guardrails(
    body: list[GuardrailTestInput],
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> BatchTestResponse:
    workspace = auth[0]
    results: list[BatchTestResult] = []
    total_blocks = 0
    total_allows = 0
    total_mods = 0

    for i, row in enumerate(body):
        decision, row_results, _ = await evaluate_guardrails(
            db,
            workspace.id,
            "pre_call",
            texts=row.texts,
            images=row.images,
            tools=row.tools,
            tool_calls=row.tool_calls,
            structured_messages=row.structured_messages,
            model=row.model,
            user_id=row.user_id,
            team_id=row.team_id,
            end_user_id=row.end_user_id,
            metadata=row.metadata,
        )
        results.append(
            BatchTestResult(
                row_index=i,
                input_text=" | ".join(row.texts),
                decisions=[GuardrailTestResult(**r) for r in row_results],
                overall_decision=decision,
            )
        )
        if decision == "block":
            total_blocks += 1
        elif decision == "modify":
            total_mods += 1
        else:
            total_allows += 1

    await db.commit()
    return BatchTestResponse(
        total_rows=len(body),
        total_blocks=total_blocks,
        total_allows=total_allows,
        total_modifications=total_mods,
        results=results,
    )


# ── Test Cases (regression testing) ──────────────────────────────────────────


@router.post(
    "/test-cases",
    response_model=GuardrailTestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_test_case(
    body: GuardrailTestCaseCreate,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> GuardrailTestCaseResponse:
    workspace = auth[0]
    tc = GuardrailTestCase(
        workspace_id=workspace.id,
        guardrail_rule_id=body.guardrail_rule_id,
        name=body.name,
        input_text=body.input_text,
        input_metadata=body.input_metadata,
        expected_decision=body.expected_decision,
    )
    db.add(tc)
    await db.flush()
    await db.commit()
    await db.refresh(tc)
    return GuardrailTestCaseResponse.model_validate(tc)


@router.get(
    "/test-cases",
    response_model=GuardrailTestCaseList,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_test_cases(
    ws: WorkspaceDep,
    db: DbDep,
    guardrail_rule_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GuardrailTestCaseList:
    stmt = select(GuardrailTestCase).where(GuardrailTestCase.workspace_id == ws.id)
    if guardrail_rule_id:
        stmt = stmt.where(GuardrailTestCase.guardrail_rule_id == guardrail_rule_id)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = int(count_result.scalar() or 0)

    stmt = stmt.order_by(GuardrailTestCase.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return GuardrailTestCaseList(
        items=[GuardrailTestCaseResponse.model_validate(tc) for tc in items], total=total
    )


@router.delete(
    "/test-cases/{test_case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def delete_test_case(
    test_case_id: uuid.UUID,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    result = await db.execute(
        select(GuardrailTestCase).where(
            GuardrailTestCase.id == test_case_id, GuardrailTestCase.workspace_id == workspace.id
        )
    )
    tc = result.scalar_one_or_none()
    if tc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")
    await db.delete(tc)
    await db.commit()


@router.post(
    "/{guardrail_id}/regression",
    response_model=GuardrailRegressionReport,
    dependencies=[Depends(management_rate_limit)],
)
async def run_regression(
    guardrail_id: uuid.UUID,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> GuardrailRegressionReport:
    workspace = auth[0]
    rule_result = await db.execute(
        select(GuardrailRule).where(
            GuardrailRule.id == guardrail_id, GuardrailRule.workspace_id == workspace.id
        )
    )
    rule = rule_result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardrail not found")

    tc_result = await db.execute(
        select(GuardrailTestCase)
        .where(
            GuardrailTestCase.guardrail_rule_id == guardrail_id,
            GuardrailTestCase.workspace_id == workspace.id,
        )
        .order_by(GuardrailTestCase.created_at.asc())
    )
    test_cases = tc_result.scalars().all()

    results: list[GuardrailRegressionResult] = []
    passed = 0
    failed = 0

    for tc in test_cases:
        start = time.monotonic()
        if rule.rule_type == "builtin_filter":
            gr = evaluate_builtin_filter(rule.template_id or "", [tc.input_text], rule.severity)
        elif rule.logic:
            gr = execute_custom_logic(
                rule.logic,
                [tc.input_text],
                [],
                [],
                [],
                [],
                None,
                None,
                None,
                None,
                {**tc.input_metadata, **rule.config},
            )
        else:
            gr = allow()
        elapsed = (time.monotonic() - start) * 1000

        match = gr.decision == tc.expected_decision
        if match:
            passed += 1
        else:
            failed += 1

        results.append(
            GuardrailRegressionResult(
                test_case_id=tc.id,
                test_case_name=tc.name,
                expected_decision=tc.expected_decision,
                actual_decision=gr.decision,
                passed=match,
                latency_ms=round(elapsed, 2),
                reason=gr.reason,
            )
        )

    return GuardrailRegressionReport(
        guardrail_rule_id=guardrail_id,
        guardrail_name=rule.name,
        total_cases=len(test_cases),
        passed=passed,
        failed=failed,
        results=results,
    )


# ── Partner Guardrails CRUD ──────────────────────────────────────────────────


@router.post(
    "/partners",
    response_model=PartnerGuardrailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_partner_guardrail(
    body: PartnerGuardrailCreate,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> PartnerGuardrailResponse:
    workspace = auth[0]
    pg = PartnerGuardrail(
        workspace_id=workspace.id,
        provider=body.provider,
        name=body.name,
        mode=body.mode,
        endpoint_url=body.endpoint_url,
        credentials=body.credentials,
        config=body.config,
        timeout_ms=body.timeout_ms,
        fallback_action=body.fallback_action,
        priority=body.priority,
    )
    db.add(pg)
    await db.flush()
    await db.commit()
    await db.refresh(pg)

    log.info("partner_guardrail_created", provider=body.provider, name=body.name)
    await emit_audit_event(
        db,
        workspace.id,
        "guardrail.partner_created",
        target_type="partner_guardrail",
        target_id=str(pg.id),
        after={"provider": body.provider, "name": body.name},
    )
    return PartnerGuardrailResponse.model_validate(pg)


@router.get(
    "/partners", response_model=PartnerGuardrailList, dependencies=[Depends(analytics_rate_limit)]
)
async def list_partner_guardrails(
    ws: WorkspaceDep,
    db: DbDep,
    provider: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PartnerGuardrailList:
    stmt = select(PartnerGuardrail).where(PartnerGuardrail.workspace_id == ws.id)
    if provider:
        stmt = stmt.where(PartnerGuardrail.provider == provider)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = int(count_result.scalar() or 0)

    stmt = stmt.order_by(PartnerGuardrail.priority.asc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return PartnerGuardrailList(
        items=[PartnerGuardrailResponse.model_validate(p) for p in items], total=total
    )


@router.get(
    "/partners/{partner_id}",
    response_model=PartnerGuardrailResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_partner_guardrail(
    partner_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
) -> PartnerGuardrailResponse:
    result = await db.execute(
        select(PartnerGuardrail).where(
            PartnerGuardrail.id == partner_id, PartnerGuardrail.workspace_id == ws.id
        )
    )
    pg = result.scalar_one_or_none()
    if pg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Partner guardrail not found"
        )
    return PartnerGuardrailResponse.model_validate(pg)


@router.put(
    "/partners/{partner_id}",
    response_model=PartnerGuardrailResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_partner_guardrail(
    partner_id: uuid.UUID,
    body: PartnerGuardrailUpdate,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> PartnerGuardrailResponse:
    workspace = auth[0]
    result = await db.execute(
        select(PartnerGuardrail).where(
            PartnerGuardrail.id == partner_id, PartnerGuardrail.workspace_id == workspace.id
        )
    )
    pg = result.scalar_one_or_none()
    if pg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Partner guardrail not found"
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pg, field, value)
    pg.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(pg)
    log.info("partner_guardrail_updated", partner_id=str(partner_id))
    return PartnerGuardrailResponse.model_validate(pg)


@router.delete(
    "/partners/{partner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def delete_partner_guardrail(
    partner_id: uuid.UUID,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    result = await db.execute(
        select(PartnerGuardrail).where(
            PartnerGuardrail.id == partner_id, PartnerGuardrail.workspace_id == workspace.id
        )
    )
    pg = result.scalar_one_or_none()
    if pg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Partner guardrail not found"
        )

    await db.delete(pg)
    await db.commit()
    log.info("partner_guardrail_deleted", partner_id=str(partner_id))
    await emit_audit_event(
        db,
        workspace.id,
        "guardrail.partner_deleted",
        target_type="partner_guardrail",
        target_id=str(partner_id),
        after={"provider": pg.provider, "name": pg.name},
    )


@router.post(
    "/partners/{partner_id}/health",
    response_model=PartnerGuardrailResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def health_check_partner(
    partner_id: uuid.UUID,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> PartnerGuardrailResponse:
    workspace = auth[0]
    result = await db.execute(
        select(PartnerGuardrail).where(
            PartnerGuardrail.id == partner_id, PartnerGuardrail.workspace_id == workspace.id
        )
    )
    pg = result.scalar_one_or_none()
    if pg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Partner guardrail not found"
        )

    pg.last_health_check = datetime.now(UTC)
    pg.health_status = "healthy"
    await db.commit()
    await db.refresh(pg)
    return PartnerGuardrailResponse.model_validate(pg)


# ── Event Feedback (false positive marking) ────────────────────────────────


@router.post(
    "/events/{event_id}/feedback",
    response_model=GuardrailEventResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def submit_event_feedback(
    event_id: uuid.UUID,
    body: GuardrailFeedbackInput,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> GuardrailEventResponse:
    workspace = auth[0]
    result = await db.execute(
        select(GuardrailEvent).where(
            GuardrailEvent.id == event_id,
            GuardrailEvent.workspace_id == workspace.id,
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guardrail event not found"
        )

    event.is_false_positive = body.is_false_positive
    event.feedback_reason = body.reason
    await db.commit()
    await db.refresh(event)

    log.info(
        "guardrail_feedback",
        event_id=str(event_id),
        is_false_positive=body.is_false_positive,
    )
    await emit_audit_event(
        db,
        workspace.id,
        "guardrail.feedback",
        target_type="guardrail_event",
        target_id=str(event_id),
        after={"is_false_positive": body.is_false_positive, "reason": body.reason},
    )
    return GuardrailEventResponse.model_validate(event)


# ── Guardrail Alerts ───────────────────────────────────────────────────────


@router.get(
    "/alerts", response_model=GuardrailAlertList, dependencies=[Depends(analytics_rate_limit)]
)
async def list_guardrail_alerts(
    ws: WorkspaceDep,
    db: DbDep,
    alert_type: Annotated[str | None, Query()] = None,
    alert_status: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GuardrailAlertList:
    stmt = select(GuardrailAlert).where(GuardrailAlert.workspace_id == ws.id)
    if alert_type:
        stmt = stmt.where(GuardrailAlert.alert_type == alert_type)
    if alert_status:
        stmt = stmt.where(GuardrailAlert.status == alert_status)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = int(count_result.scalar() or 0)

    stmt = stmt.order_by(GuardrailAlert.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return GuardrailAlertList(
        items=[GuardrailAlertResponse.model_validate(a) for a in items],
        total=total,
    )


@router.post(
    "/alerts/evaluate",
    response_model=list[dict[str, Any]],
    dependencies=[Depends(management_rate_limit)],
)
async def trigger_alert_evaluation(
    auth: WorkspaceAdminDep,
    db: DbDep,
    window_hours: Annotated[int, Query(ge=1, le=24)] = 1,
    baseline_hours: Annotated[int, Query(ge=1, le=168)] = 24,
) -> list[dict[str, Any]]:
    workspace = auth[0]
    alerts = await evaluate_guardrail_alerts(db, workspace.id, window_hours, baseline_hours)
    await db.commit()
    return alerts


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=GuardrailAlertResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> GuardrailAlertResponse:
    workspace = auth[0]
    result = await db.execute(
        select(GuardrailAlert).where(
            GuardrailAlert.id == alert_id,
            GuardrailAlert.workspace_id == workspace.id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guardrail alert not found"
        )

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(alert)
    return GuardrailAlertResponse.model_validate(alert)


# ── Single Rule CRUD Endpoints ───────────────────────────────────────────────


@router.get(
    "/{guardrail_id}",
    response_model=GuardrailRuleResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_guardrail(
    guardrail_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
) -> GuardrailRuleResponse:
    result = await db.execute(
        select(GuardrailRule).where(
            GuardrailRule.id == guardrail_id, GuardrailRule.workspace_id == ws.id
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardrail not found")
    return GuardrailRuleResponse.model_validate(rule)


@router.put(
    "/{guardrail_id}",
    response_model=GuardrailRuleResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_guardrail(
    guardrail_id: uuid.UUID,
    body: GuardrailRuleUpdate,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> GuardrailRuleResponse:
    workspace = auth[0]
    result = await db.execute(
        select(GuardrailRule).where(
            GuardrailRule.id == guardrail_id, GuardrailRule.workspace_id == workspace.id
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardrail not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    rule.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(rule)
    log.info("guardrail_updated", guardrail_id=str(guardrail_id))
    await emit_audit_event(
        db,
        workspace.id,
        "guardrail.updated",
        target_type="guardrail",
        target_id=str(guardrail_id),
        after=update_data,
    )
    return GuardrailRuleResponse.model_validate(rule)


@router.delete(
    "/{guardrail_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def delete_guardrail(
    guardrail_id: uuid.UUID,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    result = await db.execute(
        select(GuardrailRule).where(
            GuardrailRule.id == guardrail_id, GuardrailRule.workspace_id == workspace.id
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardrail not found")

    await db.delete(rule)
    await db.commit()
    log.info("guardrail_deleted", guardrail_id=str(guardrail_id))
    await emit_audit_event(
        db,
        workspace.id,
        "guardrail.deleted",
        target_type="guardrail",
        target_id=str(guardrail_id),
        after={"name": rule.name},
    )
