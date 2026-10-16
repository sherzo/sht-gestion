"""Cuadre de la caja por método de pago (RF-31; FR-006, FR-007; ADR-0004; research R1 de la
etapa 1.4).

Función pura, sin base de datos: el esperado de cada método en su moneda, con la fórmula

    esperado = fondo (solo cash_ves y cash_usd) + cobrado − vuelto − devuelto
               + vuelto recuperado − egresos no anulados

y, si hay contado, la diferencia (contado − esperado). No convierte monedas ni usa la tasa
del día: cada método se cuadra en la suya (RN-04, RN-05). El esperado puede ser negativo,
por ejemplo con la devolución de una venta de otra caja (RF-27). Los egresos pueden salir de
cualquier método (RF-32, PRD v0.12).

`packages/shared/src/cash.ts` implementa exactamente lo mismo para el equipo, y los dos
ejecutan los casos de `packages/shared/test-vectors/cash.json`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0.00")
_CENT = Decimal("0.01")

# Los dos métodos con fondo inicial al abrir la caja (RF-29).
CASH_METHODS = ("cash_ves", "cash_usd")
KINDS = ("sale_payment", "change", "void_refund", "void_change")


@dataclass(frozen=True)
class MethodInfo:
    code: str
    currency: str  # "VES" | "USD" | "USDT"


@dataclass(frozen=True)
class CashMovement:
    """Fila de `payment` de la caja: cobro, vuelto o su espejo por anulación."""

    method: str
    currency: str
    kind: str  # uno de KINDS
    amount: Decimal


@dataclass(frozen=True)
class OutflowInput:
    method: str
    amount: Decimal
    voided: bool = False


@dataclass(frozen=True)
class ReconciliationRow:
    method: str
    currency: str
    opening: Decimal
    collected: Decimal
    change_given: Decimal
    refunded: Decimal
    change_recovered: Decimal
    outflows: Decimal
    expected: Decimal
    counted: Decimal | None
    difference: Decimal | None


def _cents(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _unknown_method(code: str) -> ValueError:
    return ValueError(f"Método de pago desconocido: {code}")


def compute_reconciliation(
    methods: Sequence[MethodInfo],
    opening_float_ves: Decimal,
    opening_float_usd: Decimal,
    movements: Sequence[CashMovement],
    outflows: Sequence[OutflowInput],
    counted: Mapping[str, Decimal] | None = None,
) -> list[ReconciliationRow]:
    """Una fila por método, en el orden de `methods` (el del catálogo). Con `counted`, un
    método que falta se toma como contado 0,00 (campo en blanco al cerrar)."""
    currency = {method.code: method.currency for method in methods}
    totals = {code: dict.fromkeys(KINDS, ZERO) for code in currency}
    for movement in movements:
        if movement.kind not in KINDS:
            raise ValueError(f"Tipo de movimiento de caja desconocido: {movement.kind}")
        if movement.method not in currency:
            raise _unknown_method(movement.method)
        if movement.currency != currency[movement.method]:
            raise ValueError(
                f"El movimiento en {movement.method} debe estar en {currency[movement.method]}"
            )
        totals[movement.method][movement.kind] += movement.amount

    outflow_totals = dict.fromkeys(currency, ZERO)
    for outflow in outflows:
        if outflow.method not in currency:
            raise _unknown_method(outflow.method)
        if not outflow.voided:
            outflow_totals[outflow.method] += outflow.amount

    if counted is not None:
        for code, amount in counted.items():
            if code not in currency:
                raise _unknown_method(code)
            if amount < 0:
                raise ValueError("El monto contado no puede ser negativo")

    openings = {"cash_ves": opening_float_ves, "cash_usd": opening_float_usd}
    rows = []
    for method in methods:
        kinds = totals[method.code]
        opening = openings.get(method.code, ZERO)
        expected = (
            opening
            + kinds["sale_payment"]
            - kinds["change"]
            - kinds["void_refund"]
            + kinds["void_change"]
            - outflow_totals[method.code]
        )
        row_counted = None if counted is None else counted.get(method.code, ZERO)
        rows.append(
            ReconciliationRow(
                method=method.code,
                currency=method.currency,
                opening=_cents(opening),
                collected=_cents(kinds["sale_payment"]),
                change_given=_cents(kinds["change"]),
                refunded=_cents(kinds["void_refund"]),
                change_recovered=_cents(kinds["void_change"]),
                outflows=_cents(outflow_totals[method.code]),
                expected=_cents(expected),
                counted=None if row_counted is None else _cents(row_counted),
                difference=None if row_counted is None else _cents(row_counted - expected),
            )
        )
    return rows
