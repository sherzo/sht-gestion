"""Costo de las compras (RN-09, RN-14, RN-20; ADR-0004; research R1).

Funciones puras, sin base de datos: monto de los gastos, reparto por valor, costo final
por unidad, promedio ponderado y su reversión al anular. Solo redondean con los
helpers de `domain/money.py`.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import round_cost, round_usd

ZERO = Decimal("0")


@dataclass(frozen=True)
class ChargeInput:
    """Gasto de una compra: porcentaje del total de mercancía o monto fijo."""

    charge_type: str  # "percent" | "fixed"
    percent: Decimal | None = None
    amount: Decimal | None = None
    currency: str | None = None  # "USD" | "VES", solo si es fijo


def charge_amount_usd(
    charge: ChargeInput, merchandise_total_usd: Decimal, rate: Decimal | None
) -> Decimal:
    """Monto en USD de un gasto, a 2 decimales (FR-030)."""
    if charge.charge_type == "percent":
        return round_usd(merchandise_total_usd * charge.percent / 100)
    if charge.currency == "VES":
        if rate is None:
            raise ValueError("Un gasto en Bs necesita la tasa de la compra")
        return round_usd(charge.amount / rate)
    return round_usd(charge.amount)


def allocate_by_value(line_totals: list[Decimal], charges_total: Decimal) -> list[Decimal]:
    """Reparte los gastos en proporción al total de cada línea, a 2 decimales (FR-031).

    El residuo de redondeo va a la línea de mayor valor (la primera, si hay empate), así
    la suma de lo repartido es exactamente `charges_total`.
    """
    if not line_totals:
        return []
    base = sum(line_totals, ZERO)
    if charges_total == 0 or base == 0:
        return [round_usd(ZERO) for _ in line_totals]
    shares = [round_usd(charges_total * total / base) for total in line_totals]
    residue = charges_total - sum(shares, ZERO)
    if residue:
        largest = max(range(len(line_totals)), key=lambda i: (line_totals[i], -i))
        shares[largest] += residue
    return shares


def landed_unit_cost(unit_cost_usd: Decimal, allocated: Decimal, quantity: Decimal) -> Decimal:
    """Costo final por unidad: costo de factura + gasto asignado ÷ cantidad (RN-20)."""
    return round_cost(unit_cost_usd + allocated / quantity)


def weighted_average(
    stock: Decimal, cost: Decimal | None, quantity: Decimal, unit_cost: Decimal
) -> Decimal:
    """Costo promedio ponderado tras una entrada (RN-09/FR-011, FR-015).

    Con stock previo cero o negativo, o sin costo previo, el costo es el de la compra.
    """
    if stock <= 0 or cost is None:
        return round_cost(unit_cost)
    return round_cost((stock * cost + quantity * unit_cost) / (stock + quantity))


def undo_purchase(
    stock: Decimal, cost: Decimal | None, quantity: Decimal, unit_cost: Decimal
) -> Decimal | None:
    """Costo tras deshacer una compra (RN-14/FR-018).

    Devuelve `None` si el resultado no es válido (stock resultante cero o negativo,
    producto sin costo o costo negativo): quien llama conserva el costo y alerta.
    """
    remaining = stock - quantity
    if remaining <= 0 or cost is None:
        return None
    result = round_cost((stock * cost - quantity * unit_cost) / remaining)
    return None if result < 0 else result
