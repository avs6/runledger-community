"""FinOps: durable budget spend, model-scoped budgets, runaway holds, sealed ledger.

Review items (W1-D): cd:B-01 / G-01 / top#2, cd:B-05, cd:B-09, F-12, F-22, F-25, cd:M-02.

- budgets.api_key_id: optional key filter for model-scoped budgets. Model budgets
  (model_budgets, per API key) become budgets with scope_type='model',
  scope_id=<model pattern>, api_key_id=<key>. Rows without a spend limit (rpm/tpm
  only, never enforced) are dropped; the model_budgets table is removed.
- Duplicate active budgets are deactivated (newest kept) and a partial unique index
  stops new ones (F-12).
- budget_spend: per budget per period, the source of truth for spend; Redis is a
  cache in front of it (cd:B-05). budget_spend_calls makes counting idempotent per
  provider call without relying on Redis keys that can be evicted.
- budget_runaway_holds: runs/sessions the runaway detector stopped; the gateway
  refuses calls for a held subject (cd:B-09).
- budget_notification_deliveries: payload, next_attempt_at, breach_id so webhook
  delivery is queued and retried by a worker instead of running inline (F-22).
- provider_pricing.cache_write_cost_per_1m: prompt-cache write rate (F-25).
- ledger_snapshots: prev_hash / entries_root / entry_count / sealed_at, plus
  ledger_snapshot_entries, the per-call manifest a snapshot seals (cd:M-02).

Revision ID: finops_budget_spend
Revises: 095_ip_acl_access_groups
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "finops_budget_spend"
down_revision = "095_ip_acl_access_groups"
branch_labels = None
depends_on = None

_TS = sa.TIMESTAMP(timezone=True)


def upgrade() -> None:
    # ── Model budgets → budget scopes ────────────────────────────────────────
    op.add_column("budgets", sa.Column("api_key_id", PGUUID(as_uuid=True), nullable=True))
    op.execute(
        """
        INSERT INTO budgets
            (id, workspace_id, scope_type, scope_id, api_key_id, period_type, limit_usd,
             action, downgrade_to_model, is_active, created_at)
        SELECT mb.id, k.workspace_id, 'model', mb.model_pattern, mb.api_key_id,
               CASE WHEN mb.period_type IN ('daily', 'weekly', 'monthly', 'total')
                    THEN mb.period_type ELSE 'monthly' END,
               mb.max_spend_usd,
               CASE WHEN mb.action IN ('notify', 'block', 'throttle') THEN mb.action
                    ELSE 'block' END,
               NULL, mb.is_active, mb.created_at
        FROM model_budgets AS mb
        JOIN api_keys AS k ON k.id = mb.api_key_id
        WHERE mb.max_spend_usd IS NOT NULL AND mb.max_spend_usd > 0
        """
    )
    op.drop_index("ix_model_budgets_key", table_name="model_budgets")
    op.drop_table("model_budgets")

    # ── One active budget per scope (F-12) ───────────────────────────────────
    op.execute(
        """
        UPDATE budgets AS b SET is_active = false
        FROM (
            SELECT id, row_number() OVER (
                PARTITION BY workspace_id, scope_type, COALESCE(scope_id, ''),
                             COALESCE(api_key_id::text, ''), period_type
                ORDER BY created_at DESC, id
            ) AS rn
            FROM budgets WHERE is_active
        ) AS d
        WHERE b.id = d.id AND d.rn > 1
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_budgets_active_scope ON budgets
            (workspace_id, scope_type, COALESCE(scope_id, ''),
             COALESCE(api_key_id::text, ''), period_type)
        WHERE is_active
        """
    )

    # ── Durable spend (cd:B-05) ──────────────────────────────────────────────
    op.create_table(
        "budget_spend",
        sa.Column(
            "budget_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("budgets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("period_key", sa.String(16), primary_key=True),
        sa.Column("spend_usd", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("call_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("threshold_notified_at", _TS, nullable=True),
        sa.Column("breached_at", _TS, nullable=True),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_table(
        "budget_spend_calls",
        sa.Column("provider_call_id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("counted_at", _TS, nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index(
        "ix_budget_spend_calls_workspace", "budget_spend_calls", ["workspace_id", "counted_at"]
    )

    # ── Runaway holds (cd:B-09) ──────────────────────────────────────────────
    op.create_table(
        "budget_runaway_holds",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("subject_type", sa.String(16), nullable=False),
        sa.Column("subject_id", sa.Text, nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by", PGUUID(as_uuid=True), nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", _TS, nullable=False),
        sa.Column("released_at", _TS, nullable=True),
        sa.Column("released_by", PGUUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_budget_runaway_holds_subject",
        "budget_runaway_holds",
        ["workspace_id", "subject_type", "subject_id"],
    )

    # ── Queued webhook delivery (F-22) ───────────────────────────────────────
    op.add_column("budget_notification_deliveries", sa.Column("payload", JSONB, nullable=True))
    op.add_column("budget_notification_deliveries", sa.Column("next_attempt_at", _TS, nullable=True))
    op.add_column(
        "budget_notification_deliveries",
        sa.Column("breach_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_budget_notification_deliveries_due",
        "budget_notification_deliveries",
        ["status", "next_attempt_at"],
    )

    # ── Cache-write pricing (F-25) ───────────────────────────────────────────
    op.add_column(
        "provider_pricing", sa.Column("cache_write_cost_per_1m", sa.Numeric(14, 8), nullable=True)
    )

    # ── Sealed ledger snapshots (cd:M-02) ────────────────────────────────────
    op.add_column("ledger_snapshots", sa.Column("prev_hash", sa.Text, nullable=True))
    op.add_column("ledger_snapshots", sa.Column("entries_root", sa.Text, nullable=True))
    op.add_column("ledger_snapshots", sa.Column("entry_count", sa.Integer, nullable=True))
    op.add_column("ledger_snapshots", sa.Column("sealed_at", _TS, nullable=True))
    op.create_table(
        "ledger_snapshot_entries",
        sa.Column(
            "snapshot_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("ledger_snapshots.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("provider_call_id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("row_hash", sa.String(64), nullable=False),
        sa.Column("cost_usd", sa.Numeric(14, 8), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ledger_snapshot_entries")
    for col in ("sealed_at", "entry_count", "entries_root", "prev_hash"):
        op.drop_column("ledger_snapshots", col)
    op.drop_column("provider_pricing", "cache_write_cost_per_1m")
    op.drop_index(
        "ix_budget_notification_deliveries_due", table_name="budget_notification_deliveries"
    )
    for col in ("breach_id", "next_attempt_at", "payload"):
        op.drop_column("budget_notification_deliveries", col)
    op.drop_index("ix_budget_runaway_holds_subject", table_name="budget_runaway_holds")
    op.drop_table("budget_runaway_holds")
    op.drop_index("ix_budget_spend_calls_workspace", table_name="budget_spend_calls")
    op.drop_table("budget_spend_calls")
    op.drop_table("budget_spend")
    op.execute("DROP INDEX IF EXISTS uq_budgets_active_scope")

    op.create_table(
        "model_budgets",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("api_key_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("model_pattern", sa.String(255), nullable=False),
        sa.Column("max_spend_usd", sa.Numeric(14, 6), nullable=True),
        sa.Column("period_type", sa.String(16), nullable=False, server_default="monthly"),
        sa.Column("rpm_limit", sa.Integer, nullable=True),
        sa.Column("tpm_limit", sa.Integer, nullable=True),
        sa.Column("action", sa.String(16), nullable=False, server_default="block"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_model_budgets_key", "model_budgets", ["api_key_id", "is_active"])
    op.execute(
        """
        INSERT INTO model_budgets
            (id, api_key_id, model_pattern, max_spend_usd, period_type, action, is_active,
             created_at)
        SELECT id, api_key_id, scope_id,
               limit_usd, CASE WHEN period_type = 'weekly' THEN 'monthly' ELSE period_type END,
               action, is_active, created_at
        FROM budgets WHERE scope_type = 'model' AND api_key_id IS NOT NULL
        """
    )
    op.execute("DELETE FROM budgets WHERE scope_type = 'model'")
    op.execute("UPDATE budgets SET period_type = 'monthly' WHERE period_type = 'weekly'")
    op.drop_column("budgets", "api_key_id")
