"""Endpoints de productos (RF-01, RF-02, RF-06, RF-07; FR-001 a FR-015, FR-032, FR-033).

Contrato: specs/002-productos-inventario/contracts/api.md. Las respuestas usan el
esquema del rol leído de la base (principio IV, research R6). Los esquemas de entrada
rechazan campos desconocidos: el SKU, el precio, el costo y la publicación no se pueden
enviar aquí (FR-003, FR-009).
"""

import uuid
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.api.deps import CurrentUser, DbSession, require_authenticated, require_roles
from app.api.product_schemas import (
    ProductOut,
    StockMovementOut,
    movement_for_role,
    product_for_role,
)
from app.core.config import get_settings
from app.db.models import Product, Unit
from app.domain.roles import Role
from app.services import inventory as inventory_service
from app.services import photos as photos_service
from app.services import products as products_service
from app.services.users import users_by_id

router = APIRouter(prefix="/products", tags=["products"])

AnyUser = Annotated[CurrentUser, Depends(require_authenticated())]
Editor = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.WAREHOUSE))]

ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
AttributeValues = dict[str, str | int | None]
MovementType = Literal["purchase", "sale", "sale_void", "purchase_void", "adjustment"]
ATTRIBUTE_PREFIX = "attr."


class CreateProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: uuid.UUID
    unit_id: uuid.UUID | None = None
    name: ProductName
    description: Description = ""
    attributes: AttributeValues = {}
    min_stock: Decimal = Decimal("0")


class UpdateProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ProductName | None = None
    description: Description | None = None
    attributes: AttributeValues | None = None
    min_stock: Decimal | None = None
    category_id: uuid.UUID | None = None
    unit_id: uuid.UUID | None = None
    is_active: bool | None = None
    # El `updated_at` que leyó la pantalla, para avisar si editó sobre datos viejos (R15).
    updated_at: datetime | None = None


class ReorderPhotosRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    photo_ids: list[uuid.UUID]


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int


def products_out(
    db: DbSession, role: Role, products: list[Product], warnings: Iterable[str] = ()
) -> list[ProductOut]:
    views = products_service.build_views(db, products)
    result = []
    for view in views:
        out = product_for_role(
            role, view.product, category=view.category, unit=view.unit, photos=view.photos
        )
        out.warnings = list(warnings)
        result.append(out)
    return result


def product_out(
    db: DbSession, current: CurrentUser, product: Product, warnings: Iterable[str] = ()
) -> ProductOut:
    db.refresh(product)
    return products_out(db, current.role, [product], warnings)[0]


@router.get("")
def list_products(
    request: Request,
    current: AnyUser,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=200)] = None,
    category_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    is_published: bool | None = None,
    low_stock: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ProductPage:
    """Búsqueda (FR-032, FR-033). Los filtros por atributo llegan como `attr.<clave>=<valor>`
    y solo se admiten las claves marcadas como filtrables."""
    attributes = {
        key.removeprefix(ATTRIBUTE_PREFIX): value
        for key, value in request.query_params.items()
        if key.startswith(ATTRIBUTE_PREFIX)
    }
    if attributes:
        allowed = products_service.filterable_keys(db)
        invalid = {
            f"{ATTRIBUTE_PREFIX}{key}": "No se puede filtrar por este atributo"
            for key in attributes
            if key not in allowed
        }
        if invalid:
            raise products_service.validation_error(invalid)
    rows, total = products_service.list_products(
        db,
        role=current.role,
        q=q,
        category_id=category_id,
        attributes=attributes,
        is_active=is_active,
        is_published=is_published,
        low_stock=low_stock,
        page=page,
        page_size=page_size,
    )
    return ProductPage(
        items=products_out(db, current.role, rows), total=total, page=page, page_size=page_size
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_product(body: CreateProductRequest, current: Editor, db: DbSession) -> ProductOut:
    product, warnings = products_service.create_product(
        db,
        actor=current.user,
        category_id=body.category_id,
        unit_id=body.unit_id,
        name=body.name,
        description=body.description,
        attributes=body.attributes,
        min_stock=body.min_stock,
    )
    return product_out(db, current, product, warnings)


@router.get("/{product_id}")
def get_product(product_id: uuid.UUID, current: AnyUser, db: DbSession) -> ProductOut:
    product = products_service.get_product(db, product_id, role=current.role)
    return product_out(db, current, product)


@router.patch("/{product_id}")
def update_product(
    product_id: uuid.UUID, body: UpdateProductRequest, current: Editor, db: DbSession
) -> ProductOut:
    changes = {
        key: value
        for key, value in body.model_dump(exclude_unset=True, exclude={"updated_at"}).items()
        if value is not None
    }
    product, warnings = products_service.update_product(
        db, actor=current.user, product_id=product_id, changes=changes, updated_at=body.updated_at
    )
    return product_out(db, current, product, warnings)


@router.post("/{product_id}/photos", status_code=status.HTTP_201_CREATED)
def add_photo(
    product_id: uuid.UUID, file: UploadFile, current: Editor, db: DbSession
) -> ProductOut:
    # Se lee como máximo un byte más del límite: basta para saber si lo supera.
    data = file.file.read(get_settings().photo_max_upload_bytes + 1)
    product = photos_service.add_photo(db, actor=current.user, product_id=product_id, data=data)
    return product_out(db, current, product)


@router.delete("/{product_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_photo(
    product_id: uuid.UUID, photo_id: uuid.UUID, current: Editor, db: DbSession
) -> None:
    photos_service.remove_photo(db, actor=current.user, product_id=product_id, photo_id=photo_id)


@router.put("/{product_id}/photos/order")
def reorder_photos(
    product_id: uuid.UUID, body: ReorderPhotosRequest, current: Editor, db: DbSession
) -> ProductOut:
    product = photos_service.reorder_photos(
        db, actor=current.user, product_id=product_id, photo_ids=body.photo_ids
    )
    return product_out(db, current, product)


class MovementPage(BaseModel):
    items: list[StockMovementOut]
    total: int
    page: int
    page_size: int


@router.get("/{product_id}/movements")
def list_movements(
    product_id: uuid.UUID,
    current: Editor,
    db: DbSession,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    type: MovementType | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> MovementPage:
    """Kardex del producto para Admin y Almacén; el Vendedor solo ve el stock (FR-022)."""
    rows, total = inventory_service.list_movements(
        db,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        type=type,
        page=page,
        page_size=page_size,
    )
    product = db.get(Product, product_id)
    unit = db.get(Unit, product.unit_id)
    requesters = inventory_service.requesters_of(db, rows)
    users = users_by_id(db, {movement.created_by for movement in rows} | set(requesters.values()))
    items = [
        movement_for_role(
            current.role, movement, unit=unit, users=users, requested_by=requesters.get(movement.id)
        )
        for movement in rows
    ]
    return MovementPage(items=items, total=total, page=page, page_size=page_size)
