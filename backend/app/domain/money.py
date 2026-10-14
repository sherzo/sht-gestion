"""Montos en USD (RN-01, ADR-0004): precios con 2 decimales y costos con hasta 6.

Los montos con más decimales de los permitidos se rechazan, no se redondean. La
conversión a Bs y el redondeo de la venta llegan con la etapa 1.3 a este mismo módulo.
"""

from decimal import Decimal, InvalidOperation

PRICE_DECIMALS = 2  # usd_amount: NUMERIC(14,2)
COST_DECIMALS = 6  # usd_cost: NUMERIC(18,6)
MAX_PRICE = Decimal("1E12")
MAX_COST = Decimal("1E12")


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
