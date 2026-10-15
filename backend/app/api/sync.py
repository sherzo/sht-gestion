"""Cola de salida del mostrador (FR-017, FR-018; ADR-0003, research R4).

Contrato: specs/004-ventas-multimoneda/contracts/api.md. Una operación por petición,
idempotente por su `id`: reenviarla devuelve la misma respuesta, también si se rechazó.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.api.deps import CurrentDevice, CurrentUser, DbSession, require_roles
from app.api.sale_schemas import cash_session_out
from app.core.errors import validation_error, validation_fields
from app.db.models import AppUser, Device
from app.domain.money import MAX_PRICE, MAX_VES, PRICE_DECIMALS, VES_DECIMALS, validate_usd
from app.domain.roles import Role
from app.services import cash_sessions as cash_sessions_service
from app.services import sync as sync_service

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


sync_service.HANDLERS.update({"cash_session.open": handle_cash_session_open})


class OutboxOperationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    operation_type: str = Field(min_length=1, max_length=60)
    schema_version: Literal[1]
    created_at: AwareDatetime
    payload: dict[str, Any]


@router.post("/operations", response_model=None)
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
