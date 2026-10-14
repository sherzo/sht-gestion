"""Configuración del inventario: unidades, categorías y atributos (RF-03 a RF-05;
FR-028 a FR-031).

El sistema se instala con las categorías, unidades y atributos de FR-028 (migración
0004). Solo el Admin los cambia, y nada se borra: se desactiva.
"""

import uuid
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import AppUser, AttributeDefinition, Category, Product, Unit
from app.services.audit import record_audit

MAX_OPTION_LENGTH = 60


def list_units(db: Session, include_inactive: bool) -> list[Unit]:
    query = select(Unit).order_by(Unit.name)
    if not include_inactive:
        query = query.where(Unit.is_active.is_(True))
    return list(db.scalars(query))


def list_categories(
    db: Session, *, include_inactive: bool
) -> list[tuple[Category, list[AttributeDefinition], bool]]:
    """Categorías con sus atributos (solo los activos, salvo `include_inactive`) y si
    tienen productos."""
    query = select(Category).order_by(Category.name)
    if not include_inactive:
        query = query.where(Category.is_active.is_(True))
    categories = list(db.scalars(query))
    attributes_query = select(AttributeDefinition).order_by(
        AttributeDefinition.sort_order, AttributeDefinition.label
    )
    if not include_inactive:
        attributes_query = attributes_query.where(AttributeDefinition.is_active.is_(True))
    by_category: dict[uuid.UUID, list[AttributeDefinition]] = {
        category.id: [] for category in categories
    }
    for attribute in db.scalars(attributes_query):
        if attribute.category_id in by_category:
            by_category[attribute.category_id].append(attribute)
    with_products = set(db.scalars(select(Product.category_id).distinct()))
    return [
        (category, by_category[category.id], category.id in with_products)
        for category in categories
    ]


def category_with_attributes(
    db: Session, category_id: uuid.UUID
) -> tuple[Category, list[AttributeDefinition], bool]:
    category = db.get(Category, category_id)
    attributes = list(
        db.scalars(
            select(AttributeDefinition)
            .where(AttributeDefinition.category_id == category_id)
            .order_by(AttributeDefinition.sort_order, AttributeDefinition.label)
        )
    )
    has_products = db.scalar(select(exists().where(Product.category_id == category_id)))
    return category, attributes, bool(has_products)


# --- Escritura: solo el Admin (FR-029 a FR-031) --------------------------------------


def validation_error_for(field: str, message: str) -> ApiError:
    return validation_error({field: message})


def _not_found(what: str) -> ApiError:
    return ApiError(404, "not_found", f"{what} no existe")


def _already_exists(message: str) -> ApiError:
    return ApiError(409, "already_exists", message)


def _flush_or_conflict(db: Session, error: ApiError) -> None:
    """Las restricciones únicas de la base resuelven las altas simultáneas. Un nombre de
    categoría repetido entre las activas tiene su propio mensaje."""
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "ux_category_active_name":
            raise _already_exists("Ya existe una categoría activa con ese nombre") from exc
        raise error from exc


def _unit_snapshot(unit: Unit) -> dict[str, Any]:
    return {
        "code": unit.code,
        "name": unit.name,
        "decimals": unit.decimals,
        "is_active": unit.is_active,
    }


def create_unit(db: Session, *, actor: AppUser, code: str, name: str, decimals: int) -> Unit:
    duplicate = _already_exists("Ya existe una unidad con ese código o nombre")
    if db.scalar(select(Unit.id).where((Unit.code == code) | (Unit.name == name))):
        raise duplicate
    unit = Unit(code=code, name=name, decimals=decimals, is_active=True, created_by=actor.id)
    db.add(unit)
    _flush_or_conflict(db, duplicate)
    record_audit(
        db,
        action="unit.created",
        user_id=actor.id,
        entity_type="unit",
        entity_id=unit.id,
        after=_unit_snapshot(unit),
    )
    db.commit()
    return unit


