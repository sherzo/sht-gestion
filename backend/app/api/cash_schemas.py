"""Esquemas de cajas, egresos y cuadre (contrato: specs/005-cierre-caja/contracts/api.md).
Decimales como cadenas (ADR-0004); fechas ISO. La caja no tiene costos ni márgenes: el
mismo esquema sirve para todos los roles (research R9)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.product_schemas import UserRef, user_ref
from app.core.clock import utcnow
from app.db.models import CashOutflow, CashSession, Device
from app.domain.business_time import business_date
from app.services import cash_sessions as cash_service
from app.services.users import users_by_id


def _str(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


class DeviceBrief(BaseModel):
    id: uuid.UUID
    name: str
    series: str


class DeviceName(BaseModel):
    id: uuid.UUID
    name: str


class OutflowVoidOut(BaseModel):
    reason: str
    voided_by: UserRef
    voided_at: datetime


class CashOutflowOut(BaseModel):
    id: uuid.UUID
    cash_session_id: uuid.UUID
    method: str
    currency: str
    amount: str
    reason: str
    reference: str | None
    created_by: UserRef
    occurred_at: datetime
    void: OutflowVoidOut | None


class ReconciliationRowOut(BaseModel):
    method: str
    method_name: str
    currency: str
    opening: str
    collected: str
    change_given: str
    refunded: str
    change_recovered: str
    outflows: str
    expected: str
    device_expected: str | None
    counted: str | None
    difference: str | None


class CashSessionSummary(BaseModel):
    id: uuid.UUID
    device: DeviceBrief
    business_date: date
    status: str
    opened_by: UserRef
    opened_at: datetime
    closed_by: UserRef | None
    closed_at: datetime | None
    closed_outside_device: bool | None
    has_differences: bool
    opened_on_previous_day: bool


class CashSessionPage(BaseModel):
    items: list[CashSessionSummary]
    total: int
    page: int
    page_size: int


class SaleRefOut(BaseModel):
    id: uuid.UUID
    number: str


class CashMovementOut(BaseModel):
    sale: SaleRefOut
    kind: str
    method: str
    currency: str
    amount: str
    reference: str | None
    occurred_at: datetime
    after_close: bool


class RefundSessionOut(BaseModel):
    id: uuid.UUID
    device: DeviceName


class VoidedAfterCloseOut(BaseModel):
    sale: SaleRefOut
    voided_at: datetime
    refund_cash_session: RefundSessionOut | None


class PostCloseOperationOut(BaseModel):
    type: str  # "sale" | "cash_outflow"
    id: uuid.UUID
    number: str | None = None
    occurred_at: datetime
    method: str | None = None
    amount: str | None = None


class CashSessionDetail(CashSessionSummary):
    opening_float_ves: str
    opening_float_usd: str
    closed_from_device: DeviceName | None
    closing_note: str | None
    reconciliation: list[ReconciliationRowOut]
    movements: list[CashMovementOut]
    outflows: list[CashOutflowOut]
    voided_after_close: list[VoidedAfterCloseOut]
    post_close_operations: list[PostCloseOperationOut]


class CashSessionClosed(CashSessionDetail):
    """Respuesta del cierre: el detalle de la caja cerrada y las alertas creadas."""

    alerts_created: list[str]


def opened_on_previous_day(session: CashSession) -> bool:
    return session.status == "open" and session.business_date != business_date(utcnow())


def outflows_out(db: Session, outflows: list[CashOutflow]) -> list[CashOutflowOut]:
    users = users_by_id(
        db,
        {o.created_by for o in outflows} | {o.voided_by for o in outflows if o.voided_by},
    )
    return [
        CashOutflowOut(
            id=o.id,
            cash_session_id=o.cash_session_id,
            method=o.payment_method_code,
            currency=o.currency,
            amount=str(o.amount),
            reason=o.reason,
            reference=o.reference,
            created_by=user_ref(users[o.created_by]),
            occurred_at=o.occurred_at,
            void=None
            if o.voided_at is None
            else OutflowVoidOut(
                reason=o.void_reason, voided_by=user_ref(users[o.voided_by]), voided_at=o.voided_at
            ),
        )
        for o in outflows
    ]


def summaries_out(db: Session, sessions: list[CashSession]) -> list[CashSessionSummary]:
    devices = {
        device.id: device
        for device in db.scalars(
            select(Device).where(Device.id.in_({s.device_id for s in sessions}))
        )
    }
    users = users_by_id(
        db, {s.opened_by for s in sessions} | {s.closed_by for s in sessions if s.closed_by}
    )
    differences = cash_service.sessions_with_differences(db, [s.id for s in sessions])
    return [
        CashSessionSummary(
            id=s.id,
            device=DeviceBrief(
                id=s.device_id, name=devices[s.device_id].name, series=devices[s.device_id].series
            ),
            business_date=s.business_date,
            status=s.status,
            opened_by=user_ref(users[s.opened_by]),
            opened_at=s.opened_at,
            closed_by=user_ref(users[s.closed_by]) if s.closed_by else None,
            closed_at=s.closed_at,
            closed_outside_device=s.closed_outside_device,
            has_differences=s.id in differences,
            opened_on_previous_day=opened_on_previous_day(s),
        )
        for s in sessions
    ]


def _device_name(db: Session, device_id: uuid.UUID | None) -> DeviceName | None:
    device = db.get(Device, device_id) if device_id else None
    return None if device is None else DeviceName(id=device.id, name=device.name)


def cash_session_detail(db: Session, session: CashSession) -> CashSessionDetail:
    movements = cash_service.session_movements(db, session)
    outflows = cash_service.session_outflows(db, session)
    rows = cash_service.reconcile(db, session, movements=movements, outflows=outflows)
    post_close = [
        PostCloseOperationOut(
            type="sale", id=sale.id, number=sale.number, occurred_at=sale.occurred_at
        )
        for sale in cash_service.post_close_sales(db, session)
    ] + [
        PostCloseOperationOut(
            type="cash_outflow",
            id=view.outflow.id,
            occurred_at=view.outflow.occurred_at,
            method=view.outflow.payment_method_code,
            amount=str(view.outflow.amount),
        )
        for view in outflows
        if view.after_close
    ]
    voided = [
        VoidedAfterCloseOut(
            sale=SaleRefOut(id=item.sale.id, number=item.sale.number),
            voided_at=item.voided_at,
            refund_cash_session=None
            if item.refund_session is None
            else RefundSessionOut(
                id=item.refund_session.id,
                device=_device_name(db, item.refund_session.device_id),
            ),
        )
        for item in cash_service.voided_after_close(db, session)
    ]
    summary = summaries_out(db, [session])[0]
    return CashSessionDetail(
        **summary.model_dump(),
        opening_float_ves=str(session.opening_float_ves),
        opening_float_usd=str(session.opening_float_usd),
        closed_from_device=_device_name(db, session.closed_from_device_id),
        closing_note=session.closing_note,
        reconciliation=[
            ReconciliationRowOut(
                method=row.method,
                method_name=row.method_name,
                currency=row.currency,
                opening=str(row.opening),
                collected=str(row.collected),
                change_given=str(row.change_given),
                refunded=str(row.refunded),
                change_recovered=str(row.change_recovered),
                outflows=str(row.outflows),
                expected=str(row.expected),
                device_expected=_str(row.device_expected),
                counted=_str(row.counted),
                difference=_str(row.difference),
            )
            for row in rows
        ],
        movements=[
            CashMovementOut(
                sale=SaleRefOut(id=view.payment.sale_id, number=view.sale_number),
                kind=view.payment.kind,
                method=view.payment.payment_method_code,
                currency=view.payment.currency,
                amount=str(view.payment.amount),
                reference=view.payment.reference,
                occurred_at=view.occurred_at,
                after_close=view.after_close,
            )
            for view in movements
        ],
        outflows=outflows_out(db, [view.outflow for view in outflows]),
        voided_after_close=voided,
        post_close_operations=post_close,
    )
