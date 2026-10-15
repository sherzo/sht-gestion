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
from datetime import date, timedelta  # noqa: E402
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
    ChargeTemplate,
    Device,
    ExchangeRate,
    Product,
    StockMovement,
    Supplier,
    Unit,
)
from app.db.session import get_sessionmaker  # noqa: E402
from app.domain.business_time import business_date  # noqa: E402
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
    "alert",
    "purchase_void",
    "purchase_charge",
    "purchase_item",
    "purchase",
    "charge_template",
    "exchange_rate",
    "supplier",
    "sequence_counter",
    "payment",
    "sale_void",
    "sale_item",
    "sale",
    "discount_authorization",
    "cash_session",
    "customer",
    "outbox_operation",
    "device",
    "payment_method",
)
SEEDED_TABLES = (
    "unit",
    "category",
    "attribute_definition",
    "sequence_counter",
    "payment_method",
)


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


# --- Proveedores, compras y tasa (etapa 1.2) -------------------------------------------


@pytest.fixture
def make_supplier(db: Session) -> Callable[..., Supplier]:
    """Proveedor directo en la base (sus servicios llegan con US1)."""

    def factory(
        name: str = "Proveedor", *, rif: str | None = None, is_active: bool = True
    ) -> Supplier:
        supplier = Supplier(name=name, rif=rif, is_active=is_active)
        db.add(supplier)
        db.commit()
        return supplier

    return factory


@pytest.fixture
def make_rate(
    db: Session, make_user: Callable[..., AppUser]
) -> Callable[[date, str], ExchangeRate]:
    """Tasa BCV directa en la base (la carga por la API llega con US6)."""
    holder: dict[str, AppUser] = {}

    def factory(business_date: date, rate: str) -> ExchangeRate:
        if "admin" not in holder:
            holder["admin"] = make_user(Role.ADMIN, username="tasas")
        row = ExchangeRate(
            rate_type="BCV",
            business_date=business_date,
            rate=Decimal(rate),
            created_by=holder["admin"].id,
            created_at=clock.utcnow(),
        )
        db.add(row)
        db.commit()
        return row

    return factory


@pytest.fixture
def make_charge_template(db: Session) -> Callable[..., ChargeTemplate]:
    """Gasto frecuente directo en la base (sus servicios llegan con US7)."""

    def factory(
        name: str,
        charge_type: str,
        default_value: str | None = None,
        currency: str | None = None,
        *,
        is_active: bool = True,
    ) -> ChargeTemplate:
        row = ChargeTemplate(
            name=name,
            charge_type=charge_type,
            default_value=None if default_value is None else Decimal(default_value),
            currency=currency,
            is_active=is_active,
        )
        db.add(row)
        db.commit()
        return row

    return factory


@pytest.fixture
def make_purchase(client: TestClient) -> Callable[..., dict]:
    """Crea (y si se pide confirma) una compra por la API, como lo haría la pantalla.

    `items` es una lista de `(producto, cantidad, costo unitario)` en la moneda de la
    compra; `charges`, una lista de gastos con el formato de `PurchaseInput`.
    """

    def factory(
        headers: dict[str, str],
        supplier: Supplier,
        items: list[tuple[Product, str, str]],
        *,
        charges: list[dict] | None = None,
        currency: str = "USD",
        purchase_date: date | None = None,
        supplier_invoice_number: str | None = None,
        confirm: bool = False,
    ) -> dict:
        body = {
            "supplier_id": str(supplier.id),
            "purchase_date": (purchase_date or business_date(clock.utcnow())).isoformat(),
            "currency": currency,
            "supplier_invoice_number": supplier_invoice_number,
            "items": [
                {"product_id": str(product.id), "quantity": quantity, "unit_cost": unit_cost}
                for product, quantity, unit_cost in items
            ],
            "charges": charges or [],
        }
        response = client.post("/api/v1/purchases", json=body, headers=headers)
        assert response.status_code == 201, response.text
        purchase = response.json()
        if confirm:
            response = client.post(
                f"/api/v1/purchases/{purchase['id']}/confirm",
                json={"updated_at": purchase["updated_at"]},
                headers=headers,
            )
            assert response.status_code == 200, response.text
            purchase = response.json()
        return purchase

    return factory


# --- Equipos, caja y ventas (etapa 1.3) -------------------------------------------------


@pytest.fixture
def make_device(
    db: Session, make_user: Callable[..., AppUser]
) -> Callable[..., tuple[Device, str]]:
    """Registra un equipo con el servicio real (serie del contador) y devuelve el token en
    claro. `revoked=True` lo revoca enseguida."""
    from app.services.devices import register_device, revoke_device

    holder: dict[str, AppUser] = {}

    def factory(name: str = "Mostrador", *, revoked: bool = False) -> tuple[Device, str]:
        if "admin" not in holder:
            holder["admin"] = make_user(Role.ADMIN, username="equipos")
        device, token = register_device(db, actor=holder["admin"], name=name)
        if revoked:
            revoke_device(db, actor=holder["admin"], device_id=device.id)
        db.commit()
        return device, token

    return factory


def device_headers(headers: dict[str, str], token: str) -> dict[str, str]:
    """Cabeceras de una petición de mostrador: sesión del usuario y token del equipo."""
    return {**headers, "X-Device-Token": token}


