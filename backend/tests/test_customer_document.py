"""Documento del cliente: cédula o RIF (RF-28/FR-019, research R11). Sin base de datos."""

import pytest

from app.domain.customer_document import normalize_document


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("v12345678", "V-12345678"),
        ("V 12.345.678", "V-12345678"),
        ("E-1234567", "E-1234567"),
        ("V-123456", "V-123456"),
        ("V-12345678-9", "V-12345678-9"),
        ("v12345678-9", "V-12345678-9"),
        ("j-40123456-7", "J-40123456-7"),
        ("J401234567", "J-40123456-7"),
        ("g200001234", "G-20000123-4"),
    ],
)
def test_normaliza(raw: str, expected: str) -> None:
    assert normalize_document(raw) == expected


def test_v_con_nueve_digitos_sin_guiones_pide_los_guiones() -> None:
    """A2 del análisis: con V o E siempre es cédula; el RIF natural va con guiones."""
    with pytest.raises(ValueError, match="escribe los guiones"):
        normalize_document("V123456789")


@pytest.mark.parametrize("raw", ["V-12345", "X-12345678", "", "12345678", "V-1234A678"])
def test_rechaza(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_document(raw)