def update_unit(
    db: Session, *, actor: AppUser, unit_id: uuid.UUID, changes: dict[str, Any]
) -> Unit:
    """Solo cambian el nombre y el estado: el código y los decimales son fijos. Una unidad
    que usan productos activos, o que una categoría activa tiene por defecto, no se
    desactiva (FR-031)."""
    unit = db.get(Unit, unit_id, with_for_update=True)
    if unit is None:
        raise _not_found("La unidad")
    before = _unit_snapshot(unit)
    if "name" in changes and changes["name"] != unit.name:
        if db.scalar(select(Unit.id).where(Unit.name == changes["name"], Unit.id != unit.id)):
            raise _already_exists("Ya existe una unidad con ese nombre")
        unit.name = changes["name"]
    if changes.get("is_active") is False and unit.is_active:
        used_by_products = db.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.unit_id == unit.id, Product.is_active.is_(True))
        )
        used_by_categories = db.scalar(
            select(func.count())
            .select_from(Category)
            .where(Category.default_unit_id == unit.id, Category.is_active.is_(True))
        )
        if used_by_products or used_by_categories:
            raise ApiError(
                409,
                "unit_in_use",
                "La unidad la usan productos o categorías activos: no se puede desactivar",
            )
    if "is_active" in changes:
        unit.is_active = changes["is_active"]
    after = _unit_snapshot(unit)
    if after != before:
        record_audit(
            db,
            action="unit.updated",
            user_id=actor.id,
            entity_type="unit",
            entity_id=unit.id,
            before=before,
            after=after,
        )
    db.commit()
    return unit


def _category_snapshot(category: Category) -> dict[str, Any]:
    return {
        "name": category.name,
        "sku_prefix": category.sku_prefix,
        "default_unit_id": str(category.default_unit_id),
        "unit_locked": category.unit_locked,
        "is_active": category.is_active,
    }


def _active_unit(db: Session, unit_id: uuid.UUID) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None or not unit.is_active:
        raise validation_error_for("default_unit_id", "Elige una unidad activa")
    return unit


def _prefix_in_use() -> ApiError:
    return ApiError(
        409,
        "prefix_in_use",
        "El prefijo ya lo usa otra categoría o la categoría ya tiene productos",
    )


def _check_name(db: Session, name: str, exclude: uuid.UUID | None = None) -> None:
    query = select(Category.id).where(
        func.lower(Category.name) == name.lower(), Category.is_active.is_(True)
    )
    if exclude is not None:
        query = query.where(Category.id != exclude)
    if db.scalar(query):
        raise _already_exists("Ya existe una categoría activa con ese nombre")


def create_category(
    db: Session,
    *,
    actor: AppUser,
    name: str,
    sku_prefix: str,
    default_unit_id: uuid.UUID,
    unit_locked: bool,
) -> Category:
    _active_unit(db, default_unit_id)
    if db.scalar(select(Category.id).where(Category.sku_prefix == sku_prefix)):
        raise _prefix_in_use()
    _check_name(db, name)
    category = Category(
        name=name,
        sku_prefix=sku_prefix,
        next_sku_number=1,
        default_unit_id=default_unit_id,
        unit_locked=unit_locked,
        is_active=True,
        created_by=actor.id,
    )
    db.add(category)
    _flush_or_conflict(db, _prefix_in_use())
    record_audit(
        db,
        action="category.created",
        user_id=actor.id,
        entity_type="category",
        entity_id=category.id,
        after=_category_snapshot(category),
    )
    db.commit()
    return category


def update_category(
    db: Session, *, actor: AppUser, category_id: uuid.UUID, changes: dict[str, Any]
) -> Category:
    """El prefijo no cambia si la categoría tiene productos (FR-029); el nombre sí."""
    category = db.get(Category, category_id, with_for_update=True)
    if category is None:
        raise _not_found("La categoría")
    before = _category_snapshot(category)
    prefix = changes.get("sku_prefix")
    if prefix is not None and prefix != category.sku_prefix:
        has_products = db.scalar(select(Product.id).where(Product.category_id == category.id))
        taken = db.scalar(select(Category.id).where(Category.sku_prefix == prefix))
        if has_products or taken:
            raise _prefix_in_use()
        category.sku_prefix = prefix
    if "name" in changes and changes["name"] != category.name:
        _check_name(db, changes["name"], exclude=category.id)
        category.name = changes["name"]
    if "default_unit_id" in changes:
        _active_unit(db, changes["default_unit_id"])
        category.default_unit_id = changes["default_unit_id"]
    if "unit_locked" in changes:
        category.unit_locked = changes["unit_locked"]
    if "is_active" in changes:
        if changes["is_active"] and not category.is_active:
            _check_name(db, category.name, exclude=category.id)
        category.is_active = changes["is_active"]
    after = _category_snapshot(category)
    if after != before:
        category.updated_at = utcnow()
        _flush_or_conflict(db, _prefix_in_use())
        record_audit(
            db,
            action="category.updated",
            user_id=actor.id,
            entity_type="category",
            entity_id=category.id,
            before=before,
            after=after,
        )
    db.commit()
    return category


