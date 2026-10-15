"""Documento del cliente de una venta: cédula o RIF (RF-28/FR-019, research R11).

- Con `V` o `E` sin dígito verificador es una cédula de 6 a 8 dígitos: `v12345678` y
  `V 12.345.678` → `V-12345678`. Con más dígitos se rechaza: el RIF de una persona
  natural se escribe con guiones (`V-12345678-9`).
- Escrito con guion antes del dígito verificador, o con `J`, `G`, `P` o `C`, es un RIF
  normalizado con `domain/rif.py`.
"""

import re

from app.domain.rif import normalize_rif

_SPACES_AND_DOTS = re.compile(r"[\s.]")
_ID_CARD = re.compile(r"^([VE])-?(\d+)$")
_NATURAL_RIF = re.compile(r"^[VE]-?\d{1,8}-\d$")


def normalize_document(text: str) -> str:
    """Devuelve la cédula o el RIF normalizado, o lanza ValueError en español."""
    compact = _SPACES_AND_DOTS.sub("", text).upper()
    if _NATURAL_RIF.fullmatch(compact) or compact[:1] in {"J", "G", "P", "C"}:
        return normalize_rif(compact)
    match = _ID_CARD.fullmatch(compact)
    if match is None:
        raise ValueError("El documento debe ser una cédula (V-12345678) o un RIF (J-12345678-9)")
    letter, digits = match.groups()
    if len(digits) > 8:
        raise ValueError(
            "Para un RIF de persona natural escribe los guiones, por ejemplo V-12345678-9"
        )
    if len(digits) < 6:
        raise ValueError("La cédula debe tener entre 6 y 8 dígitos")
    return f"{letter}-{digits}"
