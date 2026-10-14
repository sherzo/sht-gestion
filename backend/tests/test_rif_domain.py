"""Normalización del RIF (RF-13/FR-002, research R5). Sin base de datos."""

import pytest

from app.domain.rif import normalize_rif


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("j123456789", "J-12345678-9"),
        ("J-12345678-9", "J-12345678-9"),
        ("J 12345678 9", "J-12345678-9"),
        ("V-1234567-8", "V-01234567-8"),
        ("g200001234", "G-20000123-4"),
    ],
)
def test_normaliza(raw: str, expected: str) -> None:
    assert normalize_rif(raw) == expected


@pytest.mark.parametrize("raw", ["X-12345678-9", "J-1", "J-123456789-1", "", "J-1234A678-9"])
def test_rechaza(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_rif(raw)
