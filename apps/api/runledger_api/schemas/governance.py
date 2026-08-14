"""Schemas for governance evidence and audit-pack exports."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class GovernanceAuditSummary(BaseModel):
    total_requests: int
    total_cost_usd: Decimal
    models_used: int
    users_active: int
    policies_enforced: int
    approvals_processed: int
    alerts_fired: int


class GovernanceModelUsage(BaseModel):
    model: str
    provider: str | None
    request_count: int
    cost_usd: Decimal
    first_used: datetime
    last_used: datetime


class GovernancePolicyAction(BaseModel):
    policy_type: str
    action: str
    count: int
    last_triggered: datetime


class GovernanceApprovalRecord(BaseModel):
    request_type: str
    status: str
    requested_by: str | None
    decided_by: str | None
    created_at: datetime


class GovernanceCapturePolicy(BaseModel):
    scope: str
    privacy_mode: str
    retention_days: int | None


class GovernanceBudgetAlert(BaseModel):
    budget_name: str
    threshold_pct: int
    triggered_at: datetime
    current_spend_usd: Decimal
    limit_usd: Decimal


class GovernanceAuditPack(BaseModel):
    generated_at: datetime
    period_from: str
    period_to: str
    summary: GovernanceAuditSummary
    model_usage: list[GovernanceModelUsage]
    policy_enforcements: list[GovernancePolicyAction]
    approvals: list[GovernanceApprovalRecord]
    data_capture_policies: list[GovernanceCapturePolicy]
    budget_alerts: list[GovernanceBudgetAlert]
