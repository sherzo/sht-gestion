"""Errores de la API con código estable en inglés y mensaje en español (ADR-0006).

Formato: {"detail": {"code": "...", "message": "...", ...}}.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.extra = extra


def validation_error(fields: dict[str, str]) -> ApiError:
    """Error 422 con el mismo formato que los de validación de Pydantic."""
    return ApiError(422, "validation_error", "Hay datos inválidos", fields=fields)


# Mensajes en español para los tipos de error de validación más comunes de Pydantic.
_VALIDATION_MESSAGES = {
    "missing": "Este campo es obligatorio",
    "string_too_short": "Es demasiado corto",
    "string_too_long": "Es demasiado largo",
    "string_pattern_mismatch": "El formato no es válido",
    "string_type": "Debe ser un texto",
    "int_parsing": "Debe ser un número entero",
    "less_than_equal": "El valor es demasiado grande",
    "greater_than_equal": "El valor es demasiado pequeño",
    "literal_error": "El valor no está permitido",
    "enum": "El valor no está permitido",
    "uuid_parsing": "El identificador no es válido",
    "date_from_datetime_parsing": "La fecha no es válida",
    "date_parsing": "La fecha no es válida",
    "bool_parsing": "Debe ser verdadero o falso",
    "json_invalid": "El cuerpo de la petición no es JSON válido",
    "extra_forbidden": "Este campo no se puede enviar",
    "decimal_parsing": "Debe ser un número",
    "decimal_type": "Debe ser un número",
    "dict_type": "Debe ser un objeto",
    "list_type": "Debe ser una lista",
    "bool_type": "Debe ser verdadero o falso",
    "uuid_type": "El identificador no es válido",
    "datetime_from_date_parsing": "La fecha no es válida",
    "datetime_parsing": "La fecha no es válida",
}


def _field_name(location: tuple[Any, ...]) -> str:
    # Se omite el origen ("body", "query", "path") y se unen los niveles con punto.
    parts = [str(part) for part in location[1:]] or [str(part) for part in location]
    return ".".join(parts)


def validation_fields(errors: Any, *, prefix: str | None = None) -> dict[str, str]:
    """Campos con su mensaje en español a partir de los errores de Pydantic. Sin `prefix`
    se omite el origen (`body`, `query`, `path`); con él, se antepone (por ejemplo,
    `payload` para el contenido de una operación de la cola)."""
    fields: dict[str, str] = {}
    for error in errors:
        location = tuple(error.get("loc", ()))
        name = (
            _field_name(location)
            if prefix is None
            else ".".join([prefix, *(str(part) for part in location)])
        )
        if error.get("type") == "value_error":
            # Validadores propios: el mensaje en español viene en el ValueError.
            message = str(error.get("ctx", {}).get("error", "El valor no es válido"))
        else:
            message = _VALIDATION_MESSAGES.get(error.get("type", ""), "El valor no es válido")
        fields.setdefault(name, message)
    return fields


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        detail = {"code": exc.code, "message": exc.message, **exc.extra}
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = validation_fields(exc.errors())
        detail = {"code": "validation_error", "message": "Hay datos inválidos", "fields": fields}
        return JSONResponse(status_code=422, content={"detail": detail})
