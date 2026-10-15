"""Anulación de una venta: solo el Admin, con motivo, una vez; reversos de kardex y espejo
de cada pago y vuelto en la caja de la venta (RF-27/FR-041 a FR-044, SC-008; research R10)."""

from decimal import Decimal

import pytest
from sqlalchemy import select, text

from app.core import clock
from app.db.models import Payment, Product, StockMovement
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

REASON = "Cliente devolvió la mercancía"


@pytest.fixture
def scenario(
    make_user,
    auth_headers,
    make_device,
    make_rate,
    open_cash_session,
    make_product,
    give_stock,
    make_sale,
):
    make_rate(business_date(clock.utcnow()), "36.50")
    seller_headers = auth_headers(make_user(Role.SELLER))
    admin_headers = auth_headers(make_user(Role.ADMIN))
    _, token = make_device()
    session = open_cash_session(seller_headers, token)
    fitting = make_product("CON", sale_price="7.70")
    hose = make_product("MAN", sale_price="4.00")
    give_stock(fitting, "10")
    give_stock(hose, "5")
    sale = make_sale(
        seller_headers,
        token,
        session["id"],
        [(fitting, "1"), (hose, "0.30", "cm")],
        payments=[("cash_usd", "10.00", None), ("mobile_payment", "36.50", "REF1")],
        change=[("cash_ves", "58.40", None), ("cash_usd", "0.50", None)],
    )
    return {
        "sale": sale,
        "admin": admin_headers,
        "seller": seller_headers,
        "fitting": fitting,
        "hose": hose,
    }


def void(client, scenario, headers=None, reason=REASON):
    return client.post(
        f"/api/v1/sales/{scenario['sale']['id']}/void",
        json={"reason": reason},
        headers=headers or scenario["admin"],
    )


def test_anular_devuelve_el_stock_y_espeja_los_pagos(client, scenario, db) -> None:
    response = void(client, scenario)
    assert response.status_code == 200, response.text
    sale = response.json()
    assert sale["status"] == "voided"
    assert sale["void"]["reason"] == REASON

    db.expire_all()
    assert db.get(Product, scenario["fitting"].id).stock == Decimal("10.00")
    assert db.get(Product, scenario["hose"].id).stock == Decimal("5.00")
    reversals = db.scalars(select(StockMovement).where(StockMovement.type == "sale_void")).all()
    assert sorted(movement.quantity_delta for movement in reversals) == [
        Decimal("0.30"),
        Decimal("1.00"),
    ]
    assert all(movement.reference_type == "sale_item" for movement in reversals)

    payments = db.scalars(select(Payment).where(Payment.sale_id == scenario["sale"]["id"])).all()
    kinds = sorted(
        (payment.kind, payment.payment_method_code, payment.amount) for payment in payments
    )
    assert kinds == sorted(
        [
            ("sale_payment", "cash_usd", Decimal("10.00")),
            ("sale_payment", "mobile_payment", Decimal("36.50")),
            ("change", "cash_ves", Decimal("58.40")),
            ("change", "cash_usd", Decimal("0.50")),
            ("void_refund", "cash_usd", Decimal("10.00")),
            ("void_refund", "mobile_payment", Decimal("36.50")),
            ("void_change", "cash_ves", Decimal("58.40")),
            ("void_change", "cash_usd", Decimal("0.50")),
        ]
    )
    # Lo que entra y sale con la anulación es exactamente lo contrario de la venta.
    signs = {"sale_payment": 1, "change": -1, "void_refund": -1, "void_change": 1}
    assert sum(signs[p.kind] * p.amount_usd for p in payments) == 0
    refund = next(
        p for p in payments if p.kind == "void_refund" and p.payment_method_code == "mobile_payment"
    )
    assert refund.reference == "REF1"
    assert refund.sale_void_id is not None
    assert all(str(p.cash_session_id) == scenario["sale"]["cash_session_id"] for p in payments)

    [entry] = audit_entries(db, "sale.voided")
    assert entry.reason == REASON


@pytest.mark.parametrize("reason", ["mal", "x" * 501, "    "])
def test_motivo_invalido(client, scenario, reason) -> None:
    assert void(client, scenario, reason=reason).status_code == 422


def test_no_se_anula_dos_veces(client, scenario) -> None:
    assert void(client, scenario).status_code == 200
    again = void(client, scenario)
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "invalid_state"


def test_solo_el_admin_anula(client, scenario, make_user, auth_headers) -> None:
    assert void(client, scenario, headers=scenario["seller"]).status_code == 403
    warehouse = auth_headers(make_user(Role.WAREHOUSE))
    assert void(client, scenario, headers=warehouse).status_code == 403


def test_venta_inexistente(client, scenario) -> None:
    response = client.post(
        "/api/v1/sales/01a1411c-0000-7000-8000-000000000000/void",
        json={"reason": REASON},
        headers=scenario["admin"],
    )
    assert response.status_code == 404


def test_venta_con_stock_negativo_vuelve_a_lo_previo(
    client,
    make_user,
    auth_headers,
    make_device,
    make_rate,
    open_cash_session,
    make_product,
    make_sale,
    db,
) -> None:
    make_rate(business_date(clock.utcnow()), "36.50")
    admin = auth_headers(make_user(Role.ADMIN))
    _, token = make_device()
    session = open_cash_session(admin, token)
    product = make_product("CON", sale_price="1.00")
    sale = make_sale(admin, token, session["id"], [(product, "3")])
    db.expire_all()
    assert db.get(Product, product.id).stock == Decimal("-3.00")
    assert (
        client.post(
            f"/api/v1/sales/{sale['id']}/void", json={"reason": REASON}, headers=admin
        ).status_code
        == 200
    )
    db.expire_all()
    assert db.get(Product, product.id).stock == Decimal("0.00")


def test_la_anulacion_es_inmutable(client, scenario, db) -> None:
    void(client, scenario)
    for sql in (
        "UPDATE sale_void SET reason = 'otro motivo' WHERE sale_id = :id",
        "DELETE FROM sale_void WHERE sale_id = :id",
        "DELETE FROM payment WHERE sale_id = :id AND kind = 'void_refund'",
    ):
        with pytest.raises(Exception, match="solo inserción"):
            db.execute(text(sql), {"id": scenario["sale"]["id"]})
        db.rollback()
