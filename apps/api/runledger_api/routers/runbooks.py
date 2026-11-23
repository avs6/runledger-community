"""
Runbooks API — get, export and delete generated runbooks (review B-12).

Prefix: /runbooks
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
GET    /runbooks                    List runbooks (paged; ?severity=&run_id=)
GET    /runbooks/{id}               Get one runbook
GET    /runbooks/{id}/export        Download as Markdown (?format=md) or JSON
DELETE /runbooks/{id}               Delete a runbook

Runbooks are generated from a run with ``POST /runs/{run_id}/runbook``. They are
derived documents, so there is no update: regenerate instead.
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_writer
from runledger_api.core.pagination import PageDep, paginate
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.events import RunbookEntry
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.runs import RunbookList, RunbookResponse
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.runbooks import runbook_markdown

router = APIRouter(
    prefix="/runbooks", tags=["runbooks"], dependencies=[Depends(management_rate_limit)]
)
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _get_or_404(db: AsyncSession, runbook_id: uuid.UUID, ws: Workspace) -> RunbookEntry:
    entry = (
        await db.execute(
            select(RunbookEntry).where(
                RunbookEntry.id == runbook_id, RunbookEntry.workspace_id == ws.id
            )
        )
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Runbook not found")
    return entry


@router.get("", response_model=RunbookList)
async def list_runbooks(
    workspace: WorkspaceDep,
    db: DbDep,
    page: PageDep,
    response: Response,
    severity: Annotated[str | None, Query(pattern="^(info|warning|critical)$")] = None,
    run_id: uuid.UUID | None = None,
) -> RunbookList:
    stmt = select(RunbookEntry).where(RunbookEntry.workspace_id == workspace.id)
    if severity:
        stmt = stmt.where(RunbookEntry.severity == severity)
    if run_id:
        stmt = stmt.where(RunbookEntry.run_id == run_id)
    rows = await paginate(
        db, stmt.order_by(RunbookEntry.generated_at.desc(), RunbookEntry.id), page, response
    )
    return RunbookList(
        items=[RunbookResponse.model_validate(r) for r in rows],
        total=int(response.headers.get("X-Total-Count", len(rows))),
    )


@router.get("/{runbook_id}", response_model=RunbookResponse)
async def get_runbook(runbook_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> RunbookResponse:
    return RunbookResponse.model_validate(await _get_or_404(db, runbook_id, workspace))


@router.get("/{runbook_id}/export")
async def export_runbook(
    runbook_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
    format: Annotated[str, Query(pattern="^(md|markdown|json)$")] = "md",  # noqa: A002
) -> Response:
    entry = await _get_or_404(db, runbook_id, workspace)
    stem = f"runbook-{str(entry.run_id)[:8]}"
    if format == "json":
        body = json.dumps(RunbookResponse.model_validate(entry).model_dump(mode="json"), indent=2)
        return Response(
            body,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{stem}.json"'},
        )
    return Response(
        runbook_markdown(entry),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{stem}.md"'},
    )


@router.delete(
    "/{runbook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_workspace_writer)],
)
async def delete_runbook(runbook_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> None:
    entry = await _get_or_404(db, runbook_id, workspace)
    run_id = str(entry.run_id)
    await db.delete(entry)
    await db.commit()
    await emit_audit_event(
        db,
        workspace.id,
        "runbook.deleted",
        target_type="runbook",
        target_id=str(runbook_id),
        before={"run_id": run_id},
    )
