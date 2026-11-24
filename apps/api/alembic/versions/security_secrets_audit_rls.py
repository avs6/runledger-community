"""Security stream W1-A: encrypted secrets, secret inventory, chained audit, RLS.

1. audit_events: actor_type / actor_label (S-16) and a per-chain hash chain
   (chain_key, seq, prev_hash, hash). Existing events are chained in created_at
   order so ``GET /audit/verify`` covers the whole history.
2. secret_records: one row per stored credential (secret age, rotation, timeline).
3. Encrypts every stored secret with ``core/secrets.py`` (S-03, S-04, G-05, F-15,
   B-09): OIDC/OAuth2 client secrets and LDAP bind passwords (previously
   ``<hmac>:<plaintext>``), search-provider and pass-through ``auth_config`` /
   ``header_config`` secret keys, notification webhook URLs and evaluator API
   keys, plus ledger keys left in plaintext when LEDGER_MASTER_KEY was unset
   (cd:M-03). Downgrade decrypts them again.
4. Postgres row-level security as defence in depth (tr-security): tenant tables
   get a policy keyed on the ``app.tenant_id`` / ``app.workspace_id`` settings the
   API sets per transaction. With the settings unset (workers, migrations,
   internal calls) the policy allows everything, so behaviour is unchanged.

Revision ID: security_secrets_audit_rls
Revises: governance_tool_policy
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "security_secrets_audit_rls"
down_revision = "governance_tool_policy"
branch_labels = None
depends_on = None

# (kind, table, column, is_json, legacy_hmac, label column)
SECRET_COLUMNS: list[tuple[str, str, str, bool, bool, str]] = [
    ("oidc_client_secret", "oidc_providers", "client_secret_encrypted", False, True, "name"),
    ("oauth2_client_secret", "oauth2_providers", "client_secret_encrypted", False, True, "name"),
    ("ldap_bind_password", "ldap_providers", "bind_password_encrypted", False, True, "name"),
    ("search_provider_auth", "search_tools", "auth_config", True, False, "name"),
    ("passthrough_auth", "gateway_passthrough_endpoints", "auth_config", True, False, "slug"),
    ("passthrough_headers", "gateway_passthrough_endpoints", "header_config", True, False, "slug"),
    ("notification_webhook", "budget_notifications", "destination_url", False, False, "channel"),
    ("evaluator_api_key", "evaluators", "config", True, False, "name"),
]

# Tenant tables with a NOT NULL workspace_id that get RLS (only those that exist).
RLS_TABLES = [
    "agent_runs",
    "provider_calls",
    "tool_calls",
    "spans",
    "outcome_events",
    "approvals",
    "auto_approval_policies",
    "budgets",
    "budget_notifications",
    "evaluators",
    "search_tools",
    "gateway_passthrough_endpoints",
    "gateway_requests",
    "guardrail_events",
    "oidc_providers",
    "oauth2_providers",
    "ldap_providers",
    "prompts",
    "secret_records",
]

RLS_POLICY = """
    coalesce(current_setting('app.tenant_id', true), '') = ''
    OR (
        workspace_id IN (
            SELECT w.id FROM workspaces w
            WHERE w.tenant_id::text = current_setting('app.tenant_id', true)
        )
        AND (
            coalesce(current_setting('app.workspace_id', true), '') = ''
            OR workspace_id::text = current_setting('app.workspace_id', true)
        )
    )
