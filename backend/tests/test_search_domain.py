"""Normalización del texto de búsqueda, sin base de datos (RF-06/FR-032, R4)."""

from app.domain.search import build_search_text, normalize_text, search_tokens


def test_sin_acentos_ni_mayusculas() -> None:
    """FR-032: la búsqueda no distingue mayúsculas ni acentos."""
    assert normalize_text("Conexión") == "conexion"
    assert normalize_text("  MANGUERA   Hidráulica ") == "manguera hidraulica"


def test_conserva_medidas_y_sku() -> None:
    """FR-032: medidas como 1/2" y códigos como CON-0012 se buscan tal cual."""
    assert normalize_text('R2 1/2"') == 'r2 1/2"'
    assert normalize_text("CON-0012") == "con-0012"


def test_texto_de_busqueda_reune_todos_los_campos() -> None:
    """FR-032: nombre, descripción, SKU y valores de atributos."""
    text = build_search_text("Manguera R2", "Dos mallas", "MAN-0001", ["R2", '1/2"', "Caucho"])
    assert text == 'man-0001 manguera r2 dos mallas r2 1/2" caucho'


def test_palabras_de_la_consulta() -> None:
    """FR-032: varias palabras en cualquier orden, sin repetidos."""
    assert search_tokens('  R2   1/2"  r2 ') == ["r2", '1/2"']
    assert search_tokens("   ") == []
