"""Inmutabilidad de compras en la base: ni por SQL directo se modifica una compra
confirmada o anulada, sus líneas, sus gastos ni su anulación; corregir una tasa no cambia
las compras confirmadas (RN-14/FR-016, SC-002; RN-05/FR-028, SC-009; research R2)."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core import clock
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db


@pytest.fixture
def headers(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.ADMIN, username="dueno"))


@pytest.fixture
def confirmed(headers, make_supplier, make_product, make_purchase) -> dict:
    charges = [{"description": "Envío", "charge_type": "fixed", "amount": "5", "currency": "USD"}]
    return make_purchase(
        headers, make_supplier(), [(make_product("FRT"), "2", "10")], charges=charges, confirm=True
    )


STATEMENTS = [
    "UPDATE purchase SET notes = 'x' WHERE id = :id",
    "UPDATE purchase SET status = 'draft' WHERE id = :id",
    "DELETE FROM purchase WHERE id = :id",
    "UPDATE purchase_item SET quantity = 1 WHERE purchase_id = :id",
    "DELETE FROM purchase_item WHERE purchase_id = :id",
    "UPDATE purchase_charge SET amount = 1 WHERE purchase_id = :id",
    "DELETE FROM purchase_charge WHERE purchase_id = :id",
]


@pytest.mark.parametrize("statement", STATEMENTS)
def test_compra_confirmada_no_cambia_por_sql(db, confirmed, statement) -> None:
    with pytest.raises(DBAPIError):
        db.execute(text(statement), {"id": confirmed["id"]})
    db.rollback()


def test_no_se_agregan_lineas_a_una_confirmada(db, confirmed, make_product) -> None:
    product = make_product("FRT")
    with pytest.raises(DBAPIError):
        db.execute(
            text(
                "INSERT INTO purchase_item (id, purchase_id, product_id, line_number, quantity, "
                "unit_cost_usd, line_total_usd, allocated_charges_usd, landed_unit_cost_usd) "
                "VALUES (:item, :id, :product, 9, 1, 1, 1, 0, 1)"
            ),
            {"item": uuid.uuid7(), "id": confirmed["id"], "product": product.id},
        )
    db.rollback()


def test_en_borrador_si_se_modifica(
    db, headers, make_supplier, make_product, make_purchase
) -> None:
    draft = make_purchase(headers, make_supplier(), [(make_product("FRT"), "2", "10")])
    db.execute(
        text("UPDATE purchase_item SET quantity = 3 WHERE purchase_id = :id"), {"id": draft["id"]}
    )
    db.execute(text("UPDATE purchase SET notes = 'x' WHERE id = :id"), {"id": draft["id"]})
    db.commit()


def test_confirmar_sin_numero_falla(
    db, headers, make_supplier, make_product, make_purchase
) -> None:
    draft = make_purchase(headers, make_supplier(), [(make_product("FRT"), "2", "10")])
    with pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE purchase SET status = 'confirmed' WHERE id = :id"), {"id": draft["id"]}
        )
    db.rollback()


def test_anulada_y_su_anulacion_no_cambian(db, client, headers, confirmed) -> None:
    response = client.post(
        f"/api/v1/purchases/{confirmed['id']}/void",
        json={"reason": "Costo mal escrito"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    for statement in (
        "UPDATE purchase SET status = 'confirmed' WHERE id = :id",
        "UPDATE purchase_void SET reason = 'otro motivo' WHERE purchase_id = :id",
        "DELETE FROM purchase_void WHERE purchase_id = :id",
    ):
        with pytest.raises(DBAPIError):
            db.execute(text(statement), {"id": confirmed["id"]})
        db.rollback()


def test_corregir_la_tasa_no_cambia_compras_confirmadas(
    client, headers, make_supplier, make_product, make_rate, make_purchase
) -> None:
    """SC-009: ni un céntimo cambia al corregir la tasa de la fecha de la compra."""
    today = business_date(clock.utcnow())
    make_rate(today - timedelta(days=1), "36.00")
    make_rate(today, "36.50")
    purchase = make_purchase(
        headers,
        make_supplier(),
        [(make_product("FRT"), "3", "100.00")],
        currency="VES",
        confirm=True,
    )
    response = client.put(
        f"/api/v1/exchange-rates/{today.isoformat()}", json={"rate": "40"}, headers=headers
    )
    assert response.status_code == 200, response.text
    after = client.get(f"/api/v1/purchases/{purchase['id']}", headers=headers).json()
    for key in ("items", "charges", "exchange_rate", "merchandise_total_usd", "total_usd"):
        assert after[key] == purchase[key], key
    assert after["exchange_rate"] == "36.50000000"
