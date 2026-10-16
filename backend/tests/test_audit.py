"""Registro y consulta de auditoría (RF-46, RNF-08/FR-020 a FR-025; SC-005)."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.db.models import AppUser, AuditLog
from app.domain.roles import Role
from tests.helpers import audit_actions, bearer

pytestmark = pytest.mark.db

ALL_ACTIONS = {
    "setup.admin_created",
    "setup.failed",
    "auth.login_succeeded",
    "auth.login_failed",
    "auth.login_locked",
    "auth.password_changed",
    "auth.pin_set",
    "auth.pin_verified",
    "auth.pin_failed",
    "auth.pin_locked",
    "user.created",
    "user.updated",
    "user.role_changed",
    "user.deactivated",
    "user.reactivated",
    "user.password_reset",
}
SECRETS = [
    "codigo-de-prueba",
    "clave-del-dueno",
    "clave-inicial-1",
    "temporal-123",
    "clave-propia-1",
    "864209",
]


def _post(client, path, body, token=None):
    return client.post(path, json=body, headers=bearer(token) if token else {})


def test_recorrido_completo_genera_todas_las_acciones_sin_secretos(client, db) -> None:
    # Instalación con un intento fallido.
    _post(
        client,
        "/api/v1/setup",
        {
            "setup_code": "x",
            "full_name": "Dueño",
            "username": "dueno",
            "password": "clave-del-dueno",
        },
    )
    setup = _post(
        client,
        "/api/v1/setup",
        {
            "setup_code": "codigo-de-prueba",
            "full_name": "Dueño",
            "username": "dueno",
            "password": "clave-del-dueno",
        },
    )
    admin_token = setup.json()["access_token"]

    # Usuarios: alta, nombre, rol, desactivación, reactivación y restablecimiento.
    created = _post(
        client,
        "/api/v1/users",
        {"full_name": "Maria", "username": "maria", "role": "admin", "password": "clave-inicial-1"},
        admin_token,
    ).json()
    user_path = f"/api/v1/users/{created['id']}"
    client.patch(user_path, json={"full_name": "María"}, headers=bearer(admin_token))
    client.patch(user_path, json={"role": "seller"}, headers=bearer(admin_token))
    client.patch(user_path, json={"is_active": False}, headers=bearer(admin_token))
    client.patch(user_path, json={"is_active": True}, headers=bearer(admin_token))
    _post(client, f"{user_path}/password", {"new_password": "temporal-123"}, admin_token)

    # Sesión: ingreso, cambio de contraseña, fallos y bloqueo.
    maria_token = _post(
        client, "/api/v1/auth/login", {"username": "maria", "password": "temporal-123"}
    ).json()["access_token"]
    _post(
        client,
        "/api/v1/auth/password",
        {"current_password": "temporal-123", "new_password": "clave-propia-1"},
        maria_token,
    )
    for _ in range(5):
        _post(client, "/api/v1/auth/login", {"username": "maria", "password": "incorrecta"})

    # PIN: definición, verificación correcta, fallos y bloqueo.
    client.put(
        "/api/v1/auth/pin",
        json={"current_password": "clave-del-dueno", "pin": "864209"},
        headers=bearer(admin_token),
    )
    _post(
        client, "/api/v1/auth/pin/verify", {"admin_username": "dueno", "pin": "864209"}, maria_token
    )
    for _ in range(5):
        _post(
            client,
            "/api/v1/auth/pin/verify",
            {"admin_username": "dueno", "pin": "0000"},
            maria_token,
        )

    assert set(audit_actions(db)) == ALL_ACTIONS

    rows = db.execute(
        text("SELECT before::text, after::text, details::text, reason FROM audit_log")
    ).all()
    stored = " ".join(str(value) for row in rows for value in row if value)
    for secret in SECRETS:
        assert secret not in stored, f"La auditoría contiene el secreto {secret!r}"


def test_la_auditoria_no_se_modifica_ni_se_borra(make_user, db) -> None:
    user = make_user(Role.ADMIN)
    db.add(AuditLog(occurred_at=datetime.now(UTC), user_id=user.id, action="user.created"))
    db.commit()

    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE audit_log SET action = 'user.updated'"))
    db.rollback()
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM audit_log"))
    db.rollback()


def test_si_la_auditoria_falla_la_accion_no_ocurre(
    client, make_user, auth_headers, db, monkeypatch
) -> None:
    headers = auth_headers(make_user(Role.ADMIN))

    def broken(*args, **kwargs):
        raise RuntimeError("auditoría caída")

    monkeypatch.setattr("app.services.users.record_audit", broken)
    with pytest.raises(RuntimeError):
        client.post(
            "/api/v1/users",
            json={
                "full_name": "X",
                "username": "nuevo",
                "role": "seller",
                "password": "clave-1234",
            },
            headers=headers,
        )

    db.expire_all()
    assert db.scalar(select(AppUser).where(AppUser.username == "nuevo")) is None


def _entry(db, user, action, occurred_at):
    db.add(AuditLog(occurred_at=occurred_at, user_id=user.id if user else None, action=action))


@pytest.fixture
def admin_headers(make_user, auth_headers):
    return auth_headers(make_user(Role.ADMIN, username="dueno"))


def test_filtros_por_usuario_accion_y_fecha_de_caracas(
    client, make_user, admin_headers, db
) -> None:
    maria = make_user(Role.SELLER, username="maria", full_name="María")
    # 23:30 del 15/09 en Caracas (ya es 16/09 en UTC) y 00:30 del 16/09 en Caracas.
    _entry(db, maria, "user.created", datetime(2026, 9, 16, 3, 30, tzinfo=UTC))
    _entry(db, maria, "auth.pin_failed", datetime(2026, 9, 16, 4, 30, tzinfo=UTC))
    _entry(db, None, "setup.failed", datetime(2026, 9, 10, 12, 0, tzinfo=UTC))
    db.commit()

    def query(**params):
        response = client.get("/api/v1/audit-log", params=params, headers=admin_headers)
        assert response.status_code == 200, response.text
        return response.json()

    day = query(date_from="2026-09-15", date_to="2026-09-15")
    assert [item["action"] for item in day["items"]] == ["user.created"]
    assert day["items"][0]["user"] == {
        "id": str(maria.id),
        "username": "maria",
        "full_name": "María",
    }

    by_user = query(user_id=str(maria.id))
    assert [item["action"] for item in by_user["items"]] == ["auth.pin_failed", "user.created"]

    exact = query(action="user.created")
    assert [item["action"] for item in exact["items"]] == ["user.created"]

    group = query(action="user.created,auth.pin_failed")
    assert {item["action"] for item in group["items"]} == {"user.created", "auth.pin_failed"}

    prefix = query(action="auth.", date_from="2026-09-01", date_to="2026-09-30")
    assert {item["action"] for item in prefix["items"]} == {"auth.pin_failed"}


def test_paginacion_y_orden(client, admin_headers, db) -> None:
    for hour in (10, 11, 12):
        _entry(db, None, "setup.failed", datetime(2026, 10, 1, hour, tzinfo=UTC))
    db.commit()

    params = {"action": "setup.failed", "page_size": 2}
    first = client.get("/api/v1/audit-log", params=params, headers=admin_headers).json()
    second = client.get(
        "/api/v1/audit-log", params={**params, "page": 2}, headers=admin_headers
    ).json()

    assert first["total"] == 3
    assert [item["occurred_at"][:13] for item in first["items"]] == [
        "2026-10-01T12",
        "2026-10-01T11",
    ]
    assert [item["occurred_at"][:13] for item in second["items"]] == ["2026-10-01T10"]


def test_tamano_de_pagina_maximo(client, admin_headers) -> None:
    response = client.get("/api/v1/audit-log", params={"page_size": 101}, headers=admin_headers)
    assert response.status_code == 422


# --- Etapa 1.2: proveedores, compras, tasa, gastos frecuentes y alertas (R12) ---------


def test_acciones_de_compras_y_tasas(
    client, make_user, auth_headers, make_product, give_stock, make_purchase, db
) -> None:
    """RF-46/FR-023, SC-007: cada acción sensible de la etapa queda con usuario, entidad y
    valores antes y después; guardar o descartar un borrador no audita."""
    from app.core.clock import utcnow
    from app.domain.business_time import business_date

    admin_user = make_user(Role.ADMIN, username="dueno")
    admin = auth_headers(admin_user)
    today = business_date(utcnow()).isoformat()

    supplier = client.post("/api/v1/suppliers", json={"name": "Aragua"}, headers=admin).json()
    client.patch(f"/api/v1/suppliers/{supplier['id']}", json={"name": "Aragua C.A."}, headers=admin)
    client.post(
        "/api/v1/exchange-rates", json={"business_date": today, "rate": "36.50"}, headers=admin
    )
    client.put(f"/api/v1/exchange-rates/{today}", json={"rate": "36.55"}, headers=admin)
    template = client.post(
        "/api/v1/charge-templates",
        json={"name": "Comisión", "charge_type": "percent"},
        headers=admin,
    ).json()
    client.patch(
        f"/api/v1/charge-templates/{template['id']}", json={"default_value": "10"}, headers=admin
    )

    product = make_product("FRT", avg_cost="1")
    supplier_row = SimpleNamespace(id=supplier["id"])
    before_drafts = db.scalar(select(text("count(*)")).select_from(AuditLog))
    draft = make_purchase(admin, supplier_row, [(product, "1", "1")])
    client.delete(f"/api/v1/purchases/{draft['id']}", headers=admin)
    assert db.scalar(select(text("count(*)")).select_from(AuditLog)) == before_drafts

    purchase = make_purchase(admin, supplier_row, [(product, "5", "2")], confirm=True)
    give_stock(product, "-5")
    client.post(
        f"/api/v1/purchases/{purchase['id']}/void",
        json={"reason": "Factura repetida"},
        headers=admin,
    )
    alert = client.get("/api/v1/alerts", headers=admin).json()["items"][0]
    client.post(f"/api/v1/alerts/{alert['id']}/resolve", headers=admin)

    entries = {
        entry.action: entry for entry in db.scalars(select(AuditLog).order_by(AuditLog.occurred_at))
    }
    expected = {
        "supplier.created",
        "supplier.updated",
        "exchange_rate.created",
        "exchange_rate.corrected",
        "charge_template.created",
        "charge_template.updated",
        "purchase.confirmed",
        "purchase.voided",
        "product.cost_updated",
        "alert.resolved",
    }
    assert expected <= set(entries)
    for action in expected:
        assert entries[action].user_id == admin_user.id, action
    assert entries["supplier.updated"].before["name"] == "Aragua"
    assert entries["supplier.updated"].after["name"] == "Aragua C.A."
    assert entries["exchange_rate.corrected"].before["rate"] == "36.50000000"
    assert entries["exchange_rate.corrected"].after["rate"] == "36.55000000"
    assert entries["charge_template.updated"].after["default_value"] == "10.00"
    assert entries["purchase.voided"].reason == "Factura repetida"
    cost = entries["product.cost_updated"]
    assert cost.entity_id == product.id
    assert (cost.before["avg_cost_usd"], cost.after["avg_cost_usd"]) == ("1.000000", "2.000000")
    assert cost.details["cause"] == "purchase"

    group = ",".join(sorted(expected))
    listed = client.get("/api/v1/audit-log", params={"action": group}, headers=admin).json()
    assert {item["action"] for item in listed["items"]} == expected


def test_acciones_de_ventas_y_caja(
    client,
    make_user,
    auth_headers,
    make_device,
    make_rate,
    open_cash_session,
    make_product,
    give_stock,
    make_sale,
    db,
) -> None:
    """RF-46/FR-050: equipos, apertura de caja, descuentos y su autorización, y anulación
    quedan con usuario, equipo, entidad y detalle; una venta sin descuento no se audita."""
    import uuid as uuid_module

    from app.core.clock import utcnow
    from app.domain.business_time import business_date
    from tests.conftest import device_headers

    make_rate(business_date(utcnow()), "36.50")
    admin_user = make_user(Role.ADMIN, username="dueno", pin="4321")
    admin = auth_headers(admin_user)
    seller_user = make_user(Role.SELLER, username="vende")
    seller = auth_headers(seller_user)

    registered = client.post("/api/v1/devices", json={"name": "Mostrador"}, headers=admin).json()
    token = registered["token"]
    spare = client.post("/api/v1/devices", json={"name": "Tablet"}, headers=admin).json()
    client.post(f"/api/v1/devices/{spare['id']}/revoke", headers=admin)
    session = open_cash_session(seller, token, "100.00", "5.00")

    product = make_product("CON", sale_price="10.00")
    give_stock(product, "20")
    before = db.scalar(select(text("count(*)")).select_from(AuditLog))
    make_sale(seller, token, session["id"], [(product, "1")])
    assert db.scalar(select(text("count(*)")).select_from(AuditLog)) == before

    sale_id = str(uuid_module.uuid7())
    request = {
        "method": "request",
        "sale_id": sale_id,
        "discount_type": "percent",
        "discount_value": "10.00",
        "base_usd": "10.00",
    }
    pending = client.post(
        "/api/v1/discount-authorizations", json=request, headers=device_headers(seller, token)
    ).json()
    client.post(
        f"/api/v1/discount-authorizations/{pending['id']}/approve",
        json={"discount_value": "5.00"},
        headers=admin,
    )
    other = client.post(
        "/api/v1/discount-authorizations", json=request, headers=device_headers(seller, token)
    ).json()
    client.post(
        f"/api/v1/discount-authorizations/{other['id']}/reject",
        json={"reason": "No aplica"},
        headers=admin,
    )
    sale = make_sale(
        seller,
        token,
        session["id"],
        [(product, "1")],
        discount={"type": "percent", "value": "5.00", "authorization_id": pending["id"]},
        sale_id=sale_id,
    )
    client.post(
        f"/api/v1/sales/{sale['id']}/void", json={"reason": "Error de cobro"}, headers=admin
    )

    entries: dict[str, list[AuditLog]] = {}
    for entry in db.scalars(select(AuditLog).order_by(AuditLog.occurred_at)):
        entries.setdefault(entry.action, []).append(entry)
    expected = {
        "device.registered",
        "device.revoked",
        "cash_session.opened",
        "discount_authorization.requested",
        "discount_authorization.approved",
        "discount_authorization.rejected",
        "sale.discounted",
        "sale.voided",
    }
    assert expected <= set(entries)
    assert len(entries["device.registered"]) == 2
    assert entries["device.registered"][0].after == {"name": "Mostrador", "series": "A"}
    assert entries["cash_session.opened"][0].user_id == seller_user.id
    assert str(entries["cash_session.opened"][0].device_id) == registered["id"]
    approved = entries["discount_authorization.approved"][0]
    assert approved.user_id == admin_user.id
    assert (approved.before["discount_value"], approved.after["discount_value"]) == (
        "10.00",
        "5.00",
    )
    assert approved.after["requested_value"] == "10.00"
    assert entries["discount_authorization.rejected"][0].reason == "No aplica"
    discounted = entries["sale.discounted"][0]
    assert discounted.user_id == seller_user.id
    assert discounted.details["sale_discount"]["method"] == "request"
    assert discounted.details["sale_discount"]["authorized_by"] == str(admin_user.id)
    voided = entries["sale.voided"][0]
    assert voided.reason == "Error de cobro"
    assert str(voided.entity_id) == sale["id"]

    group = ",".join(sorted(expected))
    listed = client.get("/api/v1/audit-log", params={"action": group}, headers=admin).json()
    assert {item["action"] for item in listed["items"]} == expected


def test_acciones_de_caja(
    client,
    make_user,
    auth_headers,
    make_device,
    make_rate,
    open_cash_session,
    make_product,
    make_sale,
    register_outflow,
    close_cash_session,
    db,
) -> None:
    """RF-46/FR-027: egresos y su anulación, cierre por la cola y por el Admin desde otro
    equipo, y anulación con devolución en otra caja quedan con usuario, equipo, entidad y
    detalle; `GET /audit-log` las filtra juntas."""
    from app.core.clock import utcnow
    from app.domain.business_time import business_date
    from tests.conftest import device_headers

    make_rate(business_date(utcnow()), "36.50")
    admin_user = make_user(Role.ADMIN, username="dueno")
    admin = auth_headers(admin_user)
    seller_user = make_user(Role.SELLER, username="vende")
    seller = auth_headers(seller_user)
    counter, token = make_device("Mostrador")
    _, tablet_token = make_device("Tablet")
    session = open_cash_session(seller, token, "0.00", "20.00")
    product = make_product("CON", sale_price="10.00")
    sale = make_sale(seller, token, session["id"], [(product, "1")])

    outflow = register_outflow(seller, token, session["id"], amount="2.00").json()
    client.post(
        f"/api/v1/cash-outflows/{outflow['id']}/void",
        json={"reason": "Registrado por error"},
        headers=admin,
    )
    assert close_cash_session(seller, token, session["id"]).status_code == 200
    open_cash_session(seller, token)
    voided = client.post(
        f"/api/v1/sales/{sale['id']}/void",
        json={"reason": "Error de cobro"},
        headers=device_headers(admin, token),
    )
    assert voided.status_code == 200, voided.text
    orphan = open_cash_session(seller, tablet_token)
    closed = client.post(
        f"/api/v1/cash-sessions/{orphan['id']}/close",
        json={
            "counts": [
                {"method": method, "counted": "0.00"}
                for method in ("cash_ves", "mobile_payment", "pos_card")
                + ("cash_usd", "zelle", "binance_usdt")
            ],
            "note": "La tablet se dañó",
        },
        headers=admin,
    )
    assert closed.status_code == 200, closed.text

    entries: dict[str, list[AuditLog]] = {}
    for entry in db.scalars(select(AuditLog).order_by(AuditLog.occurred_at)):
        entries.setdefault(entry.action, []).append(entry)
    created = entries["cash_outflow.created"][0]
    assert (created.user_id, created.device_id) == (seller_user.id, counter.id)
    assert (created.after["method"], created.after["amount"]) == ("cash_usd", "2.00")
    assert created.after["reason"] == "Compra de botellones de agua"
    voided_outflow = entries["cash_outflow.voided"][0]
    assert voided_outflow.user_id == admin_user.id
    assert voided_outflow.reason == "Registrado por error"
    by_queue, by_admin = entries["cash_session.closed"]
    assert (by_queue.user_id, by_queue.device_id) == (seller_user.id, counter.id)
    assert by_queue.after["outside_device"] is False
    assert len(by_queue.after["counts"]) == 6
    assert by_admin.user_id == admin_user.id
    assert by_admin.after["outside_device"] is True
    assert by_admin.after["note"] == "La tablet se dañó"
    sale_void = entries["sale.voided"][0]
    assert sale_void.after["refund_cash_session_id"] != session["id"]
    assert sale_void.after["refund_device_id"] == str(counter.id)

    expected = {"cash_outflow.created", "cash_outflow.voided", "cash_session.closed"}
    group = ",".join(sorted(expected))
    listed = client.get("/api/v1/audit-log", params={"action": group}, headers=admin).json()
    assert {item["action"] for item in listed["items"]} == expected
