"""Cola de salida del mostrador (FR-017, FR-018; ADR-0003, research R4).

Contrato: specs/004-ventas-multimoneda/contracts/api.md. Una operación por petición,
idempotente por su `id`: reenviarla devuelve la misma respuesta, también si se rechazó.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.api.deps import CurrentDevice, CurrentUser, DbSession, require_roles
from app.api.sale_schemas import (
    CashSessionOut,
    SaleAdmin,
    SaleSeller,
    cash_session_out,
    sales_for_role,
)
from app.core.errors import validation_error, validation_fields
from app.db.models import AppUser, Device
from app.domain import sale_math
from app.domain.money import MAX_PRICE, MAX_VES, PRICE_DECIMALS, VES_DECIMALS, validate_usd
from app.domain.roles import Role
from app.services import cash_sessions as cash_sessions_service
from app.services import sales as sales_service
from app.services import sync as sync_service
from app.services.customers import CustomerData

router = APIRouter(prefix="/sync", tags=["sync"])

AdminOrSeller = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.SELLER))]


def parse_payload[P: BaseModel](model: type[P], operation: sync_service.Operation) -> P:
    """Valida el contenido de la operación; los errores son un rechazo 422 permanente."""
    try:
        return model.model_validate(operation.payload)
    except ValidationError as exc:
        raise validation_error(validation_fields(exc.errors(), prefix="payload")) from exc


def amount_field(value: Decimal, field: str, *, decimals: int, maximum: Decimal) -> Decimal:
    """Monto mayor o igual que cero con los decimales de su moneda (ADR-0004)."""
    try:
        return validate_usd(value, decimals, allow_zero=True, maximum=maximum)
    except ValueError as exc:
        raise validation_error({f"payload.{field}": str(exc)}) from exc


# --- Manejadores de las operaciones (research R4) --------------------------------------


class CashSessionOpenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    opening_float_ves: Decimal
    opening_float_usd: Decimal


def handle_cash_session_open(
    db: Session, device: Device, user: AppUser, operation: sync_service.Operation
) -> dict[str, Any]:
    data = parse_payload(CashSessionOpenInput, operation)
    session = cash_sessions_service.open_cash_session(
        db,
        device=device,
        user=user,
        operation_id=operation.id,
        session_id=data.id,
        float_ves=amount_field(
            data.opening_float_ves, "opening_float_ves", decimals=VES_DECIMALS, maximum=MAX_VES
        ),
        float_usd=amount_field(
            data.opening_float_usd, "opening_float_usd", decimals=PRICE_DECIMALS, maximum=MAX_PRICE
        ),
        opened_at=operation.created_at,
    )
    return cash_session_out(db, session).model_dump(mode="json")


class DiscountIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["amount", "percent"]
    value: Decimal
    authorization_id: uuid.UUID | None = None


class SaleItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    entered_unit: Literal["m", "cm", "unit"]
    unit_price_usd: Decimal
    discount: DiscountIn | None = None


class MoneyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = Field(min_length=1, max_length=30)
    amount: Decimal
    reference: str | None = Field(default=None, max_length=60)


class CustomerIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: uuid.UUID
    name: str = Field(min_length=2, max_length=100)
    document_id: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)


class SaleIn(BaseModel):
    """Contenido de `sale.create` (contrato, `SaleInput`)."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    sequence_number: int = Field(ge=1)
    cash_session_id: uuid.UUID
    seller_id: uuid.UUID
    occurred_at: AwareDatetime
    exchange_rate: Decimal
    exchange_rate_date: date
    customer: CustomerIn | None = None
    customer_id: uuid.UUID | None = None
    items: list[SaleItemIn] = Field(max_length=sale_math.MAX_LINES)
    discount: DiscountIn | None = None
    payments: list[MoneyIn] = Field(max_length=sale_math.MAX_PAYMENTS)
    change: list[MoneyIn] = Field(max_length=sale_math.MAX_CHANGE)
    device_total_usd: Decimal


def _discount_data(discount: DiscountIn | None) -> sales_service.DiscountData | None:
    if discount is None:
        return None
    return sales_service.DiscountData(discount.type, discount.value, discount.authorization_id)


def _money_data(entries: list[MoneyIn]) -> list[sales_service.MoneyData]:
    return [
        sales_service.MoneyData(entry.method, entry.amount, entry.reference) for entry in entries
    ]


def handle_sale_create(
    db: Session, device: Device, user: AppUser, operation: sync_service.Operation
) -> dict[str, Any]:
    data = parse_payload(SaleIn, operation)
    if data.customer is not None and data.customer_id is not None:
        raise validation_error(
            {"payload.customer_id": "Envía el cliente nuevo o uno existente, no ambos"}
        )
    outcome = sales_service.create_sale(
        db,
        device=device,
        user=user,
        operation_id=operation.id,
        data=sales_service.SaleData(
            id=data.id,
            sequence_number=data.sequence_number,
            cash_session_id=data.cash_session_id,
            seller_id=data.seller_id,
            occurred_at=data.occurred_at,
            exchange_rate=data.exchange_rate,
            exchange_rate_date=data.exchange_rate_date,
            items=[
                sales_service.ItemData(
                    item.id,
                    item.product_id,
                    item.quantity,
                    item.entered_unit,
                    item.unit_price_usd,
                    _discount_data(item.discount),
                )
                for item in data.items
            ],
            payments=_money_data(data.payments),
            change=_money_data(data.change),
            device_total_usd=data.device_total_usd,
            discount=_discount_data(data.discount),
            customer=None
            if data.customer is None
            else CustomerData(
                data.customer.id, data.customer.name, data.customer.document_id, data.customer.phone
            ),
            customer_id=data.customer_id,
        ),
    )
    db.flush()
    [sale] = sales_for_role(db, [outcome.sale], Role(user.role))
    return {
        **sale.model_dump(mode="json"),
        "alerts_created": outcome.alerts,
        "warnings": outcome.warnings,
    }


sync_service.HANDLERS.update(
    {"cash_session.open": handle_cash_session_open, "sale.create": handle_sale_create}
)


class OutboxOperationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    operation_type: str = Field(min_length=1, max_length=60)
    schema_version: Literal[1]
    created_at: AwareDatetime
    payload: dict[str, Any]


@router.post(
    "/operations",
    response_model=None,
    # Documenta en el OpenAPI las respuestas posibles, para los tipos del frontend.
    responses={200: {"model": SaleAdmin | SaleSeller | CashSessionOut}},
)
def post_operation(
    body: OutboxOperationIn, current: AdminOrSeller, device: CurrentDevice, db: DbSession
) -> JSONResponse:
    """Procesa una operación del mostrador. 200 con el resultado; los rechazos
    permanentes (403 `device_revoked`, 409, 422) llevan el formato de error común."""
    created_at: datetime = body.created_at
    http_status, content = sync_service.process_operation(
        db,
        device=device,
        user=current.user,
        operation=sync_service.Operation(
            id=body.id,
            operation_type=body.operation_type,
            schema_version=body.schema_version,
            created_at=created_at,
            payload=body.payload,
        ),
    )
    db.commit()
    if http_status == 200:
        return JSONResponse(status_code=200, content=content)
    return JSONResponse(status_code=http_status, content={"detail": content})
