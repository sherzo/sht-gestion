"""Endpoints de conteos físicos (RF-12, RN-19; FR-024 a FR-027, FR-025a).

Contrato: specs/002-productos-inventario/contracts/api.md. El Almacén cuenta a ciegas:
sus respuestas no incluyen el stock esperado ni la diferencia (FR-025, research R8).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.api.deps import CurrentUser, DbSession, require_roles
from app.api.product_schemas import UserRef, user_ref
from app.db.models import Product, StockCount, StockCountLine, Unit
from app.domain.roles import Role
from app.services import stock_counts as counts_service
from app.services.stock_counts import line_difference, quantity_str
from app.services.users import users_by_id

router = APIRouter(prefix="/stock-counts", tags=["stock-counts"])

AdminOrWarehouse = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.WAREHOUSE))]
Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]

Text500 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
CountStatus = Literal["open", "ready_for_review", "applied", "cancelled"]


class Scope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["all", "categories", "products"]
    ids: list[uuid.UUID] = []


class OpenCountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Scope
    notes: Text500 | None = None


class RecordLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counted_quantity: Decimal


class ApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acknowledge_uncounted: bool = False


class CancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Reason


class LineUnit(BaseModel):
    code: str
    decimals: int


class LineProduct(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    unit: LineUnit


class StockCountLineBlind(BaseModel):
    """Línea para el Almacén: sin stock esperado ni diferencia (conteo a ciegas)."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    product: LineProduct
    counted_quantity: str | None
    counted_at: datetime | None
    counted_by: UserRef | None


class StockCountLineOut(StockCountLineBlind):
    expected_quantity: str | None
    difference: str | None


class StockCountSummary(BaseModel):
    id: uuid.UUID
    status: str
    scope: dict[str, Any]
    notes: str | None
    started_by: UserRef | None
    started_at: datetime
    ready_at: datetime | None
    closed_by: UserRef | None
    closed_at: datetime | None
    cancel_reason: str | None
    lines_total: int
    lines_counted: int


class StockCountWarehouse(StockCountSummary):
    model_config = ConfigDict(extra="forbid")

    lines: list[StockCountLineBlind]


class StockCountAdmin(StockCountSummary):
    model_config = ConfigDict(extra="forbid")

    lines: list[StockCountLineOut]
    lines_with_difference: int


StockCountOut = StockCountAdmin | StockCountWarehouse


class NegativeProduct(BaseModel):
    id: uuid.UUID
    sku: str
    name: str


class ApplyResult(BaseModel):
    count: StockCountAdmin
    adjustments: int
    negative_products: list[NegativeProduct]


def _summary_fields(count: StockCount, users: dict, total: int, counted: int) -> dict[str, Any]:
    return {
        "id": count.id,
        "status": count.status,
        "scope": count.scope,
        "notes": count.notes,
        "started_by": user_ref(users.get(count.started_by)),
        "started_at": count.started_at,
        "ready_at": count.ready_at,
        "closed_by": user_ref(users.get(count.closed_by)) if count.closed_by else None,
        "closed_at": count.closed_at,
        "cancel_reason": count.cancel_reason,
        "lines_total": total,
        "lines_counted": counted,
    }


def _line_out(
    role: Role, line: StockCountLine, product: Product, unit: Unit, users: dict
) -> StockCountLineOut | StockCountLineBlind:
    blind = {
        "id": line.id,
        "product": LineProduct(
            id=product.id,
            sku=product.sku,
            name=product.name,
            unit=LineUnit(code=unit.code, decimals=unit.decimals),
        ),
        "counted_quantity": quantity_str(line.counted_quantity, unit.decimals),
        "counted_at": line.counted_at,
        "counted_by": user_ref(users.get(line.counted_by)) if line.counted_by else None,
    }
    if role != Role.ADMIN:
        return StockCountLineBlind(**blind)
    return StockCountLineOut(
        **blind,
        expected_quantity=quantity_str(line.expected_quantity, unit.decimals),
        difference=quantity_str(line_difference(line), unit.decimals),
    )


