"""SKU automático por categoría (RF-02/FR-002 a FR-004, SC-006, research R1)."""

import pytest

from app.domain.sku import format_sku


def test_formato_del_sku() -> None:
    """RF-02/FR-002: prefijo y correlativo de al menos 4 dígitos."""
    assert format_sku("MAN", 1) == "MAN-0001"
    assert format_sku("MAN", 9999) == "MAN-9999"
    assert format_sku("MAN", 10000) == "MAN-10000"


def test_el_correlativo_empieza_en_uno() -> None:
    with pytest.raises(ValueError):
        format_sku("MAN", 0)
