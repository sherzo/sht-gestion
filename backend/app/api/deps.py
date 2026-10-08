"""Declaración de acceso por endpoint y usuario actual (RNF-05, principio IV, ADR-0005).

Cada endpoint declara exactamente una de: `public()`, `require_authenticated()` o
`require_roles(...)`. Una prueba recorre todas las rutas y falla si alguna no la tiene
(FR-011, research R9).

El JWT solo identifica usuario y sesión: en cada petición se leen ambos de la base, así
que desactivar, cambiar el rol o cerrar sesión rige desde la siguiente operación
(FR-013, research R3).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.db.models import AppUser, UserSession
from app.db.session import get_db
from app.domain.roles import Role

DbSession = Annotated[Session, Depends(get_db)]


@dataclass(frozen=True)
class CurrentUser:
    user: AppUser
    session: UserSession

    @property
    def role(self) -> Role:
        return Role(self.user.role)


def _not_authenticated() -> ApiError:
    return ApiError(401, "not_authenticated", "Debes iniciar sesión")


def _session_ended() -> ApiError:
    return ApiError(401, "session_ended", "Tu sesión terminó. Vuelve a iniciar sesión")


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def _load_current_user(request: Request, db: Session) -> CurrentUser:
    token = _bearer_token(request)
    if token is None:
        raise _not_authenticated()
    claims = decode_access_token(token)
    if claims is None:
        raise _not_authenticated()
    row = db.execute(
        select(AppUser, UserSession)
        .join(UserSession, UserSession.user_id == AppUser.id)
        .where(UserSession.id == claims.session_id, AppUser.id == claims.user_id)
    ).first()
    if row is None:
        raise _not_authenticated()
    user, session = row
    if not user.is_active or session.revoked_at is not None or session.expires_at <= utcnow():
        raise _session_ended()
    return CurrentUser(user=user, session=session)


def _mark(dependency: Callable[..., Any], access: str) -> Callable[..., Any]:
    dependency.access = access  # type: ignore[attr-defined]
    return dependency


def public() -> Callable[..., Any]:
    """Accesible sin sesión (FR-012)."""

    def dependency() -> None:
        return None

    return _mark(dependency, "public")


def require_authenticated(*, allow_temporary_password: bool = False) -> Callable[..., Any]:
    """Cualquier usuario con sesión. Con contraseña temporal solo si se permite (FR-016a)."""

    def dependency(request: Request, db: DbSession) -> CurrentUser:
        current = _load_current_user(request, db)
        if current.user.must_change_password and not allow_temporary_password:
            raise ApiError(
                403,
                "password_change_required",
                "Debes cambiar tu contraseña antes de continuar",
            )
        return current

    return _mark(dependency, "authenticated")


def require_roles(*roles: Role) -> Callable[..., Any]:
    """Solo los roles indicados, leídos de la base de datos (FR-010)."""
    allowed = frozenset(roles)

    def dependency(request: Request, db: DbSession) -> CurrentUser:
        current = _load_current_user(request, db)
        if current.user.must_change_password:
            raise ApiError(
                403,
                "password_change_required",
                "Debes cambiar tu contraseña antes de continuar",
            )
        if current.role not in allowed:
            raise ApiError(403, "forbidden", "No tienes permiso para esta operación")
        return current

    return _mark(dependency, "roles")
