"""Caja de un equipo: apertura, cuadre, cierre y consulta (RF-27, RF-29 a RF-33, RN-12,
RN-16; research R4, R6, R7 y R9 de la etapa 1.4).

- La apertura llega por la cola (`cash_session.open`) con el id generado en el equipo. Un
  equipo tiene como máximo una caja abierta; quien la abre responde por ella.
- El esperado por método lo calcula `domain/cash_math.py` con los pagos y los egresos de la
  caja; el equipo usa el mismo cálculo (`packages/shared/src/cash.ts`).
- El cierre llega por la cola desde el equipo de la caja, o lo hace el Admin desde otro
  equipo (caja huérfana). En los dos casos el servidor recalcula el esperado, guarda un
  conteo por método y la caja queda inmutable (trigger `cash_session_guard`).
- Las operaciones que el servidor registró después del cierre (`closed_recorded_at`,
  research R7) no cambian el cuadre guardado; el detalle las muestra aparte.
"""

import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import (
    AppUser,
    CashCount,
    CashOutflow,
    CashSession,
    Device,
    OutboxOperation,
    Payment,
    PaymentMethod,
    Sale,
    SaleVoid,
)
from app.domain.business_time import business_date, day_bounds_utc
from app.domain.cash_math import (
    CashMovement,
    MethodInfo,
    OutflowInput,
    ReconciliationRow,
    compute_reconciliation,
)
from app.domain.roles import Role
from app.services.alerts import create_cash_session_alert
from app.services.audit import record_audit
from app.services.devices import device_revoked
from app.services.devices import open_cash_session as current_open_session
from app.services.exchange_rates import applicable_rate, exchange_rate_missing

CENT = Decimal("0.01")
MAX_COUNTED = Decimal("1E14")  # numeric(16, 2)


def open_cash_session(
    db: Session,
    *,
    device: Device,
    user: AppUser,
    operation_id: uuid.UUID,
    session_id: uuid.UUID,
    float_ves: Decimal,
    float_usd: Decimal,
    opened_at: datetime,
) -> CashSession:
    """Abre la caja del equipo. 409 `cash_session_open` si ya hay una abierta y 409
    `exchange_rate_missing` si no hay ninguna tasa BCV cargada (RF-18)."""
    # Un equipo revocado no abre caja, aunque la operación diga ser anterior a la revocación:
    # la hora la escribe el equipo (hallazgo del code review).
    if device.revoked_at is not None:
        raise device_revoked()
    # El bloqueo del equipo serializa dos aperturas simultáneas en el mismo equipo.
    db.execute(select(Device.id).where(Device.id == device.id).with_for_update())
    existing = current_open_session(db, device.id)
    if existing is not None:
        opener = db.get(AppUser, existing.opened_by)
        raise ApiError(
            409,
            "cash_session_open",
            f"Este equipo ya tiene la caja abierta por {opener.full_name}",
            opened_by=opener.full_name,
            opened_at=existing.opened_at.isoformat(),
        )
    day = business_date(opened_at)
    if applicable_rate(db, day) is None:
        raise exchange_rate_missing(day)

    session = CashSession(
        id=session_id,
        device_id=device.id,
        business_date=day,
        opened_by=user.id,
        opened_at=opened_at,
        opening_float_ves=float_ves,
        opening_float_usd=float_usd,
        status="open",
        outbox_operation_id=operation_id,
    )
    db.add(session)
    db.flush()
    record_audit(
        db,
        action="cash_session.opened",
        user_id=user.id,
        device_id=device.id,
        entity_type="cash_session",
        entity_id=session.id,
        after={"opening_float_ves": str(float_ves), "opening_float_usd": str(float_usd)},
    )
    return session


# --- Cuadre (RF-31; FR-006, FR-007; research R1) ----------------------------------------


@dataclass(frozen=True)
class MovementView:
    """Pago, vuelto o devolución de la caja, con su venta, para el detalle (FR-009)."""

    payment: Payment
    sale_number: str
    occurred_at: datetime
    after_close: bool


