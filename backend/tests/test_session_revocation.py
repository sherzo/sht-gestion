"""Desactivar o cambiar el rol rige desde la siguiente petición (RNF-05/FR-013; SC-004).

Usa las rutas de prueba /_test/ para no depender de otras historias.
"""

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.models import UserSession
from app.domain.roles import Role
from tests.helpers import bearer

pytestmark = pytest.mark.db


def test_usuario_desactivado_pierde_el_acceso_en_la_siguiente_peticion(
    client, make_user, auth_headers, db
) -> None:
    user = make_user(Role.SELLER)
    headers = auth_headers(user)
    assert client.get("/api/v1/_test/any-user", headers=headers).status_code == 200

    user.is_active = False
    db.commit()

    response = client.get("/api/v1/_test/any-user", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "session_ended"


def test_cambio_de_rol_rige_sin_renovar_el_token(client, make_user, auth_headers, db) -> None:
    user = make_user(Role.ADMIN)
    headers = auth_headers(user)
    assert client.get("/api/v1/_test/admin-only", headers=headers).status_code == 200

    user.role = Role.SELLER.value
    db.commit()

    response = client.get("/api/v1/_test/admin-only", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "forbidden"


def test_el_rol_del_token_no_da_acceso(client, make_user, auth_headers, db) -> None:
    user = make_user(Role.SELLER)
    auth_headers(user)
    session = db.scalar(select(UserSession).where(UserSession.user_id == user.id))

    forged = create_access_token(user.id, session.id, Role.ADMIN.value)

    response = client.get("/api/v1/_test/admin-only", headers=bearer(forged))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "forbidden"
