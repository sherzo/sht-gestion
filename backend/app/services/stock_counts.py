"""Conteo físico (RF-12, RN-19; FR-024 a FR-027, FR-025a; research R8).

- El Almacén o el Admin abren un conteo de todo el inventario, de categorías o de
  productos elegidos. Un producto no puede estar en dos conteos abiertos: lo impide un
  índice único parcial sobre las líneas abiertas, aun con aperturas simultáneas.
- Al anotar se guarda el stock del sistema en ese momento; la diferencia se calcula
  contra él, así las compras o ventas posteriores no se pierden ni se duplican (FR-025).
- Solo el Admin aplica: cada diferencia se convierte en un ajuste "conteo físico", todo
  junto o nada. El Almacén cuenta a ciegas (los esquemas de la API no le envían el
  stock esperado ni la diferencia).
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import AppUser, Category, Product, StockCount, StockCountLine, Unit
from app.domain.roles import Role
from app.domain.units import format_quantity, validate_quantity
from app.services.audit import record_audit
from app.services.inventory import apply_adjustment, lock_product


def _invalid_state(message: str) -> ApiError:
    return ApiError(409, "invalid_state", message)


def get_count(db: Session, count_id: uuid.UUID, *, lock: bool = False) -> StockCount:
    count = db.get(StockCount, count_id, with_for_update=lock, populate_existing=lock)
    if count is None:
        raise ApiError(404, "not_found", "El conteo no existe")
    return count


def count_lines(db: Session, count_id: uuid.UUID) -> list[StockCountLine]:
    return list(
        db.scalars(
            select(StockCountLine)
            .join(Product, Product.id == StockCountLine.product_id)
            .where(StockCountLine.stock_count_id == count_id)
            .order_by(Product.name, Product.sku)
        )
    )


def list_counts(db: Session, *, status: str | None = None) -> list[tuple[StockCount, int, int]]:
    """Conteos con su avance (líneas anotadas / total), más recientes primero."""
    progress = (
        select(
            StockCountLine.stock_count_id,
            func.count().label("total"),
            func.count(StockCountLine.counted_quantity).label("counted"),
        )
        .group_by(StockCountLine.stock_count_id)
        .subquery()
    )
    query = (
        select(StockCount, progress.c.total, progress.c.counted)
        .outerjoin(progress, progress.c.stock_count_id == StockCount.id)
        .order_by(StockCount.started_at.desc())
    )
    if status is not None:
        query = query.where(StockCount.status == status)
    return [(count, total or 0, counted or 0) for count, total, counted in db.execute(query)]


def _scope_products(db: Session, scope: dict[str, Any]) -> list[uuid.UUID]:
    """Productos del alcance: con todo o por categorías, los activos y los inactivos que
    todavía tienen stock (FR-007); por productos, los elegidos, activos o no."""
    kind = scope["type"]
    if kind == "products":
        ids = list(dict.fromkeys(scope.get("ids") or []))
        found = set(db.scalars(select(Product.id).where(Product.id.in_(ids))))
        if not ids or found != set(ids):
            raise validation_error({"scope.ids": "Elige productos que existan"})
        return ids
    query = select(Product.id).where(or_(Product.is_active.is_(True), Product.stock != 0))
    if kind == "categories":
        ids = list(dict.fromkeys(scope.get("ids") or []))
        found = set(db.scalars(select(Category.id).where(Category.id.in_(ids))))
        if not ids or found != set(ids):
            raise validation_error({"scope.ids": "Elige categorías que existan"})
        query = query.where(Product.category_id.in_(ids))
    return list(db.scalars(query.order_by(Product.name)))


def _conflicts(db: Session, product_ids: list[uuid.UUID]) -> list[str]:
    return list(
        db.scalars(
            select(Product.sku)
            .join(StockCountLine, StockCountLine.product_id == Product.id)
            .where(StockCountLine.is_open.is_(True), Product.id.in_(product_ids))
            .order_by(Product.sku)
        )
    )


def _in_open_count(skus: list[str]) -> ApiError:
    return ApiError(
        409,
        "product_in_open_count",
        "Hay productos que ya están en otro conteo abierto",
        skus=skus,
    )


def open_count(
    db: Session, *, actor: AppUser, scope: dict[str, Any], notes: str | None
) -> StockCount:
    product_ids = _scope_products(db, scope)
    if not product_ids:
        raise validation_error({"scope": "El conteo no tiene productos"})
    conflicts = _conflicts(db, product_ids)
    if conflicts:
        raise _in_open_count(conflicts)
    stored_scope = {"type": scope["type"]}
    if scope["type"] != "all":
        stored_scope["ids"] = [str(item) for item in scope["ids"]]
    count = StockCount(
        status="open",
        scope=stored_scope,
        notes=notes,
        started_by=actor.id,
        started_at=utcnow(),
    )
    db.add(count)
    try:
        db.flush()
        db.add_all(
            StockCountLine(stock_count_id=count.id, product_id=product_id, is_open=True)
            for product_id in product_ids
        )
        db.flush()
    except IntegrityError as exc:
        # Otra apertura simultánea ganó el índice único parcial (FR-024).
        db.rollback()
        raise _in_open_count(_conflicts(db, product_ids)) from exc
    record_audit(
        db,
        action="stock_count.opened",
        user_id=actor.id,
        entity_type="stock_count",
        entity_id=count.id,
        details={"scope": stored_scope, "lines": len(product_ids), "notes": notes},
    )
    db.commit()
    return count


def record_line(
    db: Session,
    *,
    actor: AppUser,
    count_id: uuid.UUID,
    line_id: uuid.UUID,
    counted: Decimal,
) -> StockCountLine:
    """Anota lo contado y guarda el stock del sistema de ese momento (FR-025)."""
    count = get_count(db, count_id, lock=True)
    if count.status != "open":
        raise _invalid_state("Solo se anota con el conteo abierto")
    line = db.get(StockCountLine, line_id)
    if line is None or line.stock_count_id != count.id:
        raise ApiError(404, "not_found", "La línea no existe")
    product = lock_product(db, line.product_id)
    unit = db.get(Unit, product.unit_id)
    try:
        quantity = validate_quantity(counted, unit.decimals, allow_zero=True, allow_negative=False)
    except ValueError as exc:
        raise validation_error({"counted_quantity": str(exc)}) from exc
    line.counted_quantity = quantity
    line.expected_quantity = product.stock
    line.counted_by = actor.id
    line.counted_at = utcnow()
    db.commit()
    return line


def mark_ready(db: Session, *, actor: AppUser, count_id: uuid.UUID) -> StockCount:
    count = get_count(db, count_id, lock=True)
    if count.status != "open":
        raise _invalid_state("Solo un conteo abierto pasa a revisión")
    count.status = "ready_for_review"
    count.ready_by = actor.id
    count.ready_at = utcnow()
    record_audit(
        db,
        action="stock_count.ready",
        user_id=actor.id,
        entity_type="stock_count",
        entity_id=count.id,
    )
    db.commit()
    return count


def reopen(db: Session, *, actor: AppUser, count_id: uuid.UUID) -> StockCount:
    """El Admin devuelve un conteo en revisión para que se vuelva a contar (FR-025a)."""
    count = get_count(db, count_id, lock=True)
    if count.status != "ready_for_review":
        raise _invalid_state("Solo se devuelve un conteo listo para revisión")
    count.status = "open"
    record_audit(
        db,
        action="stock_count.returned",
        user_id=actor.id,
        entity_type="stock_count",
        entity_id=count.id,
    )
    db.commit()
    return count


@dataclass(frozen=True)
class AppliedCount:
    count: StockCount
    adjustments: int
    negative_products: list[Product]


def apply_count(
    db: Session, *, actor: AppUser, count_id: uuid.UUID, acknowledge_uncounted: bool
) -> AppliedCount:
    """Genera un ajuste "conteo físico" por cada diferencia anotada, todo junto o nada
    (FR-026). Las líneas sin anotar no se ajustan: hay que confirmarlo. El saldo puede
    quedar negativo por salidas posteriores a la anotación; se informa."""
    count = get_count(db, count_id, lock=True)
    if count.status not in ("open", "ready_for_review"):
        raise _invalid_state("El conteo ya está aplicado o cancelado")
    lines = count_lines(db, count.id)
    uncounted = sum(1 for line in lines if line.counted_quantity is None)
    if uncounted and not acknowledge_uncounted:
        raise ApiError(
            409,
            "uncounted_lines",
            f"Quedan {uncounted} productos sin contar; no se ajustarán",
            uncounted=uncounted,
        )

    adjustments = 0
    negatives: list[Product] = []
    for line in lines:
        if line.counted_quantity is not None:
            difference = line.counted_quantity - line.expected_quantity
            if difference != 0:
                product = lock_product(db, line.product_id)
                movement = apply_adjustment(
                    db,
                    actor_id=actor.id,
                    product=product,
                    unit=db.get(Unit, product.unit_id),
                    quantity_delta=difference,
                    reason="physical_count",
                    note=None,
                    reference_type="stock_count_line",
                    reference_id=line.id,
                    allow_negative=True,
                    extra_details={"stock_count_id": str(count.id)},
                )
                line.stock_movement_id = movement.id
                adjustments += 1
                if movement.balance_after < 0:
                    negatives.append(product)
        line.is_open = False
    # Las líneas se cierran antes que el conteo: el trigger no deja tocarlas después.
    db.flush()

    count.status = "applied"
    count.closed_by = actor.id
    count.closed_at = utcnow()
    record_audit(
        db,
        action="stock_count.applied",
        user_id=actor.id,
        entity_type="stock_count",
        entity_id=count.id,
        details={
            "lines": len(lines),
            "counted": len(lines) - uncounted,
            "uncounted": uncounted,
            "adjustments": adjustments,
            "negative": [product.sku for product in negatives],
        },
    )
    db.commit()
    return AppliedCount(count=count, adjustments=adjustments, negative_products=negatives)


def cancel_count(db: Session, *, actor: AppUser, count_id: uuid.UUID, reason: str) -> StockCount:
    """Cancela sin generar movimientos y libera los productos para otro conteo. El Almacén
    solo cancela conteos abiertos; uno en revisión lo decide el Admin (FR-025a)."""
    count = get_count(db, count_id, lock=True)
    if count.status not in ("open", "ready_for_review"):
        raise _invalid_state("El conteo ya está aplicado o cancelado")
    if count.status == "ready_for_review" and actor.role != Role.ADMIN.value:
        raise ApiError(403, "forbidden", "Un conteo en revisión solo lo cancela el administrador")
    for line in count_lines(db, count.id):
        line.is_open = False
    db.flush()
    count.status = "cancelled"
    count.cancel_reason = reason
    count.closed_by = actor.id
    count.closed_at = utcnow()
    record_audit(
        db,
        action="stock_count.cancelled",
        user_id=actor.id,
        entity_type="stock_count",
        entity_id=count.id,
        reason=reason,
    )
    db.commit()
    return count


def line_difference(line: StockCountLine) -> Decimal | None:
    if line.counted_quantity is None or line.expected_quantity is None:
        return None
    return line.counted_quantity - line.expected_quantity


def quantity_str(value: Decimal | None, decimals: int) -> str | None:
    return None if value is None else format_quantity(value, decimals)
