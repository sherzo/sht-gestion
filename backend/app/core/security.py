"""Hash de contraseñas y PIN, tokens de acceso y de renovación (ADR-0005, research R1–R4)."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.clock import utcnow
from app.core.config import get_settings

JWT_ALGORITHM = "HS256"


@lru_cache
def _hasher() -> PasswordHasher:
    settings = get_settings()
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
    )


@lru_cache
def _dummy_hash() -> str:
    return _hasher().hash(secrets.token_urlsafe(16))


def hash_secret(value: str) -> str:
    """Argon2id para contraseñas y PIN (FR-008, FR-029)."""
    return _hasher().hash(value)


def verify_secret(stored_hash: str, value: str) -> bool:
    try:
        return _hasher().verify(stored_hash, value)
    except VerificationError, InvalidHashError:
        return False


def verify_dummy(value: str) -> None:
    """Gasta el mismo tiempo que una verificación real, para no delatar usuarios (FR-003)."""
    verify_secret(_dummy_hash(), value)


def _jwt_secret() -> str:
    secret = get_settings().jwt_secret
    if secret is None:
        raise RuntimeError("Falta la variable de entorno JWT_SECRET")
    return secret.get_secret_value()


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID, role: str) -> str:
    now = utcnow()
    expires = now + timedelta(minutes=get_settings().access_token_minutes)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID


def decode_access_token(token: str) -> AccessClaims | None:
    """Devuelve los datos del token o None si es inválido o venció."""
    try:
        payload = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            options={
                "require": ["sub", "sid", "exp"],
                "verify_exp": False,
                "verify_iat": False,
            },
        )
        # Las fechas se comparan con el reloj de la API (simulable en pruebas), no con el
        # de PyJWT; por eso se desactivan sus validaciones de exp e iat.
        if payload["exp"] <= utcnow().timestamp():
            return None
        return AccessClaims(uuid.UUID(payload["sub"]), uuid.UUID(payload["sid"]))
    except jwt.InvalidTokenError, ValueError, KeyError:
        return None


def new_refresh_token() -> tuple[str, str]:
    """Token de renovación opaco y su hash SHA-256, que es lo único que se guarda."""
    token = secrets.token_urlsafe(32)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def access_token_expires_in() -> int:
    return get_settings().access_token_minutes * 60


def session_expiry(started_at: datetime) -> datetime:
    return started_at + timedelta(hours=get_settings().session_hours)
