"""Categorías, atributos y unidades configurables por el Admin (RF-03 a RF-05; FR-028 a
FR-031; US6; research R5 y R12)."""

import pytest

from app.domain.roles import Role
from tests.helpers import audit_actions

pytestmark = pytest.mark.db


@pytest.fixture
def actors(make_user, auth_headers):
    return {
        role: auth_headers(make_user(role, username=f"config_{role.value}"))
        for role in (Role.ADMIN, Role.SELLER, Role.WAREHOUSE)
    }


def _categories(client, headers, **params) -> dict[str, dict]:
    response = client.get("/api/v1/categories", params=params, headers=headers)
    return {category["sku_prefix"]: category for category in response.json()}


def _units(client, headers, **params) -> dict[str, dict]:
    response = client.get("/api/v1/units", params=params, headers=headers)
    return {unit["code"]: unit for unit in response.json()}


def test_datos_iniciales(client, actors) -> None:
    """US6 escenario 1, FR-028: las cuatro categorías, sus atributos y las dos unidades."""
    headers = actors[Role.SELLER]
    categories = _categories(client, headers)
    units = _units(client, headers)
    assert set(categories) == {"MAN", "CON", "FER", "FRT"}
    assert categories["MAN"]["name"] == "Mangueras"
    assert categories["MAN"]["unit_locked"] is True
    assert categories["MAN"]["default_unit_id"] == units["m"]["id"]
    assert [a["key"] for a in categories["MAN"]["attributes"]] == [
        "hose_type",
        "diameter",
        "material",
    ]
    hose_type = categories["MAN"]["attributes"][0]
    assert hose_type["is_required"] and hose_type["is_filterable"]
    assert "R2" in [option["value"] for option in hose_type["options"]]
    assert [a["key"] for a in categories["CON"]["attributes"]] == [
        "fitting_type",
        "thread",
        "size",
        "material",
    ]
    assert [a["key"] for a in categories["FER"]["attributes"]] == ["ferrule_type", "size"]
    assert categories["FRT"]["attributes"] == []
    assert (units["m"]["decimals"], units["u"]["decimals"]) == (2, 0)


def _new_category(client, headers, prefix="ACE", name="Aceites", unit_code="u"):
    units = _units(client, headers)
    return client.post(
        "/api/v1/categories",
        json={
            "name": name,
            "sku_prefix": prefix,
            "default_unit_id": units[unit_code]["id"],
            "unit_locked": False,
        },
        headers=headers,
    )


def test_categoria_nueva_con_su_prefijo(client, actors) -> None:
    """US6 (prueba independiente): una categoría nueva da SKU con su prefijo."""
    admin = actors[Role.ADMIN]
    created = _new_category(client, admin)
    assert created.status_code == 201, created.text
    product = client.post(
        "/api/v1/products",
        json={"category_id": created.json()["id"], "name": "Aceite hidráulico 68"},
        headers=admin,
    )
    assert product.json()["sku"] == "ACE-0001"


@pytest.mark.parametrize(("prefix", "status"), [("MAN", 409), ("ac", 422), ("ACEI", 422)])
def test_prefijo_repetido_o_invalido(client, actors, prefix, status) -> None:
    """US6 escenario 2, FR-029: tres letras mayúsculas, único."""
    response = _new_category(client, actors[Role.ADMIN], prefix=prefix)
    assert response.status_code == status
    if status == 409:
        assert response.json()["detail"]["code"] == "prefix_in_use"


def test_prefijo_fijo_con_productos_y_renombrar(client, actors, make_product, category_id) -> None:
    """US6 escenario 3: con productos el prefijo no cambia; el nombre sí."""
    admin = actors[Role.ADMIN]
    make_product("CON")
    path = f"/api/v1/categories/{category_id('CON')}"
    blocked = client.patch(path, json={"sku_prefix": "COX"}, headers=admin)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "prefix_in_use"
    renamed = client.patch(path, json={"name": "Conexiones y adaptadores"}, headers=admin)
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Conexiones y adaptadores"
    free = client.patch(
        f"/api/v1/categories/{category_id('FRT')}", json={"sku_prefix": "FRR"}, headers=admin
    )
    assert free.json()["sku_prefix"] == "FRR"


def test_categoria_inactiva_no_admite_productos(client, actors, category_id) -> None:
    admin = actors[Role.ADMIN]
    client.patch(
        f"/api/v1/categories/{category_id('FRT')}", json={"is_active": False}, headers=admin
    )
    response = client.post(
        "/api/v1/products",
        json={"category_id": str(category_id("FRT")), "name": "Tornillo"},
        headers=admin,
    )
    assert response.status_code == 422
    assert "category_id" in response.json()["detail"]["fields"]
    assert "FRT" not in _categories(client, admin)
    assert "FRT" in _categories(client, admin, include_inactive="true")


