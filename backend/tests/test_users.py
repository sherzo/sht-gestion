"""Gestión de usuarios por el admin (RF-45/FR-015 a FR-019, FR-016a; SC-009)."""

import pytest
from sqlalchemy import select

from app.db.models import AppUser, UserSession
from app.domain.roles import Role
from tests.conftest import DEFAULT_PASSWORD
from tests.helpers import audit_entries, bearer

pytestmark = pytest.mark.db

NEW_USER = {
    "full_name": "María Pérez",
    "username": "Maria.Perez",
    "role": "seller",
    "password": "clave-inicial-1",
}


@pytest.fixture
def admin(make_user):
    return make_user(Role.ADMIN, username="dueno", full_name="Dueño")


@pytest.fixture
def admin_headers(admin, auth_headers):
    return auth_headers(admin)


def _create(client, headers, **overrides):
    return client.post("/api/v1/users", json={**NEW_USER, **overrides}, headers=headers)


def test_alta_con_contrasena_temporal(client, admin, admin_headers, db) -> None:
    response = _create(client, admin_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "maria.perez"
    assert body["role"] == "seller"
    assert body["is_active"] is True
    assert body["must_change_password"] is True
    assert body["has_pin"] is False
    assert body["last_login_at"] is None

    [entry] = audit_entries(db, "user.created")
    assert entry.user_id == admin.id
    assert entry.after == {"username": "maria.perez", "full_name": "María Pérez", "role": "seller"}
    assert "clave-inicial-1" not in str(entry.after)

    login = client.post(
        "/api/v1/auth/login", json={"username": "maria.perez", "password": "clave-inicial-1"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"] is True


@pytest.mark.parametrize("username", ["ab", "con espacio", "ñandú", "x" * 31])
def test_nombre_de_usuario_invalido(client, admin_headers, username) -> None:
    response = _create(client, admin_headers, username=username)
    assert response.status_code == 422
    assert "username" in response.json()["detail"]["fields"]


def test_nombre_duplicado_sin_distinguir_mayusculas_ni_estado(
    client, admin_headers, make_user
) -> None:
    make_user(Role.SELLER, username="maria.perez", is_active=False)

    response = _create(client, admin_headers, username="MARIA.PEREZ")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "username_taken"


def test_lista_filtrable_y_ordenada_por_nombre(client, admin_headers, make_user) -> None:
    make_user(Role.SELLER, username="zeta", full_name="Zoila Vendedora")
    make_user(Role.WAREHOUSE, username="alma", full_name="Alberto Almacén")
    make_user(Role.SELLER, username="inactivo", full_name="Beto Inactivo", is_active=False)

    everyone = client.get("/api/v1/users", headers=admin_headers).json()
    assert [u["full_name"] for u in everyone] == [
        "Alberto Almacén",
        "Beto Inactivo",
        "Dueño",
        "Zoila Vendedora",
    ]

    sellers = client.get("/api/v1/users?role=seller&is_active=true", headers=admin_headers).json()
    assert [u["username"] for u in sellers] == ["zeta"]


def test_usuario_inexistente(client, admin_headers) -> None:
    response = client.get(
        "/api/v1/users/0192f0a0-0000-7000-8000-000000000000", headers=admin_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "user_not_found"


def test_cambio_de_nombre_se_audita(client, admin_headers, make_user, db) -> None:
    user = make_user(Role.SELLER, full_name="Maria")

    response = client.patch(
        f"/api/v1/users/{user.id}", json={"full_name": "María Pérez"}, headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "María Pérez"
    [entry] = audit_entries(db, "user.updated")
    assert entry.before == {"full_name": "Maria"}
    assert entry.after == {"full_name": "María Pérez"}


def test_cambio_de_rol_se_audita_y_quita_el_pin(client, admin_headers, make_user, db) -> None:
    other_admin = make_user(Role.ADMIN, username="socio", pin="1234")

    response = client.patch(
        f"/api/v1/users/{other_admin.id}", json={"role": "warehouse"}, headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["role"] == "warehouse"
    assert response.json()["has_pin"] is False
    [entry] = audit_entries(db, "user.role_changed")
    assert entry.before == {"role": "admin"}
    assert entry.after == {"role": "warehouse"}


def test_desactivar_cierra_sus_sesiones_y_reactivar(
    client, admin_headers, make_user, auth_headers, db
) -> None:
    user = make_user(Role.SELLER, username="maria")
    user_headers = auth_headers(user)

    off = client.patch(f"/api/v1/users/{user.id}", json={"is_active": False}, headers=admin_headers)
    assert off.status_code == 200
    assert off.json()["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=user_headers).status_code == 401
    sessions = db.scalars(select(UserSession).where(UserSession.user_id == user.id)).all()
    assert all(s.revoked_reason == "user_deactivated" for s in sessions)
    assert len(audit_entries(db, "user.deactivated")) == 1

    on = client.patch(f"/api/v1/users/{user.id}", json={"is_active": True}, headers=admin_headers)
    assert on.status_code == 200
    assert len(audit_entries(db, "user.reactivated")) == 1
    login = client.post(
        "/api/v1/auth/login", json={"username": "maria", "password": DEFAULT_PASSWORD}
    )
    assert login.status_code == 200


def test_no_puede_desactivarse_a_si_mismo(client, admin, admin_headers, make_user) -> None:
    make_user(Role.ADMIN, username="socio")

    response = client.patch(
        f"/api/v1/users/{admin.id}", json={"is_active": False}, headers=admin_headers
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "cannot_deactivate_self"


@pytest.mark.parametrize("change", [{"role": "seller"}, {"is_active": False}])
def test_con_otro_admin_activo_se_puede_degradar_o_desactivar(
    client, admin_headers, make_user, change
) -> None:
    partner = make_user(Role.ADMIN, username="socio")

    response = client.patch(f"/api/v1/users/{partner.id}", json=change, headers=admin_headers)
    assert response.status_code == 200


def test_ultimo_admin_no_cambia_de_rol(client, admin, admin_headers) -> None:
    response = client.patch(
        f"/api/v1/users/{admin.id}", json={"role": "seller"}, headers=admin_headers
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "last_admin"


def test_restablecer_contrasena(client, admin, admin_headers, make_user, auth_headers, db) -> None:
    user = make_user(Role.SELLER, username="maria")
    user_headers = auth_headers(user)

    response = client.post(
        f"/api/v1/users/{user.id}/password",
        json={"new_password": "temporal-123"},
        headers=admin_headers,
    )

    assert response.status_code == 204
    assert client.get("/api/v1/auth/me", headers=user_headers).status_code == 401
    db.expire_all()
    assert db.get(AppUser, user.id).must_change_password is True
    [entry] = audit_entries(db, "user.password_reset")
    assert entry.user_id == admin.id
    assert entry.details == {"source": "admin"}
    assert "temporal-123" not in str(entry.details)

    old = client.post(
        "/api/v1/auth/login", json={"username": "maria", "password": DEFAULT_PASSWORD}
    )
    assert old.status_code == 401
    token = client.post(
        "/api/v1/auth/login", json={"username": "maria", "password": "temporal-123"}
    ).json()["access_token"]
    blocked = client.get("/api/v1/users", headers=bearer(token))
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "password_change_required"
