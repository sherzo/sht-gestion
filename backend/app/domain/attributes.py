"""Validación de los atributos de un producto contra su categoría (RF-04/FR-006, R5).

Cada categoría define sus atributos (texto, número u opción de una lista). Un producto
guarda `{clave: valor}`. Reglas:

- Las claves que la categoría no define se rechazan.
- Los atributos obligatorios activos deben tener valor.
- Una opción debe existir y estar activa. Un valor ya guardado se conserva aunque su
  opción o su atributo se hayan desactivado después (FR-030), pero no se puede elegir de
  nuevo.
- Los valores vacíos se tratan como ausentes.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

DataType = Literal["text", "number", "option"]
MAX_TEXT_LENGTH = 200


@dataclass(frozen=True)
class AttributeSpec:
    key: str
    label: str
    data_type: DataType
    options: list[dict[str, Any]] = field(default_factory=list)
    is_required: bool = False
    is_active: bool = True

    def option_values(self, *, only_active: bool) -> set[str]:
        return {
            str(option["value"])
            for option in self.options
            if not only_active or option.get("is_active", True)
        }


class AttributeValidationError(ValueError):
    """Errores por clave de atributo, con mensajes en español."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Hay atributos inválidos")
        self.errors = errors


def _is_empty(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _clean_value(spec: AttributeSpec, value: object, previous: object) -> str:
    if spec.data_type == "number":
        if isinstance(value, bool) or not isinstance(value, str | int):
            raise ValueError("Debe ser un número")
        try:
            number = Decimal(str(value).strip())
        except InvalidOperation as exc:
            raise ValueError("Debe ser un número") from exc
        if not number.is_finite():
            raise ValueError("Debe ser un número")
        return str(number)
    if not isinstance(value, str):
        raise ValueError("Debe ser un texto")
    text = value.strip()
    if spec.data_type == "text":
        if len(text) > MAX_TEXT_LENGTH:
            raise ValueError(f"Admite como máximo {MAX_TEXT_LENGTH} caracteres")
        return text
    # Opción: una ya guardada se conserva aunque se haya desactivado.
    if text == previous:
        return text
    if text in spec.option_values(only_active=True):
        return text
    if text in spec.option_values(only_active=False):
        raise ValueError("Esta opción está desactivada")
    raise ValueError("Elige una de las opciones de la lista")


def validate_attributes(
    values: dict[str, Any], specs: list[AttributeSpec], previous: dict[str, Any] | None
) -> dict[str, str]:
    """Devuelve los atributos limpios o lanza AttributeValidationError."""
    previous = previous or {}
    by_key = {spec.key: spec for spec in specs}
    errors: dict[str, str] = {}
    cleaned: dict[str, str] = {}

    for key, value in values.items():
        spec = by_key.get(key)
        if spec is None:
            errors[key] = "Este atributo no existe en la categoría"
            continue
        if _is_empty(value):
            continue
        if not spec.is_active and value != previous.get(key):
            errors[key] = "Este atributo está desactivado"
            continue
        try:
            cleaned[key] = _clean_value(spec, value, previous.get(key))
        except ValueError as exc:
            errors[key] = str(exc)

    for spec in specs:
        if spec.is_active and spec.is_required and spec.key not in cleaned:
            errors.setdefault(spec.key, "Este campo es obligatorio")

    if errors:
        raise AttributeValidationError(errors)
    return cleaned