def test_atributos(client, actors, make_product, category_id) -> None:
    """US6 escenario 4, FR-030: agregar una opción, desactivar una usada sin alterar el
    valor guardado, y claves y tipos que no cambian."""
    admin = actors[Role.ADMIN]
    categories = _categories(client, admin)
    hose_type = categories["MAN"]["attributes"][0]
    path = f"/api/v1/attributes/{hose_type['id']}"

    options = [*hose_type["options"], {"value": "R13", "is_active": True}]
    added = client.patch(path, json={"options": options}, headers=admin)
    assert added.status_code == 200, added.text
    assert "R13" in [option["value"] for option in added.json()["options"]]

    product = make_product("MAN", attributes={"hose_type": "R1", "diameter": '1/2"'})
    without_r1 = [
        {**option, "is_active": option["value"] != "R1"} for option in added.json()["options"]
    ]
    client.patch(path, json={"options": without_r1}, headers=admin)
    kept = client.get(f"/api/v1/products/{product.id}", headers=admin).json()
    assert kept["attributes"]["hose_type"] == "R1"
    rejected = client.post(
        "/api/v1/products",
        json={
            "category_id": str(category_id("MAN")),
            "name": "Manguera",
            "attributes": {"hose_type": "R1", "diameter": '1/2"'},
        },
        headers=admin,
    )
    assert rejected.status_code == 422

    removed = client.patch(path, json={"options": without_r1[1:]}, headers=admin)
    assert removed.status_code == 422
    for field in ({"key": "tipo"}, {"data_type": "text"}):
        assert client.patch(path, json=field, headers=admin).status_code == 422


def test_atributo_nuevo(client, actors, category_id) -> None:
    admin = actors[Role.ADMIN]
    path = f"/api/v1/categories/{category_id('FRT')}/attributes"
    created = client.post(
        path,
        json={
            "key": "material",
            "label": "Material",
            "data_type": "option",
            "options": [{"value": "Acero", "is_active": True}],
            "is_required": False,
            "is_filterable": True,
            "sort_order": 1,
        },
        headers=admin,
    )
    assert created.status_code == 201, created.text
    bad_key = client.post(
        path,
        json={"key": "Material X", "label": "X", "data_type": "text"},
        headers=admin,
    )
    assert bad_key.status_code == 422
    repeated = client.post(
        path, json={"key": "material", "label": "Otro", "data_type": "text"}, headers=admin
    )
    assert repeated.status_code == 409
    no_options = client.post(
        path, json={"key": "color", "label": "Color", "data_type": "option"}, headers=admin
    )
    assert no_options.status_code == 422


def test_unidades(client, actors, make_product) -> None:
    """US6 escenario 5, FR-031: unidades con 0 o 2 decimales; decimales y código fijos;
    una unidad en uso no se desactiva."""
    admin = actors[Role.ADMIN]
    box = client.post(
        "/api/v1/units", json={"code": "caja", "name": "caja", "decimals": 0}, headers=admin
    )
    assert box.status_code == 201
    assert (
        client.post(
            "/api/v1/units", json={"code": "kg", "name": "kilo", "decimals": 1}, headers=admin
        ).status_code
        == 422
    )
    path = f"/api/v1/units/{box.json()['id']}"
    assert client.patch(path, json={"decimals": 2}, headers=admin).status_code == 422
    assert client.patch(path, json={"code": "cj"}, headers=admin).status_code == 422
    assert client.patch(path, json={"name": "caja de 10"}, headers=admin).json()["name"] == (
        "caja de 10"
    )

    make_product("CON")
    piece = _units(client, admin)["u"]
    in_use = client.patch(f"/api/v1/units/{piece['id']}", json={"is_active": False}, headers=admin)
    assert in_use.status_code == 409
    assert in_use.json()["detail"]["code"] == "unit_in_use"
    off = client.patch(path, json={"is_active": False}, headers=admin)
    assert off.json()["is_active"] is False
    assert "caja" not in _units(client, admin)
    assert "caja" in _units(client, admin, include_inactive="true")


@pytest.mark.parametrize("role", [Role.SELLER, Role.WAREHOUSE])
def test_solo_el_admin_configura(client, actors, category_id, role) -> None:
    """US6 escenario 6."""
    headers = actors[role]
    assert _new_category(client, headers).status_code == 403
    response = client.patch(
        f"/api/v1/categories/{category_id('FRT')}", json={"name": "X"}, headers=headers
    )
    assert response.status_code == 403
    unit = client.post(
        "/api/v1/units", json={"code": "x", "name": "x", "decimals": 0}, headers=headers
    )
    assert unit.status_code == 403


def test_auditoria_de_configuracion(client, actors, category_id, db) -> None:
    """FR-034: cambios de categorías, atributos y unidades, con antes y después."""
    admin = actors[Role.ADMIN]
    created = _new_category(client, admin).json()
    client.patch(
        f"/api/v1/categories/{created['id']}", json={"name": "Aceites y grasas"}, headers=admin
    )
    client.post(
        f"/api/v1/categories/{created['id']}/attributes",
        json={"key": "viscosity", "label": "Viscosidad", "data_type": "text"},
        headers=admin,
    )
    client.post("/api/v1/units", json={"code": "lt", "name": "litro", "decimals": 2}, headers=admin)
    actions = audit_actions(db)
    for action in ("category.created", "category.updated", "attribute.created", "unit.created"):
        assert action in actions
