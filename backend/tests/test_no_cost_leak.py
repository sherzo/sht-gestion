"""Ninguna respuesta a Vendedor o Almacén contiene costos o márgenes, y ninguna al Almacén
contiene el precio de venta (principio IV, FR-014, SC-004, research R6).

Dirigida por datos: cada historia agrega a LEAK_CASES los endpoints que lee o responde
con datos de productos. Por cada caso y por cada rol que puede usarlo se recorre el JSON
de la respuesta en todos sus niveles y se buscan claves prohibidas.
"""

import io
from dataclasses import dataclass, field
from typing import Any

import pytest
from PIL import Image

from app.domain.roles import Role

pytestmark = pytest.mark.db

SELLER = Role.SELLER
WAREHOUSE = Role.WAREHOUSE


@dataclass(frozen=True)
class LeakCase:
    method: str
    # Ruta con marcadores que llena el contexto: {product_id}, {request_id}, {count_id}…
    path: str
    roles: tuple[Role, ...] = (SELLER, WAREHOUSE)
    body: dict[str, Any] | None = field(default=None)
    # Sube una foto en `multipart/form-data` en lugar de enviar JSON.
    photo: bool = False

    @property
    def id(self) -> str:
        return f"{self.method} {self.path}"


LEAK_CASES: list[LeakCase] = []


def forbidden_keys(data: Any, role: Role, path: str = "") -> list[str]:
    """Claves prohibidas para el rol, en cualquier nivel del JSON."""
    found: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            name = str(key).lower()
            if "cost" in name or "margin" in name or (role == WAREHOUSE and "price" in name):
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


@pytest.fixture
def leak_context(make_user, auth_headers, make_product, give_stock) -> dict[str, Any]:
    """Datos con precio y costo definidos para que una fuga se note."""
    product = make_product("MAN", sale_price="12.50", avg_cost="7.250000", min_stock="50")
    give_stock(product, "10")
    headers = {
        SELLER: auth_headers(make_user(SELLER, username="vendedor_fuga")),
        WAREHOUSE: auth_headers(make_user(WAREHOUSE, username="almacen_fuga")),
    }
    return {"headers": headers, "product_id": str(product.id), "product": product}


@pytest.mark.parametrize("case", LEAK_CASES, ids=lambda case: case.id)
def test_sin_costos_para_vendedor_ni_precio_para_almacen(
    client, leak_context, case: LeakCase
) -> None:
    for role in case.roles:
        values = {key: value for key, value in leak_context.items() if isinstance(value, str)}
        path = case.path.format(**values)
        kwargs: dict[str, Any] = {"headers": leak_context["headers"][role]}
        if case.photo:
            kwargs["files"] = {"file": ("foto.jpg", jpeg_bytes(), "image/jpeg")}
        elif case.body is not None:
            kwargs["json"] = case.body
        response = client.request(case.method, path, **kwargs)
        assert response.status_code < 300, f"{role} en {case.id}: {response.text}"
        leaks = forbidden_keys(response.json(), role) if response.content else []
        assert not leaks, f"{role} recibe {leaks} en {case.id}"
