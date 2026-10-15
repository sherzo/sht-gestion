"""Equipos de mostrador: registro con serie, token y revocación (RN-11/FR-001 a FR-004;
research R3)."""

import pytest
from fastapi.testclient import TestClient

from app.core import clock
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.conftest import device_headers
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

URL = "/api/v1/devices"


@pytest.fixture
def admin_headers(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.ADMIN))


def test_registro_asigna_series_en_orden_y_token_una_sola_vez(
    client: TestClient, admin_headers, db
) -> None:
    first = client.post(URL, json={"name": "Mostrador principal"}, headers=admin_headers)
    assert first.status_code == 201, first.text
    data = first.json()
    assert data["series"] == "A"
    assert data["name"] == "Mostrador principal"
    assert data["last_sequence_number"] == 0
    assert len(data["token"]) >= 40

    second = client.post(URL, json={"name": "Tablet"}, headers=admin_headers).json()
    assert second["series"] == "B"

    listed = client.get(URL, headers=admin_headers).json()
    assert [device["series"] for device in listed] == ["A", "B"]
    assert all("token" not in device for device in listed)

    entries = audit_entries(db, "device.registered")
    assert [entry.after["series"] for entry in entries] == ["A", "B"]
    assert all("token" not in (entry.after or {}) for entry in entries)


def test_una_serie_revocada_no_se_reutiliza(client: TestClient, admin_headers, db) -> None:
    first = client.post(URL, json={"name": "A"}, headers=admin_headers).json()
    client.post(URL, json={"name": "B"}, headers=admin_headers)
    revoked = client.post(f"{URL}/{first['id']}/revoke", headers=admin_headers)
    assert revoked.status_code == 200
    assert revoked.json()["revoked_at"] is not None
    third = client.post(URL, json={"name": "C"}, headers=admin_headers).json()
    assert third["series"] == "C"

    again = client.post(f"{URL}/{first['id']}/revoke", headers=admin_headers)
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "invalid_state"
    assert len(audit_entries(db, "device.revoked")) == 1


def test_equipo_actual_con_su_caja_y_correlativo(
    client: TestClient, make_user, auth_headers, make_device, make_rate, open_cash_session
) -> None:
    make_rate(business_date(clock.utcnow()), "36.50")
    seller = make_user(Role.SELLER)
    headers = auth_headers(seller)
    device, token = make_device("Mostrador")

    current = client.get(f"{URL}/current", headers=device_headers(headers, token))
    assert current.status_code == 200
    assert current.json()["series"] == device.series
    assert current.json()["open_cash_session"] is None

    session = open_cash_session(headers, token, "500.00", "20.00")
    current = client.get(f"{URL}/current", headers=device_headers(headers, token)).json()
    assert current["open_cash_session"]["id"] == session["id"]
    assert current["open_cash_session"]["opened_by"]["id"] == str(seller.id)


def test_equipo_actual_con_token_invalido_o_revocado(
    client: TestClient, make_user, auth_headers, make_device
) -> None:
    headers = auth_headers(make_user(Role.SELLER))
    response = client.get(f"{URL}/current", headers=device_headers(headers, "otro"))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "device_required"

    _, token = make_device(revoked=True)
    response = client.get(f"{URL}/current", headers=device_headers(headers, token))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "device_revoked"


@pytest.mark.parametrize("name", ["", "   ", "x" * 61])
def test_nombre_invalido(client: TestClient, admin_headers, name: str) -> None:
    assert client.post(URL, json={"name": name}, headers=admin_headers).status_code == 422
