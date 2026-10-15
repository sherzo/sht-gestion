"""Ninguna respuesta a Vendedor o Almacén contiene costos o márgenes, y ninguna al Almacén
contiene el precio de venta (principio IV, FR-014, SC-004, research R6).

Dirigida por datos: cada historia agrega a LEAK_CASES los endpoints que lee o responde
con datos de productos. Por cada caso y por cada rol que puede usarlo se recorre el JSON
de la respuesta en todos sus niveles y se buscan claves prohibidas.
"""

import io
import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest
from PIL import Image

from app.core.clock import utcnow
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.conftest import operation

pytestmark = pytest.mark.db

SELLER = Role.SELLER
WAREHOUSE = Role.WAREHOUSE


# Compra con gastos, para que una fuga en las líneas o en los gastos se note.
PURCHASE_BODY = {
    "supplier_id": "{supplier_id}",
    "purchase_date": "{today}",
    "currency": "USD",
    "items": [{"product_id": "{product_id}", "quantity": "2", "unit_cost": "3"}],
    "charges": [{"description": "Envío", "charge_type": "fixed", "amount": "1", "currency": "USD"}],
}


def fill(value: Any, values: dict[str, str]) -> Any:
    if isinstance(value, str):
        return value.format(**values)
    if isinstance(value, dict):
        return {key: fill(item, values) for key, item in value.items()}
    if isinstance(value, list):
        return [fill(item, values) for item in value]
    return value


@dataclass(frozen=True)
class LeakCase:
    method: str
    # Ruta con marcadores que llena el contexto: {product_id}, {request_id}, {count_id}…
    path: str
    roles: tuple[Role, ...] = (SELLER, WAREHOUSE)
    body: dict[str, Any] | None = field(default=None)
    # Sube una foto en `multipart/form-data` en lugar de enviar JSON.
    photo: bool = False
    # Operación de mostrador: el cuerpo lo arma la función del contexto con ese nombre y se
    # envía el token del equipo (etapa 1.3).
    counter_body: str | None = None

    @property
    def id(self) -> str:
        return f"{self.method} {self.path} {self.body or ''}"


LEAK_CASES: list[LeakCase] = [
    # Productos (US1)
    LeakCase("GET", "/api/v1/products"),
    LeakCase("GET", "/api/v1/products/{product_id}"),
    LeakCase(
        "POST",
        "/api/v1/products",
        (WAREHOUSE,),
        body={"category_id": "{frt_category_id}", "name": "Teflón"},
    ),
    LeakCase("PATCH", "/api/v1/products/{product_id}", (WAREHOUSE,), body={"description": "x"}),
    LeakCase("POST", "/api/v1/products/{product_id}/photos", (WAREHOUSE,), photo=True),
    LeakCase(
        "PUT",
        "/api/v1/products/{product_id}/photos/order",
        (WAREHOUSE,),
        body={"photo_ids": []},
    ),
    # Kardex y ajustes (US2)
    LeakCase("GET", "/api/v1/products/{product_id}/movements", (WAREHOUSE,)),
    LeakCase("GET", "/api/v1/inventory/adjustment-requests", (WAREHOUSE,)),
    LeakCase(
        "POST",
        "/api/v1/inventory/adjustments",
        (WAREHOUSE,),
        body={"product_id": "{product_id}", "quantity_delta": "1", "reason": "correction"},
    ),
    LeakCase(
        "POST",
        "/api/v1/inventory/adjustments",
        (WAREHOUSE,),
        body={"product_id": "{product_id}", "quantity_delta": "-1", "reason": "loss"},
    ),
    # Ficha de un producto publicado con precio y costo definidos (US4)
    LeakCase("GET", "/api/v1/products/{published_id}"),
    # Búsqueda y stock bajo (US3)
    LeakCase("GET", "/api/v1/products?q=producto&low_stock=true"),
    LeakCase("GET", "/api/v1/inventory/low-stock", (WAREHOUSE,)),
    LeakCase("GET", "/api/v1/inventory/summary", (WAREHOUSE,)),
    # Venta por la cola de salida (etapa 1.3, US2): el Vendedor no recibe costo ni margen.
    LeakCase("POST", "/api/v1/sync/operations", (SELLER,), counter_body="sale_operation"),
    LeakCase("GET", "/api/v1/customers?q=taller", (SELLER,)),
    # Consulta de ventas (US7)
    LeakCase("GET", "/api/v1/sales", (SELLER,)),
    LeakCase("GET", "/api/v1/sales/{sale_id}", (SELLER,)),
    # Conteos físicos (US5): el Almacén tampoco recibe el stock esperado ni la diferencia
    LeakCase("GET", "/api/v1/stock-counts", (WAREHOUSE,)),
    LeakCase("GET", "/api/v1/stock-counts/{count_id}", (WAREHOUSE,)),
    LeakCase(
        "PUT",
        "/api/v1/stock-counts/{count_id}/lines/{line_id}",
        (WAREHOUSE,),
        body={"counted_quantity": "7"},
    ),
    # Proveedores y compras (etapa 1.2): el Almacén recibe los costos de factura, nunca el
    # costo promedio ni el costo antes y después (FR-022, R7); el Vendedor no tiene acceso.
    LeakCase("GET", "/api/v1/suppliers", (WAREHOUSE,)),
    LeakCase("GET", "/api/v1/purchases", (WAREHOUSE,)),
    LeakCase("GET", "/api/v1/purchases/{purchase_id}", (WAREHOUSE,)),
    LeakCase("POST", "/api/v1/purchases", (WAREHOUSE,), body=PURCHASE_BODY),
    LeakCase("PUT", "/api/v1/purchases/{draft_id}", (WAREHOUSE,), body=PURCHASE_BODY),
    LeakCase(
        "POST",
        "/api/v1/purchases/{draft_id}/confirm",
        (WAREHOUSE,),
        body={"updated_at": "{draft_updated_at}"},
    ),
    LeakCase("GET", "/api/v1/charge-templates", (WAREHOUSE,)),
    LeakCase("GET", "/api/v1/exchange-rates/applicable?date={today}", (WAREHOUSE,)),
]

