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

from pydantic import BaseModel, ConfigDict

from app.db.models import AppUser, Category, Product, ProductPhoto, StockMovement, Unit
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
    # Sin campos extra: un producto de Admin nunca se confunde con el de otro rol al
    # validar la respuesta contra la unión de esquemas.
    model_config = ConfigDict(extra="forbid")

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
    # Avisos que no bloquean: duplicate_name, has_stock, stale_data (research R10, R15).
    warnings: list[str] = []


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


# --- Kardex (FR-017, FR-022): el Almacén no recibe los costos del movimiento ---------


class StockMovementWarehouse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    occurred_at: datetime
    type: str
    quantity_delta: str
    balance_after: str
    adjustment_reason: str | None
    note: str | None
    reference_type: str | None
    reference_id: uuid.UUID | None
    created_by: UserRef | None
    # Quién pidió la salida, si el movimiento viene de una solicitud aprobada (RN-19).
    requested_by: UserRef | None


class StockMovementAdmin(StockMovementWarehouse):
    cost_before_usd: str | None
    cost_after_usd: str | None


StockMovementOut = StockMovementAdmin | StockMovementWarehouse


def user_ref(user: AppUser | None) -> UserRef | None:
    return None if user is None else UserRef(id=user.id, full_name=user.full_name)


def movement_for_role(
    role: Role,
    movement: StockMovement,
    *,
    unit: Unit,
    users: dict[uuid.UUID, AppUser],
    requested_by: uuid.UUID | None = None,
) -> StockMovementOut:
    common = {
        "id": movement.id,
        "occurred_at": movement.occurred_at,
        "type": movement.type,
        "quantity_delta": format_quantity(movement.quantity_delta, unit.decimals),
        "balance_after": format_quantity(movement.balance_after, unit.decimals),
        "adjustment_reason": movement.adjustment_reason,
        "note": movement.note,
        "reference_type": movement.reference_type,
        "reference_id": movement.reference_id,
        "created_by": user_ref(users.get(movement.created_by)) if movement.created_by else None,
        "requested_by": user_ref(users.get(requested_by)) if requested_by else None,
    }
    if role == Role.ADMIN:
        return StockMovementAdmin(
            **common,
            cost_before_usd=decimal_str(movement.cost_before_usd),
            cost_after_usd=decimal_str(movement.cost_after_usd),
        )
    return StockMovementWarehouse(**common)
