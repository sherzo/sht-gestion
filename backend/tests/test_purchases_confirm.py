"""Confirmar compras: kardex, costo promedio con el costo final, número sin huecos,
revalidación y datos viejos (RF-16, RN-09, RN-20/FR-008 a FR-015; research R3)."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core import clock
from app.db.models import AuditLog, Product, StockMovement
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db

URL = "/api/v1/purchases"


@pytest.fixture
def admin(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.ADMIN, username="dueno"))


@pytest.fixture
def warehouse(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.WAREHOUSE, username="almacen"))


@pytest.fixture
def supplier(make_supplier):
    return make_supplier("Hidráulica Aragua")


def product_state(db, product) -> tuple[Decimal, Decimal | None, bool]:
    db.expire_all()
    row = db.get(Product, product.id)
    return row.stock, row.avg_cost_usd, row.cost_locked


def confirm(client, headers, purchase) -> object:
    return client.post(
        f"{URL}/{purchase['id']}/confirm",
        json={"updated_at": purchase["updated_at"]},
        headers=headers,
    )


def test_confirmar_mueve_el_kardex_y_promedia(
    client, admin, supplier, make_product, give_stock, make_purchase, db
) -> None:
    product = make_product("MAN", avg_cost="2")
    give_stock(product, "10")
    purchase = make_purchase(admin, supplier, [(product, "30", "3.00")])
    response = confirm(client, admin, purchase)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["number"] == "C-000001"
    assert body["cost_changes"] == [
        {
            "product_id": str(product.id),
            "sku": product.sku,
            "cost_before_usd": "2.000000",
            "cost_after_usd": "2.750000",
        }
    ]
    assert product_state(db, product) == (Decimal("40.00"), Decimal("2.750000"), True)
    movement = db.scalar(select(StockMovement).where(StockMovement.type == "purchase"))
    assert movement.reference_type == "purchase_item"
    assert movement.reference_id == body_item_id(body)
    assert (movement.cost_before_usd, movement.cost_after_usd) == (
        Decimal("2.000000"),
        Decimal("2.750000"),
    )
    actions = set(db.scalars(select(AuditLog.action)))
    assert {"purchase.confirmed", "product.cost_updated"} <= actions


def body_item_id(body):
    import uuid

    return uuid.UUID(body["items"][0]["id"])


@pytest.mark.parametrize(
    ("stock", "cost", "quantity", "unit_cost", "expected"),
    [
        ("-2", "10", "5", "12", "12.000000"),  # stock negativo: costo de la compra (RN-09)
        ("0", "4", "10", "5", "5.000000"),  # stock cero con costo inicial
        ("5", None, "3", "7", "7.000000"),  # stock sin costo (FR-015)
    ],
)
def test_casos_del_costo(
    client,
    admin,
    supplier,
    make_product,
    give_stock,
    make_purchase,
    db,
    stock,
    cost,
    quantity,
    unit_cost,
    expected,
) -> None:
    product = make_product("FRT", avg_cost=cost)
    if stock != "0":
        give_stock(product, stock)
    make_purchase(admin, supplier, [(product, quantity, unit_cost)], confirm=True)
    assert product_state(db, product)[1] == Decimal(expected)


def test_la_primera_compra_bloquea_el_costo_inicial(
    client, admin, supplier, make_product, make_purchase
) -> None:
    product = make_product("FRT", avg_cost="4")
    make_purchase(admin, supplier, [(product, "1", "5")], confirm=True)
    response = client.put(
        f"/api/v1/products/{product.id}/initial-cost", json={"avg_cost_usd": "6"}, headers=admin
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "cost_locked"


def test_numeros_consecutivos_sin_huecos(
    client, warehouse, supplier, make_product, make_purchase
) -> None:
    product = make_product("FRT")
    first = make_purchase(warehouse, supplier, [(product, "1", "1")], confirm=True)
    discarded = make_purchase(warehouse, supplier, [(product, "1", "1")])
    client.delete(f"{URL}/{discarded['id']}", headers=warehouse)
    second = make_purchase(warehouse, supplier, [(product, "1", "1")], confirm=True)
    assert (first["number"], second["number"]) == ("C-000001", "C-000002")


def test_confirmar_dos_veces(client, warehouse, supplier, make_product, make_purchase, db) -> None:
    product = make_product("FRT")
    purchase = make_purchase(warehouse, supplier, [(product, "4", "1")])
    assert confirm(client, warehouse, purchase).status_code == 200
    again = confirm(client, warehouse, purchase)
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "invalid_state"
    assert product_state(db, product)[0] == Decimal("4")


def test_confirmar_con_datos_viejos(
    client, warehouse, supplier, make_product, make_purchase, db
) -> None:
    """Edge case: otro usuario cambió el borrador; no se confirma (F1)."""
    product = make_product("FRT")
    purchase = make_purchase(warehouse, supplier, [(product, "1", "1")])
    edited = client.put(
        f"{URL}/{purchase['id']}",
        json={
            "supplier_id": str(supplier.id),
            "purchase_date": business_date(clock.utcnow()).isoformat(),
            "currency": "USD",
            "items": [{"product_id": str(product.id), "quantity": "9", "unit_cost": "1"}],
        },
        headers=warehouse,
    ).json()
    stale = confirm(client, warehouse, purchase)
    assert stale.status_code == 409
    detail = stale.json()["detail"]
    assert detail["code"] == "stale_data"
    assert detail["purchase"]["items"][0]["quantity"] == "9"
    assert detail["purchase"]["number"] is None
    assert product_state(db, product)[0] == Decimal("0")
    assert confirm(client, warehouse, edited).status_code == 200


def test_producto_o_proveedor_desactivado_despues(
    client, warehouse, supplier, make_product, make_purchase, db
) -> None:
    product = make_product("FRT")
    purchase = make_purchase(warehouse, supplier, [(product, "1", "1")])
    product.is_active = False
    db.commit()
    response = confirm(client, warehouse, purchase)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "inactive_products"
    assert response.json()["detail"]["skus"] == [product.sku]
    product.is_active = True
    supplier.is_active = False
    db.commit()
    response = confirm(client, warehouse, purchase)
    assert response.json()["detail"]["code"] == "inactive_supplier"


def test_el_almacen_no_recibe_cost_changes(
    client, warehouse, supplier, make_product, make_purchase
) -> None:
    purchase = make_purchase(warehouse, supplier, [(make_product("FRT"), "1", "1")])
    body = confirm(client, warehouse, purchase).json()
    assert "cost_changes" not in body


def test_el_costo_usa_el_costo_final_de_la_importacion(
    client, admin, supplier, make_product, give_stock, make_purchase, db
) -> None:
    """Stock 10 a 12,00 + 10 u. con costo final 12,50 → 12,25 (RN-20, RN-09)."""
    product = make_product("CON", avg_cost="12")
    give_stock(product, "10")
    other = make_product("CON")
    charges = [
        {"description": "Envío", "charge_type": "fixed", "amount": "45.00", "currency": "USD"}
    ]
    purchase = make_purchase(
        admin, supplier, [(product, "10", "10"), (other, "10", "8")], charges=charges, confirm=True
    )
    assert purchase["items"][0]["landed_unit_cost_usd"] == "12.500000"
    assert product_state(db, product)[1] == Decimal("12.250000")
    movement = db.scalar(
        select(StockMovement).where(
            StockMovement.type == "purchase", StockMovement.product_id == product.id
        )
    )
    assert movement.cost_after_usd == Decimal("12.250000")


def test_bs_confirmada_conserva_su_tasa(
    client, warehouse, supplier, make_product, make_rate, make_purchase, db
) -> None:
    rate = make_rate(business_date(clock.utcnow()), "40")
    product = make_product("FRT")
    purchase = make_purchase(
        warehouse, supplier, [(product, "10", "100.00")], currency="VES", confirm=True
    )
    assert purchase["items"][0]["unit_cost_usd"] == "2.500000"
    assert product_state(db, product)[1] == Decimal("2.500000")
    rate.rate = Decimal("50")
    db.commit()
    again = client.get(f"{URL}/{purchase['id']}", headers=warehouse).json()
    assert again["exchange_rate"] == "40.00000000"
    assert again["items"][0]["unit_cost_usd"] == "2.500000"
    assert again["total_usd"] == purchase["total_usd"]


def test_la_tasa_cambio_desde_el_ultimo_guardado(
    client, warehouse, supplier, make_product, make_rate, make_purchase, db
) -> None:
    """Regresión del code review: no se confirma con costos que nadie revisó."""
    rate = make_rate(business_date(clock.utcnow()), "40")
    product = make_product("FRT")
    purchase = make_purchase(warehouse, supplier, [(product, "10", "100.00")], currency="VES")
    rate.rate = Decimal("50")
    db.commit()
    response = confirm(client, warehouse, purchase)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "rate_changed"
    assert product_state(db, product)[0] == Decimal("0")
    saved = client.put(
        f"{URL}/{purchase['id']}",
        json={
            "supplier_id": str(supplier.id),
            "purchase_date": purchase["purchase_date"],
            "currency": "VES",
            "items": [{"product_id": str(product.id), "quantity": "10", "unit_cost": "100.00"}],
        },
        headers=warehouse,
    ).json()
    assert saved["items"][0]["unit_cost_usd"] == "2.000000"
    assert confirm(client, warehouse, saved).status_code == 200
