"""Toda ruta declara su acceso; lo que no declara no se expone (RNF-05/FR-011, R9)."""

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.main import app


def _access_declarations(dependant: Dependant) -> list[str]:
    found: list[str] = []
    for sub in dependant.dependencies:
        access = getattr(sub.call, "access", None)
        if access is not None:
            found.append(access)
        found.extend(_access_declarations(sub))
    return found


def test_cada_ruta_declara_exactamente_un_acceso() -> None:
    sin_declaracion: list[str] = []
    con_varias: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        declarations = _access_declarations(route.dependant)
        name = f"{sorted(route.methods)} {route.path}"
        if not declarations:
            sin_declaracion.append(name)
        elif len(declarations) > 1:
            con_varias.append(f"{name}: {declarations}")
    assert not sin_declaracion, f"Rutas sin declaración de acceso: {sin_declaracion}"
    assert not con_varias, f"Rutas con más de una declaración: {con_varias}"
