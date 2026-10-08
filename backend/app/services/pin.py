"""PIN del admin para autorizaciones (RF-44, RN-07/FR-026 a FR-029, research R6).

`verify_admin_pin` lo reutilizarán las etapas siguientes (por ejemplo, el descuento
autorizado de la etapa 1.3) dentro de su propia transacción: si el PIN es correcto, la
autorización queda auditada en esa misma transacción. Si es incorrecto, se deshace lo
pendiente, se guarda el fallo y se lanza el error, porque la operación no debe ocurrir.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError
from app.core.security import hash_secret, verify_dummy, verify_secret
from app.db.models import AppUser, UserSession
from app.domain.lockout import is_locked, register_failure
from app.domain.roles import Role
from app.services.audit import record_audit
from app.services.auth import check_current_password, normalize_username


def set_pin(
    db: Session, *, user: AppUser, session: UserSession, current_password: str, pin: str
) -> None:
    check_current_password(db, user=user, session=session, password=current_password)
    first_time = user.pin_hash is None
    user.pin_hash = hash_secret(pin)
    user.pin_failed_attempts = 0
    user.pin_locked_until = None
    record_audit(
        db,
        action="auth.pin_set",
        user_id=user.id,
        entity_type="app_user",
        entity_id=user.id,
        details={"first_time": first_time},
    )
    db.commit()


def _invalid() -> ApiError:
    return ApiError(403, "pin_invalid", "PIN incorrecto o administrador no válido")


def verify_admin_pin(db: Session, *, requester: AppUser, admin_username: str, pin: str) -> AppUser:
    """Devuelve el admin que autoriza; no confirma la transacción si el PIN es correcto."""
    name = normalize_username(admin_username)
    now = utcnow()
    admin = db.scalar(select(AppUser).where(AppUser.username == name).with_for_update())
    usable = (
        admin is not None
        and admin.role == Role.ADMIN.value
        and admin.is_active
        and admin.pin_hash is not None
    )

    if usable and is_locked(admin.pin_locked_until, now):
        raise ApiError(
            423,
            "pin_locked",
            "El PIN está bloqueado por demasiados intentos fallidos. Espera 15 minutos",
            locked_until=admin.pin_locked_until.isoformat(),
        )

    if usable and verify_secret(admin.pin_hash, pin):
        admin.pin_failed_attempts = 0
        admin.pin_locked_until = None
        record_audit(
            db,
            action="auth.pin_verified",
            user_id=requester.id,
            entity_type="app_user",
            entity_id=admin.id,
            details={"authorized_by": str(admin.id), "admin_username": admin.username},
        )
        return admin

    if not usable:
        verify_dummy(pin)

    # Fallo: se descarta lo pendiente de la operación y se guarda solo el intento.
    admin_id = admin.id if usable else None
    db.rollback()
    target = db.get(AppUser, admin_id, with_for_update=True) if admin_id else None
    details: dict[str, object] = {"admin_username": name}
    if target is not None:
        # Si un bloqueo anterior ya venció, la cuenta de fallos empieza de cero.
        previous = target.pin_failed_attempts
        if target.pin_locked_until is not None and target.pin_locked_until <= now:
            previous = 0
            target.pin_locked_until = None
        attempts, locked_until = register_failure(previous, now)
        target.pin_failed_attempts = attempts
        details["consecutive_failures"] = attempts
        if locked_until is not None:
            target.pin_locked_until = locked_until
    entity = {"entity_type": "app_user", "entity_id": admin_id} if admin_id else {}
    record_audit(db, action="auth.pin_failed", user_id=requester.id, details=details, **entity)
    if target is not None and target.pin_locked_until is not None and target.pin_locked_until > now:
        record_audit(
            db,
            action="auth.pin_locked",
            user_id=requester.id,
            details={"admin_username": name, "locked_until": target.pin_locked_until.isoformat()},
            **entity,
        )
    db.commit()
    raise _invalid()
