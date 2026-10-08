"""Inicio de sesión, jornada de 12 horas, renovación y cierre (RF-44/FR-002 a FR-006)."""

from datetime import timedelta

import pytest

from app.domain.roles import Role
from tests.conftest import DEFAULT_PASSWORD
from tests.helpers import REFRESH_COOKIE, audit_entries, bearer

pytestmark = pytest.mark.db


def _login(client, username, password=DEFAULT_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _refresh_with(client, token):
    client.cookies.clear()
    return client.post(
        "/api/v1/auth/refresh", json={}, headers={"Cookie": f"{REFRESH_COOKIE}={token}"}
    )


def test_inicio_de_sesion_sin_distinguir_mayusculas(client, make_user, db) -> None:
    user = make_user(Role.SELLER, username="maria")

    response = _login(client, "  MARIA ")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == str(user.id)
    assert body["user"]["role"] == "seller"
    assert body["expires_in"] == 900
    assert REFRESH_COOKIE in response.cookies
    db.refresh(user)
    assert user.last_login_at is not None
    [entry] = audit_entries(db, "auth.login_succeeded")
    assert entry.user_id == user.id
    assert entry.details["username"] == "maria"


def test_credenciales_incorrectas_no_revelan_si_el_usuario_existe(client, make_user, db) -> None:
    make_user(Role.SELLER, username="maria")
    make_user(Role.SELLER, username="pedro", is_active=False)

    wrong_password = _login(client, "maria", "otra-clave")
    unknown_user = _login(client, "nadie")
    inactive_user = _login(client, "pedro")

    for response in (wrong_password, unknown_user, inactive_user):
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "invalid_credentials"
    messages = {
        r.json()["detail"]["message"] for r in (wrong_password, unknown_user, inactive_user)
    }
    assert len(messages) == 1
    failed = audit_entries(db, "auth.login_failed")
    assert [entry.details["username"] for entry in failed] == ["maria", "nadie", "pedro"]


def test_cinco_fallos_bloquean_15_minutos_aunque_la_clave_sea_correcta(
    client, make_user, advance_clock, db
) -> None:
    make_user(Role.SELLER, username="maria")
    for _ in range(5):
        assert _login(client, "maria", "otra-clave").status_code == 401

    locked = _login(client, "maria")
    assert locked.status_code == 423
    assert locked.json()["detail"]["code"] == "account_locked"
    assert "locked_until" in locked.json()["detail"]
    # Uno al empezar el bloqueo y otro por el intento rechazado (R6).
    assert len(audit_entries(db, "auth.login_locked")) == 2

    advance_clock(timedelta(minutes=15, seconds=1))
    assert _login(client, "maria").status_code == 200


def test_un_nombre_inexistente_se_bloquea_igual_que_uno_real(client, make_user) -> None:
    make_user(Role.SELLER, username="maria")
    for _ in range(5):
        _login(client, "maria", "otra-clave")
        _login(client, "fantasma", "otra-clave")

    real = _login(client, "maria", "otra-clave")
    fake = _login(client, "fantasma", "otra-clave")

    assert real.status_code == fake.status_code == 423
    assert real.json()["detail"]["message"] == fake.json()["detail"]["message"]


def test_un_acierto_reinicia_la_cuenta_de_fallos(client, make_user) -> None:
    make_user(Role.SELLER, username="maria")
    for _ in range(4):
        _login(client, "maria", "otra-clave")
    assert _login(client, "maria").status_code == 200
    for _ in range(4):
        _login(client, "maria", "otra-clave")

    assert _login(client, "maria").status_code == 200


def test_renovar_rota_el_token(client, make_user) -> None:
    make_user(Role.SELLER, username="maria")
    first = _login(client, "maria").cookies[REFRESH_COOKIE]

    response = client.post("/api/v1/auth/refresh", json={})

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.cookies[REFRESH_COOKIE] != first


def test_la_jornada_vence_a_las_12_horas_aunque_se_renueve(
    client, make_user, advance_clock
) -> None:
    make_user(Role.SELLER, username="maria")
    _login(client, "maria")

    advance_clock(timedelta(hours=11, minutes=50))
    assert client.post("/api/v1/auth/refresh", json={}).status_code == 200

    advance_clock(timedelta(minutes=11))
    expired = client.post("/api/v1/auth/refresh", json={})
    assert expired.status_code == 401
    assert expired.json()["detail"]["code"] == "session_ended"


def test_reutilizar_un_token_rotado_revoca_la_sesion(client, make_user, advance_clock) -> None:
    make_user(Role.SELLER, username="maria")
    first = _login(client, "maria").cookies[REFRESH_COOKIE]
    second = _refresh_with(client, first).cookies[REFRESH_COOKIE]

    advance_clock(timedelta(seconds=31))
    reused = _refresh_with(client, first)
    assert reused.status_code == 401

    # La sesión quedó revocada: el token vigente tampoco sirve.
    assert _refresh_with(client, second).status_code == 401


def test_dos_pestanas_que_renuevan_a_la_vez_no_cierran_la_sesion(client, make_user) -> None:
    make_user(Role.SELLER, username="maria")
    first = _login(client, "maria").cookies[REFRESH_COOKIE]
    assert _refresh_with(client, first).status_code == 200

    # Dentro de los 30 segundos de gracia, el token anterior todavía sirve.
    assert _refresh_with(client, first).status_code == 200


def test_renovar_exige_json(client, make_user) -> None:
    make_user(Role.SELLER, username="maria")
    _login(client, "maria")

    response = client.post("/api/v1/auth/refresh", content=b"")
    assert response.status_code == 415


def test_renovar_sin_cookie(client) -> None:
    response = client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "session_ended"


def test_cerrar_sesion_invalida_el_token_de_inmediato(client, make_user) -> None:
    make_user(Role.SELLER, username="maria")
    token = _login(client, "maria").json()["access_token"]

    assert client.post("/api/v1/auth/logout", json={}, headers=bearer(token)).status_code == 204

    me = client.get("/api/v1/auth/me", headers=bearer(token))
    assert me.status_code == 401
    assert me.json()["detail"]["code"] == "session_ended"
    assert client.post("/api/v1/auth/refresh", json={}).status_code == 401


def test_me_devuelve_el_usuario_y_el_vencimiento_de_la_jornada(client, make_user) -> None:
    user = make_user(Role.WAREHOUSE, username="ana", full_name="Ana Gómez")
    token = _login(client, "ana").json()["access_token"]

    response = client.get("/api/v1/auth/me", headers=bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert body["user"] == {
        "id": str(user.id),
        "username": "ana",
        "full_name": "Ana Gómez",
        "role": "warehouse",
        "must_change_password": False,
    }
    assert body["session_expires_at"]


def test_sin_token_o_con_token_invalido(client) -> None:
    assert client.get("/api/v1/auth/me").json()["detail"]["code"] == "not_authenticated"
    invalid = client.get("/api/v1/auth/me", headers=bearer("no-es-un-jwt"))
    assert invalid.status_code == 401
    assert invalid.json()["detail"]["code"] == "not_authenticated"


def test_al_vencer_el_bloqueo_la_cuenta_vuelve_a_cero(client, make_user, advance_clock) -> None:
    """RF-44/FR-004: tras el bloqueo, un solo error no vuelve a bloquear."""
    make_user(Role.SELLER, username="maria")
    for _ in range(5):
        _login(client, "maria", "otra-clave")
    advance_clock(timedelta(minutes=15, seconds=1))

    assert _login(client, "maria", "otra-clave").status_code == 401
    assert _login(client, "maria").status_code == 200


def test_intentos_en_paralelo_no_superan_el_limite(make_user, db) -> None:
    """RF-44/FR-004: peticiones simultáneas no prueban más de 5 contraseñas."""
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    from app.main import app

    make_user(Role.SELLER, username="maria")

    def attempt(_: int) -> int:
        with TestClient(app) as local_client:
            return _login(local_client, "maria", "otra-clave").status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        statuses = list(pool.map(attempt, range(12)))

    assert statuses.count(401) == 5
    assert statuses.count(423) == 7
    assert len(audit_entries(db, "auth.login_failed")) == 5
