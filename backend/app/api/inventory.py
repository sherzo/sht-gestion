"""Endpoints de inventario: ajustes, solicitudes del Almacén, stock bajo y resumen
(RF-08 a RF-11, RN-19; FR-016 a FR-023).

Contrato: specs/002-productos-inventario/contracts/api.md.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.api.deps import CurrentUser, DbSession, require_roles
from app.api.product_schemas import (
    ProductOut,
    StockMovementOut,
    UnitRef,
    UserRef,
    movement_for_role,
    unit_ref,
    user_ref,
)
from app.api.products import products_out
from app.db.models import AdjustmentRequest, Product, Unit
from app.domain.roles import Role
from app.domain.units import format_quantity
from app.services import alerts as alerts_service
from app.services import inventory as inventory_service
from app.services import products as products_service
from app.services import purchases as purchases_service
from app.services.users import users_by_id

router = APIRouter(prefix="/inventory", tags=["inventory"])

AdminOrWarehouse = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.WAREHOUSE))]
Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]
Warehouse = Annotated[CurrentUser, Depends(require_roles(Role.WAREHOUSE))]

Reason = Literal["physical_count", "damage", "loss", "correction"]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
DecisionReason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
RequestStatus = Literal["pending", "approved", "rejected", "withdrawn"]


class AdjustmentRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: uuid.UUID
    quantity_delta: Decimal
    reason: Reason
    note: Note | None = None


class RejectBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: DecisionReason


class RequestProduct(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    unit: UnitRef
    stock: str


class AdjustmentRequestOut(BaseModel):
    id: uuid.UUID
    product: RequestProduct
    quantity_delta: str
    adjustment_reason: str
    note: str | None
    status: str
    requested_by: UserRef
    requested_at: datetime
    decided_by: UserRef | None
    decided_at: datetime | None
    rejection_reason: str | None
    stock_movement_id: uuid.UUID | None


class AdjustmentRequestPage(BaseModel):
    items: list[AdjustmentRequestOut]
    total: int
    page: int
    page_size: int


class AdjustmentResultOut(BaseModel):
    status: Literal["applied", "pending"]
    movement: StockMovementOut | None = None
    request: AdjustmentRequestOut | None = None


def requests_out(db: DbSession, requests: list[AdjustmentRequest]) -> list[AdjustmentRequestOut]:
    products = {
        product.id: product
        for product in db.query(Product).filter(
            Product.id.in_({request.product_id for request in requests})
        )
    }
    units = {unit.id: unit for unit in db.query(Unit)}
    users = users_by_id(
        db, {request.requested_by for request in requests} | {r.decided_by for r in requests}
    )
    result = []
    for request in requests:
        product = products[request.product_id]
        unit = units[product.unit_id]
        result.append(
            AdjustmentRequestOut(
                id=request.id,
                product=RequestProduct(
                    id=product.id,
                    sku=product.sku,
                    name=product.name,
                    unit=unit_ref(unit),
                    stock=format_quantity(product.stock, unit.decimals),
                ),
                quantity_delta=format_quantity(request.quantity_delta, unit.decimals),
                adjustment_reason=request.adjustment_reason,
                note=request.note,
                status=request.status,
                requested_by=user_ref(users[request.requested_by]),
                requested_at=request.requested_at,
                decided_by=user_ref(users.get(request.decided_by)) if request.decided_by else None,
                decided_at=request.decided_at,
                rejection_reason=request.rejection_reason,
                stock_movement_id=request.stock_movement_id,
            )
        )
    return result


def request_out(db: DbSession, request: AdjustmentRequest) -> AdjustmentRequestOut:
    db.refresh(request)
    return requests_out(db, [request])[0]


@router.post(
    "/adjustments",
    status_code=status.HTTP_201_CREATED,
    responses={202: {"model": AdjustmentResultOut, "description": "Salida pendiente"}},
)
def register_adjustment(
    body: AdjustmentRequestBody, current: AdminOrWarehouse, db: DbSession, response: Response
) -> AdjustmentResultOut:
    result = inventory_service.register_adjustment(
        db,
        actor=current.user,
        product_id=body.product_id,
        quantity_delta=body.quantity_delta,
        reason=body.reason,
        note=body.note or None,
    )
    if result.request is not None:
        response.status_code = status.HTTP_202_ACCEPTED
        return AdjustmentResultOut(status="pending", request=request_out(db, result.request))
    movement = result.movement
    product = db.get(Product, movement.product_id)
    unit = db.get(Unit, product.unit_id)
    users = users_by_id(db, {movement.created_by})
    return AdjustmentResultOut(
        status="applied",
        movement=movement_for_role(current.role, movement, unit=unit, users=users),
    )


@router.get("/adjustment-requests")
def list_adjustment_requests(
    current: AdminOrWarehouse,
    db: DbSession,
    status: RequestStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AdjustmentRequestPage:
    rows, total = inventory_service.list_requests(
        db, actor=current.user, status=status, page=page, page_size=page_size
    )
    return AdjustmentRequestPage(
        items=requests_out(db, rows), total=total, page=page, page_size=page_size
    )


@router.post("/adjustment-requests/{request_id}/approve")
def approve_request(request_id: uuid.UUID, current: Admin, db: DbSession) -> AdjustmentRequestOut:
    request = inventory_service.approve_request(db, actor=current.user, request_id=request_id)
    return request_out(db, request)


@router.post("/adjustment-requests/{request_id}/reject")
def reject_request(
    request_id: uuid.UUID, body: RejectBody, current: Admin, db: DbSession
) -> AdjustmentRequestOut:
    request = inventory_service.reject_request(
        db, actor=current.user, request_id=request_id, reason=body.reason
    )
    return request_out(db, request)


@router.post("/adjustment-requests/{request_id}/withdraw")
def withdraw_request(
    request_id: uuid.UUID, current: Warehouse, db: DbSession
) -> AdjustmentRequestOut:
    request = inventory_service.withdraw_request(db, actor=current.user, request_id=request_id)
    return request_out(db, request)


class AdminSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    low_stock: int
    pending_adjustments: int
    counts_ready_for_review: int
    open_alerts: int
    draft_purchases: int


class WarehouseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    low_stock: int
    my_pending_requests: int
    open_counts: int
    draft_purchases: int


@router.get("/low-stock")
def low_stock(current: AdminOrWarehouse, db: DbSession) -> list[ProductOut]:
    """Productos activos con stock menor o igual al mínimo, por categoría (RF-11/FR-023)."""
    return products_out(db, current.role, products_service.low_stock_products(db))


@router.get("/summary")
def summary(current: AdminOrWarehouse, db: DbSession) -> AdminSummary | WarehouseSummary:
    """Contadores de las tarjetas del inicio (research R11)."""
    counts = inventory_service.summary(db, actor=current.user)
    if current.role == Role.ADMIN:
        return AdminSummary(
            low_stock=counts.low_stock,
            pending_adjustments=counts.pending_requests,
            counts_ready_for_review=counts.counts_ready_for_review,
            open_alerts=alerts_service.open_alerts_count(db),
            draft_purchases=purchases_service.draft_count(db),
        )
    return WarehouseSummary(
        low_stock=counts.low_stock,
        my_pending_requests=counts.pending_requests,
        open_counts=counts.open_counts,
        draft_purchases=purchases_service.draft_count(db),
    )
