"""Validación de cantidades por unidad, sin base de datos (RF-05/FR-020, ADR-0004, R3)."""

from decimal import Decimal

import pytest

from app.domain.units import format_quantity, validate_quantity


def _check(value: str, decimals: int, *, allow_zero=False, allow_negative=False) -> Decimal:
    return validate_quantity(
        Decimal(value), decimals, allow_zero=allow_zero, allow_negative=allow_negative
    )


def test_unidad_entera_rechaza_decimales() -> None:
    """RF-05/FR-020: en `unidad` las cantidades son enteras."""
    with pytest.raises(ValueError, match="enteras"):
        _check("1.5", 0)
    assert _check("3", 0) == Decimal("3")
    assert _check("3.00", 0) == Decimal("3")


def test_metro_admite_centimetros_y_no_mas() -> None:
    """RF-05/FR-020: en `metro` la precisión máxima es el centímetro, sin redondear."""
    with pytest.raises(ValueError, match="2 decimales"):
        _check("0.305", 2)
    assert _check("0.30", 2) == Decimal("0.30")
    assert str(_check("0.3", 2)) == "0.30"


def test_cero_solo_si_se_permite() -> None:
    """FR-019: un ajuste no puede tener cantidad cero; un conteo sí puede anotar cero."""
    with pytest.raises(ValueError, match="cero"):
        _check("0", 2)
    assert _check("0", 2, allow_zero=True) == Decimal("0.00")


def test_negativos_solo_si_se_permiten() -> None:
    """FR-019: los ajustes admiten negativos; el stock mínimo y lo contado, no."""
    with pytest.raises(ValueError, match="negativa"):
        _check("-2", 0)
    assert _check("-2", 0, allow_negative=True) == Decimal("-2")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1E12"])
def test_valores_no_finitos_o_enormes(value: str) -> None:
    with pytest.raises(ValueError):
        _check(value, 2, allow_negative=True)


def test_formato_segun_la_unidad() -> None:
    """ADR-0004: las cantidades viajan como cadenas con los decimales de su unidad."""
    assert format_quantity(Decimal("8.00"), 0) == "8"
    assert format_quantity(Decimal("8"), 2) == "8.00"
    assert format_quantity(Decimal("-0.5"), 2) == "-0.50"
