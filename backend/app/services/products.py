"""Productos: alta con SKU automático, edición, activación y consulta (RF-01, RF-02,
RF-05, RF-07; FR-001 a FR-010; research R1, R10 y R15).

Reglas principales:

- El SKU se reserva bloqueando la fila de la categoría (R1): nunca se repite ni se
  reutiliza, aun con altas simultáneas.
- Categoría y unidad solo cambian mientras el producto no tenga movimientos (FR-004).
- Las mangueras (categoría con unidad fija) siempre van por metro (FR-005).
- Los productos no se borran: se desactivan, y desactivar los saca del catálogo (FR-007).
- El precio, el costo y la publicación tienen sus propias operaciones, solo del Admin.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError
from app.db.models import AppUser, AttributeDefinition, Category, Product, ProductPhoto, Unit
from app.domain.attributes import AttributeSpec, AttributeValidationError, validate_attributes
from app.domain.roles import Role
from app.domain.search import build_search_text
from app.domain.sku import format_sku
from app.domain.units import format_quantity, validate_quantity
from app.services.audit import record_audit
from app.services.inventory import lock_product, product_not_found

# Campos descriptivos que registra `product.updated` con su valor anterior y nuevo.
DESCRIPTIVE_FIELDS = ("name", "description", "attributes", "min_stock", "unit")


def validation_error(fields: dict[str, str]) -> ApiError:
    return ApiError(422, "validation_error", "Hay datos inválidos", fields=fields)


@dataclass(frozen=True)
class ProductView:
    """Producto con lo necesario para responderlo (categoría, unidad y fotos)."""

    product: Product
    category: Category
    unit: Unit
    photos: list[ProductPhoto]


# --- Lectura -----------------------------------------------------------------------


def active_photos(db: Session, product_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[ProductPhoto]]:
    photos: dict[uuid.UUID, list[ProductPhoto]] = {product_id: [] for product_id in product_ids}
    if not product_ids:
        return photos
    rows = db.scalars(
        select(ProductPhoto)
        .where(ProductPhoto.product_id.in_(product_ids), ProductPhoto.removed_at.is_(None))
        .order_by(ProductPhoto.sort_order, ProductPhoto.created_at)
    )
    for photo in rows:
        photos[photo.product_id].append(photo)
    return photos


def build_views(db: Session, products: list[Product]) -> list[ProductView]:
    categories = {category.id: category for category in db.scalars(select(Category))}
    units = {unit.id: unit for unit in db.scalars(select(Unit))}
    photos = active_photos(db, [product.id for product in products])
    return [
        ProductView(
            product=product,
            category=categories[product.category_id],
            unit=units[product.unit_id],
            photos=photos[product.id],
        )
        for product in products
    ]


def view_of(db: Session, product: Product) -> ProductView:
    db.refresh(product)
    return build_views(db, [product])[0]


def get_product(db: Session, product_id: uuid.UUID, *, role: Role) -> Product:
    product = db.get(Product, product_id)
    # El Vendedor solo ve productos activos (FR-007).
    if product is None or (role == Role.SELLER and not product.is_active):
        raise product_not_found()
    return product


def list_products(
    db: Session,
    *,
    role: Role,
    category_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Product], int]:
    conditions = []
    if role == Role.SELLER:
        conditions.append(Product.is_active.is_(True))
    elif is_active is not None:
        conditions.append(Product.is_active.is_(is_active))
    if category_id is not None:
        conditions.append(Product.category_id == category_id)
    total = db.scalar(select(func.count()).select_from(Product).where(*conditions))
    rows = db.scalars(
        select(Product)
        .where(*conditions)
        .order_by(Product.name, Product.sku)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


# --- Validaciones ------------------------------------------------------------------


def attribute_specs(db: Session, category_id: uuid.UUID) -> list[AttributeSpec]:
    definitions = db.scalars(
        select(AttributeDefinition)
        .where(AttributeDefinition.category_id == category_id)
        .order_by(AttributeDefinition.sort_order)
    )
    return [
        AttributeSpec(
            key=definition.key,
            label=definition.label,
            data_type=definition.data_type,  # type: ignore[arg-type]
            options=definition.options or [],
            is_required=definition.is_required,
            is_active=definition.is_active,
        )
        for definition in definitions
    ]


def _clean_attributes(
    db: Session, category_id: uuid.UUID, values: dict[str, Any], previous: dict[str, Any] | None
) -> dict[str, str]:
    try:
        return validate_attributes(values, attribute_specs(db, category_id), previous)
    except AttributeValidationError as exc:
        raise validation_error(
            {f"attributes.{key}": message for key, message in exc.errors.items()}
        ) from exc


def _resolve_unit(db: Session, category: Category, unit_id: uuid.UUID | None) -> Unit:
    if category.unit_locked or unit_id is None:
        if unit_id is not None and unit_id != category.default_unit_id:
            unit = db.get(Unit, category.default_unit_id)
            raise validation_error(
                {"unit_id": f"Los productos de {category.name} siempre van por {unit.name}"}
            )
        unit = db.get(Unit, category.default_unit_id)
    else:
        unit = db.get(Unit, unit_id)
        if unit is None:
            raise validation_error({"unit_id": "La unidad no existe"})
    if not unit.is_active:
        raise validation_error({"unit_id": "La unidad está desactivada"})
    return unit


def _min_stock(value: Decimal, unit: Unit) -> Decimal:
    try:
        return validate_quantity(value, unit.decimals, allow_zero=True, allow_negative=False)
    except ValueError as exc:
        raise validation_error({"min_stock": str(exc)}) from exc


def _lock_category(db: Session, category_id: uuid.UUID) -> Category:
    category = db.get(Category, category_id, with_for_update=True, populate_existing=True)
    if category is None:
        raise validation_error({"category_id": "La categoría no existe"})
    if not category.is_active:
        raise validation_error({"category_id": "La categoría está desactivada"})
    return category


def _next_sku(category: Category) -> str:
    """Reserva el siguiente correlativo; la categoría debe estar bloqueada (R1)."""
    sku = format_sku(category.sku_prefix, category.next_sku_number)
    category.next_sku_number += 1
    return sku


def _has_duplicate_name(db: Session, product: Product) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(Product)
            .where(
                Product.category_id == product.category_id,
                Product.is_active.is_(True),
                func.lower(Product.name) == product.name.lower(),
                Product.id != product.id,
            )
        )
        > 0
    )


def _search_text(product: Product) -> str:
    return build_search_text(
        product.name, product.description, product.sku, product.attributes.values()
    )


def _snapshot(product: Product, unit: Unit) -> dict[str, Any]:
    return {
        "name": product.name,
        "description": product.description,
        "attributes": dict(product.attributes),
        "min_stock": format_quantity(product.min_stock, unit.decimals),
        "unit": unit.code,
    }


# --- Escritura ---------------------------------------------------------------------


def create_product(
    db: Session,
    *,
    actor: AppUser,
    category_id: uuid.UUID,
    unit_id: uuid.UUID | None,
    name: str,
    description: str,
    attributes: dict[str, Any],
    min_stock: Decimal,
) -> tuple[Product, list[str]]:
    category = _lock_category(db, category_id)
    unit = _resolve_unit(db, category, unit_id)
    cleaned = _clean_attributes(db, category.id, attributes, None)
    minimum = _min_stock(min_stock, unit)
    product = Product(
        sku=_next_sku(category),
        category_id=category.id,
        unit_id=unit.id,
        name=name,
        description=description,
        attributes=cleaned,
        min_stock=minimum,
        stock=Decimal("0"),
        cost_locked=False,
        has_movements=False,
        is_active=True,
        is_published=False,
        created_by=actor.id,
        updated_by=actor.id,
        updated_at=utcnow(),
    )
    product.search_text = _search_text(product)
    db.add(product)
    db.flush()
    warnings = ["duplicate_name"] if _has_duplicate_name(db, product) else []
    record_audit(
        db,
        action="product.created",
        user_id=actor.id,
        entity_type="product",
        entity_id=product.id,
        after={"sku": product.sku, "category": category.sku_prefix, **_snapshot(product, unit)},
        details={"sku": product.sku},
    )
    db.commit()
    return product, warnings


def update_product(
    db: Session,
    *,
    actor: AppUser,
    product_id: uuid.UUID,
    changes: dict[str, Any],
    updated_at: datetime | None = None,
) -> tuple[Product, list[str]]:
    """Aplica solo los campos presentes en `changes` (los que envió la pantalla)."""
    product = lock_product(db, product_id)
    warnings: list[str] = []
    if updated_at is not None and updated_at != product.updated_at:
        # Gana el último que guarda, pero se avisa que había cambios (R15).
        warnings.append("stale_data")

    old_category = db.get(Category, product.category_id)
    old_unit = db.get(Unit, product.unit_id)
    before = _snapshot(product, old_unit)
    old_sku = product.sku

    new_category_id = changes.get("category_id")
    category_changed = new_category_id is not None and new_category_id != product.category_id
    unit_changed = "unit_id" in changes and changes["unit_id"] not in (None, product.unit_id)
    if (category_changed or unit_changed) and product.has_movements:
        raise ApiError(
            409,
            "product_has_movements",
            "El producto ya tiene movimientos: su categoría y su unidad no cambian",
        )

    category = _lock_category(db, new_category_id) if category_changed else old_category
    if category_changed:
        # Al cambiar de categoría se usa la unidad de la nueva, salvo que se indique otra.
        unit = _resolve_unit(db, category, changes.get("unit_id"))
    elif unit_changed:
        unit = _resolve_unit(db, category, changes["unit_id"])
    else:
        unit = old_unit

    if "attributes" in changes or category_changed:
        values = changes.get("attributes", product.attributes)
        previous = None if category_changed else product.attributes
        product.attributes = _clean_attributes(db, category.id, values, previous)
    if "name" in changes:
        product.name = changes["name"]
    if "description" in changes:
        product.description = changes["description"]
    minimum = changes.get("min_stock", product.min_stock)
    product.min_stock = _min_stock(minimum, unit)
    product.unit_id = unit.id
    if category_changed:
        product.category_id = category.id
        product.sku = _next_sku(category)

    product.search_text = _search_text(product)
    product.updated_at = utcnow()
    product.updated_by = actor.id
    db.flush()

    if ("name" in changes or category_changed) and _has_duplicate_name(db, product):
        warnings.append("duplicate_name")

    after = _snapshot(product, unit)
    changed = {key for key in DESCRIPTIVE_FIELDS if before[key] != after[key]}
    if changed:
        record_audit(
            db,
            action="product.updated",
            user_id=actor.id,
            entity_type="product",
            entity_id=product.id,
            before={key: before[key] for key in changed},
            after={key: after[key] for key in changed},
            details={"sku": product.sku},
        )
    if category_changed:
        record_audit(
            db,
            action="product.category_changed",
            user_id=actor.id,
            entity_type="product",
            entity_id=product.id,
            before={"sku": old_sku, "category": old_category.sku_prefix},
            after={"sku": product.sku, "category": category.sku_prefix},
            details={"sku": product.sku},
        )

    is_active = changes.get("is_active")
    if is_active is not None and is_active != product.is_active:
        _set_active(db, actor, product, is_active)
        if not is_active and product.stock != 0:
            warnings.append("has_stock")

    db.commit()
    return product, warnings


def _set_active(db: Session, actor: AppUser, product: Product, is_active: bool) -> None:
    product.is_active = is_active
    details = {"sku": product.sku}
    if not is_active and product.is_published:
        # Desactivar saca el producto del catálogo (FR-009).
        product.is_published = False
        record_audit(
            db,
            action="product.unpublished",
            user_id=actor.id,
            entity_type="product",
            entity_id=product.id,
            details={**details, "cause": "deactivated"},
        )
    record_audit(
        db,
        action="product.activated" if is_active else "product.deactivated",
        user_id=actor.id,
        entity_type="product",
        entity_id=product.id,
        details=details,
    )
