"""Cierre de caja por la cola desde el equipo de la caja (RF-30, RF-31, RF-33, RN-16/FR-005 a
FR-017; SC-004, SC-008; research R4)."""

import uuid

import pytest
from sqlalchemy import func, select

from app.core import clock
from app.db.models import Alert, CashCount, CashSession
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.conftest import device_headers, operation
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

URL = "/api/v1/sync/operations"
NOTE = "Faltó 1 USD; se revisa mañana"
METHODS = ("cash_ves", "mobile_payment", "pos_card", "cash_usd", "zelle", "binance_usdt")


@pytest.fixture
def counter(
    make_user, auth_headers, make_device, make_rate, open_cash_session, make_product, make_sale
):
    """Escenario 1 de la US1: fondo de 500,00 Bs y 20,00 USD; una venta de 47,70 USD
    cobrada con 50,00 en Efectivo USD y 2,30 de vuelto, y otra de 20,00 USD cobrada con
    730,00 Bs por Pago móvil."""
    make_rate(business_date(clock.utcnow()), "36.50")
    seller = make_user(Role.SELLER, full_name="Vendedor Uno")
    headers = auth_headers(seller)
    device, token = make_device("Mostrador principal")
    session = open_cash_session(headers, token, "500.00", "20.00")
    big = make_product("CON", sale_price="47.70")
    small = make_product("CON", sale_price="20.00")
    make_sale(
        headers,
        token,
        session["id"],
        [(big, "1")],
        payments=[("cash_usd", "50.00", None)],
        change=[("cash_usd", "2.30", None)],
    )
    make_sale(
        headers,
        token,
        session["id"],
        [(small, "1")],
        payments=[("mobile_payment", "730.00", "004512")],
    )
    return {
        "seller": seller,
        "headers": headers,
        "device": device,
        "token": token,
        "session_id": session["id"],
    }


def cash_alerts(db) -> list[Alert]:
    return list(db.scalars(select(Alert).where(Alert.entity_type == "cash_session")))


def expected_by_method(rows: list[dict]) -> dict[str, str]:
    return {row["method"]: row["expected"] for row in rows}


def test_esperado_del_escenario_1(client, counter) -> None:
    """RF-31/FR-006: el esperado por método coincide con el cálculo a mano."""
    response = client.get(
        f"/api/v1/cash-sessions/{counter['session_id']}",
        headers=device_headers(counter["headers"], counter["token"]),
    )
    assert response.status_code == 200, response.text
    assert expected_by_method(response.json()["reconciliation"]) == {
        "cash_ves": "500.00",
        "mobile_payment": "730.00",
        "pos_card": "0.00",
        "cash_usd": "67.70",
        "zelle": "0.00",
        "binance_usdt": "0.00",
    }


