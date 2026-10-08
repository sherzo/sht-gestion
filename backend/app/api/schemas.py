"""Esquemas comunes de la API: usuario de sesión y validación de campos de usuario."""

import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,30}$")


def _normalize_username(value: str) -> str:
    normalized = value.strip().lower()
    if not USERNAME_RE.fullmatch(normalized):
        raise ValueError(
            "Usa de 3 a 30 caracteres: letras sin acento, números, punto, guion o guion bajo"
        )
    return normalized


# Nombre de usuario de alta: normalizado a minúsculas y validado (FR-002, R11).
NewUsername = Annotated[str, AfterValidator(_normalize_username)]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# Contraseñas: mínimo 8 caracteres (FR-008); máximo para no hashear textos enormes.
Password = Annotated[str, Field(min_length=8, max_length=200)]
RoleName = Literal["admin", "seller", "warehouse"]


class SessionUser(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    role: RoleName
    must_change_password: bool


class SessionResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    session_expires_at: datetime
    user: SessionUser
