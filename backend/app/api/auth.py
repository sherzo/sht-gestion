"""Endpoints de sesión: ingreso, renovación, cierre, usuario actual, contraseña y PIN (RF-44).

Contrato: specs/001-usuarios-autenticacion-permisos/contracts/api.md.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, public, require_authenticated, require_roles
from app.api.schemas import Password, SessionResponse, SessionUser
from app.core.clock import utcnow
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import access_token_expires_in
from app.domain.roles import Role
from app.services import auth as auth_service
from app.services import pin as pin_service
from app.services.auth import IssuedSession

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_PATH = "/api/v1/auth"

# Ruta permitida aun con contraseña temporal (lista blanca de FR-016a).
SessionHolder = Annotated[
    CurrentUser, Depends(require_authenticated(allow_temporary_password=True))
]
AnyRole = Annotated[CurrentUser, Depends(require_authenticated())]
Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]

PinCode = Annotated[str, Field(pattern=r"^[0-9]{4,6}$")]


def require_json(request: Request) -> None:
    """Las peticiones que usan la cookie exigen JSON: obliga a la consulta previa de CORS,
    así un sitio ajeno no puede completarlas (protección CSRF, research R5)."""
    content_type = request.headers.get("content-type", "")
    if not content_type.lower().startswith("application/json"):
        raise ApiError(415, "json_required", "La petición debe enviarse como JSON")


def set_refresh_cookie(response: Response, token: str, expires_at: datetime) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=max(0, int((expires_at - utcnow()).total_seconds())),
        path=COOKIE_PATH,
        domain=settings.refresh_cookie_domain,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )


def clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=COOKIE_PATH,
        domain=settings.refresh_cookie_domain,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )


def session_response(response: Response, issued: IssuedSession) -> SessionResponse:
    set_refresh_cookie(response, issued.refresh_token, issued.session.expires_at)
    return SessionResponse(
        access_token=issued.access_token,
        expires_in=access_token_expires_in(),
        session_expires_at=issued.session.expires_at,
        user=SessionUser.model_validate(issued.user, from_attributes=True),
    )


class LoginRequest(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=200)


class MeResponse(BaseModel):
    user: SessionUser
    session_expires_at: datetime


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: Password


@router.post("/login", dependencies=[Depends(public())])
def login(body: LoginRequest, response: Response, db: DbSession) -> SessionResponse:
    issued = auth_service.login(db, username=body.username, password=body.password)
    return session_response(response, issued)


@router.post("/refresh", dependencies=[Depends(public()), Depends(require_json)])
def refresh(request: Request, response: Response, db: DbSession) -> SessionResponse:
    token = request.cookies.get(get_settings().refresh_cookie_name)
    issued = auth_service.refresh(db, token)
    return session_response(response, issued)


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_json)]
)
def logout(current: SessionHolder, response: Response, db: DbSession) -> None:
    auth_service.logout(db, current.session)
    clear_refresh_cookie(response)


@router.get("/me")
def me(current: SessionHolder) -> MeResponse:
    return MeResponse(
        user=SessionUser.model_validate(current.user, from_attributes=True),
        session_expires_at=current.session.expires_at,
    )


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: ChangePasswordRequest, current: SessionHolder, db: DbSession) -> None:
    auth_service.change_password(
        db,
        user=current.user,
        session=current.session,
        current_password=body.current_password,
        new_password=body.new_password,
    )


class SetPinRequest(BaseModel):
    current_password: str = Field(max_length=200)
    pin: PinCode


class VerifyPinRequest(BaseModel):
    admin_username: str = Field(max_length=100)
    pin: str = Field(max_length=20)


class Authorizer(BaseModel):
    id: uuid.UUID
    full_name: str


class VerifyPinResponse(BaseModel):
    authorized_by: Authorizer


@router.put("/pin", status_code=status.HTTP_204_NO_CONTENT)
def set_pin(body: SetPinRequest, current: Admin, db: DbSession) -> None:
    pin_service.set_pin(
        db,
        user=current.user,
        session=current.session,
        current_password=body.current_password,
        pin=body.pin,
    )


@router.post("/pin/verify")
def verify_pin(body: VerifyPinRequest, current: AnyRole, db: DbSession) -> VerifyPinResponse:
    admin = pin_service.verify_admin_pin(
        db, requester=current.user, admin_username=body.admin_username, pin=body.pin
    )
    db.commit()
    return VerifyPinResponse(authorized_by=Authorizer(id=admin.id, full_name=admin.full_name))
