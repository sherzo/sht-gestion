"""Ventas que se registran igual con alerta para el Admin: stock negativo, precio, total o
tasa distintos (RN-10/FR-030 a FR-032, SC-009; research R6)."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core import clock
from app.db.models import Alert, AppUser, Product
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db


@pytest.fixture
def counter(make_user, auth_headers, make_device, make_rate, open_cash_session):
    make_rate(business_date(clock.utcnow()), "36.50")
    headers = auth_headers(make_user(Role.SELLER))
    _, token = make_device()
    session = open_cash_session(headers, token)
    return headers, token, session["id"]


def sell(make_sale, counter, items, **kwargs):
    headers, token, session_id = counter
    return make_sale(headers, token, session_id, items, **kwargs)


def alerts(db, alert_type: str) -> list[Alert]:
    db.expire_all()
    return list(db.scalars(select(Alert).where(Alert.type == alert_type)))


def test_stock_negativo_con_alerta(make_sale, counter, make_product, give_stock, db) -> None:
    product = make_product("CON", sale_price="2.00")
    give_stock(product, "2")
    sale = sell(make_sale, counter, [(product, "3")])
    assert sale["warnings"] == ["negative_stock"]
    assert "negative_stock" in sale["alerts_created"]
    db.expire_all()
    assert db.get(Product, product.id).stock == Decimal("-1.00")
    [alert] = alerts(db, "negative_stock")
    assert alert.entity_type == "sale"
    assert alert.details["sale_number"] == sale["number"]
    assert alert.details["products"] == [
        {"sku": product.sku, "name": product.name, "quantity": "3", "stock_after": "-1.00"}
    ]


def test_una_alerta_por_tipo_con_todos_los_productos(
    make_sale, counter, make_product, give_stock, db
) -> None:
    first = make_product("CON", sale_price="2.00")
    second = make_product("FRT", sale_price="1.00")
    sell(make_sale, counter, [(first, "1"), (second, "2")])
    [alert] = alerts(db, "negative_stock")
    assert {item["sku"] for item in alert.details["products"]} == {first.sku, second.sku}


def test_precio_distinto_al_vigente(make_sale, counter, make_product, give_stock, db) -> None:
    product = make_product("CON", sale_price="5.00")
    give_stock(product, "10")
    sale = sell(make_sale, counter, [(product, "1")], unit_prices={product.id: Decimal("4.50")})
    assert sale["items"][0]["unit_price_usd"] == "4.50"
    assert sale["items"][0]["server_price_usd"] == "5.00"
    assert sale["total_usd"] == "4.50"
    [alert] = alerts(db, "price_mismatch")
    assert alert.details["products"][0]["server_price_usd"] == "5.00"


def test_total_distinto_se_registra_con_el_del_servidor(
    make_sale, counter, make_product, give_stock, db
) -> None:
    product = make_product("CON", sale_price="5.00")
    give_stock(product, "10")
    # El equipo calculó 4,00 y cobró eso: el servidor guarda 5,00 y alerta con el saldo.
    sale = sell(
        make_sale,
        counter,
        [(product, "1")],
        payments=[("cash_usd", "4.00", None)],
        device_total_usd="4.00",
    )
    assert sale["total_usd"] == "5.00"
    assert sale["device_total_usd"] == "4.00"
    [alert] = alerts(db, "total_mismatch")
    assert alert.details == {
        "sale_number": sale["number"],
        "device_total_usd": "4.00",
        "server_total_usd": "5.00",
        "balance_usd": "1.00",
    }


def test_tasa_distinta_de_la_cargada(make_sale, counter, make_product, give_stock, db) -> None:
    """La tasa se corrigió después de vender, o el equipo envió otra: se alerta."""
    product = make_product("CON", sale_price="5.00")
    give_stock(product, "10")
    today = business_date(clock.utcnow())
    sale = sell(make_sale, counter, [(product, "1")], rate=("40.00000000", today))
    assert sale["exchange_rate"] == "40.00000000"
    [alert] = alerts(db, "rate_mismatch")
    assert alert.details["sale_rate"] == "40.00000000"
    assert alert.details["loaded_rate"] == "36.50000000"


def test_fecha_sin_tasa_cargada(make_sale, counter, make_product, give_stock, db) -> None:
    product = make_product("CON", sale_price="5.00")
    give_stock(product, "10")
    yesterday = business_date(clock.utcnow()).replace(day=1)
    sell(make_sale, counter, [(product, "1")], rate=("36.50000000", yesterday))
    [alert] = alerts(db, "rate_mismatch")
    assert alert.details["loaded_rate"] is None


def test_sin_diferencias_no_hay_alertas(make_sale, counter, make_product, give_stock, db) -> None:
    product = make_product("CON", sale_price="5.00")
    give_stock(product, "10")
    sale = sell(make_sale, counter, [(product, "1")])
    assert sale["alerts_created"] == []
    db.expire_all()
    assert db.scalars(select(Alert)).all() == []


def test_deteccion_de_vendedor_inactivo(db, make_user) -> None:
    """R17: en la 1.3 la venta la envía su vendedor con sesión vigente, así que no ocurre;
    la detección queda lista para la 1.5 (`not seller.is_active`)."""
    seller = make_user(Role.SELLER, is_active=False)
    assert db.get(AppUser, seller.id).is_active is False


def test_alertas_de_venta_en_pendientes(
    client, make_sale, counter, make_product, auth_headers, make_user
) -> None:
    product = make_product("CON", sale_price="2.00")
    sale = sell(make_sale, counter, [(product, "1")])
    admin_headers = auth_headers(make_user(Role.ADMIN))
    listed = client.get("/api/v1/alerts", headers=admin_headers).json()["items"]
    [alert] = [item for item in listed if item["type"] == "negative_stock"]
    assert alert["sale"] == {"id": sale["id"], "number": sale["number"]}