def operation(operation_type: str, payload: dict, *, op_id: str | None = None) -> dict:
    """Cuerpo de `POST /sync/operations` con un id nuevo y la hora actual del equipo."""
    return {
        "id": op_id or str(uuid.uuid7()),
        "operation_type": operation_type,
        "schema_version": 1,
        "created_at": clock.utcnow().isoformat(),
        "payload": payload,
    }


@pytest.fixture
def open_cash_session(client: TestClient) -> Callable[..., dict]:
    """Abre la caja del equipo por la cola, como la pantalla de Caja."""

    def factory(
        headers: dict[str, str], token: str, float_ves: str = "0.00", float_usd: str = "0.00"
    ) -> dict:
        payload = {
            "id": str(uuid.uuid7()),
            "opening_float_ves": float_ves,
            "opening_float_usd": float_usd,
        }
        response = client.post(
            "/api/v1/sync/operations",
            json=operation("cash_session.open", payload),
            headers=device_headers(headers, token),
        )
        assert response.status_code == 200, response.text
        return response.json()

    return factory


def _is_meter(db: Session, product: Product) -> bool:
    return db.scalar(select(Unit.decimals).where(Unit.id == product.unit_id)) > 0


@pytest.fixture
def make_sale(client: TestClient, db: Session) -> Callable[..., dict]:
    """Arma un `SaleInput` válido (precios del producto, tasa aplicable de hoy y totales de
    `compute_sale`) y lo envía por la cola, como la pantalla de venta.

    `items` es una lista de `(producto, cantidad[, unidad escrita[, descuento]])`, con la
    cantidad ya en la unidad del producto; sin `payments`, se paga el total en efectivo
    USD. Los pagos y vueltos son `(método, monto, referencia)`. Devuelve el cuerpo de la
    respuesta; `expect` es el código HTTP esperado.
    """
    from app.domain.sale_math import DiscountInput, LineInput, SaleInput, compute_sale
    from app.services.devices import hash_token
    from app.services.exchange_rates import applicable_rate

    def discount_input(data: dict | None) -> DiscountInput | None:
        return None if data is None else DiscountInput(data["type"], Decimal(data["value"]))

    def factory(
        headers: dict[str, str],
        token: str,
        cash_session_id: str,
        items: list[tuple],
        *,
        payments: list[tuple] | None = None,
        change: list[tuple] | None = None,
        discount: dict | None = None,
        customer: dict | None = None,
        customer_id: str | None = None,
        sequence_number: int | None = None,
        seller_id: str | None = None,
        rate: tuple[str, date] | None = None,
        device_total_usd: str | None = None,
        unit_prices: dict | None = None,
        sale_id: str | None = None,
        op_id: str | None = None,
        expect: int = 200,
    ) -> dict:
        db.expire_all()
        if rate is None:
            applicable = applicable_rate(db, business_date(clock.utcnow()))
            assert applicable is not None, "La prueba necesita una tasa cargada (make_rate)"
            rate = (str(applicable.rate), applicable.business_date)
        if seller_id is None:
            seller_id = client.get("/api/v1/auth/me", headers=headers).json()["user"]["id"]
        if sequence_number is None:
            device = db.scalar(select(Device).where(Device.token_hash == hash_token(token)))
            sequence_number = device.last_sequence_number + 1
        lines = []
        for item in items:
            product, quantity = item[0], item[1]
            default_unit = "m" if _is_meter(db, product) else "unit"
            price = (unit_prices or {}).get(product.id, product.sale_price_usd)
            lines.append(
                {
                    "id": str(uuid.uuid7()),
                    "product_id": str(product.id),
                    "quantity": quantity,
                    "entered_unit": item[2] if len(item) > 2 else default_unit,
                    "unit_price_usd": str(price),
                    "discount": item[3] if len(item) > 3 else None,
                }
            )
        calc_input = SaleInput(
            rate=Decimal(rate[0]),
            lines=[
                LineInput(
                    line["id"],
                    Decimal(line["unit_price_usd"]),
                    Decimal(line["quantity"]),
                    discount_input(line["discount"]),
                )
                for line in lines
            ],
            discount=discount_input(discount),
        )
        try:
            total = compute_sale(calc_input).total_usd
        except ValueError:
            total = Decimal("0.00")  # venta inválida a propósito: la rechaza el servidor
        if payments is None:
            payments = [("cash_usd", str(total), None)] if total > 0 else []
        payload = {
            "id": sale_id or str(uuid.uuid7()),
            "sequence_number": sequence_number,
            "cash_session_id": cash_session_id,
            "seller_id": seller_id,
            "occurred_at": clock.utcnow().isoformat(),
            "exchange_rate": rate[0],
            "exchange_rate_date": rate[1].isoformat(),
            "customer": customer,
            "customer_id": customer_id,
            "items": lines,
            "discount": discount,
            "payments": [
                {"method": method, "amount": amount, "reference": reference}
                for method, amount, reference in payments
            ],
            "change": [
                {"method": method, "amount": amount, "reference": reference}
                for method, amount, reference in (change or [])
            ],
            "device_total_usd": device_total_usd or str(total),
        }
        response = client.post(
            "/api/v1/sync/operations",
            json=operation("sale.create", payload, op_id=op_id),
            headers=device_headers(headers, token),
        )
        assert response.status_code == expect, response.text
        return response.json()

    return factory
