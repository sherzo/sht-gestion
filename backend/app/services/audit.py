"""Registro de auditoría de acciones sensibles (RF-46, RNF-08, principio II).

`record_audit` agrega el registro a la transacción en curso: la acción y su auditoría se
confirman juntas o no ocurre ninguna (FR-022). Nunca se guardan contraseñas ni PIN
(FR-021).
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.db.models import AppUser, AuditLog
from app.domain.business_time import day_bounds_utc

# Campos que jamás deben llegar a la auditoría, en ningún nivel del JSON.
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "current_password",
        "new_password",
        "pin",
        "pin_hash",
        "setup_code",
        "token",
        "refresh_token",
        "access_token",
    }
)


def _assert_no_secrets(data: Any, path: str = "") -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).lower() in SENSITIVE_KEYS:
                raise ValueError(f"La auditoría no puede guardar el campo sensible {path}{key}")
            _assert_no_secrets(value, f"{path}{key}.")
    elif isinstance(data, list):
        for item in data:
            _assert_no_secrets(item, path)


def record_audit(
    db: Session,
    *,
    action: str,
    user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    for data in (before, after, details):
        _assert_no_secrets(data)
    entry = AuditLog(
        occurred_at=utcnow(),
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        reason=reason,
        details=details,
    )
    db.add(entry)
    return entry


def query_audit(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[tuple[AuditLog, AppUser | None]], int]:
    """Consulta con filtros, más recientes primero (FR-025). Las fechas son días de
    negocio en America/Caracas. `action` admite un código, varios separados por coma o
    un prefijo terminado en punto."""
    conditions = []
    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)
    if action:
        if "," in action:
            # Varias acciones exactas (un grupo de la pantalla de auditoría).
            codes = [code.strip() for code in action.split(",") if code.strip()]
            conditions.append(AuditLog.action.in_(codes))
        elif action.endswith("."):
            conditions.append(AuditLog.action.startswith(action, autoescape=True))
        else:
            conditions.append(AuditLog.action == action)
    if date_from is not None:
        start, _ = day_bounds_utc(date_from, date_from)
        conditions.append(AuditLog.occurred_at >= start)
    if date_to is not None:
        _, end = day_bounds_utc(date_to, date_to)
        conditions.append(AuditLog.occurred_at < end)

    total = db.scalar(select(func.count()).select_from(AuditLog).where(*conditions))
    rows = db.execute(
        select(AuditLog, AppUser)
        .outerjoin(AppUser, AppUser.id == AuditLog.user_id)
        .where(*conditions)
        .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [(entry, user) for entry, user in rows], total
