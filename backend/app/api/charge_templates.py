"""Endpoints de gastos frecuentes (RF-14/FR-032, FR-033).

Contrato: specs/003-proveedores-compras/contracts/api.md.
"""

import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.api.deps import CurrentUser, DbSession, require_roles
from app.db.models import ChargeTemplate
from app.domain.roles import Role
from app.services import charge_templates as templates_service

router = APIRouter(prefix="/charge-templates", tags=["charge-templates"])

Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]
AdminOrWarehouse = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.WAREHOUSE))]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Currency = Literal["USD", "VES"]


class TemplateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    charge_type: Literal["percent", "fixed"]
    default_value: Decimal | None = None
    currency: Currency | None = None


class TemplateUpdate(BaseModel):
    """`charge_type` no cambia: no existe en este esquema (422 si se envía)."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    default_value: Decimal | None = None
    currency: Currency | None = None
    is_active: bool | None = None


class ChargeTemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    charge_type: str
    default_value: str | None
    currency: str | None
    is_active: bool


def template_out(template: ChargeTemplate) -> ChargeTemplateOut:
    return ChargeTemplateOut(
        id=template.id,
        name=template.name,
        charge_type=template.charge_type,
        default_value=None
        if template.default_value is None
        else str(template.default_value.quantize(Decimal("0.01"))),
        currency=template.currency,
        is_active=template.is_active,
    )


@router.get("")
def list_templates(
    current: AdminOrWarehouse, db: DbSession, include_inactive: bool = False
) -> list[ChargeTemplateOut]:
    """Activos; con `include_inactive` también los inactivos, solo para el Admin."""
    rows = templates_service.list_templates(
        db, include_inactive=include_inactive and current.role == Role.ADMIN
    )
    return [template_out(row) for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateCreate, current: Admin, db: DbSession) -> ChargeTemplateOut:
    template = templates_service.create_template(
        db,
        actor=current.user,
        name=body.name,
        charge_type=body.charge_type,
        default_value=body.default_value,
        currency=body.currency,
    )
    return template_out(template)


@router.patch("/{template_id}")
def update_template(
    template_id: uuid.UUID, body: TemplateUpdate, current: Admin, db: DbSession
) -> ChargeTemplateOut:
    changes = body.model_dump(exclude_unset=True)
    for key in ("name", "is_active"):
        if key in changes and changes[key] is None:
            changes.pop(key)
    template = templates_service.update_template(
        db, actor=current.user, template_id=template_id, changes=changes
    )
    return template_out(template)
