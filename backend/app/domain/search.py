"""Normalización del texto de búsqueda de productos (RF-06/FR-032, research R4).

El backend guarda en `product.search_text` el nombre, la descripción, el SKU y los
valores de atributos normalizados (minúsculas, sin acentos, espacios simples) y la
búsqueda normaliza la consulta de la misma forma. Se conservan `/`, `"`, `-` y dígitos,
porque así se escriben las medidas (`1/2"`) y los SKU (`CON-0012`).
"""

import unicodedata
from collections.abc import Iterable


def normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.lower().split())


def build_search_text(
    name: str, description: str, sku: str, attribute_values: Iterable[object]
) -> str:
    parts = [sku, name, description, *(str(value) for value in attribute_values)]
    return normalize_text(" ".join(part for part in parts if part))


def search_tokens(query: str) -> list[str]:
    """Palabras de la consulta, normalizadas y sin repetir, en su orden."""
    return list(dict.fromkeys(normalize_text(query).split()))
