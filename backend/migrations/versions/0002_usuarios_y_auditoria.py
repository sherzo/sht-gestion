"""Usuarios, sesiones, tokens de renovación y auditoría (RF-44, RF-45, RF-46).

Tablas de specs/001-usuarios-autenticacion-permisos/data-model.md. `audit_log` es de
solo inserción: un trigger rechaza UPDATE y DELETE (FR-023, modelo de datos §1.4).

Revisión: 0002
Anterior: 0001
Fecha: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("pin_hash", sa.Text()),
        sa.Column("pin_failed_attempts", sa.Integer(), nullable=False),
        sa.Column("pin_locked_until", TIMESTAMP),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", TIMESTAMP),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("app_user.id")),
        sa.Column("updated_at", TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("username", name=op.f("uq_app_user_username")),
        sa.CheckConstraint(
            "username ~ '^[a-z0-9._-]{3,30}$'", name=op.f("ck_app_user_username_format")
        ),
        sa.CheckConstraint(
            "char_length(full_name) BETWEEN 1 AND 100 AND full_name = btrim(full_name)",
            name=op.f("ck_app_user_full_name_length"),
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'seller', 'warehouse')", name=op.f("ck_app_user_role_valid")
        ),
        sa.CheckConstraint(
            "pin_hash IS NULL OR role = 'admin'", name=op.f("ck_app_user_pin_only_admin")
        ),
        sa.CheckConstraint(
            "pin_failed_attempts >= 0", name=op.f("ck_app_user_pin_failed_attempts_positive")
        ),
    )

    op.create_table(
        "user_session",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("device_id", sa.Uuid()),
        sa.Column("started_at", TIMESTAMP, nullable=False),
        sa.Column("expires_at", TIMESTAMP, nullable=False),
        sa.Column("revoked_at", TIMESTAMP),
        sa.Column("revoked_reason", sa.Text()),
        sa.Column("last_seen_at", TIMESTAMP, nullable=False),
        sa.CheckConstraint(
            "expires_at > started_at", name=op.f("ck_user_session_expires_after_start")
        ),
        sa.CheckConstraint(
            "revoked_reason IS NULL OR revoked_reason IN ('logout', 'password_changed', "
            "'password_reset', 'user_deactivated', 'token_reuse')",
            name=op.f("ck_user_session_revoked_reason_valid"),
        ),
    )
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"])

    op.create_table(
        "refresh_token",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("user_session.id"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMP, nullable=False),
        sa.Column("rotated_at", TIMESTAMP),
        sa.Column("replaced_by_id", sa.Uuid(), sa.ForeignKey("refresh_token.id")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_token_token_hash")),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("occurred_at", TIMESTAMP, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("app_user.id")),
        sa.Column("device_id", sa.Uuid()),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text()),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("before", postgresql.JSONB()),
        sa.Column("after", postgresql.JSONB()),
        sa.Column("reason", sa.Text()),
        sa.Column("details", postgresql.JSONB()),
        sa.CheckConstraint(
            "action ~ '^[a-z_]+\\.[a-z_]+$'", name=op.f("ck_audit_log_action_format")
        ),
    )
    op.execute("CREATE INDEX ix_audit_log_occurred_at ON audit_log (occurred_at DESC)")
    op.execute(
        "CREATE INDEX ix_audit_log_user_id_occurred_at ON audit_log (user_id, occurred_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_audit_log_action_occurred_at ON audit_log (action, occurred_at DESC)"
    )
    # Bloqueo de inicio de sesión por nombre de usuario, exista o no (FR-004, research R6).
    op.execute(
        "CREATE INDEX ix_audit_log_login_username ON audit_log "
        "((details->>'username'), occurred_at DESC) "
        "WHERE action IN ('auth.login_failed', 'auth.login_succeeded')"
    )

    # Inmutabilidad impuesta en la base (FR-023).
    op.execute(
        """
        CREATE FUNCTION audit_log_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log es de solo inserción: no se modifica ni se borra';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER audit_log_immutable BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_log_immutable()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER audit_log_immutable ON audit_log")
    op.execute("DROP FUNCTION audit_log_immutable()")
    op.drop_table("audit_log")
    op.drop_table("refresh_token")
    op.drop_index("ix_user_session_user_id", table_name="user_session")
    op.drop_table("user_session")
    op.drop_table("app_user")