def _clean_options(
    options: list[dict[str, Any]] | None, previous: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Las opciones se agregan o se desactivan, nunca se borran (FR-030)."""
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for option in options or []:
        value = str(option.get("value", "")).strip()
        if not value or len(value) > MAX_OPTION_LENGTH:
            raise validation_error_for(
                "options", f"Cada opción necesita un texto de hasta {MAX_OPTION_LENGTH} caracteres"
            )
        if value in seen:
            raise validation_error_for("options", f"La opción {value} está repetida")
        seen.add(value)
        cleaned.append({"value": value, "is_active": bool(option.get("is_active", True))})
    missing = [option["value"] for option in previous or [] if option["value"] not in seen]
    if missing:
        raise validation_error_for(
            "options", f"Las opciones no se borran, se desactivan. Falta: {', '.join(missing)}"
        )
    if not any(option["is_active"] for option in cleaned):
        raise validation_error_for("options", "Deja al menos una opción activa")
    return cleaned


def _attribute_snapshot(attribute: AttributeDefinition) -> dict[str, Any]:
    return {
        "key": attribute.key,
        "label": attribute.label,
        "data_type": attribute.data_type,
        "options": attribute.options,
        "is_required": attribute.is_required,
        "is_filterable": attribute.is_filterable,
        "sort_order": attribute.sort_order,
        "is_active": attribute.is_active,
    }


def create_attribute(
    db: Session, *, actor: AppUser, category_id: uuid.UUID, data: dict[str, Any]
) -> AttributeDefinition:
    category = db.get(Category, category_id)
    if category is None:
        raise _not_found("La categoría")
    duplicate = _already_exists("La categoría ya tiene un atributo con esa clave")
    exists = db.scalar(
        select(AttributeDefinition.id).where(
            AttributeDefinition.category_id == category.id,
            AttributeDefinition.key == data["key"],
        )
    )
    if exists:
        raise duplicate
    is_option = data["data_type"] == "option"
    if not is_option and data.get("options"):
        raise validation_error_for("options", "Solo los atributos de opción tienen opciones")
    attribute = AttributeDefinition(
        category_id=category.id,
        key=data["key"],
        label=data["label"],
        data_type=data["data_type"],
        options=_clean_options(data.get("options"), None) if is_option else None,
        is_required=data.get("is_required", False),
        is_filterable=data.get("is_filterable", False),
        sort_order=data.get("sort_order", 0),
        is_active=True,
        created_by=actor.id,
    )
    db.add(attribute)
    _flush_or_conflict(db, duplicate)
    record_audit(
        db,
        action="attribute.created",
        user_id=actor.id,
        entity_type="attribute_definition",
        entity_id=attribute.id,
        after={**_attribute_snapshot(attribute), "category": category.sku_prefix},
    )
    db.commit()
    return attribute


def update_attribute(
    db: Session, *, actor: AppUser, attribute_id: uuid.UUID, changes: dict[str, Any]
) -> AttributeDefinition:
    """La clave y el tipo no cambian; desactivar un atributo o una opción no altera los
    valores guardados en los productos (FR-030)."""
    attribute = db.get(AttributeDefinition, attribute_id, with_for_update=True)
    if attribute is None:
        raise _not_found("El atributo")
    before = _attribute_snapshot(attribute)
    if "options" in changes:
        if attribute.data_type != "option":
            raise validation_error_for("options", "Solo los atributos de opción tienen opciones")
        attribute.options = _clean_options(changes["options"], attribute.options)
    for field in ("label", "is_required", "is_filterable", "sort_order", "is_active"):
        if field in changes:
            setattr(attribute, field, changes[field])
    after = _attribute_snapshot(attribute)
    changed = [key for key in after if after[key] != before[key]]
    if changed:
        attribute.updated_at = utcnow()
        record_audit(
            db,
            action="attribute.updated",
            user_id=actor.id,
            entity_type="attribute_definition",
            entity_id=attribute.id,
            before={key: before[key] for key in changed},
            after={key: after[key] for key in changed},
            details={"key": attribute.key},
        )
    db.commit()
    return attribute
