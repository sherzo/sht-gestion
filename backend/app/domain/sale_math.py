"""Cálculo de la venta (RF-21, RF-22, RF-23, RF-25; RN-02, RN-04, RN-06; ADR-0004; research
R1 de la etapa 1.3).

Funciones puras, sin base de datos: subtotales, descuentos por ítem y sobre el total con
su reparto, totales en USD y Bs, lo que cubre cada pago, saldo, excedente, vuelto y
sobrepago. `packages/shared/src/money.ts` implementa exactamente lo mismo para el equipo, y
los dos ejecutan los casos de `packages/shared/test-vectors/money.json`. Solo redondea con
los helpers de `domain/money.py`.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.money import round_usd, usd_to_ves, validate_usd_amount, ves_to_usd

ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
MAX_LINES = 100
MAX_PAYMENTS = 10
MAX_CHANGE = 5


@dataclass(frozen=True)
class DiscountInput:
    """Descuento en monto en USD (`amount`) o en porcentaje (`percent`) (RF-22)."""

    type: str  # "amount" | "percent"
    value: Decimal


@dataclass(frozen=True)
class LineInput:
    id: str
    unit_price_usd: Decimal
    quantity: Decimal  # ya validada y convertida de cm a m (RF-21)
    discount: DiscountInput | None = None


@dataclass(frozen=True)
class MoneyInput:
    """Un pago o un vuelto, en la moneda de su método."""

    method: str
    currency: str  # "VES" | "USD" | "USDT"
    amount: Decimal


@dataclass(frozen=True)
class SaleInput:
    rate: Decimal
    lines: list[LineInput]
    discount: DiscountInput | None = None
    payments: list[MoneyInput] = field(default_factory=list)
    change: list[MoneyInput] = field(default_factory=list)


@dataclass(frozen=True)
class LineResult:
    id: str
    line_subtotal_usd: Decimal
    item_discount_usd: Decimal
    allocated_sale_discount_usd: Decimal
    line_total_usd: Decimal


@dataclass(frozen=True)
class SaleResult:
    lines: list[LineResult]
    subtotal_usd: Decimal
    discount_usd: Decimal
    total_usd: Decimal
    total_ves: Decimal
    payments_usd: list[Decimal]
    paid_usd: Decimal
    balance_usd: Decimal
    balance_ves: Decimal
    excess_usd: Decimal
    change_usd: list[Decimal]
    change_total_usd: Decimal
    overpaid_usd: Decimal


def discount_amount(discount: DiscountInput, base_usd: Decimal) -> Decimal:
    """Descuento en USD sobre `base_usd`, a 2 decimales: el monto tal cual o la base por el
    porcentaje. Rechaza valores que no sean mayores que cero o que superen la base."""
    if not discount.value.is_finite() or discount.value <= 0:
        raise ValueError("El descuento debe ser mayor que cero")
    if round_usd(discount.value) != discount.value:
        raise ValueError("El descuento admite como máximo 2 decimales")
    if discount.type == "percent":
        if discount.value > HUNDRED:
            raise ValueError("El porcentaje no puede ser mayor que 100")
        return round_usd(base_usd * discount.value / HUNDRED)
    if discount.type != "amount":
        raise ValueError("El tipo de descuento no es válido")
    amount = round_usd(discount.value)
    if amount > base_usd:
        raise ValueError("El descuento no puede ser mayor que el monto al que se aplica")
    return amount


def allocate_discount(nets: list[Decimal], discount_usd: Decimal) -> list[Decimal]:
    """Reparte el descuento sobre el total en proporción al neto de cada línea, redondeando
    mitad hacia arriba; el residuo va a la línea de mayor neto (la primera, si hay empate).
    La suma de lo repartido es exactamente `discount_usd` (ADR-0004)."""
    base = sum(nets, ZERO)
    if discount_usd == 0 or base == 0:
        return [ZERO for _ in nets]
    shares = [round_usd(discount_usd * net / base) for net in nets]
    residue = discount_usd - sum(shares, ZERO)
    if residue:
        largest = max(range(len(nets)), key=lambda i: (nets[i], -i))
        shares[largest] += residue
    return shares


def amount_usd(money: MoneyInput, rate: Decimal) -> Decimal:
    """USD que cubre un pago o un vuelto: Bs ÷ tasa (RN-06); USD, Zelle y USDT 1:1 (RN-04)."""
    amount = validate_usd_amount(money.amount)
    if money.currency == "VES":
        return ves_to_usd(amount, rate)
    return amount


def compute_sale(sale: SaleInput) -> SaleResult:
    """Calcula la venta completa. Lanza ValueError con un mensaje en español si algo no es
    válido (descuentos fuera de rango, montos no positivos, vuelto mayor que el excedente,
    límites de research R16)."""
    if not sale.lines:
        raise ValueError("La venta no tiene productos")
    if len(sale.lines) > MAX_LINES:
        raise ValueError(f"Una venta admite como máximo {MAX_LINES} productos")
    if len(sale.payments) > MAX_PAYMENTS:
        raise ValueError(f"Una venta admite como máximo {MAX_PAYMENTS} pagos")
    if len(sale.change) > MAX_CHANGE:
        raise ValueError(f"Una venta admite como máximo {MAX_CHANGE} vueltos")

    subtotals: list[Decimal] = []
    item_discounts: list[Decimal] = []
    for line in sale.lines:
        subtotal = round_usd(line.unit_price_usd * line.quantity)
        subtotals.append(subtotal)
        item_discounts.append(
            discount_amount(line.discount, subtotal) if line.discount is not None else ZERO
        )
    nets = [subtotal - item for subtotal, item in zip(subtotals, item_discounts, strict=True)]
    subtotal_usd = sum(nets, ZERO)

    discount_usd = (
        discount_amount(sale.discount, subtotal_usd) if sale.discount is not None else ZERO
    )
    allocated = allocate_discount(nets, discount_usd)
    lines = [
        LineResult(
            id=line.id,
            line_subtotal_usd=subtotals[i],
            item_discount_usd=item_discounts[i],
            allocated_sale_discount_usd=allocated[i],
            line_total_usd=nets[i] - allocated[i],
        )
        for i, line in enumerate(sale.lines)
    ]
    total_usd = subtotal_usd - discount_usd

    payments_usd = [amount_usd(payment, sale.rate) for payment in sale.payments]
    paid_usd = sum(payments_usd, ZERO)
    balance_usd = max(total_usd - paid_usd, ZERO)
    excess_usd = max(paid_usd - total_usd, ZERO)
    change_usd = [amount_usd(change, sale.rate) for change in sale.change]
    change_total_usd = sum(change_usd, ZERO)
    if change_total_usd > excess_usd:
        raise ValueError("El vuelto no puede ser mayor que el excedente")

    return SaleResult(
        lines=lines,
        subtotal_usd=subtotal_usd,
        discount_usd=discount_usd,
        total_usd=total_usd,
        total_ves=usd_to_ves(total_usd, sale.rate),
        payments_usd=payments_usd,
        paid_usd=paid_usd,
        balance_usd=balance_usd,
        balance_ves=usd_to_ves(balance_usd, sale.rate),
        excess_usd=excess_usd,
        change_usd=change_usd,
        change_total_usd=change_total_usd,
        overpaid_usd=excess_usd - change_total_usd,
    )


def suggested_ves(balance_usd: Decimal, rate: Decimal) -> Decimal:
    """Monto en Bs que cubre exactamente un saldo en USD (FR-036): con tasa mayor que 1,
    `ves_to_usd(suggested_ves(saldo))` devuelve el mismo saldo."""
    return usd_to_ves(balance_usd, rate)
