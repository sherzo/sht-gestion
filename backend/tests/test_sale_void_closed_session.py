"""Anulación de una venta cuya caja ya está cerrada: la devolución va a la caja abierta del
equipo desde el que anula el Admin y el cierre original no cambia (RF-27, PRD v0.11; RF-33/
FR-020 a FR-023; SC-006; research R8)."""

import uuid

import pytest
from sqlalchemy import select

from app.core import clock
from app.db.models import CashCount, Payment, StockMovement
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.conftest import device_headers
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

REASON = "Cliente devolvió la mercancía"


@pytest.fixture
def scenario(
    make_user,
    auth_headers,
    make_device,
    make_rate,
    open_cash_session,
    make_product,
    give_stock,
    make_sale,
):
    """Venta `A-000001` de 47,70 USD cobrada con 50,00 en Efectivo USD y 2,30 de vuelto,
    en una caja con fondo de 20,00 USD."""
    make_rate(business_date(clock.utcnow()), "36.50")
    seller = auth_headers(make_user(Role.SELLER))
    admin = auth_headers(make_user(Role.ADMIN))
    device, token = make_device("Mostrador principal")
    session = open_cash_session(seller, token, "0.00", "20.00")
    product = make_product("CON", sale_price="47.70")
    give_stock(product, "5")
    sale = make_sale(
        seller,
        token,
        session["id"],
        [(product, "1")],
        payments=[("cash_usd", "50.00", None)],
        change=[("cash_usd", "2.30", None)],
    )
    return {
        "seller": seller,
        "admin": admin,
        "device": device,
        "token": token,
        "session_id": session["id"],
        "sale": sale,
        "product": product,
    }


def void(client, scenario, headers):
    return client.post(
        f"/api/v1/sales/{scenario['sale']['id']}/void", json={"reason": REASON}, headers=headers
    )


