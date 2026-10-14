"""Kardex: el stock solo cambia mediante movimientos (RN-08, RF-08/FR-016, FR-017, FR-021;
SC-003; research R2)."""

import threading
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.errors import ApiError
from app.db.models import Product, StockMovement
from app.db.session import get_sessionmaker
from app.services.inventory import post_movement

pytestmark = pytest.mark.db


def _move(db, product, delta: str, **kwargs) -> StockMovement:
    movement = post_movement(
        db,
        product_id=product.id,
        type="adjustment",
        quantity_delta=Decimal(delta),
        created_by=None,
        adjustment_reason="correction",
        **kwargs,
    )
    db.commit()
    return movement


def _stock(db, product) -> Decimal:
    db.expire_all()
    return db.scalar(select(Product.stock).where(Product.id == product.id))


def _sum_deltas(db, product) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity_delta), 0)).where(
            StockMovement.product_id == product.id
        )
    )
    return Decimal(total)


def test_saldo_encadenado(db, make_product) -> None:
    """RF-08/FR-017: cada movimiento guarda el stock resultante."""
    product = make_product("MAN")
    first = _move(db, product, "10.50")
    second = _move(db, product, "-2.25")
    assert first.balance_after == Decimal("10.50")
    assert second.balance_after == Decimal("8.25")
    assert _stock(db, product) == Decimal("8.25")
    db.refresh(product)
    assert product.has_movements is True


def test_salida_que_deja_stock_negativo_se_rechaza(db, make_product) -> None:
    """FR-019: un ajuste manual no deja el stock negativo; un conteo sí puede (FR-026)."""
    product = make_product("FER")
    _move(db, product, "3")
    with pytest.raises(ApiError) as info:
        _move(db, product, "-5")
    assert info.value.code == "negative_stock"
    db.rollback()
    assert _stock(db, product) == Decimal("3")

    _move(db, product, "-5", allow_negative=True)
    assert _stock(db, product) == Decimal("-2")
    # Una entrada se admite aunque el stock siga negativo: lo acerca a cero.
    _move(db, product, "1")
    assert _stock(db, product) == Decimal("-1")


def test_escribir_el_stock_directamente_falla(db, make_product) -> None:
    """RN-08/FR-016: no existe forma de escribir el stock sin un movimiento."""
    product = make_product("MAN")
    with pytest.raises(DBAPIError, match="solo cambia mediante movimientos"):
        db.execute(text("UPDATE product SET stock = 100 WHERE id = :id"), {"id": product.id})
    db.rollback()
    with pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE product SET has_movements = true WHERE id = :id"), {"id": product.id}
        )
    db.rollback()
    assert _stock(db, product) == Decimal("0")


def test_los_movimientos_no_se_editan_ni_se_borran(db, make_product) -> None:
    """FR-017: el kardex es de solo inserción."""
    product = make_product("MAN")
    movement = _move(db, product, "5")
    with pytest.raises(DBAPIError, match="solo inserción"):
        db.execute(text("UPDATE stock_movement SET note = 'x' WHERE id = :id"), {"id": movement.id})
    db.rollback()
    with pytest.raises(DBAPIError, match="solo inserción"):
        db.execute(text("DELETE FROM stock_movement WHERE id = :id"), {"id": movement.id})
    db.rollback()


def test_saldo_incorrecto_insertado_a_mano_falla(db, make_product) -> None:
    """R2: el trigger verifica que el saldo sea el stock vigente más el movimiento."""
    product = make_product("MAN")
    with pytest.raises(DBAPIError, match="Saldo incorrecto"):
        db.execute(
            text(
                "INSERT INTO stock_movement (id, product_id, type, quantity_delta, "
                "balance_after, adjustment_reason, occurred_at) VALUES "
                "(gen_random_uuid(), :id, 'adjustment', 5, 50, 'correction', now())"
            ),
            {"id": product.id},
        )
    db.rollback()
    assert _stock(db, product) == Decimal("0")


def test_movimientos_simultaneos_dan_el_saldo_correcto(db, make_product) -> None:
    """FR-021: los movimientos simultáneos sobre un producto dan un stock final correcto."""
    product = make_product("CON")
    barrier = threading.Barrier(8)
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            with get_sessionmaker()() as session:
                barrier.wait()
                for _ in range(5):
                    _move(session, product, "1")
        except BaseException as exc:  # noqa: BLE001 (se reporta abajo)
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert _stock(db, product) == Decimal("40")


def test_la_suma_de_los_movimientos_es_el_stock(db, make_product) -> None:
    """SC-003: la suma de los movimientos de cada producto coincide con su stock."""
    product = make_product("MAN")
    for delta in ("12.30", "-0.30", "5", "-7.15", "0.01"):
        _move(db, product, delta)
    assert _sum_deltas(db, product) == _stock(db, product) == Decimal("9.86")


def test_el_movimiento_guarda_el_costo_antes_y_despues(db, make_product) -> None:
    """Las compras y sus anulaciones guardan el costo antes y después (RN-09, R3)."""
    product = make_product("MAN")
    movement = post_movement(
        db,
        product_id=product.id,
        type="purchase",
        quantity_delta=Decimal("5"),
        created_by=None,
        cost_before_usd=Decimal("2.000000"),
        cost_after_usd=Decimal("2.750000"),
    )
    db.commit()
    db.refresh(movement)
    assert movement.cost_before_usd == Decimal("2.000000")
    assert movement.cost_after_usd == Decimal("2.750000")
