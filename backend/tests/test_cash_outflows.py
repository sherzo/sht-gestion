"""Egresos de caja por la cola y su anulación por el Admin (RF-24, RF-32, RF-33, RF-46/FR-001
a FR-004; SC-004; PRD v0.12; research R3)."""

import uuid

import pytest
from sqlalchemy import func, select

from app.core import clock
from app.db.models import CashOutflow
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.conftest import device_headers
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

REASON = "Compra de botellones de agua"


@pytest.fixture
def counter(make_user, auth_headers, make_device, make_rate, open_cash_session):
    make_rate(business_date(clock.utcnow()), "36.50")
    seller = make_user(Role.SELLER, full_name="Vendedor Uno")
    admin = make_user(Role.ADMIN, full_name="Dueño")
    headers = auth_headers(seller)
    admin_headers = auth_headers(admin)
    device, token = make_device()
    session = open_cash_session(headers, token, "500.00", "20.00")
    return {
        "seller": seller,
        "admin": admin,
        "headers": headers,
        "admin_headers": admin_headers,
        "device": device,
        "token": token,
        "session_id": session["id"],
    }


def expected(client, counter) -> dict[str, str]:
    detail = client.get(
        f"/api/v1/cash-sessions/{counter['session_id']}",
        headers=device_headers(counter["headers"], counter["token"]),
    ).json()
    return {row["method"]: row["expected"] for row in detail["reconciliation"]}


def test_egreso_en_efectivo_resta_del_esperado(client, counter, register_outflow, db) -> None:
    """RF-32/FR-001: queda con quién, cuándo, método, monto y motivo, y resta del esperado."""
    response = register_outflow(counter["headers"], counter["token"], counter["session_id"])
    assert response.status_code == 200, response.text
    data = response.json()
    assert (data["method"], data["currency"], data["amount"], data["reason"]) == (
        "cash_usd",
        "USD",
        "5.00",
        REASON,
    )
    assert data["created_by"]["id"] == str(counter["seller"].id)
    assert data["reference"] is None
    assert data["void"] is None
    assert expected(client, counter)["cash_usd"] == "15.00"
    [entry] = audit_entries(db, "cash_outflow.created")
    assert entry.user_id == counter["seller"].id
    assert entry.device_id == counter["device"].id
    assert entry.after["amount"] == "5.00"
    assert entry.after["reason"] == REASON


def test_egreso_en_bolivares_y_del_admin(client, counter, register_outflow) -> None:
    response = register_outflow(
        counter["admin_headers"], counter["token"], counter["session_id"], "cash_ves", "120.50"
    )
    assert response.status_code == 200, response.text
    assert response.json()["created_by"]["id"] == str(counter["admin"].id)
    assert expected(client, counter)["cash_ves"] == "379.50"


@pytest.mark.parametrize(
    ("method", "currency", "amount"),
    [("mobile_payment", "VES", "300.00"), ("binance_usdt", "USDT", "12.00")],
)
def test_egreso_electronico_con_referencia_y_sin_tope(
    client, counter, register_outflow, method, currency, amount
) -> None:
    """PRD v0.12: cualquier método; los electrónicos exigen referencia y no tienen tope
    (la cuenta puede tener dinero de otros días): el esperado queda negativo."""
    response = register_outflow(
        counter["headers"],
        counter["token"],
        counter["session_id"],
        method,
        amount,
        "Pago de un delivery",
        reference="004512",
    )
    assert response.status_code == 200, response.text
    assert response.json()["currency"] == currency
    assert response.json()["reference"] == "004512"
    assert expected(client, counter)[method] == f"-{amount}"


