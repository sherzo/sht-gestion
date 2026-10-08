"""Regla de bloqueo por intentos fallidos (RF-44/FR-004, FR-028)."""

from datetime import UTC, datetime, timedelta

from app.domain.lockout import is_locked, login_locked_until, register_failure

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def test_cuatro_fallos_no_bloquean() -> None:
    attempts = 0
    for _ in range(4):
        attempts, locked_until = register_failure(attempts, NOW)
    assert attempts == 4
    assert locked_until is None


def test_quinto_fallo_bloquea_15_minutos() -> None:
    attempts, locked_until = register_failure(4, NOW)
    assert attempts == 5
    assert locked_until == NOW + timedelta(minutes=15)


def test_bloqueo_vigente_hasta_que_pasan_15_minutos() -> None:
    locked_until = NOW + timedelta(minutes=15)
    assert is_locked(locked_until, NOW + timedelta(minutes=14, seconds=59))
    assert not is_locked(locked_until, NOW + timedelta(minutes=15))
    assert not is_locked(None, NOW)


def test_bloqueo_de_inicio_de_sesion_desde_la_auditoria() -> None:
    assert login_locked_until(4, NOW) is None
    assert login_locked_until(5, NOW) == NOW + timedelta(minutes=15)
    assert login_locked_until(7, NOW) == NOW + timedelta(minutes=15)
    assert login_locked_until(0, None) is None
