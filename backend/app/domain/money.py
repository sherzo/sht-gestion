"""Montos en USD y Bs (RN-01, RN-02, ADR-0004): precios con 2 decimales, costos con
hasta 6, montos en Bs con 2 y tasas con hasta 8.

Las entradas con más decimales de los permitidos se rechazan, no se redondean. Los
cálculos redondean solo con los helpers de este módulo, siempre mitad hacia arriba
(`ROUND_HALF_UP`, ADR-0004); el costo de compras los usa desde `domain/costing.py`.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

PRICE_DECIMALS = 2  # usd_amount: NUMERIC(14,2)
COST_DECIMALS = 6  # usd_cost: NUMERIC(18,6)
VES_DECIMALS = 2  # ves_amount: NUMERIC(16,2)
RATE_DECIMALS = 8  # rate: NUMERIC(18,8)
PERCENT_DECIMALS = 2  # percent: NUMERIC(5,2)
MAX_PRICE = Decimal("1E12")
MAX_COST = Decimal("1E12")
MAX_VES = Decimal("1E14")
MAX_RATE = Decimal("1E10")

_USD_STEP = Decimal(1).scaleb(-PRICE_DECIMALS)
_COST_STEP = Decimal(1).scaleb(-COST_DECIMALS)


def validate_usd(value: Decimal, decimals: int, *, allow_zero: bool, maximum: Decimal) -> Decimal:
    """Devuelve el monto con exactamente `decimals` decimales o lanza ValueError."""
    if not value.is_finite():
        raise ValueError("El monto no es válido")
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(
            "El monto debe ser mayor que cero"
            if not allow_zero
            else "El monto no puede ser negativo"
        )
    if value >= maximum:
        raise ValueError("El monto es demasiado grande")
    try:
        exact = value.quantize(Decimal(1).scaleb(-decimals))
    except InvalidOperation as exc:
        raise ValueError("El monto no es válido") from exc
    if exact != value:
        raise ValueError(f"Admite como máximo {decimals} decimales")
    return exact


def validate_price(value: Decimal) -> Decimal:
    """Precio de venta en USD con IVA incluido (FR-011, RN-17): mayor que cero."""
    return validate_usd(value, PRICE_DECIMALS, allow_zero=False, maximum=MAX_PRICE)


def validate_cost(value: Decimal) -> Decimal:
    """Costo en USD (FR-013): mayor o igual a cero."""
    return validate_usd(value, COST_DECIMALS, allow_zero=True, maximum=MAX_COST)


def validate_purchase_cost(value: Decimal) -> Decimal:
    """Costo unitario de compra en USD (FR-006): mayor que cero, hasta 6 decimales."""
    return validate_usd(value, COST_DECIMALS, allow_zero=False, maximum=MAX_COST)


def validate_usd_amount(value: Decimal) -> Decimal:
    """Monto en USD (gastos fijos, FR-029): mayor que cero, hasta 2 decimales."""
    return validate_usd(value, PRICE_DECIMALS, allow_zero=False, maximum=MAX_PRICE)


def validate_ves(value: Decimal) -> Decimal:
    """Monto en Bs (FR-006, FR-029): mayor que cero, hasta 2 decimales."""
    return validate_usd(value, VES_DECIMALS, allow_zero=False, maximum=MAX_VES)


def validate_rate(value: Decimal) -> Decimal:
    """Tasa BCV (FR-025): mayor que cero, hasta 8 decimales."""
    try:
        return validate_usd(value, RATE_DECIMALS, allow_zero=False, maximum=MAX_RATE)
    except ValueError as exc:
        raise ValueError(str(exc).replace("El monto", "La tasa")) from exc


def validate_percent(value: Decimal) -> Decimal:
    """Porcentaje de un gasto (FR-029): mayor que cero y hasta 100, con 2 decimales."""
    if value.is_finite() and value > 100:
        raise ValueError("El porcentaje no puede ser mayor que 100")
    try:
        return validate_usd(value, PERCENT_DECIMALS, allow_zero=False, maximum=Decimal("100.01"))
    except ValueError as exc:
        raise ValueError(str(exc).replace("El monto", "El porcentaje")) from exc


def round_usd(value: Decimal) -> Decimal:
    """Monto en USD o en Bs a 2 decimales, mitad hacia arriba."""
    return value.quantize(_USD_STEP, rounding=ROUND_HALF_UP)


def round_cost(value: Decimal) -> Decimal:
    """Costo en USD a 6 decimales, mitad hacia arriba (RN-09)."""
    return value.quantize(_COST_STEP, rounding=ROUND_HALF_UP)


def ves_to_usd_cost(amount_ves: Decimal, rate: Decimal) -> Decimal:
    """Costo en Bs convertido a USD con la tasa de la compra (RF-15): 6 decimales."""
    return round_cost(amount_ves / rate)
