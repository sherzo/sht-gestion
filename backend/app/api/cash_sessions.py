"""Consulta de cajas y cierre del Admin desde otro equipo (RF-31, RF-33; FR-018, FR-024 a
FR-026; research R6 y R9 de la etapa 1.4).

Contrato: specs/005-cierre-caja/contracts/api.md. La apertura, los egresos y el cierre
desde el equipo de la caja llegan por la cola de salida (`POST /sync/operations`). La caja
no tiene costos ni márgenes: el mismo esquema sirve para el Admin y el Vendedor.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.cash_schemas import (
    CashSessionClosed,
    CashSessionDetail,
    CashSessionPage,
    cash_session_detail,
    summaries_out,
)
from app.api.deps import CurrentUser, DbSession, OptionalDevice, require_roles
from app.domain.roles import Role
from app.services import cash_sessions as cash_service

router = APIRouter(prefix="/cash-sessions", tags=["cash-sessions"])

Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]
AdminOrSeller = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.SELLER))]


@router.get("")
def list_cash_sessions(
    current: AdminOrSeller,
    device: OptionalDevice,
    db: DbSession,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    device_id: uuid.UUID | None = None,
    opened_by: uuid.UUID | None = None,
    closed_by: uuid.UUID | None = None,
    status: Literal["open", "closed"] | None = None,
    with_differences: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> CashSessionPage:
    """Más recientes primero. El Vendedor recibe solo la caja abierta del equipo desde el
    que consulta y las cajas que él cerró hoy: los filtros se ignoran (FR-025)."""
    rows, total = cash_service.list_cash_sessions(
        db,
        actor=current.user,
        device=device,
        filters=cash_service.CashSessionFilters(
            date_from=date_from,
            date_to=date_to,
            device_id=device_id,
            opened_by=opened_by,
            closed_by=closed_by,
            status=status,
            with_differences=with_differences,
        ),
        page=page,
        page_size=page_size,
    )
    return CashSessionPage(
        items=summaries_out(db, rows), total=total, page=page, page_size=page_size
    )


@router.get("/{session_id}")
def get_cash_session(
    session_id: uuid.UUID, current: AdminOrSeller, device: OptionalDevice, db: DbSession
) -> CashSessionDetail:
    session = cash_service.visible_session(
        db, actor=current.user, session_id=session_id, device=device
    )
    return cash_session_detail(db, session)


class AdminCountIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = Field(min_length=1, max_length=30)
    counted: Decimal


class AdminCloseIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    counts: list[AdminCountIn] = Field(max_length=6)
    note: str = Field(min_length=5, max_length=500)


@router.post("/{session_id}/close")
def close_cash_session(
    session_id: uuid.UUID,
    body: AdminCloseIn,
    current: Admin,
    device: OptionalDevice,
    db: DbSession,
) -> CashSessionClosed:
    """Cierre de una caja de otro equipo, vigente o revocado (caja huérfana, FR-018). La
    observación es obligatoria y el cierre queda marcado como hecho fuera del equipo."""
    session, alerts = cash_service.close_cash_session(
        db,
        session_id=session_id,
        actor=current.user,
        counts=[cash_service.CountData(method=c.method, counted=c.counted) for c in body.counts],
        note=body.note,
        closed_at=None,  # la del servidor, igual a closed_recorded_at (R6)
        device=device,
        operation_id=None,
        outside_device=True,
        field_prefix="",
    )
    db.commit()
    db.expire_all()
    detail = cash_session_detail(db, session)
    return CashSessionClosed(**detail.model_dump(), alerts_created=alerts)
