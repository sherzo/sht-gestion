"""Búsqueda de productos con filtros (RF-06/FR-032, FR-033; US3; research R4)."""

import pytest

from app.domain.roles import Role

pytestmark = pytest.mark.db


@pytest.fixture
def actors(make_user, auth_headers):
    return {
        role: auth_headers(make_user(role, username=f"busca_{role.value}"))
        for role in (Role.ADMIN, Role.SELLER, Role.WAREHOUSE)
    }


@pytest.fixture
def catalog(make_product, give_stock, category_id):
    hose_r2 = make_product(
        "MAN", name="Manguera hidráulica", attributes={"hose_type": "R2", "diameter": '1/2"'}
    )
    hose_r1 = make_product(
        "MAN", name="Manguera hidráulica", attributes={"hose_type": "R1", "diameter": '1/2"'}
    )
    hose_r2_big = make_product(
        "MAN", name="Manguera hidráulica", attributes={"hose_type": "R2", "diameter": '3/4"'}
    )
    swivel = make_product(
        "CON",
        name="Conexión hembra giratoria",
        attributes={"fitting_type": "Hembra giratoria", "size": '1/2"', "thread": "JIC"},
        sale_price="4.00",
        is_published=True,
    )
    low = make_product("FER", name="Ferrule prensable", min_stock="5")
    give_stock(low, "5")
    inactive = make_product("FRT", name="Teflón viejo", is_active=False)
    return {
        "hose_r2": hose_r2,
        "hose_r1": hose_r1,
        "hose_r2_big": hose_r2_big,
        "swivel": swivel,
        "low": low,
        "inactive": inactive,
    }


def _search(client, headers, **params):
    response = client.get("/api/v1/products", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _skus(data) -> list[str]:
    return [item["sku"] for item in data["items"]]


def test_sin_acento_ni_mayusculas(client, actors, catalog) -> None:
    """US3 escenario 2: "conexion giratoria" encuentra "Conexión hembra giratoria"."""
    data = _search(client, actors[Role.SELLER], q="CONEXION giratoria")
    assert _skus(data) == [catalog["swivel"].sku]


def test_por_atributos_y_en_cualquier_orden(client, actors, catalog) -> None:
    """US3 escenario 1: "r2 1/2" encuentra las mangueras R2 de 1/2" por sus atributos."""
    assert _skus(_search(client, actors[Role.SELLER], q="r2 1/2")) == [catalog["hose_r2"].sku]
    assert _skus(_search(client, actors[Role.SELLER], q='1/2" r2')) == [catalog["hose_r2"].sku]


def test_sku_exacto_primero(client, actors, catalog) -> None:
    """FR-032: buscar un SKU lo encuentra; el SKU exacto aparece primero."""
    sku = catalog["hose_r2_big"].sku
    data = _search(client, actors[Role.WAREHOUSE], q=sku.lower())
    assert _skus(data)[0] == sku
    assert _skus(_search(client, actors[Role.WAREHOUSE], q="man-"))[0].startswith("MAN-")


def test_comodines_de_like_no_rompen_la_busqueda(client, actors, catalog) -> None:
    assert _search(client, actors[Role.ADMIN], q="%")["items"] == []
    assert _search(client, actors[Role.ADMIN], q="_")["items"] == []


def test_filtros(client, actors, catalog, category_id) -> None:
    """US3 escenario 3, FR-033: categoría, atributo filtrable, estado, publicación y stock
    bajo."""
    admin = actors[Role.ADMIN]
    by_category = _search(client, admin, category_id=str(category_id("MAN")))
    assert len(by_category["items"]) == 3
    by_attribute = _search(client, admin, **{"attr.hose_type": "R2"})
    assert sorted(_skus(by_attribute)) == sorted(
        [catalog["hose_r2"].sku, catalog["hose_r2_big"].sku]
    )
    combined = _search(client, admin, **{"attr.hose_type": "R2", "attr.diameter": '3/4"'})
    assert _skus(combined) == [catalog["hose_r2_big"].sku]
    assert _skus(_search(client, admin, is_active="false")) == [catalog["inactive"].sku]
    assert _skus(_search(client, admin, is_published="true")) == [catalog["swivel"].sku]
    low_stock = _skus(_search(client, admin, low_stock="true"))
    assert catalog["low"].sku in low_stock
    assert catalog["swivel"].sku in low_stock  # stock 0 y mínimo 0: agotado


def test_atributo_no_filtrable(client, actors, catalog) -> None:
    """R4: solo se filtra por atributos marcados como filtrables."""
    response = client.get(
        "/api/v1/products", params={"attr.material": "Caucho"}, headers=actors[Role.ADMIN]
    )
    assert response.status_code == 422
    assert "attr.material" in response.json()["detail"]["fields"]


def test_vendedor_solo_ve_activos(client, actors, catalog) -> None:
    """FR-007: el Vendedor no recibe productos inactivos aunque los pida."""
    data = _search(client, actors[Role.SELLER], is_active="false")
    assert catalog["inactive"].sku not in _skus(data)
    assert all(item["is_active"] for item in data["items"])


def test_paginacion(client, actors, catalog) -> None:
    # El Admin ve también el producto inactivo: seis en total.
    first = _search(client, actors[Role.ADMIN], page_size=2, page=1)
    second = _search(client, actors[Role.ADMIN], page_size=2, page=2)
    assert first["total"] == second["total"] == 6
    assert len(first["items"]) == len(second["items"]) == 2
    assert not set(_skus(first)) & set(_skus(second))
