"""Consulta del kardex por producto (RF-08, RF-09/FR-017, FR-022; US2 escenarios 10 y 11)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db


@pytest.fixture
def actors(make_user, auth_headers):
    return {
        role: auth_headers(make_user(role, username=f"kardex_{role.value}"))
        for role in (Role.ADMIN, Role.SELLER, Role.WAREHOUSE)
    }


def _movements(client, headers, product, **params):
    return client.get(f"/api/v1/products/{product.id}/movements", params=params, headers=headers)


def test_mas_recientes_primero_con_saldo(client, actors, make_product, give_stock) -> None:
    """FR-022: los movimientos más recientes primero, con el stock resultante."""
    product = make_product("MAN")
    for delta in ("10", "-2.50", "0.75"):
        give_stock(product, delta)
    data = _movements(client, actors[Role.ADMIN], product).json()
    assert [item["balance_after"] for item in data["items"]] == ["8.25", "7.50", "10.00"]
    assert [item["quantity_delta"] for item in data["items"]] == ["0.75", "-2.50", "10.00"]
    assert data["total"] == 3


def test_filtros_por_fecha_de_caracas_y_tipo(
    client, actors, make_product, give_stock, advance_clock
) -> None:
    """FR-022: rango de fechas de negocio (America/Caracas) y tipo de movimiento."""
    product = make_product("CON")
    # Un movimiento de hace tres días y otro de hoy (sin vencer la jornada de la sesión).
    advance_clock(timedelta(days=-3))
    give_stock(product, "5")
    advance_clock(timedelta(days=3))
    give_stock(product, "1")
    today = business_date(datetime.now(UTC))
    recent = _movements(client, actors[Role.WAREHOUSE], product, **{"from": str(today)}).json()
    assert [item["quantity_delta"] for item in recent["items"]] == ["1"]
    old = _movements(
        client, actors[Role.WAREHOUSE], product, to=str(today - timedelta(days=1))
    ).json()
    assert [item["quantity_delta"] for item in old["items"]] == ["5"]
    sales = _movements(client, actors[Role.WAREHOUSE], product, type="sale").json()
    assert sales["items"] == []


def test_solicitante_en_movimientos_aprobados(
    client, make_user, auth_headers, make_product, give_stock
) -> None:
    """US2 escenario 3: el kardex muestra quién solicitó y quién aprobó."""
    admin = make_user(Role.ADMIN, username="dueno")
    warehouse = make_user(Role.WAREHOUSE, username="almacen", full_name="José Almacén")
    admin_headers, warehouse_headers = auth_headers(admin), auth_headers(warehouse)
    product = make_product("CON")
    give_stock(product, "4")
    request = client.post(
        "/api/v1/inventory/adjustments",
        json={"product_id": str(product.id), "quantity_delta": "-1", "reason": "loss"},
        headers=warehouse_headers,
    ).json()["request"]
    client.post(
        f"/api/v1/inventory/adjustment-requests/{request['id']}/approve", headers=admin_headers
    )
    [latest, *_] = _movements(client, warehouse_headers, product).json()["items"]
    assert latest["requested_by"]["full_name"] == "José Almacén"
    assert latest["created_by"]["full_name"] == admin.full_name


def test_vendedor_no_ve_el_kardex(client, actors, make_product) -> None:
    """FR-022: el Vendedor solo ve el stock actual, no el kardex."""
    product = make_product("CON")
    assert _movements(client, actors[Role.SELLER], product).status_code == 403


def test_almacen_sin_costos_en_el_kardex(client, actors, make_product, give_stock) -> None:
    """FR-022, principio IV: el Almacén no recibe los campos de costo del movimiento."""
    product = make_product("CON")
    give_stock(product, "2")
    [item] = _movements(client, actors[Role.WAREHOUSE], product).json()["items"]
    assert "cost_before_usd" not in item and "cost_after_usd" not in item
    [admin_item] = _movements(client, actors[Role.ADMIN], product).json()["items"]
    assert "cost_before_usd" in admin_item
