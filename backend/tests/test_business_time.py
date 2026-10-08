"""Fecha de negocio en America/Caracas (RNF-07, arquitectura §4.2)."""

from datetime import UTC, date, datetime

from app.domain.business_time import business_date, day_bounds_utc


def test_noche_en_caracas_sigue_siendo_el_mismo_dia() -> None:
    # 23:30 del 07/10 en Caracas (UTC-4) son las 03:30 UTC del 08/10.
    instant = datetime(2026, 10, 8, 3, 30, tzinfo=UTC)
    assert business_date(instant) == date(2026, 10, 7)


def test_limites_de_un_dia_en_utc() -> None:
    start, end = day_bounds_utc(date(2026, 10, 7), date(2026, 10, 7))
    assert start == datetime(2026, 10, 7, 4, 0, tzinfo=UTC)
    assert end == datetime(2026, 10, 8, 4, 0, tzinfo=UTC)


def test_limites_de_un_rango_incluyen_el_ultimo_dia() -> None:
    start, end = day_bounds_utc(date(2026, 10, 1), date(2026, 10, 7))
    assert start == datetime(2026, 10, 1, 4, 0, tzinfo=UTC)
    assert end == datetime(2026, 10, 8, 4, 0, tzinfo=UTC)
