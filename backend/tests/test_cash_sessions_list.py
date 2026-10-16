"""Consulta de cajas: el Admin todas con filtros; el Vendedor la caja abierta de su equipo y
sus cierres de hoy; el Almacén sin acceso (RF-31/FR-024 a FR-026; research R9)."""

import uuid
from datetime import timedelta

import pytest

from app.core import clock
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.conftest import device_headers

pytestmark = pytest.mark.db

URL = "/api/v1/cash-sessions"
NOTE = "Diferencia por revisar"


@pytest.fixture
def cash_sessions(
    make_user, auth_headers, make_device, make_rate, open_cash_session, close_cash_session
):
    """Equipo A: una caja de ayer cerrada con diferencia por Vendedor Uno y una de hoy
    cerrada sin diferencia por Vendedor Dos, más su caja abierta de hoy. Equipo B: una caja
    abierta desde ayer."""
    today = business_date(clock.utcnow())
    make_rate(today - timedelta(days=1), "36.40")
    make_rate(today, "36.50")
    one = make_user(Role.SELLER, full_name="Vendedor Uno")
    two = make_user(Role.SELLER, full_name="Vendedor Dos")
    admin = make_user(Role.ADMIN)
    headers = {"one": auth_headers(one), "two": auth_headers(two), "admin": auth_headers(admin)}
    device_a, token_a = make_device("Mostrador")
    device_b, token_b = make_device("Tablet")

    clock.advance(timedelta(days=-1))
    headers_yesterday = {"one": auth_headers(one)}
    yesterday = open_cash_session(headers_yesterday["one"], token_a, "0.00", "10.00")
    closed = close_cash_session(
        headers_yesterday["one"], token_a, yesterday["id"], counted={"cash_usd": "9.00"}, note=NOTE
    )
    assert closed.status_code == 200, closed.text
    stale = open_cash_session(headers_yesterday["one"], token_b)
    clock.reset()

    today_closed = open_cash_session(headers["two"], token_a)
    response = close_cash_session(headers["two"], token_a, today_closed["id"])
    assert response.status_code == 200, response.text
    today_open = open_cash_session(headers["one"], token_a)
    return {
        "headers": headers,
        "users": {"one": one, "two": two},
        "devices": {"a": device_a, "b": device_b},
        "tokens": {"a": token_a, "b": token_b},
        "ids": {
            "yesterday": yesterday["id"],
            "stale": stale["id"],
            "today_closed": today_closed["id"],
            "today_open": today_open["id"],
        },
        "today": today,
    }


def ids_of(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def test_admin_ve_todas_las_cajas(client, cash_sessions) -> None:
    """FR-024: más recientes primero, con diferencias y avisos."""
    data = cash_sessions
    response = client.get(URL, headers=data["headers"]["admin"])
    items = {item["id"]: item for item in response.json()["items"]}
    assert response.json()["total"] == 4
    order = ["today_open", "today_closed", "stale", "yesterday"]
    assert ids_of(response) == [data["ids"][name] for name in order]
    assert items[data["ids"]["yesterday"]]["has_differences"] is True
    assert items[data["ids"]["today_closed"]]["has_differences"] is False
    assert items[data["ids"]["stale"]]["opened_on_previous_day"] is True
    assert items[data["ids"]["today_open"]]["opened_on_previous_day"] is False
    assert items[data["ids"]["yesterday"]]["closed_outside_device"] is False
    assert items[data["ids"]["yesterday"]]["device"]["name"] == "Mostrador"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("status=open", {"stale", "today_open"}),
        ("status=closed", {"yesterday", "today_closed"}),
        ("with_differences=true", {"yesterday"}),
        ("with_differences=false", {"stale", "today_closed", "today_open"}),
        ("from={today}&to={today}", {"today_closed", "today_open"}),
        ("to={yesterday}", {"yesterday", "stale"}),
        ("device_id={device_b}", {"stale"}),
        ("opened_by={two}", {"today_closed"}),
        ("closed_by={one}", {"yesterday"}),
    ],
)
def test_filtros_del_admin(client, cash_sessions, query, expected) -> None:
    data = cash_sessions
    filled = query.format(
        today=data["today"].isoformat(),
        yesterday=(data["today"] - timedelta(days=1)).isoformat(),
        device_b=data["devices"]["b"].id,
        two=data["users"]["two"].id,
        one=data["users"]["one"].id,
    )
    response = client.get(f"{URL}?{filled}", headers=data["headers"]["admin"])
    assert set(ids_of(response)) == {data["ids"][name] for name in expected}


def test_paginacion(client, cash_sessions) -> None:
    response = client.get(f"{URL}?page=2&page_size=3", headers=cash_sessions["headers"]["admin"])
    assert len(ids_of(response)) == 1
    assert response.json()["total"] == 4


def test_vendedor_ve_la_caja_abierta_de_su_equipo_y_sus_cierres_de_hoy(
    client, cash_sessions
) -> None:
    """FR-025: Vendedor Dos en el equipo A ve la caja abierta de A y su cierre de hoy; el
    de ayer de Vendedor Uno no aparece y los filtros se ignoran."""
    data = cash_sessions
    headers = device_headers(data["headers"]["two"], data["tokens"]["a"])
    assert set(ids_of(client.get(f"{URL}?status=closed&from=2000-01-01", headers=headers))) == {
        data["ids"]["today_open"],
        data["ids"]["today_closed"],
    }
    # Vendedor Uno cerró ayer: hoy solo ve la caja abierta de su equipo.
    one = device_headers(data["headers"]["one"], data["tokens"]["a"])
    assert set(ids_of(client.get(URL, headers=one))) == {data["ids"]["today_open"]}
    # Sin cabecera de equipo, solo sus cierres de hoy.
    assert set(ids_of(client.get(URL, headers=data["headers"]["two"]))) == {
        data["ids"]["today_closed"]
    }


def test_vendedor_no_ve_el_detalle_de_otra_caja(client, cash_sessions) -> None:
    data = cash_sessions
    headers = device_headers(data["headers"]["two"], data["tokens"]["a"])
    for name in ("yesterday", "stale"):
        response = client.get(f"{URL}/{data['ids'][name]}", headers=headers)
        assert response.status_code == 404
    assert client.get(f"{URL}/{data['ids']['today_closed']}", headers=headers).status_code == 200
    assert client.get(f"{URL}/{uuid.uuid7()}", headers=data["headers"]["admin"]).status_code == 404


def test_almacen_sin_acceso(client, cash_sessions, make_user, auth_headers) -> None:
    """FR-026."""
    warehouse = auth_headers(make_user(Role.WAREHOUSE))
    assert client.get(URL, headers=warehouse).status_code == 403
    response = client.get(f"{URL}/{cash_sessions['ids']['today_open']}", headers=warehouse)
    assert response.status_code == 403


def test_equipo_actual_avisa_la_caja_de_otro_dia(client, cash_sessions) -> None:
    """Research R5: `GET /devices/current` trae el fondo y si la caja es de otro día."""
    data = cash_sessions
    stale = client.get(
        "/api/v1/devices/current",
        headers=device_headers(data["headers"]["one"], data["tokens"]["b"]),
    ).json()["open_cash_session"]
    assert stale["opened_on_previous_day"] is True
    current = client.get(
        "/api/v1/devices/current",
        headers=device_headers(data["headers"]["one"], data["tokens"]["a"]),
    ).json()["open_cash_session"]
    assert current["opened_on_previous_day"] is False
    assert (current["opening_float_ves"], current["opening_float_usd"]) == ("0.00", "0.00")
