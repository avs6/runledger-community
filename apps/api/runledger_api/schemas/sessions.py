from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class SessionItem(BaseModel):
    session_id: str
    end_user_id: str | None
    run_count: int
    total_cost_usd: Decimal | None
    started_at: datetime
    ended_at: datetime | None
    avg_score: Decimal | None = None


class SessionList(BaseModel):
    items: list[SessionItem]
    total: int
    page: int
    page_size: int


class SessionRunItem(BaseModel):
    id: uuid.UUID
    status: str
    feature_tag: str | None
    deployment_version: str | None
    total_cost_usd: Decimal | None
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None
    turn_number: int


class SessionDetail(BaseModel):
    session_id: str
    end_user_id: str | None
    run_count: int
    total_cost_usd: Decimal | None
    started_at: datetime
    ended_at: datetime | None
    runs: list[SessionRunItem]


class TurnCost(BaseModel):
    turn_number: int
    run_id: uuid.UUID
    cost_usd: Decimal | None
    cumulative_cost_usd: Decimal


class TurnCostResponse(BaseModel):
    session_id: str
    turns: list[TurnCost]
