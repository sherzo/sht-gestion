"""Regla de bloqueo por intentos fallidos (FR-004, FR-028, research R6).

Tras 5 fallos seguidos, bloqueo de 15 minutos. Mientras dura, ni la credencial correcta
sirve. Un acierto reinicia la cuenta.
"""

from datetime import datetime, timedelta

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15
LOCK_DURATION = timedelta(minutes=LOCK_MINUTES)


def is_locked(locked_until: datetime | None, now: datetime) -> bool:
    return locked_until is not None and now < locked_until


def register_failure(attempts: int, now: datetime) -> tuple[int, datetime | None]:
    """Suma un fallo al contador (PIN). Devuelve el contador nuevo y el bloqueo, si hay."""
    attempts += 1
    locked_until = now + LOCK_DURATION if attempts >= MAX_ATTEMPTS else None
    return attempts, locked_until


def login_locked_until(
    consecutive_failures: int, last_failure_at: datetime | None
) -> datetime | None:
    """Bloqueo de inicio de sesión calculado desde la auditoría (por nombre de usuario).

    `consecutive_failures` son los fallos desde el último acierto con ese nombre.
    """
    if consecutive_failures < MAX_ATTEMPTS or last_failure_at is None:
        return None
    return last_failure_at + LOCK_DURATION