def detail(client, headers, session_id: str) -> dict:
    response = client.get(f"/api/v1/cash-sessions/{session_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def cash_usd(data: dict) -> dict:
    return {row["method"]: row for row in data["reconciliation"]}["cash_usd"]


@pytest.mark.parametrize("with_device", ["none", "same", "other"])
def test_caja_abierta_recibe_su_propia_devolucion(
    client, scenario, make_device, db, with_device
) -> None:
    """RF-27/FR-020: con la caja de la venta abierta, la devolución va a esa caja, sin
    importar desde dónde anule el Admin."""
    headers = scenario["admin"]
    if with_device == "same":
        headers = device_headers(headers, scenario["token"])
    elif with_device == "other":
        headers = device_headers(headers, make_device("Tablet")[1])
    response = void(client, scenario, headers)
    assert response.status_code == 200, response.text
    refunds = db.scalars(
        select(Payment).where(Payment.kind.in_(("void_refund", "void_change")))
    ).all()
    assert {str(p.cash_session_id) for p in refunds} == {scenario["session_id"]}
    assert response.json()["void"]["refund_cash_session"]["id"] == scenario["session_id"]
    assert (
        cash_usd(detail(client, scenario["admin"], scenario["session_id"]))["expected"] == "20.00"
    )


@pytest.fixture
def closed_and_reopened(client, scenario, close_cash_session, open_cash_session) -> dict:
    """La caja de la venta cerrada sin diferencias y una caja nueva abierta en el equipo."""
    response = close_cash_session(scenario["seller"], scenario["token"], scenario["session_id"])
    assert response.status_code == 200, response.text
    new = open_cash_session(scenario["seller"], scenario["token"], "0.00", "10.00")
    return {**scenario, "closed": response.json(), "new_session_id": new["id"]}


def test_devolucion_en_la_caja_abierta_del_equipo(client, closed_and_reopened, db) -> None:
    """RF-27, PRD v0.11/FR-021, SC-006: devolución en la caja abierta; cierre intacto."""
    data = closed_and_reopened
    counts_before = {
        (c.payment_method_code, c.expected_amount, c.counted_amount, c.difference)
        for c in db.scalars(
            select(CashCount).where(CashCount.cash_session_id == uuid.UUID(data["session_id"]))
        )
    }
    response = void(client, data, device_headers(data["admin"], data["token"]))
    assert response.status_code == 200, response.text
    refund = response.json()["void"]["refund_cash_session"]
    assert refund["id"] == data["new_session_id"]
    assert refund["device"]["name"] == "Mostrador principal"

    refunds = db.scalars(
        select(Payment).where(Payment.kind.in_(("void_refund", "void_change")))
    ).all()
    assert {str(p.cash_session_id) for p in refunds} == {data["new_session_id"]}
    # El stock vuelve.
    reversal = db.scalar(select(StockMovement).where(StockMovement.type == "sale_void"))
    assert reversal.product_id == data["product"].id
    # El cierre original no cambia.
    db.expire_all()
    counts_after = {
        (c.payment_method_code, c.expected_amount, c.counted_amount, c.difference)
        for c in db.scalars(
            select(CashCount).where(CashCount.cash_session_id == uuid.UUID(data["session_id"]))
        )
    }
    assert counts_after == counts_before
    original = detail(client, data["admin"], data["session_id"])
    assert original["reconciliation"] == data["closed"]["reconciliation"]
    # La caja nueva resta 50,00 y suma 2,30: 10,00 − 50,00 + 2,30 = −37,70 (sin impedirlo).
    new_row = cash_usd(detail(client, data["admin"], data["new_session_id"]))
    assert (new_row["refunded"], new_row["change_recovered"], new_row["expected"]) == (
        "50.00",
        "2.30",
        "-37.70",
    )


def test_caja_original_lista_la_venta_anulada_despues_del_cierre(
    client, closed_and_reopened
) -> None:
    """FR-023: el detalle de la caja original muestra la anulación posterior al cierre."""
    data = closed_and_reopened
    assert void(client, data, device_headers(data["admin"], data["token"])).status_code == 200
    original = detail(client, data["admin"], data["session_id"])
    [voided] = original["voided_after_close"]
    assert voided["sale"]["number"] == data["sale"]["number"]
    assert voided["refund_cash_session"]["id"] == data["new_session_id"]
    new = detail(client, data["admin"], data["new_session_id"])
    assert {m["kind"] for m in new["movements"]} == {"void_refund", "void_change"}
    assert {m["sale"]["number"] for m in new["movements"]} == {data["sale"]["number"]}


def test_auditoria_de_la_devolucion_en_otra_caja(client, closed_and_reopened, db) -> None:
    """RF-46/FR-027: `sale.voided` dice qué caja y qué equipo recibieron la devolución."""
    data = closed_and_reopened
    assert void(client, data, device_headers(data["admin"], data["token"])).status_code == 200
    [entry] = audit_entries(db, "sale.voided")
    assert entry.after["refund_cash_session_id"] == data["new_session_id"]
    assert entry.after["refund_device_id"] == str(data["device"].id)


def test_sin_equipo_se_rechaza(client, closed_and_reopened, db) -> None:
    """FR-022: sin equipo registrado, 409 `cash_session_required` y la venta sigue igual."""
    response = void(client, closed_and_reopened, closed_and_reopened["admin"])
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "cash_session_required"
    assert db.scalar(select(Payment).where(Payment.kind == "void_refund")) is None


def test_equipo_sin_caja_abierta_se_rechaza(client, scenario, close_cash_session) -> None:
    response = close_cash_session(scenario["seller"], scenario["token"], scenario["session_id"])
    assert response.status_code == 200
    rejected = void(client, scenario, device_headers(scenario["admin"], scenario["token"]))
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "cash_session_required"


def test_equipo_revocado_se_rechaza(client, closed_and_reopened, make_user, auth_headers) -> None:
    data = closed_and_reopened
    admin_user_headers = data["admin"]
    revoke = client.post(f"/api/v1/devices/{data['device'].id}/revoke", headers=admin_user_headers)
    assert revoke.status_code == 200, revoke.text
    rejected = void(client, data, device_headers(admin_user_headers, data["token"]))
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "cash_session_required"
