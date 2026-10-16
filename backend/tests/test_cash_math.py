"""Cuadre de caja con los casos compartidos con TypeScript (RF-31/FR-006, FR-007; SC-002,
SC-003). Sin base de datos: `packages/shared/src/cash.test.ts` ejecuta los mismos casos."""

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.cash_math import CashMovement, MethodInfo, OutflowInput, compute_reconciliation

VECTORS = Path(__file__).resolve().parents[2] / "packages" / "shared" / "test-vectors"
CASES = json.loads((VECTORS / "cash.json").read_text("utf-8"))
METHODS = [MethodInfo(code=item["code"], currency=item["currency"]) for item in CASES["methods"]]


def run(data: dict) -> list[dict]:
    counted = data["counted"]
    rows = compute_reconciliation(
        METHODS,
        Decimal(data["opening_float_ves"]),
        Decimal(data["opening_float_usd"]),
        [
            CashMovement(
                method=item["method"],
                currency=item["currency"],
                kind=item["kind"],
                amount=Decimal(item["amount"]),
            )
            for item in data["movements"]
        ],
        [
            OutflowInput(
                method=item["method"], amount=Decimal(item["amount"]), voided=item["voided"]
            )
            for item in data["outflows"]
        ],
        None if counted is None else {code: Decimal(amount) for code, amount in counted.items()},
    )
    return [
        {key: None if value is None else str(value) for key, value in asdict(row).items()}
        for row in rows
    ]


@pytest.mark.parametrize(
    "case", CASES["reconciliations"], ids=[case["name"] for case in CASES["reconciliations"]]
)
def test_reconciliation(case: dict) -> None:
    assert run(case["input"]) == case["expected"]


@pytest.mark.parametrize("case", CASES["errors"], ids=[case["name"] for case in CASES["errors"]])
def test_reconciliation_errors(case: dict) -> None:
    with pytest.raises(ValueError) as error:
        run(case["input"])
    assert str(error.value) == case["error"]
