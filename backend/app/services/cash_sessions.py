"""Apertura de caja en un equipo (RF-29, RF-30, RN-16; FR-005 a FR-008; research R7).

Llega por la cola de salida (`cash_session.open`) con el id generado en el equipo. Un
equipo tiene como máximo una caja abierta; quien la abre responde por ella. Egresos,
cierre y cuadre llegan en la etapa 1.4.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import AppUser, CashSession, Device
from app.domain.business_time import business_date
from app.services.audit import record_audit
from app.services.devices import open_cash_session as current_open_session
from app.services.exchange_rates import applicable_rate, exchange_rate_missing


def open_cash_session(
    db: Session,
    *,
    device: Device,
    user: AppUser,
    operation_id: uuid.UUID,
    session_id: uuid.UUID,
    float_ves: Decimal,
    float_usd: Decimal,
    opened_at: datetime,
) -> CashSession:
    """Abre la caja del equipo. 409 `cash_session_open` si ya hay una abierta y 409
    `exchange_rate_missing` si no hay ninguna tasa BCV cargada (RF-18)."""
    # El bloqueo del equipo serializa dos aperturas simultáneas en el mismo equipo.
    db.execute(select(Device.id).where(Device.id == device.id).with_for_update())
    existing = current_open_session(db, device.id)
    if existing is not None:
        opener = db.get(AppUser, existing.opened_by)
        raise ApiError(
            409,
            "cash_session_open",
            f"Este equipo ya tiene la caja abierta por {opener.full_name}",
            opened_by=opener.full_name,
            opened_at=existing.opened_at.isoformat(),
        )
    day = business_date(opened_at)
    if applicable_rate(db, day) is None:
        raise exchange_rate_missing(day)

    session = CashSession(
        id=session_id,
        device_id=device.id,
        business_date=day,
        opened_by=user.id,
        opened_at=opened_at,
        opening_float_ves=float_ves,
        opening_float_usd=float_usd,
        status="open",
        outbox_operation_id=operation_id,
    )
    db.add(session)
    db.flush()
    record_audit(
        db,
        action="cash_session.opened",
        user_id=user.id,
        device_id=device.id,
        entity_type="cash_session",
        entity_id=session.id,
        after={"opening_float_ves": str(float_ves), "opening_float_usd": str(float_usd)},
    )
    return session
