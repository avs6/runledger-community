"""Schemas for email preferences and log."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class EmailPreferenceUpdate(BaseModel):
    report_frequency: str | None = None  # 'daily'|'weekly'|'monthly'|'never'
    alerts_enabled: bool | None = None
    approvals_enabled: bool | None = None
    reconciliation_enabled: bool | None = None
    budget_alerts_enabled: bool | None = None
    billing_closed_enabled: bool | None = None
    score_regression_enabled: bool | None = None
    dispute_flagged_enabled: bool | None = None


class EmailPreferenceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    workspace_id: uuid.UUID
    report_frequency: str
    alerts_enabled: bool
    approvals_enabled: bool
    reconciliation_enabled: bool
    budget_alerts_enabled: bool
    billing_closed_enabled: bool
    score_regression_enabled: bool
    dispute_flagged_enabled: bool
    created_at: datetime
    updated_at: datetime


class EmailLogItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    to_email: str
    subject: str
    event_type: str
    status: str
    error_message: str | None
    sent_at: datetime


class EmailLogList(BaseModel):
    items: list[EmailLogItem]
    total: int
