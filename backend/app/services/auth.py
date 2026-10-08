"""Instalación, inicio de sesión, jornada, renovación y contraseña propia (RF-44).

Decisiones: specs/001-usuarios-autenticacion-permisos/research.md R4, R6 y R7.
"""

import hmac
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import exists, func, select, text, update
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import (
    create_access_token,
    hash_refresh_token,
    hash_secret,
    new_refresh_token,
    session_expiry,
    verify_dummy,
    verify_secret,
)
from app.db.models import AppUser, AuditLog, RefreshToken, UserSession
from app.domain.lockout import LOCK_DURATION, MAX_ATTEMPTS, login_locked_until
from app.domain.roles import Role
from app.services.audit import record_audit

# Clave del bloqueo transaccional que serializa las instalaciones simultáneas.
_SETUP_LOCK_KEY = 1_100_001


@dataclass(frozen=True)
class IssuedSession:
    user: AppUser
    session: UserSession
    access_token: str
    refresh_token: str


def normalize_username(value: str) -> str:
    return value.strip().lower()


def _session_ended() -> ApiError:
    return ApiError(401, "session_ended", "Tu sesión terminó. Vuelve a iniciar sesión")


def _has_users(db: Session) -> bool:
    return bool(db.scalar(select(exists().where(AppUser.id.is_not(None)))))


# --- Instalación (FR-001) ---


def setup_required(db: Session) -> bool:
    return get_settings().setup_code is not None and not _has_users(db)


def setup_admin(
    db: Session, *, setup_code: str, full_name: str, username: str, password: str
) -> IssuedSession:
    configured = get_settings().setup_code
    not_available = ApiError(409, "setup_not_available", "El sistema ya está instalado")
    if configured is None:
        raise not_available

    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _SETUP_LOCK_KEY})
    if _has_users(db):
        raise not_available

    now = utcnow()
    recent_failures = db.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.action == "setup.failed", AuditLog.occurred_at > now - LOCK_DURATION)
    )
    if recent_failures >= MAX_ATTEMPTS:
        raise ApiError(
            429,
            "setup_locked",
            "Demasiados intentos fallidos. Espera 15 minutos e intenta de nuevo",
        )

    if not hmac.compare_digest(setup_code.encode(), configured.get_secret_value().encode()):
        record_audit(db, action="setup.failed", details={"reason": "invalid_code"})
        db.commit()
        raise ApiError(403, "invalid_setup_code", "El código de instalación no es correcto")

    user = AppUser(
        username=normalize_username(username),
        full_name=full_name,
        role=Role.ADMIN.value,
        password_hash=hash_secret(password),
        must_change_password=False,
        pin_failed_attempts=0,
        is_active=True,
        last_login_at=now,
    )
    db.add(user)
    db.flush()
    record_audit(
        db,
        action="setup.admin_created",
        user_id=user.id,
        entity_type="app_user",
        entity_id=user.id,
        after={"username": user.username, "full_name": user.full_name, "role": user.role},
    )
    issued = start_session(db, user)
    db.commit()
    return issued


# --- Inicio de sesión (FR-002 a FR-004) ---


def _login_state(db: Session, username: str, now: datetime) -> tuple[int, datetime | None]:
    """Estado del bloqueo de un nombre, exista o no el usuario (R6, ADR-0008).

    Devuelve los fallos seguidos que cuentan y, si está bloqueado, hasta cuándo. Cuentan
    los fallos posteriores al último acierto y al fin del último bloqueo: al vencer un
    bloqueo, la cuenta vuelve a cero.
    """
    name = AuditLog.details["username"].astext
    last_success = db.scalar(
        select(func.max(AuditLog.occurred_at)).where(
            AuditLog.action == "auth.login_succeeded", name == username
        )
    )
    lock_query = select(func.max(AuditLog.details["locked_until"].astext)).where(
        AuditLog.action == "auth.login_locked", name == username
    )
    if last_success is not None:
        lock_query = lock_query.where(AuditLog.occurred_at > last_success)
    last_lock = db.scalar(lock_query)
    locked_until = datetime.fromisoformat(last_lock) if last_lock else None
    if locked_until is not None and now < locked_until:
        return 0, locked_until

    since = max(filter(None, (last_success, locked_until)), default=None)
    query = select(func.count()).where(AuditLog.action == "auth.login_failed", name == username)
    if since is not None:
        query = query.where(AuditLog.occurred_at > since)
    return db.scalar(query), None


def _locked_error(locked_until: datetime) -> ApiError:
    return ApiError(
        423,
        "account_locked",
        "Demasiados intentos fallidos. Espera 15 minutos e intenta de nuevo",
        locked_until=locked_until.isoformat(),
    )


