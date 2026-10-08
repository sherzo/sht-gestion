"""Instalación del primer administrador con código secreto (RF-44/FR-001, US1)."""

from datetime import timedelta

import pytest

from app.core.config import get_settings
from app.domain.roles import Role
from tests.helpers import REFRESH_COOKIE, audit_actions, audit_entries

pytestmark = pytest.mark.db

SETUP = {
    "setup_code": "codigo-de-prueba",
    "full_name": "Dueño del Negocio",
    "username": "Dueno",
    "password": "clave-del-dueno",
}


def test_estado_pide_instalacion_con_base_vacia(client) -> None:
    assert client.get("/api/v1/setup/status").json() == {"setup_required": True}


def test_estado_no_pide_instalacion_si_hay_usuarios(client, make_user) -> None:
    make_user(Role.ADMIN)
    assert client.get("/api/v1/setup/status").json() == {"setup_required": False}


def test_estado_no_pide_instalacion_sin_codigo_configurado(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "setup_code", None)
    assert client.get("/api/v1/setup/status").json() == {"setup_required": False}


def test_codigo_incorrecto_se_rechaza_y_se_audita(client, db) -> None:
    response = client.post("/api/v1/setup", json={**SETUP, "setup_code": "otro"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "invalid_setup_code"
    assert audit_actions(db) == ["setup.failed"]
    assert client.get("/api/v1/setup/status").json() == {"setup_required": True}


def test_cinco_fallos_bloquean_la_instalacion_15_minutos(client, advance_clock) -> None:
    for _ in range(5):
        client.post("/api/v1/setup", json={**SETUP, "setup_code": "otro"})

    locked = client.post("/api/v1/setup", json=SETUP)
    assert locked.status_code == 429
    assert locked.json()["detail"]["code"] == "setup_locked"

    advance_clock(timedelta(minutes=15, seconds=1))
    assert client.post("/api/v1/setup", json=SETUP).status_code == 201


def test_instalacion_correcta_crea_el_admin_y_entra(client, db) -> None:
    response = client.post("/api/v1/setup", json=SETUP)

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "dueno"
    assert body["user"]["role"] == "admin"
    assert body["user"]["must_change_password"] is False
    assert REFRESH_COOKIE in response.cookies

    [entry] = audit_entries(db, "setup.admin_created")
    assert str(entry.user_id) == body["user"]["id"]
    assert entry.after == {"username": "dueno", "full_name": "Dueño del Negocio", "role": "admin"}

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200


def test_segunda_instalacion_no_esta_disponible(client) -> None:
    assert client.post("/api/v1/setup", json=SETUP).status_code == 201

    again = client.post("/api/v1/setup", json={**SETUP, "username": "otro"})
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "setup_not_available"


def test_sin_codigo_configurado_la_instalacion_no_esta_disponible(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "setup_code", None)

    response = client.post("/api/v1/setup", json=SETUP)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "setup_not_available"


def test_datos_invalidos_de_instalacion(client) -> None:
    response = client.post(
        "/api/v1/setup", json={**SETUP, "username": "no válido", "password": "corta"}
    )
    assert response.status_code == 422
    fields = response.json()["detail"]["fields"]
    assert "username" in fields
    assert "password" in fields
