"""Validación de cantidades según la unidad (RF-05/FR-020, ADR-0004, research R3).

Único punto del backend que valida los decimales de una cantidad. Cada unidad declara
cuántos decimales admite (`metro` 2, precisión de centímetro; `unidad` 0). Lo que tiene
más decimales se rechaza, nunca se redondea en silencio.
"""

from decimal import Decimal, InvalidOperation

# Límite del dominio `quantity` (NUMERIC(14,2)): 12 dígitos enteros.
MAX_ABS_QUANTITY = Decimal("1E12")


def _step(decimals: int) -> Decimal:
    return Decimal(1).scaleb(-decimals)


def validate_quantity(
    value: Decimal, decimals: int, *, allow_zero: bool, allow_negative: bool
) -> Decimal:
    """Devuelve la cantidad con exactamente `decimals` decimales o lanza ValueError con
    un mensaje en español."""
    if not value.is_finite():
        raise ValueError("La cantidad no es válida")
    if abs(value) >= MAX_ABS_QUANTITY:
        raise ValueError("La cantidad es demasiado grande")
    try:
        exact = value.quantize(_step(decimals))
    except InvalidOperation as exc:
        raise ValueError("La cantidad no es válida") from exc
    if exact != value:
        if decimals == 0:
            raise ValueError("Esta unidad solo admite cantidades enteras")
        raise ValueError(f"Esta unidad admite como máximo {decimals} decimales")
    if exact == 0 and not allow_zero:
        raise ValueError("La cantidad no puede ser cero")
    if exact < 0 and not allow_negative:
        raise ValueError("La cantidad no puede ser negativa")
    return exact


def format_quantity(value: Decimal, decimals: int) -> str:
    """Cantidad como cadena con los decimales de la unidad (`"8"`, `"0.30"`), para JSON."""
    return str(value.quantize(_step(decimals)))
