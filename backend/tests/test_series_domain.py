"""Series de los equipos de mostrador (RN-11/FR-001, research R3). Sin base de datos."""

import pytest

from app.domain.series import series_for


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (1, "A"),
        (2, "B"),
        (26, "Z"),
        (27, "AA"),
        (52, "AZ"),
        (53, "BA"),
        (702, "ZZ"),
        (703, "AAA"),
        (18278, "ZZZ"),
    ],
)
def test_serie(number: int, expected: str) -> None:
    assert series_for(number) == expected


@pytest.mark.parametrize("number", [0, -1, 18279])
def test_fuera_de_rango(number: int) -> None:
    with pytest.raises(ValueError):
        series_for(number)


def test_series_distintas() -> None:
    """Cada número da una serie distinta: una serie nunca se repite."""
    assert len({series_for(n) for n in range(1, 18279)}) == 18278
