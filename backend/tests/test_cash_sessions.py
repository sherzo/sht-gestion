"""Apertura de caja por la cola de salida (RF-29, RF-30, RN-16/FR-005 a FR-008; R7)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import clock
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.conftest import device_headers, operation
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

URL = "/api/v1/sync/operations"


def open_body(float_ves: str = "500.00", float_usd: str = "20.00") -> dict:
    return operation(
        "cash_session.open",
        {"id": str(uuid.uuid7()), "opening_float_ves": float_ves, "opening_float_usd": float_usd},
    )


@pytest.fixture
def seller(make_user):
    return make_user(Role.SELLER, full_name="Vendedor Uno")


@pytest.fixture
def counter(make_device, make_rate):
    make_rate(business_date(clock.utcnow()), "36.50")
    return make_device("Mostrador principal")


def test_apertura_con_fondo(client: TestClient, seller, auth_headers, counter, db) -> None:
    device, token = counter
    response = client.post(
        URL, json=open_body(), headers=device_headers(auth_headers(seller), token)
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "open"
    assert data["device_id"] == str(device.id)
    assert data["opened_by"]["id"] == str(seller.id)
    assert data["opening_float_ves"] == "500.00"
    assert data["opening_float_usd"] == "20.00"
    assert data["business_date"] == business_date(clock.utcnow()).isoformat()
    [entry] = audit_entries(db, "cash_session.opened")
    assert entry.user_id == seller.id
    assert entry.device_id == device.id
    assert entry.after == {"opening_float_ves": "500.00", "opening_float_usd": "20.00"}


def test_una_sola_caja_abierta_por_equipo(
    client: TestClient, seller, make_user, auth_headers, counter, make_device
) -> None:
    _, token = counter
    headers = device_headers(auth_headers(seller), token)
    assert client.post(URL, json=open_body(), headers=headers).status_code == 200
    other_seller = device_headers(auth_headers(make_user(Role.SELLER)), token)
    second = client.post(URL, json=open_body(), headers=other_seller)
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["code"] == "cash_session_open"
    assert detail["opened_by"] == "Vendedor Uno"
    assert detail["opened_at"]
    # Otro equipo abre su propia caja.
    _, other_token = make_device("Tablet")
    other = client.post(
        URL, json=open_body(), headers=device_headers(auth_headers(seller), other_token)
    )
    assert other.status_code == 200


def test_fondo_cero_permitido(client: TestClient, seller, auth_headers, counter) -> None:
    _, token = counter
    response = client.post(
        URL, json=open_body("0.00", "0"), headers=device_headers(auth_headers(seller), token)
    )
    assert response.status_code == 200, response.text
    assert response.json()["opening_float_usd"] == "0.00"


@pytest.mark.parametrize(
    ("float_ves", "float_usd"), [("-1.00", "0"), ("0", "-0.01"), ("10.001", "0"), ("abc", "0")]
)
def test_fondo_invalido(client, seller, auth_headers, counter, float_ves, float_usd) -> None:
    _, token = counter
    response = client.post(
        URL,
        json=open_body(float_ves, float_usd),
        headers=device_headers(auth_headers(seller), token),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"


def test_sin_ninguna_tasa_no_se_abre(client, seller, auth_headers, make_device) -> None:
    _, token = make_device()
    response = client.post(
        URL, json=open_body(), headers=device_headers(auth_headers(seller), token)
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "exchange_rate_missing"


def test_almacen_no_abre_caja(client, make_user, auth_headers, counter) -> None:
    _, token = counter
    headers = device_headers(auth_headers(make_user(Role.WAREHOUSE)), token)
    assert client.post(URL, json=open_body(), headers=headers).status_code == 403


def test_los_datos_de_apertura_no_se_modifican(client, seller, auth_headers, counter, db) -> None:
    _, token = counter
    session = client.post(
        URL, json=open_body(), headers=device_headers(auth_headers(seller), token)
    ).json()
    with pytest.raises(Exception, match="no se modifican"):
        db.execute(
            text("UPDATE cash_session SET opening_float_usd = 1 WHERE id = :id"),
            {"id": session["id"]},
        )
    db.rollback()
    with pytest.raises(Exception, match="no se borra"):
        db.execute(text("DELETE FROM cash_session WHERE id = :id"), {"id": session["id"]})
    db.rollback()
