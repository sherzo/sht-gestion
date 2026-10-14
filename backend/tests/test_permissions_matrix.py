"""Matriz de permisos de la API (RNF-05/FR-010, FR-012, FR-016a; SC-003).

Cada fila de MATRIX es un endpoint del contrato (contracts/api.md) con los actores que
pueden usarlo. Por cada fila y actor se verifica que el servidor permite o niega el
acceso. Cada historia agrega aquí las filas de sus endpoints.
"""

import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select

from app.core.clock import utcnow
from app.db.models import (
    AdjustmentRequest,
    Alert,
    AttributeDefinition,
    ProductPhoto,
    StockCount,
    StockCountLine,
    Unit,
)
from app.domain.business_time import business_date
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
ADMIN_WAREHOUSE = frozenset({ADMIN, WAREHOUSE})
WAREHOUSE_ONLY = frozenset({WAREHOUSE})

PURCHASE_BODY = {
    "supplier_id": "{supplier_id}",
    "purchase_date": "{today}",
    "currency": "USD",
    "items": [{"product_id": "{product_id}", "quantity": "1", "unit_cost": "1"}],
}

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
    # Configuración del inventario (RF-03 a RF-05; specs/002 contracts/api.md)
    Row("GET", "/api/v1/units", ANY_ROLE),
    Row("POST", "/api/v1/units", ADMIN_ONLY, {"code": "caja", "name": "caja", "decimals": 0}),
    Row("PATCH", "/api/v1/units/{unit_id}", ADMIN_ONLY, {"name": "unidad suelta"}),
    Row("GET", "/api/v1/categories", ANY_ROLE),
    Row(
        "POST",
        "/api/v1/categories",
        ADMIN_ONLY,
        {"name": "Aceites", "sku_prefix": "ACE", "default_unit_id": "{unit_id}"},
    ),
    Row("PATCH", "/api/v1/categories/{category_id}", ADMIN_ONLY, {"name": "Ferretería general"}),
    Row(
        "POST",
        "/api/v1/categories/{category_id}/attributes",
        ADMIN_ONLY,
        {"key": "material", "label": "Material", "data_type": "text"},
    ),
    Row("PATCH", "/api/v1/attributes/{attribute_id}", ADMIN_ONLY, {"label": "Tipo de manguera"}),
    # Productos (RF-01, RF-02, RF-06, RF-07)
    Row("GET", "/api/v1/products", ANY_ROLE),
    Row("POST", "/api/v1/products", ADMIN_WAREHOUSE, {"category_id": "{category_id}", "name": "X"}),
    Row("GET", "/api/v1/products/{product_id}", ANY_ROLE),
    Row("PATCH", "/api/v1/products/{product_id}", ADMIN_WAREHOUSE, {"description": "Otra"}),
    Row("POST", "/api/v1/products/{product_id}/photos", ADMIN_WAREHOUSE, {}),
    Row("DELETE", "/api/v1/products/{product_id}/photos/{photo_id}", ADMIN_WAREHOUSE),
    Row(
        "PUT",
        "/api/v1/products/{product_id}/photos/order",
        ADMIN_WAREHOUSE,
        {"photo_ids": ["{photo_id}"]},
    ),
    # Precio, costo y publicación (RF-01, RF-07, RN-09)
    Row("PUT", "/api/v1/products/{product_id}/price", ADMIN_ONLY, {"sale_price_usd": "10.00"}),
    Row("GET", "/api/v1/products/{product_id}/prices", ADMIN_ONLY),
    Row("PUT", "/api/v1/products/{product_id}/initial-cost", ADMIN_ONLY, {"avg_cost_usd": "1"}),
    Row("PUT", "/api/v1/products/{product_id}/publication", ADMIN_ONLY, {"is_published": False}),
    # Kardex y ajustes (RF-08 a RF-10, RN-19)
    Row("GET", "/api/v1/products/{product_id}/movements", ADMIN_WAREHOUSE),
    Row(
        "POST",
        "/api/v1/inventory/adjustments",
        ADMIN_WAREHOUSE,
        {"product_id": "{product_id}", "quantity_delta": "1", "reason": "correction"},
    ),
    Row("GET", "/api/v1/inventory/adjustment-requests", ADMIN_WAREHOUSE),
    Row("POST", "/api/v1/inventory/adjustment-requests/{request_id}/approve", ADMIN_ONLY),
    Row(
        "POST",
        "/api/v1/inventory/adjustment-requests/{request_id}/reject",
        ADMIN_ONLY,
        {"reason": "No corresponde"},
    ),
    Row("POST", "/api/v1/inventory/adjustment-requests/{request_id}/withdraw", WAREHOUSE_ONLY),
    # Stock bajo y resumen del inicio (RF-11)
    Row("GET", "/api/v1/inventory/low-stock", ADMIN_WAREHOUSE),
    Row("GET", "/api/v1/inventory/summary", ADMIN_WAREHOUSE),
    # Conteos físicos (RF-12, RN-19)
    Row("GET", "/api/v1/stock-counts", ADMIN_WAREHOUSE),
    Row(
        "POST",
        "/api/v1/stock-counts",
        ADMIN_WAREHOUSE,
        {"scope": {"type": "products", "ids": ["{other_product_id}"]}},
    ),
    Row("GET", "/api/v1/stock-counts/{count_id}", ADMIN_WAREHOUSE),
    Row(
        "PUT",
        "/api/v1/stock-counts/{count_id}/lines/{line_id}",
        ADMIN_WAREHOUSE,
        {"counted_quantity": "3"},
    ),
    Row("POST", "/api/v1/stock-counts/{count_id}/ready", ADMIN_WAREHOUSE),
    Row("POST", "/api/v1/stock-counts/{count_id}/reopen", ADMIN_ONLY),
    Row(
        "POST",
        "/api/v1/stock-counts/{count_id}/apply",
        ADMIN_ONLY,
        {"acknowledge_uncounted": True},
    ),
    Row("POST", "/api/v1/stock-counts/{count_id}/cancel", ADMIN_WAREHOUSE, {"reason": "x"}),
    # Proveedores (RF-13)
    Row("GET", "/api/v1/suppliers", ADMIN_WAREHOUSE),
    Row("POST", "/api/v1/suppliers", ADMIN_WAREHOUSE, {"name": "Proveedor nuevo"}),
    Row("GET", "/api/v1/suppliers/{supplier_id}", ADMIN_WAREHOUSE),
    Row("PATCH", "/api/v1/suppliers/{supplier_id}", ADMIN_WAREHOUSE, {"notes": "x"}),
    # Compras (RF-14 a RF-16, RN-14, RN-20)
    Row("GET", "/api/v1/purchases", ADMIN_WAREHOUSE),
    Row("POST", "/api/v1/purchases", ADMIN_WAREHOUSE, PURCHASE_BODY),
    Row("GET", "/api/v1/purchases/{draft_id}", ADMIN_WAREHOUSE),
    Row("PUT", "/api/v1/purchases/{draft_id}", ADMIN_WAREHOUSE, PURCHASE_BODY),
    Row("DELETE", "/api/v1/purchases/{draft_id}", ADMIN_WAREHOUSE),
    Row(
        "POST",
        "/api/v1/purchases/{draft_id}/confirm",
        ADMIN_WAREHOUSE,
        {"updated_at": "{draft_updated_at}"},
    ),
    Row("GET", "/api/v1/purchases/{confirmed_id}/void-preview", ADMIN_ONLY),
    Row(
        "POST", "/api/v1/purchases/{confirmed_id}/void", ADMIN_ONLY, {"reason": "Motivo de prueba"}
    ),
    # Tasa BCV (RF-17, RN-15)
    Row("GET", "/api/v1/exchange-rates", ADMIN_ONLY),
    Row(
        "POST", "/api/v1/exchange-rates", ADMIN_ONLY, {"business_date": "{yesterday}", "rate": "36"}
    ),
    Row("PUT", "/api/v1/exchange-rates/{today}", ADMIN_ONLY, {"rate": "37"}),
    Row("GET", "/api/v1/exchange-rates/applicable?date={today}", ADMIN_WAREHOUSE),
    # Gastos frecuentes (RF-14/FR-032)
    Row("GET", "/api/v1/charge-templates", ADMIN_WAREHOUSE),
    Row(
        "POST", "/api/v1/charge-templates", ADMIN_ONLY, {"name": "Gasto", "charge_type": "percent"}
    ),
    Row("PATCH", "/api/v1/charge-templates/{template_id}", ADMIN_ONLY, {"name": "Otro"}),
    # Alertas (RN-14)
    Row("GET", "/api/v1/alerts", ADMIN_ONLY),
    Row("POST", "/api/v1/alerts/{alert_id}/resolve", ADMIN_ONLY),
]


