"""Cálculo de la venta con los casos compartidos con TypeScript (RN-02, RN-04, RN-06;
RF-21/FR-011; RF-22/FR-020, FR-021; RF-25/FR-038; FR-013, FR-036, FR-040; SC-003).
Sin base de datos: `packages/shared/src/money.test.ts` ejecuta los mismos casos."""

import json
import random
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.money import usd_to_ves, ves_to_usd
from app.domain.sale_math import (
    DiscountInput,
    LineInput,
    MoneyInput,
    SaleInput,
    allocate_discount,
    compute_sale,
    suggested_ves,
)
from app.domain.units import entered_quantity

VECTORS = Path(__file__).resolve().parents[2] / "packages" / "shared" / "test-vectors"
CASES = json.loads((VECTORS / "money.json").read_text("utf-8"))


def ids(group: str) -> list[str]:
    return [case["name"] for case in CASES[group]]


def discount(data: dict | None) -> DiscountInput | None:
    return None if data is None else DiscountInput(type=data["type"], value=Decimal(data["value"]))


def money(data: dict) -> MoneyInput:
    return MoneyInput(
        method=data["method"], currency=data["currency"], amount=Decimal(data["amount"])
    )


def sale_input(data: dict) -> SaleInput:
    return SaleInput(
        rate=Decimal(data["rate"]),
        lines=[
            LineInput(
                id=line["id"],
                unit_price_usd=Decimal(line["unit_price_usd"]),
                quantity=Decimal(line["quantity"]),
                discount=discount(line["discount"]),
            )
            for line in data["lines"]
        ],
        discount=discount(data["discount"]),
        payments=[money(item) for item in data["payments"]],
        change=[money(item) for item in data["change"]],
    )


def as_strings(result) -> dict:
    return {
        "lines": [
            {
                "id": line.id,
                "line_subtotal_usd": str(line.line_subtotal_usd),
                "item_discount_usd": str(line.item_discount_usd),
                "allocated_sale_discount_usd": str(line.allocated_sale_discount_usd),
                "line_total_usd": str(line.line_total_usd),
            }
            for line in result.lines
        ],
        "subtotal_usd": str(result.subtotal_usd),
        "discount_usd": str(result.discount_usd),
        "total_usd": str(result.total_usd),
        "total_ves": str(result.total_ves),
        "payments_usd": [str(value) for value in result.payments_usd],
        "paid_usd": str(result.paid_usd),
        "balance_usd": str(result.balance_usd),
        "balance_ves": str(result.balance_ves),
        "excess_usd": str(result.excess_usd),
        "change_usd": [str(value) for value in result.change_usd],
        "change_total_usd": str(result.change_total_usd),
        "overpaid_usd": str(result.overpaid_usd),
    }


@pytest.mark.parametrize("case", CASES["quantities"], ids=ids("quantities"))
def test_cantidades_por_unidad_y_cm(case: dict) -> None:
    """RF-21/FR-011: cm ÷ 100 antes de validar; más precisión se rechaza, no se redondea."""
    value = Decimal(case["input"])
    if "error" in case:
        with pytest.raises(ValueError, match=case["error"]):
            entered_quantity(value, case["entered_unit"], case["decimals"])
    else:
        assert (
            str(entered_quantity(value, case["entered_unit"], case["decimals"])) == case["expected"]
        )


@pytest.mark.parametrize("case", CASES["suggested_ves"], ids=ids("suggested_ves"))
def test_monto_en_bs_sugerido(case: dict) -> None:
    """FR-036: el monto en Bs sugerido para el saldo."""
    assert (
        str(suggested_ves(Decimal(case["balance_usd"]), Decimal(case["rate"]))) == case["expected"]
    )


@pytest.mark.parametrize("case", CASES["sales"], ids=ids("sales"))
def test_venta(case: dict) -> None:
    """FR-013, FR-020, FR-021, FR-035 a FR-038: los mismos resultados que el equipo."""
    if "error" in case:
        with pytest.raises(ValueError, match=case["error"]):
            compute_sale(sale_input(case["input"]))
    else:
        assert as_strings(compute_sale(sale_input(case["input"]))) == case["expected"]


def test_reparto_suma_exacta_y_sin_lineas_negativas() -> None:
    """ADR-0004/FR-021: con 200 ventas al azar, el reparto suma exactamente el descuento
    total y ninguna línea queda negativa."""
    rng = random.Random(13)
    for _ in range(200):
        nets = [Decimal(rng.randint(1, 50_000)) / 100 for _ in range(rng.randint(1, 12))]
        base = sum(nets, Decimal("0"))
        discount_usd = Decimal(rng.randint(1, int(base * 100))) / 100
        shares = allocate_discount(nets, discount_usd)
        assert sum(shares, Decimal("0")) == discount_usd
        assert all(net - share >= 0 for net, share in zip(nets, shares, strict=True))


def test_ida_y_vuelta_de_bs_devuelve_el_saldo() -> None:
    """RN-06/FR-036: con tasas mayores que 1, pagar en Bs el monto sugerido cubre el saldo
    exacto, sin un céntimo de diferencia."""
    rng = random.Random(7)
    for _ in range(200):
        balance = Decimal(rng.randint(1, 1_000_000)) / 100
        rate = Decimal(rng.randint(101_000, 100_000_000)) / 100_000
        assert ves_to_usd(usd_to_ves(balance, rate), rate) == balance
