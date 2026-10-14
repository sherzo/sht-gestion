"""Tasa BCV: carga, corrección auditada, histórico y tasa aplicable (RF-17, RN-15;
FR-025 a FR-027; research R6)."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import clock
from app.db.models import AuditLog
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db

URL = "/api/v1/exchange-rates"


@pytest.fixture
def admin(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.ADMIN, username="dueno"))


def today():
    return business_date(clock.utcnow())


def test_cargar_y_repetir(client, admin, db) -> None:
    response = client.post(
        URL, json={"business_date": today().isoformat(), "rate": "36.50"}, headers=admin
    )
    assert response.status_code == 201, response.text
    assert response.json()["rate"] == "36.50000000"
    assert response.json()["created_by"]["full_name"]
    again = client.post(
        URL, json={"business_date": today().isoformat(), "rate": "37"}, headers=admin
    )
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "rate_exists"
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "exchange_rate.created"))
    assert entry.after == {"business_date": today().isoformat(), "rate": "36.50000000"}


@pytest.mark.parametrize("rate", ["0", "-1", "1.123456789"])
def test_tasa_invalida(client, admin, rate) -> None:
    response = client.post(
        URL, json={"business_date": today().isoformat(), "rate": rate}, headers=admin
    )
    assert response.status_code == 422


def test_fecha_futura(client, admin) -> None:
    tomorrow = (today() + timedelta(days=1)).isoformat()
    assert (
        client.post(URL, json={"business_date": tomorrow, "rate": "36"}, headers=admin).status_code
        == 422
    )


def test_corregir_con_auditoria(client, admin, db) -> None:
    day = today().isoformat()
    client.post(URL, json={"business_date": day, "rate": "36.50"}, headers=admin)
    response = client.put(f"{URL}/{day}", json={"rate": "36.55"}, headers=admin)
    assert response.status_code == 200
    assert response.json()["rate"] == "36.55000000"
    assert response.json()["updated_by"] is not None
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "exchange_rate.corrected"))
    assert (entry.before["rate"], entry.after["rate"]) == ("36.50000000", "36.55000000")
    missing = client.put(
        f"{URL}/{(today() - timedelta(days=9)).isoformat()}", json={"rate": "1"}, headers=admin
    )
    assert missing.status_code == 404


def test_historico_y_tasa_aplicable(client, admin, make_user, auth_headers) -> None:
    older, newer = today() - timedelta(days=3), today()
    client.post(URL, json={"business_date": older.isoformat(), "rate": "36.20"}, headers=admin)
    client.post(URL, json={"business_date": newer.isoformat(), "rate": "36.50"}, headers=admin)
    history = client.get(URL, headers=admin).json()
    assert [item["business_date"] for item in history["items"]] == [
        newer.isoformat(),
        older.isoformat(),
    ]

    warehouse = auth_headers(make_user(Role.WAREHOUSE, username="almacen"))
    between = (today() - timedelta(days=2)).isoformat()
    applicable = client.get(f"{URL}/applicable", params={"date": between}, headers=warehouse)
    assert applicable.json() == {"rate": "36.20000000", "business_date": older.isoformat()}
    before_all = (today() - timedelta(days=4)).isoformat()
    assert (
        client.get(f"{URL}/applicable", params={"date": before_all}, headers=warehouse).status_code
        == 404
    )


def test_almacen_y_vendedor_no_cargan(client, make_user, auth_headers) -> None:
    for role in (Role.WAREHOUSE, Role.SELLER):
        headers = auth_headers(make_user(role, username=f"u_{role.value}"))
        response = client.post(
            URL, json={"business_date": today().isoformat(), "rate": "36"}, headers=headers
        )
        assert response.status_code == 403