def test_cierre_guarda_conteos_y_cierra_la_caja(client, counter, close_cash_session, db) -> None:
    """RF-31/FR-011: quién, cuándo, desde qué equipo y un conteo por método."""
    op_id = str(uuid.uuid7())
    response = close_cash_session(
        counter["headers"],
        counter["token"],
        counter["session_id"],
        counted={"cash_usd": "66.70"},
        note=NOTE,
        op_id=op_id,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "closed"
    assert data["closed_by"]["full_name"] == "Vendedor Uno"
    assert data["closed_outside_device"] is False
    assert data["closing_note"] == NOTE
    assert data["alerts_created"] == ["cash_difference"]
    row = {item["method"]: item for item in data["reconciliation"]}["cash_usd"]
    assert (row["expected"], row["device_expected"], row["counted"], row["difference"]) == (
        "67.70",
        "67.70",
        "66.70",
        "-1.00",
    )
    session = db.get(CashSession, uuid.UUID(counter["session_id"]))
    assert session.status == "closed"
    assert session.closed_from_device_id == counter["device"].id
    assert session.closing_operation_id == uuid.UUID(op_id)
    assert session.closed_recorded_at is not None
    assert session.closed_at.isoformat() == data["closed_at"].replace("Z", "+00:00")
    counts = db.scalars(select(CashCount).where(CashCount.cash_session_id == session.id)).all()
    assert len(counts) == 6
    [entry] = audit_entries(db, "cash_session.closed")
    assert entry.user_id == counter["seller"].id
    assert entry.device_id == counter["device"].id
    assert entry.after["note"] == NOTE
    assert entry.after["outside_device"] is False


def test_diferencia_exige_observacion(client, counter, close_cash_session) -> None:
    """RF-31/FR-010: con diferencia, la observación es obligatoria y de 5 a 500 caracteres."""
    args = (counter["headers"], counter["token"], counter["session_id"])
    missing = close_cash_session(*args, counted={"cash_usd": "66.70"})
    assert missing.status_code == 422
    assert "payload.note" in missing.json()["detail"]["fields"]
    short = close_cash_session(*args, counted={"cash_usd": "66.70"}, note="Falt")
    assert short.status_code == 422
    long = close_cash_session(*args, counted={"cash_usd": "66.70"}, note="x" * 501)
    assert long.status_code == 422


def test_sin_diferencias_no_pide_observacion_ni_crea_alerta(
    client, counter, close_cash_session, db
) -> None:
    """FR-010, FR-016: sin diferencias, la observación es opcional y no hay alerta."""
    response = close_cash_session(counter["headers"], counter["token"], counter["session_id"])
    assert response.status_code == 200, response.text
    assert response.json()["alerts_created"] == []
    assert cash_alerts(db) == []


def test_alerta_de_diferencia(client, counter, close_cash_session, db) -> None:
    """FR-016, SC-008: la alerta lleva la caja, el equipo, quién cerró y la diferencia."""
    close_cash_session(
        counter["headers"],
        counter["token"],
        counter["session_id"],
        counted={"cash_usd": "66.70"},
        note=NOTE,
    )
    [alert] = cash_alerts(db)
    assert alert.type == "cash_difference"
    assert alert.entity_type == "cash_session"
    assert str(alert.entity_id) == counter["session_id"]
    assert alert.details["device_name"] == "Mostrador principal"
    assert alert.details["closed_by"] == "Vendedor Uno"
    [difference] = alert.details["differences"]
    assert difference["method"] == "cash_usd"
    assert difference["difference"] == "-1.00"


def test_esperado_distinto_entre_equipo_y_servidor(client, counter, close_cash_session, db) -> None:
    """FR-010, FR-012: el usuario vio 70,00 y contó 70,00 (sin diferencia para él): se
    cierra sin observación, con el esperado del servidor y la alerta `expected_mismatch`."""
    response = close_cash_session(
        counter["headers"],
        counter["token"],
        counter["session_id"],
        device_expected={"cash_usd": "70.00"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert sorted(data["alerts_created"]) == ["cash_difference", "expected_mismatch"]
    row = {item["method"]: item for item in data["reconciliation"]}["cash_usd"]
    assert (row["expected"], row["device_expected"], row["counted"], row["difference"]) == (
        "67.70",
        "70.00",
        "70.00",
        "2.30",
    )
    mismatch = db.scalar(select(Alert).where(Alert.type == "expected_mismatch"))
    [method] = mismatch.details["methods"]
    assert (method["method"], method["device_expected"], method["expected"]) == (
        "cash_usd",
        "70.00",
        "67.70",
    )


@pytest.mark.parametrize(
    ("counts", "field"),
    [
        ("missing", "payload.counts"),
        ("repeated", "payload.counts.5.method"),
        ("negative", "payload.counts.3.counted"),
        ("three_decimals", "payload.counts.3.counted"),
    ],
)
def test_conteos_invalidos(client, counter, counts, field) -> None:
    """FR-008: los seis métodos, sin repetir, contado ≥ 0 con como máximo 2 decimales."""
    detail = client.get(
        f"/api/v1/cash-sessions/{counter['session_id']}",
        headers=device_headers(counter["headers"], counter["token"]),
    ).json()
    rows = [
        {"method": r["method"], "device_expected": r["expected"], "counted": r["expected"]}
        for r in detail["reconciliation"]
    ]
    if counts == "missing":
        rows = rows[:5]
    elif counts == "repeated":
        rows[5] = {**rows[0]}
    elif counts == "negative":
        rows[3]["counted"] = "-1.00"
    else:
        rows[3]["counted"] = "66.705"
    response = client.post(
        URL,
        json=operation(
            "cash_session.close",
            {"cash_session_id": counter["session_id"], "counts": rows, "note": NOTE},
        ),
        headers=device_headers(counter["headers"], counter["token"]),
    )
    assert response.status_code == 422, response.text
    assert field in response.json()["detail"]["fields"]


def test_contado_con_un_decimal_se_acepta(client, counter, close_cash_session) -> None:
    response = close_cash_session(
        counter["headers"],
        counter["token"],
        counter["session_id"],
        counted={"cash_usd": "66.7"},
        note=NOTE,
    )
    assert response.status_code == 200, response.text


def test_segundo_cierre_rechazado(client, counter, close_cash_session) -> None:
    """RF-33/FR-015: una caja cerrada no admite un segundo cierre."""
    args = (counter["headers"], counter["token"], counter["session_id"])
    assert close_cash_session(*args).status_code == 200
    # Otra operación de cierre (otro id) sobre la misma caja.
    response = client.post(
        URL,
        json=operation(
            "cash_session.close",
            {
                "cash_session_id": counter["session_id"],
                "counts": [
                    {"method": method, "device_expected": "0.00", "counted": "0.00"}
                    for method in METHODS
                ],
                "note": NOTE,
            },
        ),
        headers=device_headers(counter["headers"], counter["token"]),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "cash_session_closed"


def test_caja_de_otro_equipo(client, counter, make_device, close_cash_session) -> None:
    """FR-005: por la cola solo se cierra la caja del equipo que envía."""
    _, other_token = make_device("Tablet")
    detail = client.get(
        f"/api/v1/cash-sessions/{counter['session_id']}",
        headers=device_headers(counter["headers"], counter["token"]),
    ).json()
    response = client.post(
        URL,
        json=operation(
            "cash_session.close",
            {
                "cash_session_id": counter["session_id"],
                "counts": [
                    {
                        "method": r["method"],
                        "device_expected": r["expected"],
                        "counted": r["expected"],
                    }
                    for r in detail["reconciliation"]
                ],
            },
        ),
        headers=device_headers(counter["headers"], other_token),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "cash_session_unavailable"


def test_reenviar_el_cierre_no_lo_duplica(client, counter, close_cash_session, db) -> None:
    """ADR-0003/FR-013, SC-004: 10 reenvíos dejan un cierre, seis conteos y una alerta."""
    op_id = str(uuid.uuid7())
    responses = [
        close_cash_session(
            counter["headers"],
            counter["token"],
            counter["session_id"],
            counted={"cash_usd": "66.70"},
            note=NOTE,
            op_id=op_id,
        )
        for _ in range(10)
    ]
    assert {response.status_code for response in responses} == {200}
    assert len({response.json()["closed_at"] for response in responses}) == 1
    session_id = uuid.UUID(counter["session_id"])
    count = select(func.count()).select_from(CashCount)
    assert db.scalar(count.where(CashCount.cash_session_id == session_id)) == 6
    assert len(cash_alerts(db)) == 1
    assert len(audit_entries(db, "cash_session.closed")) == 1


def test_despues_del_cierre_se_abre_otra_caja_y_no_se_vende_en_la_cerrada(
    client, counter, close_cash_session, open_cash_session, make_product, make_sale
) -> None:
    """RF-30/FR-017: el equipo queda sin caja abierta; una venta creada después del cierre
    en la caja cerrada se rechaza."""
    assert (
        close_cash_session(counter["headers"], counter["token"], counter["session_id"]).status_code
        == 200
    )
    current = client.get(
        "/api/v1/devices/current", headers=device_headers(counter["headers"], counter["token"])
    ).json()
    assert current["open_cash_session"] is None
    rejected = make_sale(
        counter["headers"],
        counter["token"],
        counter["session_id"],
        [(make_product("CON", sale_price="5.00"), "1")],
        expect=409,
    )
    assert rejected["detail"]["code"] == "cash_session_closed"
    new_session = open_cash_session(counter["headers"], counter["token"])
    assert new_session["status"] == "open"


def test_otro_vendedor_cierra_la_caja(
    client, counter, make_user, auth_headers, close_cash_session
) -> None:
    """RN-16: quien abre y quien cierra pueden ser distintos; el cierre guarda a los dos."""
    other = make_user(Role.SELLER, full_name="Vendedor Dos")
    response = close_cash_session(auth_headers(other), counter["token"], counter["session_id"])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["opened_by"]["full_name"] == "Vendedor Uno"
    assert data["closed_by"]["full_name"] == "Vendedor Dos"


def test_almacen_no_cierra(client, counter, make_user, auth_headers) -> None:
    """FR-026: el Almacén no usa la cola de salida."""
    warehouse = auth_headers(make_user(Role.WAREHOUSE))
    response = client.post(
        URL,
        json=operation("cash_session.close", {"cash_session_id": counter["session_id"]}),
        headers=device_headers(warehouse, counter["token"]),
    )
    assert response.status_code == 403
