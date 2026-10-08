"""Utilidades compartidas por las pruebas de la API."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog

REFRESH_COOKIE = "sht_refresh"


def audit_actions(db: Session) -> list[str]:
    db.expire_all()
    return list(db.scalars(select(AuditLog.action).order_by(AuditLog.occurred_at, AuditLog.id)))


def audit_entries(db: Session, action: str) -> list[AuditLog]:
    db.expire_all()
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.occurred_at, AuditLog.id)
        )
    )


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
