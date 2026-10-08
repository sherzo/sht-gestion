"""Registro y consulta de auditoría (RF-46, RNF-08/FR-020 a FR-025; SC-005)."""

from datetime import UTC, datetime

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