@dataclass(frozen=True)
class OutflowView:
    outflow: CashOutflow
    after_close: bool


@dataclass(frozen=True)
class ReconciliationView(ReconciliationRow):
    """Fila del cuadre con el nombre del método y, en una caja cerrada, lo guardado en
    `cash_count`: el esperado del servidor, el que vio el equipo y lo contado."""

    method_name: str = ""
    device_expected: Decimal | None = None


def payment_methods(db: Session) -> list[PaymentMethod]:
    return list(db.scalars(select(PaymentMethod).order_by(PaymentMethod.sort_order)))


def _after_close_sale_ids(db: Session, session: CashSession) -> set[uuid.UUID]:
    """Ventas de la caja que el servidor registró después del cierre (research R7). Se
    comparan horas del servidor: un reloj atrasado en el equipo no cuenta."""
    if session.closed_recorded_at is None:
        return set()
    return set(
        db.scalars(
            select(Sale.id).where(
                Sale.cash_session_id == session.id, Sale.synced_at > session.closed_recorded_at
            )
        )
    )


def session_movements(db: Session, session: CashSession) -> list[MovementView]:
    """Todos los pagos con la caja: cobros y vueltos de sus ventas y las devoluciones
    registradas aquí, incluidas las de ventas de otras cajas ya cerradas (RF-27)."""
    after_close = _after_close_sale_ids(db, session)
    rows = db.execute(
        select(Payment, Sale.number, Sale.occurred_at, SaleVoid.voided_at)
        .join(Sale, Sale.id == Payment.sale_id)
        .outerjoin(SaleVoid, SaleVoid.id == Payment.sale_void_id)
        .where(Payment.cash_session_id == session.id)
    ).all()
    views = [
        MovementView(
            payment=payment,
            sale_number=number,
            occurred_at=voided_at or occurred_at,
            after_close=payment.sale_id in after_close,
        )
        for payment, number, occurred_at, voided_at in rows
    ]
    views.sort(key=lambda view: (view.occurred_at, view.sale_number, view.payment.line_number))
    return views


def session_outflows(db: Session, session: CashSession) -> list[OutflowView]:
    rows = db.execute(
        select(CashOutflow, OutboxOperation.received_at)
        .join(OutboxOperation, OutboxOperation.id == CashOutflow.outbox_operation_id)
        .where(CashOutflow.cash_session_id == session.id)
        .order_by(CashOutflow.occurred_at)
    ).all()
    closed = session.closed_recorded_at
    return [
        OutflowView(outflow=outflow, after_close=closed is not None and received_at > closed)
        for outflow, received_at in rows
    ]


def reconcile(
    db: Session,
    session: CashSession,
    *,
    movements: list[MovementView] | None = None,
    outflows: list[OutflowView] | None = None,
) -> list[ReconciliationView]:
    """Cuadre de la caja por método, en el orden del catálogo. Abierta: el esperado actual.
    Cerrada: los componentes sin lo registrado después del cierre y el esperado, el
    contado y la diferencia guardados en `cash_count`, sin recalcular (RF-33)."""
    methods = payment_methods(db)
    if movements is None:
        movements = session_movements(db, session)
    if outflows is None:
        outflows = session_outflows(db, session)
    rows = compute_reconciliation(
        [MethodInfo(code=m.code, currency=m.currency) for m in methods],
        session.opening_float_ves,
        session.opening_float_usd,
        [
            CashMovement(
                method=view.payment.payment_method_code,
                currency=view.payment.currency,
                kind=view.payment.kind,
                amount=view.payment.amount,
            )
            for view in movements
            if not view.after_close
        ],
        [
            OutflowInput(
                method=view.outflow.payment_method_code,
                amount=view.outflow.amount,
                voided=view.outflow.voided_at is not None,
            )
            for view in outflows
            if not view.after_close
        ],
    )
    names = {method.code: method.name for method in methods}
    counts = {}
    if session.status == "closed":
        counts = {
            count.payment_method_code: count
            for count in db.scalars(
                select(CashCount).where(CashCount.cash_session_id == session.id)
            )
        }
    views = []
    for row in rows:
        view = ReconciliationView(**row.__dict__, method_name=names[row.method])
        count = counts.get(row.method)
        if count is not None:
            view = replace(
                view,
                expected=count.expected_amount,
                device_expected=count.device_expected_amount,
                counted=count.counted_amount,
                difference=count.difference,
            )
        views.append(view)
    return views


