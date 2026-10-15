"""Autorizaciones de descuento (RF-22, RN-07; FR-023 a FR-027; research R8).

Contrato: specs/004-ventas-multimoneda/contracts/api.md. El Vendedor las pide desde un
equipo vigente; el Admin decide las solicitudes. El Admin no las necesita: sus descuentos
quedan autorizados por él mismo.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import ActiveDevice, CurrentUser, DbSession, require_roles
from app.api.product_schemas import UserRef, user_ref
from app.api.sale_schemas import money_str
from app.db.models import Device, DiscountAuthorization, Product
from app.domain.roles import Role
from app.services import discounts as discounts_service
from app.services.users import users_by_id

router = APIRouter(prefix="/discount-authorizations", tags=["discount-authorizations"])

Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]
Seller = Annotated[CurrentUser, Depends(require_roles(Role.SELLER))]
AdminOrSeller = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.SELLER))]


class AuthorizationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["pin", "request"]
    admin_username: str | None = Field(default=None, max_length=100)
    pin: str | None = Field(default=None, max_length=20)
    sale_id: uuid.UUID
    sale_item_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    discount_type: Literal["amount", "percent"]
    discount_value: Decimal
    base_usd: Decimal


class ApproveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discount_value: Decimal | None = None


class RejectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=200)


class AuthorizationProduct(BaseModel):
    id: uuid.UUID
    sku: str
    name: str


class AuthorizationDevice(BaseModel):
    id: uuid.UUID
    name: str


class DiscountAuthorizationOut(BaseModel):
    id: uuid.UUID
    sale_id: uuid.UUID
    sale_item_id: uuid.UUID | None
    product: AuthorizationProduct | None
    discount_type: str
    requested_value: str
    discount_value: str
    base_usd: str
    discount_usd: str
    method: str
    status: str
    requested_by: UserRef
    requested_at: datetime
    device: AuthorizationDevice
    decided_by: UserRef | None
    decided_at: datetime | None
    rejection_reason: str | None


def authorizations_out(
    db: Session, rows: list[DiscountAuthorization]
) -> list[DiscountAuthorizationOut]:
    users = users_by_id(db, {row.requested_by for row in rows} | {row.decided_by for row in rows})
    result = []
    for row in rows:
        product = db.get(Product, row.product_id) if row.product_id else None
        device = db.get(Device, row.device_id)
        result.append(
            DiscountAuthorizationOut(
                id=row.id,
                sale_id=row.sale_id,
                sale_item_id=row.sale_item_id,
                product=None
                if product is None
                else AuthorizationProduct(id=product.id, sku=product.sku, name=product.name),
                discount_type=row.discount_type,
                requested_value=money_str(row.requested_value),
                discount_value=money_str(row.discount_value),
                base_usd=money_str(row.base_usd),
                discount_usd=money_str(row.discount_usd),
                method=row.method,
                status=row.status,
                requested_by=user_ref(users[row.requested_by]),
                requested_at=row.requested_at,
                device=AuthorizationDevice(id=device.id, name=device.name),
                decided_by=user_ref(users.get(row.decided_by)) if row.decided_by else None,
                decided_at=row.decided_at,
                rejection_reason=row.rejection_reason,
            )
        )
    return result


@router.post("", status_code=status.HTTP_201_CREATED)
def request_authorization(
    body: AuthorizationIn, current: Seller, device: ActiveDevice, db: DbSession
) -> DiscountAuthorizationOut:
    authorization = discounts_service.request_authorization(
        db,
        device=device,
        user=current.user,
        data=discounts_service.AuthorizationRequest(
            method=body.method,
            sale_id=body.sale_id,
            sale_item_id=body.sale_item_id,
            product_id=body.product_id,
            discount_type=body.discount_type,
            discount_value=body.discount_value,
            base_usd=body.base_usd,
            admin_username=body.admin_username,
            pin=body.pin,
        ),
    )
    db.commit()
    return authorizations_out(db, [authorization])[0]


@router.get("")
def list_pending(
    current: Admin,
    db: DbSession,
    status_filter: Annotated[Literal["pending"], Query(alias="status")] = "pending",
) -> list[DiscountAuthorizationOut]:
    """Solicitudes por decidir, más antiguas primero."""
    return authorizations_out(db, discounts_service.list_pending(db))


@router.get("/{authorization_id}")
def get_authorization(
    authorization_id: uuid.UUID, current: AdminOrSeller, db: DbSession
) -> DiscountAuthorizationOut:
    authorization = discounts_service.get_authorization(
        db, user=current.user, authorization_id=authorization_id
    )
    return authorizations_out(db, [authorization])[0]


@router.post("/{authorization_id}/approve")
def approve(
    authorization_id: uuid.UUID, body: ApproveIn, current: Admin, db: DbSession
) -> DiscountAuthorizationOut:
    authorization = discounts_service.approve(
        db,
        actor=current.user,
        authorization_id=authorization_id,
        discount_value=body.discount_value,
    )
    db.commit()
    return authorizations_out(db, [authorization])[0]


@router.post("/{authorization_id}/reject")
def reject(
    authorization_id: uuid.UUID, body: RejectIn, current: Admin, db: DbSession
) -> DiscountAuthorizationOut:
    authorization = discounts_service.reject(
        db, actor=current.user, authorization_id=authorization_id, reason=body.reason
    )
    db.commit()
    return authorizations_out(db, [authorization])[0]