def login(db: Session, *, username: str, password: str) -> IssuedSession:
    name = normalize_username(username)
    # Serializa los intentos con un mismo nombre: sin esto, peticiones en paralelo leerían
    # la misma cuenta de fallos y superarían el límite de 5 (FR-004).
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:name))"), {"name": f"login:{name}"})
    now = utcnow()
    user = db.scalar(select(AppUser).where(AppUser.username == name))
    user_id = user.id if user is not None else None
    entity = {"entity_type": "app_user", "entity_id": user_id} if user_id else {}

    failures, locked_until = _login_state(db, name, now)
    if locked_until is not None:
        # Cada intento rechazado queda registrado, para ver si alguien insiste (R6).
        record_audit(
            db,
            action="auth.login_locked",
            user_id=user_id,
            details={"username": name, "locked_until": locked_until.isoformat()},
            **entity,
        )
        db.commit()
        raise _locked_error(locked_until)

    if user is None:
        verify_dummy(password)
        valid = False
    else:
        valid = verify_secret(user.password_hash, password) and user.is_active

    if not valid:
        failures += 1
        record_audit(
            db,
            action="auth.login_failed",
            user_id=user_id,
            details={"username": name, "consecutive_failures": failures},
            **entity,
        )
        new_lock = login_locked_until(failures, now)
        if new_lock is not None:
            record_audit(
                db,
                action="auth.login_locked",
                user_id=user_id,
                details={"username": name, "locked_until": new_lock.isoformat()},
                **entity,
            )
        db.commit()
        raise ApiError(401, "invalid_credentials", "Usuario o contraseña incorrectos")

    assert user is not None
    user.last_login_at = now
    issued = start_session(db, user)
    record_audit(
        db,
        action="auth.login_succeeded",
        user_id=user.id,
        entity_type="app_user",
        entity_id=user.id,
        details={"username": name, "session_id": str(issued.session.id)},
    )
    db.commit()
    return issued


# --- Jornada y renovación (FR-005, FR-006, research R4) ---


def start_session(db: Session, user: AppUser) -> IssuedSession:
    now = utcnow()
    session = UserSession(
        user_id=user.id, started_at=now, expires_at=session_expiry(now), last_seen_at=now
    )
    db.add(session)
    db.flush()
    token, token_hash = new_refresh_token()
    db.add(RefreshToken(session_id=session.id, token_hash=token_hash, created_at=now))
    access = create_access_token(user.id, session.id, user.role)
    return IssuedSession(user=user, session=session, access_token=access, refresh_token=token)


def refresh(db: Session, token: str | None) -> IssuedSession:
    if not token:
        raise _session_ended()
    now = utcnow()
    current = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(token))
        .with_for_update()
    )
    if current is None:
        raise _session_ended()
    session = db.get(UserSession, current.session_id, with_for_update=True)
    assert session is not None
    user = db.get(AppUser, session.user_id)
    assert user is not None
    if session.revoked_at is not None or session.expires_at <= now or not user.is_active:
        raise _session_ended()

    if current.rotated_at is not None:
        grace = timedelta(seconds=get_settings().refresh_reuse_grace_seconds)
        if now - current.rotated_at > grace:
            # Un token ya usado reaparece: posible robo. Se cierra la jornada entera.
            session.revoked_at = now
            session.revoked_reason = "token_reuse"
            db.commit()
            raise _session_ended()

    new_token, new_hash = new_refresh_token()
    replacement = RefreshToken(session_id=session.id, token_hash=new_hash, created_at=now)
    db.add(replacement)
    db.flush()
    if current.rotated_at is None:
        current.rotated_at = now
        current.replaced_by_id = replacement.id
    session.last_seen_at = now
    access = create_access_token(user.id, session.id, user.role)
    db.commit()
    return IssuedSession(user=user, session=session, access_token=access, refresh_token=new_token)


def logout(db: Session, session: UserSession) -> None:
    session.revoked_at = utcnow()
    session.revoked_reason = "logout"
    db.commit()


def revoke_user_sessions(
    db: Session, user_id: uuid.UUID, reason: str, except_session_id: uuid.UUID | None = None
) -> None:
    now = utcnow()
    statement = (
        update(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .values(revoked_at=now, revoked_reason=reason)
    )
    if except_session_id is not None:
        statement = statement.where(UserSession.id != except_session_id)
    db.execute(statement)


# --- Contraseña propia (FR-007, FR-016a) ---


def check_current_password(
    db: Session, *, user: AppUser, session: UserSession, password: str
) -> None:
    """Comprueba la contraseña actual al cambiarla o al definir el PIN.

    Una sesión abierta y desatendida no debe servir para adivinarla: cada fallo se audita
    y al quinto en la misma sesión esta se cierra.
    """
    if verify_secret(user.password_hash, password):
        return
    session_id = str(session.id)
    failures = 1 + db.scalar(
        select(func.count()).where(
            AuditLog.action == "auth.password_check_failed",
            AuditLog.details["session_id"].astext == session_id,
        )
    )
    record_audit(
        db,
        action="auth.password_check_failed",
        user_id=user.id,
        entity_type="app_user",
        entity_id=user.id,
        details={"session_id": session_id, "failures": failures},
    )
    if failures >= MAX_ATTEMPTS:
        session.revoked_at = utcnow()
        session.revoked_reason = "too_many_attempts"
        db.commit()
        raise ApiError(
            401,
            "session_ended",
            "Demasiados intentos con la contraseña actual. Vuelve a iniciar sesión",
        )
    db.commit()
    raise ApiError(400, "invalid_current_password", "La contraseña actual no es correcta")


def change_password(
    db: Session, *, user: AppUser, session: UserSession, current_password: str, new_password: str
) -> None:
    check_current_password(db, user=user, session=session, password=current_password)
    if new_password == current_password:
        raise ApiError(
            422,
            "validation_error",
            "Hay datos inválidos",
            fields={"new_password": "Debe ser distinta de la actual"},
        )
    user.password_hash = hash_secret(new_password)
    user.must_change_password = False
    revoke_user_sessions(db, user.id, "password_changed", except_session_id=session.id)
    record_audit(
        db,
        action="auth.password_changed",
        user_id=user.id,
        entity_type="app_user",
        entity_id=user.id,
    )
    db.commit()
