"""Unidades, categorías y atributos (RF-03 a RF-05; FR-028 a FR-031).

Contrato: specs/002-productos-inventario/contracts/api.md. Cualquier rol lee la
configuración (la necesita para crear, buscar y vender); solo el Admin la cambia.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, require_authenticated
from app.db.models import AttributeDefinition, Category, Unit
from app.domain.roles import Role
from app.services import catalog_config as config_service

router = APIRouter(tags=["catalog-config"])

AnyUser = Annotated[CurrentUser, Depends(require_authenticated())]


class UnitOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    decimals: int
    is_active: bool

    @classmethod
    def of(cls, unit: Unit) -> UnitOut:
        return cls(
            id=unit.id,
            code=unit.code,
            name=unit.name,
            decimals=unit.decimals,
            is_active=unit.is_active,
        )


class AttributeOption(BaseModel):
    value: str
    is_active: bool


class AttributeOut(BaseModel):
    id: uuid.UUID
    key: str
    label: str
    data_type: str
    options: list[AttributeOption]
    is_required: bool
    is_filterable: bool
    sort_order: int
    is_active: bool

    @classmethod
    def of(cls, attribute: AttributeDefinition) -> AttributeOut:
        options: list[dict[str, Any]] = attribute.options or []
        return cls(
            id=attribute.id,
            key=attribute.key,
            label=attribute.label,
            data_type=attribute.data_type,
            options=[AttributeOption(**option) for option in options],
            is_required=attribute.is_required,
            is_filterable=attribute.is_filterable,
            sort_order=attribute.sort_order,
            is_active=attribute.is_active,
        )


class CategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    sku_prefix: str
    default_unit_id: uuid.UUID
    unit_locked: bool
    is_active: bool
    has_products: bool
    attributes: list[AttributeOut]

    @classmethod
    def of(
        cls, category: Category, attributes: list[AttributeDefinition], has_products: bool
    ) -> CategoryOut:
        return cls(
            id=category.id,
            name=category.name,
            sku_prefix=category.sku_prefix,
            default_unit_id=category.default_unit_id,
            unit_locked=category.unit_locked,
            is_active=category.is_active,
            has_products=has_products,
            attributes=[AttributeOut.of(attribute) for attribute in attributes],
        )


def categories_out(db: DbSession, *, include_inactive: bool) -> list[CategoryOut]:
    rows = config_service.list_categories(db, include_inactive=include_inactive)
    return [CategoryOut.of(*row) for row in rows]


@router.get("/units")
def list_units(current: AnyUser, db: DbSession, include_inactive: bool = False) -> list[UnitOut]:
    # Las unidades inactivas solo las ve el Admin, para reactivarlas.
    show_inactive = include_inactive and current.role == Role.ADMIN
    return [UnitOut.of(unit) for unit in config_service.list_units(db, show_inactive)]


@router.get("/categories")
def list_categories(
    current: AnyUser, db: DbSession, include_inactive: bool = False
) -> list[CategoryOut]:
    show_inactive = include_inactive and current.role == Role.ADMIN
    return categories_out(db, include_inactive=show_inactive)