# Claves que el Almacén no recibe en un conteo, porque cuenta a ciegas (FR-025).
BLIND_KEYS = ("expected", "difference")

# Excepción del principio IV (constitución 1.2.0, FR-009, FR-022): el Almacén recibe los
# costos de factura de las compras que registra, solo dentro de las líneas de una compra
# (objetos con `landed_unit_cost_usd`). El costo promedio, el costo antes y después de
# una compra y los márgenes siguen prohibidos en cualquier parte.
PURCHASE_ITEM_KEYS = frozenset(
    {
        "unit_cost_ves",
        "unit_cost_usd",
        "line_total_usd",
        "line_total_ves",
        "allocated_charges_usd",
        "landed_unit_cost_usd",
    }
)


def _allowed_purchase_cost(data: dict, name: str, role: Role) -> bool:
    return role == WAREHOUSE and name in PURCHASE_ITEM_KEYS and "landed_unit_cost_usd" in data


def forbidden_keys(data: Any, role: Role, path: str = "") -> list[str]:
    """Claves prohibidas para el rol, en cualquier nivel del JSON."""
    found: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            name = str(key).lower()
            warehouse_only = role == WAREHOUSE and (
                "price" in name or any(blind in name for blind in BLIND_KEYS)
            )
            costly = ("cost" in name and not _allowed_purchase_cost(data, name, role)) or (
                "margin" in name
            )
            if costly or warehouse_only:
                found.append(f"{path}{key}")
            found.extend(forbidden_keys(value, role, f"{path}{key}."))
    elif isinstance(data, list):
        for item in data:
            found.extend(forbidden_keys(item, role, path))
    return found


