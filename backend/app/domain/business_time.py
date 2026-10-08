"""Fecha de negocio en America/Caracas (arquitectura §4.2, RNF-07).

Único lugar del backend donde se convierte entre instantes UTC y días de negocio.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

CARACAS = ZoneInfo("America/Caracas")


def business_date(instant: datetime) -> date:
    return instant.astimezone(CARACAS).date()


def day_bounds_utc(start: date, end: date) -> tuple[datetime, datetime]:
    """Inicio del día `start` y fin exclusivo del día `end` (inclusivo), en UTC."""
    begin = datetime.combine(start, time.min, tzinfo=CARACAS)
    finish = datetime.combine(end + timedelta(days=1), time.min, tzinfo=CARACAS)
    return begin.astimezone(UTC), finish.astimezone(UTC)
