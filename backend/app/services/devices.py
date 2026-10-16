"""Equipos de mostrador (FR-001 a FR-004; RN-11, ADR-0003, research R3).

El Admin registra el equipo desde su navegador: recibe una serie que nunca se reutiliza y
un token que se muestra una sola vez (solo se guarda su SHA-256). Cada operación de
mostrador envía el token en `X-Device-Token`.
"""

import hashlib
import secrets
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError
from app.db.models import AppUser, CashSession, Device, SequenceCounter
from app.domain.series import series_for
from app.services.audit import record_audit

SERIES_COUNTER = "device_series"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def device_required() -> ApiError:
    return ApiError(403, "device_required", "Este equipo no está registrado para vender")


def device_revoked() -> ApiError:
    return ApiError(
        403,
        "device_revoked",
        "Este equipo fue revocado: el administrador debe registrarlo de nuevo",
    )


def register_device(db: Session, *, actor: AppUser, name: str) -> tuple[Device, str]:
    """Crea el equipo con la siguiente serie y devuelve el token en claro (una sola vez)."""
    counter = db.get(SequenceCounter, SERIES_COUNTER, with_for_update=True)
    series = series_for(counter.next_number)
    counter.next_number += 1
    token = secrets.token_urlsafe(32)
    device = Device(
        id=uuid.uuid7(),
        name=name.strip(),
        series=series,
        last_sequence_number=0,
        token_hash=hash_token(token),
        registered_by=actor.id,
        registered_at=utcnow(),
    )
    db.add(device)
    db.flush()
    record_audit(
        db,
        action="device.registered",
        user_id=actor.id,
        device_id=device.id,
        entity_type="device",
        entity_id=device.id,
        after={"name": device.name, "series": series},
    )
    return device, token


def revoke_device(db: Session, *, actor: AppUser, device_id: uuid.UUID) -> Device:
    device = db.get(Device, device_id, with_for_update=True)
    if device is None:
        raise ApiError(404, "not_found", "El equipo no existe")
    if device.revoked_at is not None:
        raise ApiError(409, "invalid_state", "El equipo ya estaba revocado")
    device.revoked_at = utcnow()
    device.revoked_by = actor.id
    record_audit(
        db,
        action="device.revoked",
        user_id=actor.id,
        device_id=device.id,
        entity_type="device",
        entity_id=device.id,
        before={"revoked_at": None},
        after={"revoked_at": device.revoked_at.isoformat()},
    )
    return device


def list_devices(db: Session) -> list[Device]:
    """Vigentes primero, y dentro de cada grupo por serie."""
    return list(
        db.scalars(
            select(Device).order_by(Device.revoked_at.is_not(None), Device.registered_at)
        ).all()
    )


def device_from_token(db: Session, token: str | None) -> Device:
    """Equipo del token, aunque esté revocado: la cola decide con la hora de la operación
    (FR-002) y los demás endpoints llaman además a `ensure_active`. Las operaciones de
    caja de la cola (`STRICT_TYPES` en `services/sync.py`) rechazan cualquier equipo
    revocado, sin mirar la hora (la escribe el equipo; etapa 1.4)."""
    if not token:
        raise device_required()
    device = db.scalar(select(Device).where(Device.token_hash == hash_token(token)))
    if device is None:
        raise device_required()
    return device


def ensure_active(device: Device, *, at: datetime | None = None) -> None:
    """Rechaza un equipo revocado, salvo para operaciones creadas antes de la revocación
    (`at`). Solo la venta usa esa excepción: para apertura, egreso y cierre de caja,
    `services/sync.py` la llama sin `at` (`STRICT_TYPES`)."""
    if device.revoked_at is not None and (at is None or at >= device.revoked_at):
        raise device_revoked()


def open_cash_session(db: Session, device_id: uuid.UUID) -> CashSession | None:
    return db.scalar(
        select(CashSession).where(CashSession.device_id == device_id, CashSession.status == "open")
    )
