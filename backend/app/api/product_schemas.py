"""Esquemas de respuesta de productos según el rol (principio IV, research R6).

Cada rol recibe un esquema propio y los campos prohibidos no existen en él, en lugar de
filtrarse después (arquitectura §4.4):

- `ProductWarehouse` (Almacén): sin precio de venta ni costo.
- `ProductSeller` (Vendedor): con precio de venta, sin costo.
- `ProductAdmin` (Admin): con precio y costo.

Los decimales viajan como cadenas (ADR-0004); las cantidades, con los decimales de su
unidad.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.db.models import Category, Product, ProductPhoto, Unit
from app.domain.roles import Role
from app.domain.units import format_quantity
from app.services.photo_storage import get_photo_storage


class CategoryRef(BaseModel):
    id: uuid.UUID
    name: str
    sku_prefix: str


class UnitRef(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    decimals: int


class PhotoOut(BaseModel):
    id: uuid.UUID
    url: str
    sort_order: int
    width: int
    height: int


class UserRef(BaseModel):
    id: uuid.UUID
    full_name: str


class ProductWarehouse(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    description: str
    category: CategoryRef
    unit: UnitRef
    attributes: dict[str, str]
    stock: str
    min_stock: str
    is_low_stock: bool
    is_active: bool
    is_published: bool
    has_movements: bool
    photos: list[PhotoOut]
    updated_at: datetime


class ProductSeller(ProductWarehouse):
    sale_price_usd: str | None


class ProductAdmin(ProductSeller):
    avg_cost_usd: str | None
    cost_locked: bool


ProductOut = ProductAdmin | ProductSeller | ProductWarehouse


def decimal_str(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def category_ref(category: Category) -> CategoryRef:
    return CategoryRef(id=category.id, name=category.name, sku_prefix=category.sku_prefix)


def unit_ref(unit: Unit) -> UnitRef:
    return UnitRef(id=unit.id, code=unit.code, name=unit.name, decimals=unit.decimals)


def photo_out(photo: ProductPhoto) -> PhotoOut:
    return PhotoOut(
        id=photo.id,
        url=get_photo_storage().public_url(photo.storage_path),
        sort_order=photo.sort_order,
        width=photo.width,
        height=photo.height,
    )


def is_low_stock(product: Product) -> bool:
    """Stock bajo: producto activo con stock menor o igual al mínimo (RF-11/FR-023)."""
    return product.is_active and product.stock <= product.min_stock


def product_for_role(
    role: Role,
    product: Product,
    *,
    category: Category,
    unit: Unit,
    photos: list[ProductPhoto],
) -> ProductOut:
    common = {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "category": category_ref(category),
        "unit": unit_ref(unit),
        "attributes": product.attributes,
        "stock": format_quantity(product.stock, unit.decimals),
        "min_stock": format_quantity(product.min_stock, unit.decimals),
        "is_low_stock": is_low_stock(product),
        "is_active": product.is_active,
        "is_published": product.is_published,
        "has_movements": product.has_movements,
        "photos": [photo_out(photo) for photo in photos],
        "updated_at": product.updated_at,
    }
    if role == Role.WAREHOUSE:
        return ProductWarehouse(**common)
    if role == Role.SELLER:
        return ProductSeller(**common, sale_price_usd=decimal_str(product.sale_price_usd))
    return ProductAdmin(
        **common,
        sale_price_usd=decimal_str(product.sale_price_usd),
        avg_cost_usd=decimal_str(product.avg_cost_usd),
        cost_locked=product.cost_locked,
    )
