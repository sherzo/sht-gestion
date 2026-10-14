"""Gastos frecuentes (RF-14/FR-032, FR-033; research R9)."""

import pytest
from sqlalchemy import select

from app.db.models import AuditLog
from app.domain.roles import Role

pytestmark = pytest.mark.db

URL = "/api/v1/charge-templates"


@pytest.fixture
def admin(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.ADMIN, username="dueno"))


@pytest.fixture
def warehouse(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.WAREHOUSE, username="almacen"))


def test_crear_y_listar(client, admin, warehouse, db) -> None:
    commission = client.post(
        URL,
        json={"name": "Comisión de compra", "charge_type": "percent", "default_value": "10"},
        headers=admin,
    )
    assert commission.status_code == 201, commission.text
    assert commission.json()["default_value"] == "10.00"
    shipping = client.post(
        URL,
        json={"name": "Envío China–Venezuela", "charge_type": "fixed", "currency": "USD"},
        headers=admin,
    )
    assert shipping.status_code == 201
    client.patch(f"{URL}/{shipping.json()['id']}", json={"is_active": False}, headers=admin)
    assert [t["name"] for t in client.get(URL, headers=warehouse).json()] == ["Comisión de compra"]
    everything = client.get(URL, params={"include_inactive": True}, headers=admin).json()
    assert len(everything) == 2
    only_active = client.get(URL, params={"include_inactive": True}, headers=warehouse).json()
    assert len(only_active) == 1
    actions = list(
        db.scalars(select(AuditLog.action).where(AuditLog.action.like("charge_template.%")))
    )
    assert sorted(actions) == [
        "charge_template.created",
        "charge_template.created",
        "charge_template.updated",
    ]


def test_nombre_repetido_entre_activos(client, admin) -> None:
    client.post(
        URL, json={"name": "Flete", "charge_type": "fixed", "currency": "USD"}, headers=admin
    )
    response = client.post(URL, json={"name": "flete", "charge_type": "percent"}, headers=admin)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "template_name_in_use"


@pytest.mark.parametrize(
    "body",
    [
        {"name": "X", "charge_type": "fixed"},
        {"name": "X", "charge_type": "percent", "currency": "USD"},
        {"name": "X", "charge_type": "percent", "default_value": "101"},
        {"name": "", "charge_type": "percent"},
    ],
)
def test_datos_invalidos(client, admin, body) -> None:
    assert client.post(URL, json=body, headers=admin).status_code == 422


def test_el_tipo_no_cambia(client, admin) -> None:
    created = client.post(URL, json={"name": "X", "charge_type": "percent"}, headers=admin).json()
    response = client.patch(f"{URL}/{created['id']}", json={"charge_type": "fixed"}, headers=admin)
    assert response.status_code == 422


def test_editar_no_cambia_compras_existentes(
    client, admin, make_supplier, make_product, make_charge_template, make_purchase
) -> None:
    template = make_charge_template("Comisión", "percent", "10")
    charges = [
        {
            "description": "Comisión",
            "charge_type": "percent",
            "percent": "10",
            "charge_template_id": str(template.id),
        }
    ]
    purchase = make_purchase(
        admin, make_supplier(), [(make_product("FRT"), "1", "100")], charges=charges
    )
    client.patch(f"{URL}/{template.id}", json={"default_value": "15"}, headers=admin)
    again = client.get(f"/api/v1/purchases/{purchase['id']}", headers=admin).json()
    assert again["charges"][0]["percent"] == "10.00"
    assert again["charges"][0]["charge_template_id"] == str(template.id)


def test_almacen_no_edita_y_vendedor_no_ve(client, warehouse, make_user, auth_headers) -> None:
    assert (
        client.post(
            URL, json={"name": "X", "charge_type": "percent"}, headers=warehouse
        ).status_code
        == 403
    )
    seller = auth_headers(make_user(Role.SELLER, username="vendedor"))
    assert client.get(URL, headers=seller).status_code == 403
