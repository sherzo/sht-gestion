"""Endpoints de gestión de usuarios, solo para el admin (RF-45).

Contrato: specs/001-usuarios-autenticacion-permisos/contracts/api.md.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, require_roles
from app.api.schemas import FullName, NewUsername, Password, RoleName
from app.db.models import AppUser
from app.domain.roles import Role
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])

Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]


class UserSummary(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    role: RoleName
    is_active: bool
    must_change_password: bool
    has_pin: bool
    last_login_at: datetime | None
    created_at: datetime

    @classmethod
    def of(cls, user: AppUser) -> UserSummary:
        return cls(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            has_pin=user.pin_hash is not None,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )


class CreateUserRequest(BaseModel):
    full_name: FullName
    username: NewUsername
    role: RoleName
    password: Password


class UpdateUserRequest(BaseModel):
    full_name: FullName | None = None
    role: RoleName | None = None
    is_active: bool | None = None


class ResetPasswordRequest(BaseModel):
    new_password: Password


@router.get("")
def list_users(
    current: Admin,
    db: DbSession,
    role: RoleName | None = None,
    is_active: bool | None = None,
) -> list[UserSummary]:
    users = users_service.list_users(db, role=Role(role) if role else None, is_active=is_active)
    return [UserSummary.of(user) for user in users]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(body: CreateUserRequest, current: Admin, db: DbSession) -> UserSummary:
    user = users_service.create_user(
        db,
        actor=current.user,
        full_name=body.full_name,
        username=body.username,
        role=Role(body.role),
        password=body.password,
    )
    db.refresh(user)
    return UserSummary.of(user)


@router.get("/{user_id}")
def get_user(user_id: uuid.UUID, current: Admin, db: DbSession) -> UserSummary:
    return UserSummary.of(users_service.get_user(db, user_id))


@router.patch("/{user_id}")
def update_user(
    user_id: uuid.UUID, body: UpdateUserRequest, current: Admin, db: DbSession
) -> UserSummary:
    user = users_service.update_user(
        db,
        actor=current.user,
        user_id=user_id,
        full_name=body.full_name,
        role=Role(body.role) if body.role else None,
        is_active=body.is_active,
    )
    db.refresh(user)
    return UserSummary.of(user)


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: uuid.UUID, body: ResetPasswordRequest, current: Admin, db: DbSession
) -> None:
    users_service.reset_password(
        db, actor=current.user, user_id=user_id, new_password=body.new_password
    )
