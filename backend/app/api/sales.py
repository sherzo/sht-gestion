"""Consulta y anulación de ventas (RF-26, RF-27; FR-041 a FR-049; research R10, R12).

Contrato: specs/004-ventas-multimoneda/contracts/api.md. Las ventas se crean por la cola
de salida (`POST /sync/operations`). El esquema de respuesta se elige con el rol leído de
la base (ADR-0008): el Vendedor nunca recibe costos ni márgenes.
"""

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, DbSession, OptionalDevice, require_roles
from app.api.product_schemas import user_ref
from app.api.sale_schemas import (
    SaleAdmin,
    SalePage,
    SaleSeller,
    SaleSummary,
    money_str,
    sales_for_role,
)
from app.db.models import Customer, Device
from app.domain.roles import Role
from app.services import sales as sales_service
from app.services.users import users_by_id

router = APIRouter(prefix="/sales", tags=["sales"])

Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]
AdminOrSeller = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.SELLER))]
SaleStatus = Literal["registered", "voided", "needs_review"]


class VoidIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=5, max_length=500)


@router.get("")
def list_sales(
    current: AdminOrSeller,
    db: DbSession,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    q: Annotated[str | None, Query(max_length=20)] = None,
    seller_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    status: SaleStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SalePage:
    """Más recientes primero. El Vendedor siempre recibe solo sus ventas de hoy: los
    filtros de fecha y vendedor se ignoran (FR-046)."""
    rows, total = sales_service.list_sales(
        db,
        actor=current.user,
        filters=sales_service.SaleFilters(
            date_from=date_from,
            date_to=date_to,
            number=q,
            seller_id=seller_id,
            customer_id=customer_id,
            device_id=device_id,
            status=status,
        ),
        page=page,
        page_size=page_size,
    )
    voided = sales_service.voided_ids(db, [sale.id for sale in rows])
    users = users_by_id(db, {sale.seller_id for sale in rows})
    customers = {
        customer.id: customer
        for customer in db.query(Customer).filter(Customer.id.in_({s.customer_id for s in rows}))
    }
    devices = {
        device.id: device
        for device in db.query(Device).filter(Device.id.in_({s.device_id for s in rows}))
    }
    return SalePage(
        items=[
            SaleSummary(
                id=sale.id,
                number=sale.number,
                status="voided" if sale.id in voided else "registered",
                needs_review=sale.needs_review,
                occurred_at=sale.occurred_at,
                business_date=sale.business_date,
                seller=user_ref(users[sale.seller_id]),
                customer_name=customers[sale.customer_id].name if sale.customer_id else None,
                device_name=devices[sale.device_id].name,
                total_usd=money_str(sale.total_usd),
                total_ves=money_str(sale.total_ves),
            )
            for sale in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{sale_id}")
def get_sale(sale_id: uuid.UUID, current: AdminOrSeller, db: DbSession) -> SaleAdmin | SaleSeller:
    sale = sales_service.visible_sale(db, actor=current.user, sale_id=sale_id)
    return sales_for_role(db, [sale], current.role)[0]


@router.post("/{sale_id}/void")
def void_sale(
    sale_id: uuid.UUID, body: VoidIn, current: Admin, device: OptionalDevice, db: DbSession
) -> SaleAdmin:
    """Si la caja de la venta ya está cerrada, la devolución va a la caja abierta del
    equipo de `X-Device-Token` (RF-27, PRD v0.11); sin él, 409 `cash_session_required`."""
    sale = sales_service.void_sale(
        db, actor=current.user, sale_id=sale_id, reason=body.reason, device=device
    )
    db.commit()
    db.expire_all()
    [result] = sales_for_role(db, [sale], Role.ADMIN)
    assert isinstance(result, SaleAdmin)
    return result
