"""Gastos frecuentes de las compras (RF-14/FR-032, research R9).

Solo el Admin los mantiene; Admin y Almacén los eligen al registrar una compra. La
compra copia sus datos, así que editar la lista no cambia las compras existentes.
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import AppUser, ChargeTemplate
from app.domain.money import validate_percent, validate_usd_amount, validate_ves
from app.services.audit import record_audit


def _snapshot(template: ChargeTemplate) -> dict[str, Any]:
    return {
        "name": template.name,
        "charge_type": template.charge_type,
        "default_value": None if template.default_value is None else str(template.default_value),
        "currency": template.currency,
        "is_active": template.is_active,
    }


def _validate(
    charge_type: str, default_value: Decimal | None, currency: str | None
) -> Decimal | None:
    if charge_type == "percent" and currency is not None:
        raise validation_error({"currency": "Un gasto por porcentaje no lleva moneda"})
    if charge_type == "fixed" and currency is None:
        raise validation_error({"currency": "Indica la moneda del monto"})
    if default_value is None:
        return None
    try:
        if charge_type == "percent":
            return validate_percent(default_value)
        return (
            validate_ves(default_value) if currency == "VES" else validate_usd_amount(default_value)
        )
    except ValueError as exc:
        raise validation_error({"default_value": str(exc)}) from exc


def _name_in_use(db: Session, name: str, own_id: uuid.UUID | None = None) -> None:
    other = db.scalar(
        select(ChargeTemplate).where(
            func.lower(ChargeTemplate.name) == name.lower(), ChargeTemplate.is_active.is_(True)
        )
    )
    if other is not None and other.id != own_id:
        raise ApiError(
            409, "template_name_in_use", f"Ya hay un gasto frecuente llamado {other.name}"
        )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:  # el mismo nombre guardado al mismo tiempo
        db.rollback()
        raise ApiError(
            409, "template_name_in_use", "Ya hay un gasto frecuente con ese nombre"
        ) from exc


def create_template(
    db: Session,
    *,
    actor: AppUser,
    name: str,
    charge_type: str,
    default_value: Decimal | None,
    currency: str | None,
) -> ChargeTemplate:
    value = _validate(charge_type, default_value, currency)
    _name_in_use(db, name)
    now = utcnow()
    template = ChargeTemplate(
        id=uuid.uuid7(),
        name=name,
        charge_type=charge_type,
        default_value=value,
        currency=currency,
        is_active=True,
        created_by=actor.id,
        created_at=now,
        updated_at=now,
    )
    db.add(template)
    record_audit(
        db,
        action="charge_template.created",
        user_id=actor.id,
        entity_type="charge_template",
        entity_id=template.id,
        after=_snapshot(template),
    )
    _commit(db)
    return template


def update_template(
    db: Session, *, actor: AppUser, template_id: uuid.UUID, changes: dict[str, Any]
) -> ChargeTemplate:
    template = db.get(ChargeTemplate, template_id, with_for_update=True)
    if template is None:
        raise ApiError(404, "not_found", "El gasto frecuente no existe")
    before = _snapshot(template)
    currency = changes.get("currency", template.currency)
    value = changes.get("default_value", template.default_value)
    template.default_value = _validate(template.charge_type, value, currency)
    template.currency = currency
    if "name" in changes:
        template.name = changes["name"]
    if "is_active" in changes:
        template.is_active = changes["is_active"]
    if template.is_active:
        _name_in_use(db, template.name, template.id)
    after = _snapshot(template)
    if after != before:
        template.updated_at = utcnow()
        record_audit(
            db,
            action="charge_template.updated",
            user_id=actor.id,
            entity_type="charge_template",
            entity_id=template.id,
            before=before,
            after=after,
        )
    _commit(db)
    return template


def list_templates(db: Session, *, include_inactive: bool) -> list[ChargeTemplate]:
    query = select(ChargeTemplate)
    if not include_inactive:
        query = query.where(ChargeTemplate.is_active.is_(True))
    return list(db.scalars(query.order_by(func.lower(ChargeTemplate.name))))