def expected_for(db: Session, session: CashSession, method: str) -> Decimal:
    """Esperado actual de un método de la caja (tope de los egresos en efectivo, RF-32)."""
    return next(row.expected for row in reconcile(db, session) if row.method == method)


# --- Consulta (FR-024, FR-025; research R9) ---------------------------------------------


def _closed_today_by(actor: AppUser):
    """Cajas que el usuario cerró hoy, hora de Caracas (hora del servidor del cierre)."""
    today = business_date(utcnow())
    start, end = day_bounds_utc(today, today)
    return (
        (CashSession.closed_by == actor.id)
        & (CashSession.closed_recorded_at >= start)
        & (CashSession.closed_recorded_at < end)
    )


def _seller_condition(actor: AppUser, device: Device | None):
    """El Vendedor ve la caja abierta del equipo desde el que consulta y las que él cerró
    hoy; el servidor lo impone en la consulta (FR-025)."""
    conditions = [_closed_today_by(actor)]
    if device is not None:
        conditions.append((CashSession.device_id == device.id) & (CashSession.status == "open"))
    return or_(*conditions)


def visible_session(
    db: Session, *, actor: AppUser, session_id: uuid.UUID, device: Device | None
) -> CashSession:
    """Caja que el usuario puede consultar; para el Vendedor, cualquier otra es 404."""
    query = select(CashSession).where(CashSession.id == session_id)
    if actor.role != Role.ADMIN.value:
        query = query.where(_seller_condition(actor, device))
    session = db.scalar(query)
    if session is None:
        raise ApiError(404, "not_found", "La caja no existe")
    return session


@dataclass(frozen=True)
class CashSessionFilters:
    date_from: date | None = None
    date_to: date | None = None
    device_id: uuid.UUID | None = None
    opened_by: uuid.UUID | None = None
    closed_by: uuid.UUID | None = None
    status: str | None = None  # "open" | "closed"
    with_differences: bool | None = None


def _has_differences():
    return exists().where(CashCount.cash_session_id == CashSession.id, CashCount.difference != 0)


