"""
Tests for Phase 23 — Provider Invoice Reconciliation.

Covers:
  GET    /invoices                          — list invoices
  GET    /invoices/{id}                     — reconciliation summary
  DELETE /invoices/{id}                     — delete invoice
  POST   /invoices/{id}/reconcile          — trigger reconciliation
  GET    /invoices/{id}/lines              — list lines
  PUT    /invoices/{id}/lines/{lid}/dispute — dispute a line

Also covers unit tests for CSV/JSON parsing service functions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

# ── Mock helpers ───────────────────────────────────────────────────────────────

def _scalars_list(rows: list) -> MagicMock:
    m = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    m.scalars = MagicMock(return_value=scalars)
    return m


def _scalar_one_or_none(val) -> MagicMock:
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=val)
    return m


def _scalar(val) -> MagicMock:
    m = MagicMock()
    m.scalar = MagicMock(return_value=val)
    return m


def _one(val) -> MagicMock:
    m = MagicMock()
    m.one = MagicMock(return_value=val)
    return m


def _make_invoice(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        provider="openai",
        period_start=date(2026, 2, 1),
        period_end=date(2026, 2, 28),
        currency="USD",
        total_amount=Decimal("123.45"),
        line_count=10,
        matched_count=0,
        unmatched_amount=None,
        status="imported",
        filename="openai_usage.csv",
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_line(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        invoice_id=uuid.uuid4(),
        provider_request_id=None,
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=200,
        amount=Decimal("0.012"),
        occurred_at=datetime.now(UTC),
        match_status="unmatched",
        matched_call_id=None,
        token_delta=None,
        cost_delta=None,
        dispute_note=None,
        raw={},
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_agg_row(**kwargs) -> SimpleNamespace:
    """Simulates a SQLAlchemy aggregate row."""
    defaults = dict(
        total=10,
        exact_count=3,
        fuzzy_count=4,
        unmatched_count=3,
        disputed_count=0,
        unmatched_amount=Decimal("30.00"),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── List invoices ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_invoices_empty(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([]))
    resp = await authed_client.get("/invoices")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_list_invoices(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    inv1 = _make_invoice(workspace_id=mock_workspace.id, provider="openai")
    inv2 = _make_invoice(workspace_id=mock_workspace.id, provider="anthropic", status="reconciled")
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([inv1, inv2]))

    resp = await authed_client.get("/invoices")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["provider"] == "openai"
    assert items[1]["status"] == "reconciled"


@pytest.mark.asyncio
async def test_list_invoices_provider_filter(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    inv = _make_invoice(workspace_id=mock_workspace.id, provider="anthropic")
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([inv]))

    resp = await authed_client.get("/invoices?provider=anthropic")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["provider"] == "anthropic"


# ── Get invoice summary ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_invoice_summary(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    inv_id = uuid.uuid4()
    inv = _make_invoice(id=inv_id, workspace_id=mock_workspace.id, total_amount=Decimal("100.00"))
    agg = _make_agg_row()

    # Budget buckets query returns empty list
    bucket_m = MagicMock()
    bucket_m.all = MagicMock(return_value=[])

    mock_db_session.execute = AsyncMock(side_effect=[
        _scalar_one_or_none(inv),   # load invoice
        _one(agg),                   # aggregate counts
        _scalar(Decimal("70.00")),  # rl_total from matched calls
        MagicMock(all=MagicMock(return_value=[])),  # bucket rows
    ])

    resp = await authed_client.get(f"/invoices/{inv_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["invoice_id"] == str(inv_id)
    assert data["matched_exact"] == 3
    assert data["matched_fuzzy"] == 4
    assert data["unmatched"] == 3
    assert data["line_count"] == 10


@pytest.mark.asyncio
async def test_get_invoice_summary_not_found(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    resp = await authed_client.get(f"/invoices/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Delete invoice ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_invoice(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    inv_id = uuid.uuid4()
    inv = _make_invoice(id=inv_id, workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(side_effect=[
        _scalar_one_or_none(inv),  # load invoice
        AsyncMock(),               # delete lines
    ])
    mock_db_session.delete = AsyncMock()

    resp = await authed_client.delete(f"/invoices/{inv_id}")
    assert resp.status_code == 204
    mock_db_session.delete.assert_called_once_with(inv)


@pytest.mark.asyncio
async def test_delete_invoice_not_found(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    resp = await authed_client.delete(f"/invoices/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Reconcile invoice ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reconcile_invoice(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    inv_id = uuid.uuid4()
    inv = _make_invoice(id=inv_id, workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(inv))

    from unittest.mock import patch
    with patch("runledger_api.routers.invoices.reconcile_invoice", new=AsyncMock(return_value={
        "matched_exact": 5, "matched_fuzzy": 3, "unmatched": 2,
        "unmatched_amount": "20.00", "runledger_total": "80.00", "matched_pct": 80.0,
    })):
        resp = await authed_client.post(f"/invoices/{inv_id}/reconcile")

    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_exact"] == 5
    assert data["matched_fuzzy"] == 3


@pytest.mark.asyncio
async def test_reconcile_invoice_not_found(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    resp = await authed_client.post(f"/invoices/{uuid.uuid4()}/reconcile")
    assert resp.status_code == 404


# ── List invoice lines ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_invoice_lines(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    inv_id = uuid.uuid4()
    inv = _make_invoice(id=inv_id, workspace_id=mock_workspace.id)
    line = _make_line(invoice_id=inv_id, match_status="unmatched")

    count_m = MagicMock()
    count_m.scalar = MagicMock(return_value=1)

    mock_db_session.execute = AsyncMock(side_effect=[
        _scalar_one_or_none(inv),
        count_m,
        _scalars_list([line]),
    ])

    resp = await authed_client.get(f"/invoices/{inv_id}/lines")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["match_status"] == "unmatched"


@pytest.mark.asyncio
async def test_list_invoice_lines_filter(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    inv_id = uuid.uuid4()
    inv = _make_invoice(id=inv_id, workspace_id=mock_workspace.id)
    matched_line = _make_line(invoice_id=inv_id, match_status="exact")

    count_m = MagicMock()
    count_m.scalar = MagicMock(return_value=1)

    mock_db_session.execute = AsyncMock(side_effect=[
        _scalar_one_or_none(inv),
        count_m,
        _scalars_list([matched_line]),
    ])

    resp = await authed_client.get(f"/invoices/{inv_id}/lines?match_status=exact")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["match_status"] == "exact"


# ── Dispute line ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dispute_line(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    inv_id = uuid.uuid4()
    line_id = uuid.uuid4()
    inv = _make_invoice(id=inv_id, workspace_id=mock_workspace.id)
    line = _make_line(id=line_id, invoice_id=inv_id)

    mock_db_session.execute = AsyncMock(side_effect=[
        _scalar_one_or_none(inv),
        _scalar_one_or_none(line),
    ])

    async def mock_refresh(obj: object) -> None:
        pass

    mock_db_session.refresh = mock_refresh

    resp = await authed_client.put(
        f"/invoices/{inv_id}/lines/{line_id}/dispute",
        json={"note": "Duplicate charge — not in our runs"},
    )
    assert resp.status_code == 200
    assert line.match_status == "disputed"
    assert line.dispute_note == "Duplicate charge — not in our runs"


@pytest.mark.asyncio
async def test_dispute_line_not_found(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    inv_id = uuid.uuid4()
    inv = _make_invoice(id=inv_id, workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(side_effect=[
        _scalar_one_or_none(inv),
        _scalar_one_or_none(None),  # line not found
    ])
    resp = await authed_client.put(
        f"/invoices/{inv_id}/lines/{uuid.uuid4()}/dispute",
        json={"note": "test"},
    )
    assert resp.status_code == 404


# ── Unit tests: CSV / JSON parsing ────────────────────────────────────────────

def test_parse_csv_openai() -> None:
    from runledger_api.services.invoices import parse_csv

    csv_content = (
        b"date,model,input_tokens,output_tokens,cost\n"
        b"2026-02-15,gpt-4o,1000,200,0.012\n"
        b"2026-02-16,gpt-3.5-turbo,5000,1000,0.003\n"
    )

    provider, lines = parse_csv(csv_content, "openai_usage.csv")
    assert len(lines) == 2
    assert lines[0]["model"] == "gpt-4o"
    assert lines[0]["input_tokens"] == 1000
    assert lines[0]["output_tokens"] == 200
    assert lines[0]["amount"] == Decimal("0.012")


def test_parse_csv_anthropic_columns() -> None:
    from runledger_api.services.invoices import parse_csv

    csv_content = (
        b"timestamp,model_id,input_tokens,output_tokens,total_cost\n"
        b"2026-02-15T10:00:00Z,claude-3-5-sonnet,2000,500,0.025\n"
    )

    provider, lines = parse_csv(csv_content, "anthropic_usage.csv")
    assert len(lines) == 1
    assert lines[0]["model"] == "claude-3-5-sonnet"
    assert lines[0]["input_tokens"] == 2000
    assert lines[0]["amount"] == Decimal("0.025")


def test_parse_csv_no_data() -> None:
    from runledger_api.services.invoices import parse_csv

    csv_content = b"date,model,cost\n"  # headers only, no data
    _, lines = parse_csv(csv_content, "empty.csv")
    assert lines == []


def test_parse_csv_with_dollar_sign() -> None:
    from runledger_api.services.invoices import parse_csv

    csv_content = (
        b"Date,Model,Cost\n"
        b"2026-02-01,gpt-4o,$1.50\n"
    )

    _, lines = parse_csv(csv_content, "usage.csv")
    assert len(lines) == 1
    assert lines[0]["amount"] == Decimal("1.50")


def test_parse_json_openai_format() -> None:
    import json

    from runledger_api.services.invoices import parse_json

    payload = {
        "object": "list",
        "data": [
            {
                "snapshot_id": "gpt-4o-2024-11-20",
                "n_context_tokens_total": 1000,
                "n_generated_tokens_total": 200,
                "cost": 0.012,
                "date": "2026-02-15",
            }
        ],
    }
    content = json.dumps(payload).encode()
    provider, lines = parse_json(content)
    assert provider == "openai"
    assert len(lines) == 1
    assert lines[0]["model"] == "gpt-4o-2024-11-20"
    assert lines[0]["amount"] == Decimal("0.012")
    assert lines[0]["input_tokens"] == 1000


def test_parse_json_array_format() -> None:
    import json

    from runledger_api.services.invoices import parse_json

    payload = [
        {"model": "claude-3-5-sonnet", "input_tokens": 500, "output_tokens": 100, "cost": 0.005},
    ]
    content = json.dumps(payload).encode()
    _, lines = parse_json(content)
    assert len(lines) == 1
    assert lines[0]["model"] == "claude-3-5-sonnet"


def test_parse_csv_comma_in_tokens() -> None:
    from runledger_api.services.invoices import parse_csv

    csv_content = (
        b"date,model,input_tokens,output_tokens,cost\n"
        b'2026-02-01,gpt-4o,"1,234","5,678",0.05\n'
    )

    _, lines = parse_csv(csv_content, "usage.csv")
    assert lines[0]["input_tokens"] == 1234
    assert lines[0]["output_tokens"] == 5678


def test_detect_provider_google() -> None:
    from runledger_api.services.invoices import _detect_provider  # type: ignore[attr-defined]

    assert _detect_provider(["sku_description", "project_id", "cost"]) == "google"


def test_detect_provider_anthropic() -> None:
    from runledger_api.services.invoices import _detect_provider  # type: ignore[attr-defined]

    assert _detect_provider(["message_id", "model", "input_tokens"]) == "anthropic"
