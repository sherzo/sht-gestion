"""Recuperación del único admin por comando (RF-45/FR-016a, research R8)."""

import pytest

from app import cli
from app.domain.roles import Role
from tests.helpers import audit_entries

pytestmark = pytest.mark.db


def test_reset_password_deja_una_contrasena_temporal(
    client, make_user, auth_headers, db, capsys
) -> None:
    user = make_user(Role.ADMIN, username="dueno")
    old_headers = auth_headers(user)

    exit_code = cli.main(["reset-password", "Dueno"])

    assert exit_code == 0
    temporary = capsys.readouterr().out.strip().splitlines()[-1].split()[-1]
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 401
    login = client.post("/api/v1/auth/login", json={"username": "dueno", "password": temporary})
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"] is True

    [entry] = audit_entries(db, "user.password_reset")
    assert entry.user_id is None
    assert entry.entity_id == user.id
    assert entry.details == {"source": "cli"}


def test_reset_password_de_un_usuario_inexistente(capsys) -> None:
    assert cli.main(["reset-password", "nadie"]) != 0
    assert "no existe" in capsys.readouterr().err
