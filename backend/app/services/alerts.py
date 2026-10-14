"""Alertas para el Admin (RN-14/FR-018, research R8).

En esta etapa solo existe `purchase_void_cost`: anular una compra no pudo recalcular el
costo de un producto y se conservó el vigente. Las etapas 1.3 y 1.5 agregan otros tipos.
"""

import uuid
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError
from app.db.models import Alert, AppUser
from app.services.audit import record_audit


def create_alert(
    db: Session, *, type: str, entity_type: str, entity_id: uuid.UUID, details: dict[str, Any]
) -> Alert:
    """Agrega la alerta sin confirmar la transacción: va junto con la operación que la
    origina."""
    alert = Alert(
        id=uuid.uuid7(),
        type=type,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        created_at=utcnow(),
    )
    db.add(alert)
    return alert


def open_alerts_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Alert).where(Alert.resolved_at.is_(None)))


def list_alerts(
    db: Session, *, status: Literal["open", "resolved"], page: int, page_size: int
) -> tuple[list[Alert], int]:
    condition = Alert.resolved_at.is_(None) if status == "open" else Alert.resolved_at.is_not(None)
    total = db.scalar(select(func.count()).select_from(Alert).where(condition))
    rows = db.scalars(
        select(Alert)
        .where(condition)
        .order_by(Alert.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def resolve_alert(db: Session, *, actor: AppUser, alert_id: uuid.UUID) -> Alert:
    alert = db.get(Alert, alert_id, with_for_update=True)
    if alert is None:
        raise ApiError(404, "not_found", "La alerta no existe")
    if alert.resolved_at is not None:
        raise ApiError(409, "invalid_state", "La alerta ya estaba marcada como revisada")
    alert.resolved_at = utcnow()
    alert.resolved_by = actor.id
    record_audit(
        db,
        action="alert.resolved",
        user_id=actor.id,
        entity_type="alert",
        entity_id=alert.id,
        details={"type": alert.type, **alert.details},
    )
    db.commit()
    return alert
