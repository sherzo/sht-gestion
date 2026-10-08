"""Reloj único de la API.

Los servicios leen la hora solo desde aquí, para que las pruebas puedan simular el paso
del tiempo (jornada de 12 horas, bloqueos de 15 minutos) con `advance`.
"""

from datetime import UTC, datetime, timedelta

_offset = timedelta(0)


def utcnow() -> datetime:
    return datetime.now(UTC) + _offset


def advance(delta: timedelta) -> None:
    """Adelanta el reloj (solo pruebas)."""
    global _offset
    _offset += delta


def reset() -> None:
    global _offset
    _offset = timedelta(0)
