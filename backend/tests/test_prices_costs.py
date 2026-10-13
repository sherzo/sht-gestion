"""Precio de venta con historial, costo inicial y publicación, solo del Admin (RF-01, RF-07,
RN-01, RN-09, RN-17, RN-18; FR-009, FR-011 a FR-015; US4; research R6)."""

import pytest

from app.domain.roles import Role
from tests.helpers import audit_entries

pytestmark = pytest.mark.db


@pytest.fixture
def actors(make_user, auth_headers):
    return {
        role: auth_headers(make_user(role, username=f"precio_{role.value}"))
        for role in (Role.ADMIN, Role.SELLER, Role.WAREHOUSE)
    }


def _price(client, headers, product, value):
    return client.put(
        f"/api/v1/products/{product.id}/price", json={"sale_price_usd": value}, headers=headers
    )


def _cost(client, headers, product, value):
    return client.put(
        f"/api/v1/products/{product.id}/initial-cost", json={"avg_cost_usd": value}, headers=headers
    )


def _publish(client, headers, product, value: bool):
    return client.put(
        f"/api/v1/products/{product.id}/publication", json={"is_published": value}, headers=headers
    )


def test_precio_con_historial_y_auditoria(client, actors, make_product, db) -> None:
    """US4 escenarios 1 y 2: cada precio queda en el historial y en la auditoría."""
    product = make_product("MAN")
    admin = actors[Role.ADMIN]
    first = _price(client, admin, product, "12.50")
    assert first.status_code == 200, first.text
    assert first.json()["sale_price_usd"] == "12.50"
    assert _price(client, admin, product, "13").json()["sale_price_usd"] == "13.00"

    history = client.get(f"/api/v1/products/{product.id}/prices", headers=admin).json()
    assert [item["price_usd"] for item in history] == ["13.00", "12.50"]
    assert history[0]["set_by"]["full_name"]

    entries = audit_entries(db, "product.price_set")
    assert [entry.before for entry in entries] == [
        {"sale_price_usd": None},
        {"sale_price_usd": "12.50"},
    ]
    assert [entry.after for entry in entries] == [
        {"sale_price_usd": "12.50"},
        {"sale_price_usd": "13.00"},
    ]


@pytest.mark.parametrize("value", ["12.505", "0", "-1", "abc"])
def test_precio_invalido(client, actors, make_product, value) -> None:
    """US4 escenario 3, FR-011: mayor que cero y con 2 decimales exactos, sin redondear."""
    response = _price(client, actors[Role.ADMIN], make_product("MAN"), value)
    assert response.status_code == 422
    assert "sale_price_usd" in response.json()["detail"]["fields"]


def test_costo_inicial(client, actors, make_product, db) -> None:
    """US4 escenarios 6 y 8, FR-013: el Admin define el costo; cero es distinto de nulo."""
    product = make_product("CON")
    admin = actors[Role.ADMIN]
    detail = client.get(f"/api/v1/products/{product.id}", headers=admin).json()
    assert detail["avg_cost_usd"] is None

    assert _cost(client, admin, product, "7.250000").json()["avg_cost_usd"] == "7.250000"
    assert _cost(client, admin, product, "0").json()["avg_cost_usd"] == "0.000000"
    entries = audit_entries(db, "product.initial_cost_set")
    assert entries[0].before == {"avg_cost_usd": None}
    assert entries[0].after == {"avg_cost_usd": "7.250000"}
    assert entries[1].after == {"avg_cost_usd": "0.000000"}


@pytest.mark.parametrize("value", ["1.1234567", "-0.01"])
def test_costo_invalido(client, actors, make_product, value) -> None:
    response = _cost(client, actors[Role.ADMIN], make_product("CON"), value)
    assert response.status_code == 422
    assert "avg_cost_usd" in response.json()["detail"]["fields"]


def test_costo_bloqueado_tras_compras(client, actors, make_product, db) -> None:
    """US4 escenario 7, RN-09: con compras confirmadas el costo solo lo cambian las
    compras (la etapa 1.2 pone `cost_locked`)."""
    product = make_product("CON", avg_cost="5.000000")
    product.cost_locked = True
    db.commit()
    response = _cost(client, actors[Role.ADMIN], product, "6")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "cost_locked"


def test_publicacion(client, actors, make_product, db) -> None:
    """US4 escenario 4, FR-009: solo se publica un producto activo y con precio."""
    admin = actors[Role.ADMIN]
    product = make_product("MAN")
    without_price = _publish(client, admin, product, True)
    assert without_price.status_code == 409
    assert without_price.json()["detail"]["code"] == "not_publishable"

    _price(client, admin, product, "10.00")
    published = _publish(client, admin, product, True)
    assert published.status_code == 200
    assert published.json()["is_published"] is True
    assert _publish(client, admin, product, False).json()["is_published"] is False
    assert len(audit_entries(db, "product.published")) == 1
    assert len(audit_entries(db, "product.unpublished")) == 1

    inactive = make_product("MAN", sale_price="3.00", is_active=False)
    assert _publish(client, admin, inactive, True).status_code == 409


@pytest.mark.parametrize("role", [Role.SELLER, Role.WAREHOUSE])
def test_solo_el_admin(client, actors, make_product, role) -> None:
    """FR-001, FR-014, principio IV: Vendedor y Almacén no fijan precio, costo ni
    publicación, ni ven el historial de precios."""
    product = make_product("MAN", sale_price="10.00")
    headers = actors[role]
    assert _price(client, headers, product, "11.00").status_code == 403
    assert _cost(client, headers, product, "1").status_code == 403
    assert _publish(client, headers, product, True).status_code == 403
    prices = client.get(f"/api/v1/products/{product.id}/prices", headers=headers)
    assert prices.status_code == 403


def test_vendedor_ve_el_precio_pero_no_el_costo(client, actors, make_product) -> None:
    """US4 escenario 5, US3 escenario 5."""
    product = make_product("MAN", sale_price="12.50", avg_cost="7.250000")
    seller = client.get(f"/api/v1/products/{product.id}", headers=actors[Role.SELLER]).json()
    assert seller["sale_price_usd"] == "12.50"
    assert "avg_cost_usd" not in seller and "cost_locked" not in seller
    warehouse = client.get(f"/api/v1/products/{product.id}", headers=actors[Role.WAREHOUSE]).json()
    assert "sale_price_usd" not in warehouse
