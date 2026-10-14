"""Costo de compras con los casos compartidos (RN-09/FR-011, FR-015; RN-14/FR-018;
RN-20/FR-030, FR-031; SC-001, SC-010). Sin base de datos."""

import json
import random
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.costing import (
    ChargeInput,
    allocate_by_value,
    charge_amount_usd,
    landed_unit_cost,
    undo_purchase,
    weighted_average,
)
from app.domain.money import ves_to_usd_cost

CASES = json.loads((Path(__file__).parent / "cases" / "costing_cases.json").read_text("utf-8"))


def dec(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def ids(group: str) -> list[str]:
    return [case["name"] for case in CASES[group]]


@pytest.mark.parametrize("case", CASES["weighted_average"], ids=ids("weighted_average"))
def test_promedio_ponderado(case: dict) -> None:
    result = weighted_average(
        dec(case["stock"]), dec(case["cost"]), dec(case["quantity"]), dec(case["unit_cost"])
    )
    assert str(result) == case["expected"]


@pytest.mark.parametrize("case", CASES["undo_purchase"], ids=ids("undo_purchase"))
def test_deshacer_compra(case: dict) -> None:
    result = undo_purchase(
        dec(case["stock"]), dec(case["cost"]), dec(case["quantity"]), dec(case["unit_cost"])
    )
    assert (None if result is None else str(result)) == case["expected"]


@pytest.mark.parametrize("case", CASES["charges"], ids=ids("charges"))
def test_monto_del_gasto(case: dict) -> None:
    raw = case["charge"]
    charge = ChargeInput(
        raw["charge_type"], dec(raw["percent"]), dec(raw["amount"]), raw["currency"]
    )
    result = charge_amount_usd(charge, dec(case["merchandise_total_usd"]), dec(case["rate"]))
    assert str(result) == case["expected"]


def test_gasto_en_bs_sin_tasa() -> None:
    charge = ChargeInput("fixed", amount=Decimal("100.00"), currency="VES")
    with pytest.raises(ValueError):
        charge_amount_usd(charge, Decimal("10.00"), None)


@pytest.mark.parametrize("case", CASES["allocation"], ids=ids("allocation"))
def test_reparto_por_valor(case: dict) -> None:
    totals = [Decimal(value) for value in case["line_totals"]]
    result = allocate_by_value(totals, dec(case["charges_total"]))
    assert [str(value) for value in result] == case["expected"]


@pytest.mark.parametrize("case", CASES["landed"], ids=ids("landed"))
def test_costo_final(case: dict) -> None:
    result = landed_unit_cost(
        dec(case["unit_cost_usd"]), dec(case["allocated"]), dec(case["quantity"])
    )
    assert str(result) == case["expected"]


@pytest.mark.parametrize("case", CASES["ves_to_usd"], ids=ids("ves_to_usd"))
def test_costo_en_bs_a_usd(case: dict) -> None:
    assert str(ves_to_usd_cost(dec(case["amount_ves"]), dec(case["rate"]))) == case["expected"]


def test_el_reparto_suma_exactamente_los_gastos() -> None:
    """SC-010: la suma de lo repartido es siempre el total de gastos."""
    rng = random.Random(20261013)
    for _ in range(200):
        lines = [Decimal(rng.randint(1, 500_000)) / 100 for _ in range(rng.randint(1, 30))]
        total = Decimal(rng.randint(0, 2_000_000)) / 100
        shares = allocate_by_value(lines, total)
        assert sum(shares, Decimal(0)) == total
        assert all(share >= 0 for share in shares)
