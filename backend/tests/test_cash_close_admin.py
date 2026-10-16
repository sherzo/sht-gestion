"""Cierre de una caja por el Admin desde otro equipo (caja huérfana) y operaciones que llegan
después de ese cierre (RF-31, RF-33/FR-018, FR-019; SC-008; research R6, R7)."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import clock
from app.db.models import Alert, CashCount, CashSession
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.conftest import device_headers
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

URL = "/api/v1/sync/operations"
NOTE = "El equipo de la tablet se dañó"
METHODS = ("cash_ves", "mobile_payment", "pos_card", "cash_usd", "zelle", "binance_usdt")


@pytest.fixture
def orphan(
    client, make_user, auth_headers, make_device, make_rate, open_cash_session, make_product
):
    """Caja abierta en la tablet con 20,00 USD de fondo y una venta de 12,00 en efectivo."""
    today = business_date(clock.utcnow())
    make_rate(today, "36.50")
    seller_user = make_user(Role.SELLER, full_name="Vendedor Uno")
    seller = auth_headers(seller_user)
    admin_user = make_user(Role.ADMIN, full_name="Dueño")
    admin = auth_headers(admin_user)
    tablet, token = make_device("Tablet")
    session = open_cash_session(seller, token, "0.00", "20.00")
    product = make_product("CON", sale_price="12.00")
    context = {
        "seller_user": seller_user,
        "seller": seller,
        "admin_user": admin_user,
        "admin": admin,
        "tablet": tablet,
        "token": token,
        "session_id": session["id"],
        "product": product,
        "today": today,
        "sequence": iter(range(1, 100)),
    }
    response = send_sale(client, context)
    assert response.status_code == 200, response.text
    return context


def sale_operation(context: dict, created_at) -> dict:
    """Venta de 12,00 USD en Efectivo USD creada en el equipo a la hora `created_at`."""
    return {
        "id": str(uuid.uuid7()),
        "operation_type": "sale.create",
        "schema_version": 1,
        "created_at": created_at.isoformat(),
        "payload": {
            "id": str(uuid.uuid7()),
            "sequence_number": next(context["sequence"]),
            "cash_session_id": context["session_id"],
            "seller_id": str(context["seller_user"].id),
            "occurred_at": created_at.isoformat(),
            "exchange_rate": "36.50000000",
            "exchange_rate_date": context["today"].isoformat(),
            "items": [
                {
                    "id": str(uuid.uuid7()),
                    "product_id": str(context["product"].id),
                    "quantity": "1",
                    "entered_unit": "unit",
                    "unit_price_usd": "12.00",
                }
            ],
            "payments": [{"method": "cash_usd", "amount": "12.00"}],
            "change": [],
            "device_total_usd": "12.00",
        },
    }


def send_sale(client, context: dict, created_at=None):
    body = sale_operation(context, created_at or clock.utcnow())
    return client.post(URL, json=body, headers=device_headers(context["seller"], context["token"]))


def outflow_operation(context: dict, created_at, amount: str = "5.00") -> dict:
    return {
        "id": str(uuid.uuid7()),
        "operation_type": "cash_outflow.create",
        "schema_version": 1,
        "created_at": created_at.isoformat(),
        "payload": {
            "id": str(uuid.uuid7()),
            "cash_session_id": context["session_id"],
            "method": "cash_usd",
            "amount": amount,
            "reason": "Pago del delivery",
        },
    }


def admin_close(client, context: dict, headers=None, counted=None, note=NOTE):
    counts = [
        {"method": method, "counted": (counted or {}).get(method, "0.00")} for method in METHODS
    ]
    body = {"counts": counts}
    if note is not None:
        body["note"] = note
    return client.post(
        f"/api/v1/cash-sessions/{context['session_id']}/close",
        json=body,
        headers=headers or context["admin"],
    )


def test_admin_cierra_la_caja_de_otro_equipo(client, orphan, db) -> None:
    """FR-018: queda cerrada como cualquier cierre, marcada como hecha fuera del equipo."""
    response = admin_close(client, orphan, counted={"cash_usd": "32.00"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "closed"
    assert data["closed_outside_device"] is True
    assert data["closed_from_device"] is None
    assert data["closed_by"]["full_name"] == "Dueño"
    assert data["alerts_created"] == []
    row = {item["method"]: item for item in data["reconciliation"]}["cash_usd"]
    assert (row["expected"], row["device_expected"], row["counted"]) == ("32.00", None, "32.00")
    session = db.get(CashSession, uuid.UUID(orphan["session_id"]))
    assert session.closing_operation_id is None
    assert session.closed_at == session.closed_recorded_at
    [entry] = audit_entries(db, "cash_session.closed")
    assert entry.after["outside_device"] is True
    assert entry.after["closed_from_device_id"] is None


def test_admin_cierra_la_caja_de_un_equipo_revocado_desde_su_equipo(
    client, orphan, make_device
) -> None:
    revoke = client.post(f"/api/v1/devices/{orphan['tablet'].id}/revoke", headers=orphan["admin"])
    assert revoke.status_code == 200, revoke.text
    office, office_token = make_device("Oficina")
    response = admin_close(
        client, orphan, headers=device_headers(orphan["admin"], office_token), counted={}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["closed_from_device"] == {"id": str(office.id), "name": "Oficina"}
    assert data["alerts_created"] == ["cash_difference"]


def test_observacion_y_conteos_obligatorios(client, orphan) -> None:
    """FR-018: la observación siempre es obligatoria fuera del equipo."""
    assert admin_close(client, orphan, note=None).status_code == 422
    assert admin_close(client, orphan, note="Rota").status_code == 422
    incomplete = client.post(
        f"/api/v1/cash-sessions/{orphan['session_id']}/close",
        json={"counts": [{"method": "cash_usd", "counted": "32.00"}], "note": NOTE},
        headers=orphan["admin"],
    )
    assert incomplete.status_code == 422
    assert "counts" in incomplete.json()["detail"]["fields"]


def test_segundo_cierre_y_caja_inexistente(client, orphan, db) -> None:
    assert admin_close(client, orphan, counted={"cash_usd": "32.00"}).status_code == 200
    again = admin_close(client, orphan, counted={"cash_usd": "32.00"})
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "cash_session_closed"
    count = db.scalars(
        select(CashCount).where(CashCount.cash_session_id == uuid.UUID(orphan["session_id"]))
    ).all()
    assert len(count) == 6
    missing = client.post(
        f"/api/v1/cash-sessions/{uuid.uuid7()}/close",
        json={"counts": [], "note": NOTE},
        headers=orphan["admin"],
    )
    assert missing.status_code == 404


@pytest.mark.parametrize("role", [Role.SELLER, Role.WAREHOUSE])
def test_solo_el_admin_cierra_cajas_de_otro_equipo(
    client, orphan, make_user, auth_headers, role
) -> None:
    """FR-018: el Vendedor no cierra cajas de otro equipo (403)."""
    response = admin_close(client, orphan, headers=auth_headers(make_user(role)))
    assert response.status_code == 403


@pytest.fixture
def closed_by_admin(client, orphan) -> dict:
    before = clock.utcnow() - timedelta(minutes=5)
    response = admin_close(client, orphan, counted={"cash_usd": "32.00"})
    assert response.status_code == 200, response.text
    return {**orphan, "before": before, "closed": response.json()}


def test_venta_creada_antes_del_cierre_se_registra_con_alerta(client, closed_by_admin, db) -> None:
    """FR-019, SC-008: se registra en su caja, el cierre no cambia y alerta al Admin."""
    data = closed_by_admin
    response = send_sale(client, data, created_at=data["before"])
    assert response.status_code == 200, response.text
    assert "post_close_operation" in response.json()["alerts_created"]
    alert = db.scalar(select(Alert).where(Alert.type == "post_close_operation"))
    assert alert.entity_type == "cash_session"
    assert alert.details["operation"] == "sale"
    assert alert.details["sale_number"] == response.json()["number"]
    assert (alert.details["amount"], alert.details["currency"]) == ("12.00", "USD")

    detail = client.get(f"/api/v1/cash-sessions/{data['session_id']}", headers=data["admin"])
    detail = detail.json()
    assert detail["reconciliation"] == data["closed"]["reconciliation"]
    [late] = detail["post_close_operations"]
    assert (late["type"], late["number"]) == ("sale", response.json()["number"])
    assert sorted(m["after_close"] for m in detail["movements"]) == [False, True]


def test_egreso_creado_antes_del_cierre_se_registra_sin_tope(client, closed_by_admin, db) -> None:
    """FR-019: el dinero ya salió; no se valida contra el disponible."""
    data = closed_by_admin
    body = outflow_operation(data, data["before"], amount="500.00")
    response = client.post(URL, json=body, headers=device_headers(data["seller"], data["token"]))
    assert response.status_code == 200, response.text
    alert = db.scalar(select(Alert).where(Alert.type == "post_close_operation"))
    assert alert.details["operation"] == "cash_outflow"
    assert (alert.details["amount"], alert.details["currency"]) == ("500.00", "USD")
    detail = client.get(f"/api/v1/cash-sessions/{data['session_id']}", headers=data["admin"])
    [late] = detail.json()["post_close_operations"]
    assert (late["type"], late["method"], late["amount"]) == ("cash_outflow", "cash_usd", "500.00")
    assert detail.json()["reconciliation"] == data["closed"]["reconciliation"]


def test_operaciones_creadas_despues_del_cierre_se_rechazan(client, closed_by_admin) -> None:
    data = closed_by_admin
    sale = send_sale(client, data)
    assert sale.status_code == 409
    assert sale.json()["detail"]["code"] == "cash_session_closed"
    body = outflow_operation(data, clock.utcnow())
    outflow = client.post(URL, json=body, headers=device_headers(data["seller"], data["token"]))
    assert outflow.status_code == 409
    assert outflow.json()["detail"]["code"] == "cash_session_closed"


def test_reloj_del_equipo_atrasado_no_marca_una_venta_normal(client, orphan) -> None:
    """Research R7: una venta enviada antes del cierre, con la hora del equipo atrasada,
    no aparece como posterior al cierre (se comparan horas del servidor)."""
    late_clock = send_sale(client, orphan, created_at=clock.utcnow() - timedelta(minutes=30))
    assert late_clock.status_code == 200, late_clock.text
    response = admin_close(client, orphan, counted={"cash_usd": "44.00"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["post_close_operations"] == []
    assert all(not movement["after_close"] for movement in data["movements"])
    assert {r["method"]: r for r in data["reconciliation"]}["cash_usd"]["expected"] == "44.00"


def test_equipo_revocado_no_registra_egresos_ni_cierra(client, orphan) -> None:
    """Revisión de seguridad de la 1.4: un equipo revocado no registra egresos ni cierra su
    caja por la cola, aunque la operación diga ser anterior a la revocación (la hora la
    escribe el equipo). Su caja la cierra el Admin desde otro equipo (FR-018)."""
    before = clock.utcnow() - timedelta(minutes=5)
    revoke = client.post(f"/api/v1/devices/{orphan['tablet'].id}/revoke", headers=orphan["admin"])
    assert revoke.status_code == 200, revoke.text
    headers = device_headers(orphan["seller"], orphan["token"])
    outflow = client.post(URL, json=outflow_operation(orphan, before), headers=headers)
    assert outflow.status_code == 403
    assert outflow.json()["detail"]["code"] == "device_revoked"
    close = {
        "id": str(uuid.uuid7()),
        "operation_type": "cash_session.close",
        "schema_version": 1,
        "created_at": before.isoformat(),
        "payload": {
            "cash_session_id": orphan["session_id"],
            "counts": [
                {"method": method, "device_expected": "0.00", "counted": "0.00"}
                for method in METHODS
            ],
            "note": NOTE,
        },
    }
    closed = client.post(URL, json=close, headers=headers)
    assert closed.status_code == 403
    assert closed.json()["detail"]["code"] == "device_revoked"


def test_admin_cierra_con_el_token_del_equipo_revocado(client, orphan) -> None:
    """FR-018: el cierre del Admin desde fuera del equipo funciona aunque el navegador
    traiga el token del propio equipo revocado (no pasa por la regla de la cola)."""
    revoke = client.post(f"/api/v1/devices/{orphan['tablet'].id}/revoke", headers=orphan["admin"])
    assert revoke.status_code == 200, revoke.text
    response = admin_close(
        client,
        orphan,
        headers=device_headers(orphan["admin"], orphan["token"]),
        counted={"cash_usd": "32.00"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["closed_outside_device"] is True
