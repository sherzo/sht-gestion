"""Inventario: kardex, ajustes y solicitudes del Almacén (RF-08 a RF-11, RN-08, RN-19;
research R2 y R7).

`post_movement` es la única función del backend que cambia el stock: bloquea el
producto, calcula el saldo e inserta el movimiento. El trigger de la base verifica el
saldo y actualiza `product.stock`, así que ni un error de programación ni una consulta
manual pueden escribir el stock directamente (principio II). No confirma la
transacción: quien la llama agrega su auditoría y confirma todo junto (FR-021).
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import (
    AdjustmentRequest,
    AppUser,
    Product,
    StockCount,
    StockMovement,
    Unit,
)
from app.domain.business_time import day_bounds_utc
from app.domain.roles import Role
from app.domain.units import format_quantity, validate_quantity
from app.services.audit import record_audit


def low_stock_condition():
    """Stock bajo: producto activo con stock menor o igual al mínimo (RF-11/FR-023)."""
    return and_(Product.is_active.is_(True), Product.stock <= Product.min_stock)


def product_not_found() -> ApiError:
    return ApiError(404, "not_found", "El producto no existe")


def lock_product(db: Session, product_id: uuid.UUID) -> Product:
    """Lee el producto bloqueando su fila hasta el fin de la transacción."""
    product = db.get(Product, product_id, with_for_update=True, populate_existing=True)
    if product is None:
        raise product_not_found()
    return product


def negative_stock(stock: Decimal, delta: Decimal) -> ApiError:
    return ApiError(
        409,
        "negative_stock",
        "El stock no alcanza: la salida lo dejaría negativo",
        stock=str(stock),
        quantity_delta=str(delta),
    )


def post_movement(
    db: Session,
    *,
    product_id: uuid.UUID,
    type: str,
    quantity_delta: Decimal,
    created_by: uuid.UUID | None,
    adjustment_reason: str | None = None,
    note: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    allow_negative: bool = False,
) -> StockMovement:
    """Registra un movimiento sin confirmar la transacción.

    Una salida no puede dejar el stock negativo salvo `allow_negative` (ajuste por
    conteo, FR-026; ventas sin conexión, RN-10). Una entrada siempre se admite, aunque el
    stock siga negativo: lo acerca a cero (caso borde "stock negativo existente").
    """
    product = lock_product(db, product_id)
    balance = product.stock + quantity_delta
    if quantity_delta < 0 and balance < 0 and not allow_negative:
        raise negative_stock(product.stock, quantity_delta)
    movement = StockMovement(
        product_id=product.id,
        type=type,
        quantity_delta=quantity_delta,
        balance_after=balance,
        adjustment_reason=adjustment_reason,
        note=note,
        reference_type=reference_type,
        reference_id=reference_id,
        occurred_at=utcnow(),
        created_by=created_by,
    )
    db.add(movement)
    db.flush()
    # El trigger cambió el stock en la base: se vuelve a leer en la próxima consulta.
    db.expire(product, ["stock", "has_movements"])
    return movement


# --- Ajustes y solicitudes (RF-10, RN-19; FR-019, FR-019a, FR-019b; research R7) ----


@dataclass(frozen=True)
class AdjustmentResult:
    """Un ajuste aplicado (`movement`) o una salida del Almacén pendiente (`request`)."""

    movement: StockMovement | None = None
    request: AdjustmentRequest | None = None


def unit_of(db: Session, product: Product) -> Unit:
    return db.get(Unit, product.unit_id)


def _quantity(value: Decimal, unit: Unit) -> Decimal:
    try:
        return validate_quantity(value, unit.decimals, allow_zero=False, allow_negative=True)
    except ValueError as exc:
        raise validation_error({"quantity_delta": str(exc)}) from exc


def _stock_details(
    product: Product, unit: Unit, delta: Decimal, reason: str, note: str | None
) -> dict[str, Any]:
    return {
        "sku": product.sku,
        "quantity_delta": format_quantity(delta, unit.decimals),
        "reason": reason,
        "note": note,
        "unit_decimals": unit.decimals,
    }


def apply_adjustment(
    db: Session,
    *,
    actor_id: uuid.UUID,
    product: Product,
    unit: Unit,
    quantity_delta: Decimal,
    reason: str,
    note: str | None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    allow_negative: bool = False,
    audit_action: str = "inventory.adjustment_applied",
    extra_details: dict[str, Any] | None = None,
) -> StockMovement:
    """Genera el movimiento de un ajuste y su auditoría con el stock antes y después
    (FR-034, SC-007). No confirma la transacción."""
    before = product.stock
    movement = post_movement(
        db,
        product_id=product.id,
        type="adjustment",
        quantity_delta=quantity_delta,
        created_by=actor_id,
        adjustment_reason=reason,
        note=note,
        reference_type=reference_type,
        reference_id=reference_id,
        allow_negative=allow_negative,
    )
    record_audit(
        db,
        action=audit_action,
        user_id=actor_id,
        entity_type="product",
        entity_id=product.id,
        before={"stock": format_quantity(before, unit.decimals)},
        after={"stock": format_quantity(movement.balance_after, unit.decimals)},
        details={
            **_stock_details(product, unit, quantity_delta, reason, note),
            "movement_id": str(movement.id),
            **(extra_details or {}),
        },
    )
    return movement


def register_adjustment(
    db: Session,
    *,
    actor: AppUser,
    product_id: uuid.UUID,
    quantity_delta: Decimal,
    reason: str,
    note: str | None,
) -> AdjustmentResult:
    """Los ajustes del Admin y las entradas del Almacén se aplican de inmediato; las
    salidas del Almacén quedan pendientes de aprobación sin tocar el stock (RN-19)."""
    product = lock_product(db, product_id)
    unit = unit_of(db, product)
    delta = _quantity(quantity_delta, unit)

    if actor.role == Role.WAREHOUSE.value and delta < 0:
        if product.stock + delta < 0:
            raise negative_stock(product.stock, delta)
        request = AdjustmentRequest(
            product_id=product.id,
            quantity_delta=delta,
            adjustment_reason=reason,
            note=note,
            status="pending",
            requested_by=actor.id,
            requested_at=utcnow(),
        )
        db.add(request)
        db.flush()
        record_audit(
            db,
            action="inventory.adjustment_requested",
            user_id=actor.id,
            entity_type="adjustment_request",
            entity_id=request.id,
            details={
                **_stock_details(product, unit, delta, reason, note),
                "product_id": str(product.id),
            },
        )
        db.commit()
        return AdjustmentResult(request=request)

    movement = apply_adjustment(
        db,
        actor_id=actor.id,
        product=product,
        unit=unit,
        quantity_delta=delta,
        reason=reason,
        note=note,
    )
    db.commit()
    return AdjustmentResult(movement=movement)


def _lock_request(db: Session, request_id: uuid.UUID) -> AdjustmentRequest:
    request = db.get(AdjustmentRequest, request_id, with_for_update=True, populate_existing=True)
    if request is None:
        raise ApiError(404, "not_found", "La solicitud no existe")
    if request.status != "pending":
        raise ApiError(409, "invalid_state", "La solicitud ya fue decidida o retirada")
    return request


def approve_request(db: Session, *, actor: AppUser, request_id: uuid.UUID) -> AdjustmentRequest:
    """Revalida con el stock del momento: si bajó y la salida lo dejaría negativo, no se
    aprueba (caso borde de la spec)."""
    request = _lock_request(db, request_id)
    product = lock_product(db, request.product_id)
    unit = unit_of(db, product)
    movement = apply_adjustment(
        db,
        actor_id=actor.id,
        product=product,
        unit=unit,
        quantity_delta=request.quantity_delta,
        reason=request.adjustment_reason,
        note=request.note,
        reference_type="adjustment_request",
        reference_id=request.id,
        audit_action="inventory.adjustment_approved",
        extra_details={"request_id": str(request.id), "requested_by": str(request.requested_by)},
    )
    request.status = "approved"
    request.decided_by = actor.id
    request.decided_at = utcnow()
    request.stock_movement_id = movement.id
    db.commit()
    return request


def _close_request(
    db: Session,
    *,
    actor: AppUser,
    request: AdjustmentRequest,
    status: str,
    action: str,
    reason: str | None = None,
) -> AdjustmentRequest:
    product = db.get(Product, request.product_id)
    unit = unit_of(db, product)
    request.status = status
    request.decided_by = actor.id
    request.decided_at = utcnow()
    request.rejection_reason = reason
    record_audit(
        db,
        action=action,
        user_id=actor.id,
        entity_type="adjustment_request",
        entity_id=request.id,
        reason=reason,
        details=_stock_details(
            product, unit, request.quantity_delta, request.adjustment_reason, request.note
        ),
    )
    db.commit()
    return request


def reject_request(
    db: Session, *, actor: AppUser, request_id: uuid.UUID, reason: str
) -> AdjustmentRequest:
    request = _lock_request(db, request_id)
    return _close_request(
        db,
        actor=actor,
        request=request,
        status="rejected",
        action="inventory.adjustment_rejected",
        reason=reason,
    )


def withdraw_request(db: Session, *, actor: AppUser, request_id: uuid.UUID) -> AdjustmentRequest:
    """Solo quien la solicitó la retira; para corregirla registra otra (FR-019a)."""
    request = db.get(AdjustmentRequest, request_id)
    if request is None:
        raise ApiError(404, "not_found", "La solicitud no existe")
    if request.requested_by != actor.id:
        raise ApiError(403, "forbidden", "Solo quien hizo la solicitud puede retirarla")
    request = _lock_request(db, request_id)
    return _close_request(
        db,
        actor=actor,
        request=request,
        status="withdrawn",
        action="inventory.adjustment_withdrawn",
    )


def list_requests(
    db: Session,
    *,
    actor: AppUser,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AdjustmentRequest], int]:
    """El Admin ve todas; el Almacén, solo las suyas (FR-019b). Más recientes primero."""
    conditions = []
    if actor.role != Role.ADMIN.value:
        conditions.append(AdjustmentRequest.requested_by == actor.id)
    if status is not None:
        conditions.append(AdjustmentRequest.status == status)
    total = db.scalar(select(func.count()).select_from(AdjustmentRequest).where(*conditions))
    rows = db.scalars(
        select(AdjustmentRequest)
        .where(*conditions)
        .order_by(AdjustmentRequest.requested_at.desc(), AdjustmentRequest.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


# --- Kardex (RF-08, RF-09/FR-017, FR-022) -------------------------------------------


def list_movements(
    db: Session,
    *,
    product_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[StockMovement], int]:
    """Movimientos de un producto, más recientes primero. Las fechas son días de negocio
    en America/Caracas."""
    if db.get(Product, product_id) is None:
        raise product_not_found()
    conditions = [StockMovement.product_id == product_id]
    if date_from is not None:
        start, _ = day_bounds_utc(date_from, date_from)
        conditions.append(StockMovement.occurred_at >= start)
    if date_to is not None:
        _, end = day_bounds_utc(date_to, date_to)
        conditions.append(StockMovement.occurred_at < end)
    if type is not None:
        conditions.append(StockMovement.type == type)
    total = db.scalar(select(func.count()).select_from(StockMovement).where(*conditions))
    rows = db.scalars(
        select(StockMovement)
        .where(*conditions)
        .order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


def requesters_of(db: Session, movements: list[StockMovement]) -> dict[uuid.UUID, uuid.UUID]:
    """Para los movimientos que vienen de una solicitud aprobada: movimiento → solicitante."""
    request_ids = [
        movement.reference_id
        for movement in movements
        if movement.reference_type == "adjustment_request" and movement.reference_id
    ]
    if not request_ids:
        return {}
    rows = db.execute(
        select(AdjustmentRequest.stock_movement_id, AdjustmentRequest.requested_by).where(
            AdjustmentRequest.id.in_(request_ids)
        )
    )
    return {movement_id: requester for movement_id, requester in rows if movement_id}


# --- Resumen del inicio (research R11) -----------------------------------------------


@dataclass(frozen=True)
class InventorySummary:
    low_stock: int
    pending_requests: int
    counts_ready_for_review: int
    open_counts: int


def summary(db: Session, *, actor: AppUser) -> InventorySummary:
    """Contadores para el inicio. Las solicitudes pendientes son todas para el Admin y
    las propias para el Almacén."""
    low_stock = db.scalar(select(func.count()).select_from(Product).where(low_stock_condition()))
    pending = (
        select(func.count())
        .select_from(AdjustmentRequest)
        .where(AdjustmentRequest.status == "pending")
    )
    if actor.role != Role.ADMIN.value:
        pending = pending.where(AdjustmentRequest.requested_by == actor.id)
    by_status = dict(
        db.execute(select(StockCount.status, func.count()).group_by(StockCount.status)).all()
    )
    return InventorySummary(
        low_stock=low_stock,
        pending_requests=db.scalar(pending),
        counts_ready_for_review=by_status.get("ready_for_review", 0),
        open_counts=by_status.get("open", 0),
    )
