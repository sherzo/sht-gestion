"""Tasa BCV: carga, corrección auditada y tasa aplicable por fecha (RF-17, RN-03, RN-15;
FR-012, FR-025 a FR-028; research R6).

La etapa 1.2 adelanta la carga de la tasa de la 1.3 para las compras en Bs; las ventas
la usarán desde este mismo servicio. Las compras copian el valor de la tasa, así que una
corrección no cambia las ya confirmadas (RN-05).
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import AppUser, ExchangeRate
from app.domain.business_time import business_date
from app.domain.money import validate_rate
from app.services.audit import record_audit

BCV = "BCV"


@dataclass(frozen=True)
class ApplicableRate:
    rate: Decimal
    business_date: date


def applicable_rate(db: Session, on_date: date) -> ApplicableRate | None:
    """La última tasa BCV cargada en o antes de la fecha (FR-012, RF-18)."""
    row = db.execute(
        select(ExchangeRate.rate, ExchangeRate.business_date)
        .where(ExchangeRate.rate_type == BCV, ExchangeRate.business_date <= on_date)
        .order_by(ExchangeRate.business_date.desc())
        .limit(1)
    ).first()
    return None if row is None else ApplicableRate(rate=row.rate, business_date=row.business_date)


def exchange_rate_missing(on_date: date) -> ApiError:
    return ApiError(
        409,
        "exchange_rate_missing",
        "No hay tasa BCV cargada para esa fecha ni para días anteriores: el Admin debe "
        "cargarla primero",
        date=on_date.isoformat(),
    )


def require_rate(db: Session, on_date: date) -> ApplicableRate:
    rate = applicable_rate(db, on_date)
    if rate is None:
        raise exchange_rate_missing(on_date)
    return rate


def _rate_value(value: Decimal) -> Decimal:
    try:
        return validate_rate(value)
    except ValueError as exc:
        raise validation_error({"rate": str(exc)}) from exc


def _not_future(on_date: date) -> None:
    if on_date > business_date(utcnow()):
        raise validation_error({"business_date": "La fecha no puede ser futura"})


def get_rate(db: Session, on_date: date) -> ExchangeRate | None:
    return db.scalar(
        select(ExchangeRate).where(
            ExchangeRate.rate_type == BCV, ExchangeRate.business_date == on_date
        )
    )


def create_rate(db: Session, *, actor: AppUser, on_date: date, rate: Decimal) -> ExchangeRate:
    """Carga la tasa de una fecha; si ya existe se corrige con `correct_rate` (FR-025)."""
    _not_future(on_date)
    value = _rate_value(rate)
    if get_rate(db, on_date) is not None:
        raise ApiError(
            409,
            "rate_exists",
            "Ya hay una tasa BCV para esa fecha: corrígela en lugar de cargar otra",
            business_date=on_date.isoformat(),
        )
    row = ExchangeRate(
        id=uuid.uuid7(),
        rate_type=BCV,
        business_date=on_date,
        rate=value,
        created_by=actor.id,
        created_at=utcnow(),
    )
    db.add(row)
    record_audit(
        db,
        action="exchange_rate.created",
        user_id=actor.id,
        entity_type="exchange_rate",
        entity_id=row.id,
        after={"business_date": on_date.isoformat(), "rate": str(value)},
    )
    try:
        db.commit()
    except IntegrityError as exc:  # dos cargas simultáneas de la misma fecha
        db.rollback()
        raise ApiError(409, "rate_exists", "Ya hay una tasa BCV para esa fecha") from exc
    return row


def correct_rate(db: Session, *, actor: AppUser, on_date: date, rate: Decimal) -> ExchangeRate:
    """Corrige la tasa de una fecha con auditoría (RN-15/FR-026). Las compras
    confirmadas conservan la tasa que copiaron (FR-028)."""
    value = _rate_value(rate)
    row = db.scalar(
        select(ExchangeRate)
        .where(ExchangeRate.rate_type == BCV, ExchangeRate.business_date == on_date)
        .with_for_update()
    )
    if row is None:
        raise ApiError(404, "not_found", "No hay tasa BCV cargada para esa fecha")
    before = row.rate
    row.rate = value
    row.updated_by = actor.id
    row.updated_at = utcnow()
    record_audit(
        db,
        action="exchange_rate.corrected",
        user_id=actor.id,
        entity_type="exchange_rate",
        entity_id=row.id,
        before={"business_date": on_date.isoformat(), "rate": str(before)},
        after={"business_date": on_date.isoformat(), "rate": str(value)},
    )
    db.commit()
    return row


def list_rates(db: Session, *, page: int, page_size: int) -> tuple[list[ExchangeRate], int]:
    """Histórico de la más reciente a la más antigua (FR-027)."""
    query = select(ExchangeRate).where(ExchangeRate.rate_type == BCV)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(ExchangeRate.business_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total
