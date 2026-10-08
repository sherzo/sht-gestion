"""Instalación del primer administrador con código secreto (RF-44/FR-001, research R7)."""

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from app.api.auth import session_response
from app.api.deps import DbSession, public
from app.api.schemas import FullName, NewUsername, Password, SessionResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/setup", tags=["setup"], dependencies=[Depends(public())])


class SetupStatus(BaseModel):
    setup_required: bool


class SetupRequest(BaseModel):
    setup_code: str = Field(max_length=200)
    full_name: FullName
    username: NewUsername
    password: Password


@router.get("/status")
def setup_status(db: DbSession) -> SetupStatus:
    return SetupStatus(setup_required=auth_service.setup_required(db))


@router.post("", status_code=status.HTTP_201_CREATED)
def setup(body: SetupRequest, response: Response, db: DbSession) -> SessionResponse:
    issued = auth_service.setup_admin(
        db,
        setup_code=body.setup_code,
        full_name=body.full_name,
        username=body.username,
        password=body.password,
    )
    return session_response(response, issued)
