"""Proveedores (RF-13/FR-001 a FR-003, research R5)."""

import pytest
from sqlalchemy import select

from app.db.models import AuditLog
from app.domain.roles import Role

pytestmark = pytest.mark.db

URL = "/api/v1/suppliers"


@pytest.fixture
def warehouse(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.WAREHOUSE, username="almacen"))


def test_alta_por_almacen_normaliza_el_rif(client, warehouse, db) -> None:
    response = client.post(
        URL,
        json={"name": "Hidráulica Aragua", "rif": "j123456789", "phone": "0414-5551234"},
        headers=warehouse,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["rif"] == "J-12345678-9"
    assert body["is_active"] is True
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "supplier.created"))
    assert entry.after["rif"] == "J-12345678-9"


def test_rif_repetido_en_otro_formato(client, warehouse) -> None:
    client.post(URL, json={"name": "Hidráulica Aragua", "rif": "J-12345678-9"}, headers=warehouse)
    response = client.post(URL, json={"name": "Otro", "rif": "j 12345678 9"}, headers=warehouse)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "rif_in_use"
    assert detail["supplier_name"] == "Hidráulica Aragua"


def test_sin_rif_y_dos_sin_rif_conviven(client, warehouse) -> None:
    for name in ("Vendedor informal", "Otro informal"):
        response = client.post(URL, json={"name": name}, headers=warehouse)
        assert response.status_code == 201, response.text
        assert response.json()["rif"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"name": "X", "rif": "X-12345678-9"},
        {"name": ""},
        {"name": "a" * 121},
        {"name": "X", "phone": "1" * 31},
    ],
)
def test_datos_invalidos(client, warehouse, body) -> None:
    assert client.post(URL, json=body, headers=warehouse).status_code == 422


def test_editar_desactivar_y_reactivar(client, warehouse, db) -> None:
    created = client.post(URL, json={"name": "Proveedor"}, headers=warehouse).json()
    url = f"{URL}/{created['id']}"
    response = client.patch(
        url, json={"name": "Proveedor C.A.", "notes": "Despacha martes"}, headers=warehouse
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Proveedor C.A."
    assert (
        client.patch(url, json={"is_active": False}, headers=warehouse).json()["is_active"] is False
    )
    assert (
        client.patch(url, json={"is_active": True}, headers=warehouse).json()["is_active"] is True
    )
    entry = db.scalars(
        select(AuditLog).where(AuditLog.action == "supplier.updated").order_by(AuditLog.occurred_at)
    ).first()
    assert entry.before["name"] == "Proveedor"
    assert entry.after["name"] == "Proveedor C.A."


def test_cambiar_rif_a_uno_ocupado(client, warehouse) -> None:
    client.post(URL, json={"name": "A", "rif": "J-11111111-1"}, headers=warehouse)
    other = client.post(URL, json={"name": "B"}, headers=warehouse).json()
    response = client.patch(f"{URL}/{other['id']}", json={"rif": "J111111111"}, headers=warehouse)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "rif_in_use"


def test_busqueda_y_filtro_de_activos(client, warehouse) -> None:
    client.post(URL, json={"name": "Hidráulica Aragua", "rif": "J-12345678-9"}, headers=warehouse)
    inactive = client.post(URL, json={"name": "Mangueras Lara"}, headers=warehouse).json()
    client.patch(f"{URL}/{inactive['id']}", json={"is_active": False}, headers=warehouse)

    by_name = client.get(URL, params={"q": "hidraulica"}, headers=warehouse).json()
    assert [item["name"] for item in by_name["items"]] == ["Hidráulica Aragua"]
    by_rif = client.get(URL, params={"q": "j12345678"}, headers=warehouse).json()
    assert by_rif["total"] == 1
    active = client.get(URL, params={"is_active": "true"}, headers=warehouse).json()
    assert [item["name"] for item in active["items"]] == ["Hidráulica Aragua"]
    everyone = client.get(URL, headers=warehouse).json()
    assert everyone["total"] == 2


def test_vendedor_no_ve_proveedores(client, make_user, auth_headers) -> None:
    seller = auth_headers(make_user(Role.SELLER, username="vendedor"))
    assert client.get(URL, headers=seller).status_code == 403
