"""Cambio de la propia contraseña (RF-44/FR-007, FR-008; RF-45/FR-016a)."""

import pytest

from app.domain.roles import Role
from tests.conftest import DEFAULT_PASSWORD
from tests.helpers import audit_entries, bearer

pytestmark = pytest.mark.db

NEW_PASSWORD = "clave-nueva-123"


def _token(client, username, password=DEFAULT_PASSWORD) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return response.json()["access_token"]


def _change(client, token, current, new):
    return client.post(
        "/api/v1/auth/password",
        json={"current_password": current, "new_password": new},
        headers=bearer(token),
    )


def test_contrasena_actual_incorrecta(client, make_user) -> None:
    make_user(Role.SELLER, username="maria")
    response = _change(client, _token(client, "maria"), "otra", NEW_PASSWORD)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_current_password"


@pytest.mark.parametrize("new_password", ["corta", DEFAULT_PASSWORD])
def test_contrasena_nueva_invalida(client, make_user, new_password) -> None:
    make_user(Role.SELLER, username="maria")
    response = _change(client, _token(client, "maria"), DEFAULT_PASSWORD, new_password)

    assert response.status_code == 422
    assert "new_password" in response.json()["detail"]["fields"]


def test_cambio_correcto_quita_la_marca_temporal_y_cierra_otras_sesiones(
    client, make_user, db
) -> None:
    user = make_user(Role.SELLER, username="maria", must_change_password=True)
    other_session = _token(client, "maria")
    current_session = _token(client, "maria")

    response = _change(client, current_session, DEFAULT_PASSWORD, NEW_PASSWORD)

    assert response.status_code == 204
    db.refresh(user)
    assert user.must_change_password is False
    assert client.get("/api/v1/auth/me", headers=bearer(current_session)).status_code == 200
    ended = client.get("/api/v1/auth/me", headers=bearer(other_session))
    assert ended.status_code == 401
    assert ended.json()["detail"]["code"] == "session_ended"
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "maria", "password": NEW_PASSWORD}
        ).status_code
        == 200
    )

    [entry] = audit_entries(db, "auth.password_changed")
    assert entry.user_id == user.id
    assert entry.before is None and entry.after is None
    assert NEW_PASSWORD not in str(entry.details) and DEFAULT_PASSWORD not in str(entry.details)


def test_con_contrasena_temporal_solo_puede_cambiarla(client, make_user) -> None:
    make_user(Role.SELLER, username="maria", must_change_password=True)
    token = _token(client, "maria")

    blocked = client.get("/api/v1/_test/any-user", headers=bearer(token))
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "password_change_required"
    assert client.get("/api/v1/auth/me", headers=bearer(token)).status_code == 200

    assert _change(client, token, DEFAULT_PASSWORD, NEW_PASSWORD).status_code == 204
    assert client.get("/api/v1/_test/any-user", headers=bearer(token)).status_code == 200
