"""Endpoints de la tasa BCV (RF-17, RN-15; FR-025 a FR-028), adelantados de la etapa 1.3.

Contrato: specs/003-proveedores-compras/contracts/api.md.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import CurrentUser, DbSession, require_roles
from app.api.product_schemas import UserRef, user_ref
from app.core.errors import ApiError
from app.db.models import ExchangeRate
from app.domain.roles import Role
from app.services import exchange_rates as rates_service
from app.services.users import users_by_id

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])

Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]
AdminOrWarehouse = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.WAREHOUSE))]


class RateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_date: date
    rate: Decimal


class RateCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rate: Decimal


class ExchangeRateOut(BaseModel):
    id: uuid.UUID
    rate_type: str
    business_date: date
    rate: str
    created_by: UserRef | None
    created_at: datetime
    updated_by: UserRef | None
    updated_at: datetime | None


class ExchangeRatePage(BaseModel):
    items: list[ExchangeRateOut]
    total: int
    page: int
    page_size: int


class ApplicableRateOut(BaseModel):
    rate: str
    business_date: date


def _rate_str(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.00000001")))


def rates_out(db: DbSession, rows: list[ExchangeRate]) -> list[ExchangeRateOut]:
    users = users_by_id(db, {r.created_by for r in rows} | {r.updated_by for r in rows})
    return [
        ExchangeRateOut(
            id=row.id,
            rate_type=row.rate_type,
            business_date=row.business_date,
            rate=_rate_str(row.rate),
            created_by=user_ref(users.get(row.created_by)),
            created_at=row.created_at,
            updated_by=user_ref(users.get(row.updated_by)) if row.updated_by else None,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("")
def list_rates(
    current: Admin,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ExchangeRatePage:
    rows, total = rates_service.list_rates(db, page=page, page_size=page_size)
    return ExchangeRatePage(items=rates_out(db, rows), total=total, page=page, page_size=page_size)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_rate(body: RateCreate, current: Admin, db: DbSession) -> ExchangeRateOut:
    row = rates_service.create_rate(
        db, actor=current.user, on_date=body.business_date, rate=body.rate
    )
    return rates_out(db, [row])[0]


@router.get("/applicable")
def applicable_rate(
    current: AdminOrWarehouse, db: DbSession, on_date: Annotated[date, Query(alias="date")]
) -> ApplicableRateOut:
    """La tasa que usaría una compra con esa fecha (FR-012)."""
    rate = rates_service.applicable_rate(db, on_date)
    if rate is None:
        raise ApiError(404, "not_found", "No hay tasa BCV cargada en o antes de esa fecha")
    return ApplicableRateOut(rate=_rate_str(rate.rate), business_date=rate.business_date)


@router.put("/{business_date}")
def correct_rate(
    business_date: date, body: RateCorrection, current: Admin, db: DbSession
) -> ExchangeRateOut:
    row = rates_service.correct_rate(db, actor=current.user, on_date=business_date, rate=body.rate)
    return rates_out(db, [row])[0]
