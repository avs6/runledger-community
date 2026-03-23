"""
Provider Invoice Reconciliation API.

Prefix: /invoices
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /invoices/upload              Upload provider CSV or JSON invoice
GET    /invoices                     List all invoices
GET    /invoices/{id}                Get invoice + reconciliation summary
DELETE /invoices/{id}                Delete an invoice and its lines
POST   /invoices/{id}/reconcile      Trigger reconciliation against provider_calls
GET    /invoices/{id}/lines          List invoice lines with match status
PUT    /invoices/{id}/lines/{lid}/dispute   Mark a line disputed
GET    /invoices/{id}/export         Export signed dispute package (JSON)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.invoices import ProviderInvoice, ProviderInvoiceLine
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.invoices import (
    DisputeRequest,
    InvoiceLineList,
    InvoiceLineResponse,
    InvoiceList,
    InvoiceResponse,
    ReconciliationSummary,
    TokenMismatchBucket,
)
from runledger_api.services.invoices import (
    parse_csv,
    parse_json,
    reconcile_invoice,
    sign_dispute_export,
)

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
    dependencies=[Depends(management_rate_limit)],
)
log = structlog.get_logger()

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


# ── Upload ─────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    workspace: WorkspaceDep,
    db: DbDep,
    file: UploadFile = File(...),
    period_start: str = Query(..., description="ISO date: YYYY-MM-DD"),
    period_end: str = Query(..., description="ISO date: YYYY-MM-DD"),
    provider: str | None = Query(None, description="Override detected provider"),
) -> InvoiceResponse:
    """
    Upload a provider usage export (CSV or JSON).

    RunLedger will parse the file, detect the provider format, and store
    individual line items. Call POST /invoices/{id}/reconcile to match against
    your tracked provider_calls.
    """
    from datetime import date

    try:
        p_start = date.fromisoformat(period_start)
        p_end = date.fromisoformat(period_end)
    except ValueError:
        raise HTTPException(status_code=422, detail="period_start and period_end must be ISO dates (YYYY-MM-DD)") from None

    if p_end < p_start:
        raise HTTPException(status_code=422, detail="period_end must be >= period_start")

    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")

    filename = file.filename or "upload"
    content_type = (file.content_type or "").lower()

    try:
        if filename.endswith(".json") or "json" in content_type:
            detected_provider, lines = parse_json(content)
        else:
            detected_provider, lines = parse_csv(content, filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {exc}") from exc

    if not lines:
        raise HTTPException(status_code=422, detail="No valid invoice lines found in file")

    final_provider = provider or detected_provider
    total_amount = sum(line["amount"] for line in lines)

    invoice = ProviderInvoice(
        workspace_id=workspace.id,
        provider=final_provider,
        period_start=p_start,
        period_end=p_end,
        total_amount=total_amount,
        line_count=len(lines),
        filename=filename,
        status="imported",
    )
    db.add(invoice)
    await db.flush()

    # Bulk-insert lines
    for line in lines:
        db.add(
            ProviderInvoiceLine(
                invoice_id=invoice.id,
                provider_request_id=line["provider_request_id"],
                model=line["model"],
                input_tokens=line["input_tokens"],
                output_tokens=line["output_tokens"],
                amount=line["amount"],
                occurred_at=line["occurred_at"],
                raw=line["raw"],
            )
        )

    await db.commit()
    await db.refresh(invoice)
    log.info(
        "invoice_uploaded",
        invoice_id=str(invoice.id),
        workspace_id=str(workspace.id),
        provider=final_provider,
        lines=len(lines),
    )
    return InvoiceResponse.model_validate(invoice)


# ── List / Get / Delete ────────────────────────────────────────────────────────

@router.get("", response_model=InvoiceList)
async def list_invoices(
    workspace: WorkspaceDep,
    db: DbDep,
    provider: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> InvoiceList:
    """List uploaded invoices for the workspace."""
    stmt = select(ProviderInvoice).where(ProviderInvoice.workspace_id == workspace.id)
    if provider:
        stmt = stmt.where(ProviderInvoice.provider == provider)
    if status_filter:
        stmt = stmt.where(ProviderInvoice.status == status_filter)
    stmt = stmt.order_by(ProviderInvoice.created_at.desc())
    result = await db.execute(stmt)
    items = result.scalars().all()
    return InvoiceList(items=[InvoiceResponse.model_validate(i) for i in items])


@router.get("/{invoice_id}", response_model=ReconciliationSummary)
async def get_invoice_summary(
    invoice_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> ReconciliationSummary:
    """Get reconciliation summary for an invoice."""
    from sqlalchemy import case

    from runledger_api.models.events import ProviderCall

    result = await db.execute(
        select(ProviderInvoice).where(
            ProviderInvoice.id == invoice_id,
            ProviderInvoice.workspace_id == workspace.id,
        )
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Aggregate lines
    agg_result = await db.execute(
        select(
            func.count(ProviderInvoiceLine.id).label("total"),
            func.sum(case((ProviderInvoiceLine.match_status == "exact", 1), else_=0)).label("exact_count"),
            func.sum(case((ProviderInvoiceLine.match_status == "fuzzy", 1), else_=0)).label("fuzzy_count"),
            func.sum(case((ProviderInvoiceLine.match_status == "unmatched", 1), else_=0)).label("unmatched_count"),
            func.sum(case((ProviderInvoiceLine.match_status == "disputed", 1), else_=0)).label("disputed_count"),
            func.sum(
                case((ProviderInvoiceLine.match_status == "unmatched", ProviderInvoiceLine.amount), else_=Decimal("0"))
            ).label("unmatched_amount"),
        ).where(ProviderInvoiceLine.invoice_id == invoice_id)
    )
    agg = agg_result.one()

    # RunLedger total from matched calls
    rl_total_result = await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost_usd), Decimal("0"))).where(
            ProviderCall.id.in_(
                select(ProviderInvoiceLine.matched_call_id).where(
                    ProviderInvoiceLine.invoice_id == invoice_id,
                    ProviderInvoiceLine.matched_call_id.isnot(None),
                )
            )
        )
    )
    rl_total = Decimal(str(rl_total_result.scalar() or 0))

    total = int(agg.total or 0)
    exact = int(agg.exact_count or 0)
    fuzzy = int(agg.fuzzy_count or 0)
    unmatched = int(agg.unmatched_count or 0)
    disputed = int(agg.disputed_count or 0)
    unmatched_amount = Decimal(str(agg.unmatched_amount or 0))

    matched = exact + fuzzy
    matched_pct = Decimal(str(round(matched / total * 100, 2))) if total else Decimal("0")
    delta = invoice.total_amount - rl_total
    delta_pct = (delta / rl_total * 100) if rl_total != Decimal("0") else None

    # Token mismatch buckets (only for fuzzy matches)
    buckets_result = await db.execute(
        select(
            ProviderInvoiceLine.token_delta,
            ProviderInvoiceLine.amount,
        ).where(
            ProviderInvoiceLine.invoice_id == invoice_id,
            ProviderInvoiceLine.match_status == "fuzzy",
            ProviderInvoiceLine.token_delta.isnot(None),
        )
    )
    bucket_rows = buckets_result.all()

    b0_5 = TokenMismatchBucket(bucket="0-5%", count=0, amount=Decimal("0"))
    b5_20 = TokenMismatchBucket(bucket="5-20%", count=0, amount=Decimal("0"))
    b20p = TokenMismatchBucket(bucket=">20%", count=0, amount=Decimal("0"))

    for row in bucket_rows:
        td = abs(row.token_delta or 0)
        amt = Decimal(str(row.amount or 0))
        # Rough pct estimation using the token delta itself
        if td < 500:
            b0_5.count += 1
            b0_5.amount += amt
        elif td < 2000:
            b5_20.count += 1
            b5_20.amount += amt
        else:
            b20p.count += 1
            b20p.amount += amt

    return ReconciliationSummary(
        invoice_id=invoice.id,
        provider=invoice.provider,
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        total_amount=invoice.total_amount,
        line_count=total,
        matched_exact=exact,
        matched_fuzzy=fuzzy,
        unmatched=unmatched,
        disputed=disputed,
        matched_pct=matched_pct,
        unmatched_amount=unmatched_amount,
        runledger_total=rl_total,
        delta_amount=delta,
        delta_pct=Decimal(str(round(float(delta_pct), 2))) if delta_pct is not None else None,
        token_mismatch_buckets=[b0_5, b5_20, b20p],
        status=invoice.status,
    )


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> None:
    """Delete an invoice and all its lines."""
    result = await db.execute(
        select(ProviderInvoice).where(
            ProviderInvoice.id == invoice_id,
            ProviderInvoice.workspace_id == workspace.id,
        )
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Delete lines first
    from sqlalchemy import delete
    await db.execute(delete(ProviderInvoiceLine).where(ProviderInvoiceLine.invoice_id == invoice_id))
    await db.delete(invoice)
    await db.commit()


# ── Reconcile ─────────────────────────────────────────────────────────────────

@router.post("/{invoice_id}/reconcile")
async def trigger_reconcile(
    invoice_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> dict:
    """
    Run reconciliation: match invoice lines to provider_calls.

    Fuzzy matching: same model + timestamp within ±10 min + tokens within 10%.
    """
    result = await db.execute(
        select(ProviderInvoice).where(
            ProviderInvoice.id == invoice_id,
            ProviderInvoice.workspace_id == workspace.id,
        )
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    summary = await reconcile_invoice(db, invoice_id, workspace.id)
    log.info("invoice_reconciled", invoice_id=str(invoice_id), **summary)
    return {"invoice_id": str(invoice_id), **summary}


# ── Lines ──────────────────────────────────────────────────────────────────────

@router.get("/{invoice_id}/lines", response_model=InvoiceLineList)
async def list_lines(
    invoice_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
    match_status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InvoiceLineList:
    """List invoice lines, optionally filtered by match_status."""
    # Verify ownership
    inv_result = await db.execute(
        select(ProviderInvoice).where(
            ProviderInvoice.id == invoice_id,
            ProviderInvoice.workspace_id == workspace.id,
        )
    )
    if inv_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    stmt = select(ProviderInvoiceLine).where(ProviderInvoiceLine.invoice_id == invoice_id)
    if match_status:
        stmt = stmt.where(ProviderInvoiceLine.match_status == match_status)

    count_result = await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )
    total = count_result.scalar() or 0

    stmt = stmt.order_by(ProviderInvoiceLine.occurred_at.desc().nullslast()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return InvoiceLineList(
        items=[InvoiceLineResponse.model_validate(ln) for ln in items],
        total=int(total),
    )


@router.put("/{invoice_id}/lines/{line_id}/dispute", response_model=InvoiceLineResponse)
async def dispute_line(
    invoice_id: uuid.UUID,
    line_id: uuid.UUID,
    body: DisputeRequest,
    workspace: WorkspaceDep,
    db: DbDep,
) -> InvoiceLineResponse:
    """Mark an invoice line as disputed with a note."""
    # Verify ownership
    inv_result = await db.execute(
        select(ProviderInvoice).where(
            ProviderInvoice.id == invoice_id,
            ProviderInvoice.workspace_id == workspace.id,
        )
    )
    if inv_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    line_result = await db.execute(
        select(ProviderInvoiceLine).where(
            ProviderInvoiceLine.id == line_id,
            ProviderInvoiceLine.invoice_id == invoice_id,
        )
    )
    line = line_result.scalar_one_or_none()
    if line is None:
        raise HTTPException(status_code=404, detail="Invoice line not found")

    line.match_status = "disputed"
    line.dispute_note = body.note
    await db.commit()
    await db.refresh(line)
    return InvoiceLineResponse.model_validate(line)


# ── Export ─────────────────────────────────────────────────────────────────────

@router.get("/{invoice_id}/export")
async def export_dispute_package(
    invoice_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> JSONResponse:
    """
    Export a signed JSON dispute package for finance.

    Contains all unmatched and disputed lines with evidence links.
    Signed with HMAC-SHA256 using the workspace's signing key.
    """
    from runledger_api.core.config import settings

    result = await db.execute(
        select(ProviderInvoice).where(
            ProviderInvoice.id == invoice_id,
            ProviderInvoice.workspace_id == workspace.id,
        )
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Load unmatched + disputed lines
    lines_result = await db.execute(
        select(ProviderInvoiceLine).where(
            ProviderInvoiceLine.invoice_id == invoice_id,
            ProviderInvoiceLine.match_status.in_(["unmatched", "disputed"]),
        ).order_by(ProviderInvoiceLine.occurred_at)
    )
    lines = lines_result.scalars().all()

    unmatched = []
    disputed = []
    for line in lines:
        entry = {
            "id": str(line.id),
            "model": line.model,
            "input_tokens": line.input_tokens,
            "output_tokens": line.output_tokens,
            "amount": str(line.amount),
            "occurred_at": line.occurred_at.isoformat() if line.occurred_at else None,
            "provider_request_id": line.provider_request_id,
            "dispute_note": line.dispute_note,
        }
        if line.match_status == "disputed":
            disputed.append(entry)
        else:
            unmatched.append(entry)

    summary = {
        "provider": invoice.provider,
        "period_start": invoice.period_start.isoformat(),
        "period_end": invoice.period_end.isoformat(),
        "total_amount": str(invoice.total_amount),
        "line_count": invoice.line_count,
        "matched_count": invoice.matched_count,
        "unmatched_count": len(unmatched),
        "disputed_count": len(disputed),
    }

    payload: dict = {
        "invoice_id": str(invoice_id),
        "provider": invoice.provider,
        "period_start": invoice.period_start.isoformat(),
        "period_end": invoice.period_end.isoformat(),
        "exported_at": datetime.now(UTC).isoformat(),
        "unmatched_lines": unmatched,
        "disputed_lines": disputed,
        "summary": summary,
    }

    signing_key = getattr(settings, "billing_signing_key", str(workspace.id))
    sig = sign_dispute_export(payload, signing_key)
    payload["signature"] = sig

    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": f'attachment; filename="dispute_{invoice_id}.json"',
            "Content-Type": "application/json",
        },
    )
