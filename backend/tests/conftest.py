"""Base de las pruebas del backend.

Las pruebas marcadas `db` usan la base de DATABASE_URL (se saltan sin ella): se aplican
las migraciones una vez y se vacían las tablas antes de cada prueba. Usar una base
dedicada, por ejemplo `sht_test`, porque su contenido se borra.
"""

import os
import uuid
from decimal import Decimal

# Configuración de pruebas, antes de importar la aplicación (get_settings se cachea).
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "secreto-solo-para-pruebas-con-longitud-suficiente"
os.environ["SETUP_CODE"] = "codigo-de-prueba"
os.environ["REFRESH_COOKIE_SECURE"] = "false"
os.environ["REFRESH_COOKIE_SAMESITE"] = "lax"
os.environ["PHOTO_STORAGE"] = "local"
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
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.api.deps import CurrentUser, require_authenticated, require_roles  # noqa: E402
from app.core import clock  # noqa: E402
from app.core.security import hash_secret  # noqa: E402
from app.db.models import (  # noqa: E402
    AppUser,
    Category,
    Product,
    StockMovement,
    Unit,
)
from app.db.session import get_sessionmaker  # noqa: E402
from app.domain.roles import Role  # noqa: E402
from app.domain.search import build_search_text  # noqa: E402
from app.domain.sku import format_sku  # noqa: E402
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


# Tablas que se vacían antes de cada prueba `db`. Las de configuración del inventario
# (unidades, categorías y atributos) se vuelven a llenar con sus datos iniciales.
TABLES = (
    "app_user",
    "user_session",
    "refresh_token",
    "audit_log",
    "unit",
    "category",
    "attribute_definition",
    "product",
    "product_price",
    "product_photo",
    "stock_movement",
    "adjustment_request",
    "stock_count",
    "stock_count_line",
)
SEEDED_TABLES = ("unit", "category", "attribute_definition")


@pytest.fixture(scope="session")
def _migrated() -> None:
    """Recrea el esquema con las migraciones y copia sus datos iniciales en tablas
    `test_seed_*`, para restaurarlos rápido dentro de la base antes de cada prueba. Se
    parte de cero porque la última prueba de la sesión anterior deja datos."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    with get_sessionmaker()() as db:
        for table in SEEDED_TABLES:
            db.execute(text(f"DROP TABLE IF EXISTS test_seed_{table}"))
        db.commit()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    with get_sessionmaker()() as db:
        for table in SEEDED_TABLES:
            db.execute(text(f"CREATE TABLE test_seed_{table} AS SELECT * FROM {table}"))
        db.commit()


@pytest.fixture(autouse=True)
def _clean_state(request: pytest.FixtureRequest) -> Iterator[None]:
    clock.reset()
    if request.node.get_closest_marker("db") and HAS_DATABASE:
        request.getfixturevalue("_migrated")
        with get_sessionmaker()() as db:
            # DELETE sin triggers es más rápido que TRUNCATE en tablas pequeñas y salta
            # las reglas de inmutabilidad (que se prueban aparte) solo aquí.
            db.execute(text("SET LOCAL session_replication_role = replica"))
            for table in TABLES:
                db.execute(text(f"DELETE FROM {table}"))
            for table in SEEDED_TABLES:
                db.execute(text(f"INSERT INTO {table} SELECT * FROM test_seed_{table}"))
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


# --- Productos e inventario (etapa 1.1b) ---------------------------------------------

DEFAULT_ATTRIBUTES = {
    "MAN": {"hose_type": "R2", "diameter": '1/2"'},
    "CON": {"fitting_type": "Hembra giratoria", "size": '1/2"'},
    "FER": {"ferrule_type": "Prensable", "size": '1/2"'},
    "FRT": {},
}


@pytest.fixture
def photo_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Las fotos de la prueba se guardan en un directorio temporal."""
    from app.core.config import get_settings

    directory = tmp_path / "media"
    monkeypatch.setattr(get_settings(), "photo_local_dir", str(directory))
    return directory


@pytest.fixture
def category_id(db: Session) -> Callable[[str], uuid.UUID]:
    def lookup(prefix: str) -> uuid.UUID:
        return db.scalar(select(Category.id).where(Category.sku_prefix == prefix))

    return lookup


@pytest.fixture
def make_category(db: Session) -> Callable[..., Category]:
    def factory(prefix: str = "ACE", *, name: str | None = None, unit_code: str = "u") -> Category:
        unit_id = db.scalar(select(Unit.id).where(Unit.code == unit_code))
        category = Category(
            name=name or f"Categoría {prefix}",
            sku_prefix=prefix,
            next_sku_number=1,
            default_unit_id=unit_id,
            unit_locked=False,
            is_active=True,
        )
        db.add(category)
        db.commit()
        return category

    return factory


@pytest.fixture
def make_product(db: Session) -> Callable[..., Product]:
    """Crea un producto directo en la base, sin pasar por la API ni por la auditoría."""

    def factory(
        category: str = "MAN",
        *,
        name: str | None = None,
        description: str = "",
        attributes: dict[str, str] | None = None,
        min_stock: str = "0",
        sale_price: str | None = None,
        avg_cost: str | None = None,
        is_active: bool = True,
        is_published: bool = False,
    ) -> Product:
        row = db.scalar(select(Category).where(Category.sku_prefix == category).with_for_update())
        number = row.next_sku_number
        row.next_sku_number = number + 1
        sku = format_sku(row.sku_prefix, number)
        values = DEFAULT_ATTRIBUTES.get(category, {}) if attributes is None else attributes
        product_name = name or f"Producto {sku}"
        product = Product(
            sku=sku,
            category_id=row.id,
            unit_id=row.default_unit_id,
            name=product_name,
            description=description,
            attributes=values,
            search_text=build_search_text(product_name, description, sku, values.values()),
            sale_price_usd=Decimal(sale_price) if sale_price else None,
            avg_cost_usd=Decimal(avg_cost) if avg_cost else None,
            min_stock=Decimal(min_stock),
            is_active=is_active,
            is_published=is_published,
        )
        db.add(product)
        db.commit()
        return product

    return factory


@pytest.fixture
def give_stock(db: Session) -> Callable[[Product, str], StockMovement]:
    """Mueve el stock con un ajuste de corrección, por el único camino permitido."""
    from app.services.inventory import post_movement

    def apply(product: Product, quantity: str) -> StockMovement:
        movement = post_movement(
            db,
            product_id=product.id,
            type="adjustment",
            quantity_delta=Decimal(quantity),
            created_by=None,
            adjustment_reason="correction",
            allow_negative=True,
        )
        db.commit()
        db.refresh(product)
        return movement

    return apply
