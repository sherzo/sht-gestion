"""Matriz de permisos de la API (RNF-05/FR-010, FR-012, FR-016a; SC-003).

Cada fila de MATRIX es un endpoint del contrato (contracts/api.md) con los actores que
pueden usarlo. Por cada fila y actor se verifica que el servidor permite o niega el
acceso. Cada historia agrega aquí las filas de sus endpoints.
"""

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.domain.roles import Role
from tests.conftest import DEFAULT_PASSWORD

pytestmark = pytest.mark.db

ANONYMOUS = "anonymous"
ADMIN = "admin"
SELLER = "seller"
WAREHOUSE = "warehouse"
TEMPORARY = "temporary_password"

EVERYONE = frozenset({ANONYMOUS, ADMIN, SELLER, WAREHOUSE, TEMPORARY})
ANY_SESSION = frozenset({ADMIN, SELLER, WAREHOUSE, TEMPORARY})
ANY_ROLE = frozenset({ADMIN, SELLER, WAREHOUSE})
ADMIN_ONLY = frozenset({ADMIN})

# Códigos que indican que el acceso fue negado por permisos.
DENIAL_CODES = {"not_authenticated", "forbidden", "password_change_required"}


@dataclass(frozen=True)
class Row:
    method: str
    path: str
    allowed: frozenset[str]
    body: dict[str, Any] | None = field(default=None)

    @property
    def id(self) -> str:
        return f"{self.method} {self.path}"


MATRIX: list[Row] = [
    # Salud
    Row("GET", "/api/v1/health", EVERYONE),
    Row("GET", "/api/v1/health/db", EVERYONE),
    # Instalación
    Row("GET", "/api/v1/setup/status", EVERYONE),
    Row(
        "POST",
        "/api/v1/setup",
        EVERYONE,
        {"setup_code": "x", "full_name": "X", "username": "nuevo", "password": "clave-larga-1"},
    ),
    # Sesión
    Row("POST", "/api/v1/auth/login", EVERYONE, {"username": "nadie", "password": "x"}),
    Row("POST", "/api/v1/auth/refresh", EVERYONE, {}),
    Row("POST", "/api/v1/auth/logout", ANY_SESSION, {}),
    Row("GET", "/api/v1/auth/me", ANY_SESSION),
    Row(
        "POST",
        "/api/v1/auth/password",
        ANY_SESSION,
        {"current_password": "incorrecta", "new_password": "clave-nueva-1"},
    ),
    # Usuarios (RF-45)
    Row("GET", "/api/v1/users", ADMIN_ONLY),
    Row(
        "POST",
        "/api/v1/users",
        ADMIN_ONLY,
        {"full_name": "Nuevo", "username": "nuevo", "role": "seller", "password": "clave-1234"},
    ),
    Row("GET", "/api/v1/users/{user_id}", ADMIN_ONLY),
    Row("PATCH", "/api/v1/users/{user_id}", ADMIN_ONLY, {"full_name": "Otro nombre"}),
    Row("POST", "/api/v1/users/{user_id}/password", ADMIN_ONLY, {"new_password": "temporal-123"}),
    # PIN del admin (RF-44, RN-07)
    Row("PUT", "/api/v1/auth/pin", ADMIN_ONLY, {"current_password": "incorrecta", "pin": "1234"}),
    Row("POST", "/api/v1/auth/pin/verify", ANY_ROLE, {"admin_username": "nadie", "pin": "1234"}),
    # Auditoría (RF-46)
    Row("GET", "/api/v1/audit-log", ADMIN_ONLY),
]


@pytest.fixture
def actor_headers(make_user, auth_headers):
    """Crea los usuarios de cada actor y devuelve el encabezado del pedido."""
    target = make_user(Role.SELLER, username="objetivo")

    def headers_for(actor: str) -> dict[str, str]:
        if actor == ANONYMOUS:
            return {}
        if actor == TEMPORARY:
            user = make_user(Role.ADMIN, username="temporal", must_change_password=True)
        else:
            user = make_user(Role(actor), username=f"actor_{actor}")
        return auth_headers(user, DEFAULT_PASSWORD)

    headers_for.target_id = str(target.id)  # type: ignore[attr-defined]
    return headers_for


@pytest.mark.parametrize("actor", sorted(EVERYONE))
@pytest.mark.parametrize("row", MATRIX, ids=lambda row: row.id)
def test_matriz_de_permisos(client, actor_headers, row: Row, actor: str) -> None:
    headers = actor_headers(actor)
    path = row.path.replace("{user_id}", actor_headers.target_id)
    kwargs: dict[str, Any] = {"headers": headers}
    if row.body is not None:
        kwargs["json"] = row.body

    response = client.request(row.method, path, **kwargs)
    data = response.json() if response.content else None
    detail = data.get("detail") if isinstance(data, dict) else None
    code = detail.get("code") if isinstance(detail, dict) else None

    if actor in row.allowed:
        assert code not in DENIAL_CODES, f"{actor} debería poder usar {row.id}: {response.text}"
    elif actor == ANONYMOUS:
        assert response.status_code == 401
        assert code == "not_authenticated"
    elif actor == TEMPORARY:
        assert response.status_code == 403
        assert code == "password_change_required"
    else:
        assert response.status_code == 403
        assert code == "forbidden"
