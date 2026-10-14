"""Errores de la base de datos que los servicios traducen a mensajes del negocio."""

from sqlalchemy.exc import IntegrityError


def constraint_name(error: IntegrityError) -> str | None:
    """Nombre de la restricción que falló (índice único, `CHECK`…), si Postgres lo informa."""
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None)
