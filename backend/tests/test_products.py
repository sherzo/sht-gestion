"""Alta, edición, activación y restricciones de productos (RF-01, RF-05, RN-13; FR-001,
FR-004 a FR-007, FR-010; research R10 y R15)."""

import pytest

from app.domain.roles import Role
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

HOSE = {"hose_type": "R2", "diameter": '1/2"'}


@pytest.fixture
def actors(make_user, auth_headers):
    users = {
        role: make_user(role, username=f"usuario_{role.value}")
        for role in (Role.ADMIN, Role.SELLER, Role.WAREHOUSE)
    }
    return {role: auth_headers(user) for role, user in users.items()}


def _create(client, headers, category, **body):
    payload = {"category_id": str(category), "name": "Manguera R2 1/2", "description": "", **body}
    return client.post("/api/v1/products", json=payload, headers=headers)


def test_alta_por_almacen_sin_precio_ni_costo(client, actors, category_id) -> None:
    """US1 escenario 1: SKU, unidad metro, stock 0 y sin precio para el Almacén."""
    response = _create(
        client,
        actors[Role.WAREHOUSE],
        category_id("MAN"),
        description="Dos mallas de acero",
        attributes={**HOSE, "material": "Caucho"},
        min_stock="10",
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["sku"] == "MAN-0001"
    assert data["unit"]["code"] == "m"
    assert data["stock"] == "0.00"
    assert data["min_stock"] == "10.00"
    assert data["is_low_stock"] is True
    assert data["warnings"] == []
    assert "sale_price_usd" not in data
    assert "avg_cost_usd" not in data


def test_alta_por_admin_sin_precio_ni_costo(client, actors, category_id) -> None:
    """FR-001: el alta no fija precio ni costo; el Admin los ve vacíos."""
    data = _create(client, actors[Role.ADMIN], category_id("MAN"), attributes=HOSE).json()
    assert data["sale_price_usd"] is None
    assert data["avg_cost_usd"] is None
    assert data["cost_locked"] is False


def test_alta_no_admite_precio_en_el_cuerpo(client, actors, category_id) -> None:
    """US1 escenario 6: el Almacén no fija precio ni publica, aun sin pasar por la pantalla."""
    response = _create(
        client,
        actors[Role.WAREHOUSE],
        category_id("MAN"),
        attributes=HOSE,
        sale_price_usd="10.00",
        is_published=True,
    )
    assert response.status_code == 422
    assert {"sale_price_usd", "is_published"} <= set(response.json()["detail"]["fields"])


def test_mangueras_siempre_por_metro(client, actors, category_id, db) -> None:
    """RF-05/FR-005, US1 escenario 3: la unidad de las mangueras no cambia."""
    from sqlalchemy import select

    from app.db.models import Unit

    piece = db.scalar(select(Unit.id).where(Unit.code == "u"))
    response = _create(
        client, actors[Role.ADMIN], category_id("MAN"), attributes=HOSE, unit_id=str(piece)
    )
    assert response.status_code == 422
    assert "unit_id" in response.json()["detail"]["fields"]


def test_atributos_invalidos(client, actors, category_id) -> None:
    """FR-006, US1 escenario 4: opción fuera de la lista y obligatorio faltante."""
    wrong = _create(
        client, actors[Role.ADMIN], category_id("MAN"), attributes={**HOSE, "hose_type": "R9"}
    )
    assert wrong.status_code == 422
    assert "attributes.hose_type" in wrong.json()["detail"]["fields"]

    missing = _create(client, actors[Role.ADMIN], category_id("MAN"), attributes={})
    assert missing.status_code == 422
    assert {"attributes.hose_type", "attributes.diameter"} <= set(
        missing.json()["detail"]["fields"]
    )


def test_ferreteria_sin_atributos(client, actors, category_id) -> None:
    """US1 escenario 5: Ferretería no exige atributos técnicos."""
    response = _create(
        client,
        actors[Role.WAREHOUSE],
        category_id("FRT"),
        name="Teflón",
        description="Cinta de 3/4",
    )
    assert response.status_code == 201
    assert response.json()["unit"]["code"] == "u"


def test_nombre_repetido_advierte_al_crear_y_al_renombrar(client, actors, category_id) -> None:
    """Caso borde "nombre duplicado": se permite, pero se advierte."""
    headers = actors[Role.WAREHOUSE]
    first = _create(client, headers, category_id("FRT"), name="Teflón")
    second = _create(client, headers, category_id("FRT"), name="teflón ")
    assert first.json()["warnings"] == []
    assert second.status_code == 201
    assert second.json()["warnings"] == ["duplicate_name"]

    other = _create(client, headers, category_id("FRT"), name="Abrazadera").json()
    renamed = client.patch(
        f"/api/v1/products/{other['id']}", json={"name": "Teflón"}, headers=headers
    )
    assert renamed.status_code == 200
    assert renamed.json()["warnings"] == ["duplicate_name"]


def test_stock_minimo_segun_la_unidad(client, actors, category_id, db) -> None:
    """FR-020: el stock mínimo respeta los decimales de la unidad, también al cambiarla."""
    from sqlalchemy import select

    from app.db.models import Unit

    headers = actors[Role.WAREHOUSE]
    assert (
        _create(client, headers, category_id("FRT"), name="Tuerca", min_stock="1.5").status_code
        == 422
    )
    assert (
        _create(client, headers, category_id("MAN"), attributes=HOSE, min_stock="0.305").status_code
        == 422
    )
    meter = db.scalar(select(Unit.id).where(Unit.code == "m"))
    piece = db.scalar(select(Unit.id).where(Unit.code == "u"))
    cable = _create(
        client, headers, category_id("FRT"), name="Cable", unit_id=str(meter), min_stock="2.50"
    ).json()
    assert cable["min_stock"] == "2.50"
    changed = client.patch(
        f"/api/v1/products/{cable['id']}", json={"unit_id": str(piece)}, headers=headers
    )
    assert changed.status_code == 422
    assert "min_stock" in changed.json()["detail"]["fields"]


def test_datos_viejos_advierten_pero_se_guardan(client, actors, category_id) -> None:
    """R15: gana el último que guarda, con aviso si editó sobre datos viejos."""
    headers = actors[Role.WAREHOUSE]
    created = _create(client, headers, category_id("FRT"), name="Arandela").json()
    first = client.patch(
        f"/api/v1/products/{created['id']}",
        json={"description": "Primera", "updated_at": created["updated_at"]},
        headers=headers,
    )
    assert first.json()["warnings"] == []
    stale = client.patch(
        f"/api/v1/products/{created['id']}",
        json={"description": "Segunda", "updated_at": created["updated_at"]},
        headers=headers,
    )
    assert stale.status_code == 200
    assert stale.json()["description"] == "Segunda"
    assert stale.json()["warnings"] == ["stale_data"]


def test_categoria_y_unidad_fijas_con_movimientos(
    client, actors, category_id, make_product, give_stock
) -> None:
    """FR-004: con movimientos, la categoría y la unidad ya no cambian."""
    product = make_product("CON")
    give_stock(product, "5")
    response = client.patch(
        f"/api/v1/products/{product.id}",
        json={"category_id": str(category_id("FER"))},
        headers=actors[Role.ADMIN],
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "product_has_movements"


def test_desactivar_y_reactivar(client, actors, make_product, give_stock, db) -> None:
    """FR-007, US1 escenario 8: se desactiva sin borrarse, sale del catálogo y vuelve."""
    product = make_product("CON", sale_price="5.00", is_published=True)
    give_stock(product, "3")
    headers = actors[Role.WAREHOUSE]
    off = client.patch(f"/api/v1/products/{product.id}", json={"is_active": False}, headers=headers)
    assert off.status_code == 200
    assert off.json()["is_active"] is False
    assert off.json()["is_published"] is False
    assert off.json()["sku"] == product.sku
    assert off.json()["warnings"] == ["has_stock"]

    seller = actors[Role.SELLER]
    assert client.get(f"/api/v1/products/{product.id}", headers=seller).status_code == 404
    listed = client.get("/api/v1/products", params={"is_active": "false"}, headers=seller).json()
    assert product.sku not in [item["sku"] for item in listed["items"]]

    on = client.patch(f"/api/v1/products/{product.id}", json={"is_active": True}, headers=headers)
    assert on.json()["is_active"] is True
    assert on.json()["stock"] == "3"
    actions = [entry.action for entry in audit_entries(db, "product.deactivated")]
    assert actions == ["product.deactivated"]
    assert len(audit_entries(db, "product.unpublished")) == 1
    assert len(audit_entries(db, "product.activated")) == 1


def test_vendedor_no_crea_ni_edita(client, actors, category_id, make_product) -> None:
    """US1 escenario 7: el servidor rechaza al Vendedor."""
    seller = actors[Role.SELLER]
    assert _create(client, seller, category_id("FRT"), name="X").status_code == 403
    product = make_product("FRT")
    response = client.patch(f"/api/v1/products/{product.id}", json={"name": "Y"}, headers=seller)
    assert response.status_code == 403


def test_lista_y_ficha(client, actors, make_product) -> None:
    """FR-001: lista paginada y ficha según el rol."""
    make_product("FRT", name="Zeta")
    product = make_product("FRT", name="Alfa")
    listed = client.get("/api/v1/products", headers=actors[Role.SELLER]).json()
    assert [item["name"] for item in listed["items"]] == ["Alfa", "Zeta"]
    assert listed["total"] == 2
    detail = client.get(f"/api/v1/products/{product.id}", headers=actors[Role.SELLER]).json()
    assert detail["sale_price_usd"] is None
    assert "avg_cost_usd" not in detail


def test_auditoria_de_productos(client, actors, category_id, db) -> None:
    """FR-034: alta, edición y cambio de categoría quedan auditados con antes y después."""
    headers = actors[Role.ADMIN]
    created = _create(client, headers, category_id("MAN"), attributes=HOSE).json()
    client.patch(
        f"/api/v1/products/{created['id']}", json={"name": "Manguera nueva"}, headers=headers
    )
    client.patch(
        f"/api/v1/products/{created['id']}",
        json={
            "category_id": str(category_id("FER")),
            "attributes": {"ferrule_type": "Prensable", "size": '1/2"'},
        },
        headers=headers,
    )
    [created_entry] = audit_entries(db, "product.created")
    assert created_entry.after["sku"] == "MAN-0001"
    updated = audit_entries(db, "product.updated")
    assert updated[0].before["name"] == "Manguera R2 1/2"
    assert updated[0].after["name"] == "Manguera nueva"
    [moved] = audit_entries(db, "product.category_changed")
    assert moved.before["sku"] == "MAN-0001"
    assert moved.after["sku"] == "FER-0001"


def test_no_hay_kits(client, actors, category_id) -> None:
    """RN-13/FR-010: el producto no admite componentes."""
    response = _create(client, actors[Role.ADMIN], category_id("FRT"), name="Kit", components=["x"])
    assert response.status_code == 422


def test_atributo_desactivado_se_conserva_al_editar(client, actors, make_product, db) -> None:
    """FR-030: editar un producto sin enviar un atributo desactivado no borra su valor."""
    from sqlalchemy import select

    from app.db.models import AttributeDefinition

    product = make_product("MAN", attributes={**HOSE, "material": "Caucho"})
    material = db.scalar(select(AttributeDefinition).where(AttributeDefinition.key == "material"))
    material.is_active = False
    db.commit()
    response = client.patch(
        f"/api/v1/products/{product.id}",
        json={"name": "Manguera renombrada", "attributes": HOSE},
        headers=actors[Role.WAREHOUSE],
    )
    assert response.status_code == 200, response.text
    assert response.json()["attributes"]["material"] == "Caucho"
