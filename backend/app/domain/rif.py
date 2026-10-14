"""RIF de proveedores (RF-13/FR-002, research R5).

Se normaliza a `X-NNNNNNNN-N`. Se valida el formato, no el dígito verificador, para no
rechazar un RIF real por una variante del cálculo.
"""

import re

_RAW = re.compile(r"^[JGVEPC]\d{2,9}$")
_SEPARATORS = re.compile(r"[\s.\-]")


def normalize_rif(text: str) -> str:
    """Devuelve el RIF normalizado o lanza ValueError con un mensaje en español."""
    compact = _SEPARATORS.sub("", text).upper()
    if not _RAW.fullmatch(compact):
        raise ValueError(
            "El RIF debe tener una letra (J, G, V, E, P o C), hasta 8 dígitos y el dígito "
            "verificador, por ejemplo J-12345678-9"
        )
    letter, number, check = compact[0], compact[1:-1], compact[-1]
    return f"{letter}-{number.zfill(8)}-{check}"
