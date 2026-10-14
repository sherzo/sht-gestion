"""Endpoints de compras (RF-14 a RF-16, RN-14, RN-20; FR-004 a FR-021, FR-029 a FR-031).

Contrato: specs/003-proveedores-compras/contracts/api.md. El esquema de respuesta se
elige con el rol leído de la base (ADR-0008).
"""

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentUser, DbSession, require_roles
from app.api.purchase_schemas import (
    ConfirmInput,
    PurchaseConfirmedAdmin,
    PurchaseInput,
    PurchaseOut,
    PurchasePage,
    PurchaseVoidedOut,
    VoidInput,
    VoidPreview,
    VoidPreviewItem,
    cost_changes_out,
    cost_str,
    purchase_out,
    summaries_out,
)
from app.core.errors import ApiError
from app.domain.roles import Role
from app.domain.units import format_quantity
from app.services import purchases as purchases_service

router = APIRouter(prefix="/purchases", tags=["purchases"])

AdminOrWarehouse = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.WAREHOUSE))]
Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]
PurchaseStatus = Literal["draft", "confirmed", "voided"]


@router.get("")
def list_purchases(
    current: AdminOrWarehouse,
    db: DbSession,
    status: PurchaseStatus | None = None,
    supplier_id: uuid.UUID | None = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    product_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=60)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PurchasePage:
    rows, total = purchases_service.list_purchases(
        db,
        status=status,
        supplier_id=supplier_id,
        date_from=date_from,
        date_to=date_to,
        product_id=product_id,
        q=q,
        page=page,
        page_size=page_size,
    )
    return PurchasePage(items=summaries_out(db, rows), total=total, page=page, page_size=page_size)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_purchase(body: PurchaseInput, current: AdminOrWarehouse, db: DbSession) -> PurchaseOut:
    saved = purchases_service.create_purchase(db, actor=current.user, data=body.to_data())
    return purchase_out(db, saved.purchase, warnings=saved.warnings)


@router.get("/{purchase_id}")
def get_purchase(purchase_id: uuid.UUID, current: AdminOrWarehouse, db: DbSession) -> PurchaseOut:
    return purchase_out(db, purchases_service.get_purchase(db, purchase_id))


@router.put("/{purchase_id}")
def save_purchase(
    purchase_id: uuid.UUID, body: PurchaseInput, current: AdminOrWarehouse, db: DbSession
) -> PurchaseOut:
    saved = purchases_service.save_purchase(
        db, actor=current.user, purchase_id=purchase_id, data=body.to_data()
    )
    return purchase_out(db, saved.purchase, warnings=saved.warnings)


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
def discard_purchase(purchase_id: uuid.UUID, current: AdminOrWarehouse, db: DbSession) -> Response:
    purchases_service.discard_purchase(db, purchase_id=purchase_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{purchase_id}/confirm")
def confirm_purchase(
    purchase_id: uuid.UUID, body: ConfirmInput, current: AdminOrWarehouse, db: DbSession
) -> PurchaseConfirmedAdmin | PurchaseOut:
    try:
        purchase, changes = purchases_service.confirm_purchase(
            db, actor=current.user, purchase_id=purchase_id, updated_at=body.updated_at
        )
    except ApiError as error:
        db.rollback()
        if error.code == "stale_data":
            # La versión actual va en la respuesta para revisarla antes de confirmar.
            current_version = purchase_out(db, purchases_service.get_purchase(db, purchase_id))
            error.extra["purchase"] = current_version.model_dump(mode="json")
        raise
    out = purchase_out(db, purchase)
    if current.role == Role.ADMIN:
        return PurchaseConfirmedAdmin(**out.model_dump(), cost_changes=cost_changes_out(changes))
    return out


@router.get("/{purchase_id}/void-preview")
def void_preview(purchase_id: uuid.UUID, current: Admin, db: DbSession) -> VoidPreview:
    lines = purchases_service.void_preview(db, purchase_id=purchase_id)
    return VoidPreview(
        items=[
            VoidPreviewItem(
                product_id=line.product_id,
                sku=line.sku,
                stock_before=format_quantity(line.stock_before, line.unit_decimals),
                stock_after=format_quantity(line.stock_after, line.unit_decimals),
                cost_before_usd=cost_str(line.cost_before_usd),
                cost_after_usd=cost_str(line.cost_after_usd),
                keeps_cost=line.keeps_cost,
            )
            for line in lines
        ]
    )


@router.post("/{purchase_id}/void")
def void_purchase(
    purchase_id: uuid.UUID, body: VoidInput, current: Admin, db: DbSession
) -> PurchaseVoidedOut:
    purchase, alerts = purchases_service.void_purchase(
        db, actor=current.user, purchase_id=purchase_id, reason=body.reason
    )
    out = purchase_out(db, purchase)
    return PurchaseVoidedOut(**out.model_dump(), alerts_created=alerts)