def jpeg_bytes(size: tuple[int, int] = (64, 48)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_detector_de_claves_prohibidas() -> None:
    """La prueba detecta claves anidadas y distingue al Vendedor del Almacén."""
    data = {"items": [{"sale_price_usd": "1.00", "detail": {"avg_cost_usd": "0.5"}}]}
    assert forbidden_keys(data, SELLER) == ["items.detail.avg_cost_usd"]
    assert forbidden_keys(data, WAREHOUSE) == ["items.sale_price_usd", "items.detail.avg_cost_usd"]


def test_detector_permite_al_almacen_solo_costos_de_factura() -> None:
    """Excepción del principio IV: costos de factura solo en las líneas de una compra."""
    line = {"unit_cost_usd": "10.000000", "landed_unit_cost_usd": "14.500000"}
    purchase = {"items": [line], "cost_changes": [], "unit_cost_usd": "1"}
    assert forbidden_keys(purchase, WAREHOUSE) == ["cost_changes", "unit_cost_usd"]
    assert forbidden_keys(purchase, SELLER) == [
        "items.unit_cost_usd",
        "items.landed_unit_cost_usd",
        "cost_changes",
        "unit_cost_usd",
    ]
    assert forbidden_keys({"items": [{**line, "avg_cost_usd": "1"}]}, WAREHOUSE) == [
        "items.avg_cost_usd"
    ]


@pytest.fixture
def leak_context(
    client,
    make_user,
    auth_headers,
    make_product,
    give_stock,
    category_id,
    photo_dir,
    make_supplier,
    make_rate,
    make_purchase,
    make_device,
    open_cash_session,
) -> dict[str, Any]:
    """Datos con precio y costo definidos para que una fuga se note."""
    product = make_product("MAN", sale_price="12.50", avg_cost="7.250000", min_stock="50")
    give_stock(product, "10")
    counted = make_product("FER")
    give_stock(counted, "4")
    headers_warehouse_user = make_user(WAREHOUSE, username="almacen_fuga")
    count = client.post(
        "/api/v1/stock-counts",
        json={"scope": {"type": "products", "ids": [str(counted.id)]}},
        headers=auth_headers(make_user(Role.ADMIN, username="admin_fuga")),
    ).json()
    published = make_product(
        "CON", sale_price="4.00", avg_cost="1.500000", min_stock="2", is_published=True
    )
    headers = {
        SELLER: auth_headers(make_user(SELLER, username="vendedor_fuga")),
        WAREHOUSE: auth_headers(headers_warehouse_user),
    }
    # Compra confirmada del producto (su kardex lleva costo antes y después) y un borrador.
    supplier = make_supplier("Proveedor de la fuga")
    today = business_date(utcnow())
    make_rate(today, "36.5")
    purchase = make_purchase(
        headers[WAREHOUSE],
        supplier,
        [(product, "2", "3")],
        charges=PURCHASE_BODY["charges"],
        confirm=True,
    )
    draft = make_purchase(headers[WAREHOUSE], supplier, [(product, "1", "3")])
    # Mostrador del Vendedor con caja abierta, para vender el producto con costo.
    _, token = make_device("Mostrador de la fuga")
    session = open_cash_session(headers[SELLER], token)
    seller_id = client.get("/api/v1/auth/me", headers=headers[SELLER]).json()["user"]["id"]

    sequence = iter(range(1, 100))

    def sale_operation() -> dict[str, Any]:
        payload = {
            "id": str(uuid.uuid7()),
            "sequence_number": next(sequence),
            "cash_session_id": session["id"],
            "seller_id": seller_id,
            "occurred_at": utcnow().isoformat(),
            "exchange_rate": "36.50000000",
            "exchange_rate_date": today.isoformat(),
            "customer": {"id": str(uuid.uuid7()), "name": "Taller de la fuga"},
            "items": [
                {
                    "id": str(uuid.uuid7()),
                    "product_id": str(product.id),
                    "quantity": "1",
                    "entered_unit": "m",
                    "unit_price_usd": "12.50",
                }
            ],
            "payments": [{"method": "cash_usd", "amount": "12.50"}],
            "change": [],
            "device_total_usd": "12.50",
        }
        return operation("sale.create", payload)

    # Una venta ya registrada del Vendedor, para su consulta y el kardex del Almacén.
    sold = client.post(
        "/api/v1/sync/operations",
        json=sale_operation(),
        headers={**headers[SELLER], "X-Device-Token": token},
    ).json()

    return {
        "sale_id": sold["id"],
        "supplier_id": str(supplier.id),
        "today": today.isoformat(),
        "purchase_id": purchase["id"],
        "draft_id": draft["id"],
        "draft_updated_at": draft["updated_at"],
        "headers": headers,
        "product": product,
        "product_id": str(product.id),
        "published_id": str(published.id),
        "count_id": count["id"],
        "line_id": count["lines"][0]["id"],
        "frt_category_id": str(category_id("FRT")),
        "device_token": token,
        "sale_operation": sale_operation,
    }


@pytest.mark.parametrize("case", LEAK_CASES, ids=lambda case: case.id)
def test_sin_costos_para_vendedor_ni_precio_para_almacen(
    client, leak_context, case: LeakCase
) -> None:
    for role in case.roles:
        values = {key: value for key, value in leak_context.items() if isinstance(value, str)}
        path = case.path.format(**values)
        kwargs: dict[str, Any] = {"headers": leak_context["headers"][role]}
        if case.counter_body is not None:
            kwargs["json"] = leak_context[case.counter_body]()
            kwargs["headers"] = {
                **kwargs["headers"],
                "X-Device-Token": leak_context["device_token"],
            }
        elif case.photo:
            kwargs["files"] = {"file": ("foto.jpg", jpeg_bytes(), "image/jpeg")}
        elif case.body is not None:
            kwargs["json"] = fill(case.body, values)
        response = client.request(case.method, path, **kwargs)
        assert response.status_code < 300, f"{role} en {case.id}: {response.text}"
        leaks = forbidden_keys(response.json(), role) if response.content else []
        assert not leaks, f"{role} recibe {leaks} en {case.id}"
