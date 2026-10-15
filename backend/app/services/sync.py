"""Cola de salida del mostrador: idempotencia y despacho de operaciones (FR-017, FR-018;
ADR-0003, research R4).

Cada operación trae un UUIDv7 generado en el equipo. `process_operation`:

1. bloquea esa clave con un candado de transacción, así dos envíos simultáneos de la
   misma operación se procesan en serie;
2. si la operación ya se procesó, devuelve la respuesta guardada sin volver a aplicarla;
3. si no, la despacha a su manejador y guarda en `outbox_operation` la respuesta, tanto
   si se procesó como si se rechazó por una regla estructural (403 `device_revoked`, 409
   o 422). Esos rechazos son permanentes y se repiten igual en un reenvío.

Cualquier otro error se propaga sin guardar nada: es transitorio y el equipo reintenta.
La fila de la cola y lo que crea el manejador se confirman en la misma transacción.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError
from app.db.models import AppUser, Device, OutboxOperation
from app.services.devices import ensure_active


@dataclass(frozen=True)
class Operation:
    id: uuid.UUID
    operation_type: str
    schema_version: int
    created_at: datetime
    payload: dict[str, Any]


Handler = Callable[[Session, Device, AppUser, Operation], dict[str, Any]]

# Manejadores por tipo de operación. Los registra la capa de la API (`app/api/sync.py`):
# validan el contenido, llaman al servicio y devuelven la respuesta en JSON.
HANDLERS: dict[str, Handler] = {}


def _is_permanent(error: ApiError) -> bool:
    return error.status_code in (409, 422) or error.code == "device_revoked"


def _error_body(error: ApiError) -> dict[str, Any]:
    return {"code": error.code, "message": error.message, **error.extra}


def process_operation(
    db: Session, *, device: Device, user: AppUser, operation: Operation
) -> tuple[int, dict[str, Any]]:
    """Devuelve el código HTTP y el cuerpo de la respuesta (el resultado, o el error con
    `code` y `message`). No confirma la transacción."""
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": str(operation.id)})
    stored = db.get(OutboxOperation, operation.id, populate_existing=True)
    if stored is not None:
        return stored.http_status, stored.result if stored.result is not None else stored.error

    received_at = utcnow()
    savepoint = db.begin_nested()
    try:
        ensure_active(device, at=operation.created_at)
        handler = HANDLERS.get(operation.operation_type)
        if handler is None:
            raise ApiError(
                409,
                "operation_type_unknown",
                "El tipo de operación no se reconoce: actualiza la app",
                operation_type=operation.operation_type,
            )
        result = handler(db, device, user, operation)
        savepoint.commit()
        status, http_status, error = "processed", 200, None
    except ApiError as exc:
        savepoint.rollback()
        if not _is_permanent(exc):
            raise
        status, http_status, result, error = "rejected", exc.status_code, None, _error_body(exc)

    db.add(
        OutboxOperation(
            id=operation.id,
            device_id=device.id,
            user_id=user.id,
            operation_type=operation.operation_type,
            schema_version=operation.schema_version,
            payload=operation.payload,
            created_at_device=operation.created_at,
            received_at=received_at,
            processed_at=utcnow(),
            status=status,
            http_status=http_status,
            result=result,
            error=error,
        )
    )
    db.flush()
    return http_status, result if result is not None else error