def list_cash_sessions(
    db: Session,
    *,
    actor: AppUser,
    device: Device | None,
    filters: CashSessionFilters,
    page: int,
    page_size: int,
) -> tuple[list[CashSession], int]:
    """Más recientes primero. El Vendedor recibe solo lo que puede ver: los filtros se
    ignoran (FR-025)."""
    conditions = []
    if actor.role == Role.ADMIN.value:
        if filters.date_from:
            conditions.append(CashSession.business_date >= filters.date_from)
        if filters.date_to:
            conditions.append(CashSession.business_date <= filters.date_to)
        if filters.device_id:
            conditions.append(CashSession.device_id == filters.device_id)
        if filters.opened_by:
            conditions.append(CashSession.opened_by == filters.opened_by)
        if filters.closed_by:
            conditions.append(CashSession.closed_by == filters.closed_by)
        if filters.status:
            conditions.append(CashSession.status == filters.status)
        if filters.with_differences is not None:
            differences = _has_differences()
            conditions.append(differences if filters.with_differences else ~differences)
    else:
        conditions.append(_seller_condition(actor, device))
    query = select(CashSession).where(*conditions)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(CashSession.business_date.desc(), CashSession.opened_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def sessions_with_differences(db: Session, session_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not session_ids:
        return set()
    return set(
        db.scalars(
            select(CashCount.cash_session_id)
            .where(CashCount.cash_session_id.in_(session_ids), CashCount.difference != 0)
            .distinct()
        )
    )


@dataclass(frozen=True)
class VoidedAfterClose:
    sale: Sale
    voided_at: datetime
    refund_session: CashSession | None


def voided_after_close(db: Session, session: CashSession) -> list[VoidedAfterClose]:
    """Ventas de la caja anuladas después de su cierre, con la caja que recibió la
    devolución (FR-023). Las dos horas son del servidor."""
    if session.closed_recorded_at is None:
        return []
    rows = db.execute(
        select(Sale, SaleVoid)
        .join(SaleVoid, SaleVoid.sale_id == Sale.id)
        .where(Sale.cash_session_id == session.id, SaleVoid.voided_at > session.closed_recorded_at)
        .order_by(SaleVoid.voided_at)
    ).all()
    result = []
    for sale, sale_void in rows:
        refund_session_id = db.scalar(
            select(Payment.cash_session_id).where(Payment.sale_void_id == sale_void.id).limit(1)
        )
        result.append(
            VoidedAfterClose(
                sale=sale,
                voided_at=sale_void.voided_at,
                refund_session=db.get(CashSession, refund_session_id)
                if refund_session_id
                else None,
            )
        )
    return result


def post_close_sales(db: Session, session: CashSession) -> list[Sale]:
    """Ventas registradas después de un cierre hecho en otro lugar (FR-019, research R7)."""
    ids = _after_close_sale_ids(db, session)
    if not ids:
        return []
    return list(db.scalars(select(Sale).where(Sale.id.in_(ids)).order_by(Sale.occurred_at)))


# --- Cierre (RF-31, RF-33; FR-008 a FR-013, FR-016, FR-018; research R4, R6) -------------


@dataclass(frozen=True)
class CountData:
    method: str
    counted: Decimal
    # Esperado que vio el equipo; None en el cierre del Admin desde otro equipo (R6).
    device_expected: Decimal | None = None


NOTE_MIN, NOTE_MAX = 5, 500


def _validate_counts(
    methods: list[PaymentMethod], counts: list[CountData], prefix: str
) -> dict[str, CountData]:
    codes = [method.code for method in methods]
    by_method: dict[str, CountData] = {}
    for index, count in enumerate(counts):
        field = f"{prefix}counts.{index}"
        if count.method not in codes:
            raise validation_error({f"{field}.method": "El método de pago no existe"})
        if count.method in by_method:
            raise validation_error({f"{field}.method": "El método está repetido"})
        if count.counted < 0:
            raise validation_error({f"{field}.counted": "El monto contado no puede ser negativo"})
        if count.counted >= MAX_COUNTED:
            raise validation_error({f"{field}.counted": "El monto es demasiado grande"})
        if count.counted != count.counted.quantize(CENT):
            raise validation_error({f"{field}.counted": "Admite como máximo 2 decimales"})
        by_method[count.method] = count
    missing = [code for code in codes if code not in by_method]
    if missing:
        raise validation_error({f"{prefix}counts": f"Falta el conteo de {', '.join(missing)}"})
    return by_method


def close_cash_session(
    db: Session,
    *,
    session_id: uuid.UUID,
    actor: AppUser,
    counts: list[CountData],
    note: str | None,
    closed_at: datetime | None,
    device: Device | None,
    operation_id: uuid.UUID | None,
    outside_device: bool,
    field_prefix: str = "payload.",
) -> tuple[CashSession, list[str]]:
    """Cierra la caja en la transacción de la operación: conteos, alertas y auditoría.

    Por la cola (`outside_device = False`), la caja debe ser del equipo. El Admin desde
    otro equipo (`outside_device = True`) cierra cualquier caja abierta, con observación
    siempre obligatoria. Devuelve la caja y los tipos de alerta creados."""
    # Por la cola, un equipo revocado no cierra su caja aunque la operación diga ser
    # anterior a la revocación: la hora la escribe el equipo (revisión de seguridad de la
    # 1.4). La cierra el Admin desde otro equipo (FR-018). Se lee con el equipo bloqueado,
    # para ver una revocación confirmada mientras llegaba la operación.
    if device is not None:
        device = db.get(Device, device.id, with_for_update=True, populate_existing=True)
    if not outside_device and device is not None and device.revoked_at is not None:
        raise device_revoked()
    session = db.get(CashSession, session_id, with_for_update=True, populate_existing=True)
    if session is None:
        if outside_device:
            raise ApiError(404, "not_found", "La caja no existe")
        raise _unavailable()
    if not outside_device and (device is None or session.device_id != device.id):
        raise _unavailable()
    if session.status == "closed":
        raise ApiError(409, "cash_session_closed", "La caja ya está cerrada")

    methods = payment_methods(db)
    by_method = _validate_counts(methods, counts, field_prefix)
    rows = reconcile(db, session)
    expected = {row.method: row.expected for row in rows}
    # La observación se exige según lo que vio el usuario (FR-010); si el servidor ve otra
    # diferencia, la avisa `expected_mismatch` (FR-012).
    seen_difference = any(
        count.counted
        != (count.device_expected if count.device_expected is not None else expected[method])
        for method, count in by_method.items()
    )
    if note is not None and not NOTE_MIN <= len(note) <= NOTE_MAX:
        message = f"La observación debe tener entre {NOTE_MIN} y {NOTE_MAX} caracteres"
        raise validation_error({f"{field_prefix}note": message})
    if note is None and (outside_device or seen_difference):
        message = (
            "Escribe una observación: la caja se cierra fuera de su equipo"
            if outside_device
            else "Escribe una observación: hay diferencias en el cierre"
        )
        raise validation_error({f"{field_prefix}note": message})

    session.status = "closed"
    recorded_at = utcnow()
    session.closed_at = closed_at or recorded_at
    session.closed_recorded_at = recorded_at
    session.closed_by = actor.id
    session.closed_from_device_id = device.id if device is not None else None
    session.closed_outside_device = outside_device
    session.closing_note = note
    session.closing_operation_id = operation_id
    db.flush()
    summary = []
    for row in rows:
        count = by_method[row.method]
        difference = count.counted - row.expected
        db.add(
            CashCount(
                id=uuid.uuid7(),
                cash_session_id=session.id,
                payment_method_code=row.method,
                currency=row.currency,
                expected_amount=row.expected,
                device_expected_amount=count.device_expected,
                counted_amount=count.counted,
                difference=difference,
            )
        )
        summary.append(
            {
                "method": row.method,
                "currency": row.currency,
                "expected": str(row.expected),
                "device_expected": None
                if count.device_expected is None
                else str(count.device_expected),
                "counted": str(count.counted),
                "difference": str(difference),
            }
        )
    db.flush()

    alerts = []
    differences = [item for item in summary if Decimal(item["difference"]) != 0]
    if differences:
        create_cash_session_alert(
            db, type="cash_difference", session=session, details={"differences": differences}
        )
        alerts.append("cash_difference")
    mismatches = [
        item
        for item in summary
        if item["device_expected"] is not None
        and Decimal(item["device_expected"]) != Decimal(item["expected"])
    ]
    if mismatches:
        create_cash_session_alert(
            db, type="expected_mismatch", session=session, details={"methods": mismatches}
        )
        alerts.append("expected_mismatch")
    record_audit(
        db,
        action="cash_session.closed",
        user_id=actor.id,
        device_id=device.id if device is not None else None,
        entity_type="cash_session",
        entity_id=session.id,
        after={
            "counts": summary,
            "note": note,
            "outside_device": outside_device,
            "closed_from_device_id": None if device is None else str(device.id),
        },
    )
    return session, alerts


def _unavailable() -> ApiError:
    return ApiError(
        409, "cash_session_unavailable", "La caja indicada no está abierta en este equipo"
    )