"""


def _existing_tables(bind: Any) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _has_not_null_workspace(bind: Any, table: str) -> bool:
    for col in sa.inspect(bind).get_columns(table):
        if col["name"] == "workspace_id":
            return not col.get("nullable", True)
    return False


def upgrade() -> None:
    from runledger_api.core import secrets
    from runledger_api.services.audit import chain_key_for, compute_hash
    from runledger_api.services.secrets_inventory import secret_id

    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    tables = _existing_tables(bind)

    # ── 1. audit chain columns ────────────────────────────────────────────────
    for name, type_ in [
        ("actor_type", sa.Text()),
        ("actor_label", sa.Text()),
        ("chain_key", sa.Text()),
        ("seq", sa.BigInteger()),
        ("prev_hash", sa.Text()),
        ("hash", sa.Text()),
    ]:
        op.add_column("audit_events", sa.Column(name, type_, nullable=True))

    rows = bind.execute(
        sa.text(
            "SELECT id, workspace_id, tenant_id, actor_user_id, actor_api_key_prefix, action,"
            " target_type, target_id, before, after, ip_hash, created_at"
            " FROM audit_events ORDER BY created_at, id"
        )
    ).mappings()
    chains: dict[str, tuple[int, str]] = {}
    for r in rows:
        actor_type = (
            "user" if r["actor_user_id"] else "api_key" if r["actor_api_key_prefix"] else "system"
        )
        key = chain_key_for(r["workspace_id"], r["tenant_id"])
        seq, prev = chains.get(key, (0, "0" * 64))
        seq += 1

        def _json(v: Any) -> Any:
            return json.loads(v) if isinstance(v, str) else v

        ev = SimpleNamespace(
            id=r["id"],
            seq=seq,
            chain_key=key,
            workspace_id=r["workspace_id"],
            tenant_id=r["tenant_id"],
            actor_user_id=r["actor_user_id"],
            actor_api_key_prefix=r["actor_api_key_prefix"],
            actor_type=actor_type,
            actor_label=None,
            action=r["action"],
            target_type=r["target_type"],
            target_id=r["target_id"],
            before=_json(r["before"]),
            after=_json(r["after"]),
            ip_hash=r["ip_hash"],
            created_at=r["created_at"],
        )
        digest = compute_hash(ev, prev)  # type: ignore[arg-type]
        bind.execute(
            sa.text(
                "UPDATE audit_events SET actor_type=:t, chain_key=:k, seq=:s, prev_hash=:p,"
                " hash=:h WHERE id=:id"
            ),
            {"t": actor_type, "k": key, "s": seq, "p": prev, "h": digest, "id": r["id"]},
        )
        chains[key] = (seq, digest)
    op.create_index("ix_audit_events_chain_seq", "audit_events", ["chain_key", "seq"], unique=True)

    # ── 2. secret inventory ───────────────────────────────────────────────────
    op.create_table(
        "secret_records",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("owner_table", sa.String(64), nullable=False),
        sa.Column("owner_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("key_id", sa.String(16), nullable=True),
        sa.Column("fingerprint", sa.String(32), nullable=True),
        sa.Column("rotation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rotated_by_user_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("rotated_by_label", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "rotated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("owner_table", "owner_id", "field", name="uq_secret_records_owner"),
    )
    op.create_index("ix_secret_records_workspace_kind", "secret_records", ["workspace_id", "kind"])

    # ── 3. encrypt stored secrets and backfill the inventory ──────────────────
    primary = secrets.primary_key_id()
    for kind, table, column, is_json, legacy_hmac, label_col in SECRET_COLUMNS:
        if table not in tables:
            continue
        cols = {c["name"] for c in sa.inspect(bind).get_columns(table)}
        created = "created_at" if "created_at" in cols else None
        updated = "updated_at" if "updated_at" in cols else created
        select_cols = ["id", "workspace_id", column, label_col]
        if created:
            select_cols.append(f"{created} AS created_at")
        if updated:
            select_cols.append(f"{updated} AS rotated_at")
        for r in bind.execute(sa.text(f"SELECT {', '.join(select_cols)} FROM {table}")).mappings():
            value = r[column]
            if value in (None, "", {}):
                continue
            if is_json:
                config = json.loads(value) if isinstance(value, str) else dict(value)
                plain = secrets.open_config(config) or {}
                material = {k: v for k, v in plain.items() if secrets.is_secret_key(k) and v}
                if not material:
                    continue
                sealed = json.dumps(secrets.seal_config(plain))
                cast = "CAST(:v AS JSONB)" if is_pg else ":v"
                bind.execute(
                    sa.text(f"UPDATE {table} SET {column} = {cast} WHERE id = :id"),
                    {"v": sealed, "id": r["id"]},
                )
                fp = secrets.fingerprint(json.dumps(material, sort_keys=True))
            else:
                plain_text = secrets.decrypt(str(value), legacy_hmac=legacy_hmac) or ""
                if not plain_text:
                    continue
                bind.execute(
                    sa.text(f"UPDATE {table} SET {column} = :v WHERE id = :id"),
                    {"v": secrets.encrypt(plain_text), "id": r["id"]},
                )
                fp = secrets.fingerprint(plain_text)
            label = r[label_col]
            bind.execute(
                sa.text(
                    "INSERT INTO secret_records (id, workspace_id, kind, owner_table, owner_id,"
                    " field, label, key_id, fingerprint, rotation_count, rotated_by_label,"
                    " created_at, rotated_at) VALUES (:id, :ws, :kind, :tbl, :oid, :field,"
                    " :label, :kid, :fp, 0, 'migration', coalesce(:created, now()),"
                    " coalesce(:rotated, :created, now()))"
                ),
                {
                    "id": secret_id(table, r["id"], column),
                    "ws": r["workspace_id"],
                    "kind": kind,
                    "tbl": table,
                    "oid": r["id"],
                    "field": column,
                    "label": f"{kind.replace('_', ' ')}: {label}" if label else kind,
                    "kid": primary,
                    "fp": fp,
                    "created": r.get("created_at"),
                    "rotated": r.get("rotated_at"),
                },
            )

    # Ledger keys stored in plaintext (LEDGER_MASTER_KEY was unset): encrypt them.
    if "ledger_keys" in tables:
        for r in bind.execute(sa.text("SELECT id, key_value FROM ledger_keys")).mappings():
            stored = r["key_value"]
            if stored and not secrets.is_encrypted(stored):
                plain_key = secrets.decrypt(stored) or ""
                bind.execute(
                    sa.text("UPDATE ledger_keys SET key_value = :v WHERE id = :id"),
                    {"v": secrets.encrypt(plain_key), "id": r["id"]},
                )

    # ── 4. row-level security ─────────────────────────────────────────────────
    if is_pg:
        tables = _existing_tables(bind)
        for table in RLS_TABLES:
            if table not in tables or not _has_not_null_workspace(bind, table):
                continue
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(
                f"CREATE POLICY rl_tenant_isolation ON {table} "
                f"USING ({RLS_POLICY}) WITH CHECK ({RLS_POLICY})"
            )


def downgrade() -> None:
    from runledger_api.core import secrets

    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    tables = _existing_tables(bind)

    if is_pg:
        for table in RLS_TABLES:
            if table not in tables:
                continue
            op.execute(f"DROP POLICY IF EXISTS rl_tenant_isolation ON {table}")
            op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Decrypt secrets so the previous code (which expects plaintext) keeps working.
    for _kind, table, column, is_json, _legacy, _label in SECRET_COLUMNS:
        if table not in tables:
            continue
        for r in bind.execute(sa.text(f"SELECT id, {column} FROM {table}")).mappings():
            value = r[column]
            if value in (None, "", {}):
                continue
            if is_json:
                config = json.loads(value) if isinstance(value, str) else dict(value)
                opened = json.dumps(secrets.open_config(config))
                cast = "CAST(:v AS JSONB)" if is_pg else ":v"
                bind.execute(
                    sa.text(f"UPDATE {table} SET {column} = {cast} WHERE id = :id"),
                    {"v": opened, "id": r["id"]},
                )
            elif secrets.is_encrypted(str(value)):
                bind.execute(
                    sa.text(f"UPDATE {table} SET {column} = :v WHERE id = :id"),
                    {"v": secrets.decrypt(str(value)), "id": r["id"]},
                )

    # Ledger keys back to plaintext: the old _decrypt_key falls back to the stored value.
    if "ledger_keys" in tables:
        for r in bind.execute(sa.text("SELECT id, key_value FROM ledger_keys")).mappings():
            if secrets.is_encrypted(r["key_value"]):
                bind.execute(
                    sa.text("UPDATE ledger_keys SET key_value = :v WHERE id = :id"),
                    {"v": secrets.decrypt(r["key_value"]), "id": r["id"]},
                )

    op.drop_index("ix_secret_records_workspace_kind", table_name="secret_records")
    op.drop_table("secret_records")
    op.drop_index("ix_audit_events_chain_seq", table_name="audit_events")
    for name in ("hash", "prev_hash", "seq", "chain_key", "actor_label", "actor_type"):
        op.drop_column("audit_events", name)