def test_zelle_sin_cobros_se_acepta(client, counter, register_outflow) -> None:
    response = register_outflow(
        counter["headers"],
        counter["token"],
        counter["session_id"],
        "zelle",
        "40.00",
        reference="ZL-99",
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize(
    ("method", "amount", "reason", "reference", "field"),
    [
        ("paypal", "5.00", REASON, None, "payload.method"),
        ("mobile_payment", "5.00", REASON, None, "payload.reference"),
        ("mobile_payment", "5.00", REASON, "x" * 61, "payload.reference"),
        ("cash_usd", "0.00", REASON, None, "payload.amount"),
        ("cash_usd", "-1.00", REASON, None, "payload.amount"),
        ("cash_usd", "1.005", REASON, None, "payload.amount"),
        ("cash_usd", "1.00", "Agua", None, "payload.reason"),
        ("cash_usd", "1.00", "x" * 201, None, "payload.reason"),
    ],
)
def test_egreso_invalido(
    counter, register_outflow, db, method, amount, reason, reference, field
) -> None:
    """FR-001: método del catálogo, referencia si la exige, monto > 0 y motivo de 5 a 200."""
    response = register_outflow(
        counter["headers"],
        counter["token"],
        counter["session_id"],
        method,
        amount,
        reason,
        reference=reference,
    )
    assert response.status_code == 422, response.text
    assert field in response.json()["detail"]["fields"]
    assert db.scalar(select(func.count()).select_from(CashOutflow)) == 0


def test_egreso_en_efectivo_no_supera_el_disponible(client, counter, register_outflow) -> None:
    """FR-002: solo en efectivo, el egreso no supera el esperado; trae el disponible."""
    response = register_outflow(
        counter["headers"], counter["token"], counter["session_id"], "cash_usd", "20.01"
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "insufficient_cash"
    assert (detail["available"], detail["currency"]) == ("20.00", "USD")
    exact = register_outflow(
        counter["headers"], counter["token"], counter["session_id"], "cash_usd", "20.00"
    )
    assert exact.status_code == 200, exact.text


def test_caja_de_otro_equipo_o_cerrada(
    counter, register_outflow, make_device, close_cash_session
) -> None:
    """FR-001: solo en la caja abierta del equipo que lo envía."""
    _, other_token = make_device("Tablet")
    other = register_outflow(counter["headers"], other_token, counter["session_id"])
    assert other.status_code == 409
    assert other.json()["detail"]["code"] == "cash_session_unavailable"
    unknown = register_outflow(counter["headers"], counter["token"], str(uuid.uuid7()))
    assert unknown.json()["detail"]["code"] == "cash_session_unavailable"
    assert (
        close_cash_session(counter["headers"], counter["token"], counter["session_id"]).status_code
        == 200
    )
    closed = register_outflow(counter["headers"], counter["token"], counter["session_id"])
    assert closed.status_code == 409
    assert closed.json()["detail"]["code"] == "cash_session_closed"


def test_almacen_no_registra_egresos(counter, register_outflow, make_user, auth_headers) -> None:
    """FR-026."""
    warehouse = auth_headers(make_user(Role.WAREHOUSE))
    response = register_outflow(warehouse, counter["token"], counter["session_id"])
    assert response.status_code == 403


def test_reenviar_el_egreso_no_lo_duplica(counter, register_outflow, db) -> None:
    """ADR-0003/FR-004, SC-004: 10 reenvíos dejan un egreso."""
    op_id, outflow_id = str(uuid.uuid7()), str(uuid.uuid7())
    responses = [
        register_outflow(
            counter["headers"],
            counter["token"],
            counter["session_id"],
            outflow_id=outflow_id,
            op_id=op_id,
        )
        for _ in range(10)
    ]
    assert {response.status_code for response in responses} == {200}
    assert db.scalar(select(func.count()).select_from(CashOutflow)) == 1
    assert len(audit_entries(db, "cash_outflow.created")) == 1


# --- Anulación (RF-33/FR-003) ----------------------------------------------------------


def void(client, outflow_id: str, headers, reason: str = "Registrado por error"):
    return client.post(
        f"/api/v1/cash-outflows/{outflow_id}/void", json={"reason": reason}, headers=headers
    )


@pytest.fixture
def outflow(counter, register_outflow) -> str:
    response = register_outflow(counter["headers"], counter["token"], counter["session_id"])
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_admin_anula_el_egreso(client, counter, outflow, db) -> None:
    """RF-33/FR-003: no se borra; queda anulado y deja de restar del esperado."""
    response = void(client, outflow, counter["admin_headers"])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["void"]["reason"] == "Registrado por error"
    assert data["void"]["voided_by"]["id"] == str(counter["admin"].id)
    assert expected(client, counter)["cash_usd"] == "20.00"
    detail = client.get(
        f"/api/v1/cash-sessions/{counter['session_id']}", headers=counter["admin_headers"]
    ).json()
    [listed] = detail["outflows"]
    assert listed["void"] is not None
    [entry] = audit_entries(db, "cash_outflow.voided")
    assert entry.user_id == counter["admin"].id
    assert entry.reason == "Registrado por error"


def test_anulacion_rechazada(client, counter, outflow, close_cash_session) -> None:
    """FR-003: una sola vez, con motivo, por el Admin y con la caja abierta."""
    assert void(client, outflow, counter["headers"]).status_code == 403
    assert void(client, outflow, counter["admin_headers"], "Mal").status_code == 422
    assert void(client, str(uuid.uuid7()), counter["admin_headers"]).status_code == 404
    assert void(client, outflow, counter["admin_headers"]).status_code == 200
    again = void(client, outflow, counter["admin_headers"])
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "invalid_state"


def test_no_se_anula_con_la_caja_cerrada(client, counter, outflow, close_cash_session) -> None:
    assert (
        close_cash_session(counter["headers"], counter["token"], counter["session_id"]).status_code
        == 200
    )
    response = void(client, outflow, counter["admin_headers"])
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "cash_session_closed"


def test_cierre_con_egresos_cuadra(client, counter, register_outflow, close_cash_session) -> None:
    """RF-31, RF-32: el cierre descuenta los egresos vigentes de cada método."""
    register_outflow(counter["headers"], counter["token"], counter["session_id"])
    register_outflow(
        counter["headers"], counter["token"], counter["session_id"], "cash_ves", "100.00"
    )
    response = close_cash_session(counter["headers"], counter["token"], counter["session_id"])
    assert response.status_code == 200, response.text
    rows = {row["method"]: row for row in response.json()["reconciliation"]}
    assert (rows["cash_usd"]["outflows"], rows["cash_usd"]["expected"]) == ("5.00", "15.00")
    assert (rows["cash_ves"]["outflows"], rows["cash_ves"]["expected"]) == ("100.00", "400.00")
