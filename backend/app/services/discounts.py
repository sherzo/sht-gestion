"""Autorizaciones de descuento del Vendedor (RF-22, RN-07; FR-023 a FR-027; research R8).

Una sola tabla para los dos métodos:

- **PIN**: el Admin escribe su usuario y PIN en el equipo; se valida en el servidor (con
  el bloqueo de 5 intentos de la etapa 1.1a) y la autorización nace aprobada. El PIN nunca
  se guarda ni viaja en la venta.
- **Solicitud**: queda pendiente hasta que el Admin la aprueba (tal cual o con un valor
  menor del mismo tipo) o la rechaza desde su sesión.

La autorización queda atada a la venta y la línea (ids generados en el equipo), al tipo, al
valor autorizado y al monto base: si algo cambia, no coincide y hay que pedirla de nuevo.
La venta la usa en `services/sales.py`.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import AppUser, Device, DiscountAuthorization
from app.domain.money import validate_usd
from app.domain.roles import Role
from app.domain.sale_math import DiscountInput, discount_amount
from app.services.audit import record_audit
from app.services.pin import verify_admin_pin

MAX_BASE = Decimal("1E12")


@dataclass(frozen=True)
class AuthorizationRequest:
    method: str  # "pin" | "request"
    sale_id: uuid.UUID
    sale_item_id: uuid.UUID | None
    product_id: uuid.UUID | None
    discount_type: str
    discount_value: Decimal
    base_usd: Decimal
    admin_username: str | None = None
    pin: str | None = None


def _discount_usd(discount_type: str, value: Decimal, base: Decimal, field: str) -> Decimal:
    try:
        return discount_amount(DiscountInput(discount_type, value), base)
    except ValueError as exc:
        raise validation_error({field: str(exc)}) from exc


def _snapshot(authorization: DiscountAuthorization) -> dict[str, str | None]:
    return {
        "sale_id": str(authorization.sale_id),
        "sale_item_id": str(authorization.sale_item_id) if authorization.sale_item_id else None,
        "discount_type": authorization.discount_type,
        "requested_value": str(authorization.requested_value),
        "discount_value": str(authorization.discount_value),
        "base_usd": str(authorization.base_usd),
        "discount_usd": str(authorization.discount_usd),
        "method": authorization.method,
        "status": authorization.status,
    }


def request_authorization(
    db: Session, *, device: Device, user: AppUser, data: AuthorizationRequest
) -> DiscountAuthorization:
    """Crea la autorización: aprobada si el PIN es correcto, pendiente si es solicitud."""
    try:
        base = validate_usd(data.base_usd, 2, allow_zero=True, maximum=MAX_BASE)
    except ValueError as exc:
        raise validation_error({"base_usd": str(exc)}) from exc
    amount = _discount_usd(data.discount_type, data.discount_value, base, "discount_value")

    admin: AppUser | None = None
    if data.method == "pin":
        if not data.admin_username or not data.pin:
            raise validation_error({"pin": "Escribe el usuario y el PIN del administrador"})
        # Valida antes de escribir nada: un fallo descarta lo pendiente y guarda el intento.
        admin = verify_admin_pin(
            db, requester=user, admin_username=data.admin_username, pin=data.pin
        )

    now = utcnow()
    authorization = DiscountAuthorization(
        id=uuid.uuid7(),
        sale_id=data.sale_id,
        sale_item_id=data.sale_item_id,
        product_id=data.product_id,
        discount_type=data.discount_type,
        requested_value=data.discount_value,
        discount_value=data.discount_value,
        base_usd=base,
        discount_usd=amount,
        method=data.method,
        status="approved" if admin else "pending",
        requested_by=user.id,
        requested_at=now,
        device_id=device.id,
        decided_by=admin.id if admin else None,
        decided_at=now if admin else None,
    )
    db.add(authorization)
    db.flush()
    record_audit(
        db,
        action="discount_authorization.requested",
        user_id=user.id,
        device_id=device.id,
        entity_type="discount_authorization",
        entity_id=authorization.id,
        after=_snapshot(authorization),
    )
    return authorization


def get_authorization(
    db: Session, *, user: AppUser, authorization_id: uuid.UUID
) -> DiscountAuthorization:
    """El Admin ve todas; el Vendedor solo las suyas (las ajenas son 404)."""
    authorization = db.get(DiscountAuthorization, authorization_id)
    if authorization is None or (
        user.role != Role.ADMIN.value and authorization.requested_by != user.id
    ):
        raise ApiError(404, "not_found", "La solicitud de descuento no existe")
    return authorization


def list_pending(db: Session) -> list[DiscountAuthorization]:
    return list(
        db.scalars(
            select(DiscountAuthorization)
            .where(DiscountAuthorization.status == "pending")
            .order_by(DiscountAuthorization.requested_at)
        )
    )


def _lock_pending(db: Session, authorization_id: uuid.UUID) -> DiscountAuthorization:
    authorization = db.get(DiscountAuthorization, authorization_id, with_for_update=True)
    if authorization is None:
        raise ApiError(404, "not_found", "La solicitud de descuento no existe")
    if authorization.status != "pending":
        raise ApiError(409, "invalid_state", "La solicitud ya fue decidida")
    return authorization


def approve(
    db: Session, *, actor: AppUser, authorization_id: uuid.UUID, discount_value: Decimal | None
) -> DiscountAuthorization:
    """Aprueba tal cual o con un valor del mismo tipo, mayor que cero y no mayor que el
    pedido (aclaración del dueño, FR-025)."""
    authorization = _lock_pending(db, authorization_id)
    before = _snapshot(authorization)
    if discount_value is not None:
        if discount_value > authorization.requested_value:
            raise validation_error({"discount_value": "No puede ser mayor que el descuento pedido"})
        authorization.discount_usd = _discount_usd(
            authorization.discount_type, discount_value, authorization.base_usd, "discount_value"
        )
        authorization.discount_value = discount_value
    authorization.status = "approved"
    authorization.decided_by = actor.id
    authorization.decided_at = utcnow()
    record_audit(
        db,
        action="discount_authorization.approved",
        user_id=actor.id,
        entity_type="discount_authorization",
        entity_id=authorization.id,
        before=before,
        after=_snapshot(authorization),
    )
    return authorization


def reject(
    db: Session, *, actor: AppUser, authorization_id: uuid.UUID, reason: str | None
) -> DiscountAuthorization:
    authorization = _lock_pending(db, authorization_id)
    before = _snapshot(authorization)
    authorization.status = "rejected"
    authorization.decided_by = actor.id
    authorization.decided_at = utcnow()
    authorization.rejection_reason = (reason or "").strip() or None
    record_audit(
        db,
        action="discount_authorization.rejected",
        user_id=actor.id,
        entity_type="discount_authorization",
        entity_id=authorization.id,
        before=before,
        after=_snapshot(authorization),
        reason=authorization.rejection_reason,
    )
    return authorization
