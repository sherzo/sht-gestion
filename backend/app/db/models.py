"""Modelos de usuarios, sesiones y auditoría (RF-44 a RF-46).

Detalle y reglas: specs/001-usuarios-autenticacion-permisos/data-model.md y
docs/modelo-de-datos.md §3.1. La migración 0002 crea exactamente estas tablas.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

USERNAME_PATTERN = r"^[a-z0-9._-]{3,30}$"
ACTION_PATTERN = r"^[a-z_]+\.[a-z_]+$"
REVOKED_REASONS = (
    "logout",
    "password_changed",
    "password_reset",
    "user_deactivated",
    "token_reuse",
)


def _uuid7() -> uuid.UUID:
    return uuid.uuid7()


def _in_list(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class AppUser(Base):
    """Usuario del sistema; nunca se borra (FR-016). `user` es palabra reservada."""

    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint(f"username ~ '{USERNAME_PATTERN}'", name="username_format"),
        CheckConstraint(
            "char_length(full_name) BETWEEN 1 AND 100 AND full_name = btrim(full_name)",
            name="full_name_length",
        ),
        CheckConstraint(_in_list("role", ("admin", "seller", "warehouse")), name="role_valid"),
        CheckConstraint("pin_hash IS NULL OR role = 'admin'", name="pin_only_admin"),
        CheckConstraint("pin_failed_attempts >= 0", name="pin_failed_attempts_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    username: Mapped[str] = mapped_column(Text, unique=True)
    full_name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    pin_hash: Mapped[str | None] = mapped_column(Text)
    pin_failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    pin_locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserSession(Base):
    """Jornada de trabajo: vence 12 horas después de ingresar la contraseña (FR-005)."""

    __tablename__ = "user_session"
    __table_args__ = (
        CheckConstraint("expires_at > started_at", name="expires_after_start"),
        CheckConstraint(
            f"revoked_reason IS NULL OR {_in_list('revoked_reason', REVOKED_REASONS)}",
            name="revoked_reason_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"), index=True)
    # Sin FK hasta que la etapa 1.3 cree la tabla `device`.
    device_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(Text)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RefreshToken(Base):
    """Token de renovación rotativo; solo se guarda su hash (research R4)."""

    __tablename__ = "refresh_token"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("user_session.id"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("refresh_token.id"))


class AuditLog(Base):
    """Registro de auditoría de solo inserción (RF-46). Un trigger impide modificarlo."""

    __tablename__ = "audit_log"
    __table_args__ = (CheckConstraint(f"action ~ '{ACTION_PATTERN}'", name="action_format"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
