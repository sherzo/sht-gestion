"""Ajustes de la revisión de la etapa 1.1a (RF-44, ADR-0008).

- `user_session.revoked_reason` admite `too_many_attempts`: la sesión se cierra tras 5
  fallos al comprobar la contraseña actual.
- El índice del bloqueo de inicio de sesión incluye `auth.login_locked`, que ahora se
  consulta para saber cuándo vence el bloqueo.

Revisión: 0003
Anterior: 0002
Fecha: 2026-10-08
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REASONS = "'logout', 'password_changed', 'password_reset', 'user_deactivated', 'token_reuse'"


def _reasons_check(reasons: str) -> None:
    op.execute("ALTER TABLE user_session DROP CONSTRAINT ck_user_session_revoked_reason_valid")
    op.execute(
        "ALTER TABLE user_session ADD CONSTRAINT ck_user_session_revoked_reason_valid "
        f"CHECK (revoked_reason IS NULL OR revoked_reason IN ({reasons}))"
    )


def _login_index(actions: str) -> None:
    op.execute("DROP INDEX ix_audit_log_login_username")
    op.execute(
        "CREATE INDEX ix_audit_log_login_username ON audit_log "
        f"((details->>'username'), occurred_at DESC) WHERE action IN ({actions})"
    )


def upgrade() -> None:
    _reasons_check(f"{REASONS}, 'too_many_attempts'")
    _login_index("'auth.login_failed', 'auth.login_succeeded', 'auth.login_locked'")


def downgrade() -> None:
    op.execute(
        "UPDATE user_session SET revoked_reason = 'logout' "
        "WHERE revoked_reason = 'too_many_attempts'"
    )
    _reasons_check(REASONS)
    _login_index("'auth.login_failed', 'auth.login_succeeded'")
