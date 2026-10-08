"""Base de las pruebas del backend.

Las pruebas marcadas `db` usan la base de DATABASE_URL (se saltan sin ella): se aplican
las migraciones una vez y se vacían las tablas antes de cada prueba. Usar una base
dedicada, por ejemplo `sht_test`, porque su contenido se borra.
"""

import os

# Configuración de pruebas, antes de importar la aplicación (get_settings se cachea).
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "secreto-solo-para-pruebas-con-longitud-suficiente"
os.environ["SETUP_CODE"] = "codigo-de-prueba"
os.environ["REFRESH_COOKIE_SECURE"] = "false"
os.environ["REFRESH_COOKIE_SAMESITE"] = "lax"
# Argon2 con costo mínimo: la suite debe ser rápida.
os.environ["ARGON2_TIME_COST"] = "1"
os.environ["ARGON2_MEMORY_COST"] = "1024"
os.environ["ARGON2_PARALLELISM"] = "1"

from collections.abc import Callable, Iterator  # noqa: E402
from datetime import timedelta  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Annotated  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import APIRouter, Depends  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.api.deps import CurrentUser, require_authenticated, require_roles  # noqa: E402
from app.core import clock  # noqa: E402
from app.core.security import hash_secret  # noqa: E402
from app.db.models import AppUser  # noqa: E402
from app.db.session import get_sessionmaker  # noqa: E402
from app.domain.roles import Role  # noqa: E402
from app.main import app  # noqa: E402

HAS_DATABASE = bool(os.getenv("DATABASE_URL"))
DEFAULT_PASSWORD = "clave-segura-1"
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Rutas solo de pruebas, para probar permisos sin depender de otras historias (T018).
_test_router = APIRouter(prefix="/_test", tags=["_test"])


AdminOnly = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]
AnyUser = Annotated[CurrentUser, Depends(require_authenticated())]


@_test_router.get("/admin-only")
def _admin_only(current: AdminOnly) -> dict[str, str]:
    return {"role": current.user.role}


@_test_router.get("/any-user")
def _any_user(current: AnyUser) -> dict[str, str]:
    return {"role": current.user.role}


app.include_router(_test_router, prefix="/api/v1")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skip = pytest.mark.skip(reason="requiere DATABASE_URL")
    for item in items:
        if "db" in item.keywords and not HAS_DATABASE:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def _migrated() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def _clean_state(request: pytest.FixtureRequest) -> Iterator[None]:
    clock.reset()
    if request.node.get_closest_marker("db") and HAS_DATABASE:
        request.getfixturevalue("_migrated")
        with get_sessionmaker()() as db:
            db.execute(text("TRUNCATE app_user, user_session, refresh_token, audit_log CASCADE"))
            db.commit()
    yield
    clock.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db() -> Iterator[Session]:
    with get_sessionmaker()() as session:
        yield session


@pytest.fixture
def advance_clock() -> Callable[[timedelta], None]:
    return clock.advance


@pytest.fixture
def make_user(db: Session) -> Callable[..., AppUser]:
    def factory(
        role: Role = Role.SELLER,
        *,
        username: str | None = None,
        full_name: str | None = None,
        password: str = DEFAULT_PASSWORD,
        must_change_password: bool = False,
        is_active: bool = True,
        pin: str | None = None,
    ) -> AppUser:
        name = username or f"{role.value}{db.query(AppUser).count() + 1}"
        user = AppUser(
            username=name,
            full_name=full_name or f"Usuario {name}",
            role=role.value,
            password_hash=hash_secret(password),
            must_change_password=must_change_password,
            pin_hash=hash_secret(pin) if pin else None,
            pin_failed_attempts=0,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        return user

    return factory


def login(client: TestClient, username: str, password: str = DEFAULT_PASSWORD) -> dict:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def auth_headers(client: TestClient) -> Callable[..., dict[str, str]]:
    def factory(user: AppUser, password: str = DEFAULT_PASSWORD) -> dict[str, str]:
        token = login(client, user.username, password)["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return factory
