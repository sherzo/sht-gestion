"""Egresos de caja (RF-32, PRD v0.12; FR-001 a FR-004; research R3 de la etapa 1.4).

Un egreso es dinero que sale de la caja sin ser vuelto ni devolución: agua, limpieza, un
delivery, un retiro del dueño. Llega por la cola (`cash_outflow.create`) con el id
generado en el equipo y queda a nombre del usuario de la sesión, sin autorización del
Admin (Clarifications). Puede salir de cualquier método: los que no son en efectivo exigen
referencia (RF-24) y solo el efectivo tiene tope, el esperado del método en la caja, porque
las cuentas pueden tener dinero de otros días.

Solo el Admin lo anula, con motivo y con la caja abierta; nunca se borra (RF-33, RN-12).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import AppUser, CashOutflow, CashSession, Device, PaymentMethod
from app.services.alerts import create_cash_session_alert
from app.services.audit import record_audit
from app.services.cash_sessions import expected_for


def register_outflow(
    db: Session,
    *,
    device: Device,
    user: AppUser,
    operation_id: uuid.UUID,
    outflow_id: uuid.UUID,
    cash_session_id: uuid.UUID,
    method_code: str,
    amount: Decimal,
    reason: str,
    reference: str | None,
    occurred_at: datetime,
) -> CashOutflow:
    """Registra el egreso en la caja del equipo. Rechazos permanentes: 409
    `cash_session_unavailable` (caja ajena o inexistente), 409 `cash_session_closed`, 409
    `insufficient_cash` (efectivo) y 422 (método o referencia)."""
    db.execute(select(Device.id).where(Device.id == device.id).with_for_update())
    session = db.get(CashSession, cash_session_id, with_for_update=True, populate_existing=True)
    if session is None or session.device_id != device.id:
        raise ApiError(
            409, "cash_session_unavailable", "La caja del egreso no está abierta en este equipo"
        )
    # Un egreso creado en el equipo antes de un cierre hecho en otro lugar se registra
    # igual, con alerta (research R7): el dinero ya salió.
    late = session.status == "closed"
    if late and not occurred_at < session.closed_at:
        raise ApiError(409, "cash_session_closed", "La caja ya está cerrada: abre una caja nueva")

    method = db.get(PaymentMethod, method_code)
    if method is None:
        raise validation_error({"payload.method": "El método de pago no existe"})
    if method.requires_reference and not reference:
        raise validation_error({"payload.reference": "Este método exige la referencia"})
    if method.is_cash and not late:
        available = expected_for(db, session, method.code)
        if amount > available:
            raise ApiError(
                409,
                "insufficient_cash",
                f"El egreso supera el efectivo disponible en {method.name}",
                available=str(max(available, Decimal("0.00"))),
                currency=method.currency,
            )

    outflow = CashOutflow(
        id=outflow_id,
        cash_session_id=session.id,
        device_id=device.id,
        payment_method_code=method.code,
        currency=method.currency,
        amount=amount,
        reason=reason,
        reference=reference or None,
        created_by=user.id,
        occurred_at=occurred_at,
        outbox_operation_id=operation_id,
    )
    db.add(outflow)
    db.flush()
    record_audit(
        db,
        action="cash_outflow.created",
        user_id=user.id,
        device_id=device.id,
        entity_type="cash_outflow",
        entity_id=outflow.id,
        after={
            "cash_session_id": str(session.id),
            "method": method.code,
            "amount": str(amount),
            "currency": method.currency,
            "reason": reason,
            "reference": outflow.reference,
        },
    )
    if late:
        create_cash_session_alert(
            db,
            type="post_close_operation",
            session=session,
            details={
                "operation": "cash_outflow",
                "outflow_id": str(outflow.id),
                "amount": str(amount),
                "currency": method.currency,
                "method": method.code,
            },
        )
    return outflow


def void_outflow(db: Session, *, actor: AppUser, outflow_id: uuid.UUID, reason: str) -> CashOutflow:
    """Anula el egreso: queda visible como anulado y deja de restar del esperado (RF-33)."""
    outflow = db.get(CashOutflow, outflow_id, with_for_update=True)
    if outflow is None:
        raise ApiError(404, "not_found", "El egreso no existe")
    session = db.get(CashSession, outflow.cash_session_id, with_for_update=True)
    if outflow.voided_at is not None:
        raise ApiError(409, "invalid_state", "El egreso ya estaba anulado")
    if session.status != "open":
        raise ApiError(
            409, "cash_session_closed", "La caja del egreso ya está cerrada: no se puede anular"
        )
    outflow.voided_at = utcnow()
    outflow.voided_by = actor.id
    outflow.void_reason = reason
    db.flush()
    record_audit(
        db,
        action="cash_outflow.voided",
        user_id=actor.id,
        entity_type="cash_outflow",
        entity_id=outflow.id,
        before={"amount": str(outflow.amount), "method": outflow.payment_method_code},
        after={"status": "voided"},
        reason=reason,
    )
    return outflow
