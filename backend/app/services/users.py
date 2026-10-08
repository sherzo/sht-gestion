"""Gestión de usuarios por el admin (RF-45/FR-015 a FR-019, FR-016a).

Invariantes (data-model.md): siempre hay al menos un admin activo, un admin no se
desactiva a sí mismo, y al dejar de ser admin se borra el PIN. Los usuarios nunca se
borran.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import hash_secret
from app.db.models import AppUser
from app.domain.roles import Role
from app.services.audit import record_audit
from app.services.auth import normalize_username, revoke_user_sessions


def _not_found() -> ApiError:
    return ApiError(404, "user_not_found", "El usuario no existe")


def _username_taken() -> ApiError:
    return ApiError(409, "username_taken", "Ya existe un usuario con ese nombre")


def list_users(
    db: Session, *, role: Role | None = None, is_active: bool | None = None
) -> list[AppUser]:
    query = select(AppUser).order_by(AppUser.full_name, AppUser.username)
    if role is not None:
        query = query.where(AppUser.role == role.value)
    if is_active is not None:
        query = query.where(AppUser.is_active == is_active)
    return list(db.scalars(query))


def get_user(db: Session, user_id: uuid.UUID) -> AppUser:
    user = db.get(AppUser, user_id)
    if user is None:
        raise _not_found()
    return user


def create_user(
    db: Session, *, actor: AppUser, full_name: str, username: str, role: Role, password: str
) -> AppUser:
    name = normalize_username(username)
    if db.scalar(select(AppUser.id).where(AppUser.username == name)) is not None:
        raise _username_taken()
    user = AppUser(
        username=name,
        full_name=full_name,
        role=role.value,
        password_hash=hash_secret(password),
        must_change_password=True,
        pin_failed_attempts=0,
        is_active=True,
        created_by=actor.id,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise _username_taken() from exc
    record_audit(
        db,
        action="user.created",
        user_id=actor.id,
        entity_type="app_user",
        entity_id=user.id,
        after={"username": user.username, "full_name": user.full_name, "role": user.role},
    )
    db.commit()
    return user


def _other_active_admins(db: Session, user_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(AppUser)
        .where(
            AppUser.role == Role.ADMIN.value,
            AppUser.is_active.is_(True),
            AppUser.id != user_id,
        )
    )


def update_user(
    db: Session,
    *,
    actor: AppUser,
    user_id: uuid.UUID,
    full_name: str | None = None,
    role: Role | None = None,
    is_active: bool | None = None,
) -> AppUser:
    # Bloquea las filas de los admins activos: dos cambios simultáneos no pueden dejar
    # el sistema sin admin (FR-018).
    db.execute(
        select(AppUser.id)
        .where(AppUser.role == Role.ADMIN.value, AppUser.is_active.is_(True))
        .with_for_update()
    )
    user = db.get(AppUser, user_id, with_for_update=True)
    if user is None:
        raise _not_found()

    if is_active is False and user.id == actor.id:
        raise ApiError(409, "cannot_deactivate_self", "No puedes desactivar tu propio usuario")

    leaves_admin = user.role == Role.ADMIN.value and (
        (role is not None and role != Role.ADMIN) or is_active is False
    )
    if leaves_admin and user.is_active and _other_active_admins(db, user.id) == 0:
        raise ApiError(
            409, "last_admin", "Debe quedar al menos un administrador activo en el sistema"
        )

    if full_name is not None and full_name != user.full_name:
        record_audit(
            db,
            action="user.updated",
            user_id=actor.id,
            entity_type="app_user",
            entity_id=user.id,
            before={"full_name": user.full_name},
            after={"full_name": full_name},
        )
        user.full_name = full_name

    if role is not None and role.value != user.role:
        record_audit(
            db,
            action="user.role_changed",
            user_id=actor.id,
            entity_type="app_user",
            entity_id=user.id,
            before={"role": user.role},
            after={"role": role.value},
        )
        user.role = role.value
        if role != Role.ADMIN:
            # Solo los admin tienen PIN (FR-026).
            user.pin_hash = None
            user.pin_failed_attempts = 0
            user.pin_locked_until = None

    if is_active is not None and is_active != user.is_active:
        user.is_active = is_active
        if not is_active:
            revoke_user_sessions(db, user.id, "user_deactivated")
        record_audit(
            db,
            action="user.deactivated" if not is_active else "user.reactivated",
            user_id=actor.id,
            entity_type="app_user",
            entity_id=user.id,
        )

    db.commit()
    return user


def reset_password(
    db: Session, *, actor: AppUser | None, user_id: uuid.UUID, new_password: str
) -> AppUser:
    """Asigna una contraseña temporal (FR-016a). `actor` es None si lo hace el comando."""
    user = db.get(AppUser, user_id, with_for_update=True)
    if user is None:
        raise _not_found()
    user.password_hash = hash_secret(new_password)
    user.must_change_password = True
    revoke_user_sessions(db, user.id, "password_reset")
    record_audit(
        db,
        action="user.password_reset",
        user_id=actor.id if actor else None,
        entity_type="app_user",
        entity_id=user.id,
        details={"source": "admin" if actor else "cli"},
    )
    db.commit()
    return user
