"""IP ACL: access-group scope replaces the legacy team scope (review G-18).

- ip_acl_rules.access_group_id: rule applies to requests whose principal user is a
  member of the access group.
- Existing scope_type="team" rules are mapped to the access group with the same name
  (case-insensitive) in the rule's workspace and become scope_type="access_group".
  Unmapped team rules keep team_name and stay inert (they never match) until an admin
  reassigns or deletes them; the Security page lists them as legacy.

Revision ID: 095_ip_acl_access_groups
Revises: 094_billing_chargeback
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "095_ip_acl_access_groups"
down_revision = "094_billing_chargeback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ip_acl_rules",
        sa.Column(
            "access_group_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("access_groups.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_ip_acl_rules_access_group_id", "ip_acl_rules", ["access_group_id"])
    op.execute(
        """
        UPDATE ip_acl_rules AS r
        SET access_group_id = g.id, scope_type = 'access_group'
        FROM access_groups AS g
        WHERE r.team_name IS NOT NULL
          AND r.workspace_id = g.workspace_id
          AND lower(g.name) = lower(r.team_name)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE ip_acl_rules AS r
        SET team_name = COALESCE(r.team_name, g.name), scope_type = 'team'
        FROM access_groups AS g
        WHERE r.access_group_id = g.id
        """
    )
    op.drop_index("ix_ip_acl_rules_access_group_id", table_name="ip_acl_rules")
    op.drop_column("ip_acl_rules", "access_group_id")
