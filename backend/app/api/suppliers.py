"""Endpoints de proveedores (RF-13/FR-001 a FR-003).

Contrato: specs/003-proveedores-compras/contracts/api.md.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.api.deps import CurrentUser, DbSession, require_roles
from app.db.models import Supplier
from app.domain.roles import Role
from app.services import suppliers as suppliers_service

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

AdminOrWarehouse = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.WAREHOUSE))]

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Rif = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    rif: Rif | None = None
    phone: Phone | None = None
    notes: Notes | None = None


class SupplierUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    rif: Rif | None = None
    phone: Phone | None = None
    notes: Notes | None = None
    is_active: bool | None = None


class SupplierOut(BaseModel):
    id: uuid.UUID
    name: str
    rif: str | None
    phone: str | None
    notes: str | None
    is_active: bool
    updated_at: datetime


class SupplierPage(BaseModel):
    items: list[SupplierOut]
    total: int
    page: int
    page_size: int


def supplier_out(supplier: Supplier) -> SupplierOut:
    return SupplierOut(
        id=supplier.id,
        name=supplier.name,
        rif=supplier.rif,
        phone=supplier.phone,
        notes=supplier.notes,
        is_active=supplier.is_active,
        updated_at=supplier.updated_at,
    )


@router.get("")
def list_suppliers(
    current: AdminOrWarehouse,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    is_active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SupplierPage:
    rows, total = suppliers_service.list_suppliers(
        db, q=q, is_active=is_active, page=page, page_size=page_size
    )
    return SupplierPage(
        items=[supplier_out(row) for row in rows], total=total, page=page, page_size=page_size
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_supplier(body: SupplierCreate, current: AdminOrWarehouse, db: DbSession) -> SupplierOut:
    supplier = suppliers_service.create_supplier(
        db, actor=current.user, name=body.name, rif=body.rif, phone=body.phone, notes=body.notes
    )
    return supplier_out(supplier)


@router.get("/{supplier_id}")
def get_supplier(supplier_id: uuid.UUID, current: AdminOrWarehouse, db: DbSession) -> SupplierOut:
    return supplier_out(suppliers_service.get_supplier(db, supplier_id))


@router.patch("/{supplier_id}")
def update_supplier(
    supplier_id: uuid.UUID, body: SupplierUpdate, current: AdminOrWarehouse, db: DbSession
) -> SupplierOut:
    changes = body.model_dump(exclude_unset=True)
    if changes.get("name") is None:
        changes.pop("name", None)
    if changes.get("is_active") is None:
        changes.pop("is_active", None)
    supplier = suppliers_service.update_supplier(
        db, actor=current.user, supplier_id=supplier_id, changes=changes
    )
    return supplier_out(supplier)
