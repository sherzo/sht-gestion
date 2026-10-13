"""Inventario: movimientos del kardex (RF-08 a RF-11, RN-08, research R2).

`post_movement` es la única función del backend que cambia el stock: bloquea el
producto, calcula el saldo e inserta el movimiento. El trigger de la base verifica el
saldo y actualiza `product.stock`, así que ni un error de programación ni una consulta
manual pueden escribir el stock directamente (principio II). No confirma la
transacción: quien la llama agrega su auditoría y confirma todo junto (FR-021).
"""

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError
from app.db.models import Product, StockMovement


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
