"""Unidades, categorías y atributos (RF-03 a RF-05; FR-028 a FR-031).

Contrato: specs/002-productos-inventario/contracts/api.md. Cualquier rol lee la
configuración (la necesita para crear, buscar y vender); solo el Admin la cambia.
"""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.api.deps import CurrentUser, DbSession, require_authenticated, require_roles
from app.db.models import AttributeDefinition, Category, Unit
from app.domain.roles import Role
from app.services import catalog_config as config_service

router = APIRouter(tags=["catalog-config"])

AnyUser = Annotated[CurrentUser, Depends(require_authenticated())]
Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]

UnitCode = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=10)
]
ShortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
CategoryName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
SkuPrefix = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{3}$")]
AttributeKey = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{1,39}$")]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
SortOrder = Annotated[int, Field(ge=0, le=999)]


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


# --- Escritura: solo el Admin (FR-029 a FR-031) --------------------------------------


class CreateUnitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: UnitCode
    name: ShortName
    decimals: Literal[0, 2]


class UpdateUnitRequest(BaseModel):
    """El código y los decimales no se cambian: enviarlos es un error de validación."""

    model_config = ConfigDict(extra="forbid")

    name: ShortName | None = None
    is_active: bool | None = None


class CreateCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CategoryName
    sku_prefix: SkuPrefix
    default_unit_id: uuid.UUID
    unit_locked: bool = False


class UpdateCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CategoryName | None = None
    sku_prefix: SkuPrefix | None = None
    default_unit_id: uuid.UUID | None = None
    unit_locked: bool | None = None
    is_active: bool | None = None


class CreateAttributeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: AttributeKey
    label: Label
    data_type: Literal["text", "number", "option"]
    options: list[AttributeOption] | None = None
    is_required: bool = False
    is_filterable: bool = False
    sort_order: SortOrder = 0


class UpdateAttributeRequest(BaseModel):
    """La clave y el tipo no se cambian; las opciones se agregan o se desactivan."""

    model_config = ConfigDict(extra="forbid")

    label: Label | None = None
    options: list[AttributeOption] | None = None
    is_required: bool | None = None
    is_filterable: bool | None = None
    sort_order: SortOrder | None = None
    is_active: bool | None = None


def _changes(body: BaseModel) -> dict[str, Any]:
    return {
        key: value
        for key, value in body.model_dump(exclude_unset=True).items()
        if value is not None
    }


@router.post("/units", status_code=status.HTTP_201_CREATED)
def create_unit(body: CreateUnitRequest, current: Admin, db: DbSession) -> UnitOut:
    unit = config_service.create_unit(
        db, actor=current.user, code=body.code, name=body.name, decimals=body.decimals
    )
    return UnitOut.of(unit)


@router.patch("/units/{unit_id}")
def update_unit(
    unit_id: uuid.UUID, body: UpdateUnitRequest, current: Admin, db: DbSession
) -> UnitOut:
    unit = config_service.update_unit(
        db, actor=current.user, unit_id=unit_id, changes=_changes(body)
    )
    return UnitOut.of(unit)


def _category_out(db: DbSession, category_id: uuid.UUID) -> CategoryOut:
    return CategoryOut.of(*config_service.category_with_attributes(db, category_id))


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(body: CreateCategoryRequest, current: Admin, db: DbSession) -> CategoryOut:
    category = config_service.create_category(
        db,
        actor=current.user,
        name=body.name,
        sku_prefix=body.sku_prefix,
        default_unit_id=body.default_unit_id,
        unit_locked=body.unit_locked,
    )
    return _category_out(db, category.id)


@router.patch("/categories/{category_id}")
def update_category(
    category_id: uuid.UUID, body: UpdateCategoryRequest, current: Admin, db: DbSession
) -> CategoryOut:
    config_service.update_category(
        db, actor=current.user, category_id=category_id, changes=_changes(body)
    )
    return _category_out(db, category_id)


@router.post("/categories/{category_id}/attributes", status_code=status.HTTP_201_CREATED)
def create_attribute(
    category_id: uuid.UUID, body: CreateAttributeRequest, current: Admin, db: DbSession
) -> AttributeOut:
    attribute = config_service.create_attribute(
        db, actor=current.user, category_id=category_id, data=body.model_dump()
    )
    return AttributeOut.of(attribute)


@router.patch("/attributes/{attribute_id}")
def update_attribute(
    attribute_id: uuid.UUID, body: UpdateAttributeRequest, current: Admin, db: DbSession
) -> AttributeOut:
    attribute = config_service.update_attribute(
        db, actor=current.user, attribute_id=attribute_id, changes=_changes(body)
    )
    return AttributeOut.of(attribute)
