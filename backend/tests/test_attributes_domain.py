"""Validación de atributos contra la categoría, sin base de datos (RF-04/FR-006, R5)."""

import pytest

from app.domain.attributes import AttributeSpec, AttributeValidationError, validate_attributes

HOSE = [
    AttributeSpec(
        key="hose_type",
        label="Tipo",
        data_type="option",
        options=[
            {"value": "R1", "is_active": True},
            {"value": "R2", "is_active": True},
            {"value": "R3", "is_active": False},
        ],
        is_required=True,
    ),
    AttributeSpec(key="length_hint", label="Largo de referencia", data_type="number"),
    AttributeSpec(key="material", label="Material", data_type="text"),
    AttributeSpec(key="old", label="Antiguo", data_type="text", is_active=False),
]


def _errors(values, previous=None) -> dict[str, str]:
    with pytest.raises(AttributeValidationError) as info:
        validate_attributes(values, HOSE, previous)
    return info.value.errors


def test_valores_validos_se_limpian() -> None:
    """FR-006: texto recortado, número decimal como cadena y opción de la lista."""
    cleaned = validate_attributes(
        {"hose_type": "R2", "length_hint": "1.50", "material": "  Caucho  "}, HOSE, None
    )
    assert cleaned == {"hose_type": "R2", "length_hint": "1.50", "material": "Caucho"}


def test_opcion_fuera_de_la_lista() -> None:
    """US1 escenario 4: un valor que no está en la lista se rechaza indicando el atributo."""
    assert "hose_type" in _errors({"hose_type": "R9"})


def test_obligatorio_faltante_o_vacio() -> None:
    """FR-006: los atributos obligatorios activos deben tener valor."""
    assert _errors({})["hose_type"] == "Este campo es obligatorio"
    assert _errors({"hose_type": "  "})["hose_type"] == "Este campo es obligatorio"


def test_clave_desconocida() -> None:
    """FR-006: no se aceptan atributos que la categoría no define."""
    assert "color" in _errors({"hose_type": "R1", "color": "rojo"})


def test_numero_invalido_y_texto_largo() -> None:
    errors = _errors({"hose_type": "R1", "length_hint": "mucho", "material": "x" * 201})
    assert set(errors) == {"length_hint", "material"}


def test_opcion_desactivada_no_se_elige_pero_se_conserva() -> None:
    """FR-030: desactivar una opción no altera los valores guardados."""
    assert "hose_type" in _errors({"hose_type": "R3"})
    kept = validate_attributes({"hose_type": "R3"}, HOSE, {"hose_type": "R3"})
    assert kept == {"hose_type": "R3"}


def test_atributo_desactivado_conserva_su_valor_pero_no_admite_uno_nuevo() -> None:
    """Caso borde: un atributo desactivado conserva el valor histórico."""
    assert "old" in _errors({"hose_type": "R1", "old": "nuevo"}, {"old": "viejo"})
    kept = validate_attributes({"hose_type": "R1", "old": "viejo"}, HOSE, {"old": "viejo"})
    assert kept["old"] == "viejo"
