"""Anular compras: reversos, costo deshecho con el costo final, alerta si el resultado no
es válido y vista previa (RN-14/FR-017 a FR-019; research R10)."""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.db.models import Alert, AuditLog, Product, StockMovement
from app.domain.roles import Role

pytestmark = pytest.mark.db

URL = "/api/v1/purchases"


@pytest.fixture
def admin(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.ADMIN, username="dueno"))


def state(db, product):
    db.expire_all()
    row = db.get(Product, product.id)
    return row.stock, row.avg_cost_usd, row.cost_locked


def sum_deltas(db, product) -> Decimal:
    return db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity_delta), 0)).where(
            StockMovement.product_id == product.id
        )
    )


def void(client, headers, purchase, reason="Costo mal escrito"):
    return client.post(f"{URL}/{purchase['id']}/void", json={"reason": reason}, headers=headers)


def test_anular_deshace_stock_y_costo(
    client, admin, make_supplier, make_product, give_stock, make_purchase, db
) -> None:
    product = make_product("MAN", avg_cost="2")
    give_stock(product, "10")
    purchase = make_purchase(admin, make_supplier(), [(product, "30", "3")], confirm=True)

    preview = client.get(f"{URL}/{purchase['id']}/void-preview", headers=admin).json()
    assert preview["items"][0] | {"product_id": None} == {
        "product_id": None,
        "sku": product.sku,
        "stock_before": "40.00",
        "stock_after": "10.00",
        "cost_before_usd": "2.750000",
        "cost_after_usd": "2.000000",
        "keeps_cost": False,
    }
    assert state(db, product)[0] == Decimal("40")  # la vista previa no escribe

    response = void(client, admin, purchase)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "voided"
    assert body["void"]["reason"] == "Costo mal escrito"
    assert body["alerts_created"] == 0
    assert state(db, product) == (Decimal("10.00"), Decimal("2.000000"), True)
    movement = db.scalar(select(StockMovement).where(StockMovement.type == "purchase_void"))
    assert movement.quantity_delta == Decimal("-30")
    assert (movement.cost_before_usd, movement.cost_after_usd) == (
        Decimal("2.750000"),
        Decimal("2.000000"),
    )
    assert sum_deltas(db, product) == Decimal("10")
    actions = set(db.scalars(select(AuditLog.action)))
    assert "purchase.voided" in actions


def test_resultado_invalido_conserva_el_costo_y_alerta(
    client, admin, make_supplier, make_product, give_stock, make_purchase, db
) -> None:
    product = make_product("FRT", avg_cost="2")
    give_stock(product, "10")
    purchase = make_purchase(admin, make_supplier(), [(product, "30", "3")], confirm=True)
    give_stock(product, "-25")  # se vendió buena parte de lo comprado
    preview = client.get(f"{URL}/{purchase['id']}/void-preview", headers=admin).json()
    assert preview["items"][0]["keeps_cost"] is True
    assert preview["items"][0]["stock_after"] == "-15"

    body = void(client, admin, purchase).json()
    assert body["alerts_created"] == 1
    stock, cost, _ = state(db, product)
    assert stock == Decimal("-15")
    assert cost == Decimal("2.750000")
    alert = db.scalar(select(Alert))
    assert alert.type == "purchase_void_cost"
    assert alert.details["sku"] == product.sku
    assert alert.details["stock_after"] == "-15"
    assert alert.details["cost_kept"] == "2.750000"


def test_se_deshace_con_el_costo_final(
    client, admin, make_supplier, make_product, give_stock, make_purchase, db
) -> None:
    product = make_product("FRT", avg_cost="10")
    give_stock(product, "10")
    charges = [{"description": "Envío", "charge_type": "fixed", "amount": "50", "currency": "USD"}]
    purchase = make_purchase(
        admin, make_supplier(), [(product, "10", "10")], charges=charges, confirm=True
    )
    assert state(db, product)[1] == Decimal("12.500000")
    void(client, admin, purchase)
    assert state(db, product)[1] == Decimal("10.000000")


@pytest.mark.parametrize("reason", ["", "abcd"])
def test_motivo_obligatorio(
    client, admin, make_supplier, make_product, make_purchase, reason
) -> None:
    purchase = make_purchase(
        admin, make_supplier(), [(make_product("FRT"), "1", "1")], confirm=True
    )
    assert void(client, admin, purchase, reason).status_code == 422


def test_una_sola_vez_y_no_borradores(
    client, admin, make_supplier, make_product, make_purchase
) -> None:
    supplier, product = make_supplier(), make_product("FRT")
    draft = make_purchase(admin, supplier, [(product, "1", "1")])
    assert void(client, admin, draft).json()["detail"]["code"] == "invalid_state"
    assert client.get(f"{URL}/{draft['id']}/void-preview", headers=admin).status_code == 409
    confirmed = make_purchase(admin, supplier, [(product, "1", "1")], confirm=True)
    assert void(client, admin, confirmed).status_code == 200
    again = void(client, admin, confirmed)
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "invalid_state"


def test_solo_el_admin_anula(
    client, make_user, auth_headers, make_supplier, make_product, make_purchase
) -> None:
    warehouse = auth_headers(make_user(Role.WAREHOUSE, username="almacen"))
    purchase = make_purchase(
        warehouse, make_supplier(), [(make_product("FRT"), "1", "1")], confirm=True
    )
    assert void(client, warehouse, purchase).status_code == 403
    assert client.get(f"{URL}/{purchase['id']}/void-preview", headers=warehouse).status_code == 403