@pytest.fixture
def actor_headers(
    make_user,
    auth_headers,
    make_product,
    give_stock,
    category_id,
    db,
    photo_dir,
    make_supplier,
    make_rate,
    make_charge_template,
    make_purchase,
):
    """Crea los usuarios de cada actor y los datos de las rutas, y devuelve el encabezado
    del pedido."""
    target = make_user(Role.SELLER, username="objetivo")
    users = {
        ADMIN: make_user(Role.ADMIN, username="actor_admin"),
        SELLER: make_user(Role.SELLER, username="actor_seller"),
        WAREHOUSE: make_user(Role.WAREHOUSE, username="actor_warehouse"),
        TEMPORARY: make_user(Role.ADMIN, username="temporal", must_change_password=True),
    }
    product = make_product("FRT")
    give_stock(product, "5")
    photo = ProductPhoto(
        product_id=product.id,
        storage_path=f"products/{product.id}/foto.webp",
        width=10,
        height=10,
        size_bytes=100,
        sort_order=0,
    )
    # Solicitud pendiente del mismo Almacén que actúa, para que pueda retirarla.
    request = AdjustmentRequest(
        product_id=product.id,
        quantity_delta=Decimal("-1"),
        adjustment_reason="loss",
        status="pending",
        requested_by=users[WAREHOUSE].id,
        requested_at=utcnow(),
    )
    db.add_all([photo, request])
    db.commit()
    # Conteo abierto con una línea, y otro producto libre para abrir uno nuevo.
    other = make_product("FRT")
    count = StockCount(
        status="open",
        scope={"type": "products", "ids": [str(product.id)]},
        started_by=users[WAREHOUSE].id,
        started_at=utcnow(),
    )
    db.add(count)
    db.flush()
    line = StockCountLine(stock_count_id=count.id, product_id=product.id, is_open=True)
    db.add(line)
    db.commit()

    # Compras, tasa, gasto frecuente y alerta para las rutas de la etapa 1.2.
    supplier = make_supplier("Proveedor de la matriz")
    today = business_date(utcnow())
    make_rate(today, "36.5")
    admin_headers = auth_headers(users[ADMIN], DEFAULT_PASSWORD)
    draft = make_purchase(admin_headers, supplier, [(other, "1", "1")])
    confirmed = make_purchase(admin_headers, supplier, [(other, "1", "1")], confirm=True)
    alert = Alert(
        type="purchase_void_cost",
        entity_type="purchase",
        entity_id=uuid.UUID(confirmed["id"]),
        details={},
        created_at=utcnow(),
    )
    db.add(alert)
    db.commit()
    purchase_ids = {
        "supplier_id": str(supplier.id),
        "today": today.isoformat(),
        "yesterday": (today - timedelta(days=1)).isoformat(),
        "draft_id": draft["id"],
        "draft_updated_at": draft["updated_at"],
        "confirmed_id": confirmed["id"],
        "template_id": str(make_charge_template("Comisión", "percent", "10").id),
        "alert_id": str(alert.id),
    }

    def headers_for(actor: str) -> dict[str, str]:
        if actor == ANONYMOUS:
            return {}
        return auth_headers(users[actor], DEFAULT_PASSWORD)

    headers_for.ids = {  # type: ignore[attr-defined]
        "user_id": str(target.id),
        "product_id": str(product.id),
        "photo_id": str(photo.id),
        "request_id": str(request.id),
        "count_id": str(count.id),
        "line_id": str(line.id),
        "other_product_id": str(other.id),
        **purchase_ids,
        "category_id": str(category_id("FRT")),
        "unit_id": str(db.scalar(select(Unit.id).where(Unit.code == "u"))),
        "attribute_id": str(
            db.scalar(select(AttributeDefinition.id).where(AttributeDefinition.key == "hose_type"))
        ),
    }
    return headers_for


def _fill(value: Any, ids: dict[str, str]) -> Any:
    """Reemplaza los marcadores {nombre} de rutas y cuerpos por los datos creados."""
    if isinstance(value, str):
        return value.format(**ids)
    if isinstance(value, dict):
        return {key: _fill(item, ids) for key, item in value.items()}
    if isinstance(value, list):
        return [_fill(item, ids) for item in value]
    return value


@pytest.mark.parametrize("actor", sorted(EVERYONE))
@pytest.mark.parametrize("row", MATRIX, ids=lambda row: row.id)
def test_matriz_de_permisos(client, actor_headers, row: Row, actor: str) -> None:
    headers = actor_headers(actor)
    path = _fill(row.path, actor_headers.ids)
    kwargs: dict[str, Any] = {"headers": headers}
    if row.body is not None:
        kwargs["json"] = _fill(row.body, actor_headers.ids)

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