def _lines_out(db: DbSession, role: Role, lines: list[StockCountLine], users: dict):
    products = {
        product.id: product
        for product in db.query(Product).filter(Product.id.in_({line.product_id for line in lines}))
    }
    units = {unit.id: unit for unit in db.query(Unit)}
    return [
        _line_out(
            role,
            line,
            products[line.product_id],
            units[products[line.product_id].unit_id],
            users,
        )
        for line in lines
    ]


def count_out(db: DbSession, role: Role, count: StockCount) -> StockCountOut:
    db.refresh(count)
    lines = counts_service.count_lines(db, count.id)
    users = users_by_id(
        db,
        {count.started_by, count.closed_by} | {line.counted_by for line in lines},
    )
    counted = sum(1 for line in lines if line.counted_quantity is not None)
    fields = _summary_fields(count, users, len(lines), counted)
    if role != Role.ADMIN:
        return StockCountWarehouse(**fields, lines=_lines_out(db, role, lines, users))
    with_difference = sum(1 for line in lines if (line_difference(line) or 0) != 0)
    return StockCountAdmin(
        **fields,
        lines=_lines_out(db, role, lines, users),
        lines_with_difference=with_difference,
    )


@router.get("")
def list_counts(
    current: AdminOrWarehouse, db: DbSession, status: CountStatus | None = None
) -> list[StockCountSummary]:
    rows = counts_service.list_counts(db, status=status)
    users = users_by_id(
        db, {count.started_by for count, _, _ in rows} | {count.closed_by for count, _, _ in rows}
    )
    return [
        StockCountSummary(**_summary_fields(count, users, total, counted))
        for count, total, counted in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def open_count(body: OpenCountRequest, current: AdminOrWarehouse, db: DbSession) -> StockCountOut:
    count = counts_service.open_count(
        db, actor=current.user, scope=body.scope.model_dump(), notes=body.notes or None
    )
    return count_out(db, current.role, count)


@router.get("/{count_id}")
def get_count(count_id: uuid.UUID, current: AdminOrWarehouse, db: DbSession) -> StockCountOut:
    return count_out(db, current.role, counts_service.get_count(db, count_id))


@router.put("/{count_id}/lines/{line_id}")
def record_line(
    count_id: uuid.UUID,
    line_id: uuid.UUID,
    body: RecordLineRequest,
    current: AdminOrWarehouse,
    db: DbSession,
) -> StockCountLineOut | StockCountLineBlind:
    line = counts_service.record_line(
        db, actor=current.user, count_id=count_id, line_id=line_id, counted=body.counted_quantity
    )
    db.refresh(line)
    users = users_by_id(db, {line.counted_by})
    return _lines_out(db, current.role, [line], users)[0]


@router.post("/{count_id}/ready")
def mark_ready(count_id: uuid.UUID, current: AdminOrWarehouse, db: DbSession) -> StockCountOut:
    count = counts_service.mark_ready(db, actor=current.user, count_id=count_id)
    return count_out(db, current.role, count)


@router.post("/{count_id}/reopen")
def reopen(count_id: uuid.UUID, current: Admin, db: DbSession) -> StockCountAdmin:
    count = counts_service.reopen(db, actor=current.user, count_id=count_id)
    return count_out(db, current.role, count)


@router.post("/{count_id}/apply")
def apply_count(
    count_id: uuid.UUID, body: ApplyRequest, current: Admin, db: DbSession
) -> ApplyResult:
    result = counts_service.apply_count(
        db,
        actor=current.user,
        count_id=count_id,
        acknowledge_uncounted=body.acknowledge_uncounted,
    )
    return ApplyResult(
        count=count_out(db, current.role, result.count),
        adjustments=result.adjustments,
        negative_products=[
            NegativeProduct(id=product.id, sku=product.sku, name=product.name)
            for product in result.negative_products
        ],
    )


@router.post("/{count_id}/cancel")
def cancel_count(
    count_id: uuid.UUID, body: CancelRequest, current: AdminOrWarehouse, db: DbSession
) -> StockCountOut:
    count = counts_service.cancel_count(
        db, actor=current.user, count_id=count_id, reason=body.reason
    )
    return count_out(db, current.role, count)
