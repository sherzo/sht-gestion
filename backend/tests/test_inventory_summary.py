"""Stock bajo y resumen del inicio (RF-11/FR-023, FR-019b; US3 escenario 4; R11)."""

import pytest

from app.domain.roles import Role

pytestmark = pytest.mark.db

LOW_STOCK = "/api/v1/inventory/low-stock"
SUMMARY = "/api/v1/inventory/summary"


@pytest.fixture
def actors(make_user, auth_headers):
    return {
        role: auth_headers(make_user(role, username=f"resumen_{role.value}"))
        for role in (Role.ADMIN, Role.SELLER, Role.WAREHOUSE)
    }


def _skus(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["sku"] for item in response.json()]


def test_stock_bajo_al_llegar_al_minimo(client, actors, make_product, give_stock) -> None:
    """US3 escenario 4: con mínimo 5, aparece con stock 5 y deja de aparecer con 6."""
    product = make_product("FER", min_stock="5")
    give_stock(product, "5")
    assert product.sku in _skus(client.get(LOW_STOCK, headers=actors[Role.WAREHOUSE]))
    give_stock(product, "1")
    assert product.sku not in _skus(client.get(LOW_STOCK, headers=actors[Role.WAREHOUSE]))


def test_minimo_cero_solo_al_agotarse(client, actors, make_product, give_stock) -> None:
    """Caso borde "stock mínimo 0": se marca solo cuando se agota."""
    product = make_product("CON")
    assert product.sku in _skus(client.get(LOW_STOCK, headers=actors[Role.ADMIN]))
    give_stock(product, "1")
    assert product.sku not in _skus(client.get(LOW_STOCK, headers=actors[Role.ADMIN]))


def test_inactivo_nunca_aparece(client, actors, make_product) -> None:
    product = make_product("CON", is_active=False, min_stock="3")
    assert product.sku not in _skus(client.get(LOW_STOCK, headers=actors[Role.ADMIN]))


def test_almacen_sin_precios_en_stock_bajo(client, actors, make_product) -> None:
    """Principio IV: la lista usa el esquema del rol."""
    make_product("CON", sale_price="3.00", avg_cost="1.000000")
    [item] = client.get(LOW_STOCK, headers=actors[Role.WAREHOUSE]).json()
    assert "sale_price_usd" not in item and "avg_cost_usd" not in item


def test_resumen_del_admin_y_del_almacen(
    client, actors, make_product, make_user, auth_headers
) -> None:
    """R11: contadores del inicio según el rol."""
    make_product("CON")  # stock 0 y mínimo 0: stock bajo
    product = make_product("FER", min_stock="0")
    warehouse = make_user(Role.WAREHOUSE, username="almacen_resumen")
    warehouse_headers = auth_headers(warehouse)
    client.post(
        "/api/v1/inventory/adjustments",
        json={"product_id": str(product.id), "quantity_delta": "2", "reason": "correction"},
        headers=warehouse_headers,
    )
    client.post(
        "/api/v1/inventory/adjustments",
        json={"product_id": str(product.id), "quantity_delta": "-1", "reason": "loss"},
        headers=warehouse_headers,
    )
    admin = client.get(SUMMARY, headers=actors[Role.ADMIN]).json()
    assert admin == {"low_stock": 1, "pending_adjustments": 1, "counts_ready_for_review": 0}
    mine = client.get(SUMMARY, headers=warehouse_headers).json()
    assert mine == {"low_stock": 1, "my_pending_requests": 1, "open_counts": 0}


def test_vendedor_sin_acceso(client, actors) -> None:
    assert client.get(LOW_STOCK, headers=actors[Role.SELLER]).status_code == 403
    assert client.get(SUMMARY, headers=actors[Role.SELLER]).status_code == 403
