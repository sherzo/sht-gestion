"""Formato del SKU automático (RF-02/FR-002, research R1).

`{prefijo}-{correlativo de al menos 4 dígitos}`: `MAN-0001`, … `MAN-9999`, `MAN-10000`.
El correlativo lo reserva el servicio de productos con bloqueo de la categoría.
"""


def format_sku(prefix: str, number: int) -> str:
    if number < 1:
        raise ValueError("El correlativo del SKU empieza en 1")
    return f"{prefix}-{number:04d}"
